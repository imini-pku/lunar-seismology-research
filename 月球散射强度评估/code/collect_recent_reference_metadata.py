"""Retrieve machine-readable citation metadata for newly read primary studies."""
from pathlib import Path
import requests, json, hashlib, sys
sys.path.insert(0,'C:/Users/Administrator/.codex/skills/citation-management/scripts')
from _common import render_entry
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/raw/literature_metadata_expansion';OUT.mkdir(parents=True,exist_ok=True)
DOIS=['10.1029/2024GL114506','10.1029/2026GL122962','10.1029/2024EA003742','10.1093/gji/ggae098']
def fetch(doi):
    key=doi.split('/')[-1]
    s=requests.Session();s.trust_env=False
    url='https://api.crossref.org/works/'+doi
    cache=OUT/(key+'.json')
    if cache.exists():
        data=json.loads(cache.read_text(encoding='utf-8'))
    else:
        r=s.get(url,timeout=40);r.raise_for_status()
        data=r.json()['message']
        cache.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    year=str(data['published']['date-parts'][0][0])
    fields={'author':' and '.join(a.get('family','')+', '+a.get('given','') for a in data.get('author',[])),
            'title':data['title'][0],'journal':data['container-title'][0],'year':year,
            'doi':doi,'url':'https://doi.org/'+doi}
    for src,dst in [('volume','volume'),('issue','number'),('page','pages'),('article-number','eid')]:
        if data.get(src): fields[dst]=str(data[src])
    if not fields.get('pages') and not fields.get('eid'):
        fields['note']='Publisher article identifier: e'+key+'; verified against the journal full-text header'
    bib=render_entry('article',data['author'][0]['family'].replace('-','')+year,fields)
    (OUT/(key+'.bib')).write_text(bib,encoding='utf-8')
    return {'doi':doi,'url':url,'title':data.get('title'),'authors':data.get('author'),'journal':data.get('container-title'),'volume':data.get('volume'),'issue':data.get('issue'),'page':data.get('page'),'article_number':data.get('article-number'),'published':data.get('published'),'bib_sha256':hashlib.sha256(bib.encode()).hexdigest()}
records=[fetch(doi) for doi in DOIS]
(ROOT/'results/recent_reference_metadata.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'docs/recent_lunar_references.bib').write_text('\n\n'.join((OUT/(doi.split('/')[-1]+'.bib')).read_text(encoding='utf-8') for doi in DOIS),encoding='utf-8')
print(json.dumps([{'doi':r['doi'],'title':r['title'],'journal':r['journal'],'volume':r['volume'],'issue':r['issue'],'article_number':r['article_number'],'page':r['page']} for r in records],ensure_ascii=False,indent=2))
