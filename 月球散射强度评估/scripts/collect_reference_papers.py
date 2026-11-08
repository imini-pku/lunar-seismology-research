from pathlib import Path
import re,json,concurrent.futures,requests,time,html,ssl
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/参考文献';OUT.mkdir(parents=True,exist_ok=True)
META=OUT/'下载记录';META.mkdir(exist_ok=True)
CA=META/'windows_trusted_ca.pem'
if not CA.exists():
    certs=Path(requests.certs.where()).read_text(encoding='ascii')
    for store in ['ROOT','CA']:
        for cert,encoding,trust in ssl.enum_certificates(store):
            if encoding=='x509_asn' and (trust is True or '1.3.6.1.5.5.7.3.1' in trust):certs+='\n'+ssl.DER_cert_to_PEM_cert(cert)
    CA.write_text(certs,encoding='ascii')
def get(url):
    return requests.get(url,timeout=22,headers={'User-Agent':'ResearchReferenceCollection/1.0'},allow_redirects=True,verify=str(CA))
def inventory():
    found={}
    for p in (ROOT/'docs').rglob('*'):
        if p.suffix not in ['.md','.bib'] or OUT in p.parents:continue
        for d in re.findall(r'10\.\d{4,9}/[A-Za-z0-9._/;-]+',p.read_text(encoding='utf-8',errors='replace')):
            d=d.rstrip(').,;').lower()
            if '\\' in d:continue
            found.setdefault(d,[]).append(str(p.relative_to(ROOT)))
    (META/'doi_inventory.json').write_text(json.dumps(found,ensure_ascii=False,indent=2),encoding='utf-8')
    return found
def meta(item):
    doi,sources=item; cache=META/(re.sub(r'[^\w.-]','_',doi)+'.json')
    if cache.exists():return json.loads(cache.read_text(encoding='utf-8'))
    result={'doi':doi,'cited_in':sorted(set(sources))}
    if doi.startswith(('10.5281/','10.6084/','10.18715/')):
        result['type']='dataset_or_code';cache.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');return result
    try:
        r=get('https://api.crossref.org/works/'+doi);result['crossref_status']=r.status_code
        if r.status_code==200:
            m=r.json()['message'];result['crossref']=m;result['type']=m.get('type')
            result['title']=html.unescape(re.sub('<[^>]+>','',m.get('title',[''])[0]))
            result['author']=m.get('author',[{}])[0].get('family','Unknown')
            result['year']=m.get('published',m.get('issued',{})).get('date-parts',[[None]])[0][0]
    except Exception as e:result['crossref_error']=str(e)
    try:
        r=get('https://api.openalex.org/works/https://doi.org/'+doi);result['openalex_status']=r.status_code
        if r.status_code==200:result['openalex']=r.json()
    except Exception as e:result['openalex_error']=str(e)
    cache.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(doi,result.get('author'),result.get('year'),result.get('title','')[:90],flush=True)
    return result
if __name__=='__main__':
    found=inventory();print('DOI count',len(found),flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex: results=list(ex.map(meta,found.items()))
    (META/'all_metadata.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print('DONE',len(results),flush=True)
