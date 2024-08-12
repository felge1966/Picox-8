import usocket as socket
from enum import Enum

LISTEN_PORT = 23
MAX_CONNECTIONS = 1

# telnet option negotiation

# command codes
class Commands(Enum):
  IAC  = 255  # Interpret as Command
  DONT = 254
  DO   = 253
  WONT = 252
  WILL = 251

# Telnet options
class Options(Enum):
  BINARY = 0
  ECHO = 1
  RCP = 2
  SGA = 3
  NAMS = 4
  STATUS = 5
  TM = 6
  RCTE = 7
  NAOL = 8
  NAOP = 9
  NAOCRD = 10
  NAOHTS = 11
  NAOHTD = 12
  NAOFFD = 13
  NAOVTS = 14
  NAOVTD = 15
  NAOLFD = 16
  XASCII = 17
  LOGOUT = 18
  BM = 19
  DET = 20
  SUPDUP = 21
  SUPDUPOUTPUT = 22
  SENDLOC = 23
  TTYPE = 24
  EOR = 25
  TUID = 26
  OUTMARK = 27
  TTYLOC = 28
  _3270REGIME = 29
  X3PAD = 30
  NAWS = 31
  TSPEED = 32
  LFLOW = 33
  LINEMODE = 34
  XDISPLOC = 35
  OLD_ENVIRON = 36
  AUTHENTICATION = 37
  ENCRYPT = 38
  NEW_ENVIRON = 39

class TelnetServer:
  def __init__(self, uart):
    self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.server_socket.bind(('0.0.0.0', LISTEN_PORT))
    self.server_socket.listen(MAX_CONNECTIONS)
    self.server_socket.setblocking(False)
    self.client_socket = None
    self.uart = uart

  def poll(self):
    if self.client_socket:
      if self.uart.any() > 0:
        data = self.uart.read()
        self.client_socket.sendall(data)
        print(f'-> {data}')
      try:
        data = self.client_socket.recv(1024)
      except OSError as e:
        if e.errno == errno.EAGAIN:
          return
        raise e
      if data:
        print(f'<- {data}')
        old_data = data
        data = process_options(self.client_socket, data)
        self.uart.write(data)
      else:
        self.client_socket.close()
        self.client_socket = None
        print('connection closed')
    else:
      try:
        client_socket, client_address = self.server_socket.accept()
      except OSError as e:
        if e.errno == errno.EAGAIN:
          return
        raise e
      print(f'connection from {client_address[0]} accepted')
      self.client_socket = client_socket
      self.connected = True
      send_options(self.client_socket)

def send_telnet_option(socket, cmd, opt):
  print(f'telnet > {Commands.get_name(cmd)} {Options.get_name(opt)}')
  socket.sendall(bytes([Commands.IAC, cmd, opt]))

# telnet option negotiation only works for options that arrive within one chunk of received
# data (i.e. if they span multiple socket read()s, they won't be processed)
def process_options(socket, data):
  i = 0
  count = len(data)
  j = 0
  return_data = bytearray(data)
  while i < count:
    if data[i] == Commands.IAC and (count - i) >= 3:
      iac, cmd, opt = data[i:i+3]
      print(f'telnet < {Commands.get_name(cmd)} {Options.get_name(opt)}')
      if cmd == Commands.DO:
        send_telnet_option(socket, Commands.WILL if opt == Options.SGA or opt == Options.ECHO else Commands.WONT, opt)
      elif cmd == Commands.DONT:
        send_telnet_option(socket, Commands.WONT, opt)
      elif cmd == Commands.WILL or cmd == Commands.WONT:
        pass
      else:
        print(f'Unrecognized telnet option {cmd} {opt}')
      i += 3
    else:
      return_data[j] = data[i]
      j += 1
      i += 1
  return return_data[:j]

def send_options(socket):
  send_telnet_option(socket, Commands.WILL, Options.SGA)
  send_telnet_option(socket, Commands.WILL, Options.ECHO)
