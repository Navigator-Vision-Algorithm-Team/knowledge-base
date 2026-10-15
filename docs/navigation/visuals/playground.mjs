import { rotateVelocity, MessageLink, AStarSearch, PatrolModel, canPass } from './models.mjs';

const $ = id => document.getElementById(id);
const scenes = ['overview', 'messages', 'motion', 'astar', 'costmap', 'patrol'];
const params = new URLSearchParams(location.search);
const requested = params.get('scene');
const scene = scenes.includes(requested) ? requested : 'overview';
const embedded = window.self !== window.top;
// A lesson stays on its own topic. The separate gallery is the only scene selector.
document.querySelector('.scenes').hidden = embedded || params.get('gallery') !== '1';
document.body.classList.toggle('embedded', embedded);
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
let timer = null;
let ticks = 0;
let yaw = 0;
let sideways = false;
let motionDistance = 0;
let link = new MessageLink();
let messageProgress = 0;
let search;
let impossible = false;
let extra = 34;
let largeRobot = false;
let patrol = new PatrolModel();

const config = {
  overview: { question: '机器人怎样走到目标点？', legend: [['#2463b4', '机器人 / 当前位置'], ['#087f80', '计划路线'], ['#5e6f82', '障碍物']], note: '教学示意：地图和路线已确定。真实导航还需要传感器、定位和实时避障。' },
  messages: { question: '发送了，为什么却收不到？', legend: [['#2463b4', '带序号的消息'], ['#b63443', '名字不匹配：无法投递']], note: '这里只隔离“名字匹配”这一项；真实 ROS 2 通信还涉及消息类型、QoS 和网络。' },
  motion: { question: '车头转了，“向前”还是右边吗？', legend: [['#2463b4', '车头 / 车体前方'], ['#087f80', '实际移动轨迹'], ['#8999ab', '固定的世界坐标']], note: '俯视图：车体 +x 向前、+y 向左。使用旋转矩阵把车体速度换到世界坐标；距离为教学单位。' },
  astar: { question: 'A* 是怎样一格一格找到路的？', legend: [['#f4f7fb', '空白'], ['#f8cf78', '候选'], ['#b9daef', '已展开'], ['#138b80', '最终路径'], ['#5e6f82', '障碍']], note: '真实 A* 搜索：四邻接、每步代价 1、曼哈顿启发式。橙色边框是本次展开的格子。' },
  costmap: { question: '留白的通道，机器人一定过得去吗？', legend: [['#5e6f82', '墙'], ['#bb6670', '实心内圈：车心不可进入'], ['#f4cc8b', '渐淡外圈：可走但代价更高']], note: '圆形机器人示意；实心圈 = 车体碰撞范围，外圈 = 额外代价。教学参数，不是实车配置。' },
  patrol: { question: '巡逻遇障或取消，车还会继续走吗？', legend: [['#2463b4', '机器人'], ['#087f80', 'A / B 巡逻点'], ['#bf6b12', '等待中的障碍']], note: '离线教学任务：A → B → A，回到 A 即完成。暂停冻结演示；完成、取消和断流都保持速度 0，重播才可新建任务。' },
};

document.title = `${config[scene].question} · 动手看导航`;
$('question').textContent = config[scene].question;
$('note').textContent = config[scene].note + (reducedMotion ? ' 已跟随减少动态效果设置，建议使用“单步”。' : '');
$('legend').innerHTML = config[scene].legend.map(([color, label]) => `<span><i class="swatch" style="--swatch:${color}"></i>${label}</span>`).join('');
document.querySelector(`[data-scene="${scene}"]`).setAttribute('aria-current', 'page');

function button(label, action, className = '', attrs = '') { return `<button type="button" data-action="${action}" class="${className}" ${attrs}>${label}</button>`; }
function stop() { if (timer) clearInterval(timer); timer = null; updateControls(); }
function start() {
  if (timer) return stop();
  if (scene === 'patrol') patrol.start();
  const interval = reducedMotion ? 900 : scene === 'astar' ? 240 : scene === 'overview' ? 420 : 70;
  timer = setInterval(() => { advance(false); render(); }, interval);
  updateControls(); render();
}
function reset() {
  stop(); ticks = 0; motionDistance = 0; messageProgress = 0;
  link = new MessageLink();
  if (scene === 'messages' && $('mismatch')?.getAttribute('aria-pressed') === 'true') link.matches = false;
  patrol = new PatrolModel();
  if (scene === 'costmap') { extra = 34; $('range').value = extra; }
  makeSearch(); render();
}
function makeSearch() {
  const wall = Array.from({ length: impossible ? 7 : 5 }, (_, y) => [5, y]);
  search = new AStarSearch({ width: 12, height: 7, start: [1, 2], goal: [10, 2], obstacles: [...wall, [8, 4], [8, 5], [8, 6]] });
}
function options() {
  if (scene === 'messages') return button('名字相同', 'match', '', 'id="match" aria-pressed="true"') + button('名字不同', 'mismatch', '', 'id="mismatch" aria-pressed="false"');
  if (scene === 'motion') return button('车头 0°', 'yaw0', '', 'id="yaw0" aria-pressed="true"') + button('车头 90°', 'yaw90', '', 'id="yaw90" aria-pressed="false"') + button('向前', 'forward', '', 'id="forward" aria-pressed="true"') + button('向左侧移', 'left', '', 'id="left" aria-pressed="false"');
  if (scene === 'astar') return button('可绕障地图', 'solvable', '', 'id="solvable" aria-pressed="true"') + button('无路可走地图', 'impossible', '', 'id="impossible" aria-pressed="false"');
  if (scene === 'costmap') return '<label for="range">额外代价范围 <input id="range" type="range" min="0" max="65" value="34" step="1"><output id="range-value" class="meter" for="range">34</output></label>' + button('小车', 'small', '', 'id="small" aria-pressed="true"') + button('大车', 'large', '', 'id="large" aria-pressed="false"');
  return '';
}
$('options').innerHTML = options();
$('controls').innerHTML = button(scene === 'patrol' ? '开始巡逻' : '开始', 'play', 'primary', 'id="play"') + button('单步', 'step', '', 'id="step"') + button(scene === 'patrol' ? '重播新任务' : '重播', 'reset') + (scene === 'patrol' ? '<div class="scenario-controls" aria-label="巡逻途中操作">' + button('放入障碍', 'block', '', 'id="block"') + button('清除障碍', 'clear', '', 'id="clear"') + button('断流', 'disconnect', '', 'id="disconnect"') + button('取消任务', 'cancel', 'danger', 'id="cancel"') + '</div>' : '');

// Fit the lesson frame to its content, including wrapped controls on a narrow screen.
if (embedded) {
  const reportHeight = () => parent.postMessage({ type: 'nav-demo-resize', height: Math.ceil(document.querySelector('.shell').getBoundingClientRect().height) }, location.origin);
  new ResizeObserver(reportHeight).observe(document.querySelector('.shell'));
  window.addEventListener('message', event => {
    if (event.origin === location.origin && event.source === parent && event.data?.type === 'nav-demo-measure') reportHeight();
  });
}

function pressed(id, value) { $(id)?.setAttribute('aria-pressed', String(value)); }
document.addEventListener('click', event => {
  const action = event.target.closest('button')?.dataset.action;
  if (!action) return;
  if (action === 'play') start();
  if (action === 'step') { stop(); if (scene === 'patrol') patrol.start(); advance(true); }
  if (action === 'reset') reset();
  if (action === 'match' || action === 'mismatch') {
    if (action === 'mismatch' && link.matches) { link = new MessageLink(); messageProgress = 0; }
    link.matches = action === 'match'; pressed('match', link.matches); pressed('mismatch', !link.matches);
  }
  if (['yaw0', 'yaw90', 'forward', 'left'].includes(action)) {
    stop(); motionDistance = 0;
    if (action.startsWith('yaw')) yaw = action === 'yaw90' ? Math.PI / 2 : 0;
    else sideways = action === 'left';
    pressed('yaw0', yaw === 0); pressed('yaw90', yaw !== 0); pressed('forward', !sideways); pressed('left', sideways);
  }
  if (action === 'solvable' || action === 'impossible') { impossible = action === 'impossible'; pressed('solvable', !impossible); pressed('impossible', impossible); reset(); }
  if (action === 'small' || action === 'large') { largeRobot = action === 'large'; pressed('small', !largeRobot); pressed('large', largeRobot); }
  if (action === 'block') patrol.setBlocked(true);
  if (action === 'clear') patrol.setBlocked(false);
  if (action === 'cancel') { patrol.cancel(); stop(); }
  if (action === 'disconnect') { patrol.setStream(false); stop(); }
  render();
});
$('range')?.addEventListener('input', event => { extra = Number(event.target.value); render(); });
document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
window.addEventListener('pagehide', stop);

function updateControls() {
  const terminal = scene === 'patrol' && ['CANCELED', 'ABORTED', 'SUCCEEDED'].includes(patrol.state);
  $('play').textContent = timer ? '暂停' : scene === 'patrol' ? patrol.state === 'IDLE' ? '开始巡逻' : '继续演示' : '开始';
  $('play').disabled = terminal || (scene === 'astar' && search?.status !== 'searching') || (scene === 'motion' && motionDistance >= 3) || (scene === 'overview' && ticks >= 33);
  $('step').disabled = terminal || (scene === 'astar' && search?.status !== 'searching') || (scene === 'motion' && motionDistance >= 3) || (scene === 'overview' && ticks >= 33);
  if (scene === 'patrol') {
    $('block').disabled = terminal || patrol.blocked;
    $('clear').disabled = terminal || !patrol.blocked;
    $('disconnect').disabled = terminal;
    $('cancel').disabled = terminal;
  }
}
function advance(single) {
  ticks++;
  if (scene === 'overview' && ticks >= 33) stop();
  if (scene === 'messages') {
    messageProgress += single || reducedMotion ? 1 : .07;
    if (messageProgress >= 1) { link.send(); messageProgress = 0; }
  }
  if (scene === 'motion') {
    motionDistance = Math.min(3, motionDistance + (single || reducedMotion ? .5 : .055));
    if (motionDistance >= 3) stop();
  }
  if (scene === 'astar') { search.step(); if (search.status !== 'searching') stop(); }
  if (scene === 'costmap') {
    extra = (extra + (single || reducedMotion ? 10 : 1)) % 66;
    $('range').value = extra;
  }
  if (scene === 'patrol') { patrol.tick(single || reducedMotion ? 1 : .12); if (['CANCELED', 'ABORTED', 'SUCCEEDED'].includes(patrol.state)) stop(); }
}

const defs = '<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0 0L6 3L0 6Z" fill="context-stroke"/></marker><pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse"><path d="M30 0H0V30" class="grid" fill="none"/></pattern><radialGradient id="cost"><stop offset="0%" stop-color="#edba68" stop-opacity=".85"/><stop offset="100%" stop-color="#edba68" stop-opacity=".08"/></radialGradient></defs>';
const text = (x, y, content, cls = '', anchor = 'middle') => `<text x="${x}" y="${y}" text-anchor="${anchor}" class="${cls}">${content}</text>`;
const robot = (x, y, degrees = 0, radius = 18) => `<g transform="translate(${x} ${y}) rotate(${-degrees})"><circle r="${radius}" fill="#2463b4" stroke="#fff" stroke-width="3"/><path d="M${radius + 13} 0L${radius - 1} -8V8Z" fill="#2463b4"/><circle cx="-5" cy="-6" r="3" fill="#dcefff"/><circle cx="-5" cy="6" r="3" fill="#dcefff"/></g>`;
const routePoints = [[65, 212], [140, 212], [140, 55], [316, 55], [316, 135], [520, 135]];
function onRoute(progress) {
  const lengths = routePoints.slice(1).map((p, i) => Math.hypot(p[0] - routePoints[i][0], p[1] - routePoints[i][1]));
  let left = lengths.reduce((a, b) => a + b, 0) * Math.min(1, progress);
  for (let i = 0; i < lengths.length; i++) {
    if (left <= lengths[i] || i === lengths.length - 1) {
      const a = routePoints[i], b = routePoints[i + 1], t = left / lengths[i];
      return { x: a[0] + (b[0] - a[0]) * t, y: a[1] + (b[1] - a[1]) * t, angle: -Math.atan2(b[1] - a[1], b[0] - a[0]) * 180 / Math.PI };
    }
    left -= lengths[i];
  }
}

function renderOverview() {
  const phase = ticks % 3, position = onRoute(Math.floor(ticks / 3) / 11);
  const labels = ['我在哪', '从哪走', '怎样动'];
  $('status').textContent = ticks >= 33 ? '到达目标：定位告诉我位置，规划给出路线，控制让车沿路走。' : ['① 我在哪：蓝色圆圈标出当前机器人位置。', '② 从哪走：绿色路线绕过灰色障碍，连接目标点。', '③ 怎样动：车头沿路线朝向下一段，机器人向前走。'][phase];
  return '<rect width="600" height="280" fill="url(#grid)"/><rect x="183" y="88" width="89" height="102" rx="8" class="wall"/><rect x="365" y="182" width="100" height="47" rx="8" class="wall"/>' + `<polyline points="${routePoints.map(p => p.join(',')).join(' ')}" class="route dash"/>` + (phase === 0 ? `<circle cx="${position.x}" cy="${position.y}" r="31" fill="#2463b421" stroke="#2463b4" stroke-width="2"/>` : '') + '<circle cx="520" cy="135" r="22" fill="#d9f1e7" stroke="#087f80" stroke-width="3"/>' + text(520, 104, '目标', 'strong') + robot(position.x, position.y, position.angle) + labels.map((label, i) => `<rect x="${15 + i * 196}" y="244" width="178" height="30" rx="6" fill="${i === phase ? '#193e69' : '#eaf0f6'}"/>` + text(104 + i * 196, 267, label, i === phase ? 'light strong' : '')).join('');
}
function renderMessages() {
  const matches = link.matches;
  const x = 163 + (matches ? 274 : 145) * messageProgress;
  $('status').textContent = matches ? `发送 ${link.sent} 条 → 接收 ${link.received} 条；名字相同，消息可以送到。` : `发送 ${link.sent} 条 → 接收 0 条；发送端仍在发，接收端名字不同。`;
  return `<path d="M160 117H440" stroke="${matches ? '#8dbab3' : '#dba0a7'}" stroke-width="6" ${matches ? '' : 'stroke-dasharray="10 9"'}/><rect x="20" y="60" width="148" height="115" rx="16" fill="#e9f1fb" stroke="#2463b4" stroke-width="2"/><rect x="432" y="60" width="148" height="115" rx="16" fill="${matches ? '#e8f5f1' : '#fceff1'}" stroke="${matches ? '#087f80' : '#b63443'}" stroke-width="2"/>` + text(94, 102, '发送节点', 'strong') + text(94, 143, '/goal', 'strong') + text(506, 102, '接收节点', 'strong') + text(506, 143, matches ? '/goal' : '/goals', 'strong') + (matches ? text(300, 58, '名字对上，就能送达', 'small') : text(300, 56, '差一个 s，也对不上', 'small')) + `<circle cx="${x}" cy="117" r="21" fill="#2463b4"/>` + text(x, 125, link.sent + 1, 'light strong') + (!matches ? '<path d="M330 99L353 135M353 99L330 135" stroke="#b63443" stroke-width="6"/>' : '') + text(100, 222, `已发 ${link.sent}`, 'strong') + text(500, 222, `已收 ${link.received}`, 'strong') + text(300, 265, '试一试：改名字 → 观察计数 → 修回来', 'small');
}
function renderMotion() {
  const velocity = rotateVelocity(sideways ? 0 : 1, sideways ? 1 : 0, yaw);
  const origin = { x: 280, y: 205 };
  const x = origin.x + velocity.x * motionDistance * 47, y = origin.y - velocity.y * motionDistance * 47;
  const degrees = yaw * 180 / Math.PI;
  const forward = rotateVelocity(1, 0, yaw), left = rotateVelocity(0, 1, yaw);
  const clean = n => Math.abs(n) < 1e-8 ? 0 : n;
  $('status').textContent = `车头 ${degrees}°，车体${sideways ? '向左侧移' : '向前'} → 世界速度 (x=${clean(velocity.x)}, y=${clean(velocity.y)})。`;
  return '<rect width="600" height="280" fill="url(#grid)"/><path d="M65 225H170M65 225V120" class="axis" marker-end="url(#arrow)"/>' + text(173, 251, '世界 +x', 'small') + text(78, 108, '世界 +y', 'small') + `<path d="M${origin.x} ${origin.y}L${x} ${y}" class="route"/><circle cx="280" cy="205" r="5" fill="#087f80"/>` + `<path d="M${x} ${y}l${forward.x * 54} ${-forward.y * 54}" stroke="#2463b4" stroke-width="3" marker-end="url(#arrow)"/><path d="M${x} ${y}l${left.x * 46} ${-left.y * 46}" stroke="#bf6b12" stroke-width="3" marker-end="url(#arrow)"/>` + robot(x, y, degrees) + text(465, 36, '蓝箭头：车头前方', 'small') + text(465, 67, '橙箭头：车体左方', 'small') + text(300, 269, `已移动 ${motionDistance.toFixed(1)} / 3.0 单位`, 'small');
}
function renderAstar() {
  const result = search.snapshot();
  const expanded = new Set(result.expanded.map(p => p.join(','))), candidates = new Set(result.candidates.map(p => p.join(','))), path = new Set(result.path.map(p => p.join(',')));
  $('status').textContent = result.status === 'found' ? `找到最短路：${result.cost} 步；代价 ${result.cost}；已展开 ${result.expanded.length} 格。` : result.status === 'no-path' ? `没有可走的路：已展开 ${result.expanded.length} 格，候选耗尽。试试换地图。` : `已展开 ${result.expanded.length} 格；候选 ${result.candidates.length} 格。下一步取“已走代价 + 预计剩余”最小的一格。`;
  let svg = '';
  for (let y = 0; y < 7; y++) for (let x = 0; x < 12; x++) {
    const id = [x, y].join(','), start = x === 1 && y === 2, goal = x === 10 && y === 2;
    const cls = search.obstacles.has(id) ? 'wall' : path.has(id) ? 'path' : expanded.has(id) ? 'expanded' : candidates.has(id) ? 'candidate' : 'empty';
    svg += `<rect x="${60 + x * 40}" y="${y * 38 + 7}" width="38" height="36" rx="4" class="${cls} ${result.current?.join(',') === id ? 'current' : ''}"/>`;
    if (start || goal) svg += text(79 + x * 40, y * 38 + 34, start ? '起' : '终', path.has(id) ? 'light strong' : 'strong');
  }
  return svg;
}
function renderCostmap() {
  const radius = largeRobot ? 34 : 20;
  const gap = 56;
  const topSafe = 112 + radius, bottomSafe = 168 - radius;
  const costDepth = Math.max(1, extra);
  const upperCostHeight = Math.max(0, Math.min(extra, 168 - topSafe));
  const lowerCostTop = Math.max(112, bottomSafe - extra);
  const corridorCosts = `<defs><linearGradient id="upper-cost" gradientUnits="userSpaceOnUse" x1="0" y1="${topSafe}" x2="0" y2="${topSafe + costDepth}"><stop offset="0" stop-color="#e8a941" stop-opacity=".8"/><stop offset="1" stop-color="#e8a941" stop-opacity=".05"/></linearGradient><linearGradient id="lower-cost" gradientUnits="userSpaceOnUse" x1="0" y1="${bottomSafe}" x2="0" y2="${bottomSafe - costDepth}"><stop offset="0" stop-color="#e8a941" stop-opacity=".8"/><stop offset="1" stop-color="#e8a941" stop-opacity=".05"/></linearGradient></defs><rect x="318" y="${topSafe}" width="230" height="${upperCostHeight}" fill="url(#upper-cost)"/><rect x="318" y="${lowerCostTop}" width="230" height="${Math.max(0, bottomSafe - lowerCostTop)}" fill="url(#lower-cost)"/>`;
  $('range-value').textContent = extra;
  $('status').textContent = `${largeRobot ? '大车直径 68' : '小车直径 40'}，通道宽 ${gap}：${canPass(gap, radius) ? '车体能通过' : '车体会撞墙，不能通过'}。外圈变大只会增加贴墙的代价。`;
  return '<rect width="600" height="280" fill="url(#grid)"/>' + [109, 235].map(y => `<circle cx="135" cy="${y}" r="${radius + extra}" fill="url(#cost)"/><circle cx="135" cy="${y}" r="${radius}" fill="#bb6670"/><circle cx="135" cy="${y}" r="8" fill="#5e6f82"/>`).join('') + `<rect x="78" y="${109 + radius}" width="114" height="${Math.max(0, 126 - 2 * radius)}" fill="#087f8010"/>` + text(138, 35, '圈的含义', 'strong') + text(137, 176, '车心', 'small') + corridorCosts + '<rect x="318" y="18" width="230" height="94" fill="#5e6f82"/><rect x="318" y="168" width="230" height="94" fill="#5e6f82"/>' + `<rect x="318" y="112" width="230" height="${Math.min(56, radius)}" fill="#bb6670"/><rect x="318" y="${168 - Math.min(56, radius)}" width="230" height="${Math.min(56, radius)}" fill="#bb6670"/>` + '<path d="M288 114V166M280 114H296M280 166H296" stroke="#29435c" stroke-width="2"/>' + text(285, 99, '56', 'small') + robot(422, 140, 0, radius) + text(432, 51, '上方墙体', 'light small') + text(432, 239, '下方墙体', 'light small') + (!canPass(gap, radius) ? '<path d="M483 126L503 153M503 126L483 153" stroke="#b63443" stroke-width="5"/>' : '');
}
function renderPatrol() {
  const labels = { IDLE: '等待开始', RUNNING: '正在巡逻', WAITING: '遇障等待', CANCELED: '任务已取消', ABORTED: '断流，任务已终止', SUCCEEDED: '巡逻已完成' };
  const terminal = ['CANCELED', 'ABORTED', 'SUCCEEDED'].includes(patrol.state);
  const x = 90 + patrol.position * 42;
  $('status').textContent = `${labels[patrol.state]}｜目标 ${patrol.target === 10 ? 'B' : 'A'}，距目标 ${Math.abs(patrol.target - patrol.position).toFixed(1)} 教学单位；到点 ${patrol.visits}/2 次；速度 ${patrol.velocity.toFixed(1)} 教学单位/秒。`;
  return '<rect width="600" height="280" fill="url(#grid)"/><path d="M90 150H510" stroke="#d4e2ee" stroke-width="54" stroke-linecap="round"/><path d="M90 150H510" class="route dash"/>' + [90, 510].map((p, i) => `<circle cx="${p}" cy="150" r="26" fill="#e1f2eb" stroke="#087f80" stroke-width="3"/>` + text(p, 100, `巡逻点 ${i ? 'B' : 'A'}`, 'strong')).join('') + (patrol.blocked ? '<rect x="275" y="120" width="50" height="60" rx="5" fill="#bf6b12"/>' + text(300, 212, '障碍：清障后再走', 'small') : '') + robot(x, 150, patrol.target === 0 ? 180 : 0) + `<rect x="169" y="14" width="262" height="40" rx="20" fill="${terminal ? '#fbe7eb' : patrol.state === 'WAITING' ? '#fff0d7' : '#e4f2ef'}"/>` + text(300, 43, labels[patrol.state], 'strong') + text(300, 260, terminal ? '终态保持速度 0；重播才可新建任务' : 'A → B → A，到点两次即完成', 'small');
}
const renderers = { overview: renderOverview, messages: renderMessages, motion: renderMotion, astar: renderAstar, costmap: renderCostmap, patrol: renderPatrol };
function render() {
  $('diagram').innerHTML = defs + renderers[scene]();
  $('diagram').setAttribute('aria-label', `${config[scene].question} ${$('status').textContent}`);
  updateControls();
}
makeSearch();
render();
