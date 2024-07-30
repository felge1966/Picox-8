import picox8
while True:
  try:
    picox8.main_loop()
  except KeyboardInterrupt:
    break
