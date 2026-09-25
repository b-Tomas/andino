# Andino

This is my fork of the [Ekumen-OS/andino](https://github.com/Ekumen-OS/andino) robot, with a few modifications done to accommodate my own needs, mainly the alternative hardware that I bought.

## Hardware

Hardware changes, originally described in [andino_hardware/README.md](andino_hardware/README.md):

| Part_number |                  Was                  |                        Is                         |                 Purchase link                  |                                                                      Comments                                                                      |
| :---------: | :-----------------------------------: | :-----------------------------------------------: | :--------------------------------------------: | :------------------------------------------------------------------------------------------------------------------------------------------------: |
|      1      |        Raspberry Pi 4 B (4 GB)        |                  Raspberry Pi 5                   |                 TODO(b-Tomas)                  |                                            Needs a 5 V / 5 A supply. See [Known issues](#known-issues)                                             |
|      7      | 2 x DG01D-E motor with encoder (1:48) | 2 x motor with hall encoder, 12 PPR, 1:90 gearbox | [Amazon](https://www.amazon.com/dp/B0GHYFZ2SQ) |                                           4320 ticks per wheel rev instead of 585. See [Motors](#motors)                                           |
|      9      |             Arduino Nano              |         Arduino Nano v3 (new bootloader)          |                 TODO(b-Tomas)                  |                                                 Uploads at 115200 baud. See [Firmware](#firmware)                                                  |
|     13      |    Raspi Camera Module V2 (IMX219)    |               Arducam 8.3MP IMX415                |                 TODO(b-Tomas)                  | [Arducam docs](https://docs.arducam.com/Raspberry-Pi-Camera/Native-camera/8.3MP-IMX415/). Needs manual setup, see [Camera](#camera-arducam-imx415) |
|     14      |             Battery case              |                   TODO(b-Tomas)                   |                 TODO(b-Tomas)                  |                                                                                                                                                    |
|      -      |                   -                   |                     BMS board                     |                 TODO(b-Tomas)                  |                                                                                                                                                    |
|     17      |            DC-DC converter            |                   TODO(b-Tomas)                   |                 TODO(b-Tomas)                  |                                                                                                                                                    |

3D model changes:

- `andino_hardware/printing_model/chassis/battery_chassis_custom.{FCStd,3mf}` replaces `battery_chassis.stl`. I redesigned it for my battery holder, BMS board and DC-DC converter.

## Firmware

The new `nanoatmega328new` PlatformIO environment (`andino_firmware/platformio.ini`) flashes the newer Arduino Nano v3 clone at 115200 bps, otherwise at 57600 bps it would time out.

To flash and test the firmware:

```sh
cd andino_firmware
pio run --target upload -e nanoatmega328new
pio device monitor -b 57600 -p /dev/ttyUSB0 --echo --eol CR -f send_on_enter
```

### Motors

- 12 PPR per channel and a 1:90 gearbox. The firmware counts 12 × 4 × 90 = 4320 ticks per wheel rev.
- Open loop at PWM 150, wheels in the air: left ~103 rpm, right ~63 rpm. The right motor is noticeably slower.
- On the first test the right encoder had A/B swapped. Symptom: in closed loop the right PID got positive feedback and pinned at +255, running at full speed whatever the setpoint.

Deadband is about 35-60 PWM.

### PID

The default gains in `andino_firmware/include/andino/app/constants.h` are now kp 20, kd 18, ki 0, ko 100. The originals were 30/10/0/10.

## Software

I decided to run the Andino stack on Ubuntu 24.04 (ROS 2 Jazzy) on the Raspberry Pi 5 that I got. This meant:

- Manually setting up the IMX415 Arducam that I got.
- Skipping some steps of the SBC section of [andino_hardware/README.md](andino_hardware/README.md) that don't apply to this setup.
- Running RViz and the camera viewer from my laptop in Docker.

### SBC setup differences

Followed the SBC section of [andino_hardware/README.md](andino_hardware/README.md) with these changes:

- Skipped installing `arduino`, as I only needed it to flash the micro on my laptop.
- **Raspberry Camera Module V2:** skipped the whole section. The indications are for a legacy stack, which doesn't apply to Ubuntu 24.04 on a Pi 5. Follow [Camera](#camera-arducam-imx415).

### Camera (Arducam IMX415)

Ubuntu 24.04 ships kernel 6.8 and libcamera 0.2. Both are too old for the IMX415 on the Pi 5, which uses Raspberry Pi's PiSP camera pipeline. Arducam's own install script targets Raspberry Pi OS. Don't run it on Ubuntu.

Consider running Andino dockerized and using Raspbian with a newer kernel on the Pi instead.

1-. Device tree overlay:

```sh
sudo cp /boot/firmware/config.txt ~/config.txt.bak
wget -O ~/imx415.dtbo https://raw.githubusercontent.com/raspberrypi/firmware/master/boot/overlays/imx415.dtbo
sudo cp ~/imx415.dtbo /boot/firmware/overlays/
```

Add this under `[all]` in `/boot/firmware/config.txt`, then reboot:

```
dtoverlay=imx415
```

Check: `sudo dmesg | grep -i imx415` should print `Detected IMX415 image sensor`. A kernel update may wipe `/boot/firmware/overlays/`, so keep `~/imx415.dtbo` to copy it back.

2-. Kernel driver: libcamera sets parameters that under the default driver are read-only, producing `Unable to set controls: Permission denied` error lines on every frame and breaking features like auto-exposure. Raspberry Pi's version of the driver builds against 6.8 unchanged:

```sh
# TODO(b-Tomas): de-slop, cite sources
sudo apt install -y linux-headers-$(uname -r)
grep V4L2_CCI /boot/config-$(uname -r)          # expect =m or =y
mkdir -p ~/imx415-rpi && cd ~/imx415-rpi
wget -O imx415.c https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/drivers/media/i2c/imx415.c
echo 'obj-m += imx415.o' > Makefile
make -C /lib/modules/$(uname -r)/build M=$PWD modules
sudo install -D -m644 imx415.ko /lib/modules/$(uname -r)/updates/imx415.ko
sudo depmod -a
modinfo imx415 | head -1                        # expect .../updates/imx415.ko
sudo reboot
```

**Rebuild the module after every kernel update.**

To undo, delete the file from `updates/` and run `sudo depmod -a`.

3-. libcamera: Build Raspberry Pi's fork:

```sh
# TODO(b-Tomas): de-slop, cite sources
sudo apt install -y git meson ninja-build pkg-config python3-yaml python3-ply python3-jinja2 \
  libyaml-dev libgnutls28-dev libudev-dev libdrm-dev libboost-dev openssl libtiff-dev libevent-dev \
  nlohmann-json3-dev
git clone https://github.com/raspberrypi/libcamera.git ~/libcamera
cd ~/libcamera
meson setup build --buildtype=release \
  -Dpipelines=rpi/pisp -Dipas=rpi/pisp \
  -Dv4l2=enabled -Dcam=enabled -Dgstreamer=disabled -Dtest=false \
  -Dlc-compliance=disabled -Dqcam=disabled -Ddocumentation=disabled -Dpycamera=disabled
ninja -C build -j3
sudo ninja -C build install
sudo ldconfig
```

Check:

```sh
hash -r; which cam                  # /usr/local/bin/cam
cam -l                              # lists imx415
cam -c 1 --capture=5                # 5 frames, no errors
```

4-. camera_ros: Build it from source in the workspace so it links the new libcamera. Don't install `ros-jazzy-camera-ros` from apt. It links Ubuntu's libcamera, which has no IMX415 support.

```sh
cd ~/ws/src
git clone https://github.com/christianrauch/camera_ros.git
cd ~/ws
rosdep install --from-paths src -i -y -r --skip-keys=libcamera
colcon build --packages-select camera_ros
```

Always pass `--skip-keys=libcamera` to `rosdep install` on the robot. Otherwise rosdep installs Ubuntu's libcamera development files.

Not done yet:
- Calibration with `camera_calibration`. Until then `camera_ros` warns that there's no calibration file.
- Trying the Arducam tuning file: `LIBCAMERA_RPI_TUNING_FILE=/usr/local/share/libcamera/ipa/rpi/pisp/imx415_b0569.json`.

### Laptop (RViz, camera view)

I run the visualization tools from my laptop using the repo's Docker setup:

```sh
sudo ufw allow from <robot-ip>
./docker/build.sh --ros_distro jazzy
./docker/run.sh --ros_distro jazzy
```

Inside the container (the repo is mounted):

```sh
cd ~/ws
rosdep install -i -y --rosdistro jazzy --from-paths src
colcon build --symlink-install
source install/setup.bash
ros2 run rqt_image_view rqt_image_view /image_raw/compressed
ros2 launch andino_bringup rviz.launch.py
```

- `andino_bringup/rviz/andino.rviz` uses Fixed Frame `map`, which only exists while SLAM or localization is running. Without it, RViz drops the scans (`discarding message because the queue is full`). For teleop, set Global Options → Fixed Frame to `odom`.
- Answer `y` to the "overwrite the image" prompt when leaving the container. Otherwise the packages `rosdep` installed are lost.
- If no topics show up, check that both machines have the same `ROS_DOMAIN_ID` and that the clocks are in sync (`timedatectl`).

### ROS2

Changes to the ROS packages:

- `andino_description/config/andino/hardware.yaml`: `enc_ticks_per_rev: 4320` (was 585).
- `andino_control/config/andino_controllers.yaml`: `wheel_separation: 0.13`, `wheel_radius: 0.03365` (measured).
- `andino_bringup/launch/camera.launch.py`: `camera_ros` instead of `v4l2_camera`.
- `andino_bringup/package.xml`: `camera_ros` replaces `v4l2_camera`.

Bringup, on the robot:

```sh
cd ~/ws
colcon build
source install/setup.bash
ros2 launch andino_bringup andino_robot.launch.py
```

Check it's running:

```sh
ros2 control list_controllers
ros2 topic hz /scan
ros2 topic hz /image_raw
ros2 topic echo /odom --once
```

Teleop: `ros2 launch andino_bringup teleop_joystick.launch.py`, then hold LB or RB and move the sticks.

## Known issues

- The battery pack hasn't worked yet, working off of a lab power supply.
- The Pi rebooted when the motors started. There was no under-voltage in the kernel log, so it might be a sudden drop. The Pi was already running a but low on voltage (4.89V, `vcgencmd pmic_read_adc EXT5V_V`). For now, the Pi runs from a USB power supply and the motors from a lab power supply.
- The IMU is read by the firmware and by `andino_base::SerialMcu`, but the hardware interface doesn't export it. So there's no `/imu` topic and no sensor fusion. Localization is wheel odometry plus the lidar.

## TODO

- [ ] Calibrate the PID on the ground, with the robot's weight on the wheels.
- [ ] Ingest the PID values via serial and configure them on the ROS side.
- [ ] Fix the power path so the Pi can run from the battery.
- [ ] Expose the IMU through ros2_control.
- [ ] Calibrate the camera.

_Everything below is the upstream README.md from [Ekumen-OS/andino](https://github.com/Ekumen-OS/andino)_

---

<div align="center">

  ![Logo White](./docs/logo_white.svg#gh-dark-mode-only)

</div>

<div align="center">

  ![Logo Black](./docs/logo_black.svg#gh-light-mode-only)

</div>

Andino is a fully open-source diff drive robot designed for educational purposes and low-cost applications.
It is fully integrated with ROS 2 and it is a great base platform to improve skills over the robotics field.
With its open-source design, anyone can modify and customize the robot to suit their specific needs.

<p align="center">
  <img src="docs/real_robot.png" width=900 />
</p>

_Note: For videos go to [Media](#selfie-media) section._

## :books: Package Summary

- :rocket: [`andino_bringup`](./andino_bringup): Contains mainly launch files in order to launch all related driver and nodes to be used in the real robot.
- :robot: [`andino_hardware`](./andino_hardware): Contains information about the Andino assembly and hardware parts.
- :ledger: [`andino_description`](./andino_description): Contains the URDF description of the robot.
- :hammer_and_pick: [`andino_firmware`](./andino_firmware): Contains the code be run in the microcontroller for interfacing low level hardware with the SBC.
- :gear: [`andino_base`](./andino_base): [ROS Control hardware interface](https://control.ros.org/master/doc/ros2_control/hardware_interface/doc/writing_new_hardware_interface.html) is implemented.
- :control_knobs: [`andino_control`](./andino_control/): It launches the [`controller_manager`](https://control.ros.org/humble/doc/ros2_control/controller_manager/doc/userdoc.html) along with the [ros2 controllers](https://control.ros.org/master/doc/ros2_controllers/doc/controllers_index.html): [diff_drive_controller](https://control.ros.org/master/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html) and the [joint_state_broadcaster](https://control.ros.org/master/doc/ros2_controllers/joint_state_broadcaster/doc/userdoc.html).
- :world_map: [`andino_slam`](./andino_slam/): Provides support for SLAM with your `andino` robot.
- :compass: [`andino_navigation`](./andino_navigation/): Navigation stack based on `nav2`.

## :paperclips: Related projects

Projects built upon Andino! :rocket:

- :rocket: [`andino_ansible_config`](https://github.com/garyservin/andino_ansible_config): (**Thanks @garyservin !**): Ansible configuration to easily setup an Andino robot.
- :computer: [`andino_gz`](https://github.com/Ekumen-OS/andino_gz): [Gazebo](https://gazebosim.org/home)(non-classic)-based simulation of the `andino` robot.
- :lady_beetle: [`andino_webots`](https://github.com/Ekumen-OS/andino_webots): [Webots](https://github.com/cyberbotics/webots)-based simulation of the Andino robot fully integrated with ROS 2.
- :joystick: [`andino_o3de`](https://github.com/Ekumen-OS/andino_o3de): [O3DE](https://o3de.org/)-based simulation of the Andino robot.
- :green_circle: [`andino_isaac`](https://github.com/Ekumen-OS/andino_isaac): [Isaac Sim](https://docs.omniverse.nvidia.com/isaacsim/latest/index.html)-based simulation of the Andino robot.
- :m: [`andino_mujoco`](https://github.com/Ekumen-OS/andino_mujoco): [MuJoCo](https://mujoco.org/)-based simulation of the Andino robot.
- :robot: [`andino_rmf`](https://github.com/Ekumen-OS/andino_rmf): [OpenRMF](https://www.open-rmf.org/) integration of Andino simulation.
- :test_tube: [`andino_integration_tests`](https://github.com/Ekumen-OS/andino_integration_tests): Extension to the Andino robot showing how to build integration tests.
- :framed_picture: [`andino_lichtblick`](https://github.com/Ekumen-OS/andino_lichtblick): [Lichtblick](https://github.com/lichtblick-suite/lichtblick/) integration with Andino for web-based visualization.
- :crab: [`andino-rs`](https://github.com/Ekumen-OS/andino-rs): Rustacean version of *andino* robot. It also provides integration with [*dora*](https://github.com/dora-rs/dora) framework for both real and simulated *andino*.
- :nerd_face: [`robotics_essentials_ros2`](https://github.com/henki-robotics/robotics_essentials_ros2): ROS 2 Essentials material for robotic course at [*University of Eastern Finland*](https://www.uef.fi/en).

## :busts_in_silhouette: Community

[<img src="docs/discord-mark-blue.png" width=30 hspace="20"/>](https://discord.gg/tHhH32CTHu) Join our Discord and contribute to the community!


## :pick: Robot Assembly

Visit [`andino_hardware`](./andino_hardware/) for assembly instructions.

## :mechanical_arm: Installation

Remember to first go over the assembly instructions at [`andino_hardware`](./andino_hardware/)!

### Platforms

- ROS 2:
  - Humble Hawksbill
  - Jazzy Jalisco
- OS:
  - Ubuntu 22.04 Jammy Jellyfish (Humble)
  - Ubuntu 24.04 Noble Numbat (Jazzy)
  - Ubuntu Mate 22.04 / Ubuntu Server 24.04 (On real robot e.g: Raspberry Pi 4B)

### Via ansible

See [`andino_ansible_config`](https://github.com/garyservin/andino_ansible_config): This repository contains Ansible configurations for managing and automating the setup and configuration of an Andino robot.

### Build from Source

#### Dependencies

1. Install ROS 2: [Humble](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debians.html) or [Jazzy](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
2. Install [colcon](https://colcon.readthedocs.io/en/released/user/installation.html)

#### colcon workspace

Packages here provided are colcon packages. As such a colcon workspace is expected:

1. Create colcon workspace

```
mkdir -p ~/ws/src
```

2. Clone this repository in the `src` folder

```
cd ~/ws/src
```

```
git clone https://github.com/Ekumen-OS/andino.git
```

3. Install dependencies via `rosdep`

```
cd ~/ws
```

```
rosdep install --from-paths src --ignore-src -i -y
```

4. Build the packages

```
colcon build
```

5. Finally, source the built packages
   If using `bash`:

```
source install/setup.bash
```

`Note`: Whether your are installing the packages in your dev machine or in your robot the procedure is the same. Remember to go over the assembly instructions first.

### Install the binaries

The packages have been also released via ROS package manager system for the Humble and Jazzy distros. You can check them [here](https://repo.ros2.org/status_page/ros_humble_default.html?q=andino) (Humble) and [here](https://repo.ros2.org/status_page/ros_jazzy_default.html?q=andino) (Jazzy).

These packages can be installed using `apt` (e.g: `sudo apt install ros-humble-andino-description` or `sudo apt install ros-jazzy-andino-description`) or using `rosdep`.

## :rocket: Usage

### Robot bringup

`andino_bringup` contains launch files that concentrates the process that brings up the robot.

After installing and sourcing the andino's packages simply run.

```
ros2 launch andino_bringup andino_robot.launch.py
```

This launch files initializes the differential drive controller and brings ups the system to interface with ROS.
By default sensors like the camera and the lidar are initialized. This can be disabled via arguments and manage each initialization separately. See `ros2 launch andino_bringup andino_robot.launch.py -s ` for checking out the arguments.

- include_rplidar: `true` as default.
- include_camera: `true` as default.

After the robot is launched, use `ROS 2 CLI` for inspecting environment.
For example, by doing `ros2 topic list` the available topics can be displayed:

    /camera_info
    /cmd_vel
    /image_raw
    /odom
    /robot_description
    /scan
    /tf
    /tf_static

   _Note: Showing just some of them_

### Teleoperation

Launch files for using the keyboard or a joystick for teleoperating the robot are provided.

#### Keyboard

```
ros2 launch andino_bringup teleop_keyboard.launch.py
```
This is similarly to just executing `ros2 run teleop_twist_keyboard teleop_twist_keyboard`.

#### Joystick

Using a joystick for teleoperating is notably better.
You need the joystick configured as explained [here](andino_hardware/README.md#Using-joystick-for-teleoperation).
```
ros2 launch andino_bringup teleop_joystick.launch.py
```

### RViz

Use:

```
ros2 launch andino_bringup rviz.launch.py
```

For starting `rviz2` visualization with a provided configuration.

## :compass: Navigation

The [`andino_navigation`](./andino_navigation/README.md) package provides a navigation stack based on the great [Nav2](https://github.com/ros-planning/navigation2) package.

https://github.com/Ekumen-OS/andino/assets/53065142/29951e74-e604-4a6e-80fc-421c0c6d8fee

Follow the [`andino_navigation`'s README](./andino_navigation/README.md) instructions for bringing up the Navigation stack in the real robot or in the simulation.

## :computer: Simulation

<img src="https://github.com/Ekumen-OS/andino_gz/blob/humble/docs/media/andino_gz.png" width=600/>

Within the Andino ecosystem simulations on several platforms are provided:
 - [`andino_gz`](https://github.com/Ekumen-OS/andino_gz) - **Recommended**
 - [`andino_webots`](https://github.com/Ekumen-OS/andino_webots)
 - [`andino_o3de`](https://github.com/Ekumen-OS/andino_o3de)
 - [`andino_isaac`](https://github.com/Ekumen-OS/andino_isaac)
 - [`andino_mujoco`](https://github.com/Ekumen-OS/andino_mujoco)





## :selfie: Media

### RVIZ Visualization

https://github.com/Ekumen-OS/andino/assets/53065142/c9878894-1785-4b81-b1ce-80e07a27effd

### Slam

Using the robot for mapping.

https://github.com/Ekumen-OS/andino/assets/53065142/283f4afd-0f9a-4d37-b71f-c9d7b2f3e453

https://github.com/Ekumen-OS/andino/assets/53065142/d73f6053-b422-4334-8f62-029a38799e66


See [`andino_slam`](./andino_slam/) for more information.

## :robot: Share your Andino!

Have you built your `Andino` already? Please go to [`Show & Tell`](https://github.com/Ekumen-OS/andino/discussions/categories/show-and-tell) Discussion and share with us your own version of it.


## :star2: Inspirational sources

This section is dedicated to recognizing and expressing gratitude to the open-source repositories that have served as a source of inspiration for this project. We highly recommend exploring these repositories for further inspiration and learning.

 * [articubot_one](https://github.com/joshnewans/articubot_one)
 * [diffbot](https://github.com/ros-mobile-robots/diffbot)
 * [noah_hardware](https://github.com/GonzaCerv/noah-hardware)
 * [linorobot](https://github.com/linorobot/linorobot2)

## :raised_hands: Contributing

Issues or PRs are always welcome! Please refer to [CONTRIBUTING](CONTRIBUTING.md) doc.

## Code development

Note that a [`Docker`](./docker) folder is provided for easy setting up the workspace.
