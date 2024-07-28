import re
import config
import gc
from abbrev import abbreviate_methods
from collections import deque
import wifi
import ramdisk
import storage
import uos

BANNER = '\r\nPicoX-8 configuration interface.  Type "help" for help\r\n\n'
PROMPT = "picox-8> "

CLEAN_RE = re.compile(r'^\s*(.*?)\s*$')
SPLIT_RE = re.compile(r'\s+')
NUMBER_RE = re.compile(r'^\d+$')

MAXHISTORY = 30

class CommandProcessor:
  def __init__(self, terminal):
    self.terminal = terminal
    self.cmd_abbrevs = abbreviate_methods(self, 'cmd__')
    self.set_abbrevs = abbreviate_methods(self, 'cmd_set_')
    self.show_abbrevs = abbreviate_methods(self, 'cmd_show_')
    self.history = deque([], MAXHISTORY)
    self.history_pointer = -1
    self.terminal.write(BANNER)
    self.reset()
    self.done = False


  def reset(self):
    self.line_buffer = ''
    self.terminal.write(PROMPT)


  def say(self, s):
    self.terminal.write(s)
    self.terminal.write("\r\n")


  def cmd__help(self, args):
    self.say("""\
PicoX-8 configuration command help\r
\r
show status                            Show system status\r

set wifi <ssid> <password>             Set WiFi SSID and password\r
set phonebook <number> <host>[:<port>] Set phonebook entry\r
show phonebook                         Show phonebook\r

ls                                     List files on SD-Card\r
set ramdisk <filename>                 Set RAM-Disk file\r

quit                                   Exit configuration""")


  def cmd_show_status(self, args):
    gc.collect()
    self.say(f'Free memory: {gc.mem_free()}')
    self.say(f'WiFi status: {wifi.status()}')
    mounted = 'mounted' if storage.sdcard_mounted() else 'not mounted'
    self.say(f'SD-Card    : {mounted}')


  def cmd_set_wifi(self, args):
    if len(args) != 2:
      self.say(f'Incorrect arguments to "set wifi", need SSID and key')
      return
    config.set('wifi', args)
    wifi.connect()


  def cmd_set_phonebook(self, args):
    if len(args) != 2:
      self.say(f'Incorrect arguments to "set phonebook", try "help"')
      return
    number, host_port = args
    if not NUMBER_RE.match(number):
      self.say('Number must be numeric')
      return
    if ':' in host_port:
      host, port = host_port.split(':')
    else:
      host = host_port
      port = '23'
    if not NUMBER_RE.match(port):
      self.say('Port must be numeric')
      return
    port = int(port)
    # fixme check number and port for digits only
    phonebook = config.get('phonebook', {})
    phonebook[number] = [host, port]

    config.set('phonebook', phonebook)
    config.save()
    self.say(f'Phonebook entry for number {number} saved')


  def cmd_show_phonebook(self, args):
    if len(args) != 0:
      self.say(f'Extra argument(s) to "show phonebook", try "help"')
      return
    phonebook = config.get('phonebook', None)
    if phonebook == None:
      self.say('No phonebook entries defined')
    else:
      self.say(f'Number     Host')
      self.say(f'----------------------------------------')
      for number in sorted(phonebook.keys()):
        entry = phonebook[number]
        self.say(f'{number:<10} {entry[0]}:{entry[1]}')


  def cmd__ls(self, args):
    if len(args) != 0:
      self.say(f'Extra argument(s) to "ls", try "help"')
      return

    storage.umount_sdcard()
    if not storage.mount_sdcard():
      self.say('No SD-Card found')
      return
    files = uos.listdir(storage.SDCARD_DIR)
    self.say(f'Name                 Size')
    self.say(f'-------------------------------')
    for name in sorted(files):
      size = uos.stat(f'{storage.SDCARD_DIR}/{name}')[6]
      self.say(f'{name:<20} {size}')


  def cmd_set_ramdisk(self, args):
    if len(args) != 1:
      self.say('Missing filename argument to "set ramdisk", try "help"')
      return
    path = f'{storage.SDCARD_DIR}/{args[0]}'
    try:
      size = uos.stat(path)[6]
    except OSError as e:
      if e.errno == errno.ENOENT:
        size = None
      else:
        self.say(f'stat() error on {path}: {e}')
        return
    if size == None:
      self.say(f'File {path} not found')
      return
    if size != ramdisk.IMAGE_SIZE:
      self.say(f'File {path} has an unexpected size, need {ramdisk.IMAGE_SIZE} bytes in image')
      return
    config.set('ramdisk', path)


  def cmd__set(self, args):
    if len(args) == 0:
      self.say(f'Missing argument to "set", try "help"')
      return
    command, *args = args
    if command in self.set_abbrevs:
      method = self.set_abbrevs[command]
      method(args)
    else:
      self.say(f'Unknown command "set {command}", try "help"')


  def cmd__show(self, args):
    if len(args) == 0:
      self.say(f'Missing argument to "show", try "help"')
      return
    command, *args = args
    if command in self.show_abbrevs:
      method = self.show_abbrevs[command]
      method(args)
    else:
      self.say(f'Unknown command "show {command}", try "help"')


  def cmd__quit(self, args):
    if len(args) != 0:
      self.say(f'Unexpected argument(s) to "quit", try "help"')
      return
    self.say(f'Exiting PicoX-8 configuration interface')
    self.done = True

  def execute_command(self, command, args):
    if command in self.cmd_abbrevs:
      method = self.cmd_abbrevs[command]
      method(args)
    else:
      self.say(f'Unknown command "{command}", try "help"')


  def erase_input(self):
    count = len(self.line_buffer)
    self.terminal.write('\b' * count)
    self.terminal.write(' ' * count)
    self.terminal.write('\b' * count)
    self.line_buffer = ''


  def handle_user_char(self, c):
    if isinstance(c, int):
      c = chr(c)
    if ord(c) >= 32 and ord(c) < 127:
      self.terminal.write(c)
      self.line_buffer += c
    elif c == '\b' or c == '\x7f':                          # BS and DEL delete char
      if self.line_buffer != '':
        self.terminal.write('\b \b')
        self.line_buffer = self.line_buffer[:-1]
    elif c == '\x15':                                       # Ctrl-U erase input
      self.erase_input()
    elif c == '\x10':                                       # Ctrl-P previous history entry
      if len(self.history) > self.history_pointer+1:
        if self.history_pointer == -1:
          self.save_input = self.line_buffer
        self.history_pointer += 1
        self.erase_input()
        self.line_buffer = self.history[self.history_pointer]
        self.terminal.write(self.line_buffer)
      else:
        self.terminal.write('\x07')                         # Beep
    elif c == '\x0e':                                       # Ctrl-N next history entry
      if self.history_pointer >= 0:
        self.history_pointer -= 1
        self.erase_input()
        if self.history_pointer == -1:
          self.line_buffer = self.save_input
        else:
          self.line_buffer = self.history[self.history_pointer]
        self.terminal.write(self.line_buffer)
    elif c == '\x0d':                                       # CR
      self.terminal.write('\r\n')
      input = re.sub(CLEAN_RE, r'\1', self.line_buffer)
      if input != '':
        if not len(self.history) or input != self.history[0]:
          self.history.appendleft(input)
        self.history_pointer = -1
        command, *args = SPLIT_RE.split(input)
        self.execute_command(command, args)
      if not self.done:
        self.reset()


  def userinput(self, data):
    for c in data:
      self.handle_user_char(c)
    return self.done


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
