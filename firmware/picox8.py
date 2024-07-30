from modem import Modem
from ramdisk import RamDisk
import cpld
import wifi
import storage
import config

storage.mount_sdcard()
ramdisk = RamDisk()
modem = Modem()

def main_loop():
    wifi.connect()
    iterations = 0
    modem_enabled = False
    while True:
        byte = cpld.read_reg(cpld.REG_IRQ)
        if modem_enabled:
            if byte & cpld.IRQ_TONE_DIALER:
                modem.handle_tone_dialer()
            if byte & cpld.IRQ_MODEM_CONTROL:
                modem.handle_control()
            if byte & cpld.IRQ_BAUDRATE:
                modem.handle_baudrate()
        if byte & cpld.IRQ_CTLR2:
            ctlr2 = cpld.read_reg(cpld.REG_CTLR2)
            new_modem_enabled = (ctlr2 & 0x20) == 0
            if new_modem_enabled != modem_enabled:
                modem_enabled = new_modem_enabled
                if modem_enabled:
                    print('Enable modem')
                    modem.reset()
                else:
                    print('Disable modem')
        if byte & cpld.IRQ_RAMDISK_COMMAND:
            ramdisk.handle_command()
        if byte & cpld.IRQ_RAMDISK_OBF:
            ramdisk.handle_data()
        iterations = iterations + 1
        if iterations == 1000:
            iterations = 0
            ramdisk.maybe_flush_pending_writes()

        modem.poll()
