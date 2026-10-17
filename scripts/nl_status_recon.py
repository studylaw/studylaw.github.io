#!/usr/bin/env python3
# national-laws 全库时效性对账（月度，GitHub Actions 版）：
#   逐条调 flk 详情接口核 sxx（3=有效 2=已修改 1=已废止 4=尚未生效）→ 批量更新 D1 status → 输出 diffs 报告
# 依赖 secrets：CF_ACCOUNT_ID / CF_API_TOKEN（需 D1 Edit 权限）
import json, re, time, random, urllib.request, os, sys, datetime

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
ACCT = os.environ['CF_ACCOUNT_ID']
TOK = os.environ['CF_API_TOKEN']
UUID = 'cc06e76c-6131-425d-bf45-38c4e0cf13e6'
SXX_MAP = {'3': '有效', '2': '已修改', '1': '已废止', '4': '尚未生效'}
INTERVAL = 0.32
REPORT = 'scripts/nl_status_diffs.json'
SEEN = 'scripts/nl_seen.json'      # bbbs -> 最近对账日期（滚动对账基线）
RUN_LIMIT = 2400                    # 单次运行上限（避免触发 flk WAF 限流，实测约 2500 条后触发）


def d1(sql):
    last = None
    for i in range(3):
        try:
            req = urllib.request.Request(
                'https://api.cloudflare.com/client/v4/accounts/%s/d1/database/%s/query' % (ACCT, UUID),
                data=json.dumps({'sql': sql}).encode(), method='POST',
                headers={'Authorization': 'Bearer ' + TOK, 'Content-Type': 'application/json',
                         'User-Agent': 'nlrecon'})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception as e:
            last = e
            time.sleep(3)
    raise last


def flk_detail(bbbs):
    # 逐次新建连接（勿用 keep-alive：同连接高频会触发 flk WAF 挑战页）
    url = 'https://flk.npc.gov.cn/law-search/search/flfgDetails?bbbs=' + bbbs
    last = None
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={**UA, 'Referer': 'https://flk.npc.gov.cn/detail?id=' + bbbs})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode('utf-8', 'ignore'))
            data = d.get('data') or {}
            return str(data.get('sxx') or ''), data
        except Exception as e:
            last = e
            time.sleep(2)
    raise last


def load_all():
    rows, off = [], 0
    while True:
        d = d1('SELECT id, flk_id, status, title FROM laws WHERE flk_id IS NOT NULL AND flk_id != "" ORDER BY id LIMIT 800 OFFSET %d' % off)
        rs = d['result'][0]['results']
        rows += rs
        if len(rs) < 800:
            break
        off += 800
    return rows


def main():
    rows = load_all()
    print('带 flk_id 条数:', len(rows))
    # 滚动对账：最久未对账的优先，单次上限 RUN_LIMIT
    seen = {}
    if os.path.exists(SEEN):
        seen = json.load(open(SEEN))
    rows.sort(key=lambda r: seen.get(r['flk_id'], '1970-01-01'))
    todo = rows[:RUN_LIMIT]
    print('本轮对账:', len(todo), '（最旧对账日:', seen.get(todo[0]['flk_id'], '从未'), '）')
    updates, diffs, errs = [], [], 0
    for k, r in enumerate(todo):
        try:
            sxx, _ = flk_detail(r['flk_id'])
        except Exception as e:
            errs += 1
            print('  [跳过] id=%s %s' % (r['id'], str(e)[:60]))
            continue
        new = SXX_MAP.get(sxx)
        if new and new != r['status']:
            updates.append("UPDATE laws SET status='%s' WHERE id=%d" % (new, r['id']))
            diffs.append({'id': r['id'], 'title': r['title'][:40], 'old': r['status'], 'new': new, 'sxx': sxx})
        seen[r['flk_id']] = datetime.date.today().strftime('%Y-%m-%d')
        if (k + 1) % 50 == 0:
            print('  进度 %d/%d' % (k + 1, len(todo)), flush=True)
        time.sleep(INTERVAL + random.random() * 0.15)
    for i in range(0, len(updates), 60):
        batch = ';\n'.join(updates[i:i + 60])
        d = d1(batch)
        if not d.get('success'):
            print('批量更新失败@批', i // 60, json.dumps(d.get('errors'), ensure_ascii=False)[:200])
        else:
            print('  批 %d 提交 %d 条' % (i // 60, min(60, len(updates) - i)))
    json.dump(seen, open(SEEN, 'w'), indent=0)
    remaining = len([r for r in rows if seen.get(r['flk_id']) is None] ) + 0
    report = {'date': datetime.datetime.utcnow().strftime('%Y-%m-%d'), 'checked': len(todo),
              'changed': len(updates), 'errors': errs, 'covered_total': len(seen),
              'remaining': max(0, len(rows) - len(seen)), 'diffs': diffs}
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    json.dump(report, open(REPORT, 'w'), ensure_ascii=False, indent=1)
    print('REPORT: checked=%d changed=%d errors=%d covered=%d remaining=%d' %
          (len(todo), len(updates), errs, len(seen), report['remaining']))


if __name__ == '__main__':
    main()
