# Python based Linux driver for Huion Kamvas Pro devices

This is a userspace python based evdev driver for Huion Kamvas Pro devices so that they can be used on Linux machines which don't have officially supported driver.

I personally own a Huion Kamvas Pro 13 and I have tested this driver successfully with that device. The driver should hopefully also be usable with other Huion Kamvas devices, but they havn't been tested.

Feel free to open an issue if you ran into trouble or write me a message if you found this useful. 

## Features

This script uses a simple YAML configuration file to give you control over how your graphics tablet interacts with your computer. This configuration file is located at `~/.kamvas_config.yaml`.

With this driver you can:
- Define actions for every button on your tablet, even for pen touch. Actions can be defined for the following events
    - Pen click on the screen
    - Pen Buttons
    - Tablet buttons
    - Scrollbar levels
    - Scrollbar increment
    - Scrollbar decrement
- Manage button action profiles that you can easily switch between
- Automatically map the driver output to a desired display if you have multiple monitors. **NOTE** This uses `xinput` so you will need to have that installed on your system for this functionality to work
- The driver is automatically stopped when the USB device is unplugged and gets automatically started when it gets plugged in again

# Setup

- You will need to install the following packages from your distribution (Archlinux commands shown here)
    - Python 3: This script was tested with Python 3. It might run just fine on Python 2 if you can install the required python modules

        ```
        sudo pacman -S python3
        ```
    - [xf86-input-evdev](https://digimend.github.io/support/howto/drivers/evdev/): This is the Digimend evdev package which adds X events relevant to graphics tablets and makes them available to other apps
        
        ```
        sudo pacman -S xf86-input-input-evdev
        ```
- Install the driver module

    ```
    pip3 install huion-kamvas-driver
    ```
- Update your `/etc/X11/xorg.conf` file (create it if it is not already there):

    ```
    Section "InputClass"
        Identifier "evdev tablet catchall"
        MatchIsTablet "on"
        MatchDevicePath "/dev/input/event*"
        Driver "evdev"
    EndSection
    ```

- You might need to make sure that the DIGImend kernel driver are not loaded. Unload them using this command

    ```
    sudo rmmod hid-uclogic
    ```
- Setup a default configuration file for the driver

    ```
    kamvas -c
    ```

## Usage

- Start the driver

    ```
    kamvas start
    ```
- Stop the driver

    ```
    kamvas stop
    ```

## Configuration

You can create a default configuration file at `~/.kamvas_config.yaml` using the following command

```
kamvas -c
```

You can edit `~/.kamvas_config.json` file to define your custom settings for your graphics tablet. The config file allows you to define the following:
- Capabilies of your graphics tablet (like its resolution, pressure sensitivity, etc)
    - You will most likely not need to change this but might be useful if you are trying to adapt this driver to some other device
    - These fields are
        - xinput_name
        - vendor_id
        - product_id
        - pen
- Actions that must be performed when a button is clicked
    - The script uses `evdev` events to perform these actions so the values for these actions can be any commands starting with `KEY_` or `BTN_`. For example:
        - Use `KEY_A` to effectively simulate the presseing of the `a` key on your keyboard
        - You can also combine events like `KEY_LEFTSHIFT+KEY_A` to effectively press `Shift+a` when that action is fired
    - You can use the following command to observe which evdev events are fired when you press keys on your device. You will need to figure out the path of the event file for the device you are trying to test. It is usually located in `/dev/input/`. You can also try looking for it by name in `/dev/input/by-id/` and `/dev/input/by-path/`

        ```
        kamvas -t <path_to_event_file>
        ```
    - Leave the actions field empty if you don't to perform any action for that even
        - For example: You might not want actions to be performed when you touch the pen to the screen and want it behave like a normal mouse click. But the option if available in case you do want perform an action in that case.
    - You can also define multiple action groups. See the `config.json` to see an example.
- The `default_display` field automatically maps your driver output to a given system display name (like `HDMI1`, `DVI1`, etc)
    - This feature required `xinput` to be installed on your system
    - Remove this field if you do not have `xinput` installed or are just using a single display
    - If you have multiple displays and you do not use this field then the output from your graphics tablet will be mapped to all the displays by default
- The `default_action` field defines the button actions group that will be used by the driver if `kamvas start -a=<action_name>` is not used to start the driver 

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

## Known Issues

- The driver is unable to survive a system suspend or hibernate event
    - On resume, it will continue to show that the driver is running but the cursor will be unresponsive if you try to use the device
    - You will have to stop the driver and start it again

        ```
        kamvas stop
        kamvas start
        ```
