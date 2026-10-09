/* MVE Comics reader.
   The shelf shows every comic's cover. Inside a comic, every page sits on one
   long horizontal ribbon and a camera glides along it. A "stop" is either a
   whole page (strip mode, labelled "Page" for comics made of full pages) or a
   single frame (frame mode). In frame mode a full page opens on the whole page
   (its "intro" frame) before visiting its panels.

   Addresses:  #                    the shelf
               #<comic>             a comic, from its cover
               #<comic>/p4f2        page 4, frame 2 (the f part is optional)
               #p4f2                links shared before the shelf existed */
(() => {
  'use strict';

  const RH = 1024;               // ribbon height; every page is scaled to it
  const GAP = 140;               // ribbon units between pages
  const AUTO_FRAME_BELOW = 900;       // a wide strip shown narrower than this many CSS px => frame mode
  const AUTO_FRAME_BELOW_TALL = 600;  // a tall page shown narrower than this => frame mode
  const BLUR_LEVELS = [1.5, 3, 5, 7.5, 10.5, 14];
  const LEGACY_COMIC = 'keith-richards';
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

  const $ = id => document.getElementById(id);
  const make = (tag, cls, text) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  };
  const stage = $('stage'), win = $('win'), ribbon = $('ribbon'), bump = $('bump');
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
  };

  let library = null;                          // comics/index.json
  let comic = null, pages = [];                // the open comic
  let stops = { strip: [], frame: [] };
  let pref = store.get('mve-mode') || store.get('krpd-mode') || 'auto';   // auto | strip | frame
  let mode = 'strip', idx = 0, view = 'boot';  // view: boot | shelf | reader
  let cam = { x: 0, y: 0, w: 1536, h: RH }, dragPx = 0, scale = 1;
  let raf = 0, idleTimer = 0, capTimer = 0, fadeTimer = 0, toastTimer = 0, loadToken = 0;
  const requests = new Map();

  /* ---------- data ---------- */

  function getJSON(url) {
    return fetch(url, { cache: 'no-cache' }).then(r => {
      if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
      return r.json();
    });
  }

  function fetchComic(id) {
    if (!requests.has(id)) {
      requests.set(id, getJSON(`comics/${id}/comic.json`).catch(err => {
        requests.delete(id);
        throw err;
      }));
    }
    return requests.get(id);
  }

  const countOf = (n, unit) => `${n} ${unit}${n === 1 ? '' : 's'}`;
  const sceneWord = () => (comic && comic.sceneLabel) || 'Scene';

  function splitTitle(t) {
    const i = t.indexOf(': ');
    return i < 0 ? [t, ''] : [t.slice(0, i), t.slice(i + 2)];
  }

  function toast(msg) {
    const t = $('toast');
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove('show'), 4500);
  }

  /* ---------- shelf ---------- */

  function bookLink(c, variant) {
    const a = make('a', 'book' + (variant ? ' ' + variant : ''));
    a.href = '#' + c.id;
    a.dataset.id = c.id;
    const cover = make('span', 'book-cover');
    const img = new Image();
    img.src = c.cover;
    img.alt = '';
    img.width = c.coverW;
    img.height = c.coverH;
    img.decoding = 'async';
    img.draggable = false;
    cover.append(img);
    const [main, rest] = splitTitle(c.title);
    const info = make('span', 'book-info');
    info.append(make('span', 'book-title', main));
    if (rest || c.subtitle) info.append(make('span', 'book-series', rest || c.subtitle));
    if (variant !== 'mini') {
      const meta = make('span', 'book-meta', `${c.issue} · ${countOf(c.units ?? c.strips, c.unit || 'strip')}`);
      if (c.status === 'in-progress') meta.append(make('span', 'pill', 'In progress'));
      info.append(meta, make('span', 'book-resume'));
    }
    a.append(cover, info);
    return a;
  }

  function savedPosition(id) {
    try { return JSON.parse(store.get('mve-pos-' + id)) || null; } catch { return null; }
  }

  function refreshShelf() {
    $('books').querySelectorAll('.book').forEach(a => {
      const pos = savedPosition(a.dataset.id);
      const resume = pos && pos.page > 1;
      a.href = '#' + a.dataset.id + (resume ? `/p${pos.page}` + (pos.frame ? `f${pos.frame}` : '') : '');
      a.querySelector('.book-resume').textContent = resume ? `Continue · ${pos.where}` : '';
    });
  }

  function showShelf() {
    loadToken++;                                 // abandon any comic still loading
    refreshShelf();
    document.title = library.title;
    if (view === 'shelf') return;
    const was = comic && view === 'reader' ? comic.id : null;
    view = 'shelf';
    cancelAnimationFrame(raf);
    setBlur(0);
    closeOverlays();
    clearTimeout(idleTimer);
    document.body.classList.remove('idle', 'fresh');
    document.body.classList.add('shelf-view');
    $('reader').inert = true;
    $('shelf').inert = false;
    if (was) $('books').querySelector(`[data-id="${was}"]`)?.focus({ preventScroll: true });
  }

  function enterReader() {
    if (view === 'reader') return;
    view = 'reader';
    document.activeElement?.blur?.();
    document.body.classList.remove('shelf-view');
    $('shelf').inert = true;
    $('reader').inert = false;
    wake();
  }

  /* ---------- building a comic ---------- */

  function setupComic(data) {
    cancelAnimationFrame(raf);
    clearTimeout(fadeTimer);
    win.classList.remove('fade');
    comic = data;
    pages = data.pages;
    stops = { strip: [], frame: [] };
    ribbon.textContent = '';
    buildLayout();
    buildIndex();
    const [main, rest] = splitTitle(data.title);
    $('t-main').textContent = main;
    $('t-rest').textContent = rest ? `: ${rest}` : '';
    $('index-title').textContent = data.title;
    const whole = data.unit === 'episode' ? 'page' : 'strip';
    $('mode-strip').textContent = whole[0].toUpperCase() + whole.slice(1);
    $('mode-strip').title = `One ${whole} at a time (S)`;
  }

  function buildLayout() {
    let X = 0;
    pages.forEach((p, i) => {
      const s = RH / p.h;
      p.X = X; p.W = p.w * s;
      p.R = { x: X, y: 0, w: p.W, h: RH };
      stops.strip.push({ page: i, frame: null, R: p.R });
      p.frames.forEach((f, j) => {
        const [x, y, w, h] = f.rect;
        f.R = { x: X + x * s, y: y * s, w: w * s, h: h * s };
        stops.frame.push({ page: i, frame: j, R: f.R });
      });
      X += p.W + GAP;

      const slot = document.createElement('div');
      slot.className = 'slot';
      slot.style.cssText = `--x:${p.X};--w:${p.W};--h:${RH};background-image:url("${p.thumb}")`;
      const img = new Image();
      img.alt = `Page ${i + 1}: ${p.frames.map(f => f.title).join(', ')}`;
      img.decoding = 'async';
      img.draggable = false;
      img.onload = () => img.classList.add('ok');
      slot.append(img);
      ribbon.append(slot);
      p.slot = slot; p.img = img;
    });
  }

  function buildBlurFilters() {
    const NS = 'http://www.w3.org/2000/svg';
    BLUR_LEVELS.forEach((sd, i) => {
      const f = document.createElementNS(NS, 'filter');
      f.id = `mb${i}`;
      f.setAttribute('x', '-5%'); f.setAttribute('width', '110%');
      f.setAttribute('y', '0'); f.setAttribute('height', '100%');
      f.setAttribute('color-interpolation-filters', 'sRGB');
      const g = document.createElementNS(NS, 'feGaussianBlur');
      g.setAttribute('stdDeviation', `${sd} 0`);
      f.append(g);
      $('blur-defs').append(f);
    });
  }

  function mountAround(i) {
    pages.forEach((p, k) => {
      const near = Math.abs(k - i) <= 2;
      p.slot.hidden = Math.abs(k - i) > 3;
      if (near && !p.img.src) p.img.src = p.src;
    });
  }

  /* ---------- rendering ---------- */

  function render() {
    const vw = stage.clientWidth, vh = stage.clientHeight;
    scale = Math.min(vw / cam.w, vh / cam.h);
    const ww = cam.w * scale, wh = cam.h * scale;
    win.style.width = ww + 'px';
    win.style.height = wh + 'px';
    win.style.transform = `translate(${(vw - ww) / 2}px,${(vh - wh) / 2}px)`;
    ribbon.style.setProperty('--s', scale);
    ribbon.style.transform = `translate3d(${-cam.x * scale + dragPx}px,${-cam.y * scale}px,0)`;
  }

  function setBlur(pxPerMs) {
    if (reduceMotion) return;
    const sd = Math.min(pxPerMs * 2.6, 14);
    let level = -1;
    for (let i = 0; i < BLUR_LEVELS.length; i++) if (sd >= BLUR_LEVELS[i] * 0.8) level = i;
    const v = level < 0 ? '' : `url(#mb${level})`;
    if (win.dataset.blur !== v) { win.dataset.blur = v; win.style.filter = v; }
  }

  const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

  function animateTo(R, dur) {
    cancelAnimationFrame(raf);
    clearTimeout(fadeTimer);
    win.classList.remove('fade');
    cam.x -= dragPx / scale; dragPx = 0;          // fold any drag into the camera
    if (reduceMotion || dur <= 0) { cam = { ...R }; setBlur(0); render(); return; }
    const from = { ...cam }, t0 = performance.now();
    let lastT = t0, lastC = (from.x + from.w / 2);
    const tick = now => {
      const t = Math.min(1, (now - t0) / dur), e = ease(t);
      cam = {
        x: from.x + (R.x - from.x) * e, y: from.y + (R.y - from.y) * e,
        w: from.w + (R.w - from.w) * e, h: from.h + (R.h - from.h) * e,
      };
      render();
      const c = cam.x + cam.w / 2, dt = Math.max(1, now - lastT);
      setBlur(Math.abs(c - lastC) * scale / dt);
      lastT = now; lastC = c;
      if (t < 1) raf = requestAnimationFrame(tick);
      else { cam = { ...R }; setBlur(0); render(); }
    };
    raf = requestAnimationFrame(tick);
  }

  // Fades out, jumps to whichever stop is current when the fade ends, fades back in.
  // Reading idx and mode at that moment, not when the fade began, keeps a resize or
  // a Strip/Frame switch during the fade from being overwritten by a stale target.
  function fadeTo() {
    cancelAnimationFrame(raf);
    clearTimeout(fadeTimer);
    dragPx = 0; setBlur(0);
    if (reduceMotion) { cam = { ...list()[idx].R }; render(); return; }
    win.classList.add('fade');
    fadeTimer = setTimeout(() => { cam = { ...list()[idx].R }; render(); win.classList.remove('fade'); }, 170);
  }

  function jumpTo(i) {
    idx = i;
    mountAround(list()[idx].page);
    cancelAnimationFrame(raf);
    clearTimeout(fadeTimer);
    win.classList.remove('fade');
    dragPx = 0; setBlur(0);
    cam = { ...list()[idx].R };
    render();
  }

  /* ---------- navigation ---------- */

  const list = () => stops[mode];

  function goTo(i, how = 'slide') {
    const L = list();
    i = Math.max(0, Math.min(L.length - 1, i));
    const prev = L[idx], next = L[i];
    idx = i;
    mountAround(next.page);
    const far = Math.abs(next.page - prev.page) > 1;
    if (how === 'fade' || far) fadeTo();
    else animateTo(next.R, next.page === prev.page ? 430 : 540);
    updateChrome();
  }

  function edgeBump(d) {
    if (dragPx) animateTo(list()[idx].R, 260);
    bump.className = ''; void bump.offsetWidth; bump.className = d > 0 ? 'r' : 'l';
  }

  function step(d) {
    document.body.classList.remove('fresh');
    if (!$('end').hidden) { if (d < 0) hideEnd(); return; }
    const i = idx + d;
    if (i < 0) { edgeBump(d); return; }
    if (i >= list().length) { if (dragPx) animateTo(list()[idx].R, 260); showEnd(); return; }
    goTo(i);
  }

  function indexFor(page, frame) {
    if (mode === 'strip') return page;
    const i = stops.frame.findIndex(s => s.page === page && s.frame === frame);
    return i < 0 ? stops.frame.findIndex(s => s.page === page) : i;
  }

  function syncModeButtons() {
    $('mode-strip').setAttribute('aria-pressed', mode === 'strip');
    $('mode-frame').setAttribute('aria-pressed', mode === 'frame');
  }

  function setMode(m, explicit) {
    if (explicit) { pref = m; store.set('mve-mode', m); }
    if (m !== mode && comic) {
      const cur = list()[idx];
      mode = m;
      idx = indexFor(cur.page, 0);
      if (view === 'reader') animateTo(list()[idx].R, 480);
      else cam = { ...list()[idx].R };
      updateChrome();
    } else mode = m;
    syncModeButtons();
  }

  // The most common shape among a comic's strips or pages, ignoring covers.
  function typicalPage() {
    const tally = new Map();
    for (const p of pages || []) {
      if (p.kind !== 'strip' && p.kind !== 'page') continue;
      const k = `${p.w}x${p.h}`;
      tally.set(k, (tally.get(k) || 0) + 1);
    }
    const best = [...tally].sort((a, b) => b[1] - a[1])[0];
    if (!best) return { w: 1536, h: 1024 };
    const [w, h] = best[0].split('x').map(Number);
    return { w, h };
  }

  // Whole strips or pages when they would show big enough to read, otherwise frame by frame.
  function autoMode() {
    const t = typicalPage();
    const s = Math.min(stage.clientWidth / t.w, stage.clientHeight / t.h);
    return t.w * s < (t.w > t.h ? AUTO_FRAME_BELOW : AUTO_FRAME_BELOW_TALL) ? 'frame' : 'strip';
  }

  /* ---------- captions, address, chrome ---------- */

  function label(stop) {
    const p = pages[stop.page], sc = comic.scenes[p.scene];
    const scene = sc.num ? `${sceneWord()} ${sc.num} · ${sc.title}` : sc.title;
    const panels = p.frames.filter(f => !f.intro);
    let frame;
    if (stop.frame != null) {
      const f = p.frames[stop.frame];
      frame = f.intro ? '' : sc.num ? `${sc.num}.${f.n}  ${f.title}` : f.title;
    } else if (sc.num && panels.length) {
      const a = panels[0].n, b = panels[panels.length - 1].n;
      frame = a === b ? `${sc.num}.${a}  ${panels[0].title}` : `${sc.num}.${a} – ${sc.num}.${b}`;
    } else frame = (panels[0] || p.frames[0]).title;
    return { scene, frame: frame === scene ? '' : frame };
  }

  function updateChrome() {
    const L = list(), stop = L[idx], { scene, frame } = label(stop);
    $('cap-scene').textContent = scene;
    $('cap-frame').textContent = frame || (matchMedia('(max-width:560px)').matches ? scene : '');
    $('cap-count').textContent = `${idx + 1}/${L.length}`;
    $('progress').firstElementChild.style.width = `${(idx / Math.max(1, L.length - 1)) * 100}%`;
    $('prev').disabled = idx === 0;
    tuckCaption();
    if (view !== 'reader') return;
    const pos = { page: stop.page + 1, frame: stop.frame != null ? stop.frame + 1 : 0 };
    const h = `#${comic.id}/p${pos.page}` + (pos.frame ? `f${pos.frame}` : '');
    try { history.replaceState(history.state, '', h); } catch { /* file:// */ }
    document.title = `${frame || scene} · ${comic.title}`;
    const sc = comic.scenes[pages[stop.page].scene];
    store.set('mve-pos-' + comic.id, JSON.stringify({ ...pos, where: sc.num ? `${sceneWord()} ${sc.num}` : sc.title }));
  }

  // The caption stays put when there is empty space under the art;
  // otherwise it shows briefly after each move and then fades away.
  function tuckCaption() {
    const cap = $('caption');
    clearTimeout(capTimer);
    cap.classList.remove('tucked');
    const R = list()[idx].R, vw = stage.clientWidth, vh = stage.clientHeight;
    const s = Math.min(vw / R.w, vh / R.h), room = (vh - R.h * s) / 2;
    if (room < 34) capTimer = setTimeout(() => cap.classList.add('tucked'), 2200);
  }

  function wake(hold) {
    document.body.classList.remove('idle');
    clearTimeout(idleTimer);
    if (!hold) idleTimer = setTimeout(() => {
      if (view === 'reader' && $('index').hidden && $('end').hidden) document.body.classList.add('idle');
    }, 2800);
  }

  /* ---------- routing ---------- */

  function parseRoute() {
    const h = decodeURIComponent(location.hash.replace(/^#\/?/, ''));
    let m = /^p(\d+)(?:f(\d+))?$/.exec(h);
    if (m) return { id: LEGACY_COMIC, page: +m[1], frame: m[2] ? +m[2] : 0 };
    m = /^([\w-]+)(?:\/p(\d+)(?:f(\d+))?)?\/?$/.exec(h);
    if (m) return { id: m[1], page: m[2] ? +m[2] : 0, frame: m[3] ? +m[3] : 0 };
    return {};
  }

  function route() {
    const r = parseRoute();
    if (!r.id || !library.comics.some(c => c.id === r.id)) {
      if (location.hash) history.replaceState(history.state, '', location.pathname + location.search);
      showShelf();
      return Promise.resolve();
    }
    return openComic(r.id, r.page, r.frame);
  }

  function navigate(hash, fromShelf) {
    history.pushState(fromShelf ? { fromShelf: true } : null, '', hash || location.pathname + location.search);
    route();
  }

  function goShelf() {
    if (history.state && history.state.fromShelf) history.back();
    else navigate('', false);
  }

  async function openComic(id, page, frame) {
    const token = ++loadToken;
    const wasReading = view === 'reader';
    let fresh = false;
    if (!comic || comic.id !== id) {
      let data;
      try {
        data = await fetchComic(id);
      } catch (err) {
        if (token !== loadToken) return;
        console.error(err);
        toast('Could not load that comic. Check your connection and try again.');
        if (!wasReading) { history.replaceState(null, '', location.pathname + location.search); showShelf(); }
        return;
      }
      if (token !== loadToken) return;
      setupComic(data);
      fresh = true;
    }
    if (!wasReading || fresh) mode = pref === 'auto' ? autoMode() : pref;
    syncModeButtons();
    const p = Math.min(Math.max(page || 1, 1), pages.length) - 1;
    const f = Math.min(Math.max(frame || 1, 1), pages[p].frames.length) - 1;
    const target = indexFor(p, f);
    closeOverlays();
    if (wasReading && !fresh) {
      if (target !== idx) goTo(target, 'fade');
    } else {
      jumpTo(target);
      enterReader();
      updateChrome();
    }
    document.body.classList.toggle('fresh', idx === 0);
  }

  /* ---------- index overlay ---------- */

  function buildIndex() {
    const body = $('index-body');
    body.textContent = '';
    comic.scenes.forEach((sc, si) => {
      const sec = make('div', 'scene');
      const h = make('h3');
      if (sc.num) h.append(make('b', null, `${sceneWord()} ${sc.num}`));
      h.append(sc.title);
      const cards = make('div', 'cards');
      pages.forEach((p, pi) => {
        if (p.scene !== si) return;
        // Covers and extra-wide strips are shown whole rather than cropped to the 3:2 thumbnail box.
        const card = make('div', 'card' + (p.h > p.w ? ' tall' : p.w / p.h > 1.6 ? ' wide' : ''));
        card.dataset.page = pi;
        const tb = make('button', 'thumb');
        const img = new Image();
        img.loading = 'lazy';
        img.alt = '';
        img.src = p.thumb;
        tb.append(img);
        tb.setAttribute('aria-label', `Go to page ${pi + 1}`);
        tb.onclick = () => openAt(pi, 0);
        const ol = make('ol');
        p.frames.forEach((f, fi) => {
          if (f.intro) return;              // the thumbnail already opens the whole page
          const li = make('li'), b = make('button');
          b.append(make('span', null, sc.num ? `${sc.num}.${f.n}` : '•'), f.title);
          b.onclick = () => openAt(pi, fi);
          li.append(b);
          ol.append(li);
        });
        card.append(tb, ol);
        cards.append(card);
      });
      sec.append(h, cards);
      body.append(sec);
    });
  }

  function toggleIndex(open) {
    const el = $('index');
    el.hidden = !open;
    if (open) {
      $('end').hidden = true;
      wake(true);
      const cur = list()[idx].page;
      el.querySelectorAll('.card').forEach(c => c.classList.toggle('current', +c.dataset.page === cur));
      el.querySelector('.card.current')?.scrollIntoView({ block: 'center' });
      $('close-index').focus({ preventScroll: true });
    } else wake();
  }

  function openAt(page, frame) {
    toggleIndex(false);
    document.body.classList.remove('fresh');
    goTo(indexFor(page, frame), 'fade');
  }

  /* ---------- end of a comic ---------- */

  function showEnd() {
    const done = comic.status !== 'in-progress';
    $('end-kicker').textContent = done ? 'The End' : 'To be continued…';
    $('end-title').textContent = comic.title;
    $('end-note').textContent = done ? 'Thanks for reading.'
      : `This one is still being drawn. New ${comic.unit || 'strip'}s are on the way.`;
    const others = library.comics.filter(c => c.id !== comic.id);
    $('end-books').replaceChildren(...others.map(c => bookLink(c, 'mini')));
    $('end-more').hidden = !others.length;
    $('end').hidden = false;
    wake(true);
    $('end-shelf').focus({ preventScroll: true });
  }

  function hideEnd() {
    if ($('end').hidden) return;
    $('end').hidden = true;
    wake();
  }

  function closeOverlays() {
    $('index').hidden = true;
    $('end').hidden = true;
  }

  /* ---------- input ---------- */

  function onBookClick(e) {
    const a = e.target.closest('a.book');
    if (!a || e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    navigate(a.getAttribute('href'), view === 'shelf');
  }

  function bindInput() {
    let drag = null;
    const zoomed = () => (window.visualViewport?.scale || 1) > 1.02;
    window.visualViewport?.addEventListener('resize', () => stage.classList.toggle('zoomed', zoomed()));

    stage.addEventListener('pointerdown', e => {
      if (e.button || zoomed() || drag || !comic) return;
      drag = { id: e.pointerId, x: e.clientX, y: e.clientY, t: performance.now(), dx: 0, moved: false };
      try { stage.setPointerCapture(e.pointerId); } catch { /* ignore */ }
    });
    stage.addEventListener('pointermove', e => {
      if (e.pointerType === 'mouse' && view === 'reader') wake();
      if (!drag || e.pointerId !== drag.id) return;
      drag.dx = e.clientX - drag.x;
      if (!drag.moved && Math.abs(drag.dx) > 10 && Math.abs(drag.dx) > Math.abs(e.clientY - drag.y)) {
        drag.moved = true;
        cancelAnimationFrame(raf); setBlur(0);
      }
      if (drag.moved) {
        const atEdge = (drag.dx > 0 && idx === 0) || (drag.dx < 0 && idx === list().length - 1);
        dragPx = atEdge ? drag.dx * .25 : drag.dx;
        render();
      }
    });
    const end = e => {
      if (!drag || e.pointerId !== drag.id) return;
      const d = drag; drag = null;
      if (e.type === 'pointercancel') { if (dragPx) animateTo(list()[idx].R, 240); return; }
      if (d.moved) {
        const fast = Math.abs(d.dx) / (performance.now() - d.t) > .45;
        const farEnough = Math.abs(d.dx) > Math.min(110, stage.clientWidth * .2);
        if (fast || farEnough) step(d.dx < 0 ? 1 : -1);
        else animateTo(list()[idx].R, 240);
        return;
      }
      if (Math.abs(e.clientY - d.y) > 12) return;         // a vertical flick, not a tap
      const fx = e.clientX / stage.clientWidth;
      if (fx < .3) step(-1);
      else if (fx > .7) step(1);
      else if (document.body.classList.contains('idle')) wake();
      else { clearTimeout(idleTimer); document.body.classList.add('idle'); }
    };
    stage.addEventListener('pointerup', end);
    stage.addEventListener('pointercancel', end);

    $('prev').onclick = () => { step(-1); wake(); };
    $('next').onclick = () => { step(1); wake(); };
    $('mode-strip').onclick = () => setMode('strip', true);
    $('mode-frame').onclick = () => setMode('frame', true);
    $('open-index').onclick = () => toggleIndex(true);
    $('close-index').onclick = () => toggleIndex(false);
    $('to-shelf').onclick = goShelf;
    $('end-shelf').onclick = goShelf;
    $('end-restart').onclick = () => { hideEnd(); goTo(0, 'fade'); };
    $('end').addEventListener('click', e => { if (e.target === $('end')) hideEnd(); });
    $('books').addEventListener('click', onBookClick);
    $('end-books').addEventListener('click', onBookClick);

    const fsEl = document.documentElement;
    const canFs = fsEl.requestFullscreen || fsEl.webkitRequestFullscreen;
    const toggleFs = () => {
      if (document.fullscreenElement || document.webkitFullscreenElement)
        (document.exitFullscreen || document.webkitExitFullscreen).call(document);
      else (fsEl.requestFullscreen || fsEl.webkitRequestFullscreen).call(fsEl);
    };
    if (canFs) $('fullscreen').onclick = toggleFs; else $('fullscreen').hidden = true;

    addEventListener('keydown', e => {
      if (view !== 'reader' || e.metaKey || e.ctrlKey || e.altKey) return;
      const indexOpen = !$('index').hidden, endOpen = !$('end').hidden;
      if (e.key === 'Escape') {
        if (indexOpen) toggleIndex(false);
        else if (endOpen) hideEnd();
        return;
      }
      if (indexOpen) { if (e.key === 'i' || e.key === 'I') toggleIndex(false); return; }
      if (endOpen) {
        if (['ArrowLeft', 'ArrowUp', 'PageUp', 'k'].includes(e.key)) { hideEnd(); e.preventDefault(); }
        return;
      }
      const onButton = e.target instanceof HTMLButtonElement;
      switch (e.key) {
        case 'ArrowRight': case 'ArrowDown': case 'PageDown': case 'j': step(1); break;
        case 'ArrowLeft': case 'ArrowUp': case 'PageUp': case 'k': step(-1); break;
        case ' ': if (onButton) return; step(e.shiftKey ? -1 : 1); break;
        case 'Home': goTo(0); break;
        case 'End': goTo(list().length - 1); break;
        case 's': case 'S': case 'm': case 'M': setMode(mode === 'strip' ? 'frame' : 'strip', true); break;
        case 'i': case 'I': toggleIndex(true); break;
        case 'f': case 'F': if (canFs) toggleFs(); break;
        default: return;
      }
      e.preventDefault();
    });

    let resizeT;
    addEventListener('resize', () => {
      clearTimeout(resizeT);
      resizeT = setTimeout(() => {
        if (!comic) return;
        if (pref === 'auto') setMode(autoMode(), false);
        cancelAnimationFrame(raf); clearTimeout(fadeTimer); win.classList.remove('fade');
        dragPx = 0; setBlur(0);
        cam = { ...list()[idx].R }; render(); tuckCaption();
      }, 60);
    });
    // Both fire for some navigations; route() is safe to repeat.
    addEventListener('popstate', () => { if (library) route(); });
    addEventListener('hashchange', () => { if (library) route(); });
  }

  /* ---------- go ---------- */

  async function init() {
    buildBlurFilters();
    bindInput();
    syncModeButtons();
    library = await getJSON('comics/index.json');
    $('books').replaceChildren(...library.comics.map(c => bookLink(c)));
    await route();
    document.body.classList.remove('loading');
  }

  init().catch(err => {
    console.error(err);
    document.body.classList.remove('loading');
    document.body.classList.add('shelf-view');
    $('books').replaceChildren(make('p', 'lead', 'Could not load the comics. Please reload the page.'));
  });
})();
