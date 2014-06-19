#!/usr/bin/python

# My test at adding a satellite
# Based on: http://programmingforresearch.wordpress.com/2012/10/30/using-pyephem-to-get-the-ground-coordinates-of-a-satellite/

# I want this to be the basic framework for the eventual commander

# global "constants"
REFRESH_TIME = 1 # in seconds
SAT_NAME = "ISS"
TLE_URL = "http://www.celestrak.com/NORAD/elements/stations.txt"
TLE_FILE = "tles.txt"
# colors
COL_NORMAL = '\033[0m'
COL_GREY   = '\033[90m'
COL_RED    = '\033[91m'
COL_GREEN  = '\033[92m'
COL_YELLOW = '\033[93m'
COL_BLUE   = '\033[94m'
COL_PURPLE = '\033[95m'
COL_CYAN   = '\033[96m'
COL_WHITE  = '\033[97m'

# global variables
global grnd
global iss

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
    g_long = grnd.long
    g_lat = grnd.lat
    g_elev = grnd.elev

    print "Printing info for your ground observer:"
    print "long:", COL_BLUE, g_long, COL_NORMAL
    print "lat: ", COL_BLUE, g_lat,  COL_NORMAL
    print "elev:", g_elev
    print ""
    return

def outputSat():
    # prints output for your groundstation to stdout

    s_name = iss.name
    s_long = iss.sublong
    s_lat = iss.sublat
    s_az = iss.az
    s_alt = iss.alt
    s_elev = iss.elevation
    timeOfPass = grnd.next_pass(iss)[0]
    print s_name
    print "long:", COL_GREEN, s_long, COL_NORMAL
    print "lat: ", COL_GREEN, s_lat,  COL_NORMAL
    print "azimuth:", s_az
    print "altitude:", s_alt
    print "elevation:", s_elev
    print "next pass at" + COL_YELLOW, timeOfPass, COL_NORMAL
    print "" # blank line for formatting
    return

def outputNow():
    # prints the current time according to pyephem
    print "Current time is", COL_YELLOW, ephem.now(), COL_NORMAL
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
    f = open(TLE_FILE, 'w')
    f.write(tleData)
    f.close()

    # reload TLEs in satellite object
    lines = tleData.split('\n')
    iss = ephem.readtle(SAT_NAME, lines[1], lines[2])

    return


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
    f = open(TLE_FILE, 'w')
    f.write(tleData)
    f.close()

    # reload TLEs in satellite object
    lines = tleData.split('\n')
    iss = ephem.readtle(SAT_NAME, lines[1], lines[2])

    return

def matches(a, b):
    # Takes two strings and returns True if one is a substring of the other
    # and begins at the first character of the string.

    lenA = len(a)
    lenB = len(b)

    if lenA == 0 or lenB == 0:
        # empty string should return false always
        return False

    if lenA > lenB:
        # swap them so that a is shorter
        tmp = b
        b = a
        a = tmp

    # assume that lenA <= lenB
    b = b[0:lenA]

    # if a & b are a match, then return true
    return a == b




def prompt():
    try:
        while 1:
            key = raw_input("Press enter to see values, q to quit: ")
            if matches(key,"quit") or key == "Q" or key == ";q":
                killProgram(0)
                sys.exit(0) # redundant, but safe
            elif matches(key,"clear") or key == "cls":
                os.system('clear');
            elif matches(key,"update"):
                updateTLE()
                print "Update is complete"
            elif matches(key,"grnd") or key == "ground":
                outputGrnd()
            elif matches(key,"now"):
                outputNow()
            else:
                outputSat()
    except:
        exit(0)



def main():
    #######################################
    ## initialize satellite info
    #######################################

    # TLE == "Two line elements"
    # pull the TLE from disc
    try:
        f = open(TLE_FILE, 'r')
        tleString = f.read()
        f.close()
        lines = tleString.split('\n')
        global iss
        iss = ephem.readtle(SAT_NAME, lines[1], lines[2])
    except:
        # there was an error with the file format or the file did not exist
        updateTLE()


    global grnd
    grnd = ephem.Observer()
    grnd.long = -118.45 * ephem.degree
    grnd.lat = 34.0665 * ephem.degree
    grnd.elev = 95

    outputGrnd()

    # use threading module to spawn new threads
    my_threads = list()
    my_threads.append(threading.Thread(target=updateVariables) )
    my_threads.append(threading.Thread(target=prompt) )
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
