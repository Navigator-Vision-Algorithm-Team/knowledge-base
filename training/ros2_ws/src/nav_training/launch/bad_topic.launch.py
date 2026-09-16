"""Reproduce a relative/absolute topic mismatch; sink_topic:=sequence repairs it."""

from nav_training.presets import description


def generate_launch_description():
    return description('/sequence')
