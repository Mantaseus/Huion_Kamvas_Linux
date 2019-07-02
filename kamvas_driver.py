from __future__ import print_function
from pprint import pprint

from evdev import UInput, ecodes, AbsInfo
import usb.core
import usb.util
import sys
import time
import math
import json
import argparse

# GLOBALS -----------------------------------------------------------------------------------------

ACTION_SPLIT_CHAR = '+'
CURVE_POINTS = 10

previous_scrollbar_state = 0
previous_tablet_btn = 0
previous_pen_state = 0
previous_action = ''

pressure_curve_points = []

config = {}

# HELPER FUNCTIONS --------------------------------------------------------------------------------

def print_raw_data(data, spacing=5):
    string = ''
    for element in data:
        string = string + str(element) + ' '*(spacing-len(str(element)))
    print(string)

def get_tablet_info(device, print_data=False):
    for bRequest in range(256):
        try:
            result = usb.util.get_string(dev, bRequest)
            if print_data:
                print('{}: {}'.format(hex(bRequest), result))
        except:
            pass

def get_args():
    parser = argparse.ArgumentParser(description='A user space driver for using Huion Graphics tablets with Linux')

    parser.add_argument('-a', type=str, help='The name of the group of actions to perform when a certain event occurs as defined in the config')
    parser.add_argument('-r', action='store_true', help='Print out the raw byte data from the USB')
    parser.add_argument('-p', action='store_true', help='Print out the device information')
    parser.add_argument('-c', action='store_true', help='Print the calculated X, Y and pressure values from the pen')
    parser.add_argument('-ls', action='store_true', help='Print the available action groups available in the config')
    
    # Check if we got any input piped in
    if not sys.stdin.isatty():
        # Input was piped in and it is assumed that the first line of the piped input is action
        # group name
        input = sys.stdin.readline().rstrip()
        if input:
            args = vars(parser.parse_args(['-a', input]))
            return args
    
    # If we got to this point then we probably didn;t get any valid input from stdin
    # So, look for arguments from the user
    args = vars(parser.parse_args())

    return args

def print_available_actions():
    with open('config.json', 'r') as json_file:
        config_load = json.load(json_file)
        for key in config_load['actions']:
            print(key)

def load_config(action):
    with open('config.json', 'r') as json_file:
        config_load = json.load(json_file)

    # Get the pen config
    try: 
        config['pen'] = config_load['pen']
    except:
        print('The \'./config.yaml\' file does not have the \'pen\' property')
        exit()

    # Get the pressure curve
    try:
        config['pressure_curve'] = config_load['pressure_curve']
    except:
        print('The \'./config.yaml\' file does not have the \'pressure_curve\' property')
        exit()

    # Get the actions config
    try:
        config['actions'] = config_load['actions'][action]
    except:
        print('The \'./config.yaml\' file does not have the action group named \'{}\'. Please specify a valid action group name.'.format(action))
        exit()

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
    for value in config['actions'].values():
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

    return [ecodes.ecodes[required_ecode] for required_ecode in required_ecodes]

def generate_pressure_curve_points():
    # Generate the bezier curve based on t using the definition here: https://en.wikipedia.org/wiki/B%C3%A9zier_curve
    # This algorithm uses t which is not the same as x or y values and is more of a sampling point
    # along the length of the curve
    curve_t_x = []
    curve_t_y = []
    for i in range(0, CURVE_POINTS+1):
        t = i/CURVE_POINTS
        a = (1-t)**3
        b = 3 * t * (1-t)**2
        c = 3 * t**2 * (1-t)
        d = t**3

        curve_t_x.append((
            b*config['pressure_curve'][1]['x'] + 
            c*config['pressure_curve'][2]['x'] + 
            d
        )*config['pen']['max_pressure'])
        curve_t_y.append((
            a*config['pressure_curve'][0]['y'] + 
            b*config['pressure_curve'][1]['y'] + 
            c*config['pressure_curve'][2]['y'] + 
            d*config['pressure_curve'][3]['y']
        )*config['pen']['max_pressure'])

    # Generate the bezier curve based on x using interpolation
    # x is the index of the list and the corresponding value will be the y value
    # There will be a corresponsing value on the curve for every pressure value
    # input pressure value will the the index of the pressure curve
    for x in range(0, config['pen']['max_pressure']+1):
        if x in curve_t_x:
            # If we have an exact x match on curve then no need for interpolation
            pressure_curve_points.append(int(curve_t_y[curve_t_x.index(x)]))
        else:
            # We will need to linear interpolate
            # Find the interpolation range
            for i in range(0, len(curve_t_x)-1):
                if x > curve_t_x[i] and x < curve_t_x[i + 1]:
                    interpolated_y = ((x - curve_t_x[i]) / (curve_t_x[i+1] - curve_t_x[i])) * (curve_t_y[i+1]-curve_t_y[i]) + curve_t_y[i]
                    pressure_curve_points.append(int(interpolated_y))
                    break

# MAIN --------------------------------------------------------------------------------------------

if __name__ == '__main__':
    args = get_args()

    # Print action groups in the config
    if args['ls']:
        print_available_actions()
        exit()
   
    # Setup
    load_config(args['a'])
    generate_pressure_curve_points()

    # Define the events that will be triggered by the custom xinput device that we will create
    pen_events = {
        # Defining a pressure sensitive pen tablet area with 2 stylus buttons and no eraser
        ecodes.EV_KEY: get_required_ecodes(),
        ecodes.EV_ABS: [
            #AbsInfo input: value, min, max, fuzz, flat, resolution
            (ecodes.ABS_X, AbsInfo(0,0,config['pen']['max_x'],0,0,config['pen']['resolution'])),         
            (ecodes.ABS_Y, AbsInfo(0,0,config['pen']['max_y'],0,0,config['pen']['resolution'])),
            (ecodes.ABS_PRESSURE, AbsInfo(0,0,config['pen']['max_pressure'],0,0,0)),
            (ecodes.ABS_TILT_X, AbsInfo(0,0,config['pen']['max_tilt_x'],0,0,0)),
            (ecodes.ABS_TILT_Y, AbsInfo(0,0,config['pen']['max_tilt_y'],0,0,0)),
        ],
        #ecodes.EV_MSC: [ecodes.MSC_SCAN], #not sure why, but it appears to be needed
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
    get_tablet_info(dev, args['p'])
   
    # Seems like we need to try and read atleast once from the second endpoint on the device
    # or else the output from the first endpoint may get blocked on a tablet reboot 
    try:
        endpoint_1 = dev[0][(1,0)][0]
        data = dev.read(endpoint_1.bEndpointAddress,endpoint_1.wMaxPacketSize)
    except: pass

    # Create a virtual pen in /dev/input/ so that it shows up as a XInput device
    vpen = UInput(events=pen_events, name="kamvas-pen", version=0x3)
    
    # Get a reference to the end that the tablet's output will be read from 
    usb_endpoint = dev[0][(0,0)][0]
    
    # Read the tablet output in an infinite loop
    while True:
        try:
            # Read data from the USB
            data = dev.read(usb_endpoint.bEndpointAddress, usb_endpoint.wMaxPacketSize)

            # Only calculate these values if the event is a pen event and not tablet event
            if data[1] in [128, 129, 130, 131, 132, 133]:
                # Calculate the values            
                pen_x = (data[3] << 8) + (data[2])
                pen_y = (data[5] << 8) + data[4]
                pen_pressure = (data[7] << 8) + data[6]
                pen_tilt_x = data[10] >= 128 and (data[10]-256) or data[10]
                pen_tilt_y = data[11] >= 128 and (data[11]-256) or data[11]

                # Send data to the Xinput device so that cursor responds
                vpen.write(ecodes.EV_ABS, ecodes.ABS_X, pen_x)
                vpen.write(ecodes.EV_ABS, ecodes.ABS_Y, pen_y)
                vpen.write(ecodes.EV_ABS, ecodes.ABS_PRESSURE, pressure_curve_points[pen_pressure])
                vpen.write(ecodes.EV_ABS, ecodes.ABS_TILT_X, pen_tilt_x)
                vpen.write(ecodes.EV_ABS, ecodes.ABS_TILT_Y, pen_tilt_y)

            # Reset any actions because this code means that nothing is happening
            if data[1] == 128:
                run_action('')

            # Pen click
            if data[1] == 129:
                run_action(config['actions'].get('pen_touch', ''))

            # Pen button 1
            if data[1] == 130:
                run_action(config['actions'].get('pen_button_1', ''))

            # Pen button 1 with pen touch
            if data[1] == 131:
                run_action(config['actions'].get('pen_button_1_touch', ''))

            # Pen button 2
            if data[1] == 132:
                run_action(config['actions'].get('pen_button_2', ''))

            # Pen button 2 with pen touch
            if data[1] == 133:
                run_action(config['actions'].get('pen_button_2_touch', ''))

            # Tablet buttons
            if data[1] == 224:
                if data[4]:
                    btn_index = int(math.log(data[4],2))
                    if previous_tablet_btn != data[4] and config['actions'].get('tablet_buttons', ''):
                        run_action(config['actions']['tablet_buttons'][btn_index])
                    previous_tablet_btn = btn_index
                else:
                    run_action('')
                    previous_tablet_btn = 0

            # Scrollbar
            if data[1] == 240:
                scrollbar_state = data[5]

                if scrollbar_state:
                    if previous_scrollbar_state:
                        if scrollbar_state > previous_scrollbar_state:
                            run_action(config['actions'].get('tablet_scrollbar_increase', ''))
                        elif scrollbar_state < previous_scrollbar_state:
                            run_action(config['actions'].get('tablet_scrollbar_decrease', ''))

                    if scrollbar_state != previous_scrollbar_state and config['actions'].get('tablet_scrollbar', ''):
                        run_action(config['actions']['tablet_scrollbar'][scrollbar_state-1])
                else:
                    run_action('')
                    
                previous_scrollbar_state = scrollbar_state

            # Dispatch the evdev events
            vpen.syn()
            
            if args['r']:
                print_raw_data(data, 6)
    
            if args['c']:
                print("X {} Y {} PRESS: {} -> {}          ".format(
                    pen_x, 
                    pen_y, 
                    pen_pressure, 
                    pressure_curve_points[pen_pressure]
                ), end='\r')
        except usb.core.USBError as e:
            if e.args[0] == 19:
                print('Device has been disconnected. Exiting ...')
                exit()

            # The usb read probably timed out for this cycle. Thats ok
            data = None
        except KeyboardInterrupt:
            # The user probably pressed "Ctrl+c" to close the program, so, close it cleanly
            exit()
        
