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

from docopt import docopt

# CONSTANTS ---------------------------------------------------------------------------------------

CONFIG_PATH = os.path.expanduser('~/.kamvas_config.yaml')

# HANDLERS ----------------------------------------------------------------------------------------

def handle_start():
    pass

def handle_stop():
    pass

def handle_evdev_test(event_path):
    pass

# MAIN --------------------------------------------------------------------------------------------

def run_main():
    args = docopt(__doc__.format(
        config_path=CONFIG_PATH
    ))
    print(args)

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
        handle_evdev_test()
        return

if __name__ == '__main__':
    run_main()
