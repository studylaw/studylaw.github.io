#!/usr/bin/env python3
# 每月自动更新「AI 版权诉讼观察」：
#   抓 AI Lawsuit Tracker（版权类案件清单 + 全表）→ 与 seen 基线 diff → 新案写入 research-data.js 的 RS_NEW（自动收录区）
#   → 刷新 research.html 的更新徽章与 RS_META.updated → 维护 scripts/seen_slugs.json 基线
# 精选卡片（RS_CASES）仍由人工精读维护；本脚本只做"自动收录 + 日期滚动"。
import json, re, base64, urllib.request, os, sys, datetime, html, time

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'research-data.js')
RPAGE = os.path.join(ROOT, 'research.html')
SEEN = os.path.join(ROOT, 'scripts', 'seen_slugs.json')


def fetch(url):
    last = None
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode('utf-8', 'ignore')
        except Exception as e:
            last = e
            print('fetch 重试', i + 1, url[:60], e)
            time.sleep(4)
    raise last


def clean_case(s):
    s = re.split(r'\s+Complaint filed', s)[0]
    s = re.split(r'\s+filed\s', s)[0]
    return re.sub(r'\s+', ' ', s).strip(' |')


def clean_court(s):
    return re.split(r'\s+Filed\s', s)[0].strip(' |')


def country(court):
    c = (court or '').lower()
    if 'beijing' in c or 'hangzhou internet' in c or 'jinshan' in c:
        return '中国'
    if re.search(r"u\.s\.|united states|\b[nspcdewm]\.d\.|sdny|d\.\s*mass|d\.\s*colo|d\.\s*del|d\.\s*ariz|superior court|circuit court|county court|\d(th|st|nd|rd) cir\.|travis county|\bftc\b|sec admin", c, re.I):
        return '美国'
    for k, v in [('munich', '德国'), ('münchen', '德国'), ('german', '德国'), ('landgericht', '德国'),
                 ('amtsgericht', '德国'), ('frankfurt', '德国'), ('berlin', '德国'),
                 ('england', '英国'), ('ewhc', '英国'), ('london', '英国'), ('high court', '英国'),
                 ('canada', '加拿大'), ('denmark', '丹麦'), ('danish', '丹麦'),
                 ('budapest', '匈牙利'), ('paris', '法国'), ('delhi', '印度'), ('amsterdam', '荷兰'),
                 ('roma', '意大利'), ('australia', '澳大利亚'), ('japan', '日本'), ('tokyo', '日本'),
                 ('spain', '西班牙'), ('são paulo', '巴西'), ('sao paulo', '巴西')]:
        if k in c:
            return v
    return '其他'


def parse_cases(page):
    t = re.search(r'<table.*?</table>', page, re.S).group(0)
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S)
    info = {}
    for r in rows[1:]:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', r, re.S)
        if len(cells) != 4:
            continue
        m = re.search(r'href="(/cases/[^"]+)"', cells[0])
        if not m:
            continue
        slug = m.group(1).lstrip('/').split('/cases/')[-1].rstrip('/')
        info[slug] = dict(
            name=clean_case(html.unescape(re.sub(r'<[^>]+>', ' ', cells[0]))),
            court=clean_court(html.unescape(re.sub(r'<[^>]+>', ' ', cells[1]))),
            filed=html.unescape(re.sub(r'<[^>]+>', ' ', cells[2])).strip(),
            status=html.unescape(re.sub(r'<[^>]+>', ' ', cells[3])).strip())
    return info


def main():
    hub = fetch('https://ailawsuittracker.com/ai-copyright-lawsuits/')
    copy_slugs = set(re.findall(r'href="/cases/([^"/]+)', hub)) | \
                 set(re.findall(r'"url":\s*"https://ailawsuittracker\.com/cases/([^"/]+)', hub))
    print('tracker 版权类案件总数:', len(copy_slugs))

    info = parse_cases(fetch('https://ailawsuittracker.com/cases/'))
    print('tracker 全表案件:', len(info))

    if os.path.exists(SEEN):
        seen = set(json.load(open(SEEN)))
    else:
        data_src = open(DATA, encoding='utf-8').read()
        seen = set(re.findall(r'ailawsuittracker\.com/cases/([^/\']+)', data_src)) | copy_slugs
        os.makedirs(os.path.dirname(SEEN), exist_ok=True)
        json.dump(sorted(seen), open(SEEN, 'w'), indent=0)
        print('首次运行：已建立基线（seen=%d），本次不产出新增' % len(seen))
        return

    new_slugs = sorted(copy_slugs - seen)
    today = datetime.date.today()
    tag = today.strftime('%Y-%m')
    print('新增版权案件:', len(new_slugs))

    items = []
    for i, s in enumerate(new_slugs):
        d = info.get(s.rstrip('/'), {})
        items.append({
            'id': 'auto-%s-%02d' % (tag, i + 1),
            'title': d.get('name') or s[:60],
            'country': country(d.get('court', '')),
            'court': d.get('court', ''),
            'case_no': '',
            'filed': d.get('filed', ''),
            'status': d.get('status', ''),
            'damages': '—',
            'issues': ['自动收录'],
            'brief': '〔自动收录 · 待人工精读〕AI Lawsuit Tracker 本月新增版权类案件，要点与意义待复核后并入精选。',
            'holding': '—', 'significance': '—',
            'source': 'https://ailawsuittracker.com/cases/%s/' % s})

    src = open(DATA, encoding='utf-8').read()
    today_s = today.strftime('%Y-%m-%d')
    src = re.sub(r"(window\.RS_META = \{ updated: ')[^']+", r'\g<1>' + today_s, src, count=1)
    # 新案并入「张力案全录」RS_AUTO（按 source 去重）
    m = re.search(r'window\.RS_AUTO = (\[.*?\]);\n', src, re.S)
    cur = json.loads(m.group(1)) if m else []
    have = {x.get('source') for x in cur}
    add = [x for x in items if x['source'] not in have]
    cur.extend(add)
    new_line = 'window.RS_AUTO = ' + json.dumps(cur, ensure_ascii=False, indent=1) + ';\n'
    if m:
        src = re.sub(r'window\.RS_AUTO = (\[.*?\]);\n', lambda mm: new_line, src, count=1, flags=re.S)
    else:
        src = src.replace('window.RS_CASES = [', new_line + 'window.RS_CASES = [', 1)
    open(DATA, 'w', encoding='utf-8').write(src)
    print('并入自动全录:', len(add))

    if os.path.exists(RPAGE):
        h = open(RPAGE, encoding='utf-8').read()
        h = re.sub(r'(entry-m">)\d{4}-\d{2} 更新', lambda m: m.group(1) + tag + ' 更新', h)
        open(RPAGE, 'w', encoding='utf-8').write(h)

    seen |= copy_slugs
    json.dump(sorted(seen), open(SEEN, 'w'), indent=0)
    json.dump({'date': today_s, 'new_count': len(items)}, open(os.path.join(os.path.dirname(SEEN), 'last_run.json'), 'w'))
    print('UPDATED', today_s, 'NEW', len(items))


if __name__ == '__main__':
    main()
