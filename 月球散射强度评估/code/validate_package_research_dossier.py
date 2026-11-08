"""Validate the document package and scientific ledger, then create a portable ZIP."""
from pathlib import Path
import csv,json,re,hashlib,zipfile,collections
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'docs/研究设计总册_20261029'
OUT=ROOT/'outputs/综合研究设计_20261029'
OUT.mkdir(exist_ok=True,parents=True)
def rows(name):
 with (FOLDER/'tables'/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def yes(x):return str(x).lower()=='true'
checks={};links=[]
for p in FOLDER.rglob('*.md'):
 s=p.read_text(encoding='utf-8')
 for t in re.findall(r'\]\(([^)]+)\)',s):
  if t.startswith(('http://','https://','mailto:','#')):continue
  t=t.split('#')[0]
  q=(p.parent/t).resolve()
  links.append({'from':p.relative_to(FOLDER).as_posix(),'target':t,'exists':q.exists(),'inside_package':q.is_relative_to(FOLDER.resolve())})
checks['all_local_links_exist']=all(x['exists'] for x in links)
checks['all_local_links_portable']=all(x['inside_package'] for x in links)
checks['no_unfilled_table_placeholders']=not any(re.search(r'<!-- (?!END_)(\w+) -->\s*(?:<!-- END_\1 -->|\n\n)',p.read_text(encoding='utf-8')) for p in FOLDER.glob('*.md'))
images=[]
for p in (FOLDER/'assets').glob('*.png'):
 with Image.open(p) as im:size=im.size;im.verify()
 images.append({'file':p.relative_to(FOLDER).as_posix(),'width':size[0],'height':size[1],'sha256':sha(p)})
checks['72_pngs_decode']=len(images)==72
pairs=rows('pair_record_summary_current.csv'); traces=rows('trace_stage_comparison.csv'); jobs=rows('event_baseline_jobs_v3.csv'); domains=rows('local_simulation_candidates.csv')
refs=rows('reference_catalog.csv');oldbands=rows('impact_modern_band_screen.csv')
checks['9_events_21_pairs']=len(pairs)==21 and len({p['event_id'] for p in pairs})==9
checks['60_components_3_absent']=sum(yes(t['archive_channel_present']) for t in traces)==60 and len(traces)==63
checks['16_literature_clear_5_low']=sum(yes(p['literature_clear']) for p in pairs)==16
checks['station_counts_9_6_4_2']=collections.Counter(p['station'] for p in pairs)=={'S12':9,'S14':6,'S15':4,'S16':2}
checks['64_unique_planned_jobs']=len(jobs)==len({j['run_id'] for j in jobs})==64 and all(j['status']=='planned_not_executed' for j in jobs)
checks['16_first_stage_subset']=sum(yes(j['first_stage']) for j in jobs)==16
checks['8_event_domains']=len(domains)==len({j['event_id'] for j in jobs})==8
targets={(j['event_id'],s) for j in jobs for s in j['target_receivers'].split(';')}
pairidx={(p['event_id'],p['station']):p for p in pairs}
checks['11_recorded_clear_local_targets']=len(targets)==11 and all(k in pairidx and yes(pairidx[k]['literature_clear']) and float(pairidx[k]['distance_recomputed_km'])<400 for k in targets)
aux={(j['event_id'],s) for j in jobs for s in j['auxiliary_receivers'].split(';') if s}
checks['auxiliary_S14_is_explicit']=aux=={('A17SIVB','S14')}
checks['new_baseline_density_control_zero']=all(float(j['density_beta'])==0 for j in jobs)
checks['28_reference_ids']=len(refs)==len({r['id'] for r in refs})==28
checks['189_unqualified_template_rows']=len(rows('qualification_template.csv'))==189 and all(x['qualification_status']=='not_yet_assessed' for x in rows('qualification_template.csv'))
checks['240_historical_band_rows']=len(oldbands)==240 and all(not b['qualified_band'] for b in oldbands)
oldstatus=collections.Counter(b['provisional_record_screen'] for b in oldbands)
summary=json.loads((FOLDER/'sources/summary.json').read_text(encoding='utf-8'))
checks['21_original_archives_hash_unchanged']=len(summary['source_archive_sha256'])==21 and all(sha(ROOT/rel)==expected for rel,expected in summary['source_archive_sha256'].items())

# Inspect internal references in the volume-specific Chinese citation conventions.
allowed={r['id'] for r in refs};unknown=[]
for p in FOLDER.glob('0[2-5]_*.md'):
 for group in re.findall(r'〔([^〕]+)〕',p.read_text(encoding='utf-8')):
  for token in re.findall(r'\b[A-Z]+\d+[A-Z]?\b',group):
   if token not in allowed:unknown.append({'file':p.name,'id':token})
checks['cited_evidence_ids_resolve']=not unknown
report={'date':'2026-10-29','checks':checks,'all_passed':all(checks.values()),'links_checked':len(links),'links':links,'figures':images,'historical_band_status_counts':dict(oldstatus),'manual_visual_review':['new event_station_coverage_matrix after caption fix','new model_reference_profiles after unit fix','LOLA source-station overview','representative raw/processed waveforms'], 'review_scope':'Counts, links, provenance, planned-job scope, decodable images and selected visual inspection. Not a numerical convergence or scientific inversion validation.','propagation_runs_executed':0,'unknown_evidence_ids':unknown,'combined_characters':len((FOLDER/'月球散射研究设计_完整合订本.md').read_text(encoding='utf-8'))}
(FOLDER/'交付核验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if not report['all_passed']:
 print(json.dumps({k:v for k,v in checks.items() if not v},ensure_ascii=False));print('unknown',unknown);print('badlinks',[x for x in links if not x['exists']]);raise SystemExit(1)

contents=[]
for p in sorted(FOLDER.rglob('*')):
 if p.is_file() and p.name!='文件清单_SHA256.json':contents.append({'path':p.relative_to(FOLDER).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
(FOLDER/'文件清单_SHA256.json').write_text(json.dumps(contents,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
zip_path=OUT/'月球散射研究设计_完整文档与图表.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(FOLDER.rglob('*')):
  if p.is_file():z.write(p,arcname=p.relative_to(FOLDER).as_posix())
with zipfile.ZipFile(zip_path) as z:
 assert z.testzip() is None
 for item in contents:assert hashlib.sha256(z.read(item['path'])).hexdigest()==item['sha256']
delivery={'zip':str(zip_path),'bytes':zip_path.stat().st_size,'sha256':sha(zip_path),'content_files':len(contents),'manifest_files':1,'local_links_verified':len(links),'png_count':len(images),'validation_passed':True,'zip_crc_verified':True,'all_archived_sha256_verified':True}
(OUT/'package_validation.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'阅读说明.md').write_text('# 完整研究设计交付\n\n解压ZIP并保留目录关系，先打开`00_阅读指南与总体方案.md`，或直接阅读`月球散射研究设计_完整合订本.md`。五份专题册可分别使用；图件在assets，明细和计划在tables。\n\n该包为设计与证据阅读包，不含原始MiniSEED/SAC、派生NPZ、大幅DEM、CGFD3D程序或生产配置。科学模型、待执行计划与已核实数据已分别标注。\n\n全包CRC和逐文件SHA-256已核验；详见package_validation.json。\n',encoding='utf-8')
print(json.dumps(delivery,ensure_ascii=False,indent=2))
