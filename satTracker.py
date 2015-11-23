#!/usr/bin/python


#######################################
## Import modules
#######################################

import datetime
import dbus
import os
import signal
import sys
import threading
import time
import urllib2


def handle_dependencies():
    """Installs dependencies for the project (related to self-installer)"""

    returner = 0

    lin_install = """
    sudo apt-get install python-pip
    sudo apt-get install python-dev
    sudo pip install pyephem
    """
    mac_install = """
    sudo easy_install pip
    sudo pip install pyephem
    """

    install_cmds = lin_install # default
    print "You don't have pyephem installed!"
    print 'Install it like so:'
    if sys.platform == 'linux' or sys.platform == 'linux2':
        print lin_install
        install_cmds = lin_install
    elif sys.platform == 'darwin':
        print mac_install
        install_cmds = mac_install
    else:
        print 'Your system is not currently supported, so it may not work.'
        print 'Try:\nsudo pip install pyephem'
        return returner

    msg = ('Would you like this program to install these dependencies for you? '
           '(y/n) ')
    resp = raw_input(msg)
    if resp == 'y':
        if os.system('which pip >/dev/null 2>&1') == 0:
            # pip is already installed
            cmd = 'sudo pip install pyephem'
            print cmd
            result = os.system(cmd)
            if result != 0:
                print 'There was some failure with the command'
                returner = result

        else:
            for cmd in install_cmds.split('\n'):
                print cmd
                result = os.system(cmd)
                if result != 0:
                    print 'There was some failure with the command'
                    returner = result

    return returner

try:
    import ephem
except ImportError:
    RET = handle_dependencies()
    exit(RET)

## Global 'constants'
REFRESH_TIME = 1 # in seconds
TLE_URL = 'http://www.celestrak.com/NORAD/elements/stations.txt'
ZERO_TUPLE = (0, 0, 0, 0, 0, 0)
ISS_FULL_NAME = 'ISS (ZARYA)'
ISS_NICKNAME = 'ISS'

def get_home_dir():
    """Return the user's home directory"""
    return os.path.expanduser('~')

DATA_DIR = os.path.join(get_home_dir(), '.satTracker')
TLE_FILE = os.path.join(DATA_DIR, 'tles.txt')
GRND_FILE = os.path.join(DATA_DIR, 'grnd.txt')
CRON_FILE = os.path.join(DATA_DIR, 'cron.txt')
CURRENT_SAT_FILE = os.path.join(DATA_DIR, 'current.txt')

## Colors
COL_NORMAL = '\033[0m'
COL_GREY = '\033[90m'
COL_RED = '\033[91m'
COL_GREEN = '\033[92m'
COL_YELLOW = '\033[93m'
COL_BLUE = '\033[94m'
COL_PURPLE = '\033[95m'
COL_CYAN = '\033[96m'
COL_WHITE = '\033[97m'

## Global variables
# grnd
# sat
# displacement
# is_frozen
# p_time

#######################################
## Functions
#######################################

def kill_program(status):
    """
    This is the function that should be called to kill the program cleanly
    if there are ever multiple threads that should be killed
    """

    print '\nProgram is terminating.'
    # kills main & all daemon threads
    os._exit(status)

def sig_handler(signumber, frame):
    kill_program(0)

def notify(summary, body='', app_name='', app_icon='',
           timeout=3000, actions=[], hints=[], replaces_id=0):
    """Send a system notification"""
    _bus_name = 'org.freedesktop.Notifications'
    _object_path = '/org/freedesktop/Notifications'
    _interface_name = _bus_name

    session_bus = dbus.SessionBus()
    obj = session_bus.get_object(_bus_name, _object_path)
    interface = dbus.Interface(obj, _interface_name)
    interface.Notify(app_name, replaces_id, app_icon,
                     summary, body, actions, hints, timeout)

def get_current():
    with open(CURRENT_SAT_FILE, 'r') as fname:
        vals = fname.read().split('\n')
        full_name = vals[0]
        short_name = vals[1]
    return (full_name, short_name)

def save_current(full_name, short_name):
    with open(CURRENT_SAT_FILE, 'w') as fname:
        fname.write('\n'.join([full_name, short_name]))

def set_grnd():
    """
    This sets the grnd global variable
    """
    try:
        with open(GRND_FILE, 'r') as fname:
            grnd_string = fname.read()
        lines = grnd_string.split('\n')
        global grnd
        grnd = ephem.Observer()
        g_long = float(lines[0])
        g_lat = float(lines[1])
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
        grnd.lat = g_lat
        grnd.elev = g_elev
        return 0
    except:
        # Error, so we need to rewrite grnd file
        return 2

def update_grnd():
    """This allows users to change the ground station information"""

    print 'Please enter information for your ground observer:'
    print 'Leave a line blank to use the default value (for O.C.).'
    u_long = raw_input('Longitude (degrees): ')
    u_lat = raw_input('Latitude (degrees): ')
    u_elev = raw_input('Elevation (m): ')

    default_long = -118.45
    default_lat = 34.0665
    default_elev = 95.0

    # set values
    try:
        u_long = float(u_long)
    except ValueError:
        u_long = default_long

    try:
        u_lat = float(u_lat)
    except ValueError:
        u_lat = default_lat

    try:
        u_elev = float(u_elev)
    except ValueError:
        u_elev = default_elev



    # check validity of values & their types
    if u_elev < 0:
        u_elev = default_elev


    # convert to radians
    u_long = u_long * ephem.degree
    u_lat = u_lat * ephem.degree

    # write values to file
    values = [str(u_long), str(u_lat), str(u_elev), '']
    grnd_string = '\n'.join(values)

    with open(GRND_FILE, 'w') as fname:
        fname.write(grnd_string)

    return


def install_program():
    """
    Installs user data on the system.
    Creates the directory and asks for input for ground observer info.
    """

    print """
    Would you like to allow issTracker to install on your computer?

    It will create on your computer:

    - a file to save TLE info for your satellites
    - a file to save longitude and latitude for your ground station
    - a directory within your home directory where these files will be saved

    """

    decision = raw_input('Do you want to install issTracker? (y/n): ')
    if decision != 'y':
        print 'Not installing. Terminating issTracker.'
        exit(1)

    print '\nInstalling issTracker\n'

    # make the directory
    if not os.path.isdir(DATA_DIR):
        try:
            os.mkdir(DATA_DIR)
        except OSError:
            print 'There was an error installing the program.'
            exit(1)

    if not os.path.exists(GRND_FILE):
        update_grnd()

    if not os.path.exists(CURRENT_SAT_FILE):
        save_current(ISS_FULL_NAME, ISS_NICKNAME)

    return


def is_installed():
    """returns True if issTracker.py appears to be installed correctly"""

    return os.path.isdir(DATA_DIR) and os.path.exists(GRND_FILE)


def handle_time(argv):
    """Adjusts time forward, backward, or resets it to current time"""
    argc = len(argv)
    adjuster = ZERO_TUPLE
    if argc > 1:
        # check for single-argument commands
        fst = argv[1]
        if matches(fst, 'reset'):
            print 'Time is reset to now'
            global displacement
            displacement = ZERO_TUPLE
            global is_frozen
            is_frozen = False
            return
        if matches(fst, 'freeze') or matches(fst, 'frozen'):
            print "Time is now frozen. Use 'unfreeze' to undo this."
            is_frozen = True
            return
        if matches(fst, 'unfreeze'):
            print 'Time is now unfrozen.'
            is_frozen = False
            return
    if argc > 2:
        scnd = argv[2]
        try:
            scnd = int(scnd)
        except ValueError:
            return

        adj_list = list(adjuster)
        if matches(fst, 'Year') or matches(fst, 'year'):
            adj_list[0] = scnd
        if matches(fst, 'Month'):
            adj_list[1] = scnd
        if matches(fst, 'Day') or matches(fst, 'day'):
            adj_list[2] = scnd
        if matches(fst, 'hour') or matches(fst, 'Hour'):
            adj_list[3] = scnd
        if matches(fst, 'minute'):
            adj_list[4] = scnd
        if matches(fst, 'second') or matches(fst, 'Second'):
            adj_list[5] = scnd

        adjuster = tuple(adj_list)

    # now adjust displacement
    adjuster = tuple(sum(k) for k in zip(displacement, adjuster))

    displacement = adjuster
    return


def output_grnd():
    """Prints output for user's groundstation"""
    g_long = grnd.long
    g_lat = grnd.lat
    g_elev = grnd.elev

    print 'Printing info for your ground observer:'
    print 'long:', COL_BLUE, g_long, COL_NORMAL
    print 'lat: ', COL_BLUE, g_lat, COL_NORMAL
    print 'elev:', g_elev
    return

def output_sat():
    """Prints output for the satellite"""

    s_name = sat.name
    s_long = sat.sublong
    s_lat = sat.sublat
    s_az = sat.az
    s_alt = sat.alt
    s_elev = sat.elevation
    pass_tuple = grnd.next_pass(sat)
    time_of_pass = ephem.localtime(pass_tuple[0])
    set_time = ephem.localtime(pass_tuple[2])
    trans_time = pass_tuple[4]
    print s_name
    print 'long:', COL_GREEN, s_long, COL_NORMAL
    print 'lat: ', COL_GREEN, s_lat, COL_NORMAL
    print 'azimuth:', s_az
    print 'altitude:', s_alt
    print 'elevation:', s_elev
    print 'next pass at' + COL_YELLOW, time_of_pass, COL_NORMAL + 'local time'
    print 'end time:   ' + COL_YELLOW, set_time, COL_NORMAL
    print 'transit time:   ' + COL_RED, trans_time, COL_NORMAL
    return

def set_satellite(full_name, nick_name=''):
    with open(TLE_FILE, 'r') as fname:
        lines = fname.read().split('\n')
    counter = 0
    my_lines = []
    for line in lines:
        if matches(full_name, line):
            my_lines.append(line)
            counter = 1
        elif counter > 0 and counter < 3:
            my_lines.append(line)
            counter = counter + 1
        elif counter == 3:
            break

    if len(my_lines) != 3:
        raise ValueError('Unable to find satellite')

    if nick_name != '':
        sat_name = nick_name
    else:
        sat_name = full_name
    sat_name = full_name if nick_name == '' else nick_name

    try:
        ret = ephem.readtle(sat_name, my_lines[1], my_lines[2])
        save_current(full_name, nick_name)
        # with open(CURRENT_SAT_FILE, 'w') as fname:
        #     fname.write('\n'.join([full_name, nick_name]))
    except:
        raise
    return ret

def output_now():
    """
    By default, it prints the current time in UTC and local time This will
    print the time being tracked by the program if the user has adjusted the
    time forward or backward
    """
    e_time = ephem.Date(p_time)
    l_time = ephem.localtime(e_time)
    cti = 'Current time is'+COL_YELLOW
    print cti, e_time, COL_NORMAL + 'UTC'
    print cti, l_time, COL_NORMAL + 'local time'
    return

def update_tle():
    """
    Updates the program's TLEs for satellites
    """

    # fetch the raw data
    try:
        response = urllib2.urlopen(TLE_URL)
    except (ValueError, urllib2.URLError) as e:
        raise ValueError('Could not update TLE: %s' % str(e))

    if response.getcode() != 200:
        raise ValueError('Could not update TLE: status was %d' % response.getcode())
    if response.geturl() != TLE_URL:
        raise ValueError('URL was redirected')
    html_text = response.read() # returns a string

    # write the data to file
    with open(TLE_FILE, 'w') as fname:
        fname.write(html_text)

    return


def update_sat():
    """This is the function that updates the satellite object's position info"""
    try:
        has_shown_pass = 0
        while 1:
            if is_frozen == False:
                now = ephem.now().tuple()
                global p_time
                p_time = tuple(sum(k) for k in zip(now, displacement))
                grnd.date = p_time

            sat.compute(grnd)
            my_pass_tuple = grnd.next_pass(sat)
            start_time = ephem.localtime(my_pass_tuple[0])
            end_time = ephem.localtime(my_pass_tuple[2])
            if start_time > end_time and has_shown_pass == 0:
                # This can only happen if we're in a pass right now
                msg_string = sat.name + ' is currently passing overhead'
                try:
                    notify(msg_string)
                except dbus.DBusException:
                    print msg_string
                has_shown_pass = 1
            elif start_time < end_time and has_shown_pass == 1:
                has_shown_pass = 0

            time.sleep(REFRESH_TIME)
    except:
        exit(0)

def cron_daemon():
    """
    This loads all saved cron jobs, checks if jobs needs to be run, and then
    waits to run jobs when their deadline comes
    """
    # Load in cron jobs from disk
    if os.path.exists(CRON_FILE):
        with open(CRON_FILE, 'r') as fname:
            job_text = fname.read()
        my_jobs = job_text.split('\n')
    # print 'Jobs are loaded'

    # Loop for new jobs
    while True:
        # Check jobs

        # Sleep
        time.sleep(1)

    return

def matches(str1, str2):
    """
    Takes two strings and returns True if one is a prefix of the other
    """

    len1 = len(str1)
    len2 = len(str2)

    if len1 == 0 or len2 == 0:
        # empty string should return false always
        return False

    if len1 > len2:
        # swap them so that str1 is shorter
        tmp = str2
        str2 = str1
        str1 = tmp

    # assume that len1 <= len2
    str2 = str2[0:len1]

    # if str1 & str2 are str1 match, then return true
    return str1 == str2


def usage():
    """Outputs help info when the user inputs 'help' at the command line"""
    print """
To enter a command to issTracker, enter one or more characters at the start
of the desired command option.

issTracker command prompt options:

quit                              This quits the application cleanly
help                              This displays this help message
clear                             Clear the screen
update                            Update the satellites TLE
grnd, ground                      Display ground station information
now                               Display the current time in UTC
change                            Enter new ground station information
time [YMDhms] <int>               Increase or decrease time by <int> Years,
                                  Months, Days, hours, minutes, seconds
time reset                        Reset time to current time
print (or simply hitting enter)   Display satellite location and time of next
                                  pass
"""
    return


def prompt():
    """Creates a command line within the program"""
    try:
        while 1:
            text = raw_input('\nPress enter to see values, q to quit: ')
            key_list = []
            key = ''
            if text != '':
                key_list = text.split()
                key = key_list[0]

            if (matches(key, 'quit') or key == 'Q' or key == ';q' or
                    key == 'exit'):
                kill_program(0)
                sys.exit(0) # redundant, but safe
            elif matches(key, 'help') or key == '--help':
                usage()
            elif matches(key, 'clear') or key == 'cls':
                os.system('clear')
            elif matches(key, 'update'):
                try:
                    update_tle()
                    print 'Update is complete'
                except ValueError:
                    print 'Unable to update TLE'
            elif matches(key, 'grnd') or key == 'ground':
                output_grnd()
            elif matches(key, 'now'):
                output_now()
            elif matches(key, 'change'):
                update_grnd()
                ret = set_grnd()
                if ret == 0:
                    print 'Your update of ground station info is complete.'
                    output_grnd()
                else:
                    print 'It appears there was an error with your grnd values.'
                    kill_program(1)
            elif matches(key, 'time'):
                handle_time(key_list)

            else:
                output_sat()
    except:
        exit(0)



def main():
    """The main function"""

    # Check if installed
    if not is_installed():
        install_program()

    ## initialize satellite info
    stamp = datetime.datetime.fromtimestamp(os.stat(TLE_FILE)[8])
    stamp = stamp + datetime.timedelta(days=3)

    if datetime.datetime.now() > stamp:
        # TLE is old
        msg = ('Your TLE is getting a little stale. Would you like to update '
               'it? (y/n) ')
        resp = raw_input(msg)
        if resp == 'y':
            try:
                update_tle()
            except ValueError as e:
                print str(e)
                kill_program(1)

    # read in default satellite to examine
    try:
        full_name, short_name = get_current()
    except (IOError, IndexError):
        print 'Unable to find your satellite, defaulting to ISS'
        save_current(ISS_FULL_NAME, ISS_NICKNAME)

    # pull the TLE from disc
    try:
        global sat
        full_name, short_name = get_current()
        sat = set_satellite(full_name, short_name)
    except (IOError, ValueError):
        # there was an error with the file format or the file did not exist
        try:
            update_tle()
        except ValueError as e:
            kill_program(1)

        try:
            full_name, short_name = get_current()
            sat = set_satellite(full_name, short_name)
        except ValueError:
            try:
                full_name = ISS_FULL_NAME
                short_name = ISS_NICKNAME
                sat = set_satellite(full_name, short_name)
            except:
                kill_program(1)

    ## set up ground station information
    while True:
        ret = set_grnd()
        if ret == 0:
            break
        else:
            # there was an error with the file format or the file did not exist
            msg = (COL_RED + 'Error with ground file.' + COL_NORMAL +
                   'Please update it with valid information.')
            print msg
            update_grnd()

    # set time
    global p_time
    p_time = ephem.now().tuple()
    global displacement
    displacement = ZERO_TUPLE
    global is_frozen
    is_frozen = False

    # use threading module to spawn new threads
    my_threads = list()
    my_threads.append(threading.Thread(target=update_sat))
    my_threads.append(threading.Thread(target=cron_daemon))
    my_threads.append(threading.Thread(target=prompt))
    my_threads[0].daemon = True # run this thread in the background
    my_threads[1].daemon = True # run this thread in the background
    my_threads[2].daemon = False
    my_threads[0].start()
    my_threads[1].start()
    my_threads[2].start()

    for thread in my_threads:
        while thread.isAlive():
            thread.join(2)

    try:
        while 1:
            pass
        kill_program(0)
    except:
        kill_program(0)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help':
            usage()
            exit(0)

    # Register signal handler
    signal.signal(signal.SIGINT, sig_handler)

    # execute the main function now
    main()

exit(0)
