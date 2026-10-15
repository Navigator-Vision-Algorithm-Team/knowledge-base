/* Progressive disclosure for navigation lessons only. No script: all text remains visible. */
(() => {
  const frames = [...document.querySelectorAll('iframe[src*="visuals/playground.html"]')];
  window.addEventListener('message', event => {
    if (event.origin !== location.origin || event.data?.type !== 'nav-demo-resize') return;
    const frame = frames.find(item => item.contentWindow === event.source);
    const height = event.data.height;
    if (frame && Number.isFinite(height) && height >= 200 && height <= 1600) frame.style.height = `${Math.ceil(height)}px`;
  });
  for (const frame of frames) {
    const measure = () => frame.contentWindow?.postMessage({ type: 'nav-demo-measure' }, location.origin);
    frame.addEventListener('load', measure);
    measure();
  }
  const marker = document.querySelector('[data-nav-fold]');
  if (!marker) return;
  // Entry choices become readable cards on phones; detailed reference tables stay tables.
  for (const table of marker.parentElement.querySelectorAll('table')) {
    if (!(table.compareDocumentPosition(marker) & Node.DOCUMENT_POSITION_FOLLOWING)) continue;
    const labels = [...table.querySelectorAll('thead th')].map(cell => cell.textContent.trim());
    if (!labels.length) continue;
    table.classList.add('nav-entry-table');
    table.closest('.wy-table-responsive')?.classList.add('nav-entry-table-wrap');
    for (const row of table.querySelectorAll('tbody tr')) {
      [...row.cells].forEach((cell, index) => { cell.dataset.label = labels[index] || ''; });
    }
  }
  // Keep optional stills/GIFs available without repeating the live scene on first view.
  for (const reference of document.querySelectorAll('[data-nav-visuals]')) {
    const details = document.createElement('details');
    details.className = 'nav-visual-reference';
    const summary = document.createElement('summary');
    summary.textContent = reference.dataset.navVisuals;
    details.append(summary);
    let next = reference.nextElementSibling;
    while (next?.tagName === 'P' && next.querySelector('img') && !next.textContent.trim()) {
      const following = next.nextElementSibling;
      details.append(next);
      next = following;
    }
    if (details.querySelector('img')) reference.replaceWith(details);
  }
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  for (const image of marker.parentElement.querySelectorAll('img')) {
    if (!image.getAttribute('src')?.endsWith('.gif')) continue;
    const animated = image.getAttribute('src');
    const still = animated.replace(/\.gif$/, '-poster.png');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'nav-gif-control';
    let playing = !reducedMotion && !image.closest('.nav-visual-reference');
    const update = () => {
      image.src = playing ? animated : still;
      button.textContent = playing ? '暂停动图' : '播放动图';
      button.setAttribute('aria-label', `${button.textContent}：${image.alt}`);
    };
    button.addEventListener('click', () => { playing = !playing; update(); });
    image.after(button);
    update();
  }
  const chapters = [];
  let cursor = marker.nextElementSibling;
  while (cursor) {
    if (cursor.tagName !== 'H2') { cursor = cursor.nextElementSibling; continue; }
    const heading = cursor;
    const nextHeading = (() => {
      let node = heading.nextElementSibling;
      while (node && node.tagName !== 'H2') node = node.nextElementSibling;
      return node;
    })();
    const chapter = document.createElement('details');
    chapter.className = 'nav-chapter';
    const summary = document.createElement('summary');
    summary.textContent = heading.textContent;
    chapter.append(summary);
    heading.before(chapter);
    let node = heading;
    while (node && node !== nextHeading) {
      const next = node.nextElementSibling;
      chapter.append(node);
      node = next;
    }
    chapters.push(chapter);
    cursor = nextHeading;
  }
  const tools = document.createElement('div');
  tools.className = 'nav-reader-tools';
  const hint = document.createElement('span');
  hint.textContent = marker.dataset.navFold || '上手后再查：点开下面的原理、代码和练习。';
  tools.append(hint);
  for (const [label, opened] of [['展开全部', true], ['收起全部', false]]) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = label;
    button.addEventListener('click', () => chapters.forEach(chapter => { chapter.open = opened; }));
    tools.append(button);
  }
  marker.replaceWith(tools);
  function reveal(hash) {
    if (!hash || hash === '#') return;
    let id;
    try { id = decodeURIComponent(hash.slice(1)); } catch { return; }
    const target = document.getElementById(id);
    if (!target) return;
    for (let parent = target.parentElement; parent; parent = parent.parentElement) {
      if (parent.tagName === 'DETAILS') parent.open = true;
    }
    return target;
  }
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href]');
    if (link && link.origin === location.origin && link.pathname === location.pathname) reveal(link.hash);
  });
  window.addEventListener('hashchange', () => reveal(location.hash));
  if (location.hash) {
    const target = reveal(location.hash);
    requestAnimationFrame(() => target?.scrollIntoView());
  }
})();
