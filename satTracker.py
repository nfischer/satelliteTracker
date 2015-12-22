#!/usr/bin/python


#######################################
## Import modules
#######################################

import datetime
import os
import signal
import sys
import threading
import time
import urllib2
from SunriseSunsetCalculator.sunrise_sunset import SunriseSunset
try:
    import dbus
except ImportError:
    print 'Warning: could not import dbus module'

class Ground(object):
    """Wrapper class for the pyephem ground observer object"""
    def __init__(self, longitude, latitude, elevation, offset=0):
        self.observer = ephem.Observer()
        deg180 = 180 * ephem.degree
        deg90 = 90 * ephem.degree
        if longitude > deg180 or longitude < -1 * deg180:
            raise ValueError('Invalid longitude')
        if latitude > deg90 or latitude < -1 * deg90:
            raise ValueError('Invalid latitude')
        if elevation < 0 or elevation > 8848: # height of Mt. Everest
            raise ValueError('Invalid elevation')

        # Set the SunriseSunset object
        deg_long = longitude / ephem.degree
        deg_lat = latitude / ephem.degree
        self.ssc = SunriseSunset(dt=datetime.datetime.now(),
                                 longitude=deg_long, latitude=deg_lat,
                                 localOffset=offset)
        self.observer.long = longitude
        self.observer.lat = latitude
        self.observer.elev = elevation

    # Accessors
    def longitude(self):
        return self.observer.long
    def latitude(self):
        return self.observer.lat
    def elevation(self):
        return self.observer.elev

    def set_date(self, date):
        self.observer.date = date

    def next_pass(self, sat):
        """Wrapper for next_pass() method"""
        return self.observer.next_pass(sat)

    def sunrise_sunset(self, arg=None):
        """
        Wrapper for calculate() method.
        @param: arg can be passed on to the calculate() method
        """
        if arg is None:
            return self.ssc.calculate()
        else:
            return self.ssc.calculate(arg)

def handle_dependencies():
    """Installs dependencies for the project (related to self-installer)"""

    returner = 0

    lin_install = """
    sudo apt-get install python-pip
    sudo apt-get install python-dev
    sudo pip install pyephem
    """

    # Brew may be the necessary form of installation, depending on which install
    # of python is used
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

def clear_screen():
    """Utility to clear the terminal screen"""
    if os.name == 'posix':
        os.system('clear')
    else:
        os.system('cls')

DATA_DIR = os.path.join(os.path.expanduser('~'), '.satTracker')
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
grnd = None
sat = None
displacement = None
is_frozen = None
p_time = None

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

def sig_handler(_signumber, _frame):
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
    """Load the most recently tracked satellite into memory"""
    with open(CURRENT_SAT_FILE, 'r') as fname:
        vals = fname.read().split('\n')
        full_name = vals[0]
        short_name = vals[1]
    return (full_name, short_name)

def save_current(full_name, short_name):
    """Save the currently tracked satellite into persistent storage"""
    with open(CURRENT_SAT_FILE, 'w') as fname:
        fname.write('\n'.join([full_name, short_name, '']))

def set_grnd():
    """This sets the grnd global variable from persistent storage"""
    try:
        with open(GRND_FILE, 'r') as fname:
            lines = fname.read().split('\n')
        g_long = float(lines[0])
        g_lat = float(lines[1])
        g_elev = float(lines[2])
        offset = float(lines[3])
    except (IOError, IndexError, ValueError):
        raise ValueError('Improperly formatted ground file')

    global grnd
    grnd = Ground(g_long, g_lat, g_elev, offset)

def update_grnd():
    """This allows users to change the ground station information"""

    print 'Please enter information for your ground observer:'
    print 'Leave a line blank to use the default value (for O.C.).'
    u_long = raw_input('Longitude (degrees): ')
    u_lat = raw_input('Latitude (degrees): ')
    u_elev = raw_input('Elevation (m): ')
    u_tzn  = raw_input('Timezone offset: ')

    default_long = -118.45
    default_lat = 34.0665
    default_elev = 95.0
    default_tzn = -8

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

    try:
        u_tzn = float(u_tzn)
    except ValueError:
        u_tzn = default_tzn

    # convert to radians
    u_long = u_long * ephem.degree
    u_lat = u_lat * ephem.degree

    # write values to file
    grnd_str = '\n'.join([str(u_long), str(u_lat), str(u_elev), str(u_tzn), ''])
    print grnd_str
    with open(GRND_FILE, 'w') as fname:
        fname.write(grnd_str)

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

    if not os.path.exists(TLE_FILE):
        try:
            update_tle()
        except (ValueError, urllib2.URLError):
            print 'Unable to download a TLE. Check your network connection'
            exit(1)

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
    fst = argv[1]
    if argc == 2:
        # check for single-argument commands
        if matches(fst, 'reset'):
            print "Time is reset to 'now'"
            global displacement
            displacement = ZERO_TUPLE
            global is_frozen
            is_frozen = False
        elif matches(fst, 'freeze') or matches(fst, 'frozen'):
            is_frozen = True
            print "Time is now frozen. Use 'time unfreeze' to undo this."
        elif matches(fst, 'unfreeze'):
            is_frozen = False
            print 'Time is now unfrozen.'
        else:
            print "Unknown time argument '%s'" % fst
        return
    elif argc > 2:
        scnd = argv[2]
        try:
            scnd = int(scnd)
        except ValueError:
            return

        adj_list = list(adjuster)
        if matches(fst, 'Year') or matches(fst, 'year'):
            adj_list[0] = scnd
        elif matches(fst, 'Month'):
            adj_list[1] = scnd
        elif matches(fst, 'Day') or matches(fst, 'day'):
            adj_list[2] = scnd
        elif matches(fst, 'hour') or matches(fst, 'Hour'):
            adj_list[3] = scnd
        elif matches(fst, 'minute'):
            adj_list[4] = scnd
        elif matches(fst, 'second') or matches(fst, 'Second'):
            adj_list[5] = scnd

        adjuster = tuple(adj_list)

    # now adjust displacement
    displacement = tuple(sum(k) for k in zip(displacement, adjuster))
    return


def output_grnd():
    """Prints output for user's groundstation"""
    g_long = grnd.longitude()
    g_lat = grnd.latitude()
    g_elev = grnd.elevation()

    print 'Printing info for your ground observer:'
    print 'long:' + COL_BLUE, g_long, COL_NORMAL
    print 'lat: ' + COL_BLUE, g_lat, COL_NORMAL
    print 'elev:', g_elev
    return

def output_sat():
    """Prints output for the satellite"""

    # sat.compute(grnd.observer)
    s_name = sat.name
    s_long = sat.sublong
    s_lat = sat.sublat
    s_az = sat.az
    s_alt = sat.alt
    s_elev = sat.elevation
    try:
        pass_tuple = grnd.next_pass(sat)
        time_of_pass = ephem.localtime(pass_tuple[0]).replace(microsecond=0)
        set_time = ephem.localtime(pass_tuple[4]).replace(microsecond=0)
        rise_dt, set_dt = grnd.sunrise_sunset(time_of_pass)
        night_time = (time_of_pass < rise_dt or time_of_pass > set_dt)
        print rise_dt, set_dt
    except ValueError:
        time_of_pass = None
        set_time = None
        night_time = False
    print s_name
    print 'long:', COL_GREEN, s_long, COL_NORMAL
    print 'lat: ', COL_GREEN, s_lat, COL_NORMAL
    print 'azimuth:', s_az
    print 'altitude:', s_alt
    print 'elevation:', s_elev
    if time_of_pass is not None:
        suffix = 'local time ' + ('(night)' if night_time else '(day time)')
        print 'next pass at' + COL_YELLOW, time_of_pass, COL_NORMAL + suffix
        print 'end time:   ' + COL_YELLOW, set_time, COL_NORMAL
    else:
        print COL_PURPLE + 'This satellite will never pass' + COL_NORMAL
    return

def set_satellite(full_name, nick_name=''):
    with open(TLE_FILE, 'r') as fname:
        lines = fname.read().split('\n')
    counter = 0
    my_lines = list()
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

    sat_name = full_name if nick_name == '' else nick_name

    # May throw an exception
    ret = ephem.readtle(sat_name, my_lines[1], my_lines[2])
    save_current(full_name, nick_name)

    global sat
    sat = ret
    global grnd

def output_now():
    """
    By default, it prints the current time in UTC and local time This will
    print the time being tracked by the program if the user has adjusted the
    time forward or backward
    """
    e_time = ephem.Date(p_time)
    l_time = ephem.localtime(e_time).replace(microsecond=0)
    cti = 'Current time is'+COL_YELLOW
    print cti, l_time, COL_NORMAL + 'local time'
    print cti, e_time, COL_NORMAL + 'UTC'
    return

def update_tle():
    """
    Updates the program's TLEs for satellites

    @throws ValueError, urllib2.URLError
    """

    # fetch the raw data

    # May throw ValueError or urllib2.URLError
    response = urllib2.urlopen(TLE_URL)

    if response.getcode() != 200:
        raise ValueError('Could not update TLE: status was %d' % response.getcode())
    if response.geturl() != TLE_URL:
        raise ValueError('URL was redirected')
    raw_text = response.read() # returns a string

    # write the data to file
    formatted_text = '\n'.join([k.strip() for k in raw_text.split('\n')])
    with open(TLE_FILE, 'w') as fname:
        fname.write(formatted_text)
    return

def all_stations():
    """Returns a list of all known space stations"""
    with open(TLE_FILE, 'r') as fname:
        lines = fname.read().split('\n')
    ret_lines = list()
    lines.pop() # Take off trailing newline
    ret_lines = lines[::3] # Every third line

    # ret_lines is now all lines containing satellite names
    return ret_lines

def update_sat():
    """This is the function that updates the satellite object's position info"""
    try:
        has_shown_pass = 0
        while 1:
            if is_frozen == False:
                now = ephem.now().tuple()
                global p_time
                p_time = tuple(sum(k) for k in zip(now, displacement))
                grnd.set_date(p_time)

            global sat
            sat.compute(grnd.observer)
            try:
                my_pass_tuple = grnd.next_pass(sat)
                start_time = ephem.localtime(my_pass_tuple[0])
                end_time = ephem.localtime(my_pass_tuple[4])
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
            except ValueError:
                # satellite is always below the horizon
                pass

            time.sleep(REFRESH_TIME)
    except Exception as e:
        print type(e)
        print e
        kill_program(1)

# def cron_daemon():
#     """
#     This loads all saved cron jobs, checks if jobs needs to be run, and then
#     waits to run jobs when their deadline comes
#     """
#     # Load in cron jobs from disk
#     if os.path.exists(CRON_FILE):
#         with open(CRON_FILE, 'r') as fname:
#             job_text = fname.read()
#         my_jobs = job_text.split('\n')
#     # print 'Jobs are loaded'
#     # Loop for new jobs
#     while True:
#         # Check jobs
#         time.sleep(1)
#     return

def matches(str1, str2):
    """
    Takes two strings and returns True if one is a prefix of the other
    """

    len1 = len(str1)
    len2 = len(str2)

    if len1 == 0 or len2 == 0:
        # empty string should return false always
        return False

    if len1 < len2:
        return str1 == str2[0:len1]
    else:
        return str2 == str1[0:len2]

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
list_stations                     Display the station list
choose_station <satellite-name>   Change the station to a different space
                                  station in the station list
"""
    return

def prompt():
    """Creates a command line within the program"""
    try:
        while 1:
            text = raw_input('\nPress enter to see values, q to quit: ')
            key_list = list()
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
                clear_screen()
            elif matches(key, 'update'):
                try:
                    print 'Updating your TLE...'
                    update_tle()
                    print 'Successfully updated your TLE!'
                except (ValueError, urllib2.URLError):
                    print 'Unable to update TLE. Check your network connection'
            elif matches(key, 'grnd') or key == 'ground':
                output_grnd()
            elif matches(key, 'choose_station'):
                if len(key_list) < 2:
                    print 'Must specify a station to change to'
                    continue
                my_sat = ' '.join(key_list[1:])
                nick_name = None
                for station in all_stations():
                    if my_sat == station:
                        print 'Switching to satellite %s' % station
                        nick_name = raw_input('Enter a short name: ')
                        set_satellite(station, nick_name)
                        break
                if nick_name is None:
                    print 'Unable to find a satellite named "%s"' % my_sat
            elif matches(key, 'list_stations'):
                for k in all_stations():
                    print k
            elif matches(key, 'now'):
                output_now()
            elif matches(key, 'change'):
                update_grnd()
                try:
                    set_grnd()
                    print 'Your update of ground station info is complete.'
                    output_grnd()
                except ValueError:
                    print 'It appears there was an error with your grnd values.'
                    kill_program(1)
            elif matches(key, 'time'):
                handle_time(key_list)

            else:
                output_sat()
    except Exception as e:
        print type(e)
        print e
        kill_program(1)



def main():
    """The main function"""

    # Check if installed
    if not is_installed():
        install_program()

    ## initialize satellite info
    stamp = datetime.datetime.fromtimestamp(os.stat(TLE_FILE)[8])
    delta = datetime.timedelta(days=3)

    if datetime.datetime.now() > (stamp + delta):
        # TLE is old
        msg = ('Your TLE is getting a little stale. Would you like to update '
               'it? (y/n) ')
        resp = raw_input(msg)
        if resp == 'y':
            try:
                update_tle()
            except (ValueError, urllib2.URLError):
                print 'Unable to update TLE. Continuing anyway with old values'

    # read in last satellite viewed
    try:
        full_name, short_name = get_current()
    except (IOError, IndexError):
        print 'Unable to find your satellite, defaulting to ISS'
        save_current(ISS_FULL_NAME, ISS_NICKNAME)

    # pull the TLE from disc
    try:
        full_name, short_name = get_current()
        set_satellite(full_name, short_name)
    except (IOError, ValueError):
        # there was an error with the file format or the file did not exist
        try:
            update_tle()
        except (ValueError, urllib2.URLError):
            kill_program(1)

        try:
            full_name, short_name = get_current()
            set_satellite(full_name, short_name)
        except ValueError:
            try:
                full_name = ISS_FULL_NAME
                short_name = ISS_NICKNAME
                set_satellite(full_name, short_name)
            except:
                kill_program(1)

    ## set up ground station information
    try:
        set_grnd()
    except ValueError:
        # there was an error with the file format or the file did not exist
        msg = (COL_RED + 'Error with ground file. ' + COL_NORMAL +
               'Please update it with valid information.')
        print msg
        update_grnd()
        try:
            set_grnd()
        except:
            print 'Unable to load valid ground information'
            exit(1)

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
    # my_threads.append(threading.Thread(target=cron_daemon))
    my_threads.append(threading.Thread(target=prompt))
    my_threads[0].daemon = True # run this thread in the background
    # my_threads[1].daemon = True # run this thread in the background
    my_threads[1].daemon = False
    for thread in my_threads:
        thread.start()

    while True:
        time.sleep(100)

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
