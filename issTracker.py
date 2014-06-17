#!/usr/bin/python

# My test at adding a satellite
# Based on: http://programmingforresearch.wordpress.com/2012/10/30/using-pyephem-to-get-the-ground-coordinates-of-a-satellite/

# I want this to be the basic framework for the eventual commander

# global "constants"
REFRESH_TIME = 1 # in seconds
SAT_NAME = "ISS"
TLE_URL = "http://www.celestrak.com/NORAD/elements/stations.txt"
# colors
COL_NORMAL = '\033[0m'
COL_GREY   = '\033[90m'
COL_RED    = '\033[91m'
COL_GREEN  = '\033[92m'
COL_YELLOW = '\033[93m'
COL_BLUE   = '\033[94m'
COL_PURPLE = '\033[95m'
COL_CYAN   = '\033[96m'
COL_LT_YEL = '\033[97m'

# global variables

#######################################
## Import modules
#######################################

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

#######################################
## Functions
#######################################

def killProgram(status):
    # This is the function that should be called to kill the program cleanly
    # if there are ever multiple threads that should be killed

    print "\nProgram is terminating."
    #thread.interrupt_main() # kills main & all daemon threads
    os._exit(status)

def outputGrnd():
    # prints output for your groundstation to stdout

    print "Printing info for your ground observer:"
    print "long:", grnd.long
    print "lat:", grnd.lat
    print "elev:", grnd.elev
    print ""
    return

def outputSat():
    # prints output for your groundstation to stdout

    print iss.name
    print "long:", iss.sublong
    print "lat: ", iss.sublat
    print "azimuth:", iss.az
    print "altitude:", iss.alt
    print "elevation:", iss.elevation
    timeOfPass = grnd.next_pass(iss)[0]
    print "next pass at" + COL_YELLOW, timeOfPass, COL_NORMAL
    print "" # blank line for formatting
    return

def updateTLE():
    # Updates the program's TLEs for satellites. It saves them on disc
    # Looks in the current directory for the TLE file

    # fetch the webpage first
    response = urllib2.urlopen(TLE_URL)
    #print "error"
    #killProgram(1)

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

#######################################
## initialize satellite info
#######################################

# TLE == "Two line elements"
# pull the TLE from disc
try:
    f = open('tles.txt', 'r')
    tleString = f.read()
    f.close()
    lines = tleString.split('\n')
    iss = ephem.readtle(SAT_NAME, lines[1], lines[2])
except:
    # there was an error with the file format or the file did not exist
    updateTLE()


grnd = ephem.Observer()
grnd.long = -118.45 * ephem.degree
grnd.lat = 34.0665 * ephem.degree
grnd.elev = 95

outputGrnd()

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
    #print "error"
    #killProgram(1)

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
                killProgram(0)
                sys.exit(0) # redundant, but safe
            elif key == "c" or key == "clear" or key == "cls":
                os.system('clear');
            elif key == "u" or key == "up" or key == "update":
                updateTLE()
                print "Update is complete"
            elif key == "g" or key == "grnd" or key == "ground":
                outputGrnd()
            else:
                outputSat()
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
        killProgram(0)
    except:
        killProgram(0)




if __name__ == "__main__":
    # execute the main function now
    main()







exit(0)
