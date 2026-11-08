"""Compact, source-transparent per-event plots for the group-meeting deck."""
from pathlib import Path
import csv
import numpy as np
from scipy import signal
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from audit_impact_waveforms_darts import read_sac, ROOT, EVENTS, FIG

plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,'font.size':10})
inventory=list(csv.DictReader((ROOT/'results'/'impact_waveform_inventory.csv').open(encoding='utf-8-sig')))
pairs=list(csv.DictReader((ROOT/'results'/'impact_pairs_literature.csv').open(encoding='utf-8-sig')))
lookup={(r['event_id'],r['station']):r for r in pairs}

for event in EVENTS.values():
    stations=sorted({r['station'] for r in inventory if r['event_id']==event})
    fig,axes=plt.subplots(len(stations),1,figsize=(8,4.5),sharex=True,squeeze=False)
    fig.subplots_adjust(left=.075,right=.985,top=.81,bottom=.23,hspace=.68)
    for ax,station in zip(axes.ravel(),stations):
        alt=station=='S14' and event in ['A16SIVB','A17SIVB','A17LM']
        component='LPX' if alt else 'LPZ'
        row=next(r for r in inventory if r['event_id']==event and r['station']==station and r['component']==component)
        f,_,_,x,_=read_sac(ROOT/row['sac_path'])
        t=f[5]+np.arange(len(x))*f[0]-f[7]
        sos=signal.butter(4,[.3,.9],btype='bandpass',fs=1/f[0],output='sos')
        xf=signal.sosfiltfilt(sos,signal.detrend(x))
        selected=(t>=-300)&(t<=3600);xx=t[selected];yy=xf[selected]
        peak=np.max(abs(yy));yy=yy/(peak if peak else 1)
        width=max(1,len(yy)//2500);n=len(yy)//width*width
        xx=xx[:n].reshape(-1,width).mean(axis=1);yy=yy[:n].reshape(-1,width)
        low=lookup[(event,station)]['nunn2024_clear'].lower()=='false'
        color='#747a83' if low else '#167585'
        ax.fill_between(xx,yy.min(axis=1),yy.max(axis=1),color=color,linewidth=.25)
        ax.axvline(0,color='#252525',lw=.7,ls='--')
        ax.set(xlim=(-300,3600),ylim=(-1.08,1.08),yticks=[0]);ax.grid(axis='x',alpha=.13)
        labels=[f'{event} → {station}  {component}']
        if low:labels.append('文献：低 SNR')
        if alt:labels.append('Z 故障，显示水平分量')
        ax.set_title('  |  '.join(labels),loc='left',fontsize=9,pad=2,color='#575e68' if low else '#243442')
        ax.tick_params(labelsize=9)
        for side in ['top','right']:ax.spines[side].set_visible(False)
    axes.ravel()[-1].set_xlabel('相对 SAC 事件标记 O 的时间 / s',fontsize=10,labelpad=3)
    fig.suptitle(event+'：实际下载的代表记录',fontsize=15,fontweight='bold',y=.975)
    fig.text(.075,.89,'0.3–0.9 Hz 预备显示滤波；各台站均展示',fontsize=10,color='#53616e')
    fig.text(.075,.085,'旧档案振幅逐道峰值归一化，未去仪器响应；显示滤波不等于认证有效频带。',fontsize=9,color='#53616e')
    fig.text(.075,.038,'低 SNR 标签：Nunn et al. (2024)。完整分量、质量标记与原始数据另附。',fontsize=9,color='#53616e')
    fig.savefig(FIG/(event+'_representative_records.png'),dpi=200)
    plt.close(fig)
print('Wrote 9 compact figures containing all 21 event-station pairs.')
