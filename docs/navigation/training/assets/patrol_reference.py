"""Deterministic offline patrol protocol. No ROS, sockets or hardware access.

Units are m, s, rad. Yaw is fixed at zero: world and body axes coincide.
Input stamps mean receipt time on one monotonic teaching clock, not ROS headers.
tick(t) advances the previous command to t, then handles observations at t.
The runner uses fixed dt; a late tick still clips integration at input expiry.
"""
import argparse
import json
import math
from pathlib import Path

EPS = 1e-10
TERMINAL = {"SUCCEEDED", "CANCELED", "ABORTED"}
CASES = Path(__file__).with_name("patrol_cases.json")


def finite_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


class Patrol:
    """One active goal. Terminal instances cannot be restarted with fresh input."""

    def __init__(self, waypoints, dt=0.1, max_speed=0.2, input_timeout=0.5,
                 stop_distance=0.5, clear_distance=0.8):
        self.dt = finite_number(dt, "dt")
        self.max_speed = finite_number(max_speed, "max_speed")
        self.input_timeout = finite_number(input_timeout, "input_timeout")
        self.stop_distance = finite_number(stop_distance, "stop_distance")
        self.clear_distance = finite_number(clear_distance, "clear_distance")
        if min(self.dt, self.max_speed, self.input_timeout) <= 0:
            raise ValueError("dt, max_speed and input_timeout must be positive")
        if not 0 <= self.stop_distance < self.clear_distance:
            raise ValueError("need 0 <= stop_distance < clear_distance")
        if not isinstance(waypoints, (list, tuple)) or not waypoints:
            raise ValueError("waypoints must be a nonempty sequence of (x, y)")
        self.waypoints = []
        previous = [0.0, 0.0]
        for point in waypoints:
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                raise ValueError("each waypoint must contain exactly x and y")
            target = [finite_number(point[0], "x"), finite_number(point[1], "y")]
            finite_number(math.hypot(target[0] - previous[0], target[1] - previous[1]),
                          "waypoint segment length")
            self.waypoints.append(target)
            previous = target
        self.pose = [0.0, 0.0, 0.0]
        self.velocity = [0.0, 0.0, 0.0]
        self.state = "MOVING"
        self.index = 0
        self.stamp = None
        self.started_at = None
        self.odom_stamp = None
        self.obstacle_stamp = None
        self.obstacle_distance = None
        self.waypoint_logs = []
        self.result = None

    def distance(self):
        if self.index == len(self.waypoints):
            return 0.0
        target = self.waypoints[self.index]
        return math.hypot(target[0] - self.pose[0], target[1] - self.pose[1])

    def finish(self, state, at, reason):
        self.state = state
        self.velocity = [0.0, 0.0, 0.0]
        self.result = {"state": state, "total_time": round(at - self.started_at, 10),
                       "reached_points": self.index, "interrupted": state != "SUCCEEDED",
                       "reason": reason}

    def advance(self, end):
        if self.state != "MOVING" or self.stamp is None:
            return
        speed = math.hypot(*self.velocity[:2])
        duration = max(0.0, end - self.stamp)
        if speed > 0:
            duration = min(duration, self.distance() / speed)
        self.pose[0] += self.velocity[0] * duration
        self.pose[1] += self.velocity[1] * duration

    def snapshot(self, now, event):
        return {"time": round(now, 10), "event": event, "state": self.state,
                "velocity": self.velocity[:], "pose": self.pose[:],
                "input_age": {"odom": None if self.odom_stamp is None else round(now - self.odom_stamp, 10),
                              "obstacle": None if self.obstacle_stamp is None else round(now - self.obstacle_stamp, 10)},
                "feedback": {"current_index": self.index, "current_pose": self.pose[:],
                             "distance_to_goal": self.distance(), "state": self.state},
                "result": None if self.result is None else self.result.copy()}

    def tick(self, now, odom_stamp=None, obstacle_stamp=None, obstacle_distance=None, cancel=False):
        """Reject malformed events without mutation; integrate old command first.

        now must increase strictly. Receipt stamps may repeat but cannot regress
        or be in the future. Expiry wins over a fresh packet delivered too late;
        otherwise cancellation wins over obstacle handling and arrival logging.
        """
        now = finite_number(now, "time")
        if now < 0 or (self.stamp is not None and now <= self.stamp):
            raise ValueError("event time must be nonnegative and strictly increasing")
        if not isinstance(cancel, bool):
            raise ValueError("cancel must be bool")
        if (obstacle_stamp is None) != (obstacle_distance is None):
            raise ValueError("obstacle_stamp and obstacle_distance must be supplied together")
        observations = [("odom_stamp", odom_stamp, self.odom_stamp),
                        ("obstacle_stamp", obstacle_stamp, self.obstacle_stamp)]
        for name, stamp, previous in observations:
            if stamp is not None:
                finite_number(stamp, name)
                if stamp < 0 or stamp > now or (previous is not None and stamp < previous):
                    raise ValueError(f"{name} must not regress or be in the future")
        if obstacle_distance is not None and finite_number(obstacle_distance, "obstacle_distance") < 0:
            raise ValueError("obstacle_distance must be nonnegative")
        if self.started_at is None:
            self.started_at = now
        if self.state in TERMINAL:
            self.stamp = now
            return self.snapshot(now, "terminal_hold")

        # Integrate only while BOTH previous observations remain fresh.
        expiry = None
        if self.odom_stamp is not None and self.obstacle_stamp is not None:
            expiry = min(self.odom_stamp, self.obstacle_stamp) + self.input_timeout
        self.advance(now if expiry is None else min(now, expiry))
        self.stamp = now
        if expiry is not None and now >= expiry - EPS:
            self.finish("ABORTED", expiry, "input_timeout")
            return self.snapshot(now, "input_timeout")

        if odom_stamp is not None:
            self.odom_stamp = float(odom_stamp)
        if obstacle_stamp is not None:
            self.obstacle_stamp = float(obstacle_stamp)
        if obstacle_distance is not None:
            self.obstacle_distance = float(obstacle_distance)
        if cancel:
            self.finish("CANCELED", now, "cancel_requested")
            return self.snapshot(now, "cancel")
        if self.odom_stamp is None or self.obstacle_stamp is None or self.obstacle_distance is None:
            self.finish("ABORTED", now, "missing_input")
            return self.snapshot(now, "missing_input")
        if now - min(self.odom_stamp, self.obstacle_stamp) >= self.input_timeout - EPS:
            self.finish("ABORTED", now, "input_timeout")
            return self.snapshot(now, "input_timeout")

        event = "tick"
        if self.state == "MOVING" and self.obstacle_distance < self.stop_distance:
            self.state, event = "WAITING", "obstacle_stop"
        elif self.state == "WAITING" and self.obstacle_distance > self.clear_distance:
            self.state, event = "MOVING", "obstacle_clear"
        while self.index < len(self.waypoints) and self.distance() <= EPS:
            self.pose[:2] = self.waypoints[self.index][:]
            self.waypoint_logs.append({"time": round(now, 10), "index": self.index,
                                       "waypoint": self.waypoints[self.index][:], "pose": self.pose[:]})
            self.index += 1
            event = "waypoint_reached"
        if self.index == len(self.waypoints):
            self.finish("SUCCEEDED", now, "all_waypoints_reached")
            event = "succeeded"
        elif self.state == "WAITING":
            self.velocity = [0.0, 0.0, 0.0]
        else:
            distance = self.distance()
            speed = min(self.max_speed, distance / self.dt)
            target = self.waypoints[self.index]
            self.velocity = [speed * ((target[0] - self.pose[0]) / distance),
                             speed * ((target[1] - self.pose[1]) / distance), 0.0]
        return self.snapshot(now, event)


def check_contract(report, expected):
    """Compare fixed-case expectations and stopped output, without ROS claims."""
    errors = []
    try:
        json.dumps(report, allow_nan=False)
    except (ValueError, TypeError):
        errors.append("report must contain finite JSON values")
    def vector3(value):
        return (isinstance(value, (list, tuple)) and len(value) == 3
                and all(type(v) in (int, float) and math.isfinite(v) for v in value))
    events = report.get("events")
    if (not isinstance(events, list) or not events
            or any(not isinstance(event, dict) or not vector3(event.get("pose"))
                   or not vector3(event.get("velocity")) for event in events)):
        errors.append("every event needs a three-dimensional finite pose and velocity")
        return {"passed": False, "errors": errors, "scope": "offline protocol only"}
    result = report["result"]
    for field in ["state", "reached_points"]:
        if result[field] != expected[field]:
            errors.append(f"unexpected {field}")
    if abs(result["total_time"] - expected["total_time"]) > 1e-8:
        errors.append("unexpected total_time")
    if any(abs(a - b) > 1e-8 for a, b in zip(report["events"][-1]["pose"], expected["pose"])):
        errors.append("unexpected final pose")
    log_times = [row["time"] for row in report["waypoint_logs"]]
    if len(log_times) != len(expected["waypoint_times"]) or any(
            abs(a - b) > 1e-8 for a, b in zip(log_times, expected["waypoint_times"])):
        errors.append("unexpected waypoint log times")
    frozen = None
    for event in report["events"]:
        if math.hypot(*event["velocity"][:2]) > report["parameters"]["max_speed"] + 1e-8:
            errors.append("velocity exceeds the speed limit")
        if event["state"] == "WAITING" or event["state"] in TERMINAL:
            if event["velocity"] != [0.0, 0.0, 0.0]:
                errors.append("stopped state has nonzero velocity")
        if event["state"] in TERMINAL:
            if frozen is None:
                frozen = event["pose"]
            if event["pose"] != frozen:
                errors.append("terminal pose moved")
    return {"passed": not errors, "errors": errors, "scope": "offline protocol only"}


def run_scenario(name):
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    if name not in cases["scenarios"]:
        raise ValueError("unknown scenario; choose normal, obstacle, cancel or timeout")
    case = cases["scenarios"][name]
    model = Patrol(cases["waypoints"], **cases["parameters"])
    events = []
    terminal_tick = None
    for i in range(101):
        now = round(i * model.dt, 10)
        updates = {}
        if now <= case.get("last_input_at", math.inf):
            distance = case["obstacles"][0][1]
            for at, value in case["obstacles"]:
                if now >= at:
                    distance = value
            updates = {"odom_stamp": now, "obstacle_stamp": now, "obstacle_distance": distance}
        events.append(model.tick(now, cancel=now == case.get("cancel_at"), **updates))
        if model.state in TERMINAL:
            if terminal_tick is None:
                terminal_tick = i
            if i >= terminal_tick + 5:  # Fresh input after cancel cannot restart it.
                break
    if model.result is None:
        raise ValueError("scenario exceeded the 10-second teaching horizon")
    report = {"scenario": name, "scope": "synthetic offline; ROS and hardware untested",
              "parameters": cases["parameters"], "events": events,
              "waypoint_logs": model.waypoint_logs, "result": model.result}
    report["contract"] = check_contract(report, case["expected"])
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, choices=["normal", "obstacle", "cancel", "timeout"])
    parser.add_argument("--json", action="store_true", help="emit the complete machine-readable report")
    args = parser.parse_args(argv)
    try:
        report = run_scenario(args.scenario)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"invalid teaching input: {exc}\n")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    else:
        print(report["scope"])
        for e in report["events"]:
            print(f"t={e['time']:.1f} event={e['event']} state={e['state']} "
                  f"velocity={e['velocity']} pose={e['pose']} feedback={e['feedback']}")
        for row in report["waypoint_logs"]:
            print("waypoint_log=" + json.dumps(row, ensure_ascii=False, allow_nan=False))
        print("result=" + json.dumps(report["result"], ensure_ascii=False, allow_nan=False))
        print("contract=" + json.dumps(report["contract"], ensure_ascii=False, allow_nan=False))
    return 0 if report["contract"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
