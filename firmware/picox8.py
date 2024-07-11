from machine import Pin

# Pin assignments
PIN_DATA = [Pin(i, Pin.IN, Pin.PULL_UP) for i in range(2, 10)]
PIN_CLK = Pin(10, Pin.IN, Pin.PULL_UP)
PIN_DIR = Pin(11, Pin.OUT)
PIN_STB = Pin(12, Pin.OUT)
PIN_ADDR = [Pin(i, Pin.OUT) for i in range(13, 16)]

# IRQ pins
PIN_IRQ_TONE_DIALER = Pin(16, Pin.IN, Pin.PULL_UP)
PIN_IRQ_MODEM_STATUS = Pin(17, Pin.IN, Pin.PULL_UP)
PIN_IRQ_RAMDISK_COMMAND = Pin(18, Pin.IN, Pin.PULL_UP)
PIN_IRQ_RAMDISK_OBF = Pin(19, Pin.IN, Pin.PULL_UP)

def wait_for_rising_edge(pin):
    while pin.value() != 0:
        pass
    while pin.value() != 1:
        pass

def wait_for_falling_edge(pin):
    while pin.value() != 1:
        pass
    while pin.value() != 0:
        pass
  

def set_data_direction(direction):
    for pin in PIN_DATA:
        pin.init(direction)

def write_data(register, data):
    wait_for_rising_edge(PIN_CLK)

    set_data_direction(Pin.OUT)
    for i in range(3):
        PIN_ADDR[i].value((register >> i) & 1)
    PIN_DIR.value(1)
    for i in range(8):
        PIN_DATA[i].value((data >> i) & 1)
    PIN_STB.value(1)

    wait_for_rising_edge(PIN_CLK)
    PIN_STB.value(0)
    set_data_direction(Pin.IN)

def read_data(register):
    for i in range(3):
        PIN_ADDR[i].value((register >> i) & 1)
    PIN_DIR.value(0)
    wait_for_rising_edge(PIN_CLK)
    PIN_STB.value(1)

    wait_for_falling_edge(PIN_CLK)

    data = 0
    for i in range(8):
        data |= (PIN_DATA[i].value() << i)

    PIN_STB.value(0)

    return data

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
    write_data(0b000, 0xFF)  # Write 0xFF to register 0

    # Example read operation
    data = read_data(0b000)  # Read from register 0
    print("Data read:", data)


if __name__ == "__main__":
    main()
