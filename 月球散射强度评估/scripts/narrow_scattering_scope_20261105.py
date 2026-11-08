from pathlib import Path
import json,re,runpy
R=Path(__file__).resolve().parents[1]; D=R/'docs/研究设计总册_20261029';p=D/'02_散射模型与参数设计.md';s=p.read_text(encoding='utf-8')
(D/'sources/02_20261105_收敛研究范围前.md').write_text(s,encoding='utf-8')
s=s.replace('最终交付每区的参数表、模型预测与实测对比、接受集合/后验、参数权衡、留出事件预测，以及“考虑地形”相对于“忽略地形”造成的参数偏差。','最终交付每区的散射参数表、模型预测与实测对比、接受集合/后验、参数权衡和留出事件预测。所有候选使用固定的真实地形与选定区域背景，仅改变散射模型参数。')
s=s.replace('## 2. 已核定的旧项目继承基准','## 2. 已核定的旧项目散射参数参照')
s=s.replace('同上 |','背景历史记录，不直接用于新区域 |')
s=s.replace('保留旧复现分支','背景历史记录，不直接用于新区域').replace('复现基准；新区域地下界面另作背景约束','旧记录；新区域采用最可靠区域背景，无可靠结果则用月球平均模型')
s=s.replace('独立均匀低速层分支，不默认叠加随机扰动','仅为旧项目记录；新区域不另设低速层竞争试验')
s=s.replace('生产配置取得后，先按旧耦合复现，再成对测试这一简化，不能静默替换。','正式计算前核定并固定耦合规则；不将耦合方式设为独立科学问题或增加竞争分支。')
s=s.replace('再用统一参考面深度对照','固定采用这一深度定义，不另做参考面比较')
s=s.replace('区域参数相同时另用统一场对照，检查拼接本身是否产生伪散射；','拼接验收属于数值质量检查，不增加物理模型问题；')
s=s.replace('0–1，另检验b>1反例','0–1（项目限定，结论注明这一先验）')
s=s.replace('先固定，后期3/5/7.5离散对照','固定为5；若区域分层有可靠对应界面则预先固定为该值')
s=s.replace('优先继承核实值；可先独立测试0.25/0.5/1新分支','核实旧生产值后固定；不安排多个ν分支')
s=s.replace('0.5连接O22指数参考，其余为项目敏感性，不能冒称旧值','旧值未核齐则保持待定，不猜填或开展谱形竞争')
s=s.replace('新简化分支各向同性；多方位支持后再检验ah/az','固定各向同性，不开展各向异性分支')
s=s.replace('共享/离散干扰分支，不逐条路径自由调Q','每区域预先确定一个背景和吸收设置，整个散射搜索中固定')
s=s.replace('h₁与各向异性后置。','h₁、ν及各向同性固定，不再增加这些竞争分支。')
s=re.sub('不同ν分支若给出不同a、σ，.*?σ增加不保证','ν固定后，各区域结果统一注明其条件性。σ增加不保证',s)
s=s.replace('先核齐最终简单模型的生成器、材料文件、配置及旧波形对应，再复现A16 S-IVB→S12。旧模型的数百秒模拟不能视为已经解释整段长尾波。新参数反演主要采用真实地形；平坦对照用于度量忽略地形的参数偏差。','先核齐旧模型的散射生成规则，同时完成各区域固定背景的选取。旧4.5 km、9%/5%只作为散射参数起点，不将旧简化背景强加给各区域。所有正式候选使用真实LOLA地形，不安排平坦/起伏、无/有低速层或震源机制对比。')
s=s.replace('；另加无散射对照。','。无散射仅可用于求解器的必要数值检查，不纳入本轮科学模型矩阵。')
s=s.replace('同事件所有台站共用源机制/时间函数/幅度参数，LM与S-IVB分源族验证；场地按站组织，背景及吸收按物理模型组织，不每条记录任意调源、Q和增益。','各事件按可追溯依据固定源模型，同事件所有台站共用源参数；场地、背景和吸收在散射搜索前固定，不逐条记录任意调源、Q和增益，也不另设震源/场地模型比较。')
s=s.replace('4. 在新种子、背景、Qi、低速层、ν及可靠处理版本下检查入围解是否稳定。','4. 在固定背景、吸收、ν和处理产品下，用新的随机种子验证散射参数；不开展背景/低速层/吸收的竞争试验，结果明确为给定背景条件下的估计。')
s=s.replace('5. 比较共享参数和分区参数的留出预测；区域自由度增加必须改善独立预测，不能只改善训练拟合。','5. 用未参与拟合的事件验证所选散射参数；有效性检查服务于区域参数估计，不扩展成多问题模型对照。')
s=s.replace('同一地形对照共用母体场','不同散射候选采用统一的固定地形与坐标规则')
intro='''
## 2A. 固定区域背景：可靠区域结果优先，缺失部分使用月球平均模型

本轮只有散射模型矩阵。真实LOLA地形、每事件震源、各区域背景速度/密度/分层和吸收设置在搜索前确定，搜索中保持固定；不再以它们构建多组科学问题。数值收敛、材料统计和随机种子重复仍是必要质量检查，并非额外物理模型族。

### 选择规则

“最可靠”按实际区域覆盖、观测类型、深度/频率适用性、分辨率与不确定性、数据和数值模型是否公开来判断，不简单选最新年份或最复杂模型。优先使用可重建的区域Vp(z)、Vs(z)与界面；只有壳厚或平均速度的论文只约束相应量，不将其扩写成完整剖面。背景界面与散射层底H是不同参数，莫霍深度不等于散射深度。

统一的无区域约束后备选择为[Garcia等2019月球一维模型集合](https://doi.org/10.1007/s11214-019-0613-y)中的M1均值模型，使用作者数值表而非从图上猜读；这是本项目选择的统一平均参考，不声称M1是唯一最优月球模型。其数据入口为[作者模型数据](https://doi.org/10.5281/zenodo.21476963)。正式使用前核对版本、列名、单位、半径/深度、Vp/Vs、密度及可用吸收字段；数值表尚未接入，不填写虚构层表。若采用区域界面修正平均剖面，明确标记为项目构建背景并验证速度/走时一致性，不能宣称论文发表了这条混合剖面。

### 当前已查到的区域依据及采用边界

| 区域 | 已核查的相关研究 | 可用信息 | 背景选择状态 |
|---|---|---|---|
| R12 | Kim2025；Onodera2022；Zhang2026 | Kim提供局地壳厚与平均Vs；Onodera提供匹配相关路径的浅层建模背景；Zhang提供撞击/台站壳厚约束 | 有区域约束，需整理可重建层表；缺失深度段和参数用M1补足，不能仅凭某篇波形拟合把背景称为区域实测 |
| R14 | Zhang2026；既有Apollo区域结构文献 | 应核对S14约束与源侧/站侧分离；Kim2025的主要反演未保留S14 | 在可靠区域数值未核齐前用M1，不能因接近S12就复制S12全部背景 |
| R15 | Kim2025；Zhang2026 | 局地壳厚及平均速度约束，需核对层内结构 | 局地结果只约束明确参数，其余用M1；不照搬S12低速层 |
| R16 | Kim2025；Torrent Duch2025；Zhang2026 | 转换波、干涉反射及走时约束；不同方法的界面解释应先统一 | 尚不宣称某一结果最可靠；对照观测支撑后固定一个背景，缺失项用M1 |

本轮直接检查的[Kim2025](https://doi.org/10.1029/2024GL114506)正文§3给出S12/S15/S16壳厚32.2±6.7、29.4±6、41.1±10.6 km，以及平均Vs 2.6±0.4、2.2±0.3、2.9±0.6 km/s。这些是区域约束，**不是可直接输入CGFD3D的完整Vp/Vs/密度分层表**。

新增核查的[Zhang2026](https://doi.org/10.1029/2025JE009453)使用撞击到时约束源侧和台站侧月壳厚度，其单层壳速度参数化不等于深度细分速度剖面。出版社注明2026-06-13更正，后续提取表格必须使用更正后的版本。该文纳入背景选取，不增加另一套散射模型族。[Torrent Duch2025](https://doi.org/10.1029/2025JE009090)作为S16界面解释的独立参照。

每区最终只交付一个冻结背景文件及来源表：深度顶/底、Vp、Vs、ρ、吸收设置、该行对应文献/页表、直接区域约束或月球平均补足。对部分约束、存在冲突或尚未取得数值的字段保持待核，不能现在声称已完成“最可靠背景”的最终筛选。优先完成背景数值整理，再启动散射搜索；无需先运行多套背景波形进行竞争。

'''
s=s.replace('## 3. 统一数学定义和物理含义',intro+'## 3. 统一数学定义和物理含义')
p.write_text(s,encoding='utf-8')
# Assemble and perform existing checks before applying the narrower machine-readable scope.
runpy.run_path(str(R/'scripts/sync_vk_regional_design_20261105.py'),run_name='__main__')
j=D/'tables/区域冯卡尔曼反演设计_20261105.json';v=json.loads(j.read_text(encoding='utf-8'))
v['scope']='scattering_parameter_models_only';v['new_initial_stage'].pop('nu_sensitivity_branches',None)
v['fixed_inputs']={'topography':'LOLA actual terrain','regional_background_policy':'best justified regional result; unresolved components use Garcia2019 M1 mean','background_numeric_files_ready':False,'nu':'verify legacy production value then fix','source':'fixed per event','attenuation':'fixed before scattering search'}
v['excluded_scientific_comparisons']=['flat_vs_topography','alternate_background_models','alternate_source_mechanisms','low_velocity_layer_on_off','density_coupling_variants','anisotropy_variants','spectral_family_variants']
j.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
import hashlib
a=D/'修订核验_20261105.json';v=json.loads(a.read_text(encoding='utf-8'));v['files'][str(j.relative_to(R))]={'bytes':j.stat().st_size,'sha256':hashlib.sha256(j.read_bytes()).hexdigest()};a.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
assert '平坦对照用于' not in s and '0.25/0.5/1新分支' not in s
print('Scope narrowed; chapter, combined volume and parameter schema synchronized.')
