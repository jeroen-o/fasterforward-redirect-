"""Genereert de redirect-site voor support.fasterforward.nl.

Invoer:
  redirects.csv        oude URL;nieuwe URL;soort  (export van de migratie)
  bestaande-paden.txt  paden van support-eblinqx-connect.nl (uit de sitemap)
  titels.tsv           doel-URL<TAB>paginatitel (voor linktekst en <title>)
Uitvoer:
  <oud pad>/index.html  per oude URL een statische pagina (HTTP 200) met
                        meta-refresh 0 + canonical, die Google en AI-crawlers
                        als permanente redirect lezen
  404.html              vangnet voor alle overige paden (JavaScript)
  robots.txt, sitemap.xml, llms.txt
Gebruik: python3 maak-redirects.py  (verwijdert eerst alle eerder gegenereerde mappen)
"""
import html, json, os, re, shutil
from urllib.parse import unquote

OUD = 'https://support.fasterforward.nl'
NIEUW = 'https://support-eblinqx-connect.nl'
BEHOUDEN = {'.git'}

def norm(p):
    p = p.lower()
    return p if p.endswith('/') else p + '/'

titels = dict(l.rstrip('\n').split('\t', 1) for l in open('titels.tsv', encoding='utf-8') if '\t' in l)
bestaand = set(norm(l.strip()) for l in open('bestaande-paden.txt', encoding='utf-8') if l.strip())
kaart, pagina = {}, {}
for regel in open('redirects.csv', encoding='utf-8').read().splitlines()[1:]:
    oud, nieuw, _ = regel.split(';')
    p = norm(oud.replace(OUD, '', 1))
    n = re.sub(r'(\?q=[^#]*?)/$', r'\1', nieuw.replace(NIEUW, '', 1))  # "?q=aanmaken/" -> "?q=aanmaken"
    pagina[p] = n
    if p != n.lower():
        kaart[p] = n
    else:
        bestaand.add(p)

def titel(doel):
    if doel.startswith('/zoeken/?q='):
        return f'Zoekresultaten voor “{unquote(doel.split("=", 1)[1])}” - Blinqx Support'
    return titels.get(NIEUW + doel, 'Blinqx Support')

def redirectpagina(doel):
    url, t = html.escape(NIEUW + doel), html.escape(titel(doel))
    # Querystring alleen meegeven als het doel er zelf geen heeft
    js = json.dumps(NIEUW + doel) + ('+location.hash' if '?' in doel else '+location.search+location.hash')
    return f'''<!doctype html>
<html lang="nl">
<meta charset="utf-8">
<title>{t}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="{url}">
<meta http-equiv="refresh" content="0; url={url}">
<script>location.replace({js})</script>
<p>Deze pagina is verhuisd naar <a href="{url}">{t}</a> op support-eblinqx-connect.nl.</p>
</html>
'''

for naam in os.listdir('.'):
    if os.path.isdir(naam) and naam not in BEHOUDEN:
        shutil.rmtree(naam)
for p, doel in pagina.items():
    map_ = p.strip('/')
    if map_:
        os.makedirs(map_, exist_ok=True)
    with open(os.path.join(map_, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(redirectpagina(doel))

def js(o):
    return json.dumps(o, ensure_ascii=False, separators=(',', ':'))

vangnet = f'''<!doctype html>
<html lang="nl">
<meta charset="utf-8">
<title>Blinqx Support is verhuisd naar support-eblinqx-connect.nl</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<script>
// Gegenereerd door maak-redirects.py - niet met de hand aanpassen.
var MAP={js(kaart)};
var BESTAAT=new Set({js(sorted(bestaand))});
function doel(pad){{
  var p=decodeURIComponent(pad).toLowerCase().replace(/\\/?$/,"/");
  p=p.replace(/(\\/(feed|amp|embed|trackback))+\\/$/,"/");   // WordPress-varianten
  var basis=p.replace(/\\/page\\/\\d+\\/$/,"/");               // paginering -> eerste pagina
  if(MAP[p])return MAP[p];
  if(MAP[basis])return MAP[basis];
  if(BESTAAT.has(p))return p;
  if(BESTAAT.has(basis))return basis;
  if(/^\\/(author|wp-admin|wp-login|wp-json)/.test(p))return "/";
  var stukken=basis.split("/").filter(Boolean);
  if(!stukken.length)return "/";
  // Onbekend pad: zoek op het laatste deel van de URL
  return "/zoeken/?q="+encodeURIComponent(stukken[stukken.length-1].replace(/\\.[a-z0-9]+$/,"").replace(/[-_]+/g," "));
}}
var d=doel(location.pathname);
location.replace("{NIEUW}"+d+(d.indexOf("?")<0?location.search:"")+location.hash);
</script>
<noscript><meta http-equiv="refresh" content="0; url={NIEUW}/"></noscript>
<p>Blinqx Support is verhuisd. <a href="{NIEUW}/">Ga naar support-eblinqx-connect.nl</a></p>
</html>
'''
open('404.html', 'w', encoding='utf-8').write(vangnet)

open('robots.txt', 'w').write(f'User-agent: *\nAllow: /\n\nSitemap: {OUD}/sitemap.xml\n')
# Sitemap met de oude URLs, zodat zoekmachines de redirects snel opnieuw crawlen
with open('sitemap.xml', 'w', encoding='utf-8') as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
    for p in sorted(pagina):
        f.write(f'  <url><loc>{html.escape(OUD + p)}</loc></url>\n')
    f.write('</urlset>\n')
open('llms.txt', 'w', encoding='utf-8').write(f'''# Blinqx Support (voorheen Faster Forward support)

> support.fasterforward.nl is verhuisd naar {NIEUW}/. Alle kennisbankartikelen, releasenotes, nieuws en tips staan daar. Oude URLs verwijzen permanent door naar de nieuwe pagina.

- [Blinqx Support]({NIEUW}/): kennisbank, releasenotes en support voor eBlinqx Connect (voorheen Elements)
- [Kennisbank]({NIEUW}/kennisbank/)
- [Zoeken]({NIEUW}/zoeken/)
''')
print(f'{len(pagina)} statische redirects, {len(kaart)} met afwijkend pad, {len(bestaand)} bekende paden')
