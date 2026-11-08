from pathlib import Path
import sys,json,re,hashlib,csv
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'code'))
import build_individual_cleaning_20261103 as b
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

fits=json.loads((b.RES/'glitch_fits.json').read_text(encoding='utf-8'))
dec=json.loads((b.RES/'reviewed_glitch_decisions.json').read_text(encoding='utf-8'))
selected=[r for r in fits if r['fit_id'] in dec]
fig,axs=plt.subplots(7,2,figsize=(18,20),squeeze=False)
for ax,r in zip(axs.ravel(),selected):
 d=np.load(b.OUT/f"{r['record']}.npz");a,z=r['start_index'],r['stop_index'];t=d['t_ATT_s'][a:z]
 ax.plot(t,d['raw_counts'][a:z],color='#323c48',lw=.9,label='原始 DU')
 ax.plot(t,r['fit'],color='#b34730',lw=.8,ls='--',label='响应模型＋拟合背景')
 ax.plot(t,d['cleaned_counts'][a:z],color='#087c87',lw=.9,label='减除后 DU')
 ax.set_title(f"{r['fit_id']}  |  VR={r['variance_reduction']:.3f}  |  文献目录关联 {len(r['catalogue_matches'])} 条",fontsize=9)
 ax.set(xlabel='相对撞击时刻 / s（ATT）',ylabel='DU');ax.grid(alpha=.15)
axs.ravel()[-1].axis('off');axs.ravel()[0].legend(fontsize=8)
fig.suptitle('13 处接受的局部仪器瞬变减除｜原始、模型与残差复核',fontsize=17)
fig.text(.05,.012,'Zhang 2025 阶跃响应表达式＋Liu 2025 公开目录；本项目拟合与视觉检查。只减去阶跃分量，保留背景；仍需研究人员独立复核。',fontsize=10)
fig.tight_layout(rect=(0,.03,1,.975))
fig.savefig(b.FIG/'已减除13处瞬变_局部复核.png',dpi=150)
fig.savefig(b.FIG/'已减除13处瞬变_局部复核.pdf');plt.close(fig)

r=b.rows('results/individual_cleaning_20261103/spike_corrections.csv')[0]
d=np.load(b.OUT/f"{r['record']}.npz");i=int(r['index']);a,z=i-20,i+21;t=d['t_ATT_s'][a:z]
fig,ax=plt.subplots(figsize=(10,4))
ax.plot(t,d['raw_counts'][a:z],'.-',color='#303f49',label='原始计数')
ax.plot(t,d['cleaned_counts'][a:z],'o--',ms=4,mfc='none',color='#167d85',label='单点位翻转修正')
ax.annotate('790 → 534 DU（差值 256）',xy=(d['t_ATT_s'][i],534),xytext=(d['t_ATT_s'][i]+.5,710),arrowprops={'arrowstyle':'->'},fontsize=10)
ax.set(title=r['record']+'｜唯一接受的单点尖峰修正',xlabel='相对撞击时刻 / s（ATT）',ylabel='DU');ax.grid(alpha=.15);ax.legend();fig.tight_layout()
fig.savefig(b.FIG/'单点尖峰修正_局部复核.png',dpi=150);plt.close(fig)

# Re-read all saved outputs rather than trusting in-memory calculations.
record_checks=[]
for path in sorted(b.OUT.glob('*.npz')):
 d=np.load(path);meta=json.loads(str(d['metadataJSON']));orig=b.load(path.stem)
 checks=dict(record=path.stem,raw_preserved=np.array_equal(d['raw_counts'],orig['raw_counts']),
             gap_preserved=np.array_equal(d['original_gap_mask'],orig['original_gap_mask']),
             time_preserved=np.array_equal(d['t_ATT_s'],orig['t']),
             selected_finite_samples=int(np.isfinite(d['velocity_selected_m_s']).sum()),
             plotted_time_range_contains_all=bool(d['t_ATT_s'].min()>=b.WINDOW[0] and d['t_ATT_s'].max()<=b.WINDOW[1]),
             excluded_stays_missing=bool(np.isnan(d['velocity_selected_m_s'][d['artifact_exclusion_mask']]).all()))
 assert all(checks[k] for k in ['raw_preserved','gap_preserved','time_preserved','plotted_time_range_contains_all','excluded_stays_missing'])
 assert checks['selected_finite_samples']>0
 record_checks.append(checks)
manifest=[]
for p in sorted(b.FIG.glob('*.png')):
 with Image.open(p) as im:
  im.verify()
 with Image.open(p) as im:wh=im.size
 manifest.append(dict(file=str(p.relative_to(ROOT)),width_px=wh[0],height_px=wh[1],bytes=p.stat().st_size,sha256=b.sha(p)))
docpath=ROOT/'docs/15_Apollo逐条清洗与全波形总图_20261103.md'
text=docpath.read_text(encoding='utf-8');links=[]
for s in re.findall(r'\]\(([^)]+)\)',text):
 if s.startswith(('http','mailto:','#')):continue
 p=(docpath.parent/s.split('#')[0]).resolve();links.append(dict(target=s,exists=p.exists()));assert p.exists(),s
assert len(record_checks)==60
b.dump(b.RES/'artifact_validation.json',dict(record_count=len(record_checks),all_record_checks_passed=True,record_checks=record_checks,
     png_manifest=manifest,markdown_local_link_count=len(links),markdown_links_all_exist=True,
     visual_inspection='Full atlas top/middle/bottom and A15LM event sheet inspected; accepted 13 fit windows inspected before subtraction.',
     limitation='File, provenance, and plotting checks do not certify artifact-free or inversion-ready observations.'))
print('validated',len(record_checks),'NPZ',len(manifest),'PNG',len(links),'local links')
