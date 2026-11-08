"""Read-only numerical audit of author arrays; no filtering or waveform edits."""
from pathlib import Path
import sys, zipfile, io, hashlib, json, csv
import numpy as np
sys.path.insert(0, str(Path('.build/waveform_dependencies').resolve()))
from scipy.io import loadmat

src = Path(r'C:\Users\Administrator\Downloads\dataset.zip')
out = Path('results/kim2026_audit_20261103'); out.mkdir(parents=True, exist_ok=True)
dest = Path('data/raw/published_waveform_sources/Kim2026'); dest.mkdir(parents=True, exist_ok=True)
old = list(csv.DictReader(open('results/published_waveforms_20261103/逐记录作者处理与频段状态.csv', encoding='utf-8-sig')))
oldpairs = {(r['event'],r['station']) for r in old}
rows=[]; component_rows=[]; arrays={}; hashes={}
with zipfile.ZipFile(src) as z:
    bad=z.testzip()
    names=z.namelist()
    for name in names:
        if name.startswith('dataset/AI/') or name.startswith('dataset/code/') or name.endswith('.txt.txt'):
            if not name.endswith('/'):
                p=dest/Path(name).relative_to('dataset'); p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(z.read(name))
    for name in names:
        if not(name.startswith('dataset/AI/') and name.endswith('_uniform.mat')): continue
        d=loadmat(io.BytesIO(z.read(name)),squeeze_me=True)
        station='S'+name.split('/')[2][2:]; label=name.split('/')[3]
        event='A'+label.split('-')[1]+('LM' if label.startswith('LM') else 'SIVB')
        t=np.asarray(d['time']).ravel(); dt=float(d['dt']); key=event+'_'+station
        a={c:np.asarray(d[c]).ravel() for c in 'ZNE'}; arrays[key]=(t,a)
        row=dict(event=event,station=station,archive_file=name,n=len(t),start_s=float(t[0]),end_s=float(t[-1]),duration_s=float(t[-1]-t[0]),dt_s=dt,Fs_Hz=float(d['Fs']),time_step_max_error=float(np.max(np.abs(np.diff(t)-dt))),in_project=(event,station) in oldpairs,fields=';'.join(k for k in d if not k.startswith('__')))
        rows.append(row)
        for c,v in a.items():
            h=hashlib.sha256(v.tobytes()).hexdigest(); hashes.setdefault(h,[]).append(key+'_'+c)
            component_rows.append(dict(event=event,station=station,component=c,n=len(v),nan=int(np.isnan(v).sum()),nonfinite=int((~np.isfinite(v)).sum()),minus_one=int((v==-1).sum()),zeros=int((v==0).sum()),min=float(np.nanmin(v)),max=float(np.nanmax(v)),mean=float(np.nanmean(v)),std=float(np.nanstd(v)),integer_fraction=float(np.mean(np.isclose(v,np.round(v),atol=1e-10,rtol=0))),sha256=h))
    pol={}
    for name in names:
        if name.startswith('dataset/AI/') and name.endswith('_result.mat'):
            d=loadmat(io.BytesIO(z.read(name)),squeeze_me=True)
            pol[name]={k:{'shape':list(np.shape(v)),'min':float(np.nanmin(v)),'max':float(np.nanmax(v))} for k,v in d.items() if not k.startswith('__') and isinstance(v,np.ndarray) and np.issubdtype(v.dtype,np.number)}
for filename,data in [('waveform_inventory.csv',rows),('component_checks.csv',component_rows)]:
    with open(out/filename,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=data[0].keys()); w.writeheader(); w.writerows(data)
summary={'source':str(src),'size_bytes':src.stat().st_size,'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'zip_crc_error':bad,'zip_entries':len(names),'waveform_pairs':len(rows),'components':len(component_rows),'project_overlap':sum(r['in_project'] for r in rows),'extra_pairs':[[r['event'],r['station']] for r in rows if not r['in_project']],'missing_project_pairs':sorted(oldpairs-{(r['event'],r['station']) for r in rows}),'identical_component_arrays':[v for v in hashes.values() if len(v)>1]}
(out/'archive_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'polarization_inventory.json').write_text(json.dumps(pol,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
for r in rows: print(r['event'],r['station'],r['n'],round(r['start_s'],3),round(r['end_s'],3),r['Fs_Hz'])
print('nonfinite',sum(r['nonfinite'] for r in component_rows))
print('S14 Z', [r for r in component_rows if r['station']=='S14' and r['component']=='Z'])
