# HydraLink

Python module to control dissecto HydraLink on Linux and Windows

Can be either used as a standalone application, or as a module imported from another python program

## Installation
Installing the pyusb module is only necessary on Linux

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install pyusb
```

## Usage

```bash
# Enable slave mode, 100 megabits speed
python ./hydralink/hydralink_config.py

# Enable master mode, 100 megabits speed
python ./hydralink/hydralink_config.py -m

# Enable slave mode, gigabit speed
python ./hydralink/hydralink_config.py -g

# Enable master mode, gigabit speed
python ./hydralink/hydralink_config.py -m -g

# Blink the LEDs 10 times
python ./hydralink/hydralink_config.py -b 10
```

## API

```python
from hydralink import HydraLink
# master is True or False, speed is 100 or 1000
hl = HydraLink()
hl.setup(master=True, speed=1000)
```
