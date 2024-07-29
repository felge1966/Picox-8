from machine import SPI, Pin
import uos
import sdcard
import time
import errno

SDCARD_DIR = '/sd'

def ensure_mountpoint(dir):
  try:
    uos.mkdir(dir)
  except OSError as e:
    if e.errno != errno.EEXIST:
      raise e


def path(filename):
  return f'{SDCARD_DIR}/{filename}'


def exists(filename):
  try:
    uos.stat(path(filename))
  except OSError as e:
    if e.errno == errno.ENOENT:
      return False
    else:
      raise e
  return True


def listdir():
  return uos.listdir(SDCARD_DIR)


def file_size(filename):
  return uos.stat(path(filename))[6]


def slurp(filename):
  with open(path(filename), 'r') as f:
    return f.read()


def spit(filename, data):
  with open(path(filename), 'w') as f:
    return f.write(data)


def remove(filename):
  uos.remove(path(filename))


def mount_sdcard():
  global SDCARD_DIR
  if sdcard_mounted():
    print(f'SDCard already mounted on {SDCARD_DIR}')
    return True
  try:
    ensure_mountpoint(SDCARD_DIR)
    sd = sdcard.SDCard(SPI(0), Pin(17))
    vfs = uos.VfsFat(sd)
    uos.mount(vfs, SDCARD_DIR)
  except OSError as e:
    print(f'Error mounting SD card: {e}')
    return False
  return True


def umount_sdcard():
  if sdcard_mounted():
    global SDCARD_DIR
    uos.umount(SDCARD_DIR)


def sdcard_mounted():
  global SDCARD_DIR
  return uos.statvfs(SDCARD_DIR) != uos.statvfs('/')
