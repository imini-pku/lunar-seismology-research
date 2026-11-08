"""Download and audit the public JAXA/DARTS artificial-impact SAC collection.

No response removal or physical-amplitude inference is performed. The SAC header
IDE P value is retained as metadata and is not accepted as calibrated-unit proof.
"""
from __future__ import annotations
import concurrent.futures as cf
import csv
import hashlib
import json
import re
import struct
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import requests
from scipy import signal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.build' / 'waveform_dependencies'))
from unlzw3 import unlzw
BASE = 'https://data.darts.isas.jaxa.jp/pub/apollo/ai/sacs/'
RAW = ROOT / 'data' / 'raw' / 'impact_waveforms_darts'
RESULTS = ROOT / 'results'
FIG = ROOT / 'figures' / 'impact_audit'
EVENTS = {'12l':'A12LM','13s':'A13SIVB','14s':'A14SIVB','14l':'A14LM',
          '15s':'A15SIVB','15l':'A15LM','16s':'A16SIVB','17s':'A17SIVB','17l':'A17LM'}
BANDS = [(0.1,0.3),(0.3,0.5),(0.5,0.9),(0.9,1.5),(1.5,2.0)]

def read_sac(path):
    raw = Path(path).read_bytes()
    endian = next((e for e in ['>', '<'] if struct.unpack(e+'i', raw[304:308])[0] in [6,7]), None)
    if endian is None:
        raise ValueError(f'Unknown SAC byte order: {path}')
    f = np.array(struct.unpack(endian+'70f',raw[:280]),dtype=float)
    ints = struct.unpack(endian+'40i',raw[280:440])
    chars = [raw[440+i*8:448+i*8].decode('ascii',errors='replace').strip() for i in range(24)]
    n = ints[9]
    if len(raw) != 632+4*n:
        raise ValueError(f'Unexpected SAC byte count {len(raw)} vs {632+4*n}: {path}')
    values = np.frombuffer(raw[632:],dtype=endian+'f4').astype(float)
    ref = datetime(ints[0],1,1,tzinfo=timezone.utc)+timedelta(days=ints[1]-1,hours=ints[2],minutes=ints[3],seconds=ints[4],milliseconds=ints[5])
    return f, ints, chars, values, ref

def runs(values):
    starts = np.r_[0,np.flatnonzero(values[1:] != values[:-1])+1]
    lengths = np.diff(np.r_[starts,len(values)])
    return starts,lengths

def download(name):
    path=RAW/name
    if not path.exists():
        s=requests.Session();s.trust_env=False
        r=s.get(BASE+name,timeout=60);r.raise_for_status();path.write_bytes(r.content)
    raw=unlzw(path.read_bytes());sac=path.with_suffix('');sac.write_bytes(raw)
    return name,len(raw)

def audit(name):
    sac=(RAW/name).with_suffix('')
    f,ints,c,x,ref=read_sac(sac)
    _,event,sta,component,_=name.split('.')
    dt=f[0]; t=f[5]+np.arange(len(x))*dt-f[7]
    starts,lens=runs(x)
    idx=int(np.argmax(lens)); extrema=(x==np.nanmin(x)) | (x==np.nanmax(x))
    extreme_run=max([int(n) for st,n in zip(starts,lens) if extrema[st]],default=0)
    flags=[]
    if not np.all(np.isfinite(x)): flags.append('nonfinite')
    if np.std(x)==0: flags.append('constant')
    if lens[idx]*dt>=5: flags.append('long_constant_run_ge_5s')
    if extreme_run*dt>=1 or np.mean(extrema)>.02: flags.append('repeated_extreme_or_low_dynamic_range')
    if sta=='12' and component=='spz': flags.append('S12_SP_known_low_gain_unreliable')
    if sta=='14' and component=='lpz' and event in ['16s','17s','17l']: flags.append('S14_LPZ_known_fault_epoch_exclude')
    if component=='spz' and sta=='16': flags.append('S16_SP_thermal_noise_check')
    if f[7]==-12345: flags.append('origin_offset_missing')
    event_time=ref+timedelta(seconds=f[7])
    analysis=(t>=-600)&(t<=3600)
    aruns=[(int(st),int(n)) for st,n in zip(starts,lens) if t[st]<=3600 and t[min(st+n-1,len(t)-1)]>=-600]
    analysis_longest=max([min(t[st+n-1],3600)-max(t[st],-600)+dt for st,n in aruns],default=0)
    analysis_extreme=max([min(t[st+n-1],3600)-max(t[st],-600)+dt for st,n in aruns if extrema[st]],default=0)
    if analysis_longest>=5: flags.append('analysis_window_constant_run_ge_5s')
    if analysis_extreme>=1: flags.append('analysis_window_repeated_extreme_ge_1s')
    row={'event_id':EVENTS[event],'station':'S'+sta,'component':component.upper(),
         'filename':name,'url':BASE+name,'sac_path':str(sac.relative_to(ROOT)),
         'sha256_compressed':hashlib.sha256((RAW/name).read_bytes()).hexdigest(),
         'sha256_sac':hashlib.sha256(sac.read_bytes()).hexdigest(),
         'compressed_bytes':(RAW/name).stat().st_size,'sac_bytes':sac.stat().st_size,
         'sac_byte_order':'big' if struct.unpack('>i',sac.read_bytes()[304:308])[0] in [6,7] else 'little',
         'sac_station':c[0],'sac_event':''.join(c[1:3]),'sac_component':c[20],
         'sac_idep_enum':ints[16],'units_for_this_audit':'archive amplitude; physical units unverified',
         'sampling_rate_hz':1/dt,'delta_s':dt,'npts':len(x),'duration_s':(len(x)-1)*dt,
         'start_utc_header':(ref+timedelta(seconds=f[5])).isoformat(),
         'end_utc_header':(ref+timedelta(seconds=f[5]+(len(x)-1)*dt)).isoformat(),
         'origin_utc_header':event_time.isoformat(),'origin_offset_s':f[7],
         'seconds_before_origin':max(0,-t[0]),'seconds_after_origin':t[-1],
         'sac_station_lat':f[31],'sac_station_lon':f[32],
         'sac_event_lat':f[35],'sac_event_lon':f[36],
         'sac_dist_header':f[50],'sac_gcarc_header':f[53],
         'sac_cmpaz_deg':f[57],'sac_cmpinc_deg':f[58],
         'nonfinite_count':int(np.count_nonzero(~np.isfinite(x))),
         'zero_count':int(np.count_nonzero(x==0)), 'unique_count':len(np.unique(x)),
         'min':np.min(x),'max':np.max(x),'std':np.std(x),
         'longest_constant_run_s':lens[idx]*dt,'longest_constant_run_start_relative_origin_s':t[starts[idx]],
         'longest_extreme_run_s':extreme_run*dt, 'fraction_at_global_extremes':np.mean(extrema),
         'analysis_window_s':'-600:3600','analysis_longest_constant_run_s':analysis_longest,
         'analysis_longest_global_extreme_run_s':analysis_extreme,
         'quality_flags':';'.join(flags),'response_removed':False,'calibrated_band_status':'pending_response_and_epoch_validation'}
    noise=(t>=-600)&(t<=-60); post=(t>=60)&(t<=1800)
    nv=x[noise]; _,nc=np.unique(nv,return_counts=True); _,nr=runs(nv)
    noise_mad=float(np.median(abs(nv-np.median(nv))))
    noise_flags=[]
    if len(nc)<8:noise_flags.append('fewer_than_8_unique_noise_values')
    if nc.max()/len(nv)>=.5:noise_flags.append('noise_mode_fraction_ge_0p5')
    if noise_mad==0:noise_flags.append('noise_MAD_zero')
    if nr.max()*dt>=5:noise_flags.append('noise_constant_run_ge_5s')
    if noise_mad>0 and np.max(abs(nv-np.median(nv)))>20*1.4826*noise_mad:noise_flags.append('noise_large_impulse_vs_MAD')
    noise_reliable=not noise_flags
    screen_usable=noise_reliable and not any('known_fault' in z or 'known_low_gain' in z for z in flags) and analysis_extreme<1
    if not noise_reliable:
        flags.append('noise_window_unreliable_for_automatic_band_validation')
    row.update({'noise_window_actual_s':int(noise.sum())*dt,'signal_window_actual_s':int(post.sum())*dt,
                'noise_unique_count':len(nc),'noise_mode_fraction':nc.max()/len(nv),
                'noise_MAD':noise_mad,'noise_std':float(nv.std()),'noise_zero_fraction':float(np.mean(nv==0)),
                'noise_longest_constant_run_s':nr.max()*dt,'noise_quality_flags':';'.join(noise_flags),
                'noise_window_reliable_for_screen':noise_reliable,'screen_usable':screen_usable,
                'quality_flags':';'.join(flags)})
    bandrows=[]
    if noise.sum()*dt>=120 and post.sum()*dt>=600 and np.isfinite(x).all():
        nperseg=min(1024,noise.sum(),post.sum())
        ff,pn=signal.welch(x[noise],fs=1/dt,nperseg=nperseg,detrend='linear')
        _,ps=signal.welch(x[post],fs=1/dt,nperseg=nperseg,detrend='linear')
        for lo,hi in BANDS:
            sel=(ff>=lo)&(ff<hi);ratio=ps[sel]/np.maximum(pn[sel],np.finfo(float).tiny)
            med=float(np.median(ratio));frac=float(np.mean(ratio>=3))
            passed=med>=3 and frac>=.6
            bandrows.append({'event_id':EVENTS[event],'station':'S'+sta,'component':component.upper(),
                             'fmin_hz':lo,'fmax_hz':hi,'median_signal_to_noise_PSD':med,
                             'fraction_frequency_bins_PSD_ratio_ge_3':frac,'raw_threshold_pass':passed,
                             'screen_usable':screen_usable,'spectral_screen_pass':passed and screen_usable,
                             'physical_band_validated':False,'quality_flags':';'.join(flags),
                             'noise_quality_flags':';'.join(noise_flags),
                             'signal_window_s':'60:1800','noise_window_s':'-600:-60',
                             'note':'PSD(signal+noise)/PSD(noise), uncorrected archive amplitude; quality flags not overridden'})
    else:
        row['quality_flags']+=';insufficient_noise_or_signal_window'
    return row,bandrows,(t,x)

def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8-sig') as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def report(rows, summary, meta):
    lines=['# 人工撞击 SAC 实际下载与组件审计','',
      '审计日期：2026-10-29。数据来自 JAXA DARTS 的 UT Austin 人工撞击事件 SAC 镜像。',
      '',f"已下载 **{meta['compressed_files']} 个压缩文件**并解压核验为 {meta['SAC_files']} 个 SAC；包含 **9 个事件、21 个事件—台站组合、63 条 LP 和 18 条 SP**。这里只认实际文件，台站运行日期未被当作记录存在的证明。",'',
      '## 下载覆盖','',
      '| 撞击事件 | 有档案记录的台站 | LP 文件数 | SP 文件数 |',
      '|---|---|---:|---:|']
    for ev in EVENTS.values():
        rr=[r for r in rows if r['event_id']==ev]
        lines.append(f"| {ev} | {', '.join(sorted(set(r['station'] for r in rr)))} | {sum(r['component'].startswith('LP') for r in rr)} | {sum(r['component']=='SPZ' for r in rr)} |")
    lines += ['', '## 事件—台站具体记录','',
      '| 事件 | 台站 | 实际分量 | LP 时长/min | 分量级频谱初筛前置条件通过数 |',
      '|---|---|---|---:|---:|']
    for s in summary:
        rr=[r for r in rows if r['event_id']==s['event_id'] and r['station']==s['station'] and r['component'].startswith('LP')]
        lines.append(f"| {s['event_id']} | {s['station']} | {s['downloaded_components']} | {min(r['duration_s'] for r in rr)/60:.1f}–{max(r['duration_s'] for r in rr)/60:.1f} | {sum(bool(r['screen_usable']) for r in rr)}/3 |")
    lines += ['', '## 文件级检查和限制','',
      '- 压缩原件、解压 SAC 均保留；每个文件 URL、大小、SHA256、起止时刻、SAC 震源标记、台站与分量、采样率、点数、头坐标及质量指标写入 `results/impact_waveform_inventory.csv`。',
      f"- 全部文件满足 632 字节 SAC 头 + 4×NPTS 的长度关系；全部使用大端格式。非有限值总数：{sum(r['nonfinite_count'] for r in rows)}。无 NaN 不代表无丢失：档案可能采用恒值、保持上一数值或其他填补方式。",
      '- 实测 DELTA 对应 LP 约 6.625259 Hz、SP 约 53.002061 Hz；与标称 6.625/53 Hz 略有区别，原头字段照录，未擅自重采样。',
      '- SAC IDEP 在本集内有 42 条值为 6、39 条值为 7，分别指 IDISP/IVEL。由于完整处理历史、校准增益与单位未核实，图中统一称“档案振幅”，不将其视为已验证的位移/速度，也不直接用新 StationXML 再次去响应。',
      '- 时间零点使用各文件 SAC 的 O 字段；推得 A13SIVB 为 1970-04-15，与 JAXA 说明表中的 April 5 不一致。该表存在日期冲突，应由 NASA 主目录核定。原时间字段没有改写，也未擅自实施约 1.3 s 的 Earth-received / Moon-origin 校正。',
      '- SAC 头的事件坐标只作为原档案证据保留。新版地图与震中距应使用经 NASA 校核的坐标，尤其 A16SIVB，不应覆盖旧 SAC 的原头。',
      '', '## 明确的质量问题','',
      '- S12 SP 通道在任务期间低增益/失效；虽然 6 个事件各有 SP 文件，不能用作有效短周期记录。',
      '- A16SIVB→S14 LPZ 仅 6 个离散振幅值，A17SIVB→S14 LPZ 仅 3 个，A17LM→S14 LPZ 仅 20 个；与已知 S14 MHZ 故障时期一致，排除物理拟合。某故障记录仍可能产生很高频谱比值，故障判定优先。',
      '- A15SIVB→S14 LPY 在事件后约 143–157 s 出现同一全局极值持续约 13.6 s；A17SIVB→S14 LPY 在约 222–242 s 持续约 20.1 s。需排查饱和/阶跃，不可直接拿此段标定包络峰值。',
      '- 多数记录末端有数十至数百秒恒值段。已分别统计全记录和 -600～3600 s 分析窗，避免末端填补自动导致整条早期记录被判无效。',
      '- 事件前噪声常处于粗量化状态。例：A14SIVB→S12 LPZ 的 -600～-60 s 前窗仅 4 个值，众数比例约 82.9%，MAD=0，并有大尖峰；A16SIVB→S12 LPZ 前窗仅 3 个值、众数约 78.3%、MAD=0。这些窗不能自动认证有效频带。',
      '', '## 频带初筛方法与解释','',
      '预备显示滤波统一采用四阶 Butterworth 0.3–0.9 Hz，前后向零相位滤波，先线性去趋势。每条图迹按自己的峰值归一化；因此图用于记录形态与异常检查，不可比较台站间绝对振幅。完整未滤波图另存。',
      '', '频谱初筛使用 Welch PSD：噪声窗 -600～-60 s，信号窗 +60～+1800 s；比较 PSD(signal+noise)/PSD(noise)，对子带 0.1–0.3、0.3–0.5、0.5–0.9、0.9–1.5、1.5–2.0 Hz 保存中位频谱比和比值≥3 的频点比例。原始阈值为中位比≥3且至少60%频点≥3。',
      '', '另设保守的本项目自动筛查前置条件：前窗至少 8 个独特值、众数比例<50%、MAD>0、无≥5 s完全恒值段、峰值偏离≤20×1.4826 MAD；且非已知故障/低增益通道，分析窗无≥1 s重复全局极值。它们是本轮质量警报规则，不是公认的物理有效带判据，也不证明所有被警报记录都毫无科学价值。',
      '', f"81 条档案中，{meta['screen_usable_trace_count']} 条满足本轮自动频谱初筛前置条件。未满足者保留比值但 `screen_usable=false`、`spectral_screen_pass=false`；`raw_threshold_pass` 只记录数值阈值，不能当通过。所有 `physical_band_validated=false`，因为本轮未完成事件时期响应校正及新档案交叉验证。",
      '', '## 文件清单','',
      '- `data/raw/impact_waveforms_darts/`：81 个压缩原件、81 个解压 SAC 和官方目录页面。',
      '- `results/impact_waveform_inventory.csv`：81 行文件级详细审计。',
      '- `results/impact_event_station_download_summary.csv`：21 行事件—台站覆盖摘要。',
      '- `results/impact_waveform_spectral_screen.csv`：405 行分量×子带初筛结果。',
      '- `figures/impact_audit/*_record_overview.png`：9 张事件全分量原始归一化概览。',
      '- `figures/impact_audit/*_LP_filtered_0p3_0p9Hz.png`：9 张事件 LP 滤波概览，含全部 63 条 LP，故障分量仍显示并标注。',
      '- `figures/impact_audit/downloaded_record_coverage.png`：按实际文件统计的 9×4 台站覆盖。',
      '- 复现：系统需 numpy/scipy/matplotlib/requests；仅 Unix compress 解压依赖 unlzw3 安装到项目 `.build/waveform_dependencies`，没有改变系统包。运行 `python code/audit_impact_waveforms_darts.py` 可重算本地审计。',
      '', '## 主要资料','',
      '- [JAXA DARTS Artificial Impact Event Data](https://darts.isas.jaxa.jp/en/datasets/darts:apollo-ai-data/)',
      '- [JAXA 原始 SAC 分发目录](https://data.darts.isas.jaxa.jp/pub/apollo/ai/sacs/)',
      '- [Yamada: The Description of Apollo Seismic Experiments](https://darts.isas.jaxa.jp/missions/apollo/The_Description_of_Apollo_Seismic_Experiments.pdf)',
      '- [Yamada: The Apollo Seismometer Responses](https://darts.isas.jaxa.jp/missions/apollo/The_Apollo_Seismometer_Responses.pdf)',
      '- [SAC 官方格式说明](https://ds.iris.edu/files/sac-manual/manual/file_format.html)',
      '- [Nunn et al. (2022): 新 Apollo PSE 档案与通道故障处理](https://doi.org/10.3847/PSJ/ac87af)',
      '', '本报告完成实际记录下载与初步审计；未将文件存在、频谱阈值通过或统一显示滤波等同于正式可反演记录。']
    (ROOT/'reports'/'impact_waveform_agent.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

def figures(rows, traces):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors={'LPX':'#0072B2','LPY':'#E69F00','LPZ':'#009E73','SPZ':'#CC79A7'}
    for ev in EVENTS.values():
        rr=[r for r in rows if r['event_id']==ev]
        fig,axes=plt.subplots(len(rr),1,figsize=(13,max(4,1.1*len(rr))),sharex=True,layout='constrained')
        axes=np.atleast_1d(axes)
        for ax,row in zip(axes,rr):
            t,x=traces[row['filename']];sel=(t>=-600)&(t<=4200); tt=t[sel]; yy=x[sel]
            yy=yy-np.median(yy); scale=np.max(np.abs(yy));yy=yy/(scale if scale else 1)
            # Min/max rendering preserves impulsive extremes during display reduction.
            width=max(1,len(yy)//3500); n=(len(yy)//width)*width
            if n:
                seg=yy[:n].reshape(-1,width); tx=tt[:n].reshape(-1,width).mean(axis=1)
                ax.fill_between(tx,seg.min(axis=1),seg.max(axis=1),color=colors[row['component']],linewidth=.25)
            else: ax.plot(tt,yy,color=colors[row['component']],lw=.6)
            ax.axvline(0,color='#555555',ls='--',lw=.6);ax.set_ylim(-1.1,1.1);ax.set_yticks([0]);ax.grid(alpha=.15)
            warning=' *' if row['quality_flags'] else ''
            ax.set_ylabel(row['station']+' '+row['component']+warning,rotation=0,ha='right',va='center',fontsize=9)
        axes[-1].set_xlabel('Time relative to SAC origin marker (s)')
        fig.suptitle(ev+' | downloaded records, individually normalized\nNo response removal; * = quality/epoch flag in inventory',fontsize=13)
        fig.savefig(FIG/(ev+'_record_overview.png'),dpi=160)
        plt.close(fig)
        # Identical provisional filter on all LP traces; not a validated usable band.
        lp=[r for r in rr if r['component'].startswith('LP')]
        fig,axes=plt.subplots(len(lp),1,figsize=(13,max(4,1.1*len(lp))),sharex=True,layout='constrained')
        axes=np.atleast_1d(axes)
        for ax,row in zip(axes,lp):
            t,x=traces[row['filename']]
            sos=signal.butter(4,[.3,.9],btype='bandpass',fs=float(row['sampling_rate_hz']),output='sos')
            filt=signal.sosfiltfilt(sos,signal.detrend(x))
            sel=(t>=-600)&(t<=3600);tt=t[sel]; yy=filt[sel]
            scale=np.max(np.abs(yy));yy=yy/(scale if scale else 1)
            width=max(1,len(yy)//3500);n=(len(yy)//width)*width
            seg=yy[:n].reshape(-1,width);tx=tt[:n].reshape(-1,width).mean(axis=1)
            ax.fill_between(tx,seg.min(axis=1),seg.max(axis=1),color=colors[row['component']],linewidth=.25)
            bad='known_fault' in row['quality_flags']
            if bad:
                ax.set_facecolor('#f3e4e4');ax.text(.99,.8,'FAULT EPOCH - DO NOT FIT',transform=ax.transAxes,ha='right',fontsize=8,color='#9d2222')
            elif row['analysis_longest_global_extreme_run_s']>=1:
                ax.text(.99,.8,'REPEATED EXTREMES - CHECK CLIPPING',transform=ax.transAxes,ha='right',fontsize=8,color='#9d2222')
            ax.axvline(0,color='#555555',ls='--',lw=.6);ax.set_ylim(-1.1,1.1);ax.set_yticks([0]);ax.grid(alpha=.15)
            ax.set_ylabel(row['station']+' '+row['component'],rotation=0,ha='right',va='center',fontsize=9)
        axes[-1].set_xlabel('Time relative to SAC origin marker (s)')
        fig.suptitle(ev+' | LP records: provisional 0.3-0.9 Hz filter\nEach trace normalized by own peak; no response correction; flagged channels shown for audit',fontsize=13)
        fig.savefig(FIG/(ev+'_LP_filtered_0p3_0p9Hz.png'),dpi=160);plt.close(fig)
    # Event-station LP coverage: actual files, not operational dates.
    fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
    evs=list(EVENTS.values());stas=['S12','S14','S15','S16'];m=np.zeros((len(evs),4))
    for i,ev in enumerate(evs):
        for j,sta in enumerate(stas):m[i,j]=sum(r['event_id']==ev and r['station']==sta and r['component'].startswith('LP') for r in rows)
    ax.imshow(m,cmap='Blues',vmin=0,vmax=3,aspect='auto')
    for i in range(len(evs)):
        for j in range(4):ax.text(j,i,str(int(m[i,j]))+' LP',ha='center',va='center',color='white' if m[i,j]>1 else '#444')
    ax.set_xticks(range(4),stas);ax.set_yticks(range(len(evs)),evs);ax.set_title('Downloaded LP component coverage (file presence, not final usability)')
    fig.savefig(FIG/'downloaded_record_coverage.png',dpi=180);plt.close(fig)

def main():
    for p in [RAW,RESULTS,FIG]:p.mkdir(parents=True,exist_ok=True)
    idx=RAW/'index.html'
    if not idx.exists():
        s=requests.Session();s.trust_env=False;r=s.get(BASE,timeout=40);r.raise_for_status();idx.write_text(r.text,encoding='utf-8')
    names=re.findall(r'href="(fpsac[^\"]+)"',idx.read_text(encoding='utf-8'))
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        for k,(name,nbytes) in enumerate(pool.map(download,names),1):print(f'{k}/{len(names)} {name} {nbytes}',flush=True)
    rows=[];bands=[];traces={}
    for name in names:
        row,bb,tr=audit(name);rows.append(row);bands.extend(bb);traces[name]=tr
    write_csv(RESULTS/'impact_waveform_inventory.csv',rows)
    write_csv(RESULTS/'impact_waveform_spectral_screen.csv',bands)
    summary=[]
    for ev in EVENTS.values():
        for sta in ['S12','S14','S15','S16']:
            rr=[r for r in rows if r['event_id']==ev and r['station']==sta]
            if rr:
                summary.append({'event_id':ev,'station':sta,'downloaded_components':';'.join(r['component'] for r in rr),
                                'downloaded_file_count':len(rr),'LP_file_count':sum(r['component'].startswith('LP') for r in rr),
                                'minimum_duration_s':min(r['duration_s'] for r in rr),'maximum_duration_s':max(r['duration_s'] for r in rr),
                                'LP_candidate_band_hz':'0.3-0.9; event/component PSD screen required',
                                'response_validated_effective_band':'not_yet_validated',
                                'flags':' | '.join(r['component']+':'+r['quality_flags'] for r in rr if r['quality_flags'])})
    write_csv(RESULTS/'impact_event_station_download_summary.csv',summary)
    meta={'retrieval_date':'2026-10-29','source':BASE,'compressed_files':len(rows),'SAC_files':len(rows),
          'event_station_pairs':len(summary),'events':len(set(r['event_id'] for r in rows)),
          'LP_files':sum(r['component'].startswith('LP') for r in rows),'SP_files':sum(r['component']=='SPZ' for r in rows),
          'raw_downloads_sha256_in':'impact_waveform_inventory.csv','response_removed':False,
          'physical_units_validated':False,'spectral_screen_method':'Welch; -600:-60 s noise, +60:+1800 s signal; median PSD ratio >=3 and at least 60% frequency bins >=3',
          'noise_screen_rules':'Conservative project screening, not a published universal standard: >=8 unique noise values; modal fraction <0.5; MAD>0; no >=5 s exact constant run; peak <=20 times 1.4826*MAD. Failing traces retain PSD numbers but have screen_usable=false and spectral_screen_pass=false.',
          'screen_usable_trace_count':sum(bool(r['screen_usable']) for r in rows),
          'frequency_screen_does_not_prove':'instrument response, calibration, timing, absence of artifact, or usable physical bandwidth'}
    (RESULTS/'impact_waveform_audit_metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    figures(rows,traces)
    report(rows,summary,meta)
    print(json.dumps(meta,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
