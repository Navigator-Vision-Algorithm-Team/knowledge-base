"""Finite, planar velocity validation independent of ROS."""

import math


def bounded_number(value, name, minimum, maximum):
    """Return a finite number inside the inclusive startup parameter range."""
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f'{name} must be finite and in [{minimum}, {maximum}]')
    return number


def bound_planar_command(values, max_linear=0.5, max_angular=1.0):
    """Validate xyz/xyz Twist components and bound planar speed preserving direction.

    Invalid input raises ValueError. The ROS adapter replaces it with a zero
    command immediately, so a previous valid command cannot remain active.
    """
    max_linear = float(max_linear)
    max_angular = float(max_angular)
    if not all(math.isfinite(v) and v > 0 for v in (max_linear, max_angular)):
        raise ValueError('Velocity limits must be finite and positive')
    values = tuple(float(value) for value in values)
    if len(values) != 6 or not all(math.isfinite(value) for value in values):
        raise ValueError('Twist must contain six finite components')
    vx, vy, vz, wx, wy, wz = values
    if vz != 0 or wx != 0 or wy != 0:
        raise ValueError('Only linear.x, linear.y and angular.z are supported')
    # Normalize first to prevent overflow for otherwise finite components.
    scale = max(abs(vx), abs(vy))
    if scale:
        ux, uy = vx / scale, vy / scale
        norm = math.hypot(ux, uy)
        if scale > max_linear / norm:
            vx, vy = max_linear * ux / norm, max_linear * uy / norm
    return vx, vy, max(-max_angular, min(max_angular, wz))
