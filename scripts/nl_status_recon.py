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
    updates, diffs, errs = [], [], 0
    for k, r in enumerate(rows):
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
        if (k + 1) % 50 == 0:
            print('  进度 %d/%d' % (k + 1, len(rows)), flush=True)
        time.sleep(INTERVAL + random.random() * 0.15)
    for i in range(0, len(updates), 60):
        batch = ';\n'.join(updates[i:i + 60])
        d = d1(batch)
        if not d.get('success'):
            print('批量更新失败@批', i // 60, json.dumps(d.get('errors'), ensure_ascii=False)[:200])
        else:
            print('  批 %d 提交 %d 条' % (i // 60, min(60, len(updates) - i)))
    report = {'date': datetime.datetime.utcnow().strftime('%Y-%m-%d'), 'checked': len(rows),
              'changed': len(updates), 'errors': errs, 'diffs': diffs}
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    json.dump(report, open(REPORT, 'w'), ensure_ascii=False, indent=1)
    print('REPORT: checked=%d changed=%d errors=%d' % (len(rows), len(updates), errs))


if __name__ == '__main__':
    main()
