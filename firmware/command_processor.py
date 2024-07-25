import re
import config

PROMPT = "picox8> "

CLEAN_RE = re.compile(r'^\s*(.*?)\s*$')
SPLIT_RE = re.compile(r'\s+')

class CommandProcessor:
  def __init__(self, terminal):
    self.terminal = terminal
    self.reset()


  def reset(self):
    self.line_buffer = ''
    self.terminal.write(PROMPT)


  def say(self, s):
    self.terminal.write(s)
    self.terminal.write("\r\n")


  def cmd_help(self, args):
    self.say("""\
PicoX-8 configuration command help\r
\r
set wifi <ssid> <password>            Set WiFi SSID and password\r
set phonebook <number> <host> <port>  Set phonebook entry\r
show phonebook                        Show phonebook\r
show wifi                             Show WiFi status\r
show images                           Show RAM-Disk images\r
mount <image>                         Mount RAM-Disk image\r
download <image>                      Download RAM-Disk image from server\r
upload <image>                        Upload RAM-Disk image to server""")


  def cmd_set_wifi(self, args):
    if len(args) != 2:
      self.say(f'Incorrect arguments to "set wifi", need SSID and key')
      return
    config.set('wifi', args)


  def cmd_set(self, args):
    if len(args) == 0:
      self.say(f'Missing argument to "set", try "help"')
      return
    command, *args = args
    try:
      method = getattr(self, 'cmd_set_' + command)
      method(args)
    except AttributeError:
      self.say(f'Unknown command "set {command}", try "help"')


  def execute_command(self, command, args):
    try:
      method = getattr(self, 'cmd_' + command)
      method(args)
    except AttributeError:
      self.say(f'Unknown command: "{command}" try "help"')


  def handle_user_char(self, c):
    if isinstance(c, int):
      c = chr(c)
    if ord(c) >= 32 and ord(c) < 127:
      self.terminal.write(c)
      self.line_buffer += c
    elif c == '\b' or c == '\x7f':                          # BS and DEL
      self.terminal.write('\b \b')
      self.line_buffer = self.line_buffer[:-1]
    elif c == '\x15':                                       # Ctrl-U
      count = len(self.line_buffer)
      self.terminal.write('\b' * count)
      self.terminal.write(' ' * count)
      self.terminal.write('\b' * count)
      self.line_buffer = ''
    elif c == '\x0d':                                       # CR
      self.terminal.write('\r\n')
      input = re.sub(CLEAN_RE, r'\1', self.line_buffer)
      if input != '':
        command, *args = SPLIT_RE.split(input)
        self.execute_command(command, args)
      self.reset()


  def userinput(self, data):
    for c in data:
      self.handle_user_char(c)


if __name__ == '__main__':
  import tty
  import termios
  import sys
  save_attr = termios.tcgetattr(0)
  tty.setraw(0)
  cp = CommandProcessor(sys.stdout)
  sys.stdout.flush()
  try:
    while True:
      c = sys.stdin.read(1)
      if c == '\x00':
        break
      cp.userinput(c)
      sys.stdout.flush()
  finally:
    termios.tcsetattr(0, termios.TCSANOW, save_attr)
