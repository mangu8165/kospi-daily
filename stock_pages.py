from site_design import site_page
"""
종목별 페이지 자동 생성 (out/stock/{코드}.html) + 사이트맵 전체 재생성
- 자사주 소각 공시 이력과 공시 후 수익률 (data/buyback_events.csv)
- 최근 주요 공시와 수급 상위 기록 (data/history.csv)
"""
import csv, json, html, datetime as dt
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent
OUT, DATA = ROOT / "out", ROOT / "data"
SD = OUT / "stock"
SITE_URL = "https://mangu8165.github.io/kospi-daily"
SITE_NAME = "공시성적표"
e = html.escape


def read(p):
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pct(v, unit="%"):
    if v in (None, ""):
        return "<span class='na'>-</span>"
    v = float(v); c = "up" if v > 0 else "dn" if v < 0 else ""
    return f"<span class='{c}'>{v:+.2f}{unit}</span>"


CSS = """body{font-family:system-ui,sans-serif;max-width:900px;margin:auto;padding:16px;line-height:1.55}
table{border-collapse:collapse;width:100%;margin:8px 0 20px}th,td{border:1px solid #ddd;padding:6px;font-size:14px}
th{background:#f4f4f4}.up{color:#c0392b}.dn{color:#2463eb}.na{color:#aaa}small{color:#888}
.hero{font-size:18px;font-weight:600}dt{font-weight:600;margin-top:6px}dd{margin:0}"""


def ev_table(rows):
    return ("<table><thead><tr><th>공시일</th><th>공시</th><th>H+1</th><th>H+5</th><th>H+20</th><th>H+20 시장대비</th></tr></thead><tbody>"
            + "".join(f"<tr><td>{x['date']}</td><td><a href='{x['url']}' rel='nofollow'>{e(x['title'])}</a></td>"
                      f"<td>{pct(x.get('r1'))}</td><td>{pct(x.get('r5'))}</td><td>{pct(x.get('r20'))}</td><td>{pct(x.get('x20'), '%p')}</td></tr>"
                      for x in sorted(rows, key=lambda x: x['date'], reverse=True)) + "</tbody></table>")


def _page(code, corp, market, bb, hist, today, rt=()):
    bb = sorted(bb, key=lambda x: x["date"], reverse=True)
    hist = sorted(hist, key=lambda x: x["date"], reverse=True)[:40]
    n = len(bb)
    faq = []
    if n:
        last = bb[0]
        r20 = [float(x["r20"]) for x in bb if x.get("r20") not in (None, "") and not x.get("flag")]
        hero = (f"{corp}는 2026년 자사주 소각 결정을 {n}회 공시했습니다. 최근 공시일은 {last['date']}입니다."
                + (f" 공시 후 20거래일 평균 수익률은 {sum(r20)/len(r20):+.2f}%입니다." if r20 else ""))
        faq.append((f"{corp} 자사주 소각 했나요?", f"네. 2026년 주식소각결정 공시 {n}건, 가장 최근은 {last['date']}."))
        if r20:
            faq.append((f"{corp} 자사주 소각 후 주가는?",
                        f"공시 후 20거래일 평균 {sum(r20)/len(r20):+.2f}% ({len(r20)}건 기준)."))
    else:
        hero = f"{corp}의 최근 주요 공시와 외국인·기관 수급 상위 기록입니다."
    if rt:
        r = sorted(rt, key=lambda x: x["date"], reverse=True)
        faq.append((f"{corp} 유상증자 했나요?", f"네. 2026년 유상증자결정 공시 {len(r)}건, 가장 최근은 {r[0]['date']}."))
        if not n:
            hero = f"{corp}는 2026년 유상증자 결정을 {len(r)}회 공시했습니다. 최근 공시일은 {r[0]['date']}입니다."
    if hist:
        faq.append((f"{corp} 최근 공시는?", f"{hist[0]['date']} {hist[0]['title']}"))

    bb_rows = "".join(
        f"<tr><td>{x['date']}</td><td><a href='{x['url']}' rel='nofollow'>{e(x['title'])}</a></td>"
        f"<td>{pct(x.get('r1'))}</td><td>{pct(x.get('r5'))}</td><td>{pct(x.get('r20'))}</td><td>{pct(x.get('x20'), '%p')}</td></tr>"
        for x in bb)
    h_rows = "".join(
        f"<tr><td>{x['date']}</td><td>{e(x['category'])}</td>"
        f"<td><a href='{x['url']}' rel='nofollow'>{e(x['title'])}</a></td></tr>" for x in hist)
    ld = {"@context": "https://schema.org", "@type": "FAQPage",
          "mainEntity": [{"@type": "Question", "name": q,
                          "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    title = (f"{corp}({code}) 자사주 소각·공시 이력" if n else
             f"{corp}({code}) 유상증자·공시 이력" if rt else f"{corp}({code}) 최근 공시 정리")
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} | {SITE_NAME}</title>
<meta name="description" content="{e(hero)}">
<link rel="canonical" href="{SITE_URL}/stock/{code}.html">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>{CSS}</style></head><body>
<p><small><a href="../index.html">홈</a> › <a href="index.html">종목 목록</a></small></p>
<h1>{e(corp)} <small>{code} · {e(market)}</small></h1>
<p class="hero">{e(hero)}</p>
{f'''<h2>자사주 소각 공시와 이후 주가</h2>
<table><thead><tr><th>공시일</th><th>공시</th><th>H+1</th><th>H+5</th><th>H+20</th><th>H+20 시장대비</th></tr></thead><tbody>{bb_rows}</tbody></table>
<p><small>기준가: 공시일 종가. 전체 비교는 <a href="../buyback.html">자사주 소각 공시 성적표</a>에서 볼 수 있습니다.</small></p>''' if n else ''}
{f'''<h2>유상증자 공시와 이후 주가</h2>{ev_table(rt)}
<p><small>전체 비교는 <a href="../rights.html">유상증자 공시 성적표</a>에서 볼 수 있습니다.</small></p>''' if rt else ''}
{f'''<h2>최근 주요 공시</h2>
<table><thead><tr><th>날짜</th><th>유형</th><th>공시</th></tr></thead><tbody>{h_rows}</tbody></table>''' if hist else ''}
<h2>자주 묻는 질문</h2><dl>{''.join(f'<dt>{e(q)}</dt><dd>{e(a)}</dd>' for q, a in faq)}</dl>
<p><small>{today} 업데이트 · 출처: DART, KRX · 공개 데이터를 자동 집계한 정보 제공용이며 투자 권유가 아닙니다.</small></p>
</body></html>"""


def page(code, corp, market, bb, hist, today, rt=()):
    return site_page(_page(code, corp, market, bb, hist, today, rt), "stocks", depth=1)


def main():
    today = dt.date.today().isoformat()
    SD.mkdir(parents=True, exist_ok=True)
    bb, hist, rt = defaultdict(list), defaultdict(list), defaultdict(list)
    meta = {}
    for x in read(DATA / "buyback_events.csv"):
        bb[x["code"]].append(x); meta[x["code"]] = (x["corp"], x["market"])
    for x in read(DATA / "rights_events.csv"):
        rt[x["code"]].append(x); meta.setdefault(x["code"], (x["corp"], x["market"]))
    for x in read(DATA / "history.csv"):
        if x.get("code") and x.get("category") != "임원·주요주주 지분":
            hist[x["code"]].append(x); meta.setdefault(x["code"], (x["corp"], x["market"]))
    for code, (corp, market) in meta.items():
        (SD / f"{code}.html").write_text(page(code, corp, market, bb[code], hist[code], today, rt[code]), encoding="utf-8")

    items = sorted(meta.items(), key=lambda kv: kv[1][0])
    lis = "".join(f"<li><a href='{c}.html'>{e(n)}</a> <small>{c}{' · 소각 '+str(len(bb[c]))+'회' if bb[c] else ''}</small></li>"
                  for c, (n, m) in items)
    (SD / "index.html").write_text(
        f"<!DOCTYPE html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>종목별 자사주 소각·공시 이력 | {SITE_NAME}</title><style>{CSS}</style></head><body>"
        f"<p><small><a href='../index.html'>홈</a></small></p><h1>종목별 공시 이력 ({len(items)}개)</h1><ul>{lis}</ul></body></html>",
        encoding="utf-8")

    # 사이트맵 전체 재생성 (날짜 페이지 + 성적표 + 종목 페이지)
    index_path = SD / "index.html"
    index_path.write_text(site_page(index_path.read_text(encoding="utf-8"), "stocks", depth=1, search=True), encoding="utf-8")

    urls = [f"{SITE_URL}/", f"{SITE_URL}/buyback.html", f"{SITE_URL}/rights.html", f"{SITE_URL}/stock/index.html"]
    urls += [f"{SITE_URL}/about.html", f"{SITE_URL}/methodology.html"]
    urls += [f"{SITE_URL}/{p.name}" for p in sorted(OUT.glob("????-??-??.html"), reverse=True)]
    urls += [f"{SITE_URL}/stock/{c}.html" for c, _ in items]
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<url><loc>{u}</loc><lastmod>{today}</lastmod></url>" for u in urls) + "</urlset>",
        encoding="utf-8")
    print("종목 페이지:", len(items), "사이트맵 URL:", len(urls))


if __name__ == "__main__":
    main()
