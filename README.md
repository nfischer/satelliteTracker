satelliteTracker
----------------

A Python program to track the location of the ISS and possibly other
satellites.

Installation
------------

This relies on several other modules, so you'll need to make sure these are
installed.

### Pyephem

```Bash
$ sudo pip install pyephem
```

### Satellite Tracker

```Bash
$ git clone --recursive https://github.com/nfischer/satelliteTracker.git
$ # make sure to specify '--recursive' in order to install the submodule
```

### SunriseSunsetCalculator

This project uses Jacques-Etienne Beaudet's
[SunriseSunsetCalculator](https://github.com/jebeaudet/SunriseSunsetCalculator),
based on the algorithm for calculating sunrise and sunset found
[here](http://williams.best.vwh.net/sunrise_sunset_algorithm.htm)

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

If so, you're done! Otherwise, you will need to install the submodule manually:

```Bash
$ cd satelliteTracker/
$ git submodule init
$ git submodule update
```

And that's it, you're off to the races!

What can it do?
---------------

SatelliteTracker can:

 - update a satellite's location in real-time
 - provide accurate longitude, latitude, elevation, and other location
   parameters
 - display information about your ground station, as well as the next time a
   satellite passes over your ground station
 - automatically update TLEs for the ISS
 - notify you if your ground station data is incorrectly formatted


How does it work?
-----------------

This project is made using the pyephem module. To run this script, you will
need to first install this module. If you're unsure, try to run the script
and it will give you a guide on how to install it.

This program has two basic threads:

 - The background thread that constantly (once per second)  updates the values
   for the satellite's location.
 - The foreground thread that prompts you for commands and then executes them.

The advantage of this model is that the program will always know where the
satellite is, so this leaves room for future development on automatic
alerts (at least while the program is running) for when the satellite is
passing overhead.

If your machine does not have multiple cores (perhaps it's a Raspberry Pi,
for example), don't worry. SatelliteTracker will still run smoothly. Your
machine should switch between the threads and run them concurrently, so
you should notice very little difference in performance.
