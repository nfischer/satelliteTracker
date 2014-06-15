#!/usr/bin/python

# My test at adding a satellite
# Based on: http://programmingforresearch.wordpress.com/2012/10/30/using-pyephem-to-get-the-ground-coordinates-of-a-satellite/

# I want this to be the basic framework for the eventual commander

# global "constants"
REFRESH_TIME = 0.1 # in seconds
SAT_NAME = "ISS"
TLE_URL = "http://www.celestrak.com/NORAD/elements/stations.txt"

# global variables

import sys
import os
import urllib2

import time
#import math
import thread
import threading

try:
    import ephem
except:
    print "You don't have pyephem installed!"
    print "Install it like so:\n"
    print "$ sudo apt-get install python-pip"
    print "$ sudo apt-get install python-dev"
    print "$ sudo pip install pyephem"

    exit(1)


def outputGrnd():
    # prints output for your groundstation to stdout
    print "Printing info for your ground observer:"
    print "long:", grnd.long
    print "lat:", grnd.lat
    print "elev:", grnd.elev
    print ""
    return 0

# initialize satellite info
name = SAT_NAME

# TLE == "Two line elements"
# pull the TLE from disc
line1 = "1 25544U 98067A   14164.88420351  .00007379  00000-0  13387-3 0  4847"
line2 = "2 25544  51.6468 115.9516 0004435  99.2984 357.3865 15.50694927890818"

f = open('tles.txt', 'r')
tleString = f.read()
f.close()

lines = tleString.split('\n')

iss = ephem.readtle(name, lines[1], lines[2])

grnd = ephem.Observer()
grnd.long = -118.45 * ephem.degree
grnd.lat = 34.0665 * ephem.degree
grnd.elev = 95

outputGrnd()

def killProgram():
    print "\nProgram is terminating."
    #thread.interrupt_main() # kills main & all daemon threads
    os._exit(0)

def updateVariables():
    try:
        while 1:
            now = ephem.now()
            grnd.date = now
            iss.compute(grnd) # this computes for right now relative to grnd
            #iss.compute() # this computes for right now
            #print iss.sublong, iss.sublat
            time.sleep(REFRESH_TIME)
    except:
        exit(0)

def updateTLE():
    # Updates the program's TLEs for satellites. It saves them on disc
    # Looks in the current directory for the TLE file

    # fetch the webpage first
    response = urllib2.urlopen(TLE_URL)
    html = response.read() # returns a string
    
    # parse for the ISS (first 3 lines)
    endSub = html.find('TIANGONG')
    tleData = html[0:endSub]

    # write the data to file
    f = open('tles.txt', 'w')
    f.write(tleData)
    f.close()

    # reload TLEs in satellite object
    lines = tleData.split('\n')
    iss = ephem.readtle(SAT_NAME, lines[1], lines[2])

    return
    

def printFunc():
    try:
        while 1:
            key = raw_input("Press enter to see values, q to quit: ")
            if key == "q" or key == "Q" or key == ";q":
                killProgram()
                sys.exit(0) # redundant, but safe
            elif key == "c" or key == "clear" or key == "cls":
                os.system('clear');
            elif key == "u" or key == "up" or key == "update":
                updateTLE()
                print "done"
            else:
                # These values are computed live
                print "ISS:"
                print "long:", iss.sublong
                print "lat: ", iss.sublat
                print "azimuth:", iss.az
                print "altitude:", iss.alt
                print "elevation:", iss.elevation
                timeOfPass = grnd.next_pass(iss)[0]
                print "next pass at", timeOfPass
                print "" # blank line for formatting
    except:
        exit(0)



def main():
    # use threading module to spawn new threads
    my_threads = list()
    my_threads.append(threading.Thread(target=updateVariables) )
    my_threads.append(threading.Thread(target=printFunc) )
    my_threads[0].daemon = True # run this thread in the background
    my_threads[1].daemon = False
    my_threads[0].start()
    my_threads[1].start()

    for t in my_threads:
        while t.isAlive():
            t.join(2)

    try:
        while 1:
            pass
        killProgram()
    except:
        killProgram()




if __name__ == "__main__":
    # execute the main function now
    main()







exit(0)
