#!/usr/bin/env bash
# Query ROS and write reports. Never send robot-control commands.

nav_workspace=${NAV_WORKSPACE:-}
serial_workspace=${SERIAL_WORKSPACE:-}
robot_namespace=${ROBOT_NS:-/red_standard_robot1}
serial_node=${SERIAL_NODE:-/rm_serial_driver}
report_root=${NAV_DEBUG_REPORT_ROOT:-"$HOME/nav_debug_reports"}
full_mode=0

usage() {
  printf '%s\n' \
    'Usage: bash collect_navigation_debug.sh [options]' \
    '  --namespace /robot     ROS namespace (default: /red_standard_robot1)' \
    '  --nav-workspace PATH   Explicit navigation workspace to source' \
    '  --serial-workspace PATH  Optional explicit serial workspace to source' \
    '  --serial-node /node    Optional serial node to inspect' \
    '  --report-root PATH     Report directory (default: $HOME/nav_debug_reports)' \
    '  --full                 Also sample topic rates and TF continuously' \
    '  --help                 Show usage without writing a report' \
    'Without workspace options, use the already sourced terminal environment.' \
    'Missing optional interfaces are recorded, not assumed to be present.'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help) usage; exit 0 ;;
    --full) full_mode=1; shift ;;
    --namespace|--nav-workspace|--serial-workspace|--serial-node|--report-root)
      if [[ $# -lt 2 || -z "$2" || "$2" == --* ]]; then
        printf 'Missing value for %s\n' "$1" >&2
        exit 2
      fi
      case "$1" in
        --namespace) robot_namespace=$2 ;;
        --nav-workspace) nav_workspace=$2 ;;
        --serial-workspace) serial_workspace=$2 ;;
        --serial-node) serial_node=$2 ;;
        --report-root) report_root=$2 ;;
      esac
      shift 2
      ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; exit 2 ;;
  esac
done

if [[ "$robot_namespace" != / && ! "$robot_namespace" =~ ^(/[a-zA-Z_][a-zA-Z0-9_]*)+/?$ ]]; then
  printf 'Namespace must be an absolute ROS name: %s\n' "$robot_namespace" >&2
  exit 2
fi
robot_namespace=${robot_namespace%/}
if [[ ! "$serial_node" =~ ^(/[a-zA-Z_][a-zA-Z0-9_]*)+$ ]]; then
  printf 'Serial node must be an absolute ROS name: %s\n' "$serial_node" >&2
  exit 2
fi

for workspace in "$serial_workspace" "$nav_workspace"; do
  if [[ -n "$workspace" && ! -f "$workspace/install/setup.bash" ]]; then
    printf 'Missing workspace setup: %s/install/setup.bash\n' "$workspace" >&2
    exit 2
  fi
done
if ! command -v timeout >/dev/null 2>&1; then
  printf 'GNU timeout is required. Run this script on Ubuntu.\n' >&2
  exit 1
fi

mkdir -p "$report_root" || exit 1
report_stamp=$(date +%Y%m%d_%H%M%S)
report_directory=$(mktemp -d "$report_root/${report_stamp}_XXXXXX") || exit 1
report_file="$report_directory/report.txt"
node_file="$report_directory/nodes.txt"
topic_file="$report_directory/topics.txt"

{
  printf 'Navigation diagnostic report\nCreated: %s\n' "$(date --iso-8601=seconds)"
  printf 'Namespace: %s\nFull sampling: %s\n' "${robot_namespace:-/}" "$full_mode"
  printf 'No control messages, parameter changes, process stops or daemon restarts.\n'
  printf 'This is a snapshot, not a health verdict or robot acceptance record.\n'
} > "$report_file"

if [[ -n "$serial_workspace" || -n "$nav_workspace" ]]; then
  unset LD_LIBRARY_PATH
  for setup_file in /opt/ros/humble/setup.bash; do
    if [[ ! -f "$setup_file" ]] || ! source "$setup_file" >> "$report_file" 2>&1; then
      printf 'Cannot load Humble environment; see %s\n' "$report_file" >&2
      exit 1
    fi
  done
  for workspace in "$serial_workspace" "$nav_workspace"; do
    if [[ -n "$workspace" ]]; then
      printf '\nSource: %s/install/setup.bash\n' "$workspace" >> "$report_file"
      if ! source "$workspace/install/setup.bash" >> "$report_file" 2>&1; then
        printf 'Workspace setup failed; see %s\n' "$report_file" >&2
        exit 1
      fi
    fi
  done
fi
if ! command -v ros2 >/dev/null 2>&1; then
  printf 'ROS 2 CLI is unavailable. Source your verified environment first.\n' >&2
  printf 'ROS 2 CLI missing.\n' >> "$report_file"
  exit 1
fi

run_probe() {
  local probe_label=$1
  local probe_duration=$2
  shift 2
  printf '[%s] %s\n' "$(date +%H:%M:%S)" "$probe_label"
  {
    printf '\n===== %s =====\nTime: %s\nCommand:' "$probe_label" "$(date --iso-8601=seconds)"
    printf ' %q' "$@"
    printf '\n'
  } >> "$report_file"
  timeout --signal=INT --kill-after=2s "$probe_duration" "$@" >> "$report_file" 2>&1
  local probe_status=$?
  printf '[command exit=%s]\n' "$probe_status" >> "$report_file"
  return 0
}

echo_optional() {
  local topic_name=$1
  local message_type
  message_type=$(awk -v topic="$topic_name" '$1 == topic {gsub(/\[|\]/, "", $2); print $2; exit}' "$topic_file")
  if [[ -n "$message_type" ]]; then
    run_probe "Optional sample: $topic_name ($message_type)" 6s ros2 topic echo "$topic_name" "$message_type" --once
  else
    printf '\n[optional topic not discovered] %s\n' "$topic_name" >> "$report_file"
  fi
}

{
  printf '\n===== Environment =====\n'
  printf 'ROS_DISTRO=%s\nROS_DOMAIN_ID=%s\nROS_LOCALHOST_ONLY=%s\nRMW_IMPLEMENTATION=%s\n' \
    "${ROS_DISTRO:-unset}" "${ROS_DOMAIN_ID:-unset}" "${ROS_LOCALHOST_ONLY:-unset}" "${RMW_IMPLEMENTATION:-unset}"
  printf '\n===== Relevant local processes =====\n'
  ps -eo pid,ppid,stat,etimes,args | grep -E '[r]m_navigation_reality_launch|[c]omponent_container|[p]ointlio_mapping|[l]ivox_ros_driver2_node|[r]m_serial_driver|[s]tandard_robot_pp_ros2|[s]erial_node.py|[r]viz2'
  printf '\n===== User desktop autostart references =====\n'
  grep -RniE 'nav_test|rm_navigation_reality_launch|start_nav_tuned|world:=' "$HOME/.config/autostart" /etc/xdg/autostart 2>/dev/null
} >> "$report_file" 2>&1
run_probe 'Navigation package prefix' 6s ros2 pkg prefix pb2025_nav_bringup

timeout --signal=INT --kill-after=2s 8s ros2 node list > "$node_file" 2>&1
node_status=$?
{
  printf '\n===== Node list (exit=%s) =====\n' "$node_status"
  cat "$node_file"
  printf '\n===== Duplicate node names =====\n'
  if [[ "$node_status" -eq 0 ]]; then
    grep '^/' "$node_file" | sort | uniq -d
    printf 'No names above means none duplicated in this snapshot.\n'
  else
    printf 'Listing failed or timed out; duplicate check is inconclusive.\n'
  fi
} >> "$report_file"
timeout --signal=INT --kill-after=2s 8s ros2 topic list -t --include-hidden-topics > "$topic_file" 2>&1
topic_status=$?
{
  printf '\n===== Topic list (exit=%s) =====\n' "$topic_status"
  cat "$topic_file"
} >> "$report_file"
run_probe 'Composable components' 10s ros2 component list

for suffix in aft_mapped_to_init lidar_odometry registered_scan odometry terrain_map cmd_vel_controller cmd_vel_nav2_result cmd_vel cmd_gimbal_joint tf tf_static; do
  run_probe "Endpoints: $suffix" 6s ros2 topic info "$robot_namespace/$suffix" -v
done
run_probe 'NavigateToPose server and clients' 6s ros2 action info "$robot_namespace/navigate_to_pose"
for suffix in bt_navigator planner_server controller_server velocity_smoother; do
  run_probe "Lifecycle: $suffix" 6s ros2 lifecycle get "$robot_namespace/$suffix"
done

parameter_checks=(
  'point_lio use_sim_time'
  'sensor_scan_generation use_sim_time'
  'bt_navigator use_sim_time'
  'map_server yaml_filename'
  'small_gicp_relocalization prior_pcd_file'
  'small_gicp_relocalization auto_initialize'
  'fake_vel_transform init_spin_speed'
  'controller_server progress_checker.required_movement_radius'
  'controller_server progress_checker.movement_time_allowance'
  'controller_server FollowPath.enable_collision_guard'
  'bt_navigator default_nav_to_pose_bt_xml'
  'local_costmap/local_costmap robot_base_frame'
  'local_costmap/local_costmap footprint'
  'local_costmap/local_costmap obstacle_layer.observation_sources'
  'local_costmap/local_costmap obstacle_layer.terrain_map.topic'
  'local_costmap/local_costmap inflation_layer.inflation_radius'
  'global_costmap/global_costmap inflation_layer.inflation_radius'
)
printf '\nParameters may be absent in different source versions; record the response.\n' >> "$report_file"
for parameter_check in "${parameter_checks[@]}"; do
  read -r suffix parameter_name <<< "$parameter_check"
  run_probe "Parameter: $suffix $parameter_name" 6s ros2 param get "$robot_namespace/$suffix" "$parameter_name"
done
run_probe 'Configured optional serial node' 6s ros2 node info "$serial_node"
for topic_name in /serial/chassis_enabled /serial/chassis_velocity_feedback "$robot_namespace/serial/gimbal_joint_state" "$robot_namespace/cmd_vel_nav2_result" "$robot_namespace/cmd_vel" "$robot_namespace/navigate_to_pose/_action/status"; do
  echo_optional "$topic_name"
done

if [[ "$full_mode" -eq 1 ]]; then
  for suffix in livox/lidar/pointcloud livox/imu aft_mapped_to_init registered_scan odometry cmd_vel_nav2_result cmd_vel; do
    run_probe "Received frequency: $suffix" 7s ros2 topic hz "$robot_namespace/$suffix"
  done
  for frame_pair in 'map odom' 'odom base_footprint' 'base_footprint front_mid360'; do
    read -r source_frame target_frame <<< "$frame_pair"
    run_probe "TF: $source_frame -> $target_frame" 8s ros2 run tf2_ros tf2_echo "$source_frame" "$target_frame" --ros-args -r "/tf:=$robot_namespace/tf" -r "/tf_static:=$robot_namespace/tf_static"
  done
fi

{
  printf '\n===== Optional source configuration =====\n'
  if [[ -n "$nav_workspace" ]]; then
    grep -nE 'init_spin_speed|required_movement_radius|movement_time_allowance|inflation_radius|footprint|enable_collision_guard' "$nav_workspace/src/pb2025_sentry_nav/pb2025_nav_bringup/config/reality/nav2_params.yaml"
  else
    printf 'No workspace supplied; source paths were not guessed.\n'
  fi
  printf '\n===== Latest log target (may belong to another launch) =====\n'
  readlink -f "$HOME/.ros/log/latest"
  grep -RniE 'ERROR|WARN|GICP|BackUp|collision|queue is full|extrapolation|process has died|CRC|reopen' "$HOME/.ros/log/latest" 2>/dev/null | tail -n 100
  printf '\nFinished: %s\n' "$(date --iso-8601=seconds)"
  printf 'Supply commit, mode, map, Goal/idle state, and symptom with this report.\n'
} >> "$report_file" 2>&1
printf '\nCollection complete (not a health verdict).\nReport: %s\nNodes: %s\nTopics: %s\n' "$report_file" "$node_file" "$topic_file"
