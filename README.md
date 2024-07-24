# HydraLink

Python module to control dissecto HydraLink on Linux, MacOS and Windows

Can be either used as a standalone application, or as a module imported from another python program.

## Installation
### Windows

First, [install python 3 from the Microsoft Store](https://apps.microsoft.com/detail/9ncvdn91xzqp).

Next, open a terminal and install hydralink from pypi:

```cmd
python -m pip install hydralink
```

### MacOS

First, install python 3.
Next, install libusb and python-tk using brew:

```bash
brew install libusb python-tk
```

Finally, create a virtual environment and install pyusb and hydralink there:

```bash
python3 -m venv hydralink-venv
source hydralink-venv/bin/activate
python -m pip install pyusb hydralink
```

### Linux

NOTE: on Linux, you can also use the [hydralink kernel module](https://github.com/dissecto-GmbH/usb2ae-kernel-module) to automatically configure HydraLink without additional software.

First, install python and libusb. The specific instructions to do this are different from distribution to distribution. For example, on Ubuntu you might do it like this:

```bash
sudo apt install libusb-1.0-0 python3
```

Finally, create a virtual environment and install pyusb and hydralink there:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pyusb
```

## Usage

If you installed the hydralink module in a virtual environment, make sure to activate the virtual environment.

```bash
# Enable slave mode, 100 megabits speed
python -m hydralink

# Enable master mode, 100 megabits speed
python -m hydralink -m

# Enable slave mode, gigabit speed
python -m hydralink -g

# Enable master mode, gigabit speed
python -m hydralink -m -g

# Show the configuration gui. This requires the python tkinter module!
pyhton -m hydralink --gui
```

## API

```python
from hydralink import HydraLink
hl = HydraLink()
# master is True or False, speed is 100 or 1000.
hl.setup(master=True, speed=1000, promiscuous=True)
# If an option is not specified, the current value is not changed:
hl.setup(speed=100)  # does not change the master mode
```

## Pinout

### HydraLink RC1
On HydraLink RC1, the positive terminal is on pin 7, and the negative terminal is on pin 8 (pin 1 is the pin marked by the dot).
![Photo of HydraLink RC1](https://raw.githubusercontent.com/dissecto-GmbH/hydralink/pages/images/hydralink_rc1.jpg)

Pins 1 through 5 are connected directly to the LAN7801 GPIOs (for example to be used for JTAG). These pins will not be available in the final release.

1. GPIO4 (don't exceed 3.3V!)
2. GPIO5 (don't exceed 3.3V!)
3. GPIO6 (don't exceed 3.3V!)
4. GPIO7 (don't exceed 3.3V!)
5. GPIO8 (don't exceed 3.3V!)
6. Ground
7. Automotive Ethernet +
8. Automotive Ethernet -

## LEDs

When HydraLink is powered, 4 LEDs should turn on: red, orange, green, blue.

The red LED indicates that the HydraLink is powered.

While the HydraLink is not configured, the orange, green and blue are all turned on.

Once the HydraLink is configured, the meaning of the LEDs is:

The orange LED indicates that a 1 gb/s link is detected.

The green LED indicates that a 100 mb/s link is detected.

The blue LED indicated that there is activity on the link.

