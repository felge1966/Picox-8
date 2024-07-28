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
    return True
  except OSError as e:
    print(f'Error mounting SD card: {e}')
    return False


def umount_sdcard():
  if sdcard_mounted():
    global SDCARD_DIR
    uos.umount(SDCARD_DIR)


def sdcard_mounted():
  global SDCARD_DIR
  return uos.statvfs(SDCARD_DIR) != uos.statvfs('/')
