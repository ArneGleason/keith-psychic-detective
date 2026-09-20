/* Comic viewer: every page sits on one long horizontal ribbon, and a camera
   glides along it. A "stop" is either a whole page (strip mode) or a single
   frame (frame mode). */
(() => {
  'use strict';

  const RH = 1024;               // ribbon height; every page is scaled to it
  const GAP = 140;               // ribbon units between pages
  const AUTO_FRAME_BELOW = 900;  // strip narrower than this many CSS px => frame mode
  const BLUR_LEVELS = [1.5, 3, 5, 7.5, 10.5, 14];
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

  const $ = id => document.getElementById(id);
  const stage = $('stage'), win = $('win'), ribbon = $('ribbon'), bump = $('bump');
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
  };

  let comic, pages, stops = { strip: [], frame: [] };
  let pref = store.get('krpd-mode') || 'auto';   // auto | strip | frame
  let mode = 'strip', idx = 0;
  let cam = { x: 0, y: 0, w: 1536, h: RH }, dragPx = 0, scale = 1;
  let raf = 0, idleTimer = 0, capTimer = 0;

  /* ---------- setup ---------- */

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
      slot.style.cssText = `--x:${p.X};--w:${p.W};--h:${RH};background-image:url(${p.thumb})`;
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
    return (vh - wh) / 2;
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
    cam.x -= dragPx / scale; dragPx = 0;          // fold any drag into the camera
    if (reduceMotion || dur <= 0) { cam = { ...R }; setBlur(0); render(); return; }
    const from = { ...cam }, t0 = performance.now();
    let lastT = t0, lastC = (from.x + from.w / 2);
    const step = now => {
      const t = Math.min(1, (now - t0) / dur), e = ease(t);
      cam = {
        x: from.x + (R.x - from.x) * e, y: from.y + (R.y - from.y) * e,
        w: from.w + (R.w - from.w) * e, h: from.h + (R.h - from.h) * e,
      };
      render();
      const c = cam.x + cam.w / 2, dt = Math.max(1, now - lastT);
      setBlur(Math.abs(c - lastC) * scale / dt);
      lastT = now; lastC = c;
      if (t < 1) raf = requestAnimationFrame(step);
      else { cam = { ...R }; setBlur(0); render(); }
    };
    raf = requestAnimationFrame(step);
  }

  function fadeTo(R) {
    cancelAnimationFrame(raf);
    dragPx = 0; setBlur(0);
    if (reduceMotion) { cam = { ...R }; render(); return; }
    win.classList.add('fade');
    setTimeout(() => { cam = { ...R }; render(); win.classList.remove('fade'); }, 170);
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
    if (how === 'jump') { cam = { ...next.R }; render(); }
    else if (how === 'fade' || far) fadeTo(next.R);
    else animateTo(next.R, next.page === prev.page ? 430 : 540);
    updateChrome();
  }

  function step(d) {
    document.body.classList.remove('fresh');
    const i = idx + d;
    if (i < 0 || i >= list().length) {
      if (dragPx) animateTo(list()[idx].R, 260);
      bump.className = ''; void bump.offsetWidth; bump.className = d > 0 ? 'r' : 'l';
      return;
    }
    goTo(i);
  }

  function setMode(m, explicit) {
    if (explicit) { pref = m; store.set('krpd-mode', m); }
    if (m !== mode) {
      const cur = list()[idx];
      mode = m;
      idx = m === 'strip' ? cur.page
        : stops.frame.findIndex(s => s.page === cur.page);
      animateTo(list()[idx].R, 480);
    }
    $('mode-strip').setAttribute('aria-pressed', mode === 'strip');
    $('mode-frame').setAttribute('aria-pressed', mode === 'frame');
    updateChrome();
  }

  function autoMode() {
    const s = Math.min(stage.clientWidth / 1536, stage.clientHeight / RH);
    return 1536 * s < AUTO_FRAME_BELOW ? 'frame' : 'strip';
  }

  /* ---------- captions, hash, chrome ---------- */

  function label(stop) {
    const p = pages[stop.page], sc = comic.scenes[p.scene];
    const scene = sc.num ? `Scene ${sc.num} · ${sc.title}` : sc.title;
    let frame;
    if (stop.frame != null) {
      const f = p.frames[stop.frame];
      frame = sc.num ? `${sc.num}.${f.n}  ${f.title}` : f.title;
    } else if (sc.num) {
      const a = p.frames[0].n, b = p.frames[p.frames.length - 1].n;
      frame = a === b ? `${sc.num}.${a}` : `${sc.num}.${a} – ${sc.num}.${b}`;
    } else frame = p.frames[0].title;
    return { scene, frame: frame === scene ? '' : frame };
  }

  function updateChrome() {
    const L = list(), stop = L[idx], { scene, frame } = label(stop);
    $('cap-scene').textContent = scene;
    $('cap-frame').textContent = frame || (matchMedia('(max-width:520px)').matches ? scene : '');
    $('cap-count').textContent = `${idx + 1}/${L.length}`;
    $('progress').firstElementChild.style.width = `${(idx / (L.length - 1)) * 100}%`;
    $('prev').disabled = idx === 0;
    $('next').disabled = idx === L.length - 1;
    const h = `#p${stop.page + 1}` + (stop.frame != null ? `f${stop.frame + 1}` : '');
    try { history.replaceState(null, '', h); } catch { /* file:// */ }
    document.title = `${frame || scene} · ${comic.title}`;
    tuckCaption();
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

  function parseHash() {
    const m = /^#p(\d+)(?:f(\d+))?$/.exec(location.hash);
    if (!m) return null;
    const page = Math.min(pages.length, Math.max(1, +m[1])) - 1;
    const frame = m[2] ? Math.min(pages[page].frames.length, Math.max(1, +m[2])) - 1 : 0;
    return { page, frame };
  }

  function indexFor(page, frame) {
    return mode === 'strip' ? page
      : stops.frame.findIndex(s => s.page === page && s.frame === frame);
  }

  function wake(hold) {
    document.body.classList.remove('idle');
    clearTimeout(idleTimer);
    if (!hold) idleTimer = setTimeout(() => {
      if ($('index').hidden) document.body.classList.add('idle');
    }, 2800);
  }

  /* ---------- index overlay ---------- */

  function buildIndex() {
    const body = $('index-body');
    comic.scenes.forEach((sc, si) => {
      const sec = document.createElement('div');
      sec.className = 'scene';
      const h = document.createElement('h3');
      h.innerHTML = sc.num ? `<b>Scene ${sc.num}</b>` : '';
      h.append(sc.title);
      const cards = document.createElement('div');
      cards.className = 'cards';
      pages.forEach((p, pi) => {
        if (p.scene !== si) return;
        const card = document.createElement('div');
        card.className = 'card' + (p.h > p.w ? ' tall' : '');
        card.dataset.page = pi;
        const tb = document.createElement('button');
        tb.className = 'thumb';
        tb.innerHTML = `<img loading="lazy" alt="" src="${p.thumb}">`;
        tb.setAttribute('aria-label', `Go to page ${pi + 1}`);
        tb.onclick = () => openAt(pi, 0);
        const ol = document.createElement('ol');
        p.frames.forEach((f, fi) => {
          const li = document.createElement('li'), b = document.createElement('button');
          const num = document.createElement('span');
          num.textContent = sc.num ? `${sc.num}.${f.n}` : '•';
          b.append(num, f.title);
          b.onclick = () => openAt(pi, fi);
          li.append(b); ol.append(li);
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
      wake(true);
      const cur = list()[idx].page;
      el.querySelectorAll('.card').forEach(c => c.classList.toggle('current', +c.dataset.page === cur));
      el.querySelector('.card.current')?.scrollIntoView({ block: 'center' });
      $('close-index').focus();
    } else wake();
  }

  function openAt(page, frame) {
    toggleIndex(false);
    document.body.classList.remove('fresh');
    goTo(indexFor(page, frame), 'fade');
  }

  /* ---------- input ---------- */

  function bindInput() {
    let drag = null;
    const zoomed = () => (window.visualViewport?.scale || 1) > 1.02;
    window.visualViewport?.addEventListener('resize', () => stage.classList.toggle('zoomed', zoomed()));

    stage.addEventListener('pointerdown', e => {
      if (e.button || zoomed() || drag) return;
      drag = { id: e.pointerId, x: e.clientX, y: e.clientY, t: performance.now(), dx: 0, moved: false };
      try { stage.setPointerCapture(e.pointerId); } catch { /* ignore */ }
    });
    stage.addEventListener('pointermove', e => {
      if (e.pointerType === 'mouse') wake();
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

    const fsEl = document.documentElement;
    const canFs = fsEl.requestFullscreen || fsEl.webkitRequestFullscreen;
    const toggleFs = () => {
      if (document.fullscreenElement || document.webkitFullscreenElement)
        (document.exitFullscreen || document.webkitExitFullscreen).call(document);
      else (fsEl.requestFullscreen || fsEl.webkitRequestFullscreen).call(fsEl);
    };
    if (canFs) $('fullscreen').onclick = toggleFs; else $('fullscreen').hidden = true;

    addEventListener('keydown', e => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const indexOpen = !$('index').hidden;
      if (e.key === 'Escape') { if (indexOpen) toggleIndex(false); return; }
      if (indexOpen) { if (e.key === 'i' || e.key === 'I') toggleIndex(false); return; }
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
        if (pref === 'auto') setMode(autoMode(), false);
        cancelAnimationFrame(raf); dragPx = 0; setBlur(0);
        cam = { ...list()[idx].R }; render(); tuckCaption();
      }, 60);
    });
    addEventListener('hashchange', () => {
      const h = parseHash(); if (!h) return;
      if (!$('index').hidden) toggleIndex(false);
      const i = indexFor(h.page, h.frame);
      if (i !== idx) goTo(i, 'fade');
    });
  }

  /* ---------- go ---------- */

  async function init() {
    comic = await (await fetch('comic.json')).json();
    pages = comic.pages;
    $('title').textContent = comic.title;
    buildBlurFilters();
    buildLayout();
    buildIndex();
    mode = pref === 'auto' ? autoMode() : pref;
    const h = parseHash();
    idx = h ? indexFor(h.page, h.frame) : 0;
    if (idx === 0) document.body.classList.add('fresh');
    setMode(mode, false);
    mountAround(list()[idx].page);
    cam = { ...list()[idx].R };
    render();
    bindInput();
    updateChrome();
    document.body.classList.remove('loading');
    wake();
  }

  init().catch(err => {
    console.error(err);
    document.body.classList.remove('loading');
    $('hint').textContent = 'Could not load the comic. Please reload.';
    $('hint').style.opacity = 1;
  });
})();
