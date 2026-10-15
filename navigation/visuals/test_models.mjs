import test from 'node:test';
import assert from 'node:assert/strict';

const models = await import('./models.mjs').catch(() => ({}));
const use = name => {
  assert.equal(typeof models[name], 'function', `${name} behavior is not implemented`);
  return models[name];
};
const finish = search => {
  for (let n = 0; search.status === 'searching' && n < 2000; n++) search.step();
  return search.snapshot();
};

test('body forward becomes world +y when heading is 90 degrees', () => {
  const result = use('rotateVelocity')(1, 0, Math.PI / 2);
  assert.ok(Math.abs(result.x) < 1e-10);
  assert.equal(result.y, 1);
});

test('body left becomes world -x at 90 degrees and retains length', () => {
  const result = use('rotateVelocity')(0, 2, Math.PI / 2);
  assert.equal(result.x, -2);
  assert.ok(Math.abs(result.y) < 1e-10);
});

test('matching names deliver sequential messages; mismatch still sends; repair resumes', () => {
  const link = new (use('MessageLink'))();
  assert.deepEqual(link.send(), { number: 1, delivered: true });
  link.matches = false;
  assert.deepEqual(link.send(), { number: 2, delivered: false });
  assert.equal(link.sent, 2);
  assert.equal(link.received, 1);
  link.matches = true;
  assert.deepEqual(link.send(), { number: 3, delivered: true });
  assert.equal(link.received, 2);
});

test('four-neighbor A* finds the hand-checked shortest detour with cost 6', () => {
  const Search = use('AStarSearch');
  const search = new Search({ width: 5, height: 3, start: [0, 1], goal: [4, 1], obstacles: [[2, 0], [2, 1]] });
  const result = finish(search);
  // The lower row crosses the wall: down 1, right 4, up 1 = 6.
  assert.equal(result.status, 'found');
  assert.equal(result.cost, 6);
  assert.deepEqual(result.path[0], [0, 1]);
  assert.deepEqual(result.path.at(-1), [4, 1]);
  for (let i = 1; i < result.path.length; i++) {
    assert.equal(Math.abs(result.path[i][0] - result.path[i - 1][0]) + Math.abs(result.path[i][1] - result.path[i - 1][1]), 1);
    assert.ok(![[2, 0], [2, 1]].some(p => p[0] === result.path[i][0] && p[1] === result.path[i][1]));
  }
});

test('A* performs one expansion per step and terminates when no route exists', () => {
  const Search = use('AStarSearch');
  const search = new Search({ width: 3, height: 3, start: [0, 1], goal: [2, 1], obstacles: [[1, 0], [1, 1], [1, 2]] });
  search.step();
  assert.equal(search.snapshot().expanded.length, 1);
  const result = finish(search);
  assert.equal(result.status, 'no-path');
  assert.deepEqual(result.path, []);
  assert.equal(result.cost, null);
  assert.equal(result.expanded.length, 3);
  search.step();
  assert.equal(search.snapshot().expanded.length, 3);
});

test('A* at the goal has zero cost, including a one-cell map', () => {
  const search = new (use('AStarSearch'))({ width: 1, height: 1, start: [0, 0], goal: [0, 0], obstacles: [] });
  const result = finish(search);
  assert.equal(result.cost, 0);
  assert.deepEqual(result.path, [[0, 0]]);
});

test('A* uses unit Manhattan cost on an open rectangular map', () => {
  const search = new (use('AStarSearch'))({ width: 8, height: 5, start: [0, 0], goal: [7, 4], obstacles: [] });
  assert.equal(finish(search).cost, 11);
});

test('inflation distinguishes collision footprint from traversable cost band', () => {
  const band = use('costBand');
  assert.equal(band(0.4, 0.5, 0.8), 'blocked');
  assert.equal(band(0.5, 0.5, 0.8), 'blocked');
  assert.equal(band(0.9, 0.5, 0.8), 'cost');
  assert.equal(band(1.4, 0.5, 0.8), 'free');
  assert.equal(band(0.6, 0.5, 0), 'free');
});

test('a narrow passage must be wider than robot diameter', () => {
  const canPass = use('canPass');
  assert.equal(canPass(1.0, 0.5), false);
  assert.equal(canPass(1.2, 0.5), true);
});

test('patrol visits both points, waits for obstacles, then resumes only from waiting', () => {
  const patrol = new (use('PatrolModel'))();
  patrol.start();
  patrol.tick(10);
  assert.equal(patrol.position, 10);
  assert.equal(patrol.target, 0);
  patrol.setBlocked(true);
  assert.equal(patrol.state, 'WAITING');
  assert.equal(patrol.velocity, 0);
  patrol.tick(5);
  assert.equal(patrol.position, 10);
  patrol.setBlocked(false);
  patrol.tick(2);
  assert.equal(patrol.position, 8);
  assert.equal(patrol.velocity, -1);
});

test('cancelled patrol cannot revive through clear, start, tick, or stream repair', () => {
  const patrol = new (use('PatrolModel'))();
  patrol.start();
  patrol.tick(2);
  patrol.setBlocked(true);
  patrol.cancel();
  patrol.setBlocked(false);
  patrol.setStream(true);
  patrol.start();
  patrol.tick(30);
  assert.equal(patrol.position, 2);
  assert.equal(patrol.state, 'CANCELED');
  assert.equal(patrol.velocity, 0);
});

test('lost command stream permanently stops current task; replay creates a new task', () => {
  const Patrol = use('PatrolModel');
  const patrol = new Patrol();
  patrol.start();
  patrol.tick(3);
  patrol.setStream(false);
  patrol.setStream(true);
  patrol.setBlocked(false);
  patrol.tick(9);
  assert.equal(patrol.position, 3);
  assert.equal(patrol.velocity, 0);
  assert.equal(patrol.state, 'ABORTED');
  const next = new Patrol();
  next.start();
  next.tick(1);
  assert.equal(next.position, 1);
});

test('one patrol finishes A to B to A, stops at the second arrival, and stays succeeded', () => {
  const patrol = new (use('PatrolModel'))();
  patrol.start();
  patrol.tick(25);
  assert.equal(patrol.position, 0);
  assert.equal(patrol.visits, 2);
  assert.equal(patrol.state, 'SUCCEEDED');
  assert.equal(patrol.velocity, 0);
  patrol.start();
  patrol.setBlocked(true);
  patrol.setBlocked(false);
  patrol.setStream(false);
  patrol.setStream(true);
  patrol.cancel();
  patrol.tick(100);
  assert.equal(patrol.position, 0);
  assert.equal(patrol.state, 'SUCCEEDED');
  assert.equal(patrol.velocity, 0);
});

test('canceling a task already aborted preserves the aborted outcome', () => {
  const patrol = new (use('PatrolModel'))();
  patrol.start();
  patrol.tick(2);
  patrol.setStream(false);
  patrol.cancel();
  assert.equal(patrol.state, 'ABORTED');
  assert.equal(patrol.velocity, 0);
  assert.equal(patrol.position, 2);
});
