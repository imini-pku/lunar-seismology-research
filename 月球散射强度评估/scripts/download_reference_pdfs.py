from collect_reference_papers import ROOT,OUT,META,get
import requests,json,re,html,concurrent.futures,hashlib,unicodedata
from pathlib import Path
import pymupdf
ROWS=json.loads((META/'all_metadata.json').read_text(encoding='utf-8'))
def norm(s):return re.sub(r'\W','',s.lower())
def filename(r):
    title=' '.join(r['title'].split());title=re.sub(r'[<>:"/\\|?*\x00-\x1f]',' - ',title)
    return f"{r['author']} {r['year']} {title}".strip().rstrip('.')+'.pdf'
def fill(r):
    oa=r.get('openalex',{})
    if not r.get('title') and oa:
        r['title']=oa.get('title');r['year']=oa.get('publication_year');r['author']=oa.get('authorships',[{}])[0].get('author',{}).get('display_name','Unknown').split()[-1];r['type']='journal-article'
    return r
def validate(b,r):
    if not b.startswith(b'%PDF'):return None
    try:
        d=pymupdf.open(stream=b,filetype='pdf');txt=' '.join(p.get_text() for p in list(d)[:2]);nt=norm(txt)
        words=re.findall(r'[a-z]{4,}',r['title'].lower());score=sum(w in txt.lower() for w in words)/max(len(words),1)
        chinese=unicodedata.normalize('NFKC',txt)
        ok=norm(r['doi']) in nt or norm(r['title']) in nt or (score>.8 and norm(r['author']) in nt) or (r['doi']=='10.6038/cjg20150519' and '上月壳中的散射引起月震尾波的数值模拟研究' in chinese and '姜祥华' in chinese)
        return {'pages':len(d),'text_match_score':score,'identity_verified':ok,'first_page':d[0].get_text()[:18000]}
    except Exception:return None
def run(r):
    r=fill(r)
    if r.get('type')=='dataset_or_code':return r
    logpath=META/(re.sub(r'[^\w.-]','_',r['doi'])+'_download.json')
    if logpath.exists():
        prev=json.loads(logpath.read_text(encoding='utf-8'))
        if prev.get('status')=='saved':return prev
    result={k:r.get(k) for k in ['doi','author','year','title','type']};result['attempts']=[]
    def save(b,url):
        check=validate(b,r)
        if check and check['identity_verified']:
            p=OUT/filename(r);p.write_bytes(b);result.update(status='saved',filename=p.name,source=url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),validation=check);return True
        return False
    local=[]
    if r['doi']=='10.1029/2025ea004710':local=list(OUT.glob('*Zhang*pdf'))
    if r['doi']=='10.1029/2022je007558':local=list(OUT.glob('*Onodera*pdf'))
    for p in local:
        if p.exists() and save(p.read_bytes(),str(p)):break
    urls=[]
    for loc in r.get('openalex',{}).get('locations',[]):
        for key in ['pdf_url','landing_page_url']:
            u=loc.get(key)
            if u and u not in urls:urls.append(u)
    for link in r.get('crossref',{}).get('link',[]):
        u=link.get('URL')
        if u and u not in urls:urls.append(u)
    if not urls:urls=['https://doi.org/'+r['doi']]
    # Prefer explicitly returned PDF locations; retain repository landing pages.
    urls.sort(key=lambda u:0 if any(v in u.lower() for v in ['/pdf','.pdf','/document','/download']) else 1)
    if r.get('title'):
        for u in urls[:7]:
            if result.get('status')=='saved':break
            try:
                q=get(u);result['attempts'].append({'url':u,'status':q.status_code,'final_url':q.url,'type':q.headers.get('Content-Type'),'bytes':len(q.content)})
                if q.status_code!=200:continue
                if save(q.content,q.url):break
                if 'html' in q.headers.get('Content-Type',''):
                    from urllib.parse import urljoin
                    from html.parser import HTMLParser
                    extra=[]
                    class Links(HTMLParser):
                        def handle_starttag(self,tag,attrs):
                            a=dict(attrs)
                            if tag=='meta' and a.get('name') in ['citation_pdf_url','eprints.document_url'] and a.get('content'):extra.append(urljoin(q.url,a['content']))
                            if tag=='a' and a.get('href'):
                                href=urljoin(q.url,a['href'])
                                if href.lower().endswith('.pdf') or (href.endswith('/document') and 'hal.' in href):extra.append(href)
                    Links().feed(q.text)
                    for v in list(dict.fromkeys(extra))[:2]:
                        qq=get(v);result['attempts'].append({'url':v,'status':qq.status_code,'bytes':len(qq.content)})
                        if qq.status_code==200 and save(qq.content,qq.url):break
            except Exception as e:result['attempts'].append({'url':u,'error':str(e)})
    result.setdefault('status','unavailable')
    logpath.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(result['status'],result.get('author'),result['doi'],flush=True)
    return result
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:res=list(ex.map(run,ROWS))
    (META/'download_summary.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding='utf-8')
    print('TOTAL saved',sum(r.get('status')=='saved' for r in res),flush=True)
