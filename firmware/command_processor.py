import re

PROMPT = "picox8> "

class CommandProcessor:
  def __init__(self, terminal):
    self.terminal = terminal
    self.reset()


  def reset(self):
    self.line_buffer = ''
    self.terminal.write(PROMPT)


  def cmd_help(self, args):
    self.terminal.write("""\
PicoX-8 configuration command help\r
\r
set wifi <ssid> <password>            Set WiFi SSID and password\r
set phonebook <number> <host> <port>  Set phonebook entry\r
show phonebook                        Show phonebook\r
show wifi                             Show WiFi status\r
show images                           Show RAM-Disk images\r
mount <image>                         Mount RAM-Disk image\r
download <image>                      Download RAM-Disk image from server\r
upload <image>                        Upload RAM-Disk image to server\r
""")


  def execute_command(self, command, args):
    try:
      method = getattr(self, 'cmd_' + command)
      method(args)
    except AttributeError:
      self.terminal.write("Unknown command: " + command + "\r\n")


  def handle_user_char(self, c):
    if c.isprintable():
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
      input = re.sub(r'^\s*(.*?)\s*$', r'\1', self.line_buffer)
      if input != '':
        command, *args = re.split(r'\s+', input)
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
