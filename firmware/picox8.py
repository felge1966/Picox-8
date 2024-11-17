from machine import UART, Pin
from modem import Modem
from telnet import TelnetServer
from ramdisk import RamDisk
import cpld
import wifi
import storage
import config

DEFAULT_BAUDRATE = 4800

storage.mount_sdcard()
uart = UART(0, baudrate=DEFAULT_BAUDRATE, tx=Pin(0), rx=Pin(1))
ramdisk = RamDisk()
modem = Modem(uart)
telnet_server = TelnetServer(uart)

def main_loop():
    wifi.connect()
    ramdisk_iterations = 0
    modem_disable_delay = 0
    modem_enabled = False
    while True:
        byte = cpld.read_reg(cpld.REG_IRQ)
        if modem_enabled:
            if byte & cpld.IRQ_TONE_DIALER:
                modem.handle_tone_dialer()
            if byte & cpld.IRQ_MODEM_CONTROL:
                modem.handle_control()
            if byte & cpld.IRQ_BAUDRATE:
                handle_baudrate()
        if byte & cpld.IRQ_MISC_CONTROL:
            # fixme: handle all control bits (ser handshake, buttons)
            misc_control = cpld.read_reg(cpld.REG_MISC_CONTROL)
            # new_modem_enabled = (misc_control & 0x01) == 0
            new_modem_enabled = (misc_control & 0x20) == 0
            if new_modem_enabled != modem_enabled:
                modem_enabled = new_modem_enabled
                if modem_enabled:
                    print('Enable modem')
                    modem_disable_delay = 0
                else:
                    print('Disable modem')
                    modem_disable_delay = 1000
        if not modem_enabled and modem_disable_delay > 0:
            modem_disable_delay -= 1
            if modem_disable_delay == 0:
                print('Resetting modem')
                modem.reset()
        if byte & cpld.IRQ_RAMDISK_COMMAND:
            ramdisk.handle_command()
        if byte & cpld.IRQ_RAMDISK_OBF:
            ramdisk.handle_data()
        ramdisk_iterations += 1
        if ramdisk_iterations == 1000:
            ramdisk_iterations = 0
            ramdisk.maybe_flush_pending_writes()

        modem.poll()
        telnet_server.poll()

old_baud_control = 0

REG_TO_BAUD = {
    0: 110,
    32: 300,
    48: 600,
    64: 1200,
    80: 2400,
    96: 4800,
    112: 9600,
    160: 19200,
}

def handle_baudrate():
    global old_baud_control
    baud_control = cpld.read_reg(cpld.REG_BAUDRATE) & 0xf0
    if baud_control == old_baud_control:
        return
    old_baud_control = baud_control
    if not baud_control in REG_TO_BAUD:
        print(f'Unrecognized UART baud rate register value {baud_control}')
    baud = REG_TO_BAUD[baud_control]
    print(f'UART baud rate: {baud}')
    uart.init(baud, bits=8, parity=None, stop=1)


