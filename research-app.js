// AI 版权诉讼观察 · 前端渲染（列表 + 筛选 + 速读卡片）
(function () {
  var CASES = window.RS_CASES || [];   // 精选精读（人工维护）
  var AUTO = window.RS_AUTO || [];     // 张力案全录（自动收录，每月追加）
  var META = window.RS_META || {};
  var $list = document.getElementById('rs-list-body');
  var $card = document.getElementById('rs-card');
  var $meta = document.getElementById('rs-meta');
  var fCountry = document.getElementById('f-country');
  var fIssue = document.getElementById('f-issue');
  var fStatus = document.getElementById('f-status');
  var fQ = document.getElementById('f-q');
  if (!$list || !$card) return;
  var byId = {};
  CASES.concat(AUTO).forEach(function (c) { byId[c.id] = c; });

  function groupOf(c) {
    if (!c) return '其他';
    if (c.indexOf('中国') === 0) return '中国';
    if (c.indexOf('美国') === 0) return '美国';
    return '其他法域';
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c];
    });
  }
  function shortCourt(s) {
    s = s || '';
    return s.split('（')[0].split('(')[0];
  }

  var countries = [], issues = [], statuses = [];
  CASES.concat(AUTO).forEach(function (c) {
    var g = groupOf(c.country);
    if (countries.indexOf(g) < 0) countries.push(g);
    (c.issues || []).forEach(function (i) { if (issues.indexOf(i) < 0) issues.push(i); });
    if (statuses.indexOf(c.status) < 0) statuses.push(c.status);
  });
  function fill(sel, arr, all) {
    sel.innerHTML = '<option value="">' + all + '</option>' +
      arr.map(function (x) { return '<option>' + esc(x) + '</option>'; }).join('');
  }
  fill(fCountry, countries, '全部法域');
  fill(fIssue, issues, '全部争点');
  fill(fStatus, statuses, '全部状态');
  $meta.textContent = '精选精读 ' + CASES.length + ' 件 · 张力案全录 ' + AUTO.length +
    ' 件 · 数据更新 ' + (META.updated || '') + ' · 来源：' + (META.source || '') +
    (META.note ? ' · ' + META.note : '');

  function matchFilter(c) {
    if (fCountry.value && groupOf(c.country) !== fCountry.value) return false;
    if (fIssue.value && (c.issues || []).indexOf(fIssue.value) < 0) return false;
    if (fStatus.value && c.status !== fStatus.value) return false;
    var q = fQ.value.trim().toLowerCase();
    if (q) {
      var hay = (c.title + ' ' + c.court + ' ' + (c.case_no || '') + ' ' +
        (c.brief || '') + ' ' + (c.holding || '') + ' ' + (c.significance || '')).toLowerCase();
      if (hay.indexOf(q) < 0) return false;
    }
    return true;
  }
  function itemHtml(c) {
    return '<a class="rs-item" href="#' + c.id + '" data-id="' + c.id + '">' +
      '<span class="rs-item-t">' + esc(c.title) + '</span>' +
      '<span class="rs-item-m">' + esc(shortCourt(c.court)) + ' · ' + esc(c.status) + '</span></a>';
  }

  function renderList() {
    var fsC = CASES.filter(matchFilter);
    var fsA = AUTO.filter(matchFilter);
    var html = '', lastGroup = '';
    fsC.forEach(function (c) {
      var g = groupOf(c.country);
      if (g !== lastGroup) { html += '<div class="rs-group">精选精读 · ' + g + '</div>'; lastGroup = g; }
      html += itemHtml(c);
    });
    if (fsA.length) {
      var byC = {};
      fsA.forEach(function (c) {
        var g = groupOf(c.country);
        (byC[g] = byC[g] || []).push(c);
      });
      Object.keys(byC).sort(function (a, b) { return a.localeCompare(b, 'zh'); }).forEach(function (g) {
        html += '<div class="rs-group">张力案全录 · ' + g + '（' + byC[g].length + '）</div>';
        byC[g].forEach(function (c) { html += itemHtml(c); });
      });
    }
    $list.innerHTML = html || '<div class="rs-empty">无匹配案件</div>';
    $list.querySelectorAll('.rs-item').forEach(function (a) {
      a.addEventListener('click', function (e) {
        e.preventDefault();
        show(a.dataset.id, true);
      });
    });
  }

  function show(id, pushHash) {
    var c = byId[id];
    if (!c) return;
    $list.querySelectorAll('.rs-item').forEach(function (a) {
      a.classList.toggle('on', a.dataset.id === id);
    });
    var tags = (c.issues || []).map(function (i) {
      return '<span class="rs-tag">' + esc(i) + '</span>';
    }).join('');
    if (c.auto) tags += '<span class="rs-tag" style="background:#e8e4d4">自动收录 · 待精读</span>';
    $card.innerHTML =
      '<h1 class="rs-h1">' + esc(c.title) + '</h1>' +
      '<div class="rs-meta-line">' + esc(c.country) + ' · ' + esc(c.court) +
      (c.case_no ? ' · 案号 ' + esc(c.case_no) : '') + '</div>' +
      (tags ? '<div class="rs-tags">' + tags + '</div>' : '') +
      '<table class="rs-kv">' +
      '<tr><th>起诉时间</th><td>' + esc(c.filed || '—') + '</td></tr>' +
      '<tr><th>审理状态</th><td>' + esc(c.status) + '</td></tr>' +
      '<tr><th>标的 / 结果</th><td>' + esc(c.damages || '—') + '</td></tr>' +
      '</table>' +
      '<h2>案情</h2><p>' + esc(c.brief || '—') + '</p>' +
      '<h2>裁判要点 / 最新进展</h2><p>' + esc(c.holding || '—') + '</p>' +
      '<h2>意义</h2><p>' + esc(c.significance || '—') + '</p>' +
      (c.source ? '<div class="rs-src"><a href="' + esc(c.source) + '" target="_blank" rel="noopener">来源与原文 ↗</a></div>' : '') +
      '<div class="rs-upd">本页为客观资料整理，不构成法律意见 · 数据更新 ' + esc(META.updated || '') + '</div>';
    if (pushHash && history.replaceState) history.replaceState(null, '', '#' + id);
    if (window.innerWidth < 860) $card.scrollIntoView({ behavior: 'smooth' });
  }

  [fCountry, fIssue, fStatus].forEach(function (s) {
    s.addEventListener('change', renderList);
  });
  fQ.addEventListener('input', renderList);
  window.addEventListener('hashchange', function () { show(location.hash.slice(1), false); });

  var initId = location.hash.slice(1);
  renderList();
  if (initId && byId[initId]) show(initId, false);
  else if (CASES.length) show(CASES[0].id, false);
})();
