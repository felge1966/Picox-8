import time
from machine import Pin, UART
import rp2
from rp2 import PIO

# Pin assignments
PIN_DATA = [Pin(i, Pin.IN) for i in range(2, 10)]
PIN_CLK = Pin(10, Pin.IN)
PIN_DIR = Pin(11, Pin.OUT, Pin.PULL_DOWN)
PIN_STB = Pin(12, Pin.OUT, Pin.PULL_DOWN)
PIN_ADDR = [Pin(i, Pin.OUT) for i in range(13, 16)]

ADDR_BITS_POS = 11 # relative to pin 2

# Bit mask for 32 bit command word that is sent from MicroPython to
# the PIO state machine.  The upper half of this command word defines
# the direction bits, the lower half defines the data bits.  DIR, STB
# and the ADDR bits are always configured as outputs.  When writing,
# the data bits are also configured as outputs, and the DIR bit is set
# to one.  The MSB is an additional read/write indicator that needs to
# be set to 1 for read operations.  It is used by the PIO state
# machine to skip reading from the data lines into the FIFO when
# writing.
STB_MASK   = 0b00111110_00000000_00000100_00000000
READ_MASK  = 0b10000000_00000000_00000000_00000000
WRITE_MASK = 0b00000000_11111111_00000010_00000000

# IRQ pins
PIN_IRQ_TONE_DIALER = Pin(16, Pin.IN, Pin.PULL_UP)
PIN_IRQ_MODEM_STATUS = Pin(17, Pin.IN, Pin.PULL_UP)
PIN_IRQ_RAMDISK_COMMAND = Pin(18, Pin.IN, Pin.PULL_UP)
PIN_IRQ_RAMDISK_OBF = Pin(19, Pin.IN, Pin.PULL_UP)
PIN_IRQ_RAMDISK_IBF = Pin(20, Pin.IN, Pin.PULL_UP)

# Register numbers
REG_TONE_DIALER = 0
REG_MODEM_CONTROL = 1
REG_MODEM_STATUS = 2
REG_RAMDISK_DATA = 3
REG_RAMDISK_CONTROL = 4

# Define the PIO program
@rp2.asm_pio(out_shiftdir=PIO.SHIFT_RIGHT,
             out_init=(PIO.IN_LOW,)*8 + (PIO.IN_LOW, PIO.OUT_LOW, PIO.OUT_LOW) + (PIO.OUT_LOW,)*3,
             autopush=False, autopull=False)
def parallel_interface():
    CLK_PIN = 8 # (GP10)
    # Pull 32-bit value from FIFO
    pull()

    # Wait for rising edge on CLK
    wait(0, pin, CLK_PIN)
    wait(1, pin, CLK_PIN)

    # Output data bits to pins (DATA, CLK, DIR, STB, ADDR + extra)
    out(pins, 16)
    # Output pindirs bits to set pin directions
    out(pindirs, 15)

    # Wait for falling edge on CLK
    wait(0, pin, CLK_PIN)

    # Skip reading for write operation
    mov(x, osr)
    jmp(not_x, "finish_cycle")

    # Read 8 bits from input pins to ISR
    in_(pins, 8)
    # Push ISR content to FIFO
    push()

    label("finish_cycle")
    # Wait for next rising CLK edge to complete cycle
    wait(1, pin, CLK_PIN)

    # Set all outputs to zero
    mov(osr, null)
    out(pins, 16)
    # Set all pindirs to zero (input)
    out(pindirs, 16)


# Create and configure the state machine
sm = rp2.StateMachine(0, parallel_interface, freq=24_000_000, in_base=Pin(2), out_base=Pin(2))
sm.active(1)


# Initialize the state machine
def write_data(address, data):
    sm.put((address << ADDR_BITS_POS) | STB_MASK | WRITE_MASK | data)


def read_data(address):
    sm.put((address << ADDR_BITS_POS) | STB_MASK | READ_MASK)
    return sm.get()


# Functions to read IRQ pin statuses
def read_irq_tone_dialer():
    return PIN_IRQ_TONE_DIALER.value()


def read_irq_modem_status():
    return PIN_IRQ_MODEM_STATUS.value()


def read_irq_ramdisk_command():
    return PIN_IRQ_RAMDISK_COMMAND.value()


def read_irq_ramdisk_obf():
    return PIN_IRQ_RAMDISK_OBF.value()


def read_irq_ramdisk_ibf():
    return PIN_IRQ_RAMDISK_IBF.value()


class RamDisk:

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
            return {value: name for name, value in cls.__dict__.items() if not name.startswith('_')}

        @classmethod
        def get_name(cls, value):
            name_mapping = cls._create_name_mapping()
            return name_mapping.get(value, "UNKNOWN_COMMAND")


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
        Command = RamDisk.Command
        self.command = read_data(REG_RAMDISK_CONTROL)
        self.read_pointer = 0
        self.read_count = 0
        if self.command == Command.RESET:
            print("RAM-Disk RESET")
            self.command = None
            write_data(REG_RAMDISK_DATA, 1)                  # 1 == 120K ram Disk
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
            write_data(REG_RAMDISK_DATA, self.cksum)
        else:
            self.command = None

    def get_sector_offset(self):
        return self.px8_buffer[0] * 8192 + self.px8_buffer[1] * 128

    def get_byte_offset(self):
        return (self.px8_buffer[0] - 1) * 60544 + self.px8_buffer[1] * 256 + self.px8_buffer[2]

    def execute_current_command(self):
        Command = RamDisk.Command
        if self.command == Command.READ:
            offset = self.get_sector_offset()
            print("RAM-Disk READ", offset)
            self.file.seek(offset)
            write_data(REG_RAMDISK_DATA, 0)                 # status OK
            self.file.readinto(self.file_buffer)
            for byte in self.file_buffer:
                while read_irq_ramdisk_ibf() == 1:
                    pass
                write_data(REG_RAMDISK_DATA, byte)
        elif self.command == Command.READB:
            offset = self.get_byte_offset()
            print("RAM-Disk READB", offset)
            self.file.seek(offset)
            byte = self.file.read(1)
            write_data(REG_RAMDISK_DATA, 0)                 # status OK
            while read_irq_ramdisk_ibf() == 1:
                pass
            write_data(REG_RAMDISK_DATA, byte)
        elif self.command == Command.WRITE:
            offset = self.get_sector_offset()
            print("RAM-Disk WRITE", offset)
            self.file.seek(offset)
            self.file.write(self.px8_buffer[2:130])
            write_data(REG_RAMDISK_DATA, 0)                 # status OK
            self.pending_writes = True
        elif self.command == Command.WRITEB:
            offset = self.get_byte_offset()
            print("RAM-Disk WRITEB", offset)
            self.file.seek(offset)
            self.file.write(self.px8_buffer[3])
            write_data(REG_RAMDISK_DATA, 0)                 # status OK
            self.pending_writes = True
        else:
            print("don't know how to execute command", self.command)

    def handle_data(self):
        byte = read_data(REG_RAMDISK_DATA)
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
        if now < self.last_flush or now > self.last_flush + RamDisk.FLUSH_INTERVAL:
            self.flush_pending_writes()



ramdisk = RamDisk('ramdisk.dat')
uart = UART(0, baudrate=4800, tx=Pin(0), rx=Pin(1))


def main_loop():
    iterations = 0
    while True:
        if read_irq_tone_dialer() == 1:
            print("Tone Dialer Register:", read_data(REG_TONE_DIALER))
        if read_irq_modem_status() == 1:
            print("Modem Status Register:", read_data(REG_MODEM_STATUS))
        if read_irq_ramdisk_command() == 1:
            ramdisk.handle_command()
        if read_irq_ramdisk_obf() == 1:
            ramdisk.handle_data()
        iterations = iterations + 1
        if iterations == 1000:
            iterations = 0
            ramdisk.maybe_flush_pending_writes()

#        if uart.any() > 0:
#            bytes = uart.read()
#            print('read from uart: ', bytes)
#            uart.write(bytes)


def test_read_write():
    # Read IRQ statuses
    print("IRQ Tone Dialer:", read_irq_tone_dialer())
    print("IRQ Modem Status:", read_irq_modem_status())
    print("IRQ Ramdisk Command:", read_irq_ramdisk_command())
    print("IRQ Ramdisk OBF:", read_irq_ramdisk_obf())

    # Example write operation
    print("writing data")
    write_data(0b000, 0xFF)
    write_data(0b001, 0x55)
    write_data(0b001, 0xAA)

    # Example read operation
    data = read_data(0b000)  # Read from register 0
    print("Data read:", data)
