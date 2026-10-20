/**
 * Gravity Park jump contest — score server.
 * Bound to the "Gravity Jump Contest" Google Sheet (orenyonash@gmail.com).
 * Deploy: Deploy > New deployment > Web app, Execute as: Me, Who has access: Anyone.
 *
 * Tabs (created by setup()):
 *   Roster  — name | class        (edit names here; the game reads this list)
 *   Games   — time | name | class | score | seconds | device | gameId
 *   Config  — key | value         (deadline, class_metric = best | total)
 */

var DEFAULT_ROSTER = {
  'ג1': ['עידו', 'גילי', 'נועה', 'איתי', 'מאיה', 'יונתן', 'תמר', 'אורי', 'שירה', 'דניאל', 'עמית', 'ליה'],
  'ג2': ['רני', 'עוז', 'יואב', 'אביגיל', 'אלון', 'הילה', 'נדב', 'ניצן', 'איתמר', 'טליה', 'ארבל', 'עומר']
};
var MAX_SCORE = 5000;
var MAX_POINTS_PER_SEC = 3;

function setup() {
  var ss = SpreadsheetApp.getActive();
  var roster = sheet_('Roster', ['name', 'class']);
  if (roster.getLastRow() < 2) {
    var rows = [];
    Object.keys(DEFAULT_ROSTER).forEach(function (cls) {
      DEFAULT_ROSTER[cls].forEach(function (n) { rows.push([n, cls]); });
    });
    roster.getRange(2, 1, rows.length, 2).setValues(rows);
  }
  sheet_('Games', ['time', 'name', 'class', 'score', 'seconds', 'device', 'gameId']);
  var cfg = sheet_('Config', ['key', 'value']);
  if (cfg.getLastRow() < 2) {
    cfg.getRange(2, 1, 2, 2).setValues([
      ['deadline', '2026-11-27T13:30:00+02:00'],
      ['class_metric', 'best']
    ]);
  }
  var first = ss.getSheetByName('Sheet1') || ss.getSheetByName('גיליון1');
  if (first && ss.getSheets().length > 1) ss.deleteSheet(first);
}

function sheet_(name, headers) {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName(name) || ss.insertSheet(name);
  if (sh.getLastRow() === 0) {
    sh.appendRow(headers);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, headers.length).setFontWeight('bold');
  }
  return sh;
}

function config_() {
  var out = { deadline: '2026-11-27T13:30:00+02:00', class_metric: 'best' };
  var sh = SpreadsheetApp.getActive().getSheetByName('Config');
  if (!sh || sh.getLastRow() < 2) return out;
  sh.getRange(2, 1, sh.getLastRow() - 1, 2).getValues().forEach(function (r) {
    if (r[0]) out[String(r[0]).trim()] = r[1] instanceof Date ? r[1].toISOString() : String(r[1]).trim();
  });
  return out;
}

function roster_() {
  var sh = SpreadsheetApp.getActive().getSheetByName('Roster');
  var list = [];
  if (!sh || sh.getLastRow() < 2) return list;
  sh.getRange(2, 1, sh.getLastRow() - 1, 2).getValues().forEach(function (r) {
    var n = String(r[0]).trim(), c = String(r[1]).trim();
    if (n && c) list.push({ name: n, cls: c });
  });
  return list;
}

function board_() {
  var cfg = config_();
  var roster = roster_();
  var players = {};
  roster.forEach(function (p) { players[p.cls + '|' + p.name] = { name: p.name, cls: p.cls, best: 0, total: 0, games: 0, bestAt: 0 }; });
  var sh = SpreadsheetApp.getActive().getSheetByName('Games');
  if (sh && sh.getLastRow() > 1) {
    sh.getRange(2, 1, sh.getLastRow() - 1, 4).getValues().forEach(function (r) {
      var p = players[String(r[2]) + '|' + String(r[1])];
      if (!p) return;
      var score = Number(r[3]) || 0, t = new Date(r[0]).getTime();
      p.total += score;
      p.games += 1;
      if (score > p.best) { p.best = score; p.bestAt = t; }
    });
  }
  var list = Object.keys(players).map(function (k) { return players[k]; });
  var classes = {};
  list.forEach(function (p) {
    var c = classes[p.cls] || (classes[p.cls] = { sumBest: 0, sumTotal: 0, players: 0, record: null });
    c.sumBest += p.best;
    c.sumTotal += p.total;
    if (p.games) c.players += 1;
    // record holder: highest single score, tie goes to whoever reached it first
    if (p.best > 0 && (!c.record || p.best > c.record.best || (p.best === c.record.best && p.bestAt < c.record.bestAt))) {
      c.record = { name: p.name, best: p.best, bestAt: p.bestAt };
    }
  });
  return {
    ok: true,
    deadline: cfg.deadline,
    closed: Date.now() >= new Date(cfg.deadline).getTime(),
    classMetric: cfg.class_metric === 'total' ? 'total' : 'best',
    players: list.filter(function (p) { return p.games > 0; }),
    roster: roster,
    classes: classes,
    updated: new Date().toISOString()
  };
}

function cachedBoard_() {
  var cache = CacheService.getScriptCache();
  var hit = cache.get('board');
  if (hit) return JSON.parse(hit);
  var b = board_();
  cache.put('board', JSON.stringify(b), 15);
  return b;
}

function doGet(e) {
  return json_(cachedBoard_());
}

function doPost(e) {
  var body;
  try { body = JSON.parse(e.postData.contents); } catch (err) { return json_({ ok: false, error: 'bad_json' }); }
  var name = String(body.name || '').trim(), cls = String(body.cls || '').trim();
  var score = Math.floor(Number(body.score)), secs = Number(body.secs);
  var device = String(body.device || '').slice(0, 40), gameId = String(body.gameId || '').slice(0, 40);

  var cfg = config_();
  if (Date.now() >= new Date(cfg.deadline).getTime()) return json_({ ok: false, error: 'closed', board: cachedBoard_() });
  var known = roster_().some(function (p) { return p.name === name && p.cls === cls; });
  if (!known) return json_({ ok: false, error: 'unknown_player' });
  if (!(score >= 0 && score <= MAX_SCORE)) return json_({ ok: false, error: 'bad_score' });
  if (!(secs > 0 && secs < 7200) || score > secs * MAX_POINTS_PER_SEC + 5) return json_({ ok: false, error: 'implausible' });

  var lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    var sh = SpreadsheetApp.getActive().getSheetByName('Games');
    // ignore a retry of a game that was already saved
    if (gameId && sh.getLastRow() > 1) {
      var from = Math.max(2, sh.getLastRow() - 499);
      var ids = sh.getRange(from, 7, sh.getLastRow() - from + 1, 1).getValues();
      for (var i = 0; i < ids.length; i++) if (String(ids[i][0]) === gameId) return json_({ ok: true, duplicate: true, board: board_() });
    }
    sh.appendRow([new Date(), name, cls, score, Math.round(secs), device, gameId]);
    CacheService.getScriptCache().remove('board');
  } finally {
    lock.releaseLock();
  }
  var b = board_();
  CacheService.getScriptCache().put('board', JSON.stringify(b), 15);
  return json_({ ok: true, board: b });
}

function json_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
