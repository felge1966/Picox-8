from modem import Modem
from ramdisk import RamDisk
import cpld
import wifi

ramdisk = RamDisk('ramdisk.dat')
modem = Modem()

def main_loop():
    wifi.connect()
    iterations = 0
    while True:
        if cpld.read_irq_tone_dialer() == 1:
            modem.handle_tone_dialer()
        if cpld.read_irq_modem_control() == 1:
            modem.handle_control()
        if cpld.read_irq_ramdisk_command() == 1:
            ramdisk.handle_command()
        if cpld.read_irq_ramdisk_obf() == 1:
            ramdisk.handle_data()
        iterations = iterations + 1
        if iterations == 1000:
            iterations = 0
            ramdisk.maybe_flush_pending_writes()

        modem.poll()


def test_read_write():
    # Read IRQ statuses
    print("IRQ Tone Dialer:", cpld.read_irq_tone_dialer())
    print("IRQ Modem Status:", cpld.read_irq_modem_control())
    print("IRQ Ramdisk Command:", cpld.read_irq_ramdisk_command())
    print("IRQ Ramdisk OBF:", cpld.read_irq_ramdisk_obf())

    # Example write operation
    print("writing data")
    cpld.write_data(0b000, 0xFF)
    cpld.write_data(0b001, 0x55)
    cpld.write_data(0b001, 0xAA)

    # Example read operation
    data = cpld.read_data(0b000)  # Read from register 0
    print("Data read:", data)
