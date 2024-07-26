import network
import config

nic = None

def connect():
  global nic
  wifi_config = config.get('wifi', None)
  if not wifi_config:
    print('No "wifi" configuration')
    return
  if nic:
    nic.active(False)
  else:
    nic = network.WLAN(network.STA_IF)
  nic.active(True)
  nic.connect(wifi_config[0], wifi_config[1])


def status():
  if not nic:
    return "not configured"
  status = nic.status()
  if status == network.STAT_IDLE:
    return "idle"
  elif status == network.STAT_CONNECTING:
    return "connecting"
  elif status == network.STAT_WRONG_PASSWORD:
    return "wrong password"
  elif status == network.STAT_NO_AP_FOUND:
    return "access point not found"
  elif status == network.STAT_CONNECT_FAIL:
    return "connection failed"
  elif status == network.STAT_GOT_IP:
    ip, netmask, gateway, dns = nic.ifconfig()
    return f'connected (ip: {ip} gw: {gateway} dns: {dns})'
  else:
    return f'unknown WIFI status {status}'
