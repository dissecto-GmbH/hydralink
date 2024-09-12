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

[Install the LAN78xx driver from the Apple store](https://apps.apple.com/pl/app/lan78xx-driver-application/id1586760275?mt=12)

Also, install brew:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Ensure python 3 is installed, then install libusb and python-tk using brew:

```bash
brew install libusb
brew install python-tk
```

Finally, create a virtual environment and install pyusb and hydralink there:

```bash
python3 -m venv hydralink-venv
source hydralink-venv/bin/activate
python -m pip install pyusb hydralink
```

### Linux

NOTE: on Linux, you can also use the [hydralink kernel module](https://github.com/dissecto-GmbH/hydralink-kernel-module) to automatically configure HydraLink without additional software.

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

The following picture shows the pinout and the meaning of the LEDs of the hydralink:
![Photo of HydraLink v1.0](https://raw.githubusercontent.com/dissecto-GmbH/hydralink/pages/images/hydralink_1.0.jpg)

## LEDs

When HydraLink is powered, 4 LEDs should turn on: red, orange, green, blue.

The red LED indicates that the HydraLink is powered.

While the HydraLink is not configured, the orange, green and blue are all turned on.

Once the HydraLink is configured, the meaning of the LEDs is:

The orange LED indicates that a link is detected.

The green LED indicates that a 1 gb/s link is detected.

The blue LED indicated that there is activity on the link.

