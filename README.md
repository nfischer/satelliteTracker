satelliteTracker
----------------

A Python CLI program to track the location of the ISS and other satellites.

Installation
------------

### Cloning the project

The recommended installation method is to first clone this git repo, as such:

```Bash
# make sure to specify '--recursive' in order to install the submodules
$ git clone --recursive https://github.com/nfischer/satelliteTracker.git
```

### SunriseSunsetCalculator

This project uses Jacques-Etienne Beaudet's
[SunriseSunsetCalculator](https://github.com/jebeaudet/SunriseSunsetCalculator),
based on [this
algorithm](http://williams.best.vwh.net/sunrise_sunset_algorithm.htm) for
calculating sunrise and sunset

If you specified the `--recursive` flag when cloning, you should see a directory
structure like:

```
satelliteTracker/
  LICENSE
  README.md
  satTracker.py
  SunriseSunsetCalculator/
    __init__.py
    README.md
    sunrise_sunset.py
```

### [Pyephem](http://rhodesmill.org/pyephem/)

Before installing this module, you'll need to install pip:

```Bash
$ sudo apt-get install python-pip python-dev
```

Then install dependencies with:

```Bash
$ sudo pip install -r requirements.txt
```

And that's it, you're off to the races!

What can it do?
---------------

SatelliteTracker can:

 - update a satellite's location in real-time
 - provide accurate longitude, latitude, elevation, and other location
   parameters
 - display information about your ground station, as well as the next time your
   satellite passes overhead
 - automatically update TLEs for various satellites

How does it work?
-----------------

This project is made using the pyephem module to do the cool computations for
longitude, latitude, etc. in real-time for your satellite of choice.

This program has two basic threads:

 - The background thread that updates the values for the satellite's location.
 - The foreground thread that prompts you for commands and then executes them.

The advantage of this concurrent design is that the program will always know
where the satellite is, so this leaves room for future development on automatic
alerts in real-time for when the satellite is passing overhead or for other
events.

### A note about parallelism in Python

Python doesn't have great support for parallelism, which is unfortunate. Due to
[Global Interpreter Lock](https://wiki.python.org/moin/GlobalInterpreterLock),
a lot of Python code runs concurrently, even if you use the appropriate
multithreading modules.

This project does still work though. The background thread runs concurrently
with the foreground thread, and they context switch often enough that everything
works. So this means the project will still run smoothly, even if you have a
singe-core machine (such as a Raspberry Pi).
