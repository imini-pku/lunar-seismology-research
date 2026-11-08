"""Plot author arrays unchanged; full data and explicitly windowed detail."""
from pathlib import Path
import csv,json,hashlib
import numpy as np
from scipy.io import loadmat
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image

root=Path(__file__).resolve().parents[1]
out=root/'figures/kim2026_author_waveforms_20261103';out.mkdir(parents=True,exist_ok=True)
rows=list(csv.DictReader(open(root/'results/kim2026_audit_20261103/waveform_inventory.csv',encoding='utf-8-sig')))
events=['A12LM','A13SIVB','A14SIVB','A14LM','A15SIVB','A15LM','A16SIVB','A17SIVB','A17LM']
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Microsoft YaHei','DejaVu Sans'],'axes.unicode_minus':False,'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'path.simplify':False,'pdf.fonttype':42})
manifest=[]
pdfpath=out/'Kim2026_作者存储波形_18页.pdf'
with PdfPages(pdfpath) as pdf:
    for event in events:
        group=sorted([r for r in rows if r['event']==event],key=lambda r:r['station'])
        data=[]
        for r in group:
            path=root/'data/raw/published_waveform_sources/Kim2026'/Path(r['archive_file']).relative_to('dataset')
            d=loadmat(path,squeeze_me=True);data.append((r,d,path))
        for view in ['full','detail']:
            nr=len(group);fig,axes=plt.subplots(nr,3,figsize=(16,3.0*nr+2.0),squeeze=False)
            fig.subplots_adjust(left=.065,right=.985,bottom=.23 if nr==1 else .12,top=1-1.05/(3*nr+2),hspace=.57,wspace=.26)
            label='全时段' if view=='full' else '局部：−60 至 600 s'
            fig.suptitle(f'Kim 2026  |  {event}  |  作者存储波形 · {label}',fontsize=18,y=.98,fontweight='bold')
            fig.text(.5,1-.57/(3*nr+2),'不新增滤波、去均值、去趋势或归一化  ·  纵轴分别缩放，比较振幅请读刻度',ha='center',fontsize=10,color='#444444')
            xmin=min(float(r['start_s']) for r in group) if view=='full' else -60
            xmax=max(float(r['end_s']) for r in group) if view=='full' else 600
            for i,(r,d,path) in enumerate(data):
                t=np.asarray(d['time']).ravel()
                sel=np.ones(len(t),dtype=bool) if view=='full' else (t>=xmin)&(t<=xmax)
                for j,c in enumerate('ZNE'):
                    ax=axes[i,j];v=np.asarray(d[c]).ravel()
                    warn=''
                    if r['in_project']=='False':warn='标签时间冲突 · 暂不采用'
                    elif r['station']=='S14' and event in ['A16SIVB','A17SIVB','A17LM'] and c=='Z':warn='Z 通道来源待核实'
                    color=['#17658D','#8B4C13','#5F4B8B'][j]
                    line,=ax.plot(t[sel],v[sel],color=color,lw=.5,rasterized=True)
                    assert np.array_equal(line.get_ydata(),v[sel],equal_nan=True)
                    assert np.array_equal(line.get_xdata(),t[sel],equal_nan=True)
                    ax.axvline(0,color='#444444',ls='--',lw=.8,alpha=.7)
                    ax.set_xlim(xmin,xmax);ax.set_ylabel('振幅（DU）');ax.set_xlabel('作者相对时间 / s')
                    ax.ticklabel_format(axis='both',style='plain',useOffset=False)
                    ax.grid(alpha=.16)
                    ax.set_title(f"{r['station']} · {c}"+(f'  |  {warn}' if warn else ''),loc='left',fontsize=10,color='#A13D12' if warn else '#222222',pad=9)
                    if warn:ax.set_facecolor('#FFF8EE')
                    if view=='full':
                        if t[0]>xmin:ax.axvspan(xmin,t[0],color='#eeeeee',zorder=-1)
                        if t[-1]<xmax:ax.axvspan(t[-1],xmax,color='#eeeeee',zorder=-1)
                    ax.margins(y=.08)
                    manifest.append({'event':event,'station':r['station'],'component':c,'view':view,'n_plotted':int(sel.sum()),'source':str(path.relative_to(root)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'warning':warn,'transformations':'none; detail selects -60 <= time <= 600','ylim':list(ax.get_ylim())})
            footer='来源：Kim et al. (2026) · Figshare 10.6084/m9.figshare.32814290 · _uniform.mat · 10 Hz\n时间零点 / UTC 尚待独立核验；Z/N/E 沿用作者变量名。灰区表示文件未覆盖，数组没有提供原始缺样掩码。'
            if event=='A17SIVB':footer+='  本包缺少 S16。'
            fig.text(.065,.025,footer,fontsize=9,color='#444444',va='bottom')
            name=f'{event}_{view}.png';fig.savefig(out/name,dpi=160,facecolor='white');pdf.savefig(fig,dpi=160,facecolor='white');plt.close(fig)
            with Image.open(out/name) as im:im.verify()
            print(name,flush=True)
(out/'plot_manifest.json').write_text(json.dumps({'matplotlib':matplotlib.__version__,'panels':manifest,'source_arrays_unchanged':True,'pdf_pages':18},ensure_ascii=False,indent=2),encoding='utf-8')
doc=['# Kim 2026 作者存储波形图册','', '绘图日期：2026-11-03。9 次人工撞击，22 个作者标注的事件—台站组合，66 个分量。每个事件提供全时段和局部图，共 18 张。','', '**这里展示作者发布的 `_uniform.mat` 数值，不是原始归档波形，也不是新清洗的结果。没有新增滤波、去均值、去响应、归一化或降采样。局部图仅选择 −60 至 600 s；纵轴按当前面板数据分别缩放。**','', '来源：[Kim 2026 数据集](https://doi.org/10.6084/m9.figshare.32814290)。[完整核验报告](18_Kim2026数据包实际核验_20261103.md)。','', '[下载或翻阅 18 页 PDF](../figures/kim2026_author_waveforms_20261103/Kim2026_作者存储波形_18页.pdf)。','', '橙色标题及浅色底纹表示身份或通道疑点；保留这些文件供核对，不作为已确认有效观测。作者未提供原始缺样掩码，图中连续线不代表每点均为真实实测。时间零点尚未独立核对，不能把虚线自动理解为已核验的撞击时刻。','']
for e in events:
    doc += [f'## {e}','',f'![{e} 全时段三分量波形](../figures/kim2026_author_waveforms_20261103/{e}_full.png)','',f'![{e} 局部三分量波形，作者相对时间负60至600秒](../figures/kim2026_author_waveforms_20261103/{e}_detail.png)','']
(root/'docs/19_Kim2026作者波形图册_20261103.md').write_text('\n'.join(doc),encoding='utf-8')
print('COMPLETE',len(manifest),'panels',pdfpath)
