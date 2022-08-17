#!/usr/bin/env python3

# This daemon has a watchdog and a main loop
# The script is supposed to be invoked by cron every 1 minute
# During each invocation, if the watchdog find bus_daemon.py is not running
# or there are no recent points (within 1 minute) in the history
# assume the daemon is dead, kill it and restart it

# data is saved at scriptdir/deviceid/


import os,yaml,struct,subprocess, tempfile, time,logging,socket, sys,json
import pathlib
from datetime import datetime
from TrackingMessage import TrackingMessage

sys.stderr = open(os.devnull, "w")
import psutil
# after importing, set stderr to original
sys.stderr = sys.__stderr__

def readLastCompleteLog(filename):
    message_size = struct.calcsize(TrackingMessage.STRUCT_FORMAT)
    size = os.path.getsize(filename)
    if size < message_size:
        return None
    else:
        record_offset = message_size * (size//message_size-1)
        with open(filename,'rb') as f:
            f.seek(record_offset)
            buf = f.read(message_size)
            msg = TrackingMessage.decode(buf)
            return msg

def changeToScriptDir():
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

def readConfiguration():

    assert os.path.realpath(os.path.dirname(os.path.realpath(__file__)))==os.path.realpath(os.getcwd())
    if os.path.exists('config.yml'):
        with open('config.yml', 'r') as file:
            conf = yaml.safe_load(file)
    else:
        # development mode and default value
        conf = {'id':os.urandom(4).hex(),'interval':5.0,'server':'192.168.230.27','port':5200}
        with open('config.yml', 'w') as file:
            yaml.dump(conf,file)
    return conf


PID_FILE = tempfile.gettempdir() + "/bus_daemon.pid"


def watchdog():  # return True if service need restart, false if service don't need restart
    conf = readConfiguration()
    # check if process exist in memory
    my_pid = os.getpid()
    if os.path.isfile(PID_FILE):
        # check if the PID exists in the current process list
        try:
            pid_in_file = int(open(PID_FILE).read())
            current_pids = psutil.pids()
            if pid_in_file in current_pids:

                # check if location is up-to-date (within the last 2 minutes)
                track_file_path = conf['id'] + '/track'
                # read the last complete record from track file
                msg = readLastCompleteLog(track_file_path)

                if msg is None or msg.timestamp<TrackingMessage.getTimestampOfNow()-120:
                    # if the last tracking is more than 120 seconds old
                    # kill the pid and restart
                    psutil.Process(pid_in_file).kill()
                else:
                    return False

        except ValueError: # reading error on pid file
            # kill any process that is not myself, but have the same command line invoking of myself

            my_cmd = psutil.Process(my_pid).cmdline()

            for proc in psutil.process_iter():
                try:
                    if proc.cmdline()==my_cmd and proc.pid!=my_pid:
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

    open(PID_FILE,'w').write(repr(my_pid))

    return True

def trimTrackFile(track_path):
    message_size = TrackingMessage.getMessageSize()

    file_size = os.path.getsize(track_path)

    if file_size % message_size != 0:
        fd = os.open(track_path, os.O_RDWR | os.O_EXLOCK)
        os.ftruncate(fd, message_size*(file_size//message_size))
        os.close(fd)


if __name__ == '__main__':
    gps_cmd = 'termux-location -p gps'
    network_cmd = 'termux-location -p network'

    restart = watchdog()
    if not restart:
        exit(0)

    conf = readConfiguration()

    logging.basicConfig()

    track_path = conf['id']+'/track'

    if not os.path.exists(conf['id']):
        os.mkdir(conf['id'])
    if not os.path.exists(track_path):
        pathlib.Path(track_path).touch()

    # make sure message file length is integer times of 64 bytes
    trimTrackFile(track_path)

    f_track = open(track_path, 'ab', buffering=0)

    sock = socket.socket(socket.AF_INET, # Internet
                         socket.SOCK_DGRAM) # UDP


    while True:

        cycle_begin_time = datetime.utcnow()

        # start 2 processes to get the location, using gps and network
        popen_network_location = subprocess.Popen(network_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        try:
            json_location = subprocess.check_output(gps_cmd, shell=True, timeout=conf['interval'])

        except subprocess.TimeoutExpired as e:
            try:
                out, err = popen_network_location.communicate(timeout=conf['interval'])
                json_location = out
            except subprocess.TimeoutExpired as e2:
                popen_network_location.kill()
                print("termux-location failed for both GPS and network")
                continue

        try:
            termux_location = json.loads(json_location)
        except json.decoder.JSONDecodeError as e:
            print("termux-location failed for both GPS and network")
            continue

        # make the message and append it to log
        msg = TrackingMessage.fromTermuxLocation(int(conf['id'], 16), termux_location)
        msg_bytes = msg.encode()
        f_track.write(msg_bytes)

        # send the message to server
        sock.sendto(msg_bytes, (conf['server'], conf['port']))

        time_elapsed = (datetime.utcnow() - cycle_begin_time).total_seconds()

        sleep_time = conf['interval'] - time_elapsed
        if sleep_time>0:
            time.sleep(sleep_time)



