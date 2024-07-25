class CommandProcessor:
  def __init__(self, terminal):
    self.terminal = terminal

  def userinput(self, data):
    print("Handle userinput")
    self.terminal.write(data)

