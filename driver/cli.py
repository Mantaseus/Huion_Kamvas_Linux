"""
Usage:
    kamvas start
        [ -a=<val> | --action=<val> ]
    kamvas stop
    kamvas restart
        [ -a=<val> | --action=<val> ]
    kamvas evdev-test <unix_event_path>

Options:
    -a=<val>, --action-<val>
        Define which group of button mappings you want to use.
        The button mappings are defined in {config_path}
"""

from __future__ import print_function
import os
import sys

from docopt import docopt
import evdev
import usb.core

# CONSTANTS ---------------------------------------------------------------------------------------

CONFIG_PATH = os.path.expanduser('~/.kamvas_config.yaml')

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

    if args['evdev-test']:
        handle_evdev_test(args['<unix_event_path>'])
        return

if __name__ == '__main__':
    run_main()
