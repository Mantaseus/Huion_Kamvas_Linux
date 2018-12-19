from __future__ import print_function
from pprint import pprint

import usb.core
import usb.util
import sys
from evdev import UInput, ecodes, AbsInfo
import time
import subprocess
import math

import json

# GLOBALS -----------------------------------------------------------------------------------------

ACTION_SPLIT_CHAR = '+'

previous_scrollbar_state = 0
previous_tablet_btn = 0
previous_pen_state = 0
previous_action = ''
config = {}

# HELPER FUNCTIONS --------------------------------------------------------------------------------

def print_array(array, spacing=5):
    string = ''
    for element in array:
        string = string + str(element) + ' '*(spacing-len(str(element)))
    print(string)

def print_tablet_info(device):
    print('TABLET INFORMATION -------------------------------------------------')
    for bRequest in range(256):
        try:
            result = usb.util.get_string(dev, bRequest)
            print('{}: {}'.format(hex(bRequest), result))
        except:
            pass
    print('--------------------------------------------------------------------')

def get_args():
    args = {}

    if '-v' in sys.argv:
        args['-v'] = True
    else:
        args['-v'] = False

    if '-t' in sys.argv:
        args['-t'] = True
    else:
        args['-t'] = False

    return args

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

def load_config(action):
    with open('config.json', 'r') as json_file:
        config_load = json.load(json_file)
    pprint(config_load)
    #import pdb; pdb.set_trace()
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
        print('The \'./config.yaml\' file does not have the actions named \'{}\''.format(action))
        exit()

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

    pprint(required_ecodes)
    return [ecodes.ecodes[required_ecode] for required_ecode in required_ecodes]

def is_list_within_list(list_var):
    try:
        if type(list_var[0]) is list:
            return True
    except:
        return False
    return False

# MAIN --------------------------------------------------------------------------------------------

if __name__ == '__main__':
    args = get_args()

    load_config('krita')
    pprint(config)
   
    # Define the events that will be triggered by the custom xinput device that we will create
    pen_events = {
        # Defining a pressure sensitive pen tablet area with 2 stylus buttons and no eraser
        ecodes.EV_KEY: get_required_ecodes(), #[
        #    ecodes.KEY_A, 
        #    ecodes.BTN_TOUCH, 
        #    ecodes.BTN_TOOL_PEN, 
        #    ecodes.BTN_STYLUS, 
        #    ecodes.BTN_STYLUS2],
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
    print_tablet_info(dev)
   
    # Seems like we need to try and read atleast once from the second endpoint on the device
    # or else the output from the first endpoint may get blocked on a tablet reboot 
    try:
        endpoint_1 = dev[0][(1,0)][0]
        data = dev.read(endpoint_1.bEndpointAddress,endpoint_1.wMaxPacketSize)
    except: pass

    # Create a virtual pen in /dev/input/ so that it shows up as a XInput device
    vpen = UInput(events=pen_events, name="kamvas-pen", version=0x3)
    print('huion kamvas GT191 driver should now be running')
    
    # Get a reference to the end that the tablet's output will be read from 
    endpoint_0 = dev[0][(0,0)][0]
    
    # Read the tablet output in an infinite loop
    while True:
        #time.sleep(1)
        try:
            # Read data from the USB
            data = dev.read(endpoint_0.bEndpointAddress,endpoint_0.wMaxPacketSize)

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
                vpen.write(ecodes.EV_ABS, ecodes.ABS_PRESSURE, pen_pressure)
                vpen.write(ecodes.EV_ABS, ecodes.ABS_TILT_X, pen_tilt_x)
                vpen.write(ecodes.EV_ABS, ecodes.ABS_TILT_Y, pen_tilt_y)

            # Reset any actions because this code means that nothing is happening
            if data[1] == 128:
                run_action('')

            # Pen click
            if data[1] == 129:
                run_action(config['actions'].get('pen_touch', ''))#, ecodes.BTN_TOUCH)

            # Pen button 1
            if data[1] == 130:
                run_action(config['actions'].get('pen_button_1', ''))#, ecodes.BTN_STYLUS)

            # Pen button 1 with pen touch
            if data[1] == 131:
                run_action(config['actions'].get('pen_button_1_touch', ''))#, ecodes.BTN_STYLUS)

            # Pen button 2
            if data[1] == 132:
                run_action(config['actions'].get('pen_button_2', ''))#, ecodes.BTN_STYLUS2)

            # Pen button 2 with pen touch
            if data[1] == 133:
                run_action(config['actions'].get('pen_button_2_touch', ''))#, ecodes.BTN_STYLUS2)

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

            
            #vpen.write(ecodes.EV_KEY, ecodes.BTN_STYLUS, pen_btn1_clicked and 1 or 0)
            #vpen.write(ecodes.EV_KEY, ecodes.BTN_STYLUS2, pen_btn2_clicked and 1 or 0)
            vpen.syn()
            
            if args['-t']:
                print_array(data, 8)
    
            if args['-v']:
                print("X {} Y {} PRESS {}          ".format(
                    pen_x, 
                    pen_y, 
                    pen_pressure, 
                ), end='\r')
        except usb.core.USBError as e:
            data = None
            if e.args == ('Operation timed out',):
                print(e, file=sys.stderr)
        
