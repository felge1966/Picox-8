from machine import Pin
import rp2
from rp2 import PIO

# Pin assignments
PIN_DATA = [Pin(i, Pin.IN) for i in range(2, 10)]
PIN_CLK = Pin(10, Pin.IN)
PIN_DIR = Pin(11, Pin.OUT, Pin.PULL_DOWN)
PIN_STB = Pin(12, Pin.OUT, Pin.PULL_DOWN)
PIN_ADDR = [Pin(i, Pin.OUT) for i in range(13, 16)]

ADDR_BITS_POS = 11 # relative to pin 2

# Bit mask for 32 bit FIFO data.  The upper half defines the direction
# bits, the lower half defines the data bits.  DIR, STB and the ADDR
# bits are always configured as outputs.  When writing, the data bits
# are also configured as outputs, and the DIR bit is set to one.
STB_MASK   = 0b00111110_00000000_00000100_00000000
WRITE_MASK = 0b00000000_11111111_00000010_00000000

# IRQ pins
PIN_IRQ_TONE_DIALER = Pin(16, Pin.IN, Pin.PULL_UP)
PIN_IRQ_MODEM_STATUS = Pin(17, Pin.IN, Pin.PULL_UP)
PIN_IRQ_RAMDISK_COMMAND = Pin(18, Pin.IN, Pin.PULL_UP)
PIN_IRQ_RAMDISK_OBF = Pin(19, Pin.IN, Pin.PULL_UP)

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
    out(pindirs, 16)

    # Wait for falling edge on CLK
    wait(0, pin, CLK_PIN)

    # Read 8 bits from input pins to ISR
    in_(pins, 8)
    # Push ISR content to FIFO
    push()

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
    sm.put(data | (address << ADDR_BITS_POS) | STB_MASK | WRITE_MASK)
    sm.get()

def read_data(address):
    sm.put((address << ADDR_BITS_POS) | STB_MASK)
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

# Example usage
def main():
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


if __name__ == "__main__":
    main()
