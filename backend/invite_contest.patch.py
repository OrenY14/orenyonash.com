"""Adds the contest card to the invite (site version = live, artifact version = static)."""
import sys
path, mode = sys.argv[1], sys.argv[2]          # mode: site | artifact
GAME = 'game/' if mode == 'site' else 'https://orenyonash.com/game/'
s = open(path, encoding='utf-8').read()

def rep(a, b):
    global s
    assert s.count(a) == 1, ('NOT UNIQUE/MISSING', s.count(a), a[:90])
    s = s.replace(a, b)

# 1. remove the standalone game button (the card replaces it)
start = s.index('  <a class="btn cyan" id="play-game"')
end = s.index('</a>', start) + len('</a>\n\n')
s = s[:start] + s[end:]

# 2. contest card right before the date/time ticket
live = '''    <div class="records" id="records">
      <div class="rec"><span class="cls">ג1</span><b class="who">…</b><span class="pts"></span></div>
      <div class="rec"><span class="cls">ג2</span><b class="who">…</b><span class="pts"></span></div>
    </div>
    <div class="battle" id="battle" hidden>
      <div class="battle-head"><span>ג1 <b id="b1">0</b></span><span class="vs">נגד</span><span><b id="b2">0</b> ג2</span></div>
      <div class="battle-bar"><i id="bbar" style="width:50%"></i></div>
    </div>
''' if mode == 'site' else ''
card = f'''  <section class="card contest" aria-labelledby="contest-h">
    <p class="label must">🏆 תחרות הקפיצות</p>
    <h2 id="contest-h">ג1 נגד ג2: מי קופץ הכי גבוה?</h2>
    <p>הורים, תנו לילדים לשחק במשחק הקפיצות! מי שיחזיק בשיא הקפיצה של הכיתה כשהמסיבה מתחילה, יקבל <b>הפתעה ביום ההולדת</b> 🎁</p>
    <p>כל משחק נספר בניקוד המצטבר, וכל שיא אישי מקרב את הכיתה לניצחון.</p>
{live}    <div class="btns">
      <a class="btn lime full" href="{GAME}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="7" width="20" height="11" rx="5"/><path d="M7 10.5v4M5 12.5h4"/><circle cx="16" cy="11.5" r="1" fill="currentColor"/><circle cx="18" cy="14" r="1" fill="currentColor"/></svg>
        לשחק עכשיו
      </a>
      <a class="btn ghost full" href="{GAME}#board">🏆 טבלת השיאים</a>
    </div>
    <p class="fine">התחרות נסגרת ביום המסיבה, 27.11 בשעה 13:30. בטבלה מוצגים שם פרטי וכיתה בלבד.</p>
  </section>

'''
rep('  <section class="card ticket" aria-label="מועד המסיבה">', card + '  <section class="card ticket" aria-label="מועד המסיבה">')

# 3. styles
rep('/* Place */', '''/* Contest */
.contest { border: 3px solid var(--pink); background: rgba(255,63,174,.08); box-shadow: 0 0 26px rgba(255,63,174,.2); }
.contest h2 { margin: 0; font-size: 1.5rem; font-weight: 900; line-height: 1.15; text-wrap: balance; }
.contest .must { color: var(--pink); }
.contest p { margin: 0; color: var(--ink-soft); }
.contest p b { color: var(--ink); }
.contest .fine { font-size: .85rem; }
.records { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.rec { display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 12px 6px; border-radius: 16px; background: rgba(0,0,0,.28); min-width: 0; }
.rec .cls { font-size: .85rem; font-weight: 700; color: var(--ink-soft); }
.rec .who { font-size: 1.3rem; font-weight: 900; color: var(--lime); overflow-wrap: anywhere; }
.rec .pts { font-size: .9rem; color: var(--ink-soft); }
.battle { display: grid; gap: 6px; }
.battle-head { display: flex; justify-content: space-between; align-items: baseline; font-weight: 900; }
.battle-head b { font-size: 1.35rem; font-variant-numeric: tabular-nums; }
.battle-head span:first-child b { color: var(--pink); }
.battle-head span:last-child b { color: var(--cyan); }
.battle-head .vs { color: var(--ink-soft); font-size: .85rem; }
.battle-bar { height: 14px; border-radius: 99px; background: var(--cyan); overflow: hidden; }
.battle-bar i { display: block; height: 100%; background: var(--pink); float: right; transition: width .6s ease; }

/* Place */''')

# 4. WhatsApp text mentions the contest and links to the invite
rep("+ '✅ אנא מלאו אישור קפיצה לפני שמגיעים:\\n' + WAIVER;",
    "+ '🏆 תחרות קפיצות ג1 נגד ג2: שיאן הכיתה מקבל הפתעה במסיבה!\\n'\n"
    "    + '🎮 https://orenyonash.com/game/\\n\\n'\n"
    "    + '✅ אנא מלאו אישור קפיצה לפני שמגיעים:\\n' + WAIVER + '\\n\\n'\n"
    "    + 'כל הפרטים: https://orenyonash.com/invite.html';")

# 5. live data (site only; the artifact sandbox blocks outside requests)
if mode == 'site':
    rep('  // QR (desktop only, shown by CSS)', '''  // Contest: live record holders and class totals
  var API = '__API_URL__';
  function loadContest() {
    if (API.indexOf('__') === 0) return;
    fetch(API + '?t=' + Date.now()).then(function (r) { return r.json(); }).then(function (b) {
      if (!b || !b.ok) return;
      var recs = document.querySelectorAll('#records .rec');
      ['ג1', 'ג2'].forEach(function (cls, i) {
        var c = b.classes[cls], rec = c && c.record;
        recs[i].querySelector('.who').textContent = rec ? rec.name : 'עוד אין שיא';
        recs[i].querySelector('.pts').textContent = rec ? 'שיא: ' + rec.best : 'היו הראשונים!';
      });
      var key = b.classMetric === 'total' ? 'sumTotal' : 'sumBest';
      var a = b.classes['ג1'] ? b.classes['ג1'][key] : 0, z = b.classes['ג2'] ? b.classes['ג2'][key] : 0;
      document.getElementById('b1').textContent = a;
      document.getElementById('b2').textContent = z;
      document.getElementById('bbar').style.width = (a + z ? Math.round(a / (a + z) * 100) : 50) + '%';
      document.getElementById('battle').hidden = false;
    }).catch(function () {});
  }
  loadContest();
  setInterval(loadContest, 60000);

  // QR (desktop only, shown by CSS)''')

open(path, 'w', encoding='utf-8').write(s)
print('ok', mode)
