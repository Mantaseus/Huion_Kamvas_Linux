"""
Usage:
    kamvas
        [ -t=<val> | --evdev-test=<val> ]
        [ -c | --create-default-config ]
    kamvas start
        [ -a=<val> | --action=<val> ]
    kamvas stop
    kamvas restart
        [ -a=<val> | --action=<val> ]

Options:
    -a=<val>, --action-<val>
        Define which group of button mappings you want to use.
        The button mappings are defined in {config_path}
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
import os
import sys
import shutil

from docopt import docopt
import evdev
import usb.core

# CONSTANTS ---------------------------------------------------------------------------------------

CONFIG_PATH = os.path.expanduser('~/.kamvas_config.yaml')
DEFAULT_CONFIG_PATH = 'driver/config.yaml'

# HANDLERS ----------------------------------------------------------------------------------------

def handle_start():
    pass

def handle_stop():
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

    if args['--evdev-test']:
        handle_evdev_test(args['--evdev-test'])
        return

    if args['--create-default-config']:
        handle_create_default_config()
        return

    print(__doc__)

if __name__ == '__main__':
    run_main()
