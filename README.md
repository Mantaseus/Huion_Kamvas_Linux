# Python based Linux driver for Huion Kamvas Pro devices

This is a userspace python based evdev driver for Huion Kamvas Pro devices so that they can be used on Linux machines which don't have officially supported driver.

I personally own a Huion Kamvas Pro 13 and I have tested this driver successfully with that device. You driver should also be usable with other Huion Kamvas devices, but they havn't been tested

Feel free to open an issue if you ran into trouble or write me a message if you found this useful. 

## Features

This script uses a simple configuration file to give you control over how your graphics tablet interacts with your computer. You can:
- Define bezier pressure curves to adjust the pressure sensitivity to your needs
- Define actions for every button on your tablet, even for pen touch. Actions can defined for the following events
    - Pen click on the screen
    - Pen Buttons
    - Tablet buttons
    - Scrollbar levels
    - Scrollbar increment
    - Scrollbar decrement

## Requirements

- Packages from your distribution (Archlinux commands shown here)
    - Python 3: This script was tested with Python 3. It might run just fine on Python 2 if you can install the required python modules

        ```
        sudo pacman -S python3
        ```
    - [xf86-input-evdev](https://digimend.github.io/support/howto/drivers/evdev/): This is the Digimend evdev package which adds X events relevant to graphics tablets and makes them available to other apps
        
        ```
        sudo pacman -S xf86-input-input-evdev
        ```
- Python packages
    - [pyusb](https://walac.github.io/pyusb/): Used for communicating with the USB device and reading the data packets from the graphics tablet
    
        ```
        pip install pyusb
        ```
    - [python-evdev](https://github.com/gvalkov/python-evdev): Used for adding and controlling a new xinput device. This is needed to actually use the data from the graphics tablet and move the cursor, provide pressure senistivity, etc.
        
        ```
        pip install evdev
        ```

# Setup

- Update your `/etc/X11/xorg.conf` file (create it if it is not already there):

    ```
    Section "InputClass"
        Identifier "evdev tablet catchall"
        MatchIsTablet "on"
        MatchDevicePath "/dev/input/event*"
        Driver "evdev"
    EndSection
    ```

- Clone this repository onto your computer
- You might need to make sure that the DIGImend kernel driver are not loaded. Unload them using this command

    ```
    sudo rmmod hid-uclogic
    ```

## Usage

- To run the driver and ask it to use the `krita` action group from your `config.json` use the following command

    ```
    sudo python kamvas_driver.py -a krita
    ```
- To list the valid action group names found in `config.json`

    ```
    sudo python kamvas_driver.py -ls
    ```
- To try and print information about the connected device

    ```
    sudo python kamvas_driver.py -p
    ```
- If you want to output the raw X, Y position and pressure values to the screen then you can use the following commands

    ```
    sudo python kamvas_driver.py -c
    ```
- To print out the raw byte data from the USB use the following command
    
    ```
    sudo python kamvas_driver.py -r
    ```

## Configuration

You can edit the `./config.json` file to define your custom settings for your graphics tablet. The config file allows you to define the following:
- Capabilies of your graphics tablet (like its resolution, pressure sensitivity, etc)
- Pressure Curve 
    - A simple cubic bezier curve
    - Define the 4 points needed to describe the bezier curve
    - Make sure that the x and y values for the points are limited between 0 and 1 inclusive
    - The first and last points are fixed at x=0 and x=1
- Actions that must be performed when a button is clicked
    - The script uses `evdev` events to perform these actions so the values for these actions can be any commands starting with `KEY_` or `BTN_`. For example:
        - Use `KEY_A` to effectively simulate the presseing of the `a` key on your keyboard
        - You can also combine events like `KEY_LEFTSHIFT+KEY_A` to effectively press `Shift+a` when that action is fired
    - You can use the `keyboard_events.py` to observe  which evdev events are fired when you press keys on your keyboard. Run it using the following command

        ```
        sudo python keyboard_events.py
        ```
    - Leave the actions field empy if you don't to perform any action for that even
        - For example: You might not want actions to be performed when you touch the pen to the screen and want it behave like a normal mouse click. But the option if available in case you do want perform an action in that case.
    - You can also define multiple action groups. See the `config.json` to see an example.

## Troubleshooting

- The cursor behaves erratically or doesn't move at all
    - The graphics tablet sends out a packet of bytes every time you move the pen or click a button
    - Each byte represents a certain parameter
        - For example: For the Huion Kamvas Pro 13 the `x_pos_msb = data_packet[3]` and `x_pos_lsb = data_packet[2]`
    - It is possible that your graphics tablet arranges its data in a different way
    - You can use `-r` optional argument when running the script to print the raw byte packets
        - Each column represents a piece of data being sent by the tablet 
    - Observe how the values change when you perform certain actions
        - For example: Try to slowly move the pen from left to right and see how the values in the packet change. The values that change are most likely related to the X postion. Of those values, the byte changes more slowly is likely to be the MSB and the one that changes faster is likely to be the LSB.
    - Modify the code as needed and test your findings
