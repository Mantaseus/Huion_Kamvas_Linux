from __future__ import print_function
from pprint import pprint

import usb.core
import usb.util
import sys
from evdev import UInput, ecodes, AbsInfo
import time
import subprocess

import json

# CONFIG ------------------------------------------------------------------------------------------

PEN_MAX_X = 58752
PEN_MAX_Y = 33048
PEN_MAX_Z = 8191
PEN_MAX_TILT_X = 60
PEN_MAX_TILT_Y = 60
RESOLUTION = 5080

PEN_CLICK_ACTION = 'key a'
PEN_BTN1_ACTION = 'key b'
PEN_BTN2_ACTION = 'key c'

TABLET_BTN_ACTIONS = {
    1: 'key d',
    2: 'key e',
    4: 'key f',
    8: 'key g',
    16: 'key h',
}

TABLET_SCROLLBAR_INCREASE_ACTION = 'key i'
TABLET_SCROLLBAR_DECREASE_ACTION = 'key j'
TABLET_SCROLLBAR_ACTIONS = {
    1: 'key k',
    2: 'key l',
    3: 'key m',
    4: 'key n',
    5: 'key o',
    6: 'key p',
    7: 'key q',
}

# GLOBALS -----------------------------------------------------------------------------------------

previous_scrollbar_state = 0
previous_clicked_btn = 0
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

def run_action(action):
    cmd="xdotool {}".format(action)
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(e)

def load_config(action):
    with open('config.json', 'r') as json_file:
        config_load = json.load(json_file)
   
    try: 
        config['pen'] = config_load['pen']
    except:
        print('The \'./config.yaml\' file does not have the \'pen\' property')
        exit()

    try:
        config['pressure_curve'] = config_load['pressure_curve']
    except:
        print('The \'./config.yaml\' file does not have the \'pressure_curve\' property')
        exit()

    try:
        config['actions'] = config_load['actions'][action]

        # JSON doesn't allow numeric keys for dictionaries, so we will have to make that happen
        tablet_buttons = config['actions']['tablet_buttons']
        config['actions']['tablet_buttons'] = {}
        for data in tablet_buttons:
            config['actions']['tablet_buttons'][data['id']] = data['action'] 
    except:
        print('The \'./config.yaml\' file does not have the actions named \'{}\''.format(action))
        exit()

# MAIN --------------------------------------------------------------------------------------------

if __name__ == '__main__':
    args = get_args()

    load_config('krita')
    pprint(config)
    
    # Define the events that will be triggered by the custom xinput device that we will create
    pen_events = {
        # Defining a pressure sensitive pen tablet area with 2 stylus buttons and no eraser
        ecodes.EV_KEY: [
            ecodes.BTN_TOUCH, 
            ecodes.BTN_TOOL_PEN, 
            ecodes.BTN_STYLUS, 
            ecodes.BTN_STYLUS2],
        ecodes.EV_ABS: [
            #AbsInfo input: value, min, max, fuzz, flat, resolution
            (ecodes.ABS_X, AbsInfo(0,0,PEN_MAX_X,0,0,RESOLUTION)),         
            (ecodes.ABS_Y, AbsInfo(0,0,PEN_MAX_Y,0,0,RESOLUTION)),
            (ecodes.ABS_PRESSURE, AbsInfo(0,0,PEN_MAX_Z,0,0,0)),
            (ecodes.ABS_TILT_X, AbsInfo(0,0,PEN_MAX_TILT_X,0,0,0)),
            (ecodes.ABS_TILT_Y, AbsInfo(0,0,PEN_MAX_TILT_Y,0,0,0)),
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
        try:
            # Read data from the USB
            data = dev.read(endpoint_0.bEndpointAddress,endpoint_0.wMaxPacketSize)

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

            if data[1] == 129:
                if PEN_CLICK_ACTION:
                    run_action(PEN_CLICK_ACTION)             
                else:
                    vpen.write(ecodes.EV_KEY, ecodes.BTN_TOUCH, 1)

            if data[1] == 130:
                if PEN_BTN1_ACTION:
                    run_action(PEN_BTN1_ACTION)             
                else:
                    vpen.write(ecodes.EV_KEY, ecodes.BTN_STYLUS, 1)

            if data[1] == 132:
                if PEN_BTN2_ACTION:
                    run_action(PEN_BTN2_ACTION)             
                else:
                    vpen.write(ecodes.EV_KEY, ecodes.BTN_STYLUS2, 1)

            # Tablet buttons
            if data[1] == 224:
                btn_index = data[4]
                if btn_index != previous_clicked_btn and TABLET_BTN_ACTIONS.get(btn_index, 0):
                    run_action(TABLET_BTN_ACTIONS.get(btn_index,0))
                previous_clicked_btn = btn_index

            # Scrollbar
            if data[1] == 240:
                scrollbar_state = data[5]

                if TABLET_SCROLLBAR_INCREASE_ACTION and scrollbar_state > previous_scrollbar_state:
                    run_action(TABLET_SCROLLBAR_INCREASE_ACTION)
                elif TABLET_SCROLLBAR_DECREASE_ACTION and scrollbar_state < previous_scrollbar_state:
                    run_action(TABLET_SCROLLBAR_DECREASE_ACTION)

                if scrollbar_state != previous_scrollbar_state and TABLET_SCROLLBAR_ACTIONS.get(scrollbar_state,0):
                    run_action(TABLET_SCROLLBAR_ACTIONS.get(scrollbar_state, 0))

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
        
