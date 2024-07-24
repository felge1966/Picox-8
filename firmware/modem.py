import machine
import cpld
import rp2
from machine import Pin

@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def tone_generator():
    pull()
    wrap_target()
    set(pins, 1)
    mov(x, osr)
    label("delay_high")
    jmp(x_dec, "delay_high")
    set(pins, 0)
    mov(x, osr)
    label("delay_low")
    jmp(x_dec, "delay_low")

tone_generator1 = rp2.StateMachine(4, tone_generator, freq=10_000_000, set_base=Pin(28))
tone_generator2 = rp2.StateMachine(5, tone_generator, freq=10_000_000, set_base=Pin(28))


def set_freq(sm, f):
    if f > 0:
        sm.active(0)
        delay = int(1/f/100e-9/2)-3
        sm.restart()
        sm.put(delay)
        sm.active(1)
    else:
        sm.restart()                                        # restart to set output to low if running


class Control:
  OHC = 0x01
  HSC = 0x02
  MON = 0x04
  TXC = 0x08
  ANS = 0x10
  TEST = 0x20
  PWR = 0x40
  CCT = 0x80

  @classmethod
  def _create_name_mapping(cls):
    return {name: value for name, value in cls.__dict__.items() if not name.startswith('_') and isinstance(value, int)}
            
  @classmethod
  def get_names(cls, value):
    result = []
    for name, mask in cls._create_name_mapping().items():
      if value & mask:
        result.append(name)
    return result

class Modem:
    def __init__(self):
        self.uart = machine.UART(0, baudrate=4800, tx=machine.Pin(0), rx=machine.Pin(1))

    def handle_control(self):
        print("Modem Control Register:", Control.get_names(cpld.read_data(cpld.REG_MODEM_CONTROL)))

    DTMF_LOW = [ 697, 770, 852, 941 ]
    DTMF_HIGH = [ 1209, 1336, 1477, 1633 ]

    def handle_tone_dialer(self):
        byte = cpld.read_data(cpld.REG_TONE_DIALER)
        if byte & 0x10:
            high = byte & 0x03
            low = (byte & 0x0c) >> 2
            print("DTMF tones:", low, Modem.DTMF_LOW[low], high, Modem.DTMF_HIGH[high])
            set_freq(tone_generator1, Modem.DTMF_LOW[low])
            set_freq(tone_generator2, Modem.DTMF_HIGH[high])

        else:
            print("DTMF off")
            set_freq(tone_generator1, 0)
            set_freq(tone_generator2, 0)

    def poll_rx(self):
        if self.uart.any() > 0:
            bytes = self.uart.read()
            print('read from uart: ', bytes)
            self.uart.write(bytes)

