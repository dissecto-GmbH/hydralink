# HydraLink

Python module to control dissecto HydraLink on Linux and Windows

Can be either used as a standalone application, or as a module imported from another python program

## Installation
Installing the pyusb module is only necessary on Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pyusb
```

## Usage

```bash
# Enable slave mode, 100 megabits speed
python -m hydralink

# Enable master mode, 100 megabits speed
python -m hydralink -m

# Enable slave mode, gigabit speed
python -m hydralink -g

# Enable master mode, gigabit speed
python -m hydralink -m -g

# Blink the LEDs 10 times
python -m hydralink -b 10
```

## API

```python
from hydralink import HydraLink
# master is True or False, speed is 100 or 1000
hl = HydraLink()
hl.setup(master=True, speed=1000)
```
