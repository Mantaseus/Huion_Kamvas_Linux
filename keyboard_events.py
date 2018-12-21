## sudo pip install PyYAML
#import json
#from pprint import pprint
#
#config = {}
#with open('config.json', 'r') as json_file:
#    config = json.load(json_file)
#pprint(config)

import evdev
import usb.core

dev = evdev.InputDevice('/dev/input/event23')
if not dev:
    print("could not find device. The device may alread be open", file=sys.stderr)
    sys.exit(1)

for event in dev.read_loop():
    if event.type == evdev.ecodes.EV_KEY:
        print(evdev.categorize(event))
