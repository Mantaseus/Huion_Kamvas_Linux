"""
Usage:
    kamvas
        [ -t=<val> | --evdev-test=<val> ]
        [ -c | --create-default-config ]
    kamvas start
        [ -a=<val> | --action=<val> ]
    kamvas stop
    kamvas restart [ -a=<val> | --action=<val> ] [ -f | --start-in-foreground ]
        [ -r | --print-usb-data ]
        [ -c | --print-computed-values ]
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
    -c, --create-default-config
        Create a default config file at {config_path}
        if it doesn't already exist
"""

from __future__ import print_function
from pprint import pprint
import os
import sys
import shutil
import subprocess
import json

from docopt import docopt
import evdev
import usb.core
import yaml

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

# HANDLERS ----------------------------------------------------------------------------------------

def handle_start():
    config = load_config()
    commands = [
        'sudo',
        'python',
        DRIVER_SCRIPT,
        config['xinput_name'],
        str(config['vendor_id']),
        str(config['product_id']),
        json.dumps(config['pen']),
        json.dumps(config['actions']),
        '-c',
    ]

    subprocess.Popen(commands)
    print('Started')

def handle_stop():
    pass

def handle_status():
    pass

def handle_evdev_test(event_path):
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

# MAIN --------------------------------------------------------------------------------------------

def run_main():
    args = docopt(__doc__.format(
        config_path=CONFIG_PATH
    ))

    if args['start']:
        handle_start()
        return

    if args['stop']:
        handle_stop()
        return

    if args['restart']:
        handle_stop()
        handle_start()
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

    print(__doc__)

if __name__ == '__main__':
    run_main()
