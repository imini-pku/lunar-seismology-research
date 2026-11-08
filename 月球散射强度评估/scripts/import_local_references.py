from pathlib import Path
import json, re, hashlib, shutil, sys
sys.path.insert(0,str(Path(__file__).parent))
from download_reference_pdfs import OUT,META,validate,filename

rows=json.loads((META/'文献状态.json').read_text(encoding='utf8'))
base=Path(r'C:\Users\Administrator\Desktop\起伏月表影响数值模拟\论文文献')
src={
'10.1029/2011je004042':base/'01_月震散射与尾波/Blanchette‐Guertin_Investigation of scattering in lunar seismic coda_JGR_2012.pdf',
'10.1002/2014je004654':base/'01_月震散射与尾波/JGR Planets - 2015 - Blanchette‐Guertin - Modeling seismic energy propagation in highly scattering environments-3.pdf',
'10.1002/2015gl066151':base/'06_数值地震学与随机介质方法/Geophysical Research Letters - 2015 - Blanchette‐Guertin - Effects of lateral variations in megaregolith thickness on.pdf',
'10.1016/j.pepi.2016.11.001':base/'01_月震散射与尾波/Gillet_Scattering_attenuation_profile_Moon_PEPI_2017.pdf',
'10.1016/j.pepi.2011.06.015':base/'03_月球内部结构与月壳模型/Garcia2011.pdf',
'10.6038/cjg20150519':base/'01_月震散射与尾波/上月壳的散射引起月震尾波的数值模拟研究.pdf',
'10.3847/psj/ad83d2':OUT/'Nunn 2024.pdf',
'10.1029/2026gl122962':OUT/'Kim 2026 Locating Moonquakes With Single‐Station Seismology.pdf'}
for doi,path in src.items():
 r=next(x for x in rows if x.get('doi')==doi)
 if doi=='10.1016/j.pepi.2016.11.001':r.update(author='Gillet',year=2017)
 if doi=='10.6038/cjg20150519':r.update(author='Jiang',year=2015,title='上月壳中的散射引起月震尾波的数值模拟研究')
 b=path.read_bytes();check=validate(b,r)
 if not check or not check['identity_verified']:raise ValueError((doi,path,'identity check failed'))
 dest=OUT/filename(r)
 if dest!=path:
  if dest.exists() and dest.read_bytes()!=b:raise RuntimeError(('destination occupied',dest))
  if not dest.exists():shutil.copy2(path,dest)
 lp=META/(re.sub(r'[^\w.-]','_',doi)+'_download.json')
 old=json.loads(lp.read_text(encoding='utf8')) if lp.exists() else {}
 old.update({k:r.get(k) for k in ['doi','author','year','title','type']})
 old.update(status='saved',filename=dest.name,source=str(path),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),validation=check)
 lp.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf8')
 print(doi,check['pages'],dest.name)
