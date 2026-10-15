"""Recompute three synthetic navigation comparisons using Python's standard library.

The estimator receives only measured positions, dt and its stated model parameters.
Ground truth is used to generate the teaching observations and score outputs.
No ROS, physical robot, stochastic generator, plotting package or network is used.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
from pathlib import Path

BLUE = "#0072B2"       # Okabe-Ito blue: correct / filtered
ORANGE = "#D55E00"     # Okabe-Ito vermillion: perturbed / difference
INK = "#253346"
GRAY = "#64748B"
LIGHT = "#E2E8F0"
HERE = Path(__file__).resolve().parent


def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def vector(value, length, name):
    if not isinstance(value, (list, tuple)) or len(value) != length:
        raise ValueError(f"{name} must contain {length} numbers")
    return [number(v, name) for v in value]


def transform_point(point, translation, yaw_deg):
    """p_base = R(yaw) p_lidar + t, with metres and degrees at this boundary."""
    x, y = vector(point, 2, "point")
    tx, ty = vector(translation, 2, "translation")
    angle = math.radians(number(yaw_deg, "yaw_deg"))
    result = (math.cos(angle) * x - math.sin(angle) * y + tx,
              math.sin(angle) * x + math.cos(angle) * y + ty)
    return tuple(number(v, "transformed point") for v in result)


def map_cell_center(col, image_row, height, resolution, origin):
    """Image row 0 is north; grid row 0 is south. Return centre in map metres."""
    ox, oy, yaw = vector(origin, 3, "map origin")
    local = ((col + 0.5) * resolution, (height - 1 - image_row + 0.5) * resolution)
    return transform_point(local, (ox, oy), math.degrees(yaw))


def kalman_velocity(measured_positions, dt, config):
    """1D constant-velocity KF, state [position, velocity], H=[1,0].

    Q = acceleration_variance * [[dt**4/4, dt**3/2], [dt**3/2, dt**2]].
    P is updated in Joseph form to preserve symmetry and numerical stability.
    The first position initializes x; the stated initial velocity initializes v.
    """
    dt = number(dt, "dt_s")
    if dt <= 0:
        raise ValueError("dt_s must be positive")
    if not isinstance(measured_positions, (list, tuple)) or len(measured_positions) < 2:
        raise ValueError("measured_positions needs at least two samples")
    observations = [number(z, "measured position") for z in measured_positions]
    x = observations[0]
    v = number(config["initial_velocity_m_s"], "initial velocity")
    p00 = number(config["initial_position_variance_m2"], "initial position variance")
    p11 = number(config["initial_velocity_variance_m2_s2"], "initial velocity variance")
    r = number(config["measurement_variance_m2"], "measurement variance")
    acceleration_variance = number(config["acceleration_variance_m2_s4"], "acceleration variance")
    if r <= 0 or min(p00, p11, acceleration_variance) < 0:
        raise ValueError("measurement variance must be positive; P0 and acceleration variance nonnegative")
    p01 = p10 = 0.0
    q00, q01, q11 = (acceleration_variance * dt**4 / 4,
                      acceleration_variance * dt**3 / 2,
                      acceleration_variance * dt**2)
    velocities = [v]
    for z in observations[1:]:
        x += dt * v
        a = p00 + dt * (p01 + p10) + dt * dt * p11 + q00
        b = p01 + dt * p11 + q01
        c = p10 + dt * p11 + q01
        d = p11 + q11
        innovation_variance = number(a + r, "innovation variance")
        if innovation_variance <= 0:
            raise ValueError("innovation variance must be positive")
        k0, k1 = a / innovation_variance, c / innovation_variance
        innovation = z - x
        x += k0 * innovation
        v += k1 * innovation
        # (I-KH) P_pred (I-KH)^T + K R K^T.
        p00 = (1 - k0)**2 * a + k0 * k0 * r
        p01 = (1 - k0) * (b - k1 * a) + k0 * k1 * r
        p10 = (1 - k0) * (c - k1 * a) + k1 * k0 * r
        p11 = d - k1 * (b + c) + k1 * k1 * a + k1 * k1 * r
        for value in (x, v, p00, p01, p10, p11):
            number(value, "Kalman output")
        velocities.append(v)
    return velocities


def validate_inputs(inputs):
    """Validate the complete teaching input before any output directory is created."""
    try:
        if inputs["schema_version"] != 1 or inputs["synthetic"] is not True:
            raise ValueError("schema_version=1 and synthetic=true are required")
        tf = inputs["tf"]
        vector(tf["translation_m"], 2, "translation_m")
        number(tf["correct_yaw_deg"], "correct_yaw_deg")
        number(tf["yaw_error_deg"], "yaw_error_deg")
        if not isinstance(tf["points_lidar_m"], list) or len(tf["points_lidar_m"]) < 2:
            raise ValueError("points_lidar_m needs at least two points")
        for point in tf["points_lidar_m"]:
            vector(point, 2, "lidar point")
        if not math.isclose(math.hypot(*tf["points_lidar_m"][0]), 1.0, abs_tol=1e-12):
            raise ValueError("first lidar point must be exactly 1 m from the lidar origin")
        grid = inputs["map"]
        resolution = number(grid["resolution_m"], "resolution_m")
        if resolution <= 0:
            raise ValueError("resolution_m must be positive")
        vector(grid["origin_m_rad"], 3, "origin_m_rad")
        vector(grid["origin_shift_m"], 2, "origin_shift_m")
        rows = grid["rows_north_first"]
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], str) or not rows[0]:
            raise ValueError("rows_north_first must be nonempty binary strings")
        if any(not isinstance(row, str) or len(row) != len(rows[0]) or set(row) - {"0", "1"} for row in rows):
            raise ValueError("map rows must have equal width and use only 0/1")
        cell = grid["marked_image_cell"]
        if not isinstance(cell, list) or len(cell) != 2 or any(type(v) is not int for v in cell):
            raise ValueError("marked_image_cell must contain two integer indices")
        col, row = cell
        if not (0 <= col < len(rows[0]) and 0 <= row < len(rows)):
            raise ValueError("marked_image_cell is outside the map")
        if rows[row][col] != "1":
            raise ValueError("marked_image_cell must be occupied")
        velocity = inputs["velocity"]
        if number(velocity["dt_s"], "dt_s") <= 0:
            raise ValueError("dt_s must be positive")
        number(velocity["true_initial_position_m"], "true_initial_position_m")
        number(velocity["true_velocity_m_s"], "true_velocity_m_s")
        noise = velocity["position_noise_m"]
        if not isinstance(noise, list) or len(noise) < 2:
            raise ValueError("position_noise_m needs at least two samples")
        for n in noise:
            number(n, "position noise")
        # Also validates every KF parameter, without using synthetic truth.
        kalman_velocity([0.0, 0.0], velocity["dt_s"], velocity["kalman"])
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError(f"invalid comparison input: {exc}") from exc


def errors(values, truth):
    residuals = [v - truth for v in values]
    return (math.sqrt(sum(e * e for e in residuals) / len(residuals)),
            sum(abs(e) for e in residuals) / len(residuals))


def build_report(inputs):
    validate_inputs(inputs)
    tf, grid, velocity = inputs["tf"], inputs["map"], inputs["velocity"]
    correct = [transform_point(p, tf["translation_m"], tf["correct_yaw_deg"]) for p in tf["points_lidar_m"]]
    perturbed = [transform_point(p, tf["translation_m"], tf["correct_yaw_deg"] + tf["yaw_error_deg"]) for p in tf["points_lidar_m"]]
    point_errors = [math.dist(p, q) for p, q in zip(correct, perturbed)]
    shifted_origin = [grid["origin_m_rad"][0] + grid["origin_shift_m"][0],
                      grid["origin_m_rad"][1] + grid["origin_shift_m"][1], grid["origin_m_rad"][2]]
    col, row = grid["marked_image_cell"]
    center = map_cell_center(col, row, len(grid["rows_north_first"]), grid["resolution_m"], grid["origin_m_rad"])
    shifted_center = map_cell_center(col, row, len(grid["rows_north_first"]), grid["resolution_m"], shifted_origin)
    times = [k * velocity["dt_s"] for k in range(len(velocity["position_noise_m"]))]
    truth_positions = [velocity["true_initial_position_m"] + velocity["true_velocity_m_s"] * t for t in times]
    measured = [p + n for p, n in zip(truth_positions, velocity["position_noise_m"])]
    difference = [(right - left) / velocity["dt_s"] for left, right in zip(measured, measured[1:])]
    filtered = kalman_velocity(measured, velocity["dt_s"], velocity["kalman"])
    raw_rmse, raw_mae = errors(difference, velocity["true_velocity_m_s"])
    kf_rmse, kf_mae = errors(filtered[1:], velocity["true_velocity_m_s"])
    normalized = json.dumps(inputs, sort_keys=True, separators=(",", ":"), allow_nan=False)
    report = {
        "synthetic": True,
        "scope": "Synthetic teaching comparison; no physical estimator or localization claim.",
        "input_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        "inputs": inputs,
        "profile": {"tf_point_count": len(correct), "map_size_cells": [len(grid["rows_north_first"][0]), len(grid["rows_north_first"])],
                    "occupied_cells": sum(row.count("1") for row in grid["rows_north_first"]),
                    "position_samples": len(measured), "missing_values": 0,
                    "noise_range_m": [min(velocity["position_noise_m"]), max(velocity["position_noise_m"])],
                    "position_noise_mean_m": sum(velocity["position_noise_m"]) / len(measured)},
        "tf": {"correct_points_base_m": correct, "perturbed_points_base_m": perturbed,
               "point_errors_m": point_errors, "one_metre_point_error_m": point_errors[0],
               "maximum_point_error_m": max(point_errors), "error_definition": "Euclidean distance between two transforms of each identical point"},
        "map": {"correct_origin_m_rad": grid["origin_m_rad"], "perturbed_origin_m_rad": shifted_origin,
                "marked_center_correct_m": center, "marked_center_perturbed_m": shifted_center,
                "marked_displacement_m": math.dist(center, shifted_center),
                "shift_cells": [v / grid["resolution_m"] for v in grid["origin_shift_m"]]},
        "velocity": {"dt_s": velocity["dt_s"], "times_s": times, "true_positions_m": truth_positions,
                     "true_velocity_m_s": velocity["true_velocity_m_s"], "measured_positions_m": measured,
                     "difference_velocity_m_s": difference, "difference_times_s": times[1:],
                     "kalman_velocity_m_s": filtered,
                     "metrics": {"scored_samples": len(difference),
                                 "scoring_window": f"k=1..{len(difference)}; initialization k=0 excluded from both",
                                 "difference_rmse_m_s": raw_rmse, "difference_mae_m_s": raw_mae,
                                 "kalman_rmse_m_s": kf_rmse, "kalman_mae_m_s": kf_mae}},
    }
    # JSON serialization is also the final finite-number gate. Return JSON-native lists.
    return json.loads(json.dumps(report, allow_nan=False))


def fmt(value):
    return f"{number(value, 'SVG coordinate'):.3f}".rstrip("0").rstrip(".") or "0"


class SVG:
    def __init__(self, title, width=960, height=650):
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
                      f"<title>{html.escape(title)}</title>",
                      "<desc>Synthetic teaching data. Geometry axes use metres; velocity axes use seconds and metres per second.</desc>",
                      '<rect width="100%" height="100%" fill="white"/>',
                      '<g font-family="Arial, sans-serif" font-size="15" fill="' + INK + '">']

    def text(self, x, y, label, size=15, anchor="start", weight="normal", rotation=None):
        turn = f' transform="rotate({rotation} {fmt(x)} {fmt(y)})"' if rotation is not None else ""
        self.parts.append(f'<text x="{fmt(x)}" y="{fmt(y)}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}"{turn}>{html.escape(str(label))}</text>')

    def line(self, points, color=INK, width=2, dash=None, closed=False, fill="none"):
        tag = "polygon" if closed else "polyline"
        coords = " ".join(f"{fmt(x)},{fmt(y)}" for x, y in points)
        style = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<{tag} points="{coords}" fill="{fill}" stroke="{color}" stroke-width="{width}"{style}/>')

    def marker(self, x, y, color, cross=False, radius=4):
        if cross:
            self.line([(x - radius, y - radius), (x + radius, y + radius)], color)
            self.line([(x - radius, y + radius), (x + radius, y - radius)], color)
        else:
            self.parts.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{radius}" fill="white" stroke="{color}" stroke-width="2"/>')

    def finish(self):
        return "\n".join(self.parts + ["</g></svg>\n"])


def bounds(points, square=False):
    xs, ys = zip(*points)
    xspan, yspan = max(max(xs) - min(xs), 0.5), max(max(ys) - min(ys), 0.5)
    if square:
        xspan = yspan = max(xspan, yspan)
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    return (cx - xspan * 0.65, cx + xspan * 0.65, cy - yspan * 0.65, cy + yspan * 0.65)


def ticks(low, high):
    target = (high - low) / 5
    base = 10 ** math.floor(math.log10(target))
    step = next(factor * base for factor in (1, 2, 5, 10) if factor * base >= target)
    return [k * step for k in range(math.ceil(low / step), math.floor(high / step) + 1)]


class Axes:
    def __init__(self, svg, x, y, width, height, limits, xlabel, ylabel, equal=False):
        self.svg = svg
        self.xmin, self.xmax, self.ymin, self.ymax = limits
        if equal:
            scale = min(width / (self.xmax - self.xmin), height / (self.ymax - self.ymin))
            actual_w, actual_h = scale * (self.xmax - self.xmin), scale * (self.ymax - self.ymin)
            x += (width - actual_w) / 2
            y += (height - actual_h) / 2
            width, height = actual_w, actual_h
        self.x, self.y, self.width, self.height = x, y, width, height
        for tick in ticks(self.xmin, self.xmax):
            px, _ = self.point(tick, self.ymin)
            svg.line([(px, y), (px, y + height)], LIGHT, 1)
            svg.text(px, y + height + 24, f"{tick:g}", 13, "middle")
        for tick in ticks(self.ymin, self.ymax):
            _, py = self.point(self.xmin, tick)
            svg.line([(x, py), (x + width, py)], LIGHT, 1)
            svg.text(x - 12, py + 4, f"{tick:g}", 13, "end")
        svg.line([(x, y), (x, y + height), (x + width, y + height)], GRAY, 1.5)
        svg.text(x + width / 2, y + height + 50, xlabel, 15, "middle")
        svg.text(x - 48, y + height / 2, ylabel, 15, "middle", rotation=-90)

    def point(self, x, y):
        return (self.x + (x - self.xmin) / (self.xmax - self.xmin) * self.width,
                self.y + self.height - (y - self.ymin) / (self.ymax - self.ymin) * self.height)

    def plot(self, pairs, color, width=2, dash=None):
        self.svg.line([self.point(x, y) for x, y in pairs], color, width, dash)


def legend(svg, x, y, label, color, dash=None, cross=False):
    svg.line([(x, y - 5), (x + 34, y - 5)], color, 2.3, dash)
    svg.marker(x + 17, y - 5, color, cross, 3)
    svg.text(x + 45, y, label, 14)


def tf_figure(report):
    tf = report["tf"]
    source = report["inputs"]["tf"]
    correct, perturbed = tf["correct_points_base_m"], tf["perturbed_points_base_m"]
    svg = SVG("Synthetic TF yaw comparison")
    svg.text(42, 38, "TF yaw: same point set, one changed angle", 23, weight="bold")
    svg.text(42, 68, "Synthetic geometry | base coordinates | equal scale on x and y", 15)
    limits = bounds(correct + perturbed + [[0, 0], source["translation_m"]], square=True)
    axes = Axes(svg, 85, 110, 470, 470, limits, "x in base (m)", "y in base (m)", equal=True)
    axes.plot(correct[1:], BLUE, 2.5)
    axes.plot(perturbed[1:], ORANGE, 2.5, "7 5")
    for p, q in zip(correct, perturbed):
        axes.plot([p, q], GRAY, 1, "2 3")
        svg.marker(*axes.point(*p), BLUE)
        svg.marker(*axes.point(*q), ORANGE, cross=True)
    svg.marker(*axes.point(0, 0), INK, radius=5)
    svg.text(*[v + offset for v, offset in zip(axes.point(0, 0), (10, 22))], "base origin", 13)
    svg.marker(*axes.point(*source["translation_m"]), GRAY, cross=True, radius=5)
    legend(svg, 605, 142, f"Correct yaw {source['correct_yaw_deg']:g} deg", BLUE)
    legend(svg, 605, 181, f"Yaw error {source['yaw_error_deg']:+g} deg", ORANGE, "7 5", True)
    svg.text(605, 229, f"n = {len(correct)} identical lidar points", 14)
    svg.text(605, 267, "First point: lidar range = 1 m", 15, weight="bold")
    svg.text(605, 299, f"Position error = {tf['one_metre_point_error_m']:.5f} m", 15)
    svg.text(605, 331, f"{source['yaw_error_deg']:g} deg = {math.radians(source['yaw_error_deg']):.6f} rad", 14)
    svg.text(605, 363, "2 r sin(|yaw error| / 2)", 15)
    svg.text(605, 409, "Installation translation is held fixed.", 14)
    svg.text(605, 437, "Wall points tilt around the lidar origin.", 14)
    svg.text(42, 637, "Synthetic input; this geometric comparison does not demonstrate real localization accuracy.", 14)
    return svg.finish()


def map_corners(grid, origin):
    width, height = len(grid["rows_north_first"][0]), len(grid["rows_north_first"])
    r = grid["resolution_m"]
    return [transform_point(p, origin[:2], math.degrees(origin[2])) for p in [(0, 0), (width * r, 0), (width * r, height * r), (0, height * r)]]


def map_figure(report):
    grid, result = report["inputs"]["map"], report["map"]
    svg = SVG("Synthetic map origin comparison", height=610)
    svg.text(42, 38, "Map origin: same cells, changed map coordinates", 23, weight="bold")
    svg.text(42, 68, "Synthetic occupancy | north-first image | same axes and equal metre scale", 15)
    limits = bounds(map_corners(grid, result["correct_origin_m_rad"]) + map_corners(grid, result["perturbed_origin_m_rad"]))
    height, resolution = len(grid["rows_north_first"]), grid["resolution_m"]
    reference = result["marked_center_correct_m"]
    for left, origin, color, dash, label in [
        (85, result["correct_origin_m_rad"], BLUE, None, "a  Correct origin"),
        (550, result["perturbed_origin_m_rad"], ORANGE, "6 4", "b  Shifted origin"),
    ]:
        svg.text(left, 109, label, 17, weight="bold")
        svg.text(left, 138, f"origin = [{origin[0]:g}, {origin[1]:g}, {origin[2]:g}] m, m, rad", 14)
        axes = Axes(svg, left, 164, 345, 280, limits, "x in map (m)", "y in map (m)", equal=True)
        for row, cells in enumerate(grid["rows_north_first"]):
            for col, occupied in enumerate(cells):
                if occupied == "1":
                    south = height - 1 - row
                    vertices = [(col * resolution, south * resolution), ((col + 1) * resolution, south * resolution),
                                ((col + 1) * resolution, (south + 1) * resolution), (col * resolution, (south + 1) * resolution)]
                    points = [axes.point(*transform_point(p, origin[:2], math.degrees(origin[2]))) for p in vertices]
                    svg.line(points, "white", 0.5, closed=True, fill=GRAY)
        svg.line([axes.point(*p) for p in map_corners(grid, origin)], color, 2.5, dash, closed=True)
        center = map_cell_center(*grid["marked_image_cell"], height, resolution, origin)
        svg.marker(*axes.point(*reference), BLUE, radius=6)
        svg.marker(*axes.point(*center), color, cross=True, radius=6)
    legend(svg, 85, 523, "Fixed reference coordinate", BLUE)
    legend(svg, 550, 523, "Marked cell centre after shift", ORANGE, "6 4", True)
    svg.text(42, 560, f"{len(grid['rows_north_first'][0])} x {height} cells | resolution = {resolution:g} m/cell | shift = {result['marked_displacement_m']:.2f} m = [{result['shift_cells'][0]:g}, {result['shift_cells'][1]:g}] cells", 15)
    svg.text(42, 590, "The coordinate assignment changes; the obstacles have not physically moved. No real venue measurements.", 14)
    return svg.finish()


def velocity_figure(report):
    result, source = report["velocity"], report["inputs"]["velocity"]
    metrics = result["metrics"]
    svg = SVG("Synthetic position-noise and Kalman velocity comparison", height=775)
    svg.text(42, 38, "Position noise: differentiate, then estimate velocity", 23, weight="bold")
    svg.text(42, 68, f"Synthetic fixed sequence | dt = {source['dt_s']:g} s | n = {len(result['times_s'])} positions", 15)
    t = result["times_s"]
    svg.text(85, 110, "a  Same position observations feed both methods", 17, weight="bold")
    limits = bounds(list(zip(t, result["true_positions_m"])) + list(zip(t, result["measured_positions_m"])))
    # Time axes begin at the first observed time; y includes all measurements.
    axes = Axes(svg, 85, 137, 595, 182, (t[0], t[-1], limits[2], limits[3]), "time (s)", "position (m)")
    axes.plot(list(zip(t, result["true_positions_m"])), INK, 2, "8 4")
    for time, position in zip(t, result["measured_positions_m"]):
        svg.marker(*axes.point(time, position), ORANGE, radius=2.5)
    legend(svg, 715, 163, "Synthetic truth", INK, "8 4")
    legend(svg, 715, 202, "Noisy position", ORANGE)
    svg.text(85, 404, "b  Every velocity output, including initialization", 17, weight="bold")
    pairs = list(zip(result["difference_times_s"], result["difference_velocity_m_s"]))
    filtered_pairs = list(zip(t, result["kalman_velocity_m_s"]))
    limits = bounds(pairs + filtered_pairs + [(t[0], result["true_velocity_m_s"]), (t[-1], result["true_velocity_m_s"])])
    axes = Axes(svg, 85, 430, 595, 192, (t[0], t[-1], limits[2], limits[3]), "time (s)", "velocity (m/s)")
    axes.plot([(t[0], result["true_velocity_m_s"]), (t[-1], result["true_velocity_m_s"])], INK, 2, "8 4")
    axes.plot(pairs, ORANGE, 1.6, "4 3")
    axes.plot(filtered_pairs, BLUE, 2.4)
    for time, v in filtered_pairs[::4]:
        svg.marker(*axes.point(time, v), BLUE, radius=2.5)
    legend(svg, 715, 456, f"Truth ({result['true_velocity_m_s']:g} m/s)", INK, "8 4")
    legend(svg, 715, 495, "Position difference", ORANGE, "4 3", True)
    legend(svg, 715, 534, "CV Kalman estimate", BLUE)
    svg.text(715, 575, f"RMSE, k = 1..{metrics['scored_samples']} (m/s)", 14, weight="bold")
    svg.text(715, 604, f"Difference: {metrics['difference_rmse_m_s']:.4f}", 14)
    svg.text(715, 633, f"Kalman:     {metrics['kalman_rmse_m_s']:.4f}", 14)
    svg.text(42, 714, f"Difference describes the preceding {source['dt_s']:g} s interval; it is plotted at its end time. KF is causal.", 14)
    svg.text(42, 742, "Constant-velocity teaching model; lower error on this input is no physical estimator claim.", 14)
    return svg.finish()


def generate(inputs, output_dir):
    report = build_report(inputs)
    files = {"tf-yaw-comparison.svg": tf_figure(report), "map-origin-comparison.svg": map_figure(report),
             "velocity-noise-comparison.svg": velocity_figure(report),
             "comparison_report.json": json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"}
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        (output_dir / name).write_text(content, encoding="utf-8", newline="\n")
    return report


def main():
    parser = argparse.ArgumentParser(description="Generate three deterministic SVG comparisons from synthetic inputs (Python 3.10+, stdlib only).")
    parser.add_argument("--input", type=Path, default=HERE / "comparison_inputs.json", help="synthetic JSON input (default: alongside this script)")
    parser.add_argument("--output-dir", type=Path, required=True, help="new, nonexistent output directory for three SVG files and comparison_report.json")
    args = parser.parse_args()
    try:
        inputs = json.loads(args.input.read_text(encoding="utf-8"))
        report = generate(inputs, args.output_dir)
    except (OSError, ValueError, OverflowError) as exc:
        parser.error(f"cannot generate comparisons: {exc}")
    print(f"Synthetic comparisons generated in {args.output_dir}")
    print(f"1 m point / yaw error: {report['tf']['one_metre_point_error_m']:.8f} m")
    print(f"Map marked-cell displacement: {report['map']['marked_displacement_m']:.3f} m")
    metrics = report["velocity"]["metrics"]
    print(f"Velocity RMSE (same k=1..{metrics['scored_samples']}): difference={metrics['difference_rmse_m_s']:.6f}, Kalman={metrics['kalman_rmse_m_s']:.6f} m/s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
