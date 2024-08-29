#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from tkinter import ttk, messagebox
import tkinter as tk
from typing import Any, Dict, NamedTuple, Optional
import hydralink.hydralink
from hydralink.hydralink import HydraLink


class FoundUsbDevice(NamedTuple):
    vid: int
    pid: int
    serialnum: str
    path: str
    software_key: str


if hydralink.hydralink.is_windows():
    from hydralink.windows_apis import list_usb_devices
    from hydralink.lan7801_win import LAN7801_Win

    def get_hydralinks() -> Dict[str, Any]:
        return {t.serialnum: t for t in list_usb_devices() if t.vid == 0x0424 and t.pid == 0x7801}

    def hydralink_by_serial(serial: str) -> Optional[HydraLink]:
        devices = get_hydralinks()
        if serial not in devices:
            return None
        key = devices[serial].software_key
        mac = LAN7801_Win.by_key(key)
        if mac:
            return HydraLink(mac)
        return None

else:
    import usb.core
    from hydralink.lan7801_libusb import LAN7801_LibUSB

    def get_hydralinks() -> Dict[str, Any]:
        return {"%d.%d" % (dev.bus, dev.address) if dev.serial_number is None else dev.serial_number: dev
                for dev in usb.core.find(find_all=True, idVendor=0x0424, idProduct=0x7801)}

    def hydralink_by_serial(serial: str) -> Optional[HydraLink]:
        devices = get_hydralinks()
        if serial in devices:
            dev: usb.core.Device = devices[serial]
            return HydraLink(LAN7801_LibUSB(dev))
        else:
            return None


class Gui:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title('HydraLink configuration')
        self.frm = ttk.Frame(self.root, padding=10)
        self.frm.grid()

        self.hl: Optional[HydraLink] = None

        self.speed_var = tk.IntVar(value=-1)
        self.master_var = tk.IntVar(value=-1)
        self.promiscuous_var = tk.IntVar(value=-1)

        ttk.Label(self.frm, text="Device Selection:").grid(column=0, row=1)
        self.device_var = tk.StringVar()
        self.combobox = ttk.Combobox(self.frm, textvariable=self.device_var,
                                     state='readonly',
                                     postcommand=self.dropdown_opened)
        self.combobox.grid(column=1, row=1)
        self.combobox.bind('<<ComboboxSelected>>', self.change_device)

        self.button_gigabit = ttk.Radiobutton(self.frm, text='1 Gigabit/s', variable=self.speed_var,
                                              value=1000, command=self.update_settings,
                                              state='disabled')
        self.button_gigabit.grid(column=0, row=2)

        self.button_100mbit = ttk.Radiobutton(self.frm, text='100 Megabit/s', variable=self.speed_var,
                                              value=100, command=self.update_settings,
                                              state='disabled')
        self.button_100mbit.grid(column=1, row=2)

        self.button_master = ttk.Radiobutton(self.frm, text='Master', variable=self.master_var,
                                             value=1, command=self.update_settings,
                                             state='disabled')
        self.button_master.grid(column=0, row=3)

        self.button_slave = ttk.Radiobutton(self.frm, text='Slave', variable=self.master_var,
                                            value=0, command=self.update_settings,
                                            state='disabled')
        self.button_slave.grid(column=1, row=3)

        self.button_promiscuous = ttk.Checkbutton(self.frm, text='Promiscuous Mode',
                                                  variable=self.promiscuous_var,
                                                  onvalue=1, offvalue=0,
                                                  command=self.update_settings,
                                                  state='disabled')
        self.button_promiscuous.grid(column=0, row=4, columnspan=2)

    def run(self) -> None:
        self.root.mainloop()

    def dropdown_opened(self) -> None:
        devices = get_hydralinks()
        self.combobox['values'] = list(devices.keys())

    def update_settings(self) -> None:
        if self.hl is not None:
            speed: Optional[int] = self.speed_var.get()
            if speed not in [100, 1000]:
                speed = None
            master = bool(self.master_var.get())
            promiscuous = bool(self.promiscuous_var.get())

            try:
                self.hl.setup(speed=speed, master=master, promiscuous=promiscuous)
            except Exception as x:
                messagebox.showerror("Error", str(x))

    def device_selected(self) -> None:
        if self.hl is None:
            self.speed_var.set(-1)
            self.master_var.set(-1)
            self.promiscuous_var.set(-1)
            self.button_gigabit['state'] = "disabled"
            self.button_100mbit['state'] = "disabled"
            self.button_master['state'] = "disabled"
            self.button_slave['state'] = "disabled"
            self.button_promiscuous['state'] = "disabled"
        else:
            self.button_gigabit['state'] = "enabled"
            self.button_100mbit['state'] = "enabled"
            self.button_master['state'] = "enabled"
            self.button_slave['state'] = "enabled"
            self.button_promiscuous['state'] = "enabled"

            speed = self.hl.phy.get_speed()
            master = self.hl.phy.get_master()
            promiscuous = (self.hl.mac[0x0b0] & 0x0100) == 0x0100

            if speed is None:
                self.speed_var.set(-1)
            else:
                self.speed_var.set(speed)
            self.master_var.set(1 if master else 0)
            self.promiscuous_var.set(1 if promiscuous else 0)

    def change_device(self, o: tk.Event) -> object:  # type: ignore
        try:
            found = hydralink_by_serial(self.device_var.get())
            self.hl = found
            if found is None:
                messagebox.showerror("Error", "Selected HydraLink was not found")
            self.device_selected()
            return 1
        except Exception as x:
            messagebox.showerror("Error", str(x))


def main() -> None:
    g = Gui()
    g.run()
