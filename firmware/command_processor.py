class CommandProcessor:
  def __init__(self, terminal):
    self.terminal = terminal
    self.line_buffer = ''

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
      print("execute", self.line_buffer, "\r")
      self.line_buffer = ''

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
  try:
    while True:
      c = sys.stdin.read(1)
      if c == '\x00':
        break
      cp.userinput(c)
      sys.stdout.flush()
  finally:
    termios.tcsetattr(0, termios.TCSANOW, save_attr)
