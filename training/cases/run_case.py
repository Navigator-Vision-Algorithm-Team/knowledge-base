#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# State-machine teaching adaptation of fake_vel_transform.cpp,
# Copyright 2025 Lihan Chen. See training/LICENSE and README.md.
"""Deterministic teaching models, not ROS nodes, DDS traces or robot evidence."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys


SOURCE_SHA = "183a4109b0de2030bb8970a54654937c8b039ba9"
EPSILON = 1e-5
CONTROLLER_TIMEOUT = 0.5


def finite(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("all numbers must be finite")
    return number


def twist3(value):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError("twist must contain [vx, vy, wz]")
    return [finite(component) for component in value]


def is_zero(twist):
    return all(abs(component) < EPSILON for component in twist)


def check_mode(mode):
    if mode not in ("broken", "fixed"):
        raise ValueError("mode must be broken or fixed")


def resolve_topic(namespace, topic):
    """Only ordinary relative/absolute names; no remap, private name or DDS."""
    if not isinstance(topic, str) or not topic or topic.startswith("~"):
        raise ValueError("use an ordinary nonempty topic name")
    if not isinstance(namespace, str) or not namespace.startswith("/"):
        raise ValueError("namespace must be absolute")
    return topic if topic.startswith("/") else namespace.rstrip("/") + "/" + topic


def run_topic(data, mode):
    check_mode(mode)
    publisher = resolve_topic(data["namespace"], data["publisher"])
    subscriber = resolve_topic(data["namespace"], data["subscriber_" + mode])
    sequence = data["sequence"]
    if not isinstance(sequence, list) or not sequence:
        raise ValueError("sequence must contain at least one event")
    rows = [{"index": index, "sequence": value, "publisher": publisher,
             "subscriber": subscriber, "delivered": publisher == subscriber}
            for index, value in enumerate(sequence)]
    received = sum(row["delivered"] for row in rows)
    return rows, {"publisher": publisher, "subscriber": subscriber,
                  "sent": len(rows), "received": received,
                  "contract_passed": received == len(rows)}


class CacheModel:
    """Ordered callback model with a known initial yaw and no active local plan.

    A sync event means only syncCallback was invoked; event arrival and
    message_filters pairing are outside this model. No threads, TF, clocks,
    robot motion or input watchdog are simulated.
    """

    def __init__(self, mode, yaw, spin):
        check_mode(mode)
        self.mode = mode
        self.yaw = finite(yaw)
        self.spin = finite(spin)
        self.cache = None
        self.last_plan = None
        self.last_at = None
        self.branch = "initial"

    def transform(self, twist):
        vx, vy, wz = twist
        return [vx * math.cos(self.yaw) + vy * math.sin(self.yaw),
                -vx * math.sin(self.yaw) + vy * math.cos(self.yaw), wz + self.spin]

    def step(self, event):
        at = finite(event["at"])
        if at < 0 or (self.last_at is not None and at < self.last_at):
            raise ValueError("event times must be nonnegative and ordered")
        kind = event["event"]
        if kind == "local_plan":
            self.last_plan = at
            self.branch = "plan_activity"
            output = None
        elif kind == "spin":
            self.spin = finite(event["value"])
            self.branch = "spin_member_only"
            output = None
        elif kind == "command":
            twist = twist3(event["twist"])
            zero = is_zero(twist)
            inactive = self.last_plan is None or at - self.last_plan > CONTROLLER_TIMEOUT
            if zero or inactive:
                # The sole repair: invalidate the old cache on a zero command.
                if zero and self.mode == "fixed":
                    self.cache = None
                self.branch = "zero_immediate" if zero else "inactive_immediate"
                output = self.transform(twist)
            else:
                self.cache = twist
                self.branch = "cache_command"
                output = None
        elif kind == "sync":
            yaw = finite(event["yaw"])
            if self.cache is None:
                self.branch = "sync_no_cache"
                output = None
            else:
                self.yaw = yaw
                self.branch = "sync_cached"
                output = self.transform(self.cache)
        else:
            raise ValueError("unknown event: " + str(kind))
        self.last_at = at
        return output


def run_stale(data, mode):
    model = CacheModel(mode, data["initial_yaw"], data["initial_spin"])
    rows = []
    after_zero = False
    zero_commands = 0
    post_zero_syncs = 0
    resumed_outputs = 0
    for index, event in enumerate(data["events"]):
        before = None if model.cache is None else list(model.cache)
        output = model.step(event)
        if event["event"] == "command":
            after_zero = is_zero(twist3(event["twist"]))
            zero_commands += int(after_zero)
        stopped_sync = after_zero and event["event"] == "sync"
        post_zero_syncs += int(stopped_sync)
        stale = stopped_sync and before is not None and not is_zero(before) and output is not None
        if zero_commands and not after_zero and output is not None and not is_zero(output):
            resumed_outputs += 1
        rows.append({"index": index, "input": event, "branch": model.branch,
                     "cache_before": before,
                     "cache_after": None if model.cache is None else list(model.cache),
                     "output": output, "stale_reissue": stale})
    stale_reissues = sum(row["stale_reissue"] for row in rows)
    report = {"event_count": len(rows), "outputs": sum(row["output"] is not None for row in rows),
              "zero_commands": zero_commands, "post_zero_syncs": post_zero_syncs,
              "stale_reissues": stale_reissues, "resumed_nonzero_outputs": resumed_outputs,
              "contract_passed": (zero_commands > 0 and post_zero_syncs > 0
                                  and stale_reissues == 0 and resumed_outputs > 0)}
    return rows, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=("topic-mismatch", "stale-command"))
    parser.add_argument("--mode", choices=("broken", "fixed"), required=True)
    parser.add_argument("--input", type=Path, help="default: cases/inputs/<case>.json")
    parser.add_argument("--out-dir", type=Path, required=True, help="new evidence directory")
    parser.add_argument("--check-contract", action="store_true",
                        help="exit 1 when the teaching contract fails (broken is expected to fail)")
    args = parser.parse_args(argv)
    source = args.input or Path(__file__).resolve().parent / "inputs" / (args.case + ".json")
    try:
        payload = source.read_bytes()
        data = json.loads(payload)
        run = run_topic if args.case == "topic-mismatch" else run_stale
        rows, report = run(data, args.mode)
        report.update({"case": args.case, "mode": args.mode,
                       "evidence_kind": "synthetic_python_teaching_model",
                       "source_reference_sha": SOURCE_SHA,
                       "input_sha256": hashlib.sha256(payload).hexdigest()})
        # New directories preserve earlier evidence and make reruns explicit.
        args.out_dir.mkdir(parents=True, exist_ok=False)
        with (args.out_dir / "events.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
            for row in rows:
                stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
        with (args.out_dir / "report.json").open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 1 if args.check_contract and not report["contract_passed"] else 0


if __name__ == "__main__":
    sys.exit(main())
