import machine
import cpld
import rp2
from machine import Pin
from command_processor import CommandProcessor

TICKS_PER_SECOND = 100

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


class Enum():
  @classmethod
  def _create_name_mapping(cls):
    return {value: name for name, value in cls.__dict__.items() if isinstance(value, int)}

  @classmethod
  def get_name(cls, value):
      name_mapping = cls._create_name_mapping()
      return name_mapping.get(value, "UNKNOWN")

class Control(Enum):
  OHC = 0x01
  HSC = 0x02
  MON = 0x04
  TXC = 0x08
  ANS = 0x10
  TEST = 0x20
  PWR = 0x40
  CCT = 0x80

  @classmethod
  def get_names(cls, value):
    result = []
    for mask, name in cls._create_name_mapping().items():
      if value & mask:
        result.append(name)
    return result


class Status(Enum):
    RNG = 1
    CD = 4


class Event(Enum):
    CONTROL_OHC = 0
    CONTROL_MON = 1
    CONTROL_TXC = 2
    CONTROL_PWR = 3
    CONTROL_CCT = 4
    DTMF = 5
    TICK = 6
    UART_RX = 7


class State(Enum):
    IDLE = 0
    OFF_HOOK = 1
    DIALING = 2
    RINGING = 3
    ANSWERED = 4
    HANDSHAKE = 5
    CONNECTED = 6
    COMMAND_MODE = 7


class Modem:
    def __init__(self):
        self.uart = machine.UART(0, baudrate=4800, tx=machine.Pin(0), rx=machine.Pin(1))
        self.reset()

    def reset(self):
        self.status = Status.CD | Status.RNG
        cpld.write_data(cpld.REG_MODEM_STATUS, self.status)
        self.state = State.IDLE
        self.answer_mode = False
        self.old_modem_control = 0
        self.number_buffer = ''

    def set_state(self, state):
        print("Modem", State.get_name(self.state), "->", State.get_name(state))
        self.state = state

    def handle_event(self, event, arg):
        if self.state == State.IDLE:
            if event == Event.CONTROL_OHC and arg:
                set_freq(tone_generator1, 425)
                self.set_state(State.OFF_HOOK)
                self.number_buffer = ''
        elif self.state == State.OFF_HOOK:
            if event == Event.DTMF:
                self.number_buffer += arg
                if self.number_buffer == '***':
                    self.carrier_detected(True)
                    self.command_processor = CommandProcessor(self.uart)
                    self.set_state(State.COMMAND_MODE)
            if event == Event.TICK:
                self.tick_count += 1
                if self.tick_count == TICKS_PER_SECOND:
                    self.set_state(State.DIALING)
        elif self.state == State.DIALING:
            pass
        elif self.state == State.RINGING:
            pass
        elif self.state == State.ANSWERED:
            pass
        elif self.state == State.HANDSHAKE:
            if byte & Control.TXC:
                set_freq(tone_generator1, 1650 if byte & self.answer_mode else 980)
        elif self.state == State.CONNECTED:
            pass
        elif self.state == State.COMMAND_MODE:
            if event == Event.UART_RX:
                self.command_processor.userinput(arg)


    def handle_control(self):
        byte = cpld.read_data(cpld.REG_MODEM_CONTROL)
        if byte == 0:
            print("Reset modem")
            self.reset()
            return
        print("Modem Control:", Control.get_names(byte))
        self.answer_mode = byte & Control.ANS
        if (byte ^ self.old_modem_control) & Control.OHC:
            self.handle_event(Event.CONTROL_OHC, byte & Control.OHC)
        if (byte ^ self.old_modem_control) & Control.MON:
            self.handle_event(Event.CONTROL_MON, byte & Control.MON)
        if (byte ^ self.old_modem_control) & Control.TXC:
            self.handle_event(Event.CONTROL_TXC, byte & Control.TXC)
        if (byte ^ self.old_modem_control) & Control.PWR:
            self.handle_event(Event.CONTROL_PWR, byte & Control.PWR)
        if (byte ^ self.old_modem_control) & Control.CCT:
            self.handle_event(Event.CONTROL_CCT, byte & Control.CCT)

    DTMF_LOW = [ 697, 770, 852, 941 ]
    DTMF_HIGH = [ 1209, 1336, 1477, 1633 ]
    DTMF_FREQ_MAP = {
        0: '1',
        1: '2',
        2: '3',
        4: '4',
        5: '5',
        6: '6',
        8: '7',
        9: '8',
        10: '9',
        12: '*',
        13: '0'
    }

    def carrier_detected(self, on):
        if on:
            self.status = self.status & ~Status.CD
        else:
            self.status = self.status | Status.CD
        cpld.write_data(cpld.REG_MODEM_STATUS, self.status)

    def ringing(self, on):
        if on:
            self.status = self.status & ~Status.RNG
        else:
            self.status = self.status | Status.RNG
        cpld.write_data(cpld.REG_MODEM_STATUS, self.status)

    def handle_tone_dialer(self):
        byte = cpld.read_data(cpld.REG_TONE_DIALER)
        if byte & 0x10:
            high = byte & 0x03
            low = (byte & 0x0c) >> 2
            print("DTMF tones:", low, Modem.DTMF_LOW[low], high, Modem.DTMF_HIGH[high])
            set_freq(tone_generator1, Modem.DTMF_LOW[low])
            set_freq(tone_generator2, Modem.DTMF_HIGH[high])
            self.handle_event(Event.DTMF, Modem.DTMF_FREQ_MAP[byte & 0x0f])
        else:
            print("DTMF off")
            set_freq(tone_generator1, 0)
            set_freq(tone_generator2, 0)

    def poll(self):
        if self.uart.any() > 0:
            self.handle_event(Event.UART_RX, self.uart.read())

