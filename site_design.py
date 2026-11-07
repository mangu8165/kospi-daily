"""Presentation for the landing page, daily archives and company pages."""
import html
import re
from event_design import CSS

EXTRA = '''
h3{font-size:16px;margin:24px 0 8px}.sum,.flow{color:var(--muted);font-size:16px}.archive,.company-list{list-style:none;padding:0;margin:0}.archive li,.company-list li{padding:12px 0}.company-list small{margin-left:8px}.features{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px;margin:24px 0}.features a{display:block;border:1px solid var(--edge);border-radius:2px;padding:16px;text-decoration:none;background:var(--surf)}.features strong{font-size:18px;font-weight:600}.features span{display:block;color:var(--muted);font-size:14px;margin-top:8px}.intro{font-size:18px;line-height:1.7;max-width:800px}.prose{max-width:800px}.prose p{font-size:18px;line-height:1.7}.search-box{margin:24px 0}.search-box label{display:block;font-size:14px;color:var(--muted);margin-bottom:8px}input[type=search]{width:100%;max-width:640px;padding:12px 16px;background:var(--surf);color:var(--text);border:1px solid var(--edge);border-radius:2px;font:16px var(--f-body)}input:focus-visible{outline:2px solid var(--accent);outline-offset:4px}.daily td,.stocks td{font-family:var(--f-body);font-weight:400}.daily td:first-child,.daily td:nth-child(2),.stocks td:nth-child(2){text-align:left}.stocks td span.up,.stocks td span.dn{font-family:var(--f-num);font-weight:600}.site-header nav{gap:8px}.empty-search{padding:16px 0;color:var(--muted)}
'''


def site_page(page, section, depth=0, search=False):
    base='../'*depth
    nav=''.join(f'<a href="{base}{url}"'+(' aria-current="page"' if section==key else '')+f'>{name}</a>' for key,url,name in [('home','index.html','홈'),('daily','index.html#daily','일일 공시'),('buyback','buyback.html','자사주 소각'),('rights','rights.html','유상증자'),('stocks','stock/index.html','종목 찾기')])
    style=(CSS+EXTRA).replace('url(fonts/','url('+base+'fonts/')
    page=re.sub(r'<style>.*?</style>','',page,flags=re.S)
    page=page.replace('</head>','<style>'+style+'</style></head>')
    head=f'<a class="skip" href="#main">본문 바로가기</a><div class="shell"><header class="site-header"><a class="wordmark" href="{base}index.html">공시성적표</a><nav aria-label="주요 메뉴">{nav}</nav></header><main id="main" class="{section}">'
    page=page.replace('<body>','<body>'+head)
    page=re.sub(r'<table>.*?</table>',lambda m:'<div class="table-scroll" tabindex="0" role="region" aria-label="가로로 스크롤할 수 있는 데이터 표">'+m[0]+'</div>',page,flags=re.S)
    if search:
        control='<div class="search-box"><label for="company-search">종목명 또는 6자리 종목코드</label><input type="search" id="company-search" placeholder="예: 삼성전자 또는 005930" autocomplete="off"><p id="search-count" class="meta" role="status" aria-live="polite"></p><p id="search-empty" class="empty-search" hidden>검색 결과가 없습니다.</p></div>'
        page=re.sub(r'(<h1>.*?</h1>)',lambda m:m[0]+control,page,count=1,flags=re.S)
        page=page.replace('<ul>','<ul class="company-list">',1)
        page=page.replace('</body>','''<script>
const field=document.querySelector('#company-search');const items=Array.from(document.querySelectorAll('.company-list>li'));function filterCompanies(){const query=field.value.trim().toLocaleLowerCase();let count=0;for(const item of items){item.hidden=!item.textContent.toLocaleLowerCase().includes(query);if(!item.hidden)count++;}document.querySelector('#search-count').textContent=count+'개 종목';document.querySelector('#search-empty').hidden=count!==0;}field.addEventListener('input',filterCompanies);filterCompanies();
</script></body>''')
    footer=f'</main><footer class="site-footer"><a href="{base}about.html">사이트 소개</a><a href="{base}methodology.html">계산 방법</a><a href="{base}stock/index.html">종목 찾기</a><p>DART · KRX 자료 기반 · 공개 자료를 집계한 정보 제공 서비스이며 투자 권유가 아닙니다.</p></footer></div>'
    return page.replace('</body>',footer+'</body>')


def home(days, verification):
    links=''.join(f'<li><a href="{d}.html">{d} 공시·수급 기록</a></li>' for d in days)
    latest=days[0] if days else '자료 준비 중'
    page=f'''<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>공시성적표 | 공시 이후 주가를 데이터로 확인</title><meta name="description" content="자사주 소각·유상증자 공시 후 수익률과 시장 대비 성과를 표본 수·계산 기준과 함께 확인하세요.">{verification}</head><body><h1>공시 이후, 실제로 어땠을까</h1><p class="intro">자사주 소각과 유상증자 발표 이후의 주가를 같은 기준으로 비교합니다. 숫자와 원문을 함께 확인하세요.</p><p class="meta">일일 공시 최신 기준일: {html.escape(latest)} · 성적표 갱신일은 각 페이지에 표시</p><section class="features" aria-label="데이터 탐색"><a href="buyback.html"><strong>자사주 소각 성적표</strong><span>1·5·20거래일 수익률과 시장 대비 성과</span></a><a href="rights.html"><strong>유상증자 성적표</strong><span>평균·중앙값·상승 비율과 유효 표본</span></a><a href="stock/index.html"><strong>종목별 공시 이력</strong><span>종목명·코드로 검색하고 공시 원문 확인</span></a></section><p class="meta">공시의 인과 효과나 미래 수익률 예측이 아닌 과거 표본의 관측 결과입니다. <a href="methodology.html">계산 기준과 한계</a>를 함께 확인하세요.</p><h2 id="daily">일일 공시·수급 기록</h2><ul class="archive">{links}</ul></body></html>'''
    return site_page(page,'home')


def write_info_pages(out):
    sections={
        'about':('사이트 소개','''<p>공시성적표는 한국 상장기업의 공시 이후 주가 변화를 누적·비교하는 데이터 서비스입니다. 공시 원문을 찾는 데서 그치지 않고 이후 결과를 확인하는 것을 목표로 합니다.</p><h2>제공하는 자료</h2><p>일일 주요 공시와 투자자별 수급, 자사주 소각·유상증자 성적표, 종목별 공시 이력을 제공합니다. 공시는 금융감독원 DART, 주가·지수·수급은 KRX 자료를 기반으로 합니다.</p><h2>분석과 운영</h2><p>공개 데이터를 자동 수집하고 규칙과 코드로 집계합니다. 주목 공시 점수는 분류를 돕는 규칙 기반 정렬이며 투자 매력도나 기대 수익률을 보장하지 않습니다. 데이터 제공처 지연·결측과 해석 오류가 있을 수 있으니 DART 원문과 계산 기준을 함께 확인하세요.</p><h2>오류 제보</h2><p><a href="https://github.com/mangu8165/kospi-daily/issues">GitHub 이슈</a>에 페이지 주소·기준일·종목코드와 잘못된 항목을 남겨 주세요. 계좌 정보·비밀번호·API 키 등 비밀정보는 적지 마세요.</p>'''),
        'methodology':('계산 방법과 한계','''<h2>수익률 기준</h2><p>공시일 종가(휴장일은 직전 시장 거래일)를 기준으로 소속 시장 지수의 거래일 달력에서 1·5·20거래일 후 날짜를 선택합니다. 해당 날짜의 종목·지수 가격을 비교하며 종목 가격이 없거나 0인 경우 다른 날짜로 대체하지 않습니다.</p><p>수익률(%) = (목표일 가격 ÷ 기준일 가격 − 1) × 100. 시장 대비 성과(%p) = 종목 수익률 − 같은 기간 소속 시장 지수 수익률. 배당 재투자를 포함한 총수익률은 아닙니다.</p><h2>표본과 제외</h2><p>전체 공시 수와 기간별 유효 표본 수를 구분합니다. 아직 기간이 지나지 않았거나 필요한 가격이 없으면 0%로 채우지 않습니다. 최대 20거래일 창에서 하루 절대 변화율 30.5% 초과가 감지되면 현재는 사건 전체를 제외합니다. 이 규칙이 분할·감자를 확정하거나 모든 가격 조정 오류를 탐지하는 것은 아닙니다.</p><p>절사평균은 정렬된 표본의 상·하위 각 5%(건수는 내림)를 제외한 평균이며 상승 비율은 수익률이 0%를 초과한 표본 비율입니다. 시장 대비 통계의 유효 표본 수는 별도로 표시합니다.</p><h2>해석의 한계</h2><p>공시 시각은 반영하지 않아 발표 당일 반응과 실제 매매 가능한 수익률을 뜻하지 않습니다. 동일 기업의 반복 공시, 업종·규모·시장 국면 구성 차이를 통제하지 않았으므로 유형 간 평균 차이를 공시의 인과 효과로 해석할 수 없습니다.</p><p>정정·취소 공시 연결, 권리락·수정주가 품질, 거래정지 중 가격 제공 관행은 추가 검증 대상입니다. 계산 버전 변경 시 과거 표본을 재계산할 수 있으며, 한 해의 결과를 다른 기간으로 일반화해서는 안 됩니다.</p><h2>갱신과 재현</h2><p>성적표는 공시별로 계산한 JSON과 DART 원문 링크를 제공합니다. 기간별 결측·미성숙 표본 때문에 종목 수와 유효 표본 수는 다를 수 있습니다. 보고서 생성 실패 시 새 배포는 중단되고 기존 공개 페이지는 남습니다. 따라서 페이지에 표시된 갱신일을 확인해야 합니다.</p>''')}
    for slug,(title,body) in sections.items():
        page=f'<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} | 공시성적표</title></head><body><article class="prose"><h1>{title}</h1>{body}</article></body></html>'
        (out/f'{slug}.html').write_text(site_page(page,slug),encoding='utf-8')
