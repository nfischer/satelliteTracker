#!/usr/bin/python


#######################################
## Import modules
#######################################

import sys
import subprocess
import os
import getpass
import urllib2
import time
import datetime
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

# global "constants"
REFRESH_TIME = 1 # in seconds
SAT_NAME = "ISS"
TLE_URL = "http://www.celestrak.com/NORAD/elements/stations.txt"
DATA_DIR = "/home/" + getpass.getuser() + "/.satTracker/"
TLE_FILE = DATA_DIR+"tles.txt"
GRND_FILE = DATA_DIR+"grnd.txt"
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
## Functions
#######################################

def killProgram(status):
    # This is the function that should be called to kill the program cleanly
    # if there are ever multiple threads that should be killed

    print "\nProgram is terminating."
    #thread.interrupt_main() # kills main & all daemon threads
    os._exit(status)

def updateGrnd():

    print "Please enter information for your ground observer:"
    print "Leave a line blank to use the default value (for O.C.)."
    u_long = raw_input("Longitude (degrees): ")
    u_lat  = raw_input("Latitude (degrees): ")
    u_elev = raw_input("Elevation (m): ")

    defLong = -118.45
    defLat  = 34.0665
    defElev = 95.0

    # set values
    try:
        u_long = float(u_long)
    except:
        u_long = defLong

    try:
        u_lat = float(u_lat)
    except:
        u_lat = defLat

    try:
        u_elev = float(u_elev)
    except:
        u_elev = defElev



    # check validity of values & their types
    if u_elev < 0:
        u_elev = defElev


    # convert to radians
    u_long = u_long * ephem.degree
    u_lat = u_lat * ephem.degree

    # write values to file
    values = [ str(u_long), str(u_lat), str(u_elev), ""]
    grndString = '\n'.join(values)

    with open(GRND_FILE, 'w') as f:
        f.write(grndString)

    return


def installProgram():
    # creates the directory and asks for inputted ground observer info

    installMsg = """
    Would you like to allow issTracker to install on your computer?

    It will create on your computer:

    - a file to save TLE info for your satellites
    - a file to save longitude and latitude for your ground station
    - a directory within your home directory where these files will be saved

    """

    print installMsg
    decision = raw_input("Do you want to install issTracker? (y/n): ")
    if decision != "y":
        print "Not installing. Terminating issTracker."
        exit(1)

    print "\nInstalling issTracker\n"

    # make the directory
    dirExistsCmd = "test -d " + DATA_DIR
    if os.system(dirExistsCmd) != 0:
        if os.system("mkdir "+DATA_DIR) != 0:
            print "There was an error installing the program."
            exit(1)

    if os.system("test -f "+GRND_FILE) != 0:
        updateGrnd()

    return



def isInstalled():
    # returns True if issTracker.py appears to be installed correctly

    dirExistsCmd = "test -d " + DATA_DIR
    if os.system(dirExistsCmd) != 0:
        return False


    grndExistsCmd = "test -f " + GRND_FILE
    if os.system(grndExistsCmd) != 0:
        return False


    return True



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
    global iss
    iss = ephem.readtle(SAT_NAME, lines[1], lines[2])

    return


def updateVariables():
    try:
        while 1:
            now = ephem.now()
            grnd.date = now
            iss.compute(grnd) # this computes for right now relative to grnd
            #iss.compute() # this computes for right now
            time.sleep(REFRESH_TIME)
    except:
        exit(0)


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
    ## Check if installed
    if not isInstalled():
        installProgram()

    ## initialize satellite info
    stamp = datetime.datetime.fromtimestamp(os.stat(TLE_FILE)[8] )
    stamp = stamp + datetime.timedelta(days=3)

    if datetime.datetime.now() > stamp:
        # TLE is old
        resp = raw_input("Your TLE is getting a little stale. Would you like to update it? (y/n) ")
        if resp == "y":
            updateTLE()

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


    ## set up ground station information
    try:
        f = open(GRND_FILE, 'r')
        grndString = f.read()
        f.close()
        lines = grndString.split('\n')
        global grnd
        grnd = ephem.Observer()
        grnd.long = float(lines[0])
        grnd.lat =  float(lines[1])
        grnd.elev = float(lines[2])
    except:
        # there was an error with the file format or the file did not exist
        print "error with grnd file"
        killProgram(1)

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
