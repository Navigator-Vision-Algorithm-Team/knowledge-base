"""Ideal planar body-twist integration, without ROS or hardware dependencies.

Units: metres, seconds and radians. No friction, inertia, collisions or estimator.
The timeout is a teaching-model rule, not a vehicle emergency-stop guarantee.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Pose2D:
    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0


@dataclass(frozen=True)
class Twist2D:
    vx: float = 0.0
    vy: float = 0.0
    wz: float = 0.0


def _finite(*values):
    if not all(math.isfinite(value) for value in values):
        raise ValueError('Motion values and timestamps must be finite')


def integrate_body(pose: Pose2D, twist: Twist2D, dt: float) -> Pose2D:
    """Exact constant-body-twist integration over dt; yaw remains unwrapped."""
    _finite(pose.x, pose.y, pose.yaw, twist.vx, twist.vy, twist.wz, dt)
    if dt < 0:
        raise ValueError('dt must be nonnegative')
    angle = twist.wz * dt
    _finite(angle)
    # Midpoint orientation times sinc gives the exact circular-arc displacement.
    # This form also avoids cancellation in (1-cos(angle)) near zero rotation.
    half = angle / 2
    sinc = math.sin(half) / half if abs(half) > 1e-8 else 1 - half * half / 6
    heading = pose.yaw + half
    c, s = math.cos(heading), math.sin(heading)
    scale = dt * sinc
    result = Pose2D(pose.x + scale * (c * twist.vx - s * twist.vy),
                    pose.y + scale * (s * twist.vx + c * twist.vy),
                    pose.yaw + angle)
    _finite(result.x, result.y, result.yaw)
    return result


class TimedModel:
    """Integrate timestamped commands; clip motion at expiry and clear on rollback.

    set_command first advances the previous command to the new event timestamp.
    The first event establishes an epoch. A backward clock preserves pose but
    discards the previous command, so replayed time cannot reapply old velocity.
    Callers must serialize access (the ROS adapter uses one executor thread).
    """

    def __init__(self, timeout: float = 0.5, pose: Pose2D | None = None):
        _finite(timeout)
        if timeout <= 0:
            raise ValueError('timeout must be positive')
        self.timeout = timeout
        self._pose = pose if pose is not None else Pose2D()
        _finite(self._pose.x, self._pose.y, self._pose.yaw)
        self._stamp = None
        self._command = Twist2D()
        self._command_stamp = None
        self.clock_resets = 0

    @property
    def pose(self) -> Pose2D:
        return self._pose

    @property
    def stamp(self) -> float | None:
        return self._stamp

    def active_twist(self, stamp: float) -> Twist2D:
        _finite(stamp)
        if self._command_stamp is None:
            return Twist2D()
        if stamp < self._command_stamp or stamp >= self._command_stamp + self.timeout:
            return Twist2D()
        return self._command

    def set_command(self, twist: Twist2D, stamp: float) -> None:
        _finite(twist.vx, twist.vy, twist.wz, stamp)
        self.step(stamp)
        self._command = twist
        self._command_stamp = stamp

    def step(self, stamp: float) -> Pose2D:
        _finite(stamp)
        if self._stamp is None:
            self._stamp = stamp
            return self._pose
        if stamp < self._stamp:
            self._command = Twist2D()
            self._command_stamp = None
            self._stamp = stamp
            self.clock_resets += 1
            return self._pose
        if self._command_stamp is not None:
            end = min(stamp, self._command_stamp + self.timeout)
            duration = max(0.0, end - self._stamp)
            self._pose = integrate_body(self._pose, self._command, duration)
        self._stamp = stamp
        return self._pose
