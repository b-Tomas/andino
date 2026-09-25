# BSD 3-Clause License
#
# Copyright (c) 2023, Ekumen Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    # For the IMX415 on a Pi 5 we use libcamera.
    # v4l2_camera can't consume it, so we use camera_ros instead.
    # libcamera must be built from source against Raspberry Pi's libcamera fork as
    # the apt package links Ubuntu's libcamera, which has no IMX415 support.
    # TODO(b-Tomas): just run the entire ROS2 Andino dockerized in a Pi with Raspbian
    return LaunchDescription(
        [
            Node(
                package="camera_ros",
                executable="camera_node",
                name="camera",
                output="screen",
                parameters=[
                    {
                        # 16:9 like the sensor (3864x2192)
                        "width": 640,
                        "height": 360,
                        "frame_id": "camera_link",
                        # No camera_info_url for now until we calibrate the camera
                    }
                ],
                # Keep the topic names v4l2_camera used
                remappings=[
                    ("/camera/image_raw", "/image_raw"),
                    ("/camera/image_raw/compressed", "/image_raw/compressed"),
                    ("/camera/camera_info", "/camera_info"),
                ],
            )
        ]
    )

# NOTE(b-Tomas) This file was:
#
# from launch import LaunchDescription
# from launch_ros.actions import Node
# from launch.actions import DeclareLaunchArgument
# from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, TextSubstitution
# from ament_index_python.packages import get_package_share_directory
# from os.path import join

# pkg_andino_bringup = get_package_share_directory('andino_bringup')

# def generate_launch_description():
#    # Declare launch argument for the path to the camera params YAML file (the 'file://' part is mandatory, you can't skip it)
#    intrinsic_params_file = DeclareLaunchArgument(
#        'intrinsic_params_file',
#        default_value='file://' + join(pkg_andino_bringup, 'config', 'raspicam.yaml'),
#        description='Path to camera intrinsics YAML file'
#    )

#    return LaunchDescription([
#        intrinsic_params_file,
#        Node(
#            package='v4l2_camera',
#            executable='v4l2_camera_node',
#            name='v4l2_camera_node',
#            output='screen',
#            parameters=[{
#                'image_size': [640, 480],
#                'camera_frame_id': 'camera_link',
#                'camera_info_url': LaunchConfiguration('intrinsic_params_file'),
#            }],
#        )
#    ])
