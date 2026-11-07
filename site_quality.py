"""Build descriptive metadata and validate the public sitemap before deployment."""
import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

ROOT = Path(__file__).parent
OUT = ROOT / 'out'
SITE = 'https://mangu8165.github.io/kospi-daily/'


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.links, self.ids, self.meta, self.canonical = [], set(), {}, []
        self.title, self.heading = '', ''
        self.in_title = self.in_heading = False
        self.lang = None
        self.json_blocks, self.json_text, self.in_json = [], '', False
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html':
            self.lang = a.get('lang')
        if a.get('id'):
            self.ids.add(a['id'])
        if tag == 'title':
            self.in_title = True
        if tag == 'h1':
            self.in_heading = True
        if tag == 'meta':
            self.meta[a.get('name') or a.get('property')] = a.get('content', '')
        if tag == 'link' and a.get('rel') == 'canonical':
            self.canonical.append(a.get('href'))
        if tag in ('a', 'link') and a.get('href'):
            self.links.append(a['href'])
        if tag in ('img', 'script') and a.get('src'):
            self.links.append(a['src'])
        if tag == 'script' and a.get('type') == 'application/ld+json':
            self.in_json, self.json_text = True, ''

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        if tag == 'h1':
            self.in_heading = False
        if tag == 'script' and self.in_json:
            self.json_blocks.append(self.json_text)
            self.in_json = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.in_heading:
            self.heading += data
        if self.in_json:
            self.json_text += data


def site_urls():
    tree = ET.parse(OUT / 'sitemap.xml')
    urls = [e.text for e in tree.findall('.//{*}loc')]
    if not urls or len(set(urls)) != len(urls):
        raise ValueError('Sitemap is empty or contains duplicates')
    return urls


def local_path(url):
    parsed, base = urlsplit(url), urlsplit(SITE)
    if parsed.netloc != base.netloc or not parsed.path.startswith(base.path):
        return None
    relative = unquote(parsed.path[len(base.path):])
    target = (OUT / (relative or 'index.html')).resolve()
    if target.is_dir():
        target /= 'index.html'
    if not target.is_relative_to(OUT.resolve()):
        raise ValueError('Path outside site')
    return target


def metadata(url):
    path = local_path(url)
    source = path.read_text(encoding='utf-8')
    page = Page(source)
    if not page.title.strip() or not page.heading.strip():
        raise ValueError(f'Missing title or heading: {url}')
    description = page.meta.get('description') or f'{page.heading.strip()}。공시성적표의 DART·KRX 기반 공시 자료와 계산 기준을 확인하세요.'
    description = description.replace('。', '. ')
    source = re.sub(r'<link\b[^>]*\brel=[\'"]canonical[\'"][^>]*>', '', source, flags=re.I)
    source = re.sub(r'<meta\b[^>]*\bproperty=[\'"]og:[^\'"]+[\'"][^>]*>', '', source, flags=re.I)
    esc = lambda value: html.escape(value, quote=True)
    tags = f'<link rel="canonical" href="{esc(url)}">'
    if not page.meta.get('description'):
        tags += f'<meta name="description" content="{esc(description)}">'
    for name, value in [('og:title', page.title.strip()), ('og:description', description), ('og:url', url), ('og:type', 'website'), ('og:site_name', '공시성적표'), ('og:locale', 'ko_KR')]:
        tags += f'<meta property="{name}" content="{esc(value)}">'
    source = source.replace('</head>', tags + '</head>', 1)
    path.write_text(source, encoding='utf-8')


def write_source_index():
    days = sorted((p.stem for p in OUT.glob('????-??-??.html')), reverse=True)
    content = '''# 공시성적표

> 한국 상장기업의 공시 이후 가격 수익률과 시장 대비 성과를 누적 집계하는 서비스.

## 범위와 해석
- 대상: 코스피·코스닥의 자사주 소각 및 유상증자 공시. 각 페이지의 집계 범위와 갱신일을 확인할 수 있다.
- 기간: 공시일 종가 기준 1·5·20시장 거래일 후. 공시 시각을 반영한 매매 수익률이나 공시의 인과 효과가 아니다.
- 단위: 가격 수익률은 %, 지수 수익률과의 차이는 %p. 전체 공시 수와 기간별 유효 표본 수는 다르다.
- 출처: 금융감독원 DART와 KRX 자료. 정정·취소·가격 조정과 반복 공시의 한계는 계산 방법 페이지에 설명한다.
- 과거 표본의 관측 결과이며 미래 수익률을 보장하지 않는다.

## 주요 자료
'''
    for label, path in [('사이트 소개', 'about.html'), ('계산 방법과 한계', 'methodology.html'), ('자사주 소각 성적표', 'buyback.html'), ('유상증자 성적표', 'rights.html'), ('종목명·코드 검색', 'stock/index.html'), ('소각 공시별 집계 원자료', 'buyback.json'), ('유상증자 공시별 집계 원자료', 'rights.json'), ('사이트맵', 'sitemap.xml')]:
        content += f'- [{label}]({SITE}{path})\n'
    content += '\n## 최근 일일 자료\n'
    for day in days[:30]:
        content += f'- [{day} 공시·수급]({SITE}{day}.html): 집계 JSON {SITE}{day}.json\n'
    (OUT / 'llms.txt').write_text(content, encoding='utf-8')


def verify():
    urls = site_urls()
    pages, problems = {}, []
    for url in urls:
        path = local_path(url)
        if path is None or not path.exists():
            problems.append(f'Missing sitemap target: {url}')
            continue
        page = Page(path.read_text(encoding='utf-8'))
        pages[path] = page
        if not page.title.strip() or not page.heading.strip() or page.lang != 'ko':
            problems.append(f'Invalid title, heading or language: {url}')
        if page.canonical != [url]:
            problems.append(f'Invalid canonical: {url}')
        for raw in page.json_blocks:
            try:
                json.loads(raw)
            except ValueError:
                problems.append(f'Invalid JSON-LD: {url}')
    for url in urls:
        page = pages.get(local_path(url))
        if page is None:
            continue
        for link in page.links:
            absolute = urljoin(url, link)
            target = local_path(absolute)
            if target is None:
                continue
            if not target.exists():
                problems.append(f'Broken link: {url} -> {link}')
                continue
            fragment = unquote(urlsplit(absolute).fragment)
            if fragment and target.suffix == '.html':
                other = pages.get(target)
                if other is None:
                    other = Page(target.read_text(encoding='utf-8'))
                if fragment not in other.ids:
                    problems.append(f'Broken anchor: {url} -> {link}')
    home = Page((OUT/'index.html').read_text(encoding='utf-8'))
    if not home.meta.get('google-site-verification'):
        problems.append('Google verification tag missing')
    for font in ['neodgm.woff2', 'jetbrains-mono-600.woff2', 'PretendardVariable.woff2', 'neodgm.OFL.txt', 'jetbrains-mono.OFL.txt', 'OFL.txt']:
        if not (OUT/'fonts'/font).is_file():
            problems.append(f'Missing font or license: {font}')
    if problems:
        raise RuntimeError('\n'.join(problems[:30]))
    print(f'Validated {len(urls)} sitemap URLs: internal links, anchors, canonical, JSON-LD and licenses OK')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if not args.check:
        for url in site_urls():
            metadata(url)
        write_source_index()
    verify()


if __name__ == '__main__':
    main()
