"""
공시 이벤트 성적표 엔진 (자사주 소각, 유상증자 …)
- DART에서 이벤트 공시 공시를 2026-01-01부터 누적 수집 (data/buyback_events.csv)
- 공시일 종가 기준 1·5·20거래일 뒤 수익률과 시장(코스피/코스닥 지수) 대비 초과수익률 계산
- out/buyback.html, out/buyback.json 생성
"""
import os, csv, json, html, statistics as st, datetime as dt
from pathlib import Path
import requests
from pykrx import stock

DART_KEY = os.environ.get("DART_API_KEY", "")
ROOT = Path(__file__).parent
OUT, DATA = ROOT / "out", ROOT / "data"
EVENTS = [
    {"key": "buyback", "label": "자사주 소각", "kw": "주식소각결정", "ty": "I",
     "file": "buyback_events.csv", "page": "buyback.html", "json": "buyback.json"},
    {"key": "rights", "label": "유상증자", "kw": "유상증자결정", "ty": "B",
     "file": "rights_events.csv", "page": "rights.html", "json": "rights.json"},
]
EV = DATA / "buyback_events.csv"
CFG = EVENTS[0]
START = dt.date(2026, 1, 1)
HORIZONS = (1, 5, 20)
SITE_URL = "https://mangu8165.github.io/kospi-daily"
FIELDS = ["date", "code", "corp", "market", "title", "url"] + \
         [f"r{h}" for h in HORIZONS] + [f"x{h}" for h in HORIZONS] + ["flag"]
LIMIT = 0.30   # 한국 증시 일일 가격제한폭 ±30%: 이를 넘는 하루 변동 = 액면분할·감자·거래정지 등 데이터 왜곡
ymd = lambda d: d.strftime("%Y%m%d")


def load_events() -> list[dict]:
    if not EV.exists():
        return []
    with EV.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fetch_new(since: dt.date, until: dt.date) -> list[dict]:
    """DART는 회사 미지정 검색 시 기간 3개월 제한 → 월 단위로 끊어서 조회."""
    out, cur = [], since
    while cur <= until:
        end = min(cur + dt.timedelta(days=30), until)
        page = 1
        while True:
            d = requests.get("https://opendart.fss.or.kr/api/list.json", params={
                "crtfc_key": DART_KEY, "bgn_de": ymd(cur), "end_de": ymd(end),
                "pblntf_ty": CFG["ty"], "page_count": 100, "page_no": page}, timeout=30).json()
            if d.get("status") != "000":
                if d.get("status") != "013":
                    print("[DART]", d.get("status"), d.get("message"))
                break
            for it in d["list"]:
                rn = it["report_nm"].replace(" ", "")
                if CFG["kw"] in rn and "정정" not in rn and it.get("stock_code") \
                        and it.get("corp_cls") in ("Y", "K"):
                    rd = it["rcept_dt"]
                    out.append({"date": f"{rd[:4]}-{rd[4:6]}-{rd[6:]}", "code": it["stock_code"],
                                "corp": it["corp_name"],
                                "market": "코스피" if it["corp_cls"] == "Y" else "코스닥",
                                "title": it["report_nm"].strip(),
                                "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={it['rcept_no']}"})
            if page >= int(d.get("total_page", 1)):
                break
            page += 1
        cur = end + dt.timedelta(days=1)
    return out


def fwd_returns(series, base_date: str):
    """series: pandas Series(종가, DatetimeIndex). 공시일(장 마감 후 공시 포함) 종가 기준."""
    s = series[series.index <= base_date]
    if s.empty:
        return {}
    base_i = series.index.get_loc(s.index[-1])
    base = float(series.iloc[base_i])
    win = series.iloc[base_i: base_i + HORIZONS[-1] + 1].astype(float)
    if (win.pct_change().abs() > LIMIT + 0.005).any():
        return {"flag": "가격제한폭 초과 변동(분할·감자 등 의심)"}
    res = {}
    for h in HORIZONS:
        if base_i + h < len(series):
            res[h] = round((float(series.iloc[base_i + h]) / base - 1) * 100, 2)
    return res


def compute(events: list[dict], today: dt.date):
    idx = {}
    for mk, code in (("코스피", "1001"), ("코스닥", "2001")):
        try:
            idx[mk] = stock.get_index_ohlcv(ymd(START - dt.timedelta(days=14)), ymd(today), code)["종가"]
        except Exception as e:
            print("[지수 오류]", mk, e)
    for ev in events:
        if ev.get(f"r{HORIZONS[-1]}") not in (None, "") and "flag" in ev:
            continue                         # 이미 20일 수익률까지 확정된 건 건너뜀
        try:
            d0 = dt.date.fromisoformat(ev["date"])
            px = stock.get_market_ohlcv(ymd(d0 - dt.timedelta(days=14)), ymd(today), ev["code"])["종가"]
        except Exception as e:
            print("[주가 오류]", ev["corp"], e); continue
        r = fwd_returns(px, ev["date"])
        ev["flag"] = r.pop("flag", "")
        x = fwd_returns(idx[ev["market"]], ev["date"]) if ev["market"] in idx else {}
        for h in HORIZONS:
            ev[f"r{h}"] = r.get(h, "")
            ev[f"x{h}"] = round(r[h] - x[h], 2) if h in r and h in x else ""


def stats(events, key):
    v = sorted(float(e[key]) for e in events if e.get(key) not in (None, "") and not e.get("flag"))
    if not v:
        return None
    k = int(len(v) * 0.05)
    tv = v[k: len(v) - k] or v
    return {"n": len(v), "avg": round(st.mean(v), 2), "med": round(st.median(v), 2),
            "tavg": round(st.mean(tv), 2),
            "win": round(sum(1 for a in v if a > 0) / len(v) * 100, 1)}


e = html.escape
def pct(v):
    if v in (None, ""):
        return "<span class='na'>-</span>"
    v = float(v); c = "up" if v > 0 else "dn" if v < 0 else ""
    return f"<span class='{c}'>{v:+.2f}%</span>"


def render(events, today):
    L = CFG["label"]
    S = {f"{k}{h}": stats(events, f"{k}{h}") for k in "rx" for h in HORIZONS}
    byM = {m: {h: stats([x for x in events if x["market"] == m], f"x{h}") for h in HORIZONS}
           for m in ("코스피", "코스닥")}
    n = len(events)
    s20, x20, x5 = S["r20"], S["x20"], S["x5"]
    head = (f"2026년 {L} 공시 {n}건, 발표 후 20거래일 평균 {s20['avg']:+.1f}%"
            + (f" (시장 대비 {x20['avg']:+.1f}%p)" if x20 else "")) if s20 else \
           f"2026년 {L} 공시 {n}건 집계 중"

    rows = "".join(
        f"<tr><td>H+{h}</td><td>{S[f'r{h}']['n'] if S[f'r{h}'] else 0}</td>"
        f"<td>{pct(S[f'r{h}']['avg']) if S[f'r{h}'] else '-'}</td>"
        f"<td>{pct(S[f'r{h}']['tavg']) if S[f'r{h}'] else '-'}</td>"
        f"<td>{pct(S[f'r{h}']['med']) if S[f'r{h}'] else '-'}</td>"
        f"<td>{S[f'r{h}']['win'] if S[f'r{h}'] else '-'}%</td>"
        f"<td>{pct(S[f'x{h}']['avg']) if S[f'x{h}'] else '-'}</td>"
        f"<td>{S[f'x{h}']['win'] if S[f'x{h}'] else '-'}%</td></tr>" for h in HORIZONS)
    mrows = "".join(
        f"<tr><td>{m}</td>" + "".join(
            f"<td>{pct(byM[m][h]['avg']) if byM[m][h] else '-'} <small>({byM[m][h]['n'] if byM[m][h] else 0}건)</small></td>"
            for h in HORIZONS) + "</tr>" for m in byM)

    done = [x for x in events if x.get("x20") not in (None, "") and not x.get("flag")]
    flagged = [x for x in events if x.get("flag")]
    best = sorted(done, key=lambda x: float(x["x20"]), reverse=True)[:5]
    worst = sorted(done, key=lambda x: float(x["x20"]))[:5]
    li = lambda L: "".join(f"<li><b>{e(x['corp'])}</b> <small>{x['date']}</small> 시장 대비 {pct(x['x20'])}</li>" for x in L)

    recent = sorted(events, key=lambda x: x["date"], reverse=True)[:80]
    trows = "".join(
        f"<tr><td>{x['date']}</td><td>{e(x['market'])}</td><td><a href='{x['url']}' rel='nofollow'>{e(x['corp'])}</a>{' <small>※제외</small>' if x.get('flag') else ''}</td>"
        + "".join(f"<td>{pct(x.get(f'r{h}'))}</td>" for h in HORIZONS)
        + f"<td>{pct(x.get('x20'))}</td></tr>" for x in recent)

    faq = []
    if s20:
        faq.append((f"{L} 공시 후 주가는 실제로 어떻게 됐나?",
                    f"2026년 {S['r20']['n']}건 기준 공시 후 20거래일 평균 수익률은 {s20['avg']:+.2f}%, "
                    f"상승 비율은 {s20['win']}%입니다."
                    + (f" 같은 기간 지수 대비 초과수익률 평균은 {x20['avg']:+.2f}%p입니다." if x20 else "")))
    if x5:
        faq.append((f"{L} 공시 후 일주일(5거래일) 성과는?",
                    f"시장 대비 평균 {x5['avg']:+.2f}%p, 시장을 이긴 비율 {x5['win']}% ({x5['n']}건)."))
    faq.append((f"2026년 {L} 공시는 몇 건인가?", f"{today.isoformat()} 기준 코스피·코스닥 {n}건."))
    ld = {"@context": "https://schema.org", "@type": "FAQPage",
          "mainEntity": [{"@type": "Question", "name": q,
                          "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    ds = {"@context": "https://schema.org", "@type": "Dataset",
          "name": f"2026 {L} 공시 후 주가 수익률 데이터",
          "description": f"DART {CFG['kw']} 공시 이후 1·5·20거래일 수익률과 지수 대비 초과수익률",
          "dateModified": today.isoformat(), "isBasedOn": ["https://opendart.fss.or.kr", "https://data.krx.co.kr"],
          "distribution": {"@type": "DataDownload", "encodingFormat": "application/json",
                           "contentUrl": f"{SITE_URL}/{CFG['json']}"}}

    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{L} 공시 성적표 2026 — 발표 후 주가 1일·5일·20일 수익률</title>
<meta name="description" content="{e(head)}. 코스피·코스닥 {CFG["kw"]} 공시 전수 집계, 시장 대비 초과수익률.">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<script type="application/ld+json">{json.dumps(ds, ensure_ascii=False)}</script>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:auto;padding:16px;line-height:1.55}}
table{{border-collapse:collapse;width:100%;margin:8px 0 20px}}th,td{{border:1px solid #ddd;padding:6px;font-size:14px;text-align:right}}
td:nth-child(-n+3){{text-align:left}}th{{background:#f4f4f4}}.up{{color:#c0392b}}.dn{{color:#2463eb}}.na{{color:#aaa}}
.hero{{font-size:22px;font-weight:700;margin:8px 0}}small{{color:#888}}dt{{font-weight:600;margin-top:6px}}dd{{margin:0}}</style></head><body>
<h1>{L} 공시 성적표 (2026)</h1>
<p class="hero">{e(head)}</p>
<p><small>{today.isoformat()} 업데이트 · 대상: 2026-01-01 이후 코스피·코스닥 '{CFG["kw"]}' 공시(정정 제외) · 기준가: 공시일 종가 · 초과수익률 = 종목 수익률 − 같은 기간 코스피/코스닥 지수 수익률</small></p>
<h2>전체 성과</h2>
<table><thead><tr><th>기간</th><th>건수</th><th>평균</th><th>절사평균*</th><th>중앙값</th><th>상승비율</th><th>시장 대비 평균</th><th>시장 이긴 비율</th></tr></thead><tbody>{rows}</tbody></table>
<p><small>* 절사평균: 극단값 영향을 줄이기 위해 상·하위 5%를 제외한 평균. 가격제한폭(±30%)을 넘는 하루 변동이 있는 공시 {len(flagged)}건(액면분할·감자·거래정지 등 의심)은 통계에서 제외.</small></p>
<h2>시장별 초과수익률</h2>
<table><thead><tr><th>시장</th>{''.join(f'<th>H+{h}</th>' for h in HORIZONS)}</tr></thead><tbody>{mrows}</tbody></table>
<h2>20거래일 성적 상위 5</h2><ol>{li(best)}</ol>
<h2>20거래일 성적 하위 5</h2><ol>{li(worst)}</ol>
<h2>자주 묻는 질문</h2><dl>{''.join(f'<dt>{e(q)}</dt><dd>{e(a)}</dd>' for q, a in faq)}</dl>
<h2>최근 {L} 공시 {len(recent)}건</h2>
<table><thead><tr><th>공시일</th><th>시장</th><th>종목</th>{''.join(f'<th>H+{h}</th>' for h in HORIZONS)}<th>H+20 시장대비</th></tr></thead><tbody>{trows}</tbody></table>
<p><small>과거 성과가 미래 수익을 보장하지 않으며, 본 페이지는 공개 데이터를 자동 집계한 정보 제공용으로 투자 권유가 아닙니다. 원본 데이터: <a href="{CFG['json']}">{CFG['json']}</a></small></p>
<p><a href="buyback.html">자사주 소각 성적표</a> · <a href="rights.html">유상증자 성적표</a> · <a href="index.html">홈으로</a></p></body></html>"""


def run_one():
    today = dt.date.today()
    DATA.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
    events = load_events()
    seen = {(x["code"], x["date"]) for x in events}
    since = max(START, dt.date.fromisoformat(max(x["date"] for x in events)) - dt.timedelta(days=3)) \
        if events else START
    for ev in fetch_new(since, today):
        if (ev["code"], ev["date"]) not in seen:
            seen.add((ev["code"], ev["date"])); events.append(ev)
    events.sort(key=lambda x: x["date"])
    print(CFG["label"], "공시 누적:", len(events))
    compute(events, today)
    with EV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore"); w.writeheader(); w.writerows(events)
    (OUT / CFG["json"]).write_text(json.dumps(events, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / CFG["page"]).write_text(render(events, today), encoding="utf-8")
    print("완료:", CFG["page"])


def main():
    global CFG, EV
    for c in EVENTS:
        CFG, EV = c, DATA / c["file"]
        try:
            run_one()
        except Exception as ex:
            print("[실패]", c["label"], ex)


if __name__ == "__main__":
    main()
