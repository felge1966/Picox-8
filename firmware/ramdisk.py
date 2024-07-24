import cpld
import time

FLUSH_INTERVAL = 15000                                  # how often to flush ramdisk to flash

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
    def __init__(self, filename):
        self.command = None
        self.read_count = None
        self.read_pointer = None
        self.px8_buffer = bytearray(131)                         # maximum number of bytes that are exchanged with host in one command
        self.file_buffer = bytearray(128)
        self.cksum = 0                                           # formatted
        self.filename = filename
        self.pending_writes = False
        self.last_flush = time.ticks_ms()
        self.file = None
        self.reopen_file()

    def reopen_file(self):
        if self.file != None:
            self.file.close()
        self.file = open(self.filename, 'r+b')

    def handle_command(self):
        self.command = cpld.read_data(cpld.REG_RAMDISK_CONTROL)
        self.read_pointer = 0
        self.read_count = 0
        if self.command == Command.RESET:
            print("RAM-Disk RESET")
            self.command = None
            cpld.write_data(cpld.REG_RAMDISK_DATA, 1)                  # 1 == 120K ram Disk
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
            self.command = None
            cpld.write_data(cpld.REG_RAMDISK_DATA, self.cksum)
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
            self.file.seek(offset)
            cpld.write_data(cpld.REG_RAMDISK_DATA, 0)                 # status OK
            self.file.readinto(self.file_buffer)
            for byte in self.file_buffer:
                while cpld.read_irq_ramdisk_ibf() == 1:
                    pass
                cpld.write_data(cpld.REG_RAMDISK_DATA, byte)
        elif self.command == Command.READB:
            offset = self.get_byte_offset()
            print("RAM-Disk READB", offset)
            self.file.seek(offset)
            byte = self.file.read(1)
            cpld.write_data(cpld.REG_RAMDISK_DATA, 0)                 # status OK
            while cpld.read_irq_ramdisk_ibf() == 1:
                pass
            cpld.write_data(cpld.REG_RAMDISK_DATA, byte)
        elif self.command == Command.WRITE:
            offset = self.get_sector_offset()
            print("RAM-Disk WRITE", offset)
            self.file.seek(offset)
            self.file.write(self.px8_buffer[2:130])
            cpld.write_data(cpld.REG_RAMDISK_DATA, 0)                 # status OK
            self.pending_writes = True
        elif self.command == Command.WRITEB:
            offset = self.get_byte_offset()
            print("RAM-Disk WRITEB", offset)
            self.file.seek(offset)
            self.file.write(self.px8_buffer[3])
            cpld.write_data(cpld.REG_RAMDISK_DATA, 0)                 # status OK
            self.pending_writes = True
        else:
            print("don't know how to execute command", self.command)

    def handle_data(self):
        byte = cpld.read_data(cpld.REG_RAMDISK_DATA)
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
            self.reopen_file()
            self.pending_writes = False

    def maybe_flush_pending_writes(self):
        now = time.ticks_ms()
        if now < self.last_flush or now > self.last_flush + FLUSH_INTERVAL:
            self.flush_pending_writes()
            self.last_flush = now
