"""
Usage:
    kamvas
        [ -t=<val> | --evdev-test=<val> ]
        [ -u | --print-usb-events ]
        [ -c | --create-default-config ]
    kamvas start
        [ -a=<val> | --action=<val> ]
        [ -o | --print-driver-output ]
    kamvas stop
    kamvas status

Options:
    -a=<val>, --action-<val>
        Define which group of button mappings you want to use.
        The button mappings are defined in {config_path}.
        If this is not provided then the script will try to use
        default_action from the config file.
    -t=<val>, --evdev-test=<val> 
        Print out all the events that happen on your system for
        a given event file. The event files are usually located
        in `/dev/input/` directory. This usually required sudo
        access
    -u, --print-usb-events
        Prints out add, remove and bind events for any USB devices
        on your system. Use this to observe data about your device
        that might be needed in the config if it isn't working for
        you.
    -c, --create-default-config
        Create a default config file at {config_path}
        if it doesn't already exist
    -o, --print-driver-output
        The driver's stdout and stderr messages are suppressed
        by default. Use this to allow the driver to print to
        your console. Note that driver output would get printed
        at any time because the driver runs as a separate
        process
"""

from __future__ import print_function
from pprint import pprint
import os
import sys
import shutil
import subprocess
import json
import time

from pyudev import Context, Monitor, MonitorObserver
from docopt import docopt
import evdev
import usb.core
import yaml
import psutil
from elevate import elevate

# CONSTANTS ---------------------------------------------------------------------------------------

CONFIG_PATH = os.path.expanduser('~/.kamvas_config.yaml')
DEFAULT_CONFIG_PATH = 'driver/config.yaml'

DRIVER_SCRIPT = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'kamvas_driver.py')

# HELPRES -----------------------------------------------------------------------------------------

def load_config(action=''):
    if not os.path.isfile(CONFIG_PATH):
        raise Exception('Config file not found at {}. Create one using "kamvas -c"'.format(
            CONFIG_PATH
        ))

    with open(CONFIG_PATH, 'r') as yaml_file:
        config = yaml.safe_load(yaml_file)

        # Try to get the default action from the config
        if not action:
            action = config.get('default_action', '')

        # If the default_action was also not available then throw an error
        if not action:
            raise Exception("You either need to define a 'default_action' in your config or use the 'kamvas -a' option to specify an action")
        
        config['actions'] = config['actions'][action]
        return config

def driver_is_running():
    for process in psutil.process_iter():
        cmdline = process.cmdline()
        if len(cmdline) < 3:
            continue

        if cmdline[2] == DRIVER_SCRIPT:
            return True
    else:
        return False

# HANDLERS ----------------------------------------------------------------------------------------

def handle_start():
    if driver_is_running():
        print('Driver is already running')
        return

    config = load_config()

    # We need to run this as sudo because we can only have have access to USB as sudo
    commands = [
        'sudo',
        'python',
        DRIVER_SCRIPT,
        config['xinput_name'],
        str(config['vendor_id']),
        str(config['product_id']),
        json.dumps(config['pen']),
        json.dumps(config['actions']),
    ]

    if not args['--print-driver-output']:
        commands.append('-q')

    if config.get('default_display', ''):
        commands.append('-d')
        commands.append(config['default_display'])

    subprocess.Popen(commands)
    print('Driver started')

def handle_stop():
    # We will need sudo privileges to stop the driver because it was started as sudo
    if os.getuid != 0:
        elevate(graphical=False)

    for process in psutil.process_iter():
        cmdline = process.cmdline()
        if len(cmdline) < 3:
            continue

        if cmdline[2] == DRIVER_SCRIPT:
            print('Process found. Terminating it.')
            process.terminate()
            break
    else:
        print('Process not found: It is already dead')

def handle_status():
    if driver_is_running():
        print('Driver is currently running')
    else:
        print('Driver is currently NOT running')

def handle_evdev_test(event_path):
    # We will need sudo privileges to access the event files
    if os.getuid != 0:
        elevate(graphical=False)

    try:
        dev = evdev.InputDevice(event_path)
        if not dev:
            raise Exception("could not find device. The device may already be open")
        
        for event in dev.read_loop():
            if event.type == evdev.ecodes.EV_KEY:
                print(evdev.categorize(event))
    except Exception as e:
        print(e, file=sys.stderr)
    except KeyboardInterrupt:
        print('Exiting')
        exit()

def handle_create_default_config():
    if os.path.isfile(CONFIG_PATH):
        print('New config not created. Config file already exists at {}.'.format(CONFIG_PATH))
        return

    shutil.copyfile(DEFAULT_CONFIG_PATH, CONFIG_PATH)
    print('New config file created at {}'.format(CONFIG_PATH))

def handle_print_usb_events():
    def print_usb_events(action, device):
        string_to_print = '{} - {}'.format(action, device)
        for key in device.keys():
            string_to_print += '\n    {}: {}'.format(key, device.get(key, ''))
        print(string_to_print)

    # Setup the code for monitoring USB events
    context = Context()
    monitor = Monitor.from_netlink(context)
    monitor.filter_by(subsystem='usb')

    observer = MonitorObserver(monitor, print_usb_events, name='kamvas-usb-monitor')

    # This is needed to prevent the main thread from finishing which would close the process
    # and nothing will be displayed
    observer.daemon = False

    # Start monitoring USB events asynchronously
    observer.start()

# MAIN --------------------------------------------------------------------------------------------

def run_main():
    global args
    args = docopt(__doc__.format(
        config_path=CONFIG_PATH
    ))

    if args['start']:
        if not driver_is_running():
            handle_start()
        else:
            print('Driver is currently running. Stop it before starting it.')
        return

    if args['stop']:
        handle_stop()
        return

    if args['status']:
        handle_status()
        return

    if args['--evdev-test']:
        handle_evdev_test(args['--evdev-test'])
        return

    if args['--create-default-config']:
        handle_create_default_config()
        return

    if args['--print-usb-events']:
        handle_print_usb_events()
        return

    print(__doc__)

if __name__ == '__main__':
    run_main()
