#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from tkinter import ttk, messagebox
import tkinter as tk
from typing import Optional
from hydralink.hydralink import HydraLink, get_hydralinks, hydralink_by_serial


class GuiVars:
    def __init__(self) -> None:
        self.speed = tk.IntVar(value=-1)
        self.master = tk.IntVar(value=-1)
        self.promiscuous = tk.IntVar(value=-1)
        self.mac_addr = tk.StringVar(value='')

    def clear(self) -> None:
        self.speed.set(-1)
        self.master.set(-1)
        self.promiscuous.set(-1)
        self.mac_addr.set('')

    def get_vars(self, hl: HydraLink) -> None:
        speed = hl.phy.get_speed()
        master = hl.phy.get_master()
        promiscuous = hl.mac.get_promiscuous()
        mac_addr = hl.mac.get_mac_addr().hex(':')

        if speed is None:
            self.speed.set(-1)
        else:
            self.speed.set(speed)
        self.master.set(1 if master else 0)
        self.promiscuous.set(1 if promiscuous else 0)
        self.mac_addr.set(mac_addr)


def str2mac_addr(value: str) -> bytes:
    mac_segments = value.split(':')
    if any(len(a) != 2 for a in mac_segments):
        raise ValueError('Wrong MAC address format')
    try:
        return bytes(int(a, 16) for a in mac_segments)
    except Exception:
        raise ValueError('Not hexadecimal')


class Gui:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title('HydraLink configuration')
        self.frm = ttk.Frame(self.root, padding=10)
        self.frm.grid()

        self.hl: Optional[HydraLink] = None

        self.vars = GuiVars()

        ttk.Label(self.frm, text="Device Selection:").grid(column=0, row=1)
        self.device_var = tk.StringVar()
        self.combobox = ttk.Combobox(
            self.frm, textvariable=self.device_var,
            state='readonly',
            postcommand=self.dropdown_opened)
        self.combobox.grid(column=1, row=1)
        self.combobox.bind('<<ComboboxSelected>>', self.change_device)

        ttk.Label(self.frm, text="MAC address:").grid(column=0, row=2)
        self.textfield_mac_addr = ttk.Entry(
            self.frm, textvariable=self.vars.mac_addr,
            validatecommand=(self.root.register(self.validate_mac_addr), '%P'),
            validate='focusout',
            state='disabled')
        self.textfield_mac_addr.grid(column=1, row=2)

        self.button_gigabit = ttk.Radiobutton(
            self.frm, text='1 Gigabit/s', variable=self.vars.speed,
            value=1000, command=self.update_settings,
            state='disabled')
        self.button_gigabit.grid(column=0, row=3)

        self.button_100mbit = ttk.Radiobutton(
            self.frm, text='100 Megabit/s', variable=self.vars.speed,
            value=100, command=self.update_settings,
            state='disabled')
        self.button_100mbit.grid(column=1, row=3)

        self.button_master = ttk.Radiobutton(
            self.frm, text='Master', variable=self.vars.master,
            value=1, command=self.update_settings,
            state='disabled')
        self.button_master.grid(column=0, row=4)

        self.button_slave = ttk.Radiobutton(
            self.frm, text='Slave', variable=self.vars.master,
            value=0, command=self.update_settings,
            state='disabled')
        self.button_slave.grid(column=1, row=4)

        self.button_promiscuous = ttk.Checkbutton(
            self.frm, text='Force promiscuous Mode',
            variable=self.vars.promiscuous,
            onvalue=1, offvalue=0,
            command=self.update_settings,
            state='disabled')
        self.button_promiscuous.grid(column=0, row=5, columnspan=2)

    def run(self) -> None:
        self.root.mainloop()

    def dropdown_opened(self) -> None:
        devices = get_hydralinks()
        self.combobox['values'] = list(devices.keys())

    def validate_mac_addr(self, value: str) -> bool:
        try:
            str2mac_addr(value)
        except ValueError:
            return False
        else:
            return True

    def update_settings(self) -> None:
        if self.hl is not None:
            speed: Optional[int] = self.vars.speed.get()
            if speed not in [100, 1000]:
                speed = None
            master: Optional[bool] = bool(self.vars.master.get())
            promiscuous: Optional[bool] = True if self.vars.promiscuous.get() else None
            mac_addr: Optional[str] = self.vars.mac_addr.get()
            try:
                str2mac_addr(self.vars.mac_addr.get())
            except ValueError:
                mac_addr = None

            try:
                self.hl.setup(speed=speed, master=master, promiscuous=promiscuous, mac_addr=mac_addr)
            except Exception as x:
                messagebox.showerror("Error", str(x))

    def device_selected(self) -> None:
        if self.hl is None:
            self.vars.clear()
            self.button_gigabit['state'] = "disabled"
            self.button_100mbit['state'] = "disabled"
            self.button_master['state'] = "disabled"
            self.button_slave['state'] = "disabled"
            self.button_promiscuous['state'] = "disabled"
            self.textfield_mac_addr['state'] = "disabled"
        else:
            self.button_gigabit['state'] = "enabled"
            self.button_100mbit['state'] = "enabled"
            self.button_master['state'] = "enabled"
            self.button_slave['state'] = "enabled"
            self.button_promiscuous['state'] = "enabled"
            self.textfield_mac_addr['state'] = "enabled"
            self.vars.get_vars(self.hl)

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
