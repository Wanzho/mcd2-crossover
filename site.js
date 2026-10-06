/* MCD2 Crossover site: page interactions and reveals. No libraries.
   Nothing is tied to the scroll position: each scene plays by itself, on a timer,
   once it comes into view, so it looks the same however smoothly someone scrolls.
   Every feature starts on its own (see run()), so one missing element can't stop
   the rest. The only network request is an optional one to GitHub's public API for
   the newest release (see privacy.html). app-demo.js builds the "Try it" replica;
   this file never touches #app-demo. */
(function () {
  'use strict';
  window.__mcdSite = true;

  var doc = document, root = doc.documentElement;
  var motion = root.classList.contains('motion');
  var hasIO = 'IntersectionObserver' in window;
  var api = window.__mcd = { motion: motion, errors: [] };
  var $ = function (s, c) { return (c || doc).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || doc).querySelectorAll(s)); };

  function run(name, fn) {
    try { fn(); } catch (err) {
      api.errors.push(name);
      if (window.console && console.error) console.error('MCD2 Crossover site: "' + name + '" did not start', err);
    }
  }
  function onView(els, cb, opts) {
    els = els.filter(Boolean);
    if (!els.length) return null;
    if (!hasIO) { els.forEach(function (el) { cb(el, true, { unobserve: function () {}, disconnect: function () {} }, { intersectionRatio: 1 }); }); return null; }
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { cb(e.target, e.isIntersecting, io, e); });
    }, opts || {});
    els.forEach(function (el) { io.observe(el); });
    return io;
  }
  function inViewNow(el) {
    if (!el) return false;
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.top < window.innerHeight && r.bottom > 0;
  }
  // add a class with no transition (for things already on screen at load)
  function setNow(els, cls) {
    els = els.filter(Boolean);
    if (!els.length) return;
    els.forEach(function (el) { el.style.transition = 'none'; el.classList.add(cls); });
    void doc.body.offsetHeight;
    requestAnimationFrame(function () { els.forEach(function (el) { el.style.transition = ''; }); });
  }
  // a one-time class once an element scrolls into view
  function inOnce(el, cls, threshold) {
    if (!el) return;
    if (!motion || inViewNow(el)) { setNow([el], cls); return; }
    onView([el], function (t, on, io) {
      if (!on) return;
      io.disconnect();
      el.classList.add(cls);
    }, { threshold: threshold || 0.15 });
  }

  /* ---------- live region for small announcements ---------- */
  var live = null;
  function announce(t) {
    if (!live) return;
    live.textContent = '';
    setTimeout(function () { live.textContent = t; }, 30);
  }
  run('live region', function () {
    live = doc.createElement('p');
    live.className = 'sr';
    live.setAttribute('aria-live', 'polite');
    doc.body.appendChild(live);
  });

  /* ---------- the newest release: version, size and a direct link to its .dmg (optional, cached for the session) ---------- */
  run('release', function () {
    function nb(s) { return s.replace(/-/g, '‑'); }
    function apply(r) {
      if (!r || !r.v) return;
      $$('[data-version]').forEach(function (el) { el.textContent = 'Version ' + r.v; });
      if (!r.url || !r.name) return;
      $$('[data-dl]').forEach(function (a) { a.href = r.url; });
      $$('[data-dl-name]').forEach(function (el) { el.textContent = 'Download ' + nb(r.name); });
      $$('[data-dmg]').forEach(function (el) { el.textContent = nb(r.name); });
      if (r.mb) $$('[data-size]').forEach(function (el) { el.textContent = 'About ' + r.mb + ' MB'; });
    }
    var key = 'mcd2-release', cached = null;
    try { cached = JSON.parse(sessionStorage.getItem(key) || 'null'); } catch (e) { /* private mode */ }
    if (cached) { apply(cached); return; }
    if (!window.fetch) return;
    setTimeout(function () {
      fetch('https://api.github.com/repos/Wanzho/mcd2-crossover/releases/latest', { credentials: 'omit', referrerPolicy: 'no-referrer' })
        .then(function (res) { return res.ok ? res.json() : null; })
        .then(function (j) {
          var m = /^v?(\d{1,3}(?:\.\d{1,4}){1,3})$/.exec((j && j.tag_name) || '');
          if (!m) return;
          var r = { v: m[1] };
          (j.assets || []).forEach(function (a) {
            if (r.url || !/\.dmg$/i.test(a.name || '')) return;
            if (!/^https:\/\/github\.com\/Wanzho\/mcd2-crossover\/releases\/download\//.test(a.browser_download_url || '')) return;
            r.url = a.browser_download_url;
            r.name = a.name;
            r.mb = a.size ? Math.round(a.size / 1e6) : 0;
          });
          apply(r);
          try { sessionStorage.setItem(key, JSON.stringify(r)); } catch (e) { /* ignore */ }
        })
        .catch(function () { /* keep the built-in version */ });
    }, 1200);
  });

  /* ---------- local nav ---------- */
  run('nav', function () {
    var nav = $('#localnav');
    if (!nav) return;
    var toggle = $('.ln-toggle', nav);
    function setMenu(open) {
      nav.classList.toggle('is-open', open);
      if (!toggle) return;
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Hide sections' : 'Show sections');
    }
    if (toggle) toggle.addEventListener('click', function () { setMenu(!nav.classList.contains('is-open')); });
    $$('.ln-links a', nav).forEach(function (a) { a.addEventListener('click', function () { setMenu(false); }); });
    doc.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && nav.classList.contains('is-open')) { setMenu(false); if (toggle) toggle.focus(); }
    });
    doc.addEventListener('click', function (e) { if (nav.classList.contains('is-open') && !nav.contains(e.target)) setMenu(false); });

    // the section in view
    var links = {}, current = null;
    $$('.ln-links a', nav).forEach(function (a) { links[(a.getAttribute('href') || '').slice(1)] = a; });
    onView($$('main > section'), function (el, on) {
      if (!on) return;
      var link = links[el.id] || null;
      if (link === current) return;
      if (current) current.removeAttribute('aria-current');
      if (link) link.setAttribute('aria-current', 'true');
      current = link;
    }, { rootMargin: '-50% 0px -50% 0px' });

    // a darker bar once the page moves
    var ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () { ticking = false; nav.classList.toggle('is-scrolled', window.pageYOffset > 10); });
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  });

  /* ---------- reveals ---------- */
  var reveals = [];
  function revealNow() {
    setNow(reveals.filter(function (el) { return !el.classList.contains('in') && inViewNow(el); }), 'in');
  }
  run('reveals', function () {
    reveals = $$('.reveal');
    reveals.forEach(function (el) {
      var sibs = $$(':scope > .reveal', el.parentElement);
      var i = sibs.indexOf(el);
      if (i > 0) el.style.setProperty('--rd', Math.min(i, 5) * 0.09 + 's');
    });
    if (!motion) return;
    revealNow();   // anything already on screen shows at once, so the first paint is never blank
    onView(reveals, function (el, on, io) {
      if (on) { el.classList.add('in'); io.unobserve(el); }
    }, { rootMargin: '0px 0px -7% 0px', threshold: 0.1 });
  });

  /* ---------- statement: the words light up in turn once it's in view ---------- */
  run('statement', function () {
    var p = $('.statement-text');
    if (!p) return;
    var i = 0;
    (function split(node) {
      Array.prototype.slice.call(node.childNodes).forEach(function (n) {
        if (n.nodeType === 3) {
          var frag = doc.createDocumentFragment();
          n.nodeValue.split(/(\s+)/).forEach(function (t) {
            if (!t) return;
            if (/^\s+$/.test(t)) { frag.appendChild(doc.createTextNode(t)); return; }
            var w = doc.createElement('span');
            w.className = 'w';
            w.style.setProperty('--wi', i++);
            w.textContent = t;
            frag.appendChild(w);
          });
          node.replaceChild(frag, n);
        } else if (n.nodeType === 1) split(n);
      });
    })(p);
    if (!motion) { p.classList.add('is-lit'); return; }
    onView([p], function (el, on, io) {
      if (!on) return;
      io.disconnect();
      p.classList.add('is-lit');
    }, { rootMargin: '0px 0px -12% 0px', threshold: 0.3 });
  });

  /* ---------- try it: the replica grows into place ---------- */
  run('demo frame', function () { inOnce($('.demo-frame'), 'is-in', 0.12); });

  /* ---------- fixes: tiles rise in; point at one (or tap it) for the why and the fix ---------- */
  run('fixes', function () {
    var grid = $('.fix-grid');
    if (!grid) return;
    $$('.fix', grid).forEach(function (f, i) { f.style.setProperty('--fi', i % 4); });
    inOnce(grid, 'is-in', 0.08);
    $$('.fix-btn', grid).forEach(function (b) {
      b.addEventListener('click', function () {
        b.setAttribute('aria-expanded', String(b.getAttribute('aria-expanded') !== 'true'));
      });
      b.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && b.getAttribute('aria-expanded') === 'true') b.setAttribute('aria-expanded', 'false');
      });
    });
  });

  /* ---------- install: the steps count in ---------- */
  run('install', function () {
    var panel = $('.panel');
    if (!panel) return;
    $$('.steps li', panel).forEach(function (li, i) { li.style.setProperty('--si', i); });
    inOnce(panel, 'is-in', 0.15);
  });

  /* ---------- wasdmod: the keys tap along once it's in view ---------- */
  run('pair', function () { inOnce($('.pair'), 'is-in', 0.3); });

  /* ---------- FAQ: smooth open and close ---------- */
  run('faq', function () {
    $$('.faq-item').forEach(function (d) {
      var sum = $('summary', d), body = $('.faq-a', d), anim = null;
      if (!sum || !body) return;
      var state = d.open ? 'open' : 'closed';
      sum.addEventListener('click', function (e) {
        if (!motion || !body.animate) return;
        e.preventDefault();
        var from = body.offsetHeight;
        if (anim) anim.cancel();
        if (state === 'closed' || state === 'closing') {
          if (state === 'closed') from = 0;
          d.open = true;
          state = 'opening';
          var to = body.scrollHeight;
          anim = body.animate([{ height: from + 'px', opacity: from ? 1 : 0 }, { height: to + 'px', opacity: 1 }],
            { duration: 460, easing: 'cubic-bezier(.22,.8,.24,1)' });
          anim.onfinish = function () { state = 'open'; anim = null; };
        } else {
          state = 'closing';
          anim = body.animate([{ height: from + 'px', opacity: 1 }, { height: '0px', opacity: 0 }],
            { duration: 340, easing: 'cubic-bezier(.4,0,.2,1)' });
          anim.onfinish = function () { d.open = false; state = 'closed'; anim = null; };
        }
      });
    });
  });

  /* ---------- numbers: odometer roll ---------- */
  run('numbers', function () {
    var nums = $$('.num'), grid = $('.num-grid');
    if (!motion || !nums.length || !grid) return;
    nums.forEach(function (n, ni) {
      n.style.setProperty('--ni', ni);
      var b = $('.num-big[data-roll]', n);
      if (!b) return;
      var raw = b.getAttribute('data-roll'), unit = $('small', b);
      var sr = doc.createElement('span'); sr.className = 'sr'; sr.textContent = b.getAttribute('data-sr') || b.textContent;
      var odo = doc.createElement('span'); odo.className = 'odo'; odo.setAttribute('aria-hidden', 'true');
      var ci = 0;
      raw.split('').forEach(function (ch) {
        if (/\d/.test(ch)) {
          var col = doc.createElement('span');
          col.className = 'odo-col';
          col.style.setProperty('--to', 10 + Number(ch));
          col.style.setProperty('--ci', ci++);
          for (var k = 0; k < 20; k++) { var d = doc.createElement('span'); d.textContent = k % 10; col.appendChild(d); }
          odo.appendChild(col);
        } else {
          var st = doc.createElement('span'); st.className = 'odo-static'; st.textContent = ch; odo.appendChild(st);
        }
      });
      b.textContent = '';
      b.appendChild(sr);
      b.appendChild(odo);
      if (unit) { unit.setAttribute('aria-hidden', 'true'); b.appendChild(unit); }
    });
    onView([grid], function (el, on, io) {
      if (!on) return;
      io.disconnect();
      nums.forEach(function (n) { n.classList.add('is-rolled'); });
    }, { threshold: 0.35 });
  });

  /* ======================================================================
     The portal: six errors float around a dark portal. When the block fills
     the screen it lights up and takes the first three (Visual C++, Game
     Runtime, 0060) on a timer. Then it's the visitor's turn: click the rest
     in, and Play appears. Clicking any error early skips the demo.
     ====================================================================== */
  run('portal', function () {
    var show = $('.show'), stage = $('.show-stage');
    if (!show || !stage) return;
    var pin = $('.show-pin') || show;     // pinned (sticky) on most screens; plain flow otherwise
    var errs = $$('.err', show), chips = $$('.fixed-row li', show);
    var play = $('.pt-play', show), toast = $('.pt-toast', show), again = $('.sp-again', show);
    var voidEl = $('.pt-void', show), burst = $('.pt-burst', show), flash = $('.pt-flash', show);
    if (!errs.length || !voidEl) return;

    var state = 'idle';                 // idle → shown → demo → live → open → played
    var gone = [], left = errs.length, visible = false, startTimer = 0, revealedAt = 0;
    var demoT = 0, demoLast = 0, demoRaf = 0, demoNext = 0;
    var gen = 0;                        // bumped by Again, so late timers from an earlier round do nothing
    // [time in ms, what happens]
    var STEPS = [[0, 'light'], [1000, 0], [1600, 1], [2200, 2], [3000, 'turn']];

    errs.forEach(function (el, i) {
      var t = $('.err-t', el), c = $('.err-c', el) || $('.err-s', el);
      el.setAttribute('aria-label', 'Send to the portal: ' + (t ? t.textContent : '') + (c ? ', ' + c.textContent : ''));
      gone[i] = false;
    });

    function em() { return parseFloat(getComputedStyle(stage).fontSize) || 12; }
    function sparks() {
      if (!burst || !motion || !burst.animate) return;
      var size = em();
      for (var k = 0; k < 14; k++) {
        var s = doc.createElement('i');
        burst.appendChild(s);
        var a = Math.random() * Math.PI * 2, d = (5 + Math.random() * 8) * size;
        var anim = s.animate([
          { transform: 'translate(0,0) scale(1)', opacity: 1 },
          { transform: 'translate(' + (Math.cos(a) * d).toFixed(1) + 'px,' + (Math.sin(a) * d * 0.8).toFixed(1) + 'px) scale(.2)', opacity: 0 }
        ], { duration: 520 + Math.random() * 420, easing: 'cubic-bezier(.15,.8,.3,1)' });
        anim.onfinish = (function (n) { return function () { n.remove(); }; })(s);
      }
    }
    function gulp() {
      show.classList.remove('is-gulp');
      void show.offsetWidth;
      show.classList.add('is-gulp');
    }
    function light() { show.classList.add('is-in', 'is-lit'); }
    function openUp() {
      if (state === 'open' || state === 'played') return;
      state = 'open';
      show.classList.add('is-open');
      if (play) play.tabIndex = 0;
      announce('All fixed. Press Play.');
    }
    function nextFocus(i) {
      for (var k = 1; k <= errs.length; k++) { var j = (i + k) % errs.length; if (!gone[j]) return errs[j]; }
      return null;
    }
    function fix(i) {
      if (gone[i]) return;
      gone[i] = true;
      left--;
      var el = errs[i], hadFocus = doc.activeElement === el;
      el.tabIndex = -1;
      if (chips[i]) chips[i].classList.add('done');
      announce('Fixed: ' + (chips[i] ? chips[i].textContent : 'error') + '.');
      var finished = false, round = gen;
      function done() {
        if (finished || round !== gen) return;
        finished = true;
        el.classList.add('is-gone');
        if (hadFocus) {
          var n = nextFocus(i);
          if (n) n.focus();
          else if (play) setTimeout(function () { play.focus(); }, motion ? 800 : 0);
        }
        if (left === 0) setTimeout(openUp, motion ? 450 : 0);
      }
      // a hidden tab pauses animations, so it skips straight to the end; a timer backs up onfinish
      if (motion && el.animate && !doc.hidden) {
        var a = el.getBoundingClientRect(), v = voidEl.getBoundingClientRect();
        var dx = (v.left + v.width / 2) - (a.left + a.width / 2), dy = (v.top + v.height * 0.55) - (a.top + a.height / 2);
        var rot = dx < 0 ? 22 : -22;
        var anim = el.animate([
          { transform: 'none', opacity: 1, filter: 'blur(0px)' },
          { transform: 'translate(' + (dx * 0.45).toFixed(1) + 'px,' + (dy * 0.45).toFixed(1) + 'px) scale(.62) rotate(' + rot / 2 + 'deg)', opacity: 1, filter: 'blur(0px)', offset: 0.5 },
          { transform: 'translate(' + dx.toFixed(1) + 'px,' + dy.toFixed(1) + 'px) scale(.04) rotate(' + rot + 'deg)', opacity: 0, filter: 'blur(3px)' }
        ], { duration: 640, easing: 'cubic-bezier(.5,0,.75,.35)', fill: 'forwards' });
        anim.onfinish = function () { if (!finished) { sparks(); gulp(); } done(); };
        setTimeout(function () { if (!finished && round === gen) { anim.finish(); done(); } }, 1200);
      } else done();
    }

    // the demo runs on its own clock, which only moves while the block is on screen
    function demoTick(t) {
      var dt = Math.min(50, Math.max(0, t - demoLast));
      demoLast = t;
      if (visible) demoT += dt;
      while (demoNext < STEPS.length && demoT >= STEPS[demoNext][0]) {
        var what = STEPS[demoNext++][1];
        if (what === 'light') light();
        else if (what === 'turn') { demoRaf = 0; yourTurn(); return; }
        else fix(what);
      }
      demoRaf = requestAnimationFrame(demoTick);
    }
    function startDemo() {
      startTimer = 0;
      if (state !== 'shown' || !visible) return;   // scrolled away before it began: wait for the next time
      state = 'demo';
      demoT = 0;
      demoNext = 0;
      demoLast = performance.now();
      demoRaf = requestAnimationFrame(demoTick);
    }
    function reveal() {
      if (show.classList.contains('is-in')) return;
      show.classList.add('is-in');
      revealedAt = performance.now();
      if (state === 'idle') state = 'shown';
    }
    function maybeStart() {
      if (state !== 'shown' || startTimer) return;
      startTimer = setTimeout(startDemo, Math.max(150, 900 - (performance.now() - revealedAt)));
    }
    function yourTurn() {
      if (demoRaf) { cancelAnimationFrame(demoRaf); demoRaf = 0; }
      if (startTimer) { clearTimeout(startTimer); startTimer = 0; }
      light();
      if (state === 'idle' || state === 'shown' || state === 'demo') state = 'live';
      show.classList.add('is-prompt');
    }

    errs.forEach(function (el, i) {
      el.addEventListener('click', function () {
        if (gone[i] || state === 'played') return;
        if (state !== 'live' && state !== 'open') yourTurn();
        show.classList.add('is-touched');
        fix(i);
      });
    });
    if (play) play.addEventListener('click', function () {
      if (state !== 'open') return;
      state = 'played';
      show.classList.add('is-played');
      play.tabIndex = -1;
      if (toast) toast.textContent = 'Steam is opening the game. You can close this app now.';
      if (flash && motion && flash.animate) {
        flash.animate([
          { opacity: 0, transform: 'scale(.2)' },
          { opacity: 1, transform: 'scale(.9)', offset: 0.3 },
          { opacity: 0, transform: 'scale(1.4)' }
        ], { duration: 1300, easing: 'cubic-bezier(.2,.7,.3,1)' });
      }
      if (again) setTimeout(function () { again.focus({ preventScroll: true }); }, motion ? 600 : 0);
    });
    if (again) again.addEventListener('click', function () {
      gen++;
      errs.forEach(function (el, i) {
        if (el.getAnimations) el.getAnimations().forEach(function (a) { a.cancel(); });
        el.classList.remove('is-gone');
        el.tabIndex = 0;
        gone[i] = false;
      });
      chips.forEach(function (c) { c.classList.remove('done'); });
      left = errs.length;
      if (toast) toast.textContent = '';
      show.classList.remove('is-open', 'is-played', 'is-prompt', 'is-touched');
      if (play) play.tabIndex = -1;
      if (!motion) { state = 'live'; show.classList.add('is-prompt'); errs[0].focus(); return; }
      state = 'shown';
      visible = true;
      startDemo();
      errs[0].focus({ preventScroll: true });
    });

    if (!motion) { state = 'live'; show.classList.add('is-in', 'is-lit', 'is-prompt'); }
    else if (hasIO) {
      new IntersectionObserver(function (es) {
        es.forEach(function (e) {
          // how much of the screen it fills (the pinned block is one screen tall)
          var fill = e.isIntersecting ? Math.max(e.intersectionRatio, e.intersectionRect.height / (window.innerHeight || 1)) : 0;
          visible = fill >= 0.3;
          if (state === 'idle' && fill >= 0.35) reveal();
          if (state === 'shown') {
            if (fill >= 0.85) maybeStart();
            else if (startTimer && fill < 0.5) { clearTimeout(startTimer); startTimer = 0; }
          }
        });
      }, { threshold: [0, 0.2, 0.3, 0.35, 0.5, 0.7, 0.85, 0.95, 1] }).observe(pin);
    } else { visible = true; reveal(); maybeStart(); }
    api.show = { state: function () { return state; }, left: function () { return left; } };
  });

  /* ---------- highlights: a carousel (swipe or scroll sideways, arrows, dots) ---------- */
  run('highlights', function () {
    var view = $('.hl-viewport'), track = $('.hl-track');
    if (!view || !track) return;
    var cards = $$('.hl-card', track), dotsWrap = $('.hl-dots'), arrows = $$('.hl-arrow');
    if (!cards.length) return;
    var targets = [], dots = [], active = -1;
    function measure() {
      var max = Math.max(0, view.scrollWidth - view.clientWidth), base = cards[0].offsetLeft, list = [];
      cards.forEach(function (c, i) {
        var t = Math.max(0, Math.min(c.offsetLeft - base, max));
        if (!list.length || t - list[list.length - 1].t > 4) list.push({ t: t, i: i });
      });
      targets = list;
      if (dotsWrap && dots.length !== targets.length) {
        dotsWrap.textContent = '';
        dots = targets.map(function (tg, k) {
          var b = doc.createElement('button');
          var h = $('h3', cards[tg.i]);
          b.type = 'button';
          b.className = 'hl-dot';
          b.setAttribute('aria-label', h ? h.textContent : 'Highlight ' + (k + 1));
          b.addEventListener('click', function () { go(k); });
          dotsWrap.appendChild(b);
          return b;
        });
        active = -1;
      }
      update();
    }
    function nearest() {
      var x = view.scrollLeft, best = 0, bd = Infinity;
      targets.forEach(function (tg, k) { var d = Math.abs(tg.t - x); if (d < bd) { bd = d; best = k; } });
      return best;
    }
    function update() {
      var k = nearest(), max = view.scrollWidth - view.clientWidth;
      if (k !== active) {
        active = k;
        dots.forEach(function (d, j) { if (j === k) d.setAttribute('aria-current', 'true'); else d.removeAttribute('aria-current'); });
      }
      arrows.forEach(function (a) {
        var dir = +a.getAttribute('data-dir');
        a.disabled = dir < 0 ? view.scrollLeft <= 2 : view.scrollLeft >= max - 2;
      });
    }
    function go(k) {
      if (!targets.length) return;
      k = Math.max(0, Math.min(targets.length - 1, k));
      view.scrollTo({ left: targets[k].t, behavior: motion ? 'smooth' : 'auto' });
    }
    arrows.forEach(function (a) {
      a.addEventListener('click', function () { go(nearest() + (+a.getAttribute('data-dir') || 0)); });
    });
    var ticking = false;
    view.addEventListener('scroll', function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () { ticking = false; update(); });
    }, { passive: true });
    window.addEventListener('resize', measure);
    if ('ResizeObserver' in window) new ResizeObserver(measure).observe(view);
    measure();
    // each card runs its little loop only while it's on screen
    onView(cards, function (el, on) { el.classList.toggle('is-inview', on); }, { threshold: 0.2 });
  });

  /* ---------- debug: ?y=1234 scrolls there on load; anchors line up after the components build ---------- */
  run('jump', function () {
    var qy = /[?&]y=(\d+)/.exec(location.search);
    var moved = false;
    ['wheel', 'touchstart', 'keydown', 'mousedown'].forEach(function (t) {
      window.addEventListener(t, function () { moved = true; }, { passive: true, once: true });
    });
    function jump(y) {
      var prev = root.style.scrollBehavior;
      root.style.scrollBehavior = 'auto';
      window.scrollTo(0, y);
      root.style.scrollBehavior = prev;
    }
    function align() {
      if (qy) { jump(+qy[1]); revealNow(); return; }
      if (moved || !location.hash || location.hash.length < 2) return;
      var t = null;
      try { t = doc.getElementById(decodeURIComponent(location.hash.slice(1))); } catch (e) { /* bad hash */ }
      if (!t) return;
      var pad = parseFloat(getComputedStyle(root).scrollPaddingTop) || 0;
      jump(Math.max(0, t.getBoundingClientRect().top + window.pageYOffset - pad));
    }
    if (qy && 'scrollRestoration' in history) history.scrollRestoration = 'manual';
    align();
    window.addEventListener('load', function () { align(); revealNow(); });
  });
})();
