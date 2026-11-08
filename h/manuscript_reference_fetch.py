from pathlib import Path
import urllib.request,json,concurrent.futures
P=Path(r'C:\Users\Administrator\Desktop\起伏月表影响数值模拟\投稿文件\完整中文稿_2026-09-12\核查素材')
dois=['10.1093/gji/ggw032','10.1016/j.icarus.2015.07.039','10.1029/2011JE004042','10.1029/2011JF002037','10.1016/j.pepi.2016.11.001','10.3847/PSJ/ad83d2','10.1029/2020JE006406','10.1029/2022JE007558','10.1785/BSSA0650030581','10.1111/j.1365-246x.2006.03113.x','10.1111/j.1365-246x.2012.05472.x','10.1109/TAC.1974.1100705','10.1214/aos/1176344552']
def get(doi):
 try:
  req=urllib.request.Request('https://doi.org/'+doi,headers={'Accept':'application/vnd.citationstyles.csl+json','User-Agent':'ManuscriptReferenceCheck/1.0'})
  with urllib.request.urlopen(req,timeout=30) as r:
   m=json.load(r)
   for k in ('title','container-title'):
    if isinstance(m.get(k),str):m[k]=[m[k]]
   return m
 except Exception as e:return {'DOI':doi,'title':['METADATA UNAVAILABLE'],'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
 rows=list(ex.map(get,dois))
(P/'references_metadata.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
for m in rows:print(m['DOI'],m['title'][0],m.get('published',{}))
