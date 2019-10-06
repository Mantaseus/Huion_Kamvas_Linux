"""
Usage:
    kamvas
        [ -t=<val> | --evdev-test=<val> ]
        [ -c | --create-default-config ]
    kamvas start
        [ -a=<val> | --action=<val> ]
        [ -f | --start-in-foreground ]
        [ -r | --print-usb-data ]
        [ -c | --print-computed-values ]
    kamvas stop
    kamvas restart
        [ -a=<val> | --action=<val> ]
        [ -f | --start-in-foreground ]
        [ -r | --print-usb-data ]
        [ -c | --print-computed-values ]
    kamvas status

Options:
    -f, --start-in-foreground
        Start the driver service in foreground instead if you
        want to see the debug USB data
    -r, --print-usb-data
        Only works with the `-f` option. Prints the raw USB data
        to the screen
    -c, --print-computed-values
        Only works with the `-f` option. Prints the computed X,
        Y and pressure values from the tablet
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
import os
import sys
import shutil

from docopt import docopt
import evdev
import usb.core

# CONSTANTS ---------------------------------------------------------------------------------------

CONFIG_PATH = os.path.expanduser('~/.kamvas_config.yaml')
DEFAULT_CONFIG_PATH = 'driver/config.yaml'

# HELPRES -----------------------------------------------------------------------------------------

def load_config(action):
    with open('config.json', 'r') as json_file:
        config_load = json.load(json_file)

    # Get the pen config
    try: 
        config['pen'] = config_load['pen']
    except:
        print('The \'./config.yaml\' file does not have the \'pen\' property')
        exit()

    # Get the actions config
    try:
        config['actions'] = config_load['actions'][action]
    except:
        print('The \'./config.yaml\' file does not have the action group named \'{}\'. Please specify a valid action group name.'.format(action))
        exit()


# HANDLERS ----------------------------------------------------------------------------------------

def handle_start():
    pass

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
