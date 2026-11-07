"""Shared SISA presentation for generated event reports. No data calculations."""
import html
import re

CSS = '''
@font-face{font-family:NeoDunggeunmo;src:url(fonts/neodgm.woff2) format("woff2");font-weight:400;font-display:swap}
@font-face{font-family:"JetBrains Mono";src:url(fonts/jetbrains-mono-600.woff2) format("woff2");font-weight:600;font-display:swap}
@font-face{font-family:Pretendard;src:url(fonts/PretendardVariable.woff2) format("woff2");font-weight:100 900;font-display:swap}
:root{--bg:#111113;--surf:#18191B;--hover:#272A2D;--edge:#363A3F;--hair:#272A2D;--text:#EDEEF0;--muted:#CDD1D6;--accent:#E8C28B;--up:#FF8A80;--down:#7CB0FF;--warn:#F0A35E;--pos:#7FD1A8;--f-num:"JetBrains Mono",ui-monospace,monospace;--f-body:Pretendard,system-ui,sans-serif;--f-title:NeoDunggeunmo,sans-serif}
*{box-sizing:border-box}html{color-scheme:dark}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.7 var(--f-body)}.shell{max-width:1200px;margin:auto;padding:0 24px}a{color:inherit;text-decoration:underline;text-underline-offset:4px;cursor:pointer}a:hover{background:var(--hover)}a:focus-visible,summary:focus-visible,.table-scroll:focus-visible{outline:2px solid var(--accent);outline-offset:4px}.skip{position:absolute;left:16px;top:-100px;background:var(--surf);padding:8px 16px}.skip:focus{top:8px}.site-header{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:24px 0;border-bottom:1px solid var(--edge)}.wordmark{font:400 22px var(--f-title);text-decoration:none;white-space:nowrap}nav{display:flex;flex-wrap:wrap;gap:8px}nav a{font-size:14px;padding:8px 16px;text-decoration:none;border-left:2px solid var(--edge)}nav a[aria-current]{border-left-color:var(--accent)}main{padding:32px 0}h1{font:400 22px/1.5 var(--f-title);margin:0 0 16px}h2{font-size:18px;line-height:1.5;margin:32px 0 16px}p{margin:8px 0 16px}.hero{font-size:18px;font-weight:600;line-height:1.7}small,.meta,.na{font-size:14px;color:var(--muted)}.summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px;border-top:1px solid var(--edge);border-bottom:1px solid var(--edge);padding:16px 0;margin:24px 0}.summary div{padding:8px 16px}.summary dt{font:400 14px var(--f-body);color:var(--muted);margin:0 0 8px}.summary dd{font:600 18px var(--f-num);margin:0}.up{color:var(--up);font-weight:600}.dn{color:var(--down);font-weight:600}.table-scroll{overflow-x:auto;border:1px solid var(--edge);border-radius:2px;margin:8px 0 16px}table{width:100%;border-collapse:collapse;background:var(--surf);white-space:nowrap}th,td{border:0;border-bottom:1px solid var(--hair);padding:12px 16px;text-align:right;font-size:16px}th{font:400 14px/1.5 var(--f-body);color:var(--muted)}td{font:600 16px/1.5 var(--f-num);font-variant-numeric:tabular-nums}td:first-child,th:first-child{text-align:left}td a{font-family:var(--f-body)}td small{font-weight:400}tr:last-child td{border-bottom:0}ol{padding-left:24px;margin:0}li{padding:12px 0;border-bottom:1px solid var(--hair)}li b{font-weight:600}dl:not(.summary){padding:16px;background:var(--surf);border:1px solid var(--edge);border-radius:2px}dt{font-weight:600;margin:16px 0 8px}dt:first-child{margin-top:0}dd{margin:0;color:var(--muted)}.summary dd{color:var(--text)}.summary dd.up{color:var(--up)}.summary dd.dn{color:var(--down)}details{margin:24px 0;border-bottom:1px solid var(--hair);padding:16px 0}summary{font-size:18px;font-weight:600;cursor:pointer}summary:hover{background:var(--hover)}.method p{font-size:18px;line-height:1.7}.site-footer{border-top:1px solid var(--edge);padding:24px 0 32px;font-size:14px;color:var(--muted)}.site-footer a{margin-right:16px}.tagline{font-size:14px;color:var(--muted);margin:0 0 24px}
@media(max-width:640px){.shell{padding:0 16px}.site-header{align-items:flex-start;flex-direction:column;gap:16px}nav a{padding:8px}.summary{grid-template-columns:1fr 1fr}.summary div{padding:8px 0}main{padding-top:24px}td,th{padding:12px 16px}}
@media(max-width:360px){.summary{grid-template-columns:1fr}}
'''


def decorate(page, label, stats, total, today, key):
    escape = html.escape
    def figure(value, suffix='%'):
        if value is None:
            return '—', ''
        return f'{value:+.2f}{suffix}', 'up' if value > 0 else 'dn' if value < 0 else ''
    r20, x20 = stats.get('r20'), stats.get('x20')
    median, median_class = figure(r20['med'] if r20 else None)
    excess, excess_class = figure(x20['avg'] if x20 else None, '%p')
    winning = f"{r20['win']:.1f}%" if r20 else '—'
    n = r20['n'] if r20 else 0
    summary = f'''<p class="tagline">공시를 읽고, 이후의 결과를 확인합니다.</p>
<dl class="summary" aria-label="20거래일 주요 통계"><div><dt>수익률 중앙값</dt><dd class="{median_class}">{median}</dd></div><div><dt>상승 비율</dt><dd>{winning}</dd></div><div><dt>시장 대비 평균</dt><dd class="{excess_class}">{excess}</dd></div><div><dt>20일 유효 표본 / 전체 공시</dt><dd>{n} / {total}건</dd></div></dl>
<p class="meta">20거래일 결과 기준 · 기간별 표본은 아래 표 참조 · 관측된 수익률이며 공시의 인과 효과나 미래 수익률을 뜻하지 않습니다.</p>'''
    nav = ''.join(f'<a href="{href}"'+(' aria-current="page"' if active == key else '')+f'>{name}</a>' for href,name,active in [('index.html','일일 공시','daily'),('buyback.html','자사주 소각','buyback'),('rights.html','유상증자','rights'),('stock/index.html','종목 찾기','stocks')])
    header = f'<a class="skip" href="#main">본문 바로가기</a><div class="shell"><header class="site-header"><a class="wordmark" href="index.html">공시성적표</a><nav aria-label="주요 메뉴">{nav}</nav></header><main id="main">'
    method = '''<details id="methodology" class="method"><summary>계산 방법과 한계</summary>
<p>공시일 종가를 기준으로 시장 지수의 거래일 달력에서 1·5·20거래일 뒤 날짜를 정하고, 동일 날짜의 종목·지수 가격을 비교합니다. 휴장일 공시는 직전 시장 거래일을 기준으로 합니다.</p>
<p>종목 가격이 없거나 0인 날짜는 다른 날짜 가격으로 대체하지 않습니다. 절대 수익률은 가격 변화율(%)이며, 시장 대비 성과는 종목 수익률에서 지수 수익률을 차감한 값(%p)입니다. 배당을 재투자한 총수익률은 아닙니다.</p>
<p>공시 시각을 반영하지 않아 발표 당일 반응과 실제 매매 가능한 성과를 의미하지 않습니다. 거래정지 중 유효한 가격처럼 제공되는 값, 권리락·분할 조정, 정정·취소 공시 연결은 추가 검증 대상입니다. 이상 변동 검사는 현재 최대 20일 창에 적용되어 단기 표본의 포함 여부에도 영향을 줄 수 있습니다.</p>
<p>공시별 표본은 독립적이지 않을 수 있습니다. 동일 기업의 반복 공시와 시장·규모 구성 차이를 고려하지 않은 단순 비교를 인과관계로 해석하지 마세요. 과거 결과는 미래 성과를 보장하지 않습니다.</p>
</details>'''
    footer = f'</main><footer class="site-footer"><a href="#methodology">계산 방법</a><a href="{key}.json">집계 원자료 JSON</a><span>DART · KRX 자료 기반 / 갱신 {escape(today.isoformat())}</span><p>정보 제공용 통계 · 투자 권유가 아닙니다. 폰트 라이선스: <a href="fonts/neodgm.OFL.txt">둥근모꼴</a><a href="fonts/jetbrains-mono.OFL.txt">JetBrains Mono</a><a href="fonts/OFL.txt">Pretendard</a></p></footer></div>'
    page = re.sub(r'<style>.*?</style>', '<style>'+CSS+'</style>', page, count=1, flags=re.S)
    page = page.replace('<body>', '<body>'+header)
    page = re.sub(r'(<h1>.*?</h1>)', lambda m:m[0]+summary, page, count=1, flags=re.S)
    page = re.sub(r'<table>.*?</table>', lambda m:'<div class="table-scroll" tabindex="0" role="region" aria-label="가로로 스크롤할 수 있는 데이터 표">'+m[0]+'</div>', page, flags=re.S)
    return page.replace('</body>',method+footer+'</body>')
