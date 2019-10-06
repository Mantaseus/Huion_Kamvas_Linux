"""
Usage:
    kamvas_driver <xinput_name> <usb_vendor_id> <usb_product_id> <pen_data> <action_ids> <action_data>
        [ -r | --print-usb-data ]
        [ -c | --print-calculated-data ]

Options:
    -r, --print-usb-data
        Prints the raw USB data to stdout
    -c, --print-calculated-data 
        Prints the calculated X, Y and pressure values

Note:
    <pen_data>, <action_ids> and <action_data> must be 
    JSON strings defining the capabilities of the pen 
    and the actions that need to be performed by the 
    tablet's onboard buttons respectively
"""

from __future__ import print_function
from pprint import pprint

from docopt import docopt
from evdev import UInput, ecodes, AbsInfo
import usb.core
import usb.util
import sys
import time
import math
import json
import argparse

# CONSTANTS ---------------------------------------------------------------------------------------

ACTION_SPLIT_CHAR = '+'

# GLOBALS -----------------------------------------------------------------------------------------

previous_scrollbar_state = 0
previous_tablet_btn = 0
previous_pen_state = 0
previous_action = ''

config = {}

tablet_info = []

# HELPER FUNCTIONS --------------------------------------------------------------------------------

def get_args():
    args = docopt(__doc__)
    
    try:
        args['pen'] = json.load(args['<pen_data>'])
    except:
        print('Error while loading <pen_data> as a JSON object')
        exit()

    try:
        args['action_ids'] = json.load(args['<action_ids>'])
    except:
        print('Error while loading <pen_data> as a JSON object')
        exit()

    try:
        args['actions'] = json.load(args['<action_data>'])
    except:
        print('Error while loading <action_data> as a JSON object')
        exit()

    return args

def print_raw_data(data, spacing=5):
    string = ''
    for element in data:
        string = string + str(element) + ' '*(spacing-len(str(element)))
    print(string)

def read_tablet_info(device):
    for bRequest in range(256):
        try:
            result = usb.util.get_string(dev, bRequest)
            tablet_info.append([hex(bRequest), result])
        except:
            pass

def print_available_actions():
    with open('config.json', 'r') as json_file:
        config_load = json.load(json_file)
        for key in config_load['actions']:
            print(key)

def run_action(new_action):
    def execute(action_text, press_type):
        if not action_text: return
            
        if ACTION_SPLIT_CHAR in action_text:
            actions = action_text.split(ACTION_SPLIT_CHAR)
            for action in actions:
                action_code = ecodes.ecodes.get(action, -1)
                if action_code == -1: return
                vpen.write(ecodes.EV_KEY, action_code, press_type)
        else:
            action_code = ecodes.ecodes.get(action_text, -1)
            if action_code == -1: return
            vpen.write(ecodes.EV_KEY, action_code, press_type)
  
    global previous_action
 
    if new_action == previous_action: 
        # "hold" the previously pressed action
        execute(previous_action, 2)
        return
    else:
        # Press "up" any previously pressed action
        execute(previous_action, 0)

    if new_action:
        # Press "down" the new action
        execute(new_action, 1)

    previous_action = new_action

def get_required_ecodes():
    required_ecodes = [
        'BTN_TOUCH', 
        'BTN_TOOL_PEN', 
        'BTN_STYLUS', 
        'BTN_STYLUS2'
    ]

    # Get the ecodes for pen buttons
    for value in args['actions'].values():
        if type(value) is list:
            for sub_value in value:
                if sub_value:
                    if ACTION_SPLIT_CHAR in sub_value:
                        required_ecodes.extend(sub_value.split(ACTION_SPLIT_CHAR))
                    else: 
                        required_ecodes.append(sub_value)
        else:
            if value:
                if ACTION_SPLIT_CHAR in value:
                    required_ecodes.extend(value.split(ACTION_SPLIT_CHAR))
                else: 
                    required_ecodes.append(value)

    return [
        ecodes.ecodes[required_ecode] 
        for required_ecode in required_ecodes
    ]

# MAIN --------------------------------------------------------------------------------------------

def run_main():
    global args
    args = get_args()

    # Define the events that will be triggered by the custom xinput device that we will create
    pen_events = {
        # Defining a pressure sensitive pen tablet area with 2 stylus buttons and no eraser
        ecodes.EV_KEY: get_required_ecodes(),
        ecodes.EV_ABS: [
            #AbsInfo input: value, min, max, fuzz, flat, resolution
            (ecodes.ABS_X, AbsInfo(0,0,args['pen']['max_x'],0,0,args['pen']['resolution'])),         
            (ecodes.ABS_Y, AbsInfo(0,0,args['pen']['max_y'],0,0,args['pen']['resolution'])),
            (ecodes.ABS_PRESSURE, AbsInfo(0,0,args['pen']['max_pressure'],0,0,0)),
            (ecodes.ABS_TILT_X, AbsInfo(0,0,args['pen']['max_tilt_x'],0,0,0)),
            (ecodes.ABS_TILT_Y, AbsInfo(0,0,args['pen']['max_tilt_y'],0,0,0)),
        ],
    }

    # Try to get a reference to the USB we need
    dev = usb.core.find(idVendor=0x256c, idProduct=0x006e)
    if not dev:
        print("could not find device. The device may alread be open", file=sys.stderr)
        sys.exit(1)
    
    # Forcefully claim the interface from any other script that might have been using it
    for cfg in dev:
        for interface in cfg:
            if dev.is_kernel_driver_active(interface.index):
                dev.detach_kernel_driver(interface.index)
                usb.util.claim_interface(dev, interface.index)
                print("grabbed interface {}".format(interface.index))
    
    # The method needs to be called or otherwise the tablet may not be in the correct mode
    # and no output might be seen from the first endpoint after a tablet reboot
    read_tablet_info(dev)
   
    # Seems like we need to try and read atleast once from the second endpoint on the device
    # or else the output from the first endpoint may get blocked on a tablet reboot 
    try:
        endpoint_1 = dev[0][(1,0)][0]
        data = dev.read(endpoint_1.bEndpointAddress,endpoint_1.wMaxPacketSize)
    except: 
        pass

    # Create a virtual pen in /dev/input/ so that it shows up as a XInput device
    vpen = UInput(events=pen_events, name="kamvas-pen", version=0x3)
    
    # Get a reference to the end that the tablet's output will be read from 
    usb_endpoint = dev[0][(0,0)][0]

    # USB data action IDs that still lead to position data
    position_action_ids = [
        args['action_ids']['normal'],
        args['action_ids']['pen_click'],
        args['action_ids']['pen_button_1'],
        args['action_ids']['pen_button_1_touch'],
        args['action_ids']['pen_button_2'],
        args['action_ids']['pen_button_2_touch'],
    ]
    
    # Read the tablet output in an infinite loop
    while True:
        try:
            # Read data from the USB
            data = dev.read(usb_endpoint.bEndpointAddress, usb_endpoint.wMaxPacketSize)

            # Only calculate these values if the event is a pen event and not tablet event
            if data[1] in position_action_ids:
                # Calculate the values            
                pen_x = (data[3] << 8) + (data[2])
                pen_y = (data[5] << 8) + data[4]
                pen_pressure = (data[7] << 8) + data[6]
                pen_tilt_x = data[10] >= 128 and (data[10]-256) or data[10]
                pen_tilt_y = data[11] >= 128 and (data[11]-256) or data[11]

                # Send data to the Xinput device so that cursor responds
                vpen.write(ecodes.EV_ABS, ecodes.ABS_X, pen_x)
                vpen.write(ecodes.EV_ABS, ecodes.ABS_Y, pen_y)
                vpen.write(ecodes.EV_ABS, ecodes.ABS_PRESSURE, pen_pressure)
                vpen.write(ecodes.EV_ABS, ecodes.ABS_TILT_X, pen_tilt_x)
                vpen.write(ecodes.EV_ABS, ecodes.ABS_TILT_Y, pen_tilt_y)

            # Reset any actions because this code means that nothing is happening
            if data[1] == args['action_ids']['normal']:
                run_action('')

            # Pen click
            if data[1] == args['action_ids']['pen_touch']:
                run_action(args['actions'].get('pen_touch', ''))

            # Pen button 1
            if data[1] == args['action_ids']['pen_button_1']:
                run_action(args['actions'].get('pen_button_1', ''))

            # Pen button 1 with pen touch
            if data[1] == args['action_ids']['pen_button_1_touch']:
                run_action(args['actions'].get('pen_button_1_touch', ''))

            # Pen button 2
            if data[1] == args['action_ids']['pen_button_2']:
                run_action(args['actions'].get('pen_button_2', ''))

            # Pen button 2 with pen touch
            if data[1] == args['action_ids']['pen_button_2_touch']:
                run_action(args['actions'].get('pen_button_2_touch', ''))

            # Tablet buttons
            if data[1] == args['action_ids']['tablet_button']:
                if data[4]:
                    btn_index = int(math.log(data[4],2))
                    if previous_tablet_btn != data[4] and args['actions'].get('tablet_buttons', ''):
                        run_action(args['actions']['tablet_buttons'][btn_index])
                    previous_tablet_btn = btn_index
                else:
                    run_action('')
                    previous_tablet_btn = 0

            # Scrollbar
            if data[1] == args['action_ids']['scrollbar']:
                scrollbar_state = data[5]

                if scrollbar_state:
                    if previous_scrollbar_state:
                        if scrollbar_state > previous_scrollbar_state:
                            run_action(args['actions'].get('tablet_scrollbar_increase', ''))
                        elif scrollbar_state < previous_scrollbar_state:
                            run_action(args['actions'].get('tablet_scrollbar_decrease', ''))

                    if scrollbar_state != previous_scrollbar_state and args['actions'].get('tablet_scrollbar', ''):
                        run_action(args['actions']['tablet_scrollbar'][scrollbar_state-1])
                else:
                    run_action('')
                    
                previous_scrollbar_state = scrollbar_state

            # Dispatch the evdev events
            vpen.syn()
            
            if args['--print-usb-data']:
                print_raw_data(data, 6)
    
            if args['--print-calculated-data']:
                print("X {} Y {} PRESS {}          ".format(
                    pen_x, 
                    pen_y, 
                    pen_pressure, 
                ), end='\r')
        except usb.core.USBError as e:
            if e.args[0] == 19:
                print('Device has been disconnected. Exiting ...')
                exit()

            # The usb read probably timed out for this cycle. Thats ok
            data = None
        
if __name__ == '__main__':
    run_main()
