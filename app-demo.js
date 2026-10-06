/* MCD2 Crossover "Try it" demo: a playable replica of the Mac app in macOS dark mode.
   It rebuilds the app's two screens (setup and home, as in showSetup: in
   packaging/installer.m), its three sheets (Microsoft GDK License, Change Game Copy,
   Troubleshooting) and CrossOver's Xbox sign-in code window, using the English strings
   from localization/en.json word for word. Nothing real happens: timers stand in for
   setup, sign-in and sign-out, the "copied" labels never touch the clipboard and nothing
   leaves the page. Around the app sits page-level UI in the site's cyan (a guide that
   rings the next control, a setup checklist, a sign-in card and a short finale).
   It builds itself inside #app-demo and does nothing when the page has no #app-demo.
   Testing: window.__mcdDemo = { reset(), state(), go(name) }; a #mx-<name> hash
   (e.g. #mx-signin) jumps straight to a state, see go() below. */
(function () {
  'use strict';

  /* ---------- the app's own strings (localization/en.json, verbatim) ---------- */

  var S = {
    setUpTitle: 'Set Up MCD2 Crossover',
    troubleshooting: 'Troubleshooting…',
    troubleTip: 'Record a problem and save troubleshooting logs',
    troubleTipRec: 'Recording troubleshooting logs — click to stop or save',
    introSetup: 'Choose your CrossOver bottle and installed game copy. Changing copies keeps your Microsoft sign-in saved.',
    introHome: 'After setup and your first sign-in, you can play directly from Steam in the selected bottle. This app doesn’t need to stay open.',
    introLauncher: 'Minecraft Launcher support is experimental. Play opens the selected copy in CrossOver; Microsoft still checks game ownership.',
    notSignedIn: 'Not signed in',
    signedInTo: 'Signed in to: ',
    bottleLabel: 'CrossOver Bottle',
    bottleAx: 'CrossOver bottle',
    launcherLabel: 'Launcher:',
    launcherOpt: 'Minecraft Launcher (experimental)',
    gameFolder: 'Game folder: ',
    browse: 'Browse Game Copy…',
    quitFirst: 'Quit the game first. Setup backs up replaced files and leaves saves alone. For Steam copies, it also restarts Steam.',
    viewLicense: 'View Microsoft License…',
    accept: 'I accept the Microsoft GDK license',
    vcpp: 'If Visual C++ is missing, Microsoft’s installer will open for you to finish.',
    experimental: 'Experimental: requires a Launcher-owned copy. Windows Store licensing may prevent it from running in CrossOver.',
    cancel: 'Cancel',
    setUp: 'Set Up',
    play: 'Play',
    signOut: 'Sign Out',
    closeWindow: 'Close Window',
    cancelLaunch: 'Cancel Launch',
    changeCopy: 'Change Game Copy',
    bottleIs: 'CrossOver bottle: ',
    renews: 'Saved sign-in renews in the background. If the game asks you to sign in again, click Play to reconnect.',
    homeStatus: 'To change Microsoft accounts, quit the game and choose Sign Out.',
    settingUp: 'Setting up… If Microsoft’s Visual C++ installer opens, complete it to continue.',
    checking: 'Checking sign-in… If a code window appears, finish signing in and leave it open.',
    removing: 'Removing your saved Microsoft sign-in…',
    setupDone: 'Setup complete. Press Play to open the game.',
    cancelled: 'Launch cancelled.',
    cancelling: 'Cancelling launch…',
    signedOut: 'Signed out. Your saved Microsoft credential and local session were removed. Play will ask you to sign in again.',
    steamOpening: 'Steam is opening the game. You can close this app now.',
    launcherOpening: 'The selected game copy is opening in CrossOver. Launcher support is experimental.',
    licenseTitle: 'Microsoft GDK License',
    done: 'Done',
    tsTitle: 'Troubleshooting',
    tsIntro: 'Setup and sign-in issues can be recorded here with the game closed.',
    startRec: 'Start Recording',
    stopRec: 'Stop Recording',
    saveLogs: 'Save Logs…',
    recIdle: 'For in-game problems, click on Start Recording and reproduce the problem in-game.',
    recOn: 'Recording. Reproduce the problem, then click Save Logs.',
    logsSaved: 'Logs saved, attach to issue in the GitHub page.',
    // CrossOver's sign-in code window (src/signin-ui.c, src/copy-prompt-ui.inc)
    siTitle: 'Minecraft Dungeons II — Xbox Sign-In',
    siLead: 'Sign in using your browser or phone:',
    copyLink: 'Copy link',
    copyCode: 'Copy code',
    siHelp: 'Click the link or code to copy it. Leave this window open while signing in.\nIt closes automatically when the sign-in attempt finishes.',
    cancelSignIn: 'Cancel sign-in',
    linkCopied: 'Link copied',
    codeCopied: 'Code copied'
  };

  /* ---------- demo data and page-only wording ---------- */

  var BOTTLES = ['Steam', 'Games', 'Test'];        // what the CrossOver Bottle popup lists
  var STORES = ['Steam', S.launcherOpt];             // the Launcher: popup
  var TAG = 'BlockyRogue';                           // a made-up gamertag
  var CODE = 'DEMO-K7QX';                            // obviously not a real sign-in code
  var LINK = 'https://www.microsoft.com/link';
  var STEPS = ['Visual C++ checked', 'Microsoft’s Xbox runtime added beside the game',
    'Networking and sign-in fixes in place', 'Steam set to start the game directly', 'Steam restarted'];
  var GUIDE = ['Tick the license box', 'Click Set Up', 'Click Play', 'Enter the code'];
  var PAGE = {
    region: 'Interactive replica of the MCD2 Crossover app',
    browse: 'In the app, this opens a Finder window to pick the game folder.',
    quit: 'In the app, Cancel quits MCD2 Crossover.',
    license: ['In the app, the full text of Microsoft’s GDK license is shown here.',
      'Read it, click Done, then tick “I accept the Microsoft GDK license” to continue.'],
    skipped: 'Not needed for Launcher copies',
    stepsHead: 'What Set Up does',
    codeHead: 'Signing in',
    codeText: 'On your phone or another browser you’d enter this code on Microsoft’s site.',
    entered: 'I’ve entered the code',
    doneHead: 'Signed in',
    doneSteam: ['That’s it.', 'From now on, press Play in Steam.'],
    doneLauncher: ['That’s it.', 'From now on, press Play in this app.'],
    startOver: 'Start over',
    reopen: 'Reopen MCD2 Crossover',
    reopenGuide: 'Reopen the window',
    doneGuide: 'Done'
  };
  // How long the stand-ins take, in ms.
  var MS = { first: 160, step: 640, finish: 180, signin: 900, launch: 650, signedInLaunch: 1500,
    signOut: 1300, cancel: 450, diag: 380, note: 3600 };

  // Small inline icons (currentColor), no assets.
  var CHEV = '<svg class="mx-chev" viewBox="0 0 8 13" width="8" height="13" aria-hidden="true"><path d="M1.4 4.6 4 2l2.6 2.6M1.4 8.4 4 11l2.6-2.6" fill="none" stroke="currentColor" stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var MENU_TICK = '<svg class="mx-mtick" viewBox="0 0 18 12" width="18" height="12" aria-hidden="true"><path d="M5 6.3 7.6 9 12.6 3" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var TICK = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5.6 10.4 8.6 13.3 14.6 7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var GLYPH = {
    close: '<svg viewBox="0 0 8 8" aria-hidden="true"><path d="M1.6 1.6l4.8 4.8M6.4 1.6 1.6 6.4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>',
    min: '<svg viewBox="0 0 8 8" aria-hidden="true"><path d="M1.3 4h5.4" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>',
    zoom: '<svg viewBox="0 0 8 8" aria-hidden="true"><path d="M1.6 2.4v4h4zM6.4 5.6v-4h-4z" fill="currentColor"/></svg>'
  };
  var RESTART = '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M3.2 8a4.8 4.8 0 1 0 1.5-3.5M3 2.2v2.6h2.6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';

  // The app icon sits next to this script.
  var BASE = (document.currentScript && document.currentScript.src) || location.href;
  var ICON = new URL('icon-192.png', BASE).href;

  var root, ui = {}, st, opId = 0, timers = [], menu = null, cue = null, noteTimer = 0, uidN = 0;
  var mqReduce = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;

  function motion() {
    return document.documentElement.classList.contains('motion') && !(mqReduce && mqReduce.matches);
  }
  function uid(p) { return 'mx-' + p + '-' + (++uidN); }
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function text(t, cls) { return el('p', 'mx-text' + (cls ? ' ' + cls : ''), t); }
  function btn(t, cls, onClick) {
    var b = el('button', 'mx-btn' + (cls ? ' ' + cls : ''), t);
    b.type = 'button';
    if (onClick) b.addEventListener('click', onClick);
    return b;
  }
  function pageBtn(t, cls, onClick) {
    var b = el('button', 'mx-pbtn' + (cls ? ' ' + cls : ''), t);
    b.type = 'button';
    b.addEventListener('click', onClick);
    return b;
  }
  function row(kids, cls) {
    var r = el('div', 'mx-row' + (cls ? ' ' + cls : ''));
    kids.forEach(function (k) { r.appendChild(k); });
    return r;
  }
  function focusIn(node) { var a = document.activeElement; return !!(node && a && node.contains(a)); }
  function focus(node) { if (node && node.focus) node.focus({ preventScroll: true }); }
  // Layout position of node inside anc (offsets ignore the page's reveal transform).
  function offsetIn(node, anc) {
    var x = 0, y = 0;
    while (node && node !== anc) { x += node.offsetLeft; y += node.offsetTop; node = node.offsetParent; }
    return { x: x, y: y };
  }
  function gamePath() {
    return S.gameFolder + '~/Library/Application Support/CrossOver/Bottles/' + BOTTLES[st.bottle] +
      '/drive_c/Program Files (x86)/Steam/steamapps/common/Minecraft Dungeons II';
  }
  function accountText() { return st.account ? S.signedInTo + st.account : S.notSignedIn; }

  /* ---------- timers: every stand-in task goes through later() ---------- */

  // id: the operation the callback belongs to; it's dropped if that operation was
  // cancelled or replaced meanwhile (null = always run). reset() clears them all.
  function later(ms, id, fn) {
    var t = setTimeout(function () {
      timers.splice(timers.indexOf(t), 1);
      if (id == null || id === opId) fn();
    }, ms);
    timers.push(t);
  }
  function freeze() { timers.forEach(clearTimeout); timers = []; }

  function fresh() {
    return {
      screen: 'setup',      // 'setup' | 'home', as showSetup:YES / showSetup:NO
      open: true,           // false once Close Window has quit the app
      saved: null,          // what setup saved: { bottle, store } (indexes)
      bottle: 0, store: 0,  // the selection on the setup screen or in the Change Game Copy sheet
      licensed: false,      // the GDK checkbox
      account: '',          // gamertag once signed in
      op: null,             // 'setup' | 'launch' | 'sign-out' while the app is working
      cancelling: false,
      signin: false,        // CrossOver's code window is open
      done: false,          // signed in and the game launched: the finale
      sheet: null,          // 'license' | 'copy' | 'trouble'
      recording: false, logsSaved: false, diagBusy: false,
      check: [0, 0, 0, 0, 0], // setup checklist: 0 waiting, 1 working, 2 done, 3 not needed
      status: S.vcpp
    };
  }

  /* ---------- building blocks ---------- */

  // A macOS window: title bar with the traffic lights, then content.
  function makeWindow(cls, title) {
    var win = el('section', 'mx-win ' + cls);
    win.setAttribute('aria-label', title);
    win.tabIndex = -1;
    var bar = el('div', 'mx-bar');
    var lights = el('div', 'mx-lights');
    var close = el('button', 'mx-light mx-l-close');
    close.type = 'button';
    close.tabIndex = -1;
    close.setAttribute('aria-label', 'Close');
    close.innerHTML = GLYPH.close;
    var min = el('span', 'mx-light mx-l-min');
    var zoom = el('span', 'mx-light mx-l-zoom');
    min.innerHTML = GLYPH.min;
    zoom.innerHTML = GLYPH.zoom;
    min.setAttribute('aria-hidden', 'true');
    zoom.setAttribute('aria-hidden', 'true');
    lights.appendChild(close);
    lights.appendChild(min);
    lights.appendChild(zoom);
    bar.appendChild(lights);
    bar.appendChild(el('div', 'mx-title', title));
    win.appendChild(bar);
    return { win: win, bar: bar, close: close, min: min, zoom: zoom };
  }

  // NSPopUpButton: sized to its longest item, opens a menu with the current item ticked.
  function popup(items, index, ax, cls, onPick) {
    var b = btn('', 'mx-popup' + (cls ? ' ' + cls : ''));
    b.setAttribute('aria-haspopup', 'listbox');
    b.setAttribute('aria-expanded', 'false');
    var face = el('span', 'mx-popup-face');
    var p = { el: b, items: items, index: index, ax: ax.replace(/:$/, ''), spans: [], pick: onPick };
    items.forEach(function (t) { var s = el('span', '', t); face.appendChild(s); p.spans.push(s); });
    b.appendChild(face);
    b.insertAdjacentHTML('beforeend', CHEV);
    p.set = function (i) {
      p.index = i;
      p.spans.forEach(function (s, j) { s.className = j === i ? 'is-on' : ''; });
      b.setAttribute('aria-label', p.ax + ': ' + items[i]);
    };
    p.set(index);
    b.addEventListener('click', function () { if (menu && menu.p === p) closeMenu(true); else openMenu(p); });
    b.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); openMenu(p); }
    });
    return p;
  }

  function progressBar() {
    var p = el('div', 'mx-progress');
    p.setAttribute('role', 'progressbar');
    p.setAttribute('aria-label', 'Working');
    p.hidden = true;
    return p;
  }

  function heading(title, r) {
    var h = el('div', 'mx-head');
    var icon = el('img', 'mx-icon');
    icon.src = ICON;
    icon.alt = '';
    icon.width = 64;
    icon.height = 64;
    icon.draggable = false;
    r.trouble = btn(S.troubleshooting, 'mx-small', function () { openSheet('trouble', r.trouble); });
    h.appendChild(icon);
    h.appendChild(el('div', 'mx-h', title));
    h.appendChild(r.trouble);
    return h;
  }

  // The bottle and launcher popups, the game folder and Browse Game Copy…,
  // shared by the setup screen and the Change Game Copy sheet (addCopySelectionControlsToStack:).
  function copyControls(parent, r) {
    r.bottles = popup(BOTTLES, st.bottle, S.bottleAx, 'mx-pop-bottle', function (i) { st.bottle = i; gameChanged(r); });
    parent.appendChild(row([el('span', 'mx-label', S.bottleLabel), r.bottles.el], 'mx-row-16'));
    r.stores = popup(STORES, st.store, S.launcherLabel, '', function (i) { st.store = i; gameChanged(r); });
    parent.appendChild(row([el('span', 'mx-label', S.launcherLabel), r.stores.el]));
    r.game = text(gamePath(), 'mx-sel');
    parent.appendChild(r.game);
    r.browse = btn(S.browse, '', function () { note(r.browse, PAGE.browse); });
    parent.appendChild(row([r.browse]));
  }
  function gameChanged(r) {   // updateGame
    r.game.textContent = gamePath();
    if (r === ui.s && !st.op) setStatus(st.store ? S.experimental : S.vcpp);
    sync();
  }

  function actions(kids) {
    var a = el('div', 'mx-actions');
    kids.forEach(function (k) { a.appendChild(k); });
    return a;
  }

  /* ---------- the two screens (showSetup:) ---------- */

  function setupBody(r) {
    var body = el('div', 'mx-body');
    body.appendChild(heading(S.setUpTitle, r));
    body.appendChild(text(S.introSetup));
    r.account = text(accountText(), 'mx-medium');
    body.appendChild(r.account);
    copyControls(body, r);
    body.appendChild(text(S.quitFirst));
    r.view = btn(S.viewLicense, '', function () { openSheet('license', r.view); });
    body.appendChild(row([r.view]));
    var label = el('label', 'mx-check');
    r.boxWrap = el('span', 'mx-boxwrap');
    r.license = el('input', 'mx-checkbox');
    r.license.type = 'checkbox';
    r.license.checked = st.licensed;
    r.license.addEventListener('change', function () { st.licensed = r.license.checked; sync(); });
    r.boxWrap.appendChild(r.license);
    label.appendChild(r.boxWrap);
    label.appendChild(el('span', '', S.accept));
    body.appendChild(label);
    r.status = text(st.status, 'mx-status');
    r.progress = progressBar();
    body.appendChild(r.status);
    body.appendChild(r.progress);
    r.secondary = btn(S.cancel, 'mx-w100', setupCancel);
    r.primary = btn(S.setUp, 'mx-w100 mx-default', startSetup);
    body.appendChild(actions([r.secondary, r.primary]));
    r.def = r.primary;
    r.esc = r.secondary;
    return body;
  }

  function homeBody(r) {
    var launcher = st.saved && st.saved.store === 1;
    var body = el('div', 'mx-body mx-home');
    body.appendChild(heading('Minecraft Dungeons II', r));
    body.appendChild(text(launcher ? S.introLauncher : S.introHome));
    r.account = text(accountText(), 'mx-medium');
    body.appendChild(r.account);
    r.change = btn(S.changeCopy, '', function () { openSheet('copy', r.change); });
    body.appendChild(row([el('span', 'mx-label', S.bottleIs + BOTTLES[st.saved.bottle]), r.change], 'mx-wrap'));
    body.appendChild(text(S.renews));
    r.status = text(st.status, 'mx-status');
    r.progress = progressBar();
    body.appendChild(r.status);
    body.appendChild(r.progress);
    r.close = btn(S.closeWindow, 'mx-w116', closeWindow);
    r.secondary = btn(S.signOut, 'mx-w100', function () { if (st.op === 'launch') cancelLaunch(); else signOut(); });
    r.primary = btn(S.play, 'mx-w100 mx-default', play);
    body.appendChild(actions([r.close, r.secondary, r.primary]));
    r.def = r.primary;
    r.esc = r.close;
    return body;
  }

  function showScreen(kind, status) {
    var hadFocus = focusIn(ui.content);
    closeMenu();
    hideNote();
    st.screen = kind;
    st.status = status || (kind === 'setup' ? (st.store ? S.experimental : S.vcpp) : S.homeStatus);
    var r = {};
    var body = kind === 'setup' ? setupBody(r) : homeBody(r);
    ui.content.textContent = '';
    ui.content.appendChild(body);
    ui.s = r;
    sync();
    if (status) announce(status);
    if (hadFocus) focus(r.primary.disabled ? ui.main : r.primary);
  }

  function setStatus(t) {
    st.status = t;
    ui.s.status.textContent = t;
    announce(t);
  }

  /* ---------- what the buttons do (install:, play:, signOut:, cancel:, …) ---------- */

  function setupCancel() {           // in the app this quits; here the window just shakes its head
    if (st.op) return;
    if (motion()) {
      ui.main.classList.remove('is-wiggle');
      void ui.main.offsetWidth;
      ui.main.classList.add('is-wiggle');
    }
    note(ui.s.secondary, PAGE.quit);
  }

  function begin(op) {               // run:executable:arguments:
    st.op = op;
    st.cancelling = false;
    opId++;
    var t = op === 'setup' ? S.settingUp : op === 'launch' ? S.checking : S.removing;
    var sh = ui.sh && ui.sh.kind === 'copy' ? ui.sh : null;
    if (sh) {
      sh.status.textContent = t;
      sh.status.hidden = false;
      announce(t);
    } else setStatus(t);
    sync();
    return opId;
  }

  function startSetup() {
    if (st.op || !st.open) return;
    var fromSheet = !!(ui.sh && ui.sh.kind === 'copy');
    if (!fromSheet && (st.screen !== 'setup' || !st.licensed)) return;
    hideNote();
    st.done = false;
    glow(false);
    var steam = st.store === 0;
    st.check = [0, 0, 0, steam ? 0 : 3, steam ? 0 : 3];
    var id = begin('setup');
    var t = MS.first;
    st.check.forEach(function (v, i) {
      if (v === 3) return;
      later(t, id, function () { st.check[i] = 1; drawSteps(); });
      t += MS.step;
      later(t - 90, id, function () { st.check[i] = 2; drawSteps(); });
    });
    later(t + MS.finish, id, setupFinished);
  }
  function setupFinished() {
    st.op = null;
    st.check = st.check.map(function (v) { return v === 3 ? 3 : 2; });
    st.saved = { bottle: st.bottle, store: st.store };
    if (ui.sh && ui.sh.kind === 'copy') closeSheet();
    showScreen('home', S.setupDone);
  }

  function play() {
    if (st.op || st.screen !== 'home' || st.sheet || !st.open) return;
    st.done = false;
    glow(false);
    var id = begin('launch');
    if (st.account) later(MS.signedInLaunch, id, launched);
    else later(MS.signin, id, openSignin);
  }
  function launched() {
    st.op = null;
    ui.s.account.textContent = accountText();
    setStatus(st.saved.store ? S.launcherOpening : S.steamOpening);
    st.done = true;
    glow(true);
    sync();
  }

  function cancelLaunch() {
    if (st.op !== 'launch' || st.cancelling) return;
    st.cancelling = true;
    var id = ++opId;
    setStatus(S.cancelling);
    closeSignin();
    sync();
    later(MS.cancel, id, launchCancelled);
  }
  function launchCancelled() {
    st.op = null;
    st.cancelling = false;
    setStatus(S.cancelled);
    sync();
  }

  function signOut() {
    if (st.op || st.screen !== 'home') return;
    var id = begin('sign-out');
    later(MS.signOut, id, function () {
      st.op = null;
      st.account = '';
      st.done = false;
      glow(false);
      ui.s.account.textContent = accountText();
      setStatus(S.signedOut);
      sync();
    });
  }

  // closeWindow: → windowShouldClose: → the app quits (a launch in progress is cancelled first).
  function closeWindow() {
    if (!st.open || st.sheet || (st.op && st.op !== 'launch')) return;
    var hadFocus = focusIn(ui.main);
    if (st.op === 'launch') { opId++; st.op = null; st.cancelling = false; closeSignin(); }
    closeMenu();
    hideNote();
    st.open = false;
    var m = ui.main;
    m.classList.remove('is-opening', 'is-wiggle');
    if (motion()) {
      m.classList.add('is-closing');
      setTimeout(function () {
        m.classList.remove('is-closing');
        if (!st.open) m.classList.add('is-closed');
      }, 230);
    } else m.classList.add('is-closed');
    ui.reopen.hidden = false;
    sync();
    if (hadFocus) focus(ui.reopenBtn);
  }
  function reopen() {                // a fresh launch of the app
    if (st.open) return;
    st.open = true;
    ui.reopen.hidden = true;
    var m = ui.main;
    m.classList.remove('is-closed', 'is-closing');
    if (st.saved) {
      st.bottle = st.saved.bottle;
      st.store = st.saved.store;
      showScreen('home');
    } else {
      st.licensed = false;
      st.bottle = 0;
      st.store = 0;
      showScreen('setup');
    }
    if (motion()) {
      m.classList.add('is-opening');
      setTimeout(function () { m.classList.remove('is-opening'); }, 320);
    }
    focus(ui.s.primary.disabled ? m : ui.s.primary);
  }

  /* ---------- CrossOver's sign-in code window ---------- */

  function openSignin() {
    st.signin = true;
    ui.copyLink.textContent = S.copyLink;
    ui.copyCode.textContent = S.copyCode;
    var w = ui.wine;
    w.classList.remove('is-closing');
    w.hidden = false;
    if (motion()) {
      w.classList.remove('is-opening');
      void w.offsetWidth;
      w.classList.add('is-opening');
    }
    activate('wine');
    sync();
  }
  function closeSignin() {
    if (!st.signin) return;
    st.signin = false;
    var w = ui.wine;
    if (focusIn(w)) focus(ui.main);
    w.classList.remove('is-opening');
    if (motion()) {
      w.classList.add('is-closing');
      setTimeout(function () {
        w.classList.remove('is-closing');
        if (!st.signin) w.hidden = true;
      }, 180);
    } else w.hidden = true;
    activate('main');
  }
  function cancelSignin() {          // "Cancel sign-in" or the window's red button
    if (!st.signin) return;
    var id = ++opId;
    closeSignin();
    sync();
    later(MS.cancel, id, launchCancelled);
  }
  function codeEntered() {           // the page card: the sign-in finishes, the window closes itself
    if (!st.signin || st.op !== 'launch') return;
    var id = opId;
    closeSignin();
    sync();
    later(MS.launch, id, function () { st.account = TAG; launched(); });
  }
  // The topmost code window and the main window take turns being the key window.
  function activate(which) {
    var wineKey = which === 'wine' && st.signin;
    ui.main.classList.toggle('is-inactive', wineKey);
    ui.wine.classList.toggle('is-inactive', !wineKey);
  }

  /* ---------- sheets ---------- */

  function openSheet(kind, opener) {
    if (st.sheet || !st.open) return;
    if (kind === 'copy' && (st.op || st.screen !== 'home')) return;
    closeMenu();
    hideNote();
    var widths = { license: 620, copy: 650, trouble: 600 };
    var titles = { license: S.licenseTitle, copy: S.changeCopy, trouble: S.tsTitle };
    var node = el('div', 'mx-sheet mx-sheet-' + kind);
    node.tabIndex = -1;
    node.setAttribute('role', 'dialog');
    node.setAttribute('aria-label', titles[kind]);
    node.style.width = 'min(' + widths[kind] + 'px, calc(100% - 24px))';
    var r = { kind: kind, node: node, opener: opener };
    st.sheet = kind;

    if (kind === 'license') {      // viewLicense:
      var box = el('div', 'mx-license');
      box.tabIndex = 0;
      box.setAttribute('aria-label', S.licenseTitle);
      box.appendChild(el('p', 'mx-license-h', S.licenseTitle));
      PAGE.license.forEach(function (t) { box.appendChild(el('p', '', t)); });
      r.primary = btn(S.done, 'mx-w88 mx-default', function () { closeSheet(); });
      node.appendChild(box);
      node.appendChild(actions([r.primary]));
      r.def = r.primary;
    } else if (kind === 'copy') {  // showCopySheet
      st.bottle = st.saved.bottle;
      st.store = st.saved.store;
      node.appendChild(text(S.introSetup));
      copyControls(node, r);
      node.appendChild(text(S.quitFirst));
      r.status = text('', 'mx-status');
      r.status.hidden = true;
      r.progress = progressBar();
      node.appendChild(r.status);
      node.appendChild(r.progress);
      r.secondary = btn(S.cancel, 'mx-w88', function () { if (!st.op) closeSheet(); });
      r.primary = btn(S.done, 'mx-w88 mx-default', commitCopy);
      node.appendChild(actions([r.secondary, r.primary]));
      r.def = r.primary;
      r.esc = r.secondary;
    } else {                       // openTroubleshooting:
      st.logsSaved = false;
      node.appendChild(el('div', 'mx-sheet-title', S.tsTitle));
      r.recStatus = text('', 'mx-rec');
      node.appendChild(r.recStatus);
      node.appendChild(text(S.tsIntro));
      r.rec = btn(S.startRec, '', toggleRecording);
      r.save = btn(S.saveLogs, '', saveLogs);
      r.done = btn(S.done, '', function () { closeSheet(); });
      node.appendChild(row([r.rec, r.save, r.done], 'mx-wrap'));
      r.esc = r.done;
    }

    ui.sh = r;
    ui.content.inert = true;
    ui.bar.inert = true;
    if (motion()) node.classList.add('is-off');
    ui.sheets.appendChild(node);
    if (motion()) {
      void node.offsetWidth;
      node.classList.remove('is-off');
    }
    sync();
    focus(r.def || r.primary || r.rec);
  }

  function closeSheet() {
    var r = ui.sh;
    if (!r) return;
    var hadFocus = focusIn(r.node);
    ui.sh = null;
    st.sheet = null;
    ui.content.inert = false;
    ui.bar.inert = false;
    r.node.inert = true;
    if (motion()) {
      r.node.classList.add('is-off');
      setTimeout(function () {
        r.node.remove();
        if (!ui.sh) ui.main.style.minHeight = '';
      }, 260);
    } else {
      r.node.remove();
      ui.main.style.minHeight = '';
    }
    if (r.kind === 'copy' && st.saved) { st.bottle = st.saved.bottle; st.store = st.saved.store; }
    sync();
    if (hadFocus) focus(r.opener && r.opener.isConnected ? r.opener : ui.main);
  }

  // A sheet never hangs out of the window: the window grows to hold it, as AppKit does.
  function fitSheet() {
    var m = ui.main;
    if (!ui.sh) return;
    m.style.minHeight = '';
    var need = ui.sheets.offsetTop + ui.sh.node.offsetHeight + 14;
    if (m.offsetHeight < need) m.style.minHeight = need + 'px';
  }

  function commitCopy() {            // commitCopy: (the license was accepted at setup)
    if (st.op || !ui.sh) return;
    if (st.bottle === st.saved.bottle && st.store === st.saved.store) { closeSheet(); return; }
    startSetup();
  }

  function toggleRecording() {
    if (st.diagBusy) return;
    st.diagBusy = true;
    sync();
    later(MS.diag, null, function () {
      st.diagBusy = false;
      st.recording = !st.recording;
      st.logsSaved = false;
      sync();
      announce(st.recording ? S.recOn : S.recIdle);
    });
  }
  function saveLogs() {              // the save panel is skipped; recording stops when saved
    if (st.diagBusy) return;
    st.diagBusy = true;
    sync();
    later(MS.diag + 220, null, function () {
      st.diagBusy = false;
      st.recording = false;
      st.logsSaved = true;
      sync();
      announce(S.logsSaved);
    });
  }

  /* ---------- popup menus ---------- */

  function openMenu(p) {
    closeMenu();
    if (p.el.disabled) return;
    hideNote();
    var m = el('div', 'mx-menu');
    m.id = uid('menu');
    m.setAttribute('role', 'listbox');
    m.setAttribute('aria-label', p.ax);
    m.tabIndex = -1;
    var opts = p.items.map(function (t, i) {
      var o = el('div', 'mx-item');
      o.id = uid('opt');
      o.setAttribute('role', 'option');
      o.setAttribute('aria-selected', i === p.index ? 'true' : 'false');
      o.innerHTML = MENU_TICK;
      o.appendChild(el('span', '', t));
      o.addEventListener('pointermove', function () { hot(i); });
      o.addEventListener('click', function () { choose(i); });
      m.appendChild(o);
      return o;
    });
    m.addEventListener('pointerleave', function () { hot(-1); });
    m.addEventListener('keydown', menuKey);
    ui.desk.appendChild(m);
    menu = { p: p, node: m, opts: opts, hot: -1 };
    // Like an NSPopUpButton menu: the current item lands right over the button's text.
    var at = offsetIn(p.el, ui.desk), deskW = ui.desk.clientWidth;
    var w = Math.min(Math.max(m.offsetWidth, p.el.offsetWidth + 26), deskW);
    m.style.width = w + 'px';
    m.style.left = clamp(at.x - 18, 0, deskW - w) + 'px';
    m.style.top = Math.max(0, at.y + p.el.offsetHeight / 2 - (5 + p.index * 22 + 11)) + 'px';
    p.el.setAttribute('aria-expanded', 'true');
    p.el.setAttribute('aria-controls', m.id);
    hot(p.index);
    focus(m);
  }
  function hot(i) {
    if (!menu) return;
    menu.hot = i;
    menu.opts.forEach(function (o, j) { o.classList.toggle('is-hot', j === i); });
    if (i >= 0) menu.node.setAttribute('aria-activedescendant', menu.opts[i].id);
    else menu.node.removeAttribute('aria-activedescendant');
  }
  function menuKey(e) {
    var n = menu.opts.length, h = menu.hot;
    switch (e.key) {
      case 'ArrowDown': hot(h < 0 ? 0 : Math.min(n - 1, h + 1)); break;
      case 'ArrowUp': hot(h < 0 ? n - 1 : Math.max(0, h - 1)); break;
      case 'Home': hot(0); break;
      case 'End': hot(n - 1); break;
      case 'Enter': case ' ': if (h >= 0) choose(h); else closeMenu(true); break;
      case 'Escape': case 'Tab': closeMenu(true); break;
      default: return;
    }
    e.preventDefault();
    e.stopPropagation();
  }
  function choose(i) {
    var p = menu.p;
    closeMenu(true);
    if (i !== p.index) { p.set(i); p.pick(i); }
  }
  function closeMenu(refocus) {
    if (!menu) return;
    var p = menu.p;
    menu.node.remove();
    menu = null;
    p.el.setAttribute('aria-expanded', 'false');
    p.el.removeAttribute('aria-controls');
    if (refocus) focus(p.el);
  }

  /* ---------- page-level bits: note bubble, announcer, glow ---------- */

  function note(anchor, t) {
    var n = ui.note;
    n.firstChild.textContent = t;
    n.hidden = false;
    var at = offsetIn(anchor, ui.desk), deskW = ui.desk.clientWidth, w = n.offsetWidth;
    var mid = at.x + anchor.offsetWidth / 2;
    var left = clamp(mid - w / 2, 0, Math.max(0, deskW - w));
    n.style.left = left + 'px';
    n.style.top = (at.y + anchor.offsetHeight + 12) + 'px';
    n.style.setProperty('--mx-arrow', clamp(mid - left, 16, w - 16) + 'px');
    n.classList.remove('is-in');
    void n.offsetWidth;
    n.classList.add('is-in');
    announce(t);
    clearTimeout(noteTimer);
    noteTimer = setTimeout(hideNote, MS.note);
  }
  function hideNote() {
    clearTimeout(noteTimer);
    if (ui.note) ui.note.hidden = true;
  }

  function announce(t) {
    var a = ui.announce;
    if (!a) return;
    a.textContent = '';
    setTimeout(function () { a.textContent = t; }, 30);
  }

  function glow(on) {
    var m = ui.main;
    if (!on) { m.classList.remove('is-glow'); return; }
    m.classList.remove('is-glow');
    void m.offsetWidth;
    m.classList.add('is-glow');
  }

  /* ---------- keeping everything in step ---------- */

  // Enables and disables controls the way run:/finished:/licenseChanged: do, then
  // refreshes the checklist, the side card and the guide.
  function sync() {
    var s = ui.s, w = st.op, sh = ui.sh, copying = !!(sh && sh.kind === 'copy');
    var had = document.activeElement;
    if (st.screen === 'setup') {
      s.bottles.el.disabled = s.stores.el.disabled = s.browse.disabled = s.license.disabled = !!w;
      s.secondary.disabled = !!w;
      s.primary.disabled = !!w || !st.licensed;
      s.license.checked = st.licensed;
    } else {
      var launching = w === 'launch';
      s.change.disabled = s.primary.disabled = !!w;
      s.secondary.textContent = launching ? S.cancelLaunch : S.signOut;
      s.secondary.disabled = launching ? st.cancelling : !!w;
      s.close.disabled = !!w && !launching;
      s.esc = launching ? s.secondary : s.close;
    }
    s.progress.hidden = !w || copying;
    s.trouble.title = st.recording ? S.troubleTipRec : S.troubleTip;
    if (copying) {
      sh.bottles.el.disabled = sh.stores.el.disabled = sh.browse.disabled = !!w;
      sh.secondary.disabled = sh.primary.disabled = !!w;
      sh.progress.hidden = !w;
    } else if (sh && sh.kind === 'trouble') {
      var saved = st.logsSaved && !st.recording;
      sh.rec.textContent = st.recording ? S.stopRec : S.startRec;
      sh.rec.disabled = sh.save.disabled = st.diagBusy;
      sh.recStatus.textContent = saved ? S.logsSaved : st.recording ? S.recOn : S.recIdle;
      sh.recStatus.classList.toggle('mx-link', saved);
    }
    ui.mainClose.disabled = !!st.sheet;   // while working it stays live but does nothing, as in the app
    // Nothing to undo yet, or the finale card already offers Start over.
    ui.restart.classList.toggle('is-hidden', (st.screen === 'setup' && !st.saved && !st.op && !st.licensed && st.open) ||
      (st.done && !st.signin && st.open));
    fitSheet();
    drawSteps();
    drawCards();
    drawGuide();
    // A control that just got disabled drops focus to <body>; keep it in the window
    // (or sheet) instead, so Return and Escape keep working from the keyboard.
    if (had && had.disabled && root.contains(had)) {
      ui.lost = had;
      focus(sh && sh.node.contains(had) ? sh.node : ui.main);
    } else if (ui.lost && !ui.lost.disabled && ui.lost.isConnected &&
        (document.activeElement === ui.main || (sh && document.activeElement === sh.node))) {
      focus(ui.lost);
      ui.lost = null;
    }
  }

  function drawSteps() {
    ui.steps.forEach(function (li, i) {
      var v = st.check[i];
      li.className = 'mx-step' + (v === 1 ? ' is-busy' : v === 2 ? ' is-done' : v === 3 ? ' is-skip' : '');
      li.lastChild.hidden = v !== 3;
    });
  }

  function drawCards() {
    var on = st.signin ? 'code' : st.done ? 'done' : 'steps';
    Object.keys(ui.cards).forEach(function (k) {
      var c = ui.cards[k];
      c.classList.toggle('is-on', k === on);
      c.inert = k !== on;
    });
    var lines = st.saved && st.saved.store === 1 ? PAGE.doneLauncher : PAGE.doneSteam;
    ui.doneA.textContent = lines[0];
    ui.doneB.textContent = lines[1];
  }

  // What to do next, and which control the cyan ring sits on.
  function guideInfo() {
    if (st.signin) return { n: 3, text: GUIDE[3], target: ui.entered };
    if (st.done) return { n: 4, text: PAGE.doneGuide, target: null };
    if (st.screen === 'setup') {
      if (st.op || st.licensed) return { n: 1, text: GUIDE[1], target: st.op ? null : ui.s.primary };
      return { n: 0, text: GUIDE[0], target: ui.s.boxWrap };
    }
    return { n: 2, text: GUIDE[2], target: st.op ? null : ui.s.primary };
  }
  function drawGuide() {
    var g = guideInfo();
    if (!st.open) { g.text = PAGE.reopenGuide; g.target = ui.reopenBtn; }
    if (ui.guideText.textContent !== g.text) ui.guideText.textContent = g.text;
    ui.dots.forEach(function (d, i) { d.className = i < g.n ? 'is-done' : i === g.n ? 'is-now' : ''; });
    var t = g.target;
    if (t && (t.disabled || (st.sheet && ui.main.contains(t)))) t = null;
    if (cue !== t) {
      if (cue) cue.classList.remove('mx-cue');
      if (t) t.classList.add('mx-cue');
      cue = t;
    }
    ui.guide.classList.toggle('is-wait', !t && g.n < 4);
  }

  /* ---------- keyboard: Return = default button, Escape = cancel, like AppKit ---------- */

  function windowKey(e) {
    if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey || !st.open) return;
    var scope = ui.sh || ui.s, tag = e.target && e.target.tagName;
    var b = e.key === 'Enter' ? scope.def : e.key === 'Escape' ? scope.esc : null;
    if (!b || b.disabled) return;
    if (e.key === 'Enter' && (tag === 'BUTTON' || tag === 'A')) return;   // a focused button presses itself
    e.preventDefault();
    b.classList.add('is-pressed');
    setTimeout(function () { b.classList.remove('is-pressed'); }, 140);
    b.click();
  }

  /* ---------- build ---------- */

  function buildSide() {
    var side = el('aside', 'mx-side');
    side.setAttribute('aria-label', 'What the demo is doing');
    var cards = el('div', 'mx-cards');

    var steps = el('section', 'mx-card mx-card-steps');
    steps.appendChild(el('p', 'mx-eyebrow', PAGE.stepsHead));
    var list = el('ol', 'mx-steps');
    var lis = STEPS.map(function (t) {
      var li = el('li', 'mx-step');
      var tick = el('span', 'mx-tick');
      tick.innerHTML = TICK;
      var label = el('span', 'mx-step-text', t);
      li.appendChild(tick);
      li.appendChild(label);
      li.appendChild(el('span', 'mx-step-skip', PAGE.skipped));
      list.appendChild(li);
      return li;
    });
    steps.appendChild(list);

    var code = el('section', 'mx-card mx-card-code');
    code.appendChild(el('p', 'mx-eyebrow', PAGE.codeHead));
    code.appendChild(el('p', 'mx-card-text', PAGE.codeText));
    code.appendChild(el('p', 'mx-code', CODE));
    var entered = pageBtn(PAGE.entered, 'mx-pbtn-primary', codeEntered);
    code.appendChild(entered);

    var done = el('section', 'mx-card mx-card-done');
    var badge = el('span', 'mx-badge');
    badge.innerHTML = TICK;
    done.appendChild(badge);
    var line = el('p', 'mx-done-line');
    var a = el('span', 'mx-done-a'), b = el('span', 'mx-done-b');
    line.appendChild(a);
    line.appendChild(document.createTextNode(' '));
    line.appendChild(b);
    done.appendChild(line);
    var again = pageBtn(PAGE.startOver, 'mx-pbtn-ghost', function () { reset(); focus(ui.main); });
    again.insertAdjacentHTML('afterbegin', RESTART);
    done.appendChild(again);

    cards.appendChild(steps);
    cards.appendChild(code);
    cards.appendChild(done);
    side.appendChild(cards);
    return { side: side, steps: lis, cards: { steps: steps, code: code, done: done }, entered: entered, doneA: a, doneB: b };
  }

  function buildWine() {             // runPrompt(): a Win32 window in a macOS frame
    var w = makeWindow('mx-wine', S.siTitle);
    w.win.setAttribute('role', 'dialog');
    w.win.hidden = true;
    w.min.classList.add('is-off');
    w.zoom.classList.add('is-off');
    function w32(t, cls, fn) {
      var b = el('button', 'mx-w32-btn' + (cls ? ' ' + cls : ''), t);
      b.type = 'button';
      b.addEventListener('click', fn);
      return b;
    }
    var c = el('div', 'mx-w32');
    var grid = el('div', 'mx-w32-grid');
    // Like the real window, clicking the link or code itself copies silently;
    // only the small buttons change their own label.
    grid.appendChild(w32(LINK, 'mx-w32-big', function () {}));
    ui.copyLink = w32(S.copyLink, '', function () { ui.copyLink.textContent = S.linkCopied; announce(S.linkCopied); });
    grid.appendChild(ui.copyLink);
    grid.appendChild(w32(CODE, 'mx-w32-big', function () {}));
    ui.copyCode = w32(S.copyCode, '', function () { ui.copyCode.textContent = S.codeCopied; announce(S.codeCopied); });
    grid.appendChild(ui.copyCode);
    var foot = el('div', 'mx-w32-foot');
    foot.appendChild(w32(S.cancelSignIn, '', cancelSignin));
    c.appendChild(el('p', 'mx-w32-static', S.siLead));
    c.appendChild(grid);
    c.appendChild(el('p', 'mx-w32-static mx-w32-help', S.siHelp));
    c.appendChild(foot);
    w.win.appendChild(c);
    w.close.addEventListener('click', cancelSignin);
    w.win.addEventListener('pointerdown', function () { activate('wine'); });
    w.win.addEventListener('focusin', function () { activate('wine'); });
    return w.win;
  }

  function build() {
    root.setAttribute('role', 'region');
    root.setAttribute('aria-label', PAGE.region);

    // Guide
    var top = el('div', 'mx-top');
    ui.guide = el('div', 'mx-guide');
    ui.guide.setAttribute('role', 'status');
    var dots = el('span', 'mx-dots');
    dots.setAttribute('aria-hidden', 'true');
    ui.dots = GUIDE.map(function () { var d = el('i'); dots.appendChild(d); return d; });
    ui.guideText = el('span', 'mx-guide-text');
    ui.guide.appendChild(dots);
    ui.guide.appendChild(ui.guideText);
    ui.restart = pageBtn('', 'mx-restart', function () { reset(); focus(ui.main); });
    ui.restart.innerHTML = RESTART;
    ui.restart.appendChild(el('span', 'mx-restart-label', PAGE.startOver));   // icon only on phones
    top.appendChild(ui.guide);
    top.appendChild(ui.restart);

    // Live column: the desk (windows) and the side cards
    var live = el('div', 'mx-cols mx-live');
    ui.desk = el('div', 'mx-desk');
    var w = makeWindow('mx-main', 'MCD2 Crossover');
    ui.main = w.win;
    ui.bar = w.bar;
    ui.mainClose = w.close;
    ui.content = el('div', 'mx-content');
    ui.sheets = el('div', 'mx-sheets');
    ui.main.appendChild(ui.content);
    ui.main.appendChild(ui.sheets);
    w.close.addEventListener('click', closeWindow);
    ui.main.addEventListener('keydown', windowKey);
    ui.main.addEventListener('pointerdown', function () { activate('main'); });
    ui.main.addEventListener('focusin', function () { activate('main'); });
    ui.main.addEventListener('animationend', function (e) {
      if (e.animationName === 'mx-wiggle') ui.main.classList.remove('is-wiggle');
    });
    ui.wine = buildWine();
    ui.reopen = el('div', 'mx-reopen');
    ui.reopen.hidden = true;
    ui.reopenBtn = pageBtn(PAGE.reopen, 'mx-pbtn-ghost', reopen);
    var mini = el('img', 'mx-reopen-icon');
    mini.src = ICON;
    mini.alt = '';
    ui.reopenBtn.insertBefore(mini, ui.reopenBtn.firstChild);
    ui.reopen.appendChild(ui.reopenBtn);
    ui.note = el('div', 'mx-note');
    ui.note.appendChild(el('span'));
    ui.note.hidden = true;
    ui.desk.appendChild(ui.main);
    ui.desk.appendChild(ui.wine);
    ui.desk.appendChild(ui.reopen);
    ui.desk.appendChild(ui.note);
    var side = buildSide();
    ui.steps = side.steps;
    ui.cards = side.cards;
    ui.entered = side.entered;
    ui.doneA = side.doneA;
    ui.doneB = side.doneB;
    live.appendChild(ui.desk);
    live.appendChild(side.side);

    // Ghost: an invisible copy of the tallest state (setup screen, working, long status,
    // tallest card) in the same grid cell, so stepping through never moves the page.
    var ghost = el('div', 'mx-cols mx-ghost');
    ghost.setAttribute('aria-hidden', 'true');
    ghost.inert = true;
    var gw = makeWindow('mx-main', 'MCD2 Crossover'), gr = {};
    var gbody = setupBody(gr);
    gr.status.textContent = S.experimental;
    gr.progress.hidden = false;
    gw.win.appendChild(el('div', 'mx-content')).appendChild(gbody);
    var gdesk = el('div', 'mx-desk');
    gdesk.appendChild(gw.win);
    ghost.appendChild(gdesk);
    ghost.appendChild(buildSide().side);

    var stage = el('div', 'mx-stage');
    stage.appendChild(ghost);
    stage.appendChild(live);

    ui.announce = el('div', 'mx-sr');
    ui.announce.setAttribute('aria-live', 'polite');

    root.appendChild(top);
    root.appendChild(stage);
    root.appendChild(ui.announce);

    document.addEventListener('pointerdown', function (e) {
      if (menu && !menu.node.contains(e.target) && !menu.p.el.contains(e.target)) closeMenu(false);
      if (!ui.note.hidden && !ui.note.contains(e.target)) hideNote();
    }, true);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !ui.note.hidden) hideNote(); });
    var lastW = window.innerWidth;        // only a width change moves things (not a phone's URL bar)
    window.addEventListener('resize', function () {
      if (window.innerWidth === lastW || window.innerWidth < 120) return;   // < 120: a headless capture blip
      lastW = window.innerWidth;
      closeMenu(false);
      hideNote();
      fitSheet();
    });
  }

  /* ---------- reset, state, test states ---------- */

  function reset() {
    freeze();
    opId++;
    closeMenu();
    hideNote();
    if (ui.sh) { ui.sh.node.remove(); ui.sh = null; }
    ui.main.style.minHeight = '';
    st = fresh();
    ui.content.inert = false;
    ui.bar.inert = false;
    ui.main.classList.remove('is-closed', 'is-closing', 'is-opening', 'is-inactive', 'is-glow', 'is-wiggle');
    ui.wine.hidden = true;
    ui.wine.classList.remove('is-opening', 'is-closing', 'is-inactive');
    ui.reopen.hidden = true;
    showScreen('setup');
  }

  function state() {
    return {
      screen: st.screen, open: st.open, op: st.op, licensed: st.licensed,
      bottle: BOTTLES[st.bottle], store: st.store ? 'launcher' : 'steam',
      saved: st.saved ? { bottle: BOTTLES[st.saved.bottle], store: st.saved.store ? 'launcher' : 'steam' } : null,
      account: st.account, signin: st.signin, done: st.done, sheet: st.sheet,
      recording: st.recording, logsSaved: st.logsSaved, check: st.check.slice(),
      status: ui.sh && ui.sh.kind === 'copy' && !ui.sh.status.hidden ? ui.sh.status.textContent : st.status,
      guide: ui.guideText.textContent
    };
  }

  // Jump straight to a state (for screenshots and tests). Timers are frozen so it holds still.
  function go(name) {
    function setUp() { st.licensed = true; startSetup(); freeze(); setupFinished(); }
    function signin() { setUp(); play(); freeze(); openSignin(); }
    reset();
    switch (name) {
      case 'ticked': st.licensed = true; sync(); break;
      case 'launcher': st.licensed = true; ui.s.stores.set(1); st.store = 1; gameChanged(ui.s); break;
      case 'settingup': st.licensed = true; startSetup(); freeze(); st.check = [2, 2, 1, 0, 0]; sync(); break;
      case 'menu': openMenu(ui.s.bottles); break;
      case 'license': openSheet('license', ui.s.view); break;
      case 'browse': note(ui.s.browse, PAGE.browse); break;
      case 'home': setUp(); break;
      case 'checking': setUp(); play(); freeze(); break;
      case 'signin': signin(); break;
      case 'copied': signin(); ui.copyCode.click(); break;
      case 'done': signin(); codeEntered(); freeze(); st.account = TAG; launched(); break;
      case 'copy': setUp(); openSheet('copy', ui.s.change); break;
      case 'copy-running': setUp(); openSheet('copy', ui.s.change); ui.sh.bottles.set(1); st.bottle = 1; gameChanged(ui.sh); commitCopy(); freeze(); st.check = [2, 1, 0, 0, 0]; sync(); break;
      case 'trouble': setUp(); openSheet('trouble', ui.s.trouble); break;
      case 'recording': setUp(); openSheet('trouble', ui.s.trouble); st.recording = true; sync(); break;
      case 'logs': setUp(); openSheet('trouble', ui.s.trouble); st.logsSaved = true; sync(); break;
      case 'signout': setUp(); st.account = TAG; ui.s.account.textContent = accountText(); signOut(); freeze(); break;
      case 'closed': setUp(); closeWindow(); break;
      case 'closed-setup': closeWindow(); break;
      default: break;   // 'setup'
    }
  }

  function fromHash() {
    var h = location.hash.slice(1);
    if (/^mx-/.test(h)) go(h.slice(3));
  }

  function boot() {
    root = document.getElementById('app-demo');
    if (!root || root.getAttribute('data-mx')) return;
    root.setAttribute('data-mx', '1');
    st = fresh();
    build();
    showScreen('setup');
    window.__mcdDemo = { reset: reset, state: state, go: go };
    fromHash();
    window.addEventListener('hashchange', fromHash);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
