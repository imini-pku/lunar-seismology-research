from pathlib import Path
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'docs/研究设计总册_20261029'
guide=D/'00_阅读指南与总体方案.md'
t=guide.read_text(encoding='utf-8')
notice='> 2026-11-05修订：第二册已改为分区域三维冯卡尔曼参数反演，以旧最终论文的4.5 km、9%/5%为继承设计基准。下文2026-10-29的0.65 km主模型、十类竞争模型和64/88项计划属于历史设计，不覆盖新版第二册。旧波形与数值状态未在此次重算。\n\n'
if notice not in t:t=t.replace('\n\n','\n\n'+notice,1)
t=t.replace('背景公式、ACF/PSD、a/σ/H、深度/地形、10类模型、源/Q和耦合','旧最终设计核对、统一三维冯卡尔曼、分区域a/σ/H反演、共同先验与可分辨性')
guide.write_text(t,encoding='utf-8')
for name in ['04_CGFD3D模拟与验证流程.md','05_文献依据与论文组织.md']:
 p=D/name;s=p.read_text(encoding='utf-8')
 note='> 2026-11-05版本说明：本册原计划/文献框架保留。新的区域反演目标、三维冯卡尔曼模型和参数范围以[新版第二册](02_散射模型与参数设计.md)为准；旧作业矩阵尚未按新规格重新编排。\n\n'
 if note not in s:s=s.replace('\n\n','\n\n'+note,1)
 p.write_text(s,encoding='utf-8')
order=['00_阅读指南与总体方案.md','01_事件台站与记录图册.md','02_散射模型与参数设计.md','03_波形处理与反演准入.md','04_CGFD3D模拟与验证流程.md','05_文献依据与论文组织.md','附录_Zhang2025数据清洗论文综述.md']
parts=['# 月球散射强度评估：模型设计、观测记录与实施流程完整合订本\n\n2026-11-05局部修订：第二册更新为区域三维冯卡尔曼参数反演；其他数据和历史计算状态保留其原日期。未执行新传播计算。']
for name in order:
 s=(D/name).read_text(encoding='utf-8');parts.append(re.sub(r'^(#{1,5}) ',r'#\1 ',s,flags=re.M))
(D/'月球散射研究设计_完整合订本.md').write_text('\n\n---\n\n'.join(parts),encoding='utf-8')
spec={
 'version':'2026-11-05','status':'DESIGN_ONLY_NOT_PRODUCTION_INPUT','goal':'infer region-specific parameters within 3D von Karman velocity perturbations',
 'legacy_manuscript_design':{'a_km':4.5,'sigma':[0.09,0.05],'reference_layer_boundaries_km':[0,5,10], 'nu':None,'seed':None,'vp_vs_correlation':None,'density_coupling':None,'attenuation_execution_verified':False,'production_file_chain_verified':False},
 'new_initial_stage':{'free_parameters':['a_km','sigma1'],'sigma2_over_sigma1':5/9,'h1_km':5,'H_taper_center_km':10,'taper_width_km':1,'nu':None,'nu_sensitivity_branches':[0.25,0.5,1.0],'isotropic':True,'proposed_vp_vs_common_field':True,'proposed_density_perturbation':False},
 'common_search':{'a_km_bounds':[0.2,6],'a_initial':[0.2,0.65,1.3,2,4.5,6],'sigma1_bounds':[0.01,0.15],'sigma1_initial':[0.03,0.05,0.09,0.12,0.15],'H_stage2_km':[10,15,20,30],'H_conditional_extension_km':[50,80]},
 'regions':[{'id':r,'estimated_parameters':None,'spatial_window':None,'status':'requires data admission and identifiability'} for r in ['R12','R14','R15','R16']],
 'evidence_classes':{'legacy':'confirmed manuscript design, incomplete production chain','search_bounds':'project-designed, not measured regional intervals','predictions':'not executed'}
}
(D/'tables/区域冯卡尔曼反演设计_20261105.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
changed=[D/n for n in order if n.startswith(('00','02','04','05'))]+[D/'月球散射研究设计_完整合订本.md',D/'tables/区域冯卡尔曼反演设计_20261105.json']
checks={str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in changed}
new=(D/'02_散射模型与参数设计.md').read_text(encoding='utf-8')
assert '4.5 km' in new and '9%' in new and '5%' in new
assert new.count('\\[')==new.count('\\]')
assert all(r in new for r in ['R12','R14','R15','R16'])
assert '高斯竞争场' not in new
json.loads((D/'tables/区域冯卡尔曼反演设计_20261105.json').read_text(encoding='utf-8'))
(D/'修订核验_20261105.json').write_text(json.dumps({'status':'DOCUMENT_AND_SCHEMA_CHECKED_ONLY','note':'旧交付核验及SHA清单对应2026-10-29快照；本记录仅覆盖此次文件修订，不验证数值模型或生产结果。','files':checks},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'updated_files':len(changed),'chapter_characters':len(new),'checks':'passed: required fields, math delimiters, JSON, assembled chapter'},ensure_ascii=False))
