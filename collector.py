"""
코스피/코스닥 일일 데이터 수집기 + 정적 페이지 생성기
- DART: 주요 공시(자사주, 최대주주 변동, 유상증자, 공급계약 등) 유형별 정리
- KRX(pykrx): 외국인/기관 순매수 상위 종목
출력: out/YYYY-MM-DD.html, out/YYYY-MM-DD.json, out/index.html

사용법:
  set DART_API_KEY=발급받은키     (Windows)  /  export DART_API_KEY=...  (mac/linux)
  python collector.py              # 오늘
  python collector.py 20261106     # 특정 날짜
"""
import os, sys, json, html, datetime as dt
from pathlib import Path
import requests
from pykrx import stock

DART_KEY = os.environ.get("DART_API_KEY", "")
OUT = Path(__file__).parent / "out"
SITE_NAME = "코스피 데일리 데이터"   # 나중에 사이트명으로 변경
SITE_URL = "https://mangu8165.github.io/kospi-daily"     # 도메인 생기면 변경

# 공시 분류 규칙: (카테고리, 보고서명에 포함된 키워드들)
CATEGORIES = [
    ("자사주 매입·소각", ["자기주식취득", "자기주식 취득", "주식소각", "자기주식처분"]),
    ("최대주주 변경", ["최대주주변경", "최대주주 변경"]),
    ("5% 대량보유", ["주식등의대량보유"]),
    ("유상증자·CB·BW", ["유상증자", "전환사채", "신주인수권부사채", "교환사채"]),
    ("공급계약·수주", ["단일판매ㆍ공급계약", "단일판매·공급계약"]),
    ("실적 공시", ["영업(잠정)실적", "매출액또는손익구조"]),
    ("배당", ["현금ㆍ현물배당", "현금·현물배당"]),
    ("임원·주요주주 지분", ["임원ㆍ주요주주특정증권", "임원·주요주주특정증권"]),
]

# 주목도 점수: 카테고리 기본점 + 제목 키워드 가산
BASE_SCORE = {"최대주주 변경": 9, "자사주 매입·소각": 7, "유상증자·CB·BW": 6,
              "공급계약·수주": 6, "실적 공시": 5, "배당": 4, "5% 대량보유": 3,
              "임원·주요주주 지분": 1}
KEYWORD_BONUS = [("소각", 3), ("제3자배정", 3), ("최대주주변경", 2), ("영업(잠정)실적", 1),
                 ("기재정정", -2), ("철회", 1), ("해지", 2), ("결정", 1)]
HIDE_IN_MAIN = {"임원·주요주주 지분"}   # 본문에서는 접어서 표시


def fetch_dart(day: str) -> list[dict]:
    if not DART_KEY:
        print("[경고] DART_API_KEY 없음 — 공시 수집 건너뜀")
        return []
    items, page = [], 1
    while True:
        r = requests.get("https://opendart.fss.or.kr/api/list.json", params={
            "crtfc_key": DART_KEY, "bgn_de": day, "end_de": day,
            "page_count": 100, "page_no": page}, timeout=20)
        d = r.json()
        if d.get("status") == "013":   # 데이터 없음
            break
        if d.get("status") != "000":
            print("[DART 오류]", d.get("status"), d.get("message"))
            break
        items += d["list"]
        if page >= int(d.get("total_page", 1)):
            break
        page += 1
    # 상장사(유가 Y / 코스닥 K)만
    return [i for i in items if i.get("corp_cls") in ("Y", "K")]


def classify(items: list[dict]) -> dict[str, list[dict]]:
    out = {name: [] for name, _ in CATEGORIES}
    for it in items:
        rn = it["report_nm"].replace(" ", "")
        for name, kws in CATEGORIES:
            if any(k.replace(" ", "") in rn for k in kws):
                out[name].append({
                    "corp": it["corp_name"], "code": it.get("stock_code", ""),
                    "market": "코스피" if it["corp_cls"] == "Y" else "코스닥",
                    "title": it["report_nm"].strip(),
                    "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={it['rcept_no']}",
                })
                break
    return out


def fetch_flows(day: str, top: int = 15) -> dict:
    res = {}
    for market in ("KOSPI", "KOSDAQ"):
        for inv in ("외국인", "기관합계"):
            try:
                df = stock.get_market_net_purchases_of_equities(day, day, market, inv)
            except Exception as e:
                print("[KRX 오류]", market, inv, e)
                continue
            if df is None or df.empty:
                continue
            df = df.sort_values("순매수거래대금", ascending=False)
            rows = lambda d: [{"code": c, "name": r["종목명"],
                               "net_krw_eok": round(r["순매수거래대금"] / 1e8, 1)}
                              for c, r in d.iterrows()]
            res[f"{market}_{inv}"] = {"buy": rows(df.head(top)),
                                     "sell": rows(df.tail(top).iloc[::-1])}
    return res


def score_all(disc: dict, flows: dict) -> list[dict]:
    """공시마다 점수를 매기고, 같은 날 외국인·기관 순매수/순매도 상위면 가산."""
    flow_tag = {}
    for key, v in flows.items():
        inv = key.split("_")[1]
        for r in v.get("buy", []):
            flow_tag.setdefault(r["code"], []).append(f"{inv} 순매수 상위({r['net_krw_eok']}억)")
        for r in v.get("sell", []):
            flow_tag.setdefault(r["code"], []).append(f"{inv} 순매도 상위({r['net_krw_eok']}억)")
    out = []
    for cat, lst in disc.items():
        for x in lst:
            sc = BASE_SCORE.get(cat, 0)
            t = x["title"].replace(" ", "")
            for kw, b in KEYWORD_BONUS:
                if kw in t:
                    sc += b
            tags = flow_tag.get(x["code"], [])
            if tags:
                sc += 3
            out.append({**x, "category": cat, "score": sc, "flow": tags})
    out.sort(key=lambda r: r["score"], reverse=True)
    return out


def top_picks(scored: list[dict], n: int = 5) -> list[dict]:
    seen, res = set(), []
    for r in scored:
        if r["category"] in HIDE_IN_MAIN or r["corp"] in seen:
            continue
        seen.add(r["corp"]); res.append(r)
        if len(res) == n:
            break
    return res


def save_history(day_iso: str, scored: list[dict]):
    """공시 후 주가 반응 통계를 위해 이력 누적 (data/history.csv)."""
    import csv
    hp = Path(__file__).parent / "data" / "history.csv"
    hp.parent.mkdir(exist_ok=True)
    new = not hp.exists()
    old = set()
    if not new:
        with hp.open(encoding="utf-8") as f:
            old = {(r["date"], r["url"]) for r in csv.DictReader(f)}
    with hp.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date", "code", "corp", "market", "category", "score", "title", "url"])
        for r in scored:
            if r["code"] and (day_iso, r["url"]) not in old:
                w.writerow([day_iso, r["code"], r["corp"], r["market"], r["category"],
                            r["score"], r["title"], r["url"]])


# ---------- HTML ----------
e = html.escape

def table(headers, rows):
    h = "".join(f"<th>{e(x)}</th>" for x in headers)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>"


def render(day_iso: str, disc: dict, flows: dict, picks: list[dict]) -> str:
    parts = [f"<h1>{day_iso} 코스피·코스닥 공시 및 수급 정리</h1>",
             f"<p class='sum'>{day_iso} 기준 주요 공시 {sum(len(v) for v in disc.values())}건, "
             "외국인·기관 순매수/순매도 상위 종목을 자동 집계했습니다. 출처: DART, KRX.</p>"]

    if picks:
        parts.append("<h2>오늘의 주목 공시 TOP 5</h2><ol class='top'>")
        for r in picks:
            fl = f" <span class='flow'>· {e(', '.join(r['flow']))}</span>" if r["flow"] else ""
            parts.append(f"<li><b>{e(r['corp'])}</b> <small>{e(r['code'])} · {e(r['category'])}</small><br>"
                         f"<a href='{r['url']}' rel='nofollow'>{e(r['title'])}</a>{fl}</li>")
        parts.append("</ol><p><small>점수 = 공시 유형 + 핵심 키워드(소각, 제3자배정 등) + 같은 날 외국인·기관 수급 상위 여부. 투자 권유 아님.</small></p>")

    faq = []
    for key, v in flows.items():
        if v.get("buy"):
            mk, inv = key.split("_"); b = v["buy"][0]
            faq.append((f"{day_iso} {mk} {inv} 순매수 1위 종목은?", f"{b['name']}({b['code']}), {b['net_krw_eok']}억 원"))
    if picks:
        faq.append((f"{day_iso} 가장 주목할 공시는?", f"{picks[0]['corp']} — {picks[0]['title']}"))
    if faq:
        parts.append("<h2>한눈에 보기</h2><dl>" + "".join(f"<dt>{e(q)}</dt><dd>{e(a)}</dd>" for q, a in faq) + "</dl>")

    parts.append("<h2>주요 공시</h2>")
    for cat, lst in disc.items():
        if not lst:
            continue
        if cat in HIDE_IN_MAIN:
            parts.append(f"<details><summary>{e(cat)} ({len(lst)}건) 펼치기</summary>")
        parts.append(f"<h3>{e(cat)} ({len(lst)}건)</h3>")
        parts.append(table(["시장", "종목", "공시"],
            [[e(x["market"]), f"{e(x['corp'])} <small>{e(x['code'])}</small>",
              f"<a href='{x['url']}' rel='nofollow'>{e(x['title'])}</a>"] for x in lst]))
        if cat in HIDE_IN_MAIN:
            parts.append("</details>")

    parts.append("<h2>투자자별 순매수 상위 (단위: 억원)</h2>")
    for key, v in flows.items():
        mk, inv = key.split("_")
        for side, label in (("buy", "순매수"), ("sell", "순매도")):
            parts.append(f"<h3>{mk} {inv} {label} 상위</h3>")
            parts.append(table(["순위", "종목", "코드", "금액(억)"],
                [[i + 1, e(r["name"]), r["code"], r["net_krw_eok"]] for i, r in enumerate(v[side])]))

    ld = {"@context": "https://schema.org", "@type": "Dataset",
          "name": f"{day_iso} 코스피·코스닥 공시 및 투자자별 수급",
          "description": "DART 주요 공시 유형별 분류와 KRX 외국인·기관 순매수 상위 종목 일일 집계",
          "datePublished": day_iso, "temporalCoverage": day_iso,
          "creator": {"@type": "Organization", "name": SITE_NAME},
          "isBasedOn": ["https://opendart.fss.or.kr", "https://data.krx.co.kr"],
          "distribution": {"@type": "DataDownload", "encodingFormat": "application/json",
                           "contentUrl": f"{SITE_URL}/{day_iso}.json"}}

    ld_faq = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q,
                              "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}

    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{day_iso} 코스피 공시·외국인 기관 수급 정리 | {SITE_NAME}</title>
<meta name="description" content="{day_iso} 자사주 매입, 최대주주 변동, 유상증자, 공급계약 공시와 외국인·기관 순매수 상위 종목.">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<script type="application/ld+json">{json.dumps(ld_faq, ensure_ascii=False)}</script>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:auto;padding:16px;line-height:1.5}}
table{{border-collapse:collapse;width:100%;margin:8px 0 20px}}th,td{{border:1px solid #ddd;padding:6px;font-size:14px}}
th{{background:#f4f4f4}}.sum{{color:#555}}small{{color:#888}}
.top li{{margin:8px 0}}.flow{{color:#c0392b;font-size:13px}}dt{{font-weight:600;margin-top:6px}}dd{{margin:0 0 4px 0}}</style></head><body>
{''.join(parts)}
<p><small>본 페이지는 공개 데이터를 자동 집계한 정보 제공용이며 투자 권유가 아닙니다.</small></p>
<p><a href="index.html">전체 날짜 목록</a></p></body></html>"""


def build_index():
    days = sorted((p.stem for p in OUT.glob("????-??-??.html")), reverse=True)
    links = "".join(f"<li><a href='{d}.html'>{d} 공시·수급 정리</a></li>" for d in days)
    (OUT / "index.html").write_text(
        f"<!DOCTYPE html><html lang='ko'><head><meta charset='utf-8'><title>{SITE_NAME}</title></head>"
        f"<body><h1>{SITE_NAME}</h1><p>평일 장 마감 후 DART 공시와 KRX 투자자별 수급을 자동 집계합니다.</p>"
        f"<ul>{links}</ul></body></html>", encoding="utf-8")
    (OUT / "llms.txt").write_text(
        f"# {SITE_NAME}\n\n> 한국 코스피·코스닥의 일일 주요 공시(DART)와 외국인·기관 순매수 상위(KRX)를 "
        "평일 장 마감 후 자동 집계하는 데이터 사이트. 매일 '주목 공시 TOP 5'를 규칙 기반으로 선정.\n\n"
        "## 데이터\n" + "".join(f"- [{d}]({SITE_URL}/{d}.html): HTML, 원본 JSON은 {SITE_URL}/{d}.json\n" for d in days[:30]),
        encoding="utf-8")
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + f"<url><loc>{SITE_URL}/</loc></url>"
        + "".join(f"<url><loc>{SITE_URL}/{d}.html</loc><lastmod>{d}</lastmod></url>" for d in days)
        + "</urlset>", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().strftime("%Y%m%d")
    day_iso = f"{day[:4]}-{day[4:6]}-{day[6:]}"
    OUT.mkdir(exist_ok=True)
    disc = classify(fetch_dart(day))
    flows = fetch_flows(day)
    if not flows and not any(disc.values()):
        print("데이터 없음 (휴장일?)"); return
    scored = score_all(disc, flows)
    picks = top_picks(scored)
    save_history(day_iso, scored)
    (OUT / f"{day_iso}.json").write_text(
        json.dumps({"date": day_iso, "top5": picks, "disclosures": disc, "flows": flows},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / f"{day_iso}.html").write_text(render(day_iso, disc, flows, picks), encoding="utf-8")
    build_index()
    print("완료:", OUT / f"{day_iso}.html")


if __name__ == "__main__":
    main()
