"""Shared launch description for the healthy and topic-mismatch presets."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def description(default_sink):
    namespace = 'nav_training'
    return LaunchDescription([
        DeclareLaunchArgument('sink_topic', default_value=default_sink,
                              description='Relative sequence repairs the deliberate /sequence error'),
        DeclareLaunchArgument('rate_hz', default_value='10.0'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        Node(package='nav_training', executable='sequence_publisher',
             namespace=namespace, name='sequence_source', output='screen',
             parameters=[{'topic': 'sequence', 'rate_hz': ParameterValue(
                 LaunchConfiguration('rate_hz'), value_type=float)}]),
        Node(package='nav_training', executable='sequence_subscriber',
             namespace=namespace, name='sequence_sink', output='screen',
             parameters=[{'topic': ParameterValue(LaunchConfiguration('sink_topic'),
                                                   value_type=str)}]),
        Node(package='nav_training', executable='ideal_model',
             namespace=namespace, name='ideal_model', output='screen',
             parameters=[{'use_sim_time': ParameterValue(
                 LaunchConfiguration('use_sim_time'), value_type=bool)}]),
    ])
