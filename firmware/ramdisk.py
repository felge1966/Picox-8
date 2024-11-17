import cpld
import time
import storage
import json
from machine import Pin

instance = None

CONFIG_FILE    = 'picox-8.config.json'
DEFAULT_FILE   = 'default-ramdisk.dsk'

IMAGE_KB       = 120             # size of a ramdisk image
FLUSH_INTERVAL = 15000           # how often to flush ramdisk to flash

FAILSAFE_SWITCH = Pin(27, Pin.IN, Pin.PULL_UP)

class Command:
    RESET = 0
    READ = 1
    READB = 2
    WRITE = 3
    WRITEB = 4
    CKSUM = 5

    @classmethod
    def _create_name_mapping(cls):
        # Create a dictionary mapping values to names
        return {value: name for name, value in cls.__dict__.items() if not name.startswith('_') and isinstance(value, int)}

    @classmethod
    def get_name(cls, value):
        name_mapping = cls._create_name_mapping()
        return name_mapping.get(value, "UNKNOWN_COMMAND")


class RamDisk:
    def __init__(self):
        global instance
        if instance:
            print('Warning: RamDisk instance already exists')
        instance = self
        self.command = None
        self.read_count = None
        self.read_pointer = None
        self.px8_buffer = bytearray(131)                         # maximum number of bytes that are exchanged with host in one command
        self.file_buffer = bytearray(128)
        self.cksum = 0                                           # formatted
        self.pending_writes = False
        self.last_flush = time.ticks_ms()
        self.read_only = False
        self.file = None
        self.read_config()
        self.reopen_file()

    def read_config(self):
        if storage.exists(CONFIG_FILE):
            self.config = json.loads(storage.slurp(CONFIG_FILE))
        else:
            self.init_storage()

    def write_config(self):
        storage.spit(CONFIG_FILE, json.dumps(self.config))
        print(f'RAM-Disk configuration file {CONFIG_FILE} saved')

    def init_storage(self):
        self.config = { 'ramdisk': DEFAULT_FILE }
        name = self.config['ramdisk']
        if not storage.exists(name):
            buf = bytearray(1024)
            with open(storage.path(name), 'wb') as f:
                for i in range(IMAGE_KB):
                    f.write(buf)
            print(f'RAM-Disk file {name} initialized')
        self.write_config()

    def reopen_file(self):
        if self.file != None:
            try:
                self.file.close()
            except OSError as e:
                print(f'Error {e} closing file')
        if FAILSAFE_SWITCH.value() == 0:
            path = '/ramdisk.dsk'
            self.read_only = True
            print(f'Failsafe mode, RAM-Disk in Read-only mode')
        else:
            path = storage.path(self.config['ramdisk'])
            self.read_only = False
        self.file = open(path, 'r+b')
        print(f'RAM-Disk file {path} mounted')

    def valid_file(self, name):
        size = storage.file_size(name)
        return size == IMAGE_KB * 1024

    def set_file(self, name):
        if not self.valid_file(name):
            print(f'Invalid RAM-Disk image file {name}')
            return
        self.config['ramdisk'] = name
        self.write_config()
        self.reopen_file()

    def get_file(self):
        return self.config['ramdisk']

    def handle_command(self):
        self.command = cpld.read_reg(cpld.REG_RAMDISK_CONTROL)
        self.read_pointer = 0
        self.read_count = 0
        if self.command == Command.RESET:
            print("RAM-Disk RESET")
            self.command = None
            status = 1                            # 1 == 120K ram Disk
            if FAILSAFE_SWITCH.value() == 0:
                status |= 2                       # 2 == Write Protect
            cpld.write_reg(cpld.REG_RAMDISK_DATA, status)
            self.reopen_file()
        elif self.command == Command.READ:
            self.read_count = 2
        elif self.command == Command.READB:
            self.read_count = 3
        elif self.command == Command.WRITE:
            self.read_count = 130
        elif self.command == Command.WRITEB:
            self.read_count = 4
        elif self.command == Command.CKSUM:
            print("RAM-Disk CKSUM")
            try:
                storage.umount_sdcard()
                storage.mount_sdcard()
                self.reopen_file()
            except Exception as e:
                print(f'Error {e} remounting SD-Card')
            self.command = None
            cpld.write_reg(cpld.REG_RAMDISK_DATA, self.cksum)
        else:
            self.command = None

    def get_sector_offset(self):
        return self.px8_buffer[0] * 8192 + self.px8_buffer[1] * 128

    def get_byte_offset(self):
        return (self.px8_buffer[0] - 1) * 60544 + self.px8_buffer[1] * 256 + self.px8_buffer[2]

    def execute_current_command(self):
        if self.command == Command.READ:
            offset = self.get_sector_offset()
            print("RAM-Disk READ", offset)
            try:
                self.file.seek(offset)
                self.file.readinto(self.file_buffer)
                cpld.write_reg(cpld.REG_RAMDISK_DATA, 0)                 # status OK
            except Exception as e:
                print(f'Error {e} while reading')
                cpld.write_reg(cpld.REG_RAMDISK_DATA, 255)                 # status failed
            for byte in self.file_buffer:
                while True:
                    if not cpld.read_reg(cpld.REG_IRQ) & cpld.IRQ_RAMDISK_IBF:
                        break
                cpld.write_reg(cpld.REG_RAMDISK_DATA, byte)
        elif self.command == Command.READB:
            offset = self.get_byte_offset()
            print("RAM-Disk READB", offset)
            try:
                self.file.seek(offset)
                byte = self.file.read(1)
                cpld.write_reg(cpld.REG_RAMDISK_DATA, 0)                 # status OK
            except Exception as e:
                print(f'Error {e} while writing')
                cpld.write_reg(cpld.REG_RAMDISK_DATA, 255)               # status failed
            while True:
                if not cpld.read_reg(cpld.REG_IRQ) & cpld.IRQ_RAMDISK_IBF:
                    break
            cpld.write_reg(cpld.REG_RAMDISK_DATA, byte)
        elif self.command == Command.WRITE:
            if self.read_only:
                cpld.write_reg(cpld.REG_RAMDISK_DATA, 0x04)              # status write protected
                return
            offset = self.get_sector_offset()
            print("RAM-Disk WRITE", offset)
            self.file.seek(offset)
            self.file.write(self.px8_buffer[2:130])
            cpld.write_reg(cpld.REG_RAMDISK_DATA, 0)                     # status OK
            self.pending_writes = True
        elif self.command == Command.WRITEB:
            if self.read_only:
                cpld.write_reg(cpld.REG_RAMDISK_DATA, 0x04)              # status write protected
                return
            offset = self.get_byte_offset()
            print("RAM-Disk WRITEB", offset)
            self.file.seek(offset)
            self.file.write(self.px8_buffer[3])
            cpld.write_reg(cpld.REG_RAMDISK_DATA, 0)                     # status OK
            self.pending_writes = True
        else:
            print("don't know how to execute command", self.command)

    def handle_data(self):
        byte = cpld.read_reg(cpld.REG_RAMDISK_DATA)
        if self.read_count == 0:
            print("unexpected data from host:", byte)
            return
        self.px8_buffer[self.read_pointer] = byte
        self.read_pointer = self.read_pointer + 1
        self.read_count = self.read_count - 1
        if self.read_count == 0:
            self.execute_current_command()

    def flush_pending_writes(self):
        if self.pending_writes:
            print("RAM-Disk flushing writes")
            self.pending_writes = False

    def maybe_flush_pending_writes(self):
        now = time.ticks_ms()
        if now < self.last_flush or now > self.last_flush + FLUSH_INTERVAL:
            self.flush_pending_writes()
            self.last_flush = now

