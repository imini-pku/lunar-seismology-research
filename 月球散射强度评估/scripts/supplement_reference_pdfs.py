from download_reference_pdfs import *
EXTRA={
'10.3847/psj/ac87af':['https://ds.iris.edu/data/reports/XA_1969_1977/Nunn_2022_Planet._Sci._J._3_219.pdf'],
'10.1029/2025je009223':['https://d197for5662m48.cloudfront.net/documents/publicationstatus/262736/preprint_pdf/9c7499a47d192e3fb6c11220c8a3ef70.pdf'],
'10.1029/2024je008739':['https://api.repository.cam.ac.uk/server/api/core/bitstreams/2c4ab9c8-34aa-4b8c-967b-a2b57d01dc88/content'],
'10.1029/2026gl122962':['https://essopenarchive.org/doi/pdf/10.22541/essoar.15005265/v1'],
'10.1029/2004je002332':['https://agupubs.onlinelibrary.wiley.com/doi/epdf/10.1029/2004JE002332'],
'lpsc2025-1144':['https://www.hou.usra.edu/meetings/lpsc2025/pdf/1144.pdf']}
def attempt(r):
 r=fill(r); lp=META/(re.sub(r'[^\w.-]','_',r['doi'])+'_download.json')
 result=json.loads(lp.read_text(encoding='utf-8')) if lp.exists() else {k:r.get(k) for k in ['doi','author','year','title','type']}
 result.setdefault('attempts',[])
 for url in EXTRA[r['doi']]:
  try:
   q=get(url);check=validate(q.content,r);result['attempts'].append({'url':url,'status':q.status_code,'bytes':len(q.content)})
   if q.status_code==200 and check and check['identity_verified']:
    p=OUT/filename(r);p.write_bytes(q.content);result.update(status='saved',filename=p.name,source=q.url,bytes=len(q.content),sha256=hashlib.sha256(q.content).hexdigest(),validation=check);break
  except Exception as e:result['attempts'].append({'url':url,'error':str(e)})
 result.setdefault('status','unavailable');lp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(result['status'],r['doi'],flush=True)
if __name__=='__main__':
 rows=[r for r in ROWS if r['doi'] in EXTRA]
 rows.append({'doi':'lpsc2025-1144','author':'Onodera','year':2025,'title':'Lunar Seismic Scattering Caused by Topographic Features and Megaregolith: Case Study at Szilard Crater','type':'conference-abstract'})
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:list(ex.map(attempt,rows))
