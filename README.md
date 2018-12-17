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
    - [xdotool](https://www.semicomplete.com/projects/xdotool/): Allows you to simulate keyboard input and other mouse activities. This will be used by the script to trigger user defined actions (in ./config.json file) when a certain button is pressed on the graphics tablet
        
        ```
        sudo pacman -S xdotool
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

- Run the driver using

    ```
    sudo python kamvas_driver.py
    ```

    - The script will output some tablet information and you should be able to control the mouse cursor using the graphics tablet and do all the things you would expect with the graphics tablet
- If you want to output the raw X, Y position and pressure values to the screen then you can use the following commands

    ```
    sudo python kamvas_driver.py -v
    ```
- To print out the raw byte data from the USB use the following command
    
    ```
    sudo python kamvas_driver.py -t
    ```

## Configuration

You can edit the `./config.json` file to define your custom settings for your graphics tablet. The config file allows you to define the following:
- Capabilies of your graphics tablet (like its resolution, pressure sensitivity, etc)
- Pressure Curve 
    - A simple cubic bezier curve
    - Define the 4 points needed to describe the bezier curve
    - Make sure that the x and y values for the points is limited between 0 and 1 inclusive
    - The first and last point are fixed at x=0 and x=1
- Actions that must be performed when a button is clicked
    - The script uses `xdotool` to perform these actions so the values for these actions can be any commands accepted by `xdotool`
        - For example: Use `key a` to effectively execute `xdotool key a` which simulates the presseing of the `a` key on your keyboard
    - Leave the actions field empy if you don't to perform any action for that even
        - For example: You might not want actions to be performed when you touch the pen to the screen and want it behave like a normal mouse click. But the option if available in case you do want perform an action in that case.

## Troubleshooting

- The cursor behaves erratically or doesn't move at all
    - The graphics tablet sends out a packet of bytes every time you move the pen or click a button
    - Each byte represents a certain parameter
        - For example: For the Huion Kamvas Pro 13 the `x_pos_msb = data_packet[3]` and `x_pos_lsb = data_packet[2]`
    - It is possible that your graphics tablet arranges its data in a different way
    - You can use `-t` optional argument when running the script to print the raw byte packets
        - Each column represents a piece of data being sent by the tablet 
    - Observe how the values change when you perform certain actions
        - For example: Try to slowly move the pen from left to right and see how the values in the packet change. The values that change are most likely related to the X postion. Of those values, the byte changes more slowly is likely to be the MSB and the one that changes faster is likely to be the LSB.
    - Modify the code as needed and test your findings
