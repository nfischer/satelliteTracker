#!/usr/bin/python


#######################################
## Import modules
#######################################

import sys
import os
import urllib2
import time
import datetime
#import math
import threading


def handleDependencies():

    returner = 0

    linInstall = """
    sudo apt-get install python-pip
    sudo apt-get install python-dev
    sudo pip install pyephem
    """
    macInstall = """
    sudo easy_install pip
    sudo pip install pyephem
    """

    instCmds = linInstall # default
    print "You don't have pyephem installed!"
    print "Install it like so:"
    opSys = sys.platform
    if opSys == "linux" or opSys == "linux2":
        print linInstall
        instCmds = linInstall
    elif opSys == "darwin":
        print macInstall
        instCmds = macInstall
    else:
        print "Your system is not currently supported, so it may not work."
        print "Try:\nsudo pip install pyephem"
        return returner

    resp = raw_input("Would you like this program to install these dependencies for you? (y/n) ")
    if resp == "y":
        if os.system("which pip >/dev/null 2>&1") == 0:
            # pip is already installed
            cmd = "sudo pip install pyephem"
            print cmd
            ret = os.system(cmd)
            if ret != 0:
                print "There was some failure with the command"
                returner = 1

        else:
            for cmd in instCmds.split('\n'):
                print cmd
                ret = os.system(cmd)
                if ret != 0:
                    print "There was some failure with the command"
                    returner = 1

    return returner


try:
    import ephem
except:
    ret = handleDependencies()

    exit(ret)

# global "constants"
REFRESH_TIME = 1 # in seconds
SAT_NAME = "ISS"
TLE_URL = "http://www.celestrak.com/NORAD/elements/stations.txt"
ZERO_TUPLE = (0,0,0,0,0,0)

def getHomeDir():
   return os.path.expanduser("~")

DATA_DIR  = os.path.join(getHomeDir(), ".satTracker")
TLE_FILE  = os.path.join(DATA_DIR, "tles.txt")
GRND_FILE = os.path.join(DATA_DIR, "grnd.txt")

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
global displacement
global is_frozen
global p_time

#######################################
## Functions
#######################################

def killProgram(status):
    # This is the function that should be called to kill the program cleanly
    # if there are ever multiple threads that should be killed

    print "\nProgram is terminating."
    #thread.interrupt_main() # kills main & all daemon threads
    os._exit(status)

def setGrnd():
    # This sets the grnd global variable
    try:
        f = open(GRND_FILE, 'r')
        grndString = f.read()
        f.close()
        lines = grndString.split('\n')
        global grnd
        grnd = ephem.Observer()
        g_long = float(lines[0])
        g_lat =  float(lines[1])
        g_elev = float(lines[2])

        # Check for invalid values
        deg180 = 180 * ephem.degree
        deg90 = 90 * ephem.degree
        if g_long > deg180 or g_long < -1 * deg180:
            return 1
        if g_lat > deg90 or g_lat < -1 * deg90:
            return 1
        if g_elev < 0 or g_elev > 8848: # height of Mt. Everest
            return 1
        grnd.long = g_long
        grnd.lat =  g_lat
        grnd.elev = g_elev
        return 0
    except:
        # Error, so we need to rewrite grnd file
        return 2

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


## Installs user data on the system
## Creates the directory and asks for input for ground observer info
def installProgram():

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



## returns True if issTracker.py appears to be installed correctly
def isInstalled():

    dirExistsCmd = "test -d " + DATA_DIR
    if os.system(dirExistsCmd) != 0:
        return False


    grndExistsCmd = "test -f " + GRND_FILE
    if os.system(grndExistsCmd) != 0:
        return False


    return True


## Adjusts time forward, backward, or resets it to current time
def handleTime(argv):
    # parse further
    argc = len(argv)
    p = "" # first (primary)
    s = "" # second
    t = "" # third
    adjuster = ZERO_TUPLE
    if argc > 1:
        # check for single-argument commands
        p = argv[1]
        if matches(p,"reset"):
            print "Time is reset to now"
            global displacement
            displacement = ZERO_TUPLE
            global is_frozen
            is_frozen = False
            return
        if matches(p,"freeze") or matches(p,"frozen"):
            print "Time is now frozen. Use 'unfreeze' to undo this."
            is_frozen = True
            return
        if matches(p,"unfreeze"):
            print "Time is now unfrozen."
            is_frozen = False
            return
    if argc > 2:
        s = argv[2]
        try:
            s = int(s)
        except:
            return

        adj_list = list(adjuster)
        if matches(p,"Year") or matches(p,"year"):
            adj_list[0] = s
        if matches(p,"Month"):
            adj_list[1] = s
        if matches(p,"Day") or matches(p,"day"):
            adj_list[2] = s
        if matches(p,"hour") or matches(p,"Hour"):
            adj_list[3] = s
        if matches(p,"minute"):
            adj_list[4] = s
        if matches(p,"second") or matches(p,"Second"):
            adj_list[5] = s

        adjuster = tuple(adj_list)

    # now adjust displacement
    adjuster = tuple(sum(k) for k in zip(displacement,adjuster) )

    displacement = adjuster
    return


## Prints output for user's groundstation
def outputGrnd():
    g_long = grnd.long
    g_lat = grnd.lat
    g_elev = grnd.elev

    print "Printing info for your ground observer:"
    print "long:", COL_BLUE, g_long, COL_NORMAL
    print "lat: ", COL_BLUE, g_lat,  COL_NORMAL
    print "elev:", g_elev
    return

## Prints output the satellite
def outputSat():

    s_name = iss.name
    s_long = iss.sublong
    s_lat = iss.sublat
    s_az = iss.az
    s_alt = iss.alt
    s_elev = iss.elevation
    pass_tuple = grnd.next_pass(iss)
    timeOfPass = ephem.localtime(pass_tuple[0])
    setTime = ephem.localtime(pass_tuple[2])
    print s_name
    print "long:", COL_GREEN, s_long, COL_NORMAL
    print "lat: ", COL_GREEN, s_lat,  COL_NORMAL
    print "azimuth:", s_az
    print "altitude:", s_alt
    print "elevation:", s_elev
    print "next pass at" + COL_YELLOW, timeOfPass, COL_NORMAL + "local time"
    print "end time:   " + COL_YELLOW, setTime, COL_NORMAL
    return

## By default, it prints the current time in UTC and local time
## This will print the time being tracked by the program if the user has
## adjusted the time forward or backward
def outputNow():
    #now = ephem.now().tuple()
    #time = tuple(sum(x) for x in zip(now,displacement) )
    #e_time = ephem.Date(time)
    e_time = ephem.Date(p_time)
    print "Current time is", COL_YELLOW, e_time, COL_NORMAL + "UTC"
    print "Current time is", COL_YELLOW, ephem.localtime(e_time), COL_NORMAL+ "local time"
    return

## Updates the program's TLEs for satellites. It saves them on disc
## Looks in the current directory for the TLE file
def updateTLE():

    # fetch the webpage first
    response = urllib2.urlopen(TLE_URL)

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


## This is the function that updates the satellite object's position info
def updateSat():
    try:
        while 1:
            if is_frozen == False:
                now = ephem.now().tuple()
                global p_time
                p_time = tuple(sum(k) for k in zip(now,displacement) )
                grnd.date = p_time

            iss.compute(grnd)
            time.sleep(REFRESH_TIME)
    except:
        exit(0)


## Takes two strings and returns True if one is a substring of the other
## and begins at the first character of the string.
def matches(a, b):

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


## Outputs help info when the user inputs "help" at the command line
def usage():
    HELP_MSG="""
To enter a command to issTracker, enter one or more characters at the start
of the desired command option.

issTracker command prompt options:

quit                             This quits the application cleanly
help                             This displays this help message
clear                            Clear the screen
update                           Update the ISS TLE automatically
grnd, ground                     Display ground station information
now                              Display the current time in UTC
change                           Enter new ground station information
time [YMDhms] <int>              Increase or decrease time by <int> Years,
                                 Months, Days, hours, minutes, seconds
time reset                       Reset time to current time
print (or simply hitting enter)  Display ISS location and time of next pass
"""
    print HELP_MSG
    return


## Creates a command line within the program
def prompt():
    try:
        while 1:
            text = raw_input("\nPress enter to see values, q to quit: ")
            key_list = []
            key = ""
            if text != "":
                key_list = text.split()
                key = key_list[0]

            if matches(key,"quit") or key == "Q" or key == ";q" or key == "exit":
                killProgram(0)
                sys.exit(0) # redundant, but safe
            elif matches(key,"help") or key == "--help":
                usage()
            elif matches(key,"clear") or key == "cls":
                os.system('clear');
            elif matches(key,"update"):
                updateTLE()
                print "Update is complete"
            elif matches(key,"grnd") or key == "ground":
                outputGrnd()
            elif matches(key,"now"):
                outputNow()
            elif matches(key,"change"):
                updateGrnd()
                ret = setGrnd()
                if ret == 0:
                    print "Your update of ground station info is complete."
                    outputGrnd()
                else:
                    print "It appears there was an error with your grnd values."
                    killProgram(1)
            elif matches(key,"time"):
                handleTime(key_list)

            else:
                outputSat()
    except:
        exit(0)



def main():

    # Check if installed
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
    while True:
        ret = setGrnd()
        if ret == 0:
            break
        else:
            # there was an error with the file format or the file did not exist
            print COL_RED, "Error with grnd file.", COL_NORMAL, "Please update it with valid information."
            updateGrnd()

    # set time
    global p_time
    p_time = ephem.now().tuple()
    global displacement
    displacement = ZERO_TUPLE
    global is_frozen
    is_frozen = False

    # use threading module to spawn new threads
    my_threads = list()
    my_threads.append(threading.Thread(target=updateSat) )
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
