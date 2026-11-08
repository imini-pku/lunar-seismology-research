from pathlib import Path
import sys, json, re, hashlib, shutil
import pymupdf
sys.path.insert(0,str(Path(__file__).parent))
from download_reference_pdfs import OUT, META, validate, filename

rows=json.loads((META/'文献状态.json').read_text(encoding='utf8'))
missing=[r for r in rows if r.get('type')!='dataset_or_code' and r.get('status')!='saved']
for r in missing:
 if r['doi']=='10.1016/j.pepi.2016.11.001':r['year']=2017
roots=[Path(r'C:\Users\Administrator\Desktop\起伏月表影响数值模拟\论文文献'),Path(r'C:\Users\Administrator\Desktop\组会'),OUT]
files=[]
for root in roots:
 for p in root.rglob('*.pdf'):
  if '下载记录' not in p.parts:files.append(p)
found={}
for p in files:
 try:
  d=pymupdf.open(p)
  if d.is_encrypted or not len(d):continue
  first=' '.join(d[i].get_text() for i in range(min(2,len(d))))
  low=first.lower();n=''.join(re.findall(r'\w',low))
  for r in missing:
   title=r.get('title') or '';terms=re.findall(r'[a-z]{4,}',title.lower())
   if not terms:continue
   score=sum(w in low for w in terms)/len(terms)
   # require title words and author, never match a DOI from references alone
   author=(r.get('author') or '').lower().replace('‐','-')
   a=author in low.replace('‐','-') or author.split('-')[0] in low
   chinese=r['doi']=='10.6038/cjg20150519' and '上月壳中的散射' in first and '姜祥华' in first
   if (score>=.8 and a) or chinese:
    found.setdefault(r['doi'],[]).append({'path':str(p),'pages':len(d),'score':score,'preview':first[:650]})
 except Exception:pass
print(json.dumps(found,ensure_ascii=False,indent=2))
(META/'local_candidates.json').write_text(json.dumps(found,ensure_ascii=False,indent=2),encoding='utf8')
