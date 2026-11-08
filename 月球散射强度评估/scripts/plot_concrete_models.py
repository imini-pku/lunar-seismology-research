from pathlib import Path
import zipfile,io,json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1];D=R/'docs/研究设计总册_20261029';O=D/'assets';T=D/'tables';raw=R/'data/raw/background_models'
plt.rcParams.update({'font.sans-serif':['Microsoft YaHei'],'axes.unicode_minus':False,'font.size':11})
z=zipfile.ZipFile(raw/'Garcia2019_supplement.zip');b=z.read(next(n for n in z.namelist() if n.endswith('/ISSI_MOON_M1.nd')));(raw/'ISSI_MOON_M1.nd').write_bytes(b)
readme=z.read(next(n for n in z.namelist() if n.endswith('/readme.txt')));(raw/'readme.txt').write_bytes(readme)
rows=[]
for line in b.decode().splitlines():
 try:r=[float(x) for x in line.split()]
 except ValueError:continue
 if len(r)==6:rows.append(r)
a=np.array(rows);a=a[a[:,0]<=100];assert np.all(a[:,1]>a[:,2]);np.savetxt(T/'M1_median_0_100km.csv',a,delimiter=',',header='depth_km,Vp_km_s,Vs_km_s,density_g_cm3,Qp,Qs',comments='')
v=zipfile.ZipFile(raw/'Garcia2019_v2.zip');means={}
for name in ['vp','vs']:
 for stat in ['mean','min','max']:
  key=f'M1_{name}_{stat}.dat';bb=v.read(next(n for n in v.namelist() if n.endswith('/'+key)));(raw/key).write_bytes(bb);means[name,stat]=np.loadtxt(io.BytesIO(bb))
np.savetxt(T/'M1_mean_velocity_0_100km.csv',np.column_stack([means['vp','mean'][:11,1],means['vp','mean'][:11,0],means['vs','mean'][:11,0]]),delimiter=',',header='depth_km,Vp_km_s,Vs_km_s',comments='')
fig,ax=plt.subplots(1,3,figsize=(13,6),sharey=True)
for j,key in enumerate(['vp','vs']):
 m=means[key,'mean'];lo=means[key,'min'];hi=means[key,'max'];sel=m[:,1]<=100
 ax[j].fill_betweenx(m[sel,1],np.interp(m[sel,1],lo[:,1],lo[:,0]),np.interp(m[sel,1],hi[:,1],hi[:,0]),color='#68a6c5',alpha=.25,label='均值 ±1标准差（作者表）')
 ax[j].plot(m[sel,0],m[sel,1],color='#0072B2',label='v2 均值')
 ax[j].plot(a[:,j+1],a[:,0],'--',color='#D55E00',label='原 .nd 中位数')
 ax[j].set_xlabel(('Vp' if j==0 else 'Vs')+' (km/s)');ax[j].grid(alpha=.2)
ax[0].set_ylabel('地表以下深度 (km)');ax[0].set_ylim(100,0);ax[0].legend(fontsize=9)
ax[2].plot(a[:,3],a[:,0],color='#D55E00');ax[2].set_xlabel('密度 (g/cm³)');ax[2].set_xlim(3.2,3.8);ax[2].grid(alpha=.2);ax[2].text(.5,.45,'原 .nd 指定密度 3.5 g/cm³\nQp = Qs = 6750\n不是各站局地密度测量',ha='center',transform=ax[2].transAxes,fontsize=10)
fig.suptitle('可核查的月球参考背景：Garcia 2019 / 作者数据 v2');fig.text(.5,.015,'M1无明确莫霍间断；.nd 中50 km mantle标记为软件占位。阴影是背景模型统计，不是随机速度扰动强度。',ha='center',fontsize=10);fig.tight_layout(rect=[0,.055,1,.94]);fig.savefig(O/'具体背景模型_M1.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(1,3,figsize=(13,5.5));stations=['S12','S14','S15','S16'];h=[32.2,np.nan,29.4,41.1];he=[6.7,np.nan,6,10.6];vs=[2.6,np.nan,2.2,2.9];ve=[.4,np.nan,.3,.6]
for j,(val,err,title) in enumerate([(h,he,'局地月壳厚度 (km)'),(vs,ve,'平均月壳 Vs (km/s)')]):
 for i in [0,2,3]:ax[j].errorbar(i,val[i],yerr=err[i],fmt='o',color='#0072B2',capsize=5)
 ax[j].set_xticks(range(4),stations);ax[j].set_xlim(-.5,3.5);ax[j].set_title(title);ax[j].grid(axis='y',alpha=.2);ax[j].text(1,.15,'无该文\n对应结果',ha='center',transform=ax[j].get_xaxis_transform(),fontsize=9)
ax[2].plot([9,9,5,5,0,0],[0,5,5,10,10,20],color='#D55E00',lw=2);ax[2].set_ylim(20,0);ax[2].set_xlim(0,16);ax[2].set_xlabel('相对速度扰动标准差 (%)');ax[2].set_ylabel('平坦参考深度 (km)');ax[2].set_title('旧散射设计起点：a=4.5 km');ax[2].grid(alpha=.2)
fig.suptitle('区域结构约束与散射输入：不是已反演的区域散射结果');fig.text(.5,.02,'左/中：Kim 2025 正文报告均值及±范围；不代表完整分层剖面。右：旧项目输入，层界画为原阶跃定义。',ha='center',fontsize=10);fig.tight_layout(rect=[0,.065,1,.93]);fig.savefig(O/'区域约束与散射参数.png',dpi=180);plt.close(fig)
text='''# 具体背景模型参数与图件

2026-11-05。已获取作者原始数值文件，以下区分完整参考模型、局地观测约束和项目散射输入。未执行传播或区域反演。

## 1. 已取得的完整背景参数

来源：[Garcia2019作者数据v2](https://zenodo.org/records/21476963)。原`.nd`为集合中位数，新`.dat`为集合均值/±1标准差，作者readme已随原文件保存。为避免混合不同统计量，当前完整后备背景选原M1中位数`.nd`；新均值仅单独展示和导出，不与旧密度/Q拼成“作者均值模型”。这是对前版“均值背景”措辞的具体修正。

表中密度和Q为作者文件指定值，不宣称它们全部由独立观测反演。M1连续变化，无明确定义的莫霍；50 km占位标签不得用作各地区域壳厚。节点之间线性插值是本项目实施选择，不人为添加层间跳跃。

| 深度 km | Vp km/s | Vs km/s | 密度 g/cm³ | Qp | Qs |
|---:|---:|---:|---:|---:|---:|
'''
for r in a:
 if r[0]==50 and '| 50 |' in text:continue
 text+='| '+ ' | '.join(f'{x:g}' for x in r)+' |\n'
text+='''
![M1具体剖面](assets/具体背景模型_M1.png)

[完整节点CSV](tables/M1_median_0_100km.csv)；[均值速度CSV](tables/M1_mean_velocity_0_100km.csv)。图只展示上100 km，原始.nd保留全深度；不得以图的100 km截断替代长路径计算域设计。Qp/Qs为P/S波吸收设置，不是散射Q。

## 2. 已有的具体区域约束

[Kim2025](https://doi.org/10.1029/2024GL114506)正文§3（本地PDF第7页，期刊第6页）给出：

| 台站 | 壳厚 km | 平均月壳Vs km/s | 完整局地Vp/Vs/密度层表 |
|---|---|---|---|
| S12 | 32.2±6.7 | 2.6±0.4 | 不能由这两个数唯一确定 |
| S14 | 该文无对应结果 | 该文无对应结果 | 暂用统一后备背景 |
| S15 | 29.4±6.0 | 2.2±0.3 | 不能由这两个数唯一确定 |
| S16 | 41.1±10.6 | 2.9±0.6 | 不能由这两个数唯一确定 |

图中误差按作者正文的±报告值展示，不另命名为95%区间。当前四区域都可以使用上述完整M1作为有来源的后备背景；这不代表四区真实结构相同。S12/S15/S16存在局地约束，尚不能因此宣称已建立最可靠的完整区域剖面。禁止把平均Vs直接填满整个深度，或在M1上任意移动莫霍并称为论文模型。

## 3. 可直接审阅的散射模型输入

统一三维冯卡尔曼。旧起点a=4.5 km，浅0–5 km标准差9%，5–10 km为5%；ν待生产配置核齐后固定。它是搜索起点，不是四区各自最优结果。

首轮a={0.2,0.65,1.3,2,4.5,6} km，σ₁={3,5,9,12,15}%，σ₂=(5/9)σ₁，h₁=5 km，H=10 km，共30种散射参数组合/区域。随后在入围a/σ附近搜索H={10,15,20,30} km。各区用同一范围，观测决定地区差别。所有离散取值的文献动机见第二册；这些范围是项目设计，不是局地区域观测区间。

![区域约束和散射参数](assets/区域约束与散射参数.png)

上述右图画旧阶跃幅度；新模型若采用第二册1 km余弦渐变，H为过渡中心，不应把两者冒称同一离散实现。真实起伏域按对应层界定义深度。随机介质三维切片暂不伪造：ν尚未核定，仅画明确的参数剖面。
'''
(D/'06_具体模型参数与剖面图.md').write_text(text,encoding='utf-8')
print('created 2 figures, 2 CSV tables, model report; source md5',hashlib.md5((raw/'Garcia2019_v2.zip').read_bytes()).hexdigest())
