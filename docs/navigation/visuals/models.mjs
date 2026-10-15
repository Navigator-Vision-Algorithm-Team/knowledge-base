// Small, deterministic teaching models. Distances and times are illustrative.
export function rotateVelocity(forward, left, yaw) {
  return { x: forward * Math.cos(yaw) - left * Math.sin(yaw), y: forward * Math.sin(yaw) + left * Math.cos(yaw) };
}

export class MessageLink {
  constructor() { this.matches = true; this.sent = 0; this.received = 0; }
  send() {
    this.sent++;
    if (this.matches) this.received++;
    return { number: this.sent, delivered: this.matches };
  }
}

const key = point => point.join(',');
const point = cell => cell.split(',').map(Number);
const distance = (a, b) => Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]);

// Four neighbors, unit edge costs, consistent Manhattan heuristic.
export class AStarSearch {
  constructor({ width, height, start, goal, obstacles = [] }) {
    this.width = width; this.height = height; this.start = [...start]; this.goal = [...goal];
    this.obstacles = new Set(obstacles.map(key));
    this.obstacles.delete(key(start)); this.obstacles.delete(key(goal));
    this.open = new Map([[key(start), { g: 0, h: distance(start, goal) }]]);
    this.closed = new Set(); this.parent = new Map(); this.path = [];
    this.cost = null; this.status = 'searching'; this.current = null;
  }
  step() {
    if (this.status !== 'searching') return this.snapshot();
    if (!this.open.size) { this.status = 'no-path'; return this.snapshot(); }
    const [cell, node] = [...this.open].sort((a, b) => (a[1].g + a[1].h) - (b[1].g + b[1].h) || a[1].h - b[1].h)[0];
    this.open.delete(cell); this.closed.add(cell); this.current = point(cell);
    if (cell === key(this.goal)) {
      this.status = 'found'; this.cost = node.g;
      for (let at = cell; at !== undefined; at = this.parent.get(at)) this.path.unshift(point(at));
      return this.snapshot();
    }
    const [x, y] = this.current;
    for (const next of [[x + 1, y], [x, y - 1], [x, y + 1], [x - 1, y]]) {
      const id = key(next);
      if (next[0] < 0 || next[0] >= this.width || next[1] < 0 || next[1] >= this.height || this.obstacles.has(id) || this.closed.has(id)) continue;
      const g = node.g + 1;
      if (!this.open.has(id) || g < this.open.get(id).g) {
        this.open.set(id, { g, h: distance(next, this.goal) }); this.parent.set(id, cell);
      }
    }
    if (!this.open.size) this.status = 'no-path';
    return this.snapshot();
  }
  snapshot() {
    return { status: this.status, current: this.current && [...this.current], candidates: [...this.open.keys()].map(point), expanded: [...this.closed].map(point), path: this.path.map(p => [...p]), cost: this.cost };
  }
}

export function costBand(distanceFromObstacle, robotRadius, extraRange) {
  return distanceFromObstacle <= robotRadius ? 'blocked' : distanceFromObstacle <= robotRadius + extraRange ? 'cost' : 'free';
}
export function canPass(gapWidth, robotRadius) { return gapWidth > 2 * robotRadius; }

export class PatrolModel {
  constructor() {
    this.position = 0; this.target = 10; this.state = 'IDLE';
    this.blocked = false; this.stream = true; this.visits = 0;
  }
  get velocity() { return this.state === 'RUNNING' ? Math.sign(this.target - this.position) : 0; }
  start() { if (this.state === 'IDLE') this.state = this.blocked ? 'WAITING' : 'RUNNING'; }
  cancel() { if (['IDLE', 'RUNNING', 'WAITING'].includes(this.state)) this.state = 'CANCELED'; }
  setBlocked(blocked) {
    this.blocked = blocked;
    if (this.state === 'RUNNING' && blocked) this.state = 'WAITING';
    else if (this.state === 'WAITING' && !blocked && this.stream) this.state = 'RUNNING';
  }
  setStream(available) {
    this.stream = available;
    if (!available && ['RUNNING', 'WAITING', 'IDLE'].includes(this.state)) this.state = 'ABORTED';
  }
  tick(seconds) {
    if (this.state !== 'RUNNING' || seconds <= 0) return;
    let remaining = seconds;
    while (remaining > 0) {
      const travel = Math.min(remaining, Math.abs(this.target - this.position));
      this.position += this.velocity * travel; remaining -= travel;
      if (this.position === this.target) {
        this.visits++;
        if (this.visits === 2) { this.state = 'SUCCEEDED'; return; }
        this.target = this.target === 10 ? 0 : 10;
      }
    }
  }
}
