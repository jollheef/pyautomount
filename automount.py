#!/usr/bin/env python3
## This file is part of the pyautomount application, released under
## GNU General Public License, Version 3.0
## See file COPYING for details.
##
## Author: Klementyev Mikhail <jollheef@riseup.net>
#

import os, time, pyudev, re, subprocess, argparse
from os.path import abspath, dirname
from threading import Thread, current_thread

def getstatusoutput(cmd, _shell=True): 
    """Return (status, output) of executing cmd in a shell."""
    """This new implementation should work on all platforms."""
    pipe = subprocess.Popen(cmd, shell=_shell,
                            universal_newlines=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    output = str.join("", pipe.stdout.readlines()) 
    sts = pipe.wait()
    if sts is None:
        sts = 0
    return sts, output

def InBlackListp(device) -> bool:
    Log("Check blacklist for ID_SERIAL " + device['ID_SERIAL'])
    with open(dirname(abspath(__file__)) + "/blacklist", 'r') as f:
        for devname in f.readlines():
            if device['ID_SERIAL'] == devname.rstrip():
                Log("device with ID_SERIAL == "
                    + device['ID_SERIAL']
                    + " is not mount (blacklist)")
                return True
    return False

def DeviceHandler(action, device):
    Log("Action: " + str(action) + ", " \
        + "DEVNAME: " + str(device['DEVNAME']))
    if action == "add":
        if InBlackListp(device):
            return None
        if sum(1 for _ in device.children) != 0:
            Log(str(device.device_node) + \
                " is not mount (partition table)")
            return None
        retusb = UsbMount(device)
        id_vendor = ""
        id_model = ""
        try:
            id_vendor = str(device['ID_VENDOR'])
            id_model = str(device['ID_MODEL'])
        except:
            pass
        if retusb[0] != 0:
            retsend = SendNotify("Ошибка при монтировании раздела " \
                                 + str(device.device_node) + " (" \
                                 + id_vendor + " " \
                                 + id_model + ")")
            if retsend[0] != 0:
                Log("SendNotify error: " + retsend[1])
            return None
        SendNotify(str(device.device_node) + " (" \
                   + id_vendor + " " \
                   + id_model + ") " \
                   + "смонтирован в " + str(retusb[1]))
    if action == "remove" and UsbMountedp(device):
        Log("Unsafely umount")
        retusb = UsbUmount(device)
        if retusb[0] != 0:
            Log("Umount error " + retusb[1])

def UsbMountedp(device):
    return getstatusoutput("mount | grep '" \
                           + device.device_node + "\s'" \
                           + "| awk '{print $1}'")[1]

def UsbMount(device):
    global args
    cmd = ["pmount", device.device_node]
    if args.sync == 'sync':
        cmd.insert(1, "--sync")
    retval, output = getstatusoutput(cmd, _shell = False)
    return [retval, re.sub(r'dev', 'media', device.device_node)]

def UsbUmount(device):
    if type(device) is str:
        dev = device
    else:
        dev = device.device_node
    return getstatusoutput(["pumount", str(dev)], _shell = False)

def SendNotify(notify):
    Log(notify)
    return getstatusoutput("DISPLAY=:0 notify-send " \
                           + "'" + str(notify) + "'")

def Log(message):
    print(str(time.strftime("[%d %b %Y %H:%M:%S] (")) + \
          current_thread().name + ") " + str(message))

class ObserverDeadsException(Exception):
    pass

class UdevObserver(Thread):
    def __init__(self, DeviceHandler):
        super(UdevObserver, self).__init__()
        self.quit = False

        self.context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by('block')
        self.observer = pyudev.MonitorObserver(
            self.monitor,
            lambda action, device: Thread(
                target=DeviceHandler,
                args=[action, device]).start())

    def run(self):
        self.observer.start()
        Log(self.observer)

    def wait(self):
        try:
            while True:
                time.sleep(1)
                if not self.observer.isAlive():
                    raise ObserverDeadsException
        except KeyboardInterrupt:
            exit(0)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Auto mount.')
    parser.add_argument('--sync', action='store_const',
                        const="sync", default="async",
                        help='Mount without write caching.')
    args = parser.parse_args()
    while True:
        try:
            Observer = UdevObserver(DeviceHandler)
            Observer.run()
            Observer.wait()
            while True:
                time.sleep(600)
        except ObserverDeadsException:
            Log("Observer dead. Restarting observer.")
            pass
