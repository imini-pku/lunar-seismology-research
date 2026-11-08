"""Retrieve authors' public artifact catalogues; retain event-window subsets."""
from pathlib import Path
import requests,csv,io,json,hashlib,concurrent.futures,zipfile
from datetime import datetime,timedelta,timezone
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/raw/literature/Liu2025_ACC';OUT.mkdir(parents=True,exist_ok=True)
RES=ROOT/'results/individual_cleaning_20261103'
tree=json.loads((RES/'liu2025_repository_tree.json').read_text())
revision=tree['sha'];base=f'https://raw.githubusercontent.com/liuxinigg/lunar_ACC/{revision}/'
events=list(csv.DictReader((ROOT/'results/impact_audit/events_and_domains.csv').open(encoding='utf-8-sig')))
pairs=list(csv.DictReader((ROOT/'results/impact_pairs_literature.csv').open(encoding='utf-8-sig')))
def dt(x):return datetime.fromisoformat(x.replace('Z','+00:00')).replace(tzinfo=None)
windows={e['event_id']:(dt(e['time_earth_received'])-timedelta(seconds=650),dt(e['time_earth_received'])+timedelta(seconds=3650),dt(e['time_earth_received'])) for e in events}
pairset={(r['event_id'],r['station']) for r in pairs}
def one(item):
 path=item['path'];r=requests.get(base+path,timeout=90);r.raise_for_status();content=r.content
 manifest=dict(path=path,url=base+path,bytes=len(content),sha256=hashlib.sha256(content).hexdigest(),revision=revision)
 if path.endswith('.zip'):
  with zipfile.ZipFile(io.BytesIO(content)) as z: data=z.read(next(n for n in z.namelist() if n.endswith('.csv')))
 else:data=content
 if not path.startswith('catalogs/'):
  (OUT/Path(path).name).write_bytes(data);return manifest,[]
 sta=Path(path).name.split('_')[0];found=[]
 for row in csv.DictReader(io.StringIO(data.decode('utf-8-sig'))):
  ts=row.get('Start time','')
  if not ts:continue
  for eid,(a,b,origin) in windows.items():
   if (eid,sta) not in pairset:continue
   if str(a)<=ts<=str(b):
    start=dt(ts);end=dt(row['End time'])
    found.append(dict(row,event_id=eid,station_code=sta,source_catalog=path,
                      start_relative_s=(start-origin).total_seconds(),end_relative_s=(end-origin).total_seconds()))
 manifest['matched_rows']=len(found);print(path,len(content),len(found),flush=True);return manifest,found
items=[x for x in tree['tree'] if x['type']=='blob' and (x['path'].startswith('catalogs/') or x['path'] in ['command_for_calibration.csv','cvtf.README','ACC_template_matching.py'])]
man=[];found=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 for m,f in ex.map(one,items):man.append(m);found+=f
def save(path,rr):
 with path.open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for x in rr for k in x)));w.writeheader();w.writerows(rr)
save(OUT/'event_window_glitch_catalogue.csv',found)
cal=[]
for row in csv.DictReader((OUT/'command_for_calibration.csv').open(encoding='utf-8-sig')):
 sta='S'+row['station'];time=dt(row['date'])
 for eid,(a,b,origin) in windows.items():
  if (eid,sta) in pairset and a<=time<=b:cal.append(dict(row,event_id=eid,station_code=sta,relative_s=(time-origin).total_seconds()))
save(OUT/'event_window_calibration_commands.csv',cal)
(OUT/'acquisition_manifest.json').write_text(json.dumps(dict(revision=revision,files=man,catalogue_matches=len(found),calibration_matches=len(cal)),indent=2),encoding='utf-8')
print('DONE',len(found),'catalogue matches',len(cal),'calibration commands',flush=True)
