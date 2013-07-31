#!/usr/bin/env python3
## This file is part of the pyautomount application, released under
## GNU General Public License, Version 3.0
## See file COPYING for details.
##
## Author: Klementyev Mikhail <jollheef@riseup.net>
#

from automount import *
from gi.repository import Gtk, GObject, Gdk
from pprint import pprint
from threading import Thread

def MountedVolumes():
    _, s = getstatusoutput("pmount | grep '^/dev/' " \
                           + "| awk '{print $1}'")
    return list(filter(lambda d: d != '', s.split('\n')))

class MainWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Umount")
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(10)
        self.vbox = Gtk.Box(spacing=6,
                            orientation=Gtk.Orientation.VERTICAL)
        self.add(self.vbox)

        for Volume in MountedVolumes():
            self.VolumeCheckButton = Gtk.CheckButton(str(Volume))
            self.vbox.pack_start(self.VolumeCheckButton,
                                 True, True, 0)

        UmountButton = Gtk.Button("Отмонтировать")
        UmountButton.set_border_width(10)
        UmountButton.connect("clicked", self.on_umount_click)
        self.vbox.pack_start(UmountButton, True, True, 0)

    def on_umount_click(self, _):
        ToUmount = []
        for CheckButton in self.vbox.get_children():
            if CheckButton.get_name() == 'GtkCheckButton':
                if CheckButton.get_active():
                    ToUmount.append(CheckButton)
        ErrorMessages = []
        for ActiveCheckButton in ToUmount:
            Volume = str(ActiveCheckButton.get_label())
            rv = UsbUmount(Volume)
            if rv[0] == 0:
                self.vbox.remove(ActiveCheckButton)
            else:
                message = rv[1]
                if rv[0] == 5:
                    message = message + "\n" + \
                              getstatusoutput("lsof " + Volume)[1]
                ErrorMessages.append(message)
        for message in ErrorMessages:
            mb = Gtk.MessageDialog(
                self, 0, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK,
                message)
            mb.run()
            mb.destroy()
        if len(ErrorMessages) == 0:
            exit(0)
    
if __name__ == '__main__':
    GObject.threads_init()
    if len(MountedVolumes()) == 0:
        mb = Gtk.MessageDialog(
            False, 0, Gtk.MessageType.ERROR,
            Gtk.ButtonsType.OK,
            "Нет смонтированных устройств")
        mb.set_position(Gtk.WindowPosition.CENTER)
        mb.run()
        mb.destroy()
        exit(0)
    win = MainWindow()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()
    exit(0)

