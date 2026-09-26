(function () {
  var M = window.LAW_MANIFEST; if (!M) return;
  var body = document.body;
  var prefix = body.getAttribute('data-prefix') || '';
  var curDept = body.getAttribute('data-dept') || '';
  var curSlug = body.getAttribute('data-slug') || '';
  var S = M.sections || [];
  var G = M.groups || [];
  var curSec = '';
  S.forEach(function (s) { if (location.pathname.indexOf('/' + s.code + '/') >= 0) curSec = s.code; });
  var curGroup = '';
  G.forEach(function (g) { if ((g.sections || []).indexOf(curSec) >= 0) curGroup = g.code; });
  function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;'); }
  function secOf(code){ for (var i=0;i<S.length;i++) if (S[i].code===code) return S[i]; return null; }
  function groupOf(code){ for (var i=0;i<G.length;i++) if (G[i].code===code) return G[i]; return null; }
  function isHist(d){ return d.indexOf('已废止') === 0; }
  var grp = groupOf(curGroup);
  var searchUrl = (grp && grp.search) ? grp.search : M.meta.search;

  // ---- 顶部导航 ----
  var nav = document.getElementById('topnav');
  if (nav) {
    var h = '';
    if (grp) h += '<a href="' + prefix + grp.home + '">' + esc(grp.name) + '</a>';
    var s = secOf(curSec);
    if (s) h += '<a href="' + prefix + s.home + '">首页</a>';
    if (curDept && !isHist(curDept)) {
      M.departments.forEach(function (d) {
        if (d.sec === curSec && d.name === curDept) h += '<a href="' + prefix + d.list + '">本领域列表</a>';
      });
    }
    h += '<a href="' + prefix + searchUrl + '">搜索</a>';
    nav.innerHTML = h;
  }

  // ---- 侧边栏：群切换 + 板块分段 ----
  var sb = document.getElementById('sidebar');
  if (sb) {
    var h = '';
    if (grp) h += '<div class="sb-up"><a href="' + prefix + grp.home + '">≪ ' + esc(grp.name) + '</a></div>';
    S.filter(function (s) { return s.group === curGroup; }).forEach(function (s) {
      h += '<div class="sb-sec' + (s.code === curSec ? ' cur' : '') + '"><a href="'
         + prefix + s.home + '">' + esc(s.name) + '（' + s.law_count + '）</a></div>';
      M.departments.forEach(function (d) {
        if (d.sec !== s.code) return;
        var open = (d.sec === curSec && d.name === curDept) ? ' open' : '';
        h += '<details class="sb-group"' + open + '><summary>' + esc(d.name) + '（' + d.count + '）</summary><ul>';
        M.laws.forEach(function (l) {
          if (l.sec !== d.sec || l.dept !== d.name) return;
          var cur = (l.slug === curSlug && l.sec === curSec) ? ' class="cur"' : '';
          h += '<li' + cur + '><a href="' + prefix + l.file + '">' + esc(l.short) + '</a></li>';
        });
        h += '</ul></details>';
      });
    });
    if (curGroup === 'laws' && M.hist.length) {
      var openH = isHist(curDept) ? ' open' : '';
      h += '<div class="sb-sec' + (isHist(curDept) ? ' cur' : '') + '"><a href="'
         + prefix + M.meta.hist_list + '">' + esc(M.meta.hist_name) + '（' + M.hist.length + '）</a></div>';
      h += '<details class="sb-group"' + openH + '><summary>全部已废止文本</summary><ul>';
      M.hist.forEach(function (l) {
        var cur = (l.slug === curSlug) ? ' class="cur"' : '';
        h += '<li' + cur + '><a href="' + prefix + l.file + '">' + esc(l.short) + '</a></li>';
      });
      h += '</ul></details>';
    }
    sb.innerHTML = h;
  }

  // ---- 页脚 ----
  var ft = document.getElementById('footer');
  if (ft) {
    var _s = secOf(curSec);
    ft.innerHTML = (_s && _s.foot) || M.meta.foot_default || '© 2026 Lawstudy';
  }

  // ---- 板块首页 ----
  if (body.id === 'page-home') {
    var hb = document.getElementById('home-body');
    if (hb) {
      var h2 = '';
      M.departments.forEach(function (d) {
        if (d.sec !== curSec) return;
        h2 += '<div class="group"><h2>' + esc(d.name) + '（' + d.count + '）　'
            + '<a href="' + prefix + d.list + '">〔列表页〕</a></h2><ul class="laws">';
        M.laws.forEach(function (l) {
          if (l.sec === d.sec && l.dept === d.name)
            h2 += '<li><a href="' + prefix + l.file + '">' + esc(l.short) + '</a></li>';
        });
        h2 += '</ul></div>';
      });
      hb.innerHTML = h2;
    }
  }

  // ---- 法条搜索（仅法条，不含案例）----
  if (body.id === 'page-search') {
    var sel = document.getElementById('s-dept'), inp = document.getElementById('s-q'),
        out = document.getElementById('s-out'), stt = document.getElementById('s-status');
    var IDX = window.LAW_SEARCH_IDX || {};
    var OPT = '<option value="">全部分组</option>';
    S.forEach(function (s) {
      if (!s.law_count || s.type === 'cases') return;
      OPT += '<optgroup label="' + esc(s.name) + '">';
      M.departments.forEach(function (d) {
        if (d.sec !== s.code) return;
        OPT += '<option value="' + esc(d.name) + '">' + esc(d.name) + '（' + d.count + '）</option>';
      });
      OPT += '</optgroup>';
    });
    if (M.hist.length) {
      OPT += '<optgroup label="' + esc(M.meta.hist_name) + '"><option value="__hist__">全部已废止文本（'
           + M.hist.length + '）</option></optgroup>';
    }
    sel.innerHTML = OPT;
    var qm = /[?&]dept=([^&]*)/.exec(location.search);
    if (qm) sel.value = decodeURIComponent(qm[1]);
    var timer = null;
    function run() {
      var kw = inp.value.trim(), key = sel.value, n = 0, rows = [];
      if (!kw) { stt.innerHTML = '输入关键词后开始搜索（支持法规名、条号、条文内容）'; out.innerHTML = ''; return; }
      function scan(list, isHistList) {
        list.forEach(function (l) {
          if (l.kind === 'case') return;
          if (key === '__hist__') { if (!isHistList) return; }
          else if (key && l.dept !== key) return;
          var arts = (IDX[l.dept] && IDX[l.dept][l.slug]) || [];
          arts.forEach(function (a) {
            if (a.n.indexOf(kw) >= 0 || a.txt.indexOf(kw) >= 0 || l.short.indexOf(kw) >= 0) {
              n++;
              if (n <= 200) rows.push('<p class="art"><a href="' + prefix + l.file
                + '#art-' + a.i + '">【' + esc(l.short) + '】' + a.n + '</a>　' + esc(a.txt) + '</p>');
            }
          });
        });
      }
      scan(M.laws, false); scan(M.hist, true);
      stt.innerHTML = '命中 ' + n + ' 条' + (n > 200 ? '（显示前 200 条，请细化关键词）' : '');
      out.innerHTML = rows.join('');
    }
    inp.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(run, 200); });
    sel.addEventListener('change', run);
  }

  // ---- 案例搜索（独立）----
  if (body.id === 'page-case-search') {
    var cInp = document.getElementById('s-q'), cOut = document.getElementById('s-out'),
        cStt = document.getElementById('s-status'), cSel = document.getElementById('s-field');
    var CIDX = window.LAW_CASE_IDX || {};
    var FOPT = '<option value="">全部领域</option>';
    S.forEach(function (s) {
      if (s.type !== 'cases') return;
      M.departments.forEach(function (d) {
        if (d.sec !== s.code) return;
        FOPT += '<option value="' + esc(d.name) + '">' + esc(d.name) + '（' + d.count + '）</option>';
      });
    });
    if (cSel) cSel.innerHTML = FOPT;
    var cTimer = null;
    function cRun() {
      var kw = cInp.value.trim(), fd = cSel ? cSel.value : '', n = 0, rows = [];
      if (!kw) { cStt.innerHTML = '输入关键词后开始搜索（支持案号、案名、关键词、裁判要点、正文）'; cOut.innerHTML = ''; return; }
      Object.keys(CIDX).forEach(function (slug) {
        var c = CIDX[slug];
        if (fd && c.field !== fd) return;
        var hit = (c.no.indexOf(kw) >= 0 || c.title.indexOf(kw) >= 0 || c.keys.indexOf(kw) >= 0
                   || c.rule.indexOf(kw) >= 0 || c.text.indexOf(kw) >= 0);
        if (!hit) return;
        n++;
        if (n > 200) return;
        var clip = c.rule.indexOf(kw) >= 0 ? c.rule : (c.text.indexOf(kw) >= 0 ? c.text : c.title);
        var p = clip.indexOf(kw);
        var seg = p >= 0 ? clip.substring(Math.max(0, p - 40), p + 80) : clip.substring(0, 120);
        rows.push('<div class="case-hit"><div class="t"><a href="' + prefix + c.file + '">指导案例 '
          + esc(c.no) + ' 号　' + esc(c.title) + '</a></div><div class="m">' + esc(c.field)
          + ' · ' + esc(c.published) + ' 发布' + (c.void ? ' · <b>已不再参照</b>' : '') + '</div><div>…'
          + esc(seg) + '…</div></div>');
      });
      cStt.innerHTML = '命中 ' + n + ' 件' + (n > 200 ? '（显示前 200 件，请细化关键词）' : '');
      cOut.innerHTML = rows.join('');
    }
    cInp.addEventListener('input', function () { clearTimeout(cTimer); cTimer = setTimeout(cRun, 200); });
    if (cSel) cSel.addEventListener('change', cRun);
  }
})();
