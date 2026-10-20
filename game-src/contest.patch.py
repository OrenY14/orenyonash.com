"""Adds the class contest to the game: player identity, score submission, result screen, leaderboard.
Run once against src/main.ts and src/style.css:  python -I contest.patch.py .
"""
import sys, os
os.chdir(sys.argv[1])
p = 'src/main.ts'
s = open(p, encoding='utf-8').read()

def rep(a, b):
    global s
    assert s.count(a) == 1, ('NOT UNIQUE/MISSING', s.count(a), a[:100])
    s = s.replace(a, b)

# ---------- contest module, inserted right after the kid picker code ----------
anchor = 'function pickerOpen() { return pickerElement.style.display !== "none"; }\n'
contest = r'''function pickerOpen() {
  return [pickerElement, whoElement, resultElement, boardElement].some((el) => el && el.style.display !== "none");
}

// ---- Class contest (ג1 vs ג2): who is playing, score saving, results, leaderboard ----
const API = "__API_URL__";
const DEFAULT_ROSTER: { name: string; cls: string }[] = [
  ...["עידו", "גילי", "נועה", "איתי", "מאיה", "יונתן", "תמר", "אורי", "שירה", "דניאל", "עמית", "ליה"].map((n) => ({ name: n, cls: "ג1" })),
  ...["רני", "עוז", "יואב", "אביגיל", "אלון", "הילה", "נדב", "ניצן", "איתמר", "טליה", "ארבל", "עומר"].map((n) => ({ name: n, cls: "ג2" })),
];
const CLASSES = ["ג1", "ג2"];
type Player = { name: string; cls: string };
type BoardPlayer = { name: string; cls: string; best: number; total: number; games: number };
type Board = {
  ok: boolean; deadline: string; closed: boolean; classMetric: "best" | "total";
  players: BoardPlayer[]; roster: Player[];
  classes: { [cls: string]: { sumBest: number; sumTotal: number; players: number; record: { name: string; best: number } | null } };
};

function lsGet(k: string) { try { return localStorage.getItem(k); } catch (e) { return null; } }
function lsSet(k: string, v: string) { try { localStorage.setItem(k, v); } catch (e) { /* ignore */ } }
function esc(t: string) { return String(t).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!)); }

let player: Player | null = null;
try { player = JSON.parse(lsGet("gp-player") || "null"); } catch (e) { player = null; }
let deviceId = lsGet("gp-device");
if (!deviceId) { deviceId = Math.random().toString(36).slice(2) + Date.now().toString(36); lsSet("gp-device", deviceId); }
let board: Board | null = null;
let gameStartedAt = Date.now();
let lastResult: { score: number; prevBest: number; saving: boolean; error: string } | null = null;

function rosterList(): Player[] { return board && board.roster && board.roster.length ? board.roster : DEFAULT_ROSTER; }
function me(): BoardPlayer | null {
  if (!board || !player) return null;
  return board.players.find((p) => p.name === player!.name && p.cls === player!.cls) || null;
}
function classValue(cls: string) {
  const c = board && board.classes[cls];
  if (!c) return 0;
  return board!.classMetric === "total" ? c.sumTotal : c.sumBest;
}

async function fetchBoard() {
  if (API.indexOf("__") === 0) return;
  try {
    const r = await fetch(`${API}?t=${Date.now()}`);
    const b = await r.json();
    if (b && b.ok) { board = b; onBoardUpdate(); }
  } catch (e) { /* offline: keep the last board */ }
}

function queue(): any[] { try { return JSON.parse(lsGet("gp-queue") || "[]"); } catch (e) { return []; } }
function setQueue(q: any[]) { lsSet("gp-queue", JSON.stringify(q)); }
async function flushQueue() {
  if (API.indexOf("__") === 0) return "";
  let q = queue(), error = "";
  while (q.length) {
    try {
      const r = await fetch(API, { method: "POST", body: JSON.stringify(q[0]) });
      const res = await r.json();
      if (res.board) { board = res.board; }
      if (!res.ok) error = res.error || "error";
      q.shift();  // saved, or rejected for good (closed / unknown / implausible): don't retry
      setQueue(q);
    } catch (e) {
      return "offline";
    }
  }
  onBoardUpdate();
  return error;
}

function onGameOver(score: number) {
  const secs = (Date.now() - gameStartedAt) / 1000;
  const prev = me();
  lastResult = { score, prevBest: prev ? prev.best : 0, saving: !!player && score > 0, error: "" };
  showResult();
  if (!player || score <= 0) return;
  const q = queue();
  q.push({ name: player.name, cls: player.cls, score, secs, device: deviceId, gameId: Math.random().toString(36).slice(2) + Date.now().toString(36) });
  setQueue(q);
  flushQueue().then((err) => {
    if (lastResult) { lastResult.saving = false; lastResult.error = err; }
    renderResult();
  });
}

// ---------- shared overlay helpers ----------
function overlay(cls: string) {
  const el = document.createElement("div");
  el.className = `gp-overlay ${cls}`;
  el.style.display = "none";
  document.body.appendChild(el);
  return el;
}
function show(el: HTMLElement) { el.style.display = "flex"; switchKidElement.style.display = "none"; boardBtnElement.style.display = "none"; }
function hide(el: HTMLElement) {
  el.style.display = "none";
  if (!pickerOpen() && !gameState.gameStarted && selectedKid) { switchKidElement.style.display = "block"; boardBtnElement.style.display = "block"; }
}
function battleHtml() {
  const a = classValue("ג1"), b = classValue("ג2"), sum = a + b;
  const pa = sum ? Math.round((a / sum) * 100) : 50;
  const label = board && board.classMetric === "total" ? "ניקוד מצטבר של הכיתה" : "סכום השיאים של הכיתה";
  return `<div class="battle"><div class="battle-head"><span>ג1 <b>${a}</b></span><span class="vs">נגד</span><span><b>${b}</b> ג2</span></div>
    <div class="battle-bar"><i style="width:${pa}%"></i></div><small>${label}</small></div>`;
}

// ---------- who is playing ----------
const whoElement = overlay("who-picker");
let whoClass = player ? player.cls : "ג1";
function renderWho() {
  const names = rosterList().filter((p) => p.cls === whoClass);
  whoElement.innerHTML = `<h1>מי <em>משחק?</em></h1>
    <p>בחרו כיתה ושם, וכל קפיצה שלכם תיכנס לתחרות של הכיתה</p>
    <div class="tabs">${CLASSES.map((c) => `<button type="button" data-cls="${c}" class="${c === whoClass ? "on" : ""}">${c}</button>`).join("")}</div>
    <div class="names">${names.map((p) => `<button type="button" data-name="${esc(p.name)}">${esc(p.name)}</button>`).join("")}</div>
    <button type="button" class="link guest">לשחק בלי להשתתף בתחרות</button>`;
}
whoElement.addEventListener("click", (e) => {
  const t = (e.target as HTMLElement).closest("button") as HTMLButtonElement | null;
  if (!t) return;
  if (t.dataset.cls) { whoClass = t.dataset.cls; renderWho(); return; }
  if (t.dataset.name) {
    player = { name: t.dataset.name, cls: whoClass };
    lsSet("gp-player", JSON.stringify(player));
  } else if (t.classList.contains("guest")) {
    player = null;
    lsSet("gp-player", "null");
  } else return;
  hide(whoElement);
  renderHello();
  gameState.highScore = loadHighScore();
  highScoreElement.textContent = `שיא ${gameState.highScore}`;
  if (!selectedKid) pickerElement.style.display = "flex";
});

// greeting line inside the jumper picker
const helloElement = document.createElement("div");
helloElement.className = "hello";
pickerElement.insertBefore(helloElement, pickerElement.firstChild);
function renderHello() {
  helloElement.innerHTML = player
    ? `שלום <b>${esc(player.name)}</b> · ${esc(player.cls)} <button type="button" class="link">לא ${esc(player.name)}?</button>`
    : `משחקים כאורחים <button type="button" class="link">להצטרף לתחרות</button>`;
}
helloElement.addEventListener("click", (e) => {
  if (!(e.target as HTMLElement).closest("button")) return;
  renderWho();
  show(whoElement);
});

// ---------- result after each game ----------
const resultElement = overlay("result-panel");
function showResult() { renderResult(); show(resultElement); }
function renderResult() {
  if (!lastResult) return;
  const r = lastResult, m = me();
  const best = Math.max(m ? m.best : 0, r.score), total = m ? m.total : r.score;
  const newBest = !!player && r.score > r.prevBest && r.score > 0;
  let rank = 0;
  if (board && player) {
    const mates = board.players.filter((p) => p.cls === player!.cls).sort((a, b) => b.best - a.best);
    rank = mates.findIndex((p) => p.name === player!.name) + 1;
  }
  const rec = player && board && board.classes[player.cls] ? board.classes[player.cls].record : null;
  let nudge = "";
  if (board && board.closed) nudge = "התחרות הסתיימה. נתראה במסיבה! 🎉";
  else if (!player) nudge = "רוצים שהקפיצות ייכנסו לתחרות של הכיתה? בחרו שם 👇";
  else if (rec && rec.name === player.name) nudge = `👑 השיא של ${esc(player.cls)} בידיים שלך! תשמרו עליו עד יום המסיבה`;
  else if (rec) nudge = `עוד <b>${rec.best - best + 1}</b> נקודות ושוברים את השיא של ${esc(player.cls)} (${esc(rec.name)}: ${rec.best})`;
  else nudge = `עוד אין שיא ב-${esc(player.cls)}. זה הזמן לקבוע אחד!`;
  const why = player && board && !board.closed
    ? (board.classMetric === "total" ? `כל משחק מוסיף ל${esc(player.cls)} נקודות` : `כל שיא אישי מוסיף ל${esc(player.cls)} נקודות`)
    : "";
  const status = r.saving ? "שומרים את הניקוד…" : r.error === "offline" ? "אין חיבור. הניקוד יישמר בפעם הבאה." : r.error && r.error !== "closed" ? "הניקוד לא נשמר." : "";
  resultElement.innerHTML = `<h1>קפצת <em>${r.score}</em>!</h1>
    ${newBest ? `<span class="badge">שיא אישי חדש! 🎉</span>` : ""}
    ${player ? `<div class="stats">
      <div><b>${best}</b><span>השיא שלך</span></div>
      <div><b>${total}</b><span>מצטבר${r.score > 0 ? ` (+${r.score})` : ""}</span></div>
      <div><b>${rank ? "#" + rank : "-"}</b><span>מקום ב${esc(player.cls)}</span></div>
    </div>` : ""}
    <p class="nudge">${nudge}</p>
    ${why ? `<p class="why">${why}</p>` : ""}
    ${board ? battleHtml() : ""}
    ${status ? `<p class="status">${status}</p>` : ""}
    <div class="row">
      <button type="button" class="primary again">עוד משחק!</button>
      ${player ? `<button type="button" class="ghost show-board">🏆 טבלה</button>` : `<button type="button" class="ghost join">להצטרף לתחרות</button>`}
      <button type="button" class="ghost switch">החלפת קופץ</button>
    </div>`;
}
resultElement.addEventListener("click", (e) => {
  const t = (e.target as HTMLElement).closest("button");
  if (!t) return;
  if (t.classList.contains("again")) { hide(resultElement); startGame(); }
  else if (t.classList.contains("show-board")) { hide(resultElement); openBoard(); }
  else if (t.classList.contains("join")) { hide(resultElement); renderWho(); show(whoElement); }
  else if (t.classList.contains("switch")) { hide(resultElement); pickerElement.style.display = "flex"; switchKidElement.style.display = "none"; boardBtnElement.style.display = "none"; }
});

// ---------- leaderboard ----------
const boardElement = overlay("board-panel");
let boardTab: "best" | "total" = "best";
let boardClass = player ? player.cls : "ג1";
function openBoard() { renderBoard(); show(boardElement); fetchBoard(); }
function renderBoard() {
  const left = board ? new Date(board.deadline).getTime() - Date.now() : 0;
  const days = Math.max(0, Math.floor(left / 86400000)), hours = Math.max(0, Math.floor((left % 86400000) / 3600000));
  const rows = board ? board.players.filter((p) => p.cls === boardClass).sort((a, b) => b[boardTab] - a[boardTab]).slice(0, 10) : [];
  boardElement.innerHTML = `<h1>🏆 טבלת <em>השיאים</em></h1>
    <p class="sub">${!board ? "טוענים…" : board.closed ? "התחרות הסתיימה" : `התחרות נגמרת כשהמסיבה מתחילה: עוד ${days} ימים ו-${hours} שעות`}</p>
    ${board ? battleHtml() : ""}
    <div class="tabs">${CLASSES.map((c) => `<button type="button" data-cls="${c}" class="${c === boardClass ? "on" : ""}">${c}</button>`).join("")}</div>
    <div class="tabs small">
      <button type="button" data-tab="best" class="${boardTab === "best" ? "on" : ""}">שיא במשחק אחד</button>
      <button type="button" data-tab="total" class="${boardTab === "total" ? "on" : ""}">ניקוד מצטבר</button>
    </div>
    <ol class="ranks">${rows.length ? rows.map((p, i) => `<li class="${player && p.name === player.name && p.cls === player.cls ? "me" : ""}"><span class="n">${i + 1}</span><span class="nm">${esc(p.name)}</span><b>${p[boardTab]}</b></li>`).join("") : `<li class="empty">עוד אף אחד מ${esc(boardClass)} לא שיחק. תהיו הראשונים!</li>`}</ol>
    <p class="privacy">בטבלה מוצגים שם פרטי וכיתה בלבד</p>
    <div class="row"><button type="button" class="primary close">לשחק!</button></div>`;
}
boardElement.addEventListener("click", (e) => {
  const t = (e.target as HTMLElement).closest("button") as HTMLButtonElement | null;
  if (!t) return;
  if (t.dataset.cls) { boardClass = t.dataset.cls; renderBoard(); }
  else if (t.dataset.tab) { boardTab = t.dataset.tab as "best" | "total"; renderBoard(); }
  else if (t.classList.contains("close")) {
    hide(boardElement);
    if (!selectedKid) pickerElement.style.display = "flex";
  }
});

const boardBtnElement = document.createElement("button");
boardBtnElement.type = "button";
boardBtnElement.className = "board-btn";
boardBtnElement.textContent = "🏆 טבלת השיאים";
boardBtnElement.style.display = "none";
boardBtnElement.addEventListener("click", () => { if (!gameState.gameStarted) openBoard(); });
document.body.appendChild(boardBtnElement);

const pickerBoardBtn = document.createElement("button");
pickerBoardBtn.type = "button";
pickerBoardBtn.className = "link picker-board";
pickerBoardBtn.textContent = "🏆 טבלת השיאים";
pickerBoardBtn.addEventListener("click", () => { pickerElement.style.display = "none"; openBoard(); });
pickerElement.insertBefore(pickerBoardBtn, pickerElement.querySelector(".back"));

function onBoardUpdate() {
  const m = me();
  if (m && m.best > gameState.highScore) { gameState.highScore = m.best; highScoreElement.textContent = `שיא ${gameState.highScore}`; }
  if (resultElement.style.display !== "none") renderResult();
  if (boardElement.style.display !== "none") renderBoard();
  if (whoElement.style.display !== "none") renderWho();
}

// first screen: who is playing (once per device), then pick a jumper
renderHello();
if (lsGet("gp-player") === null) { pickerElement.style.display = "none"; renderWho(); show(whoElement); }
if (location.hash === "#board") { pickerElement.style.display = "none"; openBoard(); }
fetchBoard().then(() => flushQueue());
setInterval(() => { if (!gameState.gameStarted) fetchBoard(); }, 60000);
'''
rep(anchor, contest)

# selectKid also shows the leaderboard button
rep('  pickerElement.style.display = "none";\n  switchKidElement.style.display = "block";\n}',
    '  pickerElement.style.display = "none";\n  switchKidElement.style.display = "block";\n  boardBtnElement.style.display = "block";\n}')
# switch-kid button hides the leaderboard button too
rep('  pickerElement.style.display = "flex";\n  switchKidElement.style.display = "none";\n});',
    '  pickerElement.style.display = "flex";\n  switchKidElement.style.display = "none";\n  boardBtnElement.style.display = "none";\n});')

# start: no game while an overlay is open; remember when the game began
rep('function startGame() {\n  if (gameState.gameStarted || !selectedKid) return;',
    'function startGame() {\n  if (gameState.gameStarted || !selectedKid || pickerOpen()) return;\n  gameStartedAt = Date.now();')
rep('  switchKidElement.style.display = "none";\n  gameState.introAnimation.active = true;',
    '  switchKidElement.style.display = "none";\n  boardBtnElement.style.display = "none";\n  gameState.introAnimation.active = true;')

# game over: report the score before the game resets it
rep('    gameState.score = 0;\n    gameState.world.offset = 0;',
    '    onGameOver(gameState.score);\n    gameState.score = 0;\n    gameState.world.offset = 0;')
rep('    gameState.gameStarted = false;\n    switchKidElement.style.display = "block";',
    '    gameState.gameStarted = false;')

# taps on any overlay button or link must not reach the game's touch handlers
s = s.replace('.closest?.(".switch-kid, a")', '.closest?.("button, a")')

# personal high score follows the player, not the jumper face
s = s.replace('`gravity-best-${selectedKid ? selectedKid.id : "none"}`', '`gravity-best-${player ? player.cls + "-" + player.name : "guest"}`')

open(p, 'w', encoding='utf-8').write(s)

c = 'src/style.css'
t = open(c, encoding='utf-8').read()
t += '''
/* Contest overlays share the picker look */
.gp-overlay {
  position: fixed; inset: 0; z-index: 3001;
  flex-direction: column; align-items: center; justify-content: center; gap: 14px;
  padding: calc(18px + env(safe-area-inset-top, 0px)) 16px calc(18px + env(safe-area-inset-bottom, 0px));
  text-align: center; direction: rtl; overflow-y: auto;
  background: radial-gradient(120% 60% at 50% 0%, rgba(42,13,99,.96), rgba(14,7,48,.98));
  color: #fff; font-family: "Rubik", Arial, sans-serif;
}
.gp-overlay h1 { margin: 0; font-size: clamp(1.8rem, 8vw, 2.5rem); font-weight: 900; line-height: 1.1; text-shadow: 0 0 18px rgba(46,232,255,.55); }
.gp-overlay h1 em { font-style: normal; color: #c8ff3a; }
.gp-overlay p { margin: 0; color: #cfc6ff; font-size: 1.05rem; line-height: 1.45; max-width: 34ch; }
.gp-overlay button { font-family: "Rubik", Arial, sans-serif; cursor: pointer; touch-action: manipulation; }
.gp-overlay .tabs { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; }
.gp-overlay .tabs button { min-height: 44px; padding: 8px 22px; border-radius: 99px; border: 2px solid rgba(255,255,255,.25); background: transparent; color: #fff; font-weight: 900; font-size: 1.15rem; }
.gp-overlay .tabs.small button { font-size: .95rem; padding: 6px 14px; min-height: 40px; }
.gp-overlay .tabs button.on { background: #c8ff3a; color: #0e0730; border-color: #c8ff3a; }
.gp-overlay .names { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; width: min(380px, 100%); }
.gp-overlay .names button { min-height: 52px; border-radius: 14px; border: 2px solid rgba(255,255,255,.2); background: rgba(255,255,255,.07); color: #fff; font-weight: 900; font-size: 1.1rem; }
.gp-overlay .names button:hover, .gp-overlay .names button:focus-visible { border-color: #c8ff3a; outline: none; }
.gp-overlay .link, .kid-picker .link { background: none; border: 0; color: #2ee8ff; font: 700 1rem "Rubik", Arial, sans-serif; text-decoration: underline; cursor: pointer; padding: 6px; }
.gp-overlay .row { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }
.gp-overlay .primary { min-height: 54px; padding: 12px 28px; border-radius: 18px; border: 0; background: #c8ff3a; color: #0e0730; font-weight: 900; font-size: 1.2rem; box-shadow: 0 0 22px rgba(200,255,58,.4); }
.gp-overlay .ghost { min-height: 48px; padding: 10px 18px; border-radius: 16px; border: 2px solid rgba(255,255,255,.3); background: transparent; color: #fff; font-weight: 900; font-size: 1rem; }
.gp-overlay .badge { background: #ff3fae; color: #fff; font-weight: 900; padding: 4px 14px; border-radius: 99px; transform: rotate(-3deg); }
.gp-overlay .stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; width: min(380px, 100%); }
.gp-overlay .stats div { display: flex; flex-direction: column; gap: 2px; padding: 10px 4px; border-radius: 14px; background: rgba(0,0,0,.28); }
.gp-overlay .stats b { font-size: 1.7rem; font-weight: 900; color: #2ee8ff; font-variant-numeric: tabular-nums; }
.gp-overlay .stats div:first-child b { color: #c8ff3a; }
.gp-overlay .stats span { font-size: .85rem; color: #cfc6ff; }
.gp-overlay .nudge { color: #fff; font-weight: 700; }
.gp-overlay .nudge b { color: #ff7a1a; }
.gp-overlay .why, .gp-overlay .status, .gp-overlay .privacy { font-size: .9rem; }
.gp-overlay .battle { width: min(380px, 100%); display: grid; gap: 6px; }
.gp-overlay .battle-head { display: flex; justify-content: space-between; align-items: baseline; font-weight: 900; font-size: 1.1rem; }
.gp-overlay .battle-head b { font-size: 1.4rem; font-variant-numeric: tabular-nums; }
.gp-overlay .battle-head span:first-child b { color: #ff3fae; }
.gp-overlay .battle-head span:last-child b { color: #2ee8ff; }
.gp-overlay .battle-head .vs { color: #cfc6ff; font-size: .9rem; }
.gp-overlay .battle-bar { height: 14px; border-radius: 99px; background: #2ee8ff; overflow: hidden; }
.gp-overlay .battle-bar i { display: block; height: 100%; background: #ff3fae; border-radius: 99px 0 0 99px; float: right; }
.gp-overlay .battle small { color: #cfc6ff; font-size: .8rem; }
.gp-overlay .ranks { list-style: none; margin: 0; padding: 0; width: min(380px, 100%); display: grid; gap: 6px; }
.gp-overlay .ranks li { display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-radius: 12px; background: rgba(255,255,255,.07); font-size: 1.05rem; }
.gp-overlay .ranks li .n { width: 1.6em; font-weight: 900; color: #cfc6ff; }
.gp-overlay .ranks li .nm { flex: 1; text-align: start; font-weight: 700; }
.gp-overlay .ranks li b { font-weight: 900; color: #c8ff3a; font-variant-numeric: tabular-nums; }
.gp-overlay .ranks li:first-child .n { color: #ffd84a; }
.gp-overlay .ranks li.me { outline: 2px solid #c8ff3a; }
.gp-overlay .ranks li.empty { justify-content: center; color: #cfc6ff; }
.kid-picker .hello { color: #fff; font-size: 1.05rem; }
.kid-picker .hello b { color: #c8ff3a; }
.board-btn {
  position: fixed; z-index: 1001; left: 50%; bottom: calc(10% + 58px + env(safe-area-inset-bottom, 0px)); transform: translateX(-50%);
  font: 900 1.05rem "Rubik", Arial, sans-serif; color: #fff; background: rgba(14,7,48,.75);
  border: 2px solid #c8ff3a; border-radius: 99px; padding: 10px 20px; cursor: pointer; touch-action: manipulation;
}
'''
open(c, 'w', encoding='utf-8').write(t)
print('contest patch applied')
