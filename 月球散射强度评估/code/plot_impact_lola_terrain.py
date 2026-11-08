"""Verified native LOLA LDEM_64 terrain for the audited Apollo impact domains.

Downloads only a contiguous latitude strip of the official PDS image using checked
HTTP byte ranges, then crops longitudes without resampling. Does not use the old
oversize float IMG. Heights are DN * 0.5 m relative to a 1737.4 km sphere.
"""
from pathlib import Path
import argparse, csv, hashlib, json, math, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import colors, cm
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
from matplotlib.colors import LightSource

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/lola_impact_64'; RAW.mkdir(parents=True, exist_ok=True)
OUT = ROOT / 'results/impact_terrain'; OUT.mkdir(parents=True, exist_ok=True)
FIG = ROOT / 'figures/impact_terrain'; FIG.mkdir(parents=True, exist_ok=True)
URL = 'https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldem_64.img'
PPD = 64; NX = 23040; NY = 11520; RECORD_BYTES = NX * 2
TOTAL = NX * NY * 2
# Exact native pixel edges; include generous margins around every existing domain.
WEST, EAST, SOUTH, NORTH = -38, 40, -18, 40
FIRST_ROW = int((90-NORTH)*PPD); STOP_ROW = int((90-SOUTH)*PPD)
BAND = RAW / 'ldem_64_lat40N_18S_native_int16.img'
CROP = RAW / 'ldem_64_W38_E40_S18_N40_native.npz'
META = OUT / 'lola_data_provenance.json'
NORM = colors.TwoSlopeNorm(vmin=-5, vcenter=0, vmax=5)
CMAP = plt.get_cmap('terrain')

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8*1024*1024), b''): h.update(b)
    return h.hexdigest()

def rows(name):
    with (ROOT/'results/impact_audit'/name).open(encoding='utf-8-sig') as f:
        data = list(csv.DictReader(f))
    for d in data:
        for k in ['lat','lon','west_degE','east_degE','south_degN','north_degN',
                  'width_at_midlat_km','height_km','distance_km']:
            if k in d: d[k] = float(d[k])
    return data

EVENTS = rows('events_and_domains.csv')
STATIONS = {s['station']:s for s in rows('stations.csv')}
PAIRS = rows('event_station_domains.csv')
LOCAL = {d['event_id']:d for d in rows('local_simulation_candidates.csv')}

def download():
    label = requests.get(URL.replace('.img','.lbl'), timeout=60)
    label.raise_for_status()
    (RAW/'ldem_64.lbl').write_bytes(label.content)
    txt = label.text
    assert 'LSB_INTEGER' in txt and 'SCALING_FACTOR        = 0.5' in txt
    assert 'LINES                 = 11520' in txt and 'LINE_SAMPLES          = 23040' in txt
    nbytes = (STOP_ROW-FIRST_ROW)*RECORD_BYTES
    chunks = []
    size = 8*1024*1024
    start = FIRST_ROW*RECORD_BYTES
    for i, a in enumerate(range(start, start+nbytes, size)):
        chunks.append((i,a,min(a+size,start+nbytes)-1))
    logs = []
    if not (BAND.exists() and BAND.stat().st_size == nbytes):
        def get(chunk):
            i,a,b = chunk
            for attempt in range(4):
                try:
                    r = requests.get(URL, headers={'Range':f'bytes={a}-{b}'}, timeout=120)
                    r.raise_for_status()
                    assert r.status_code == 206
                    assert r.headers.get('Content-Range') == f'bytes {a}-{b}/{TOTAL}', r.headers
                    assert len(r.content) == b-a+1
                    return i,a,r.content,dict(r.headers)
                except Exception:
                    if attempt == 3: raise
                    time.sleep(2+attempt)
        partial = BAND.with_suffix('.partial')
        with partial.open('wb') as f: f.truncate(nbytes)
        with ThreadPoolExecutor(max_workers=4) as pool:
            futs = [pool.submit(get,c) for c in chunks]
            for f in as_completed(futs):
                i,a,data,headers = f.result()
                with partial.open('r+b') as dest: dest.seek(a-start); dest.write(data)
                logs.append({'chunk':i,'content_range':headers['Content-Range'],
                             'bytes':len(data),'etag':headers.get('ETag'),
                             'sha256':hashlib.sha256(data).hexdigest()})
                print(f'LOLA chunk {len(logs)}/{len(chunks)} checked', flush=True)
        partial.replace(BAND)
    elif META.exists():
        logs = json.loads(META.read_text(encoding='utf8')).get('http_range_checks', [])
    z = np.memmap(BAND,dtype='<i2',mode='r',shape=(STOP_ROW-FIRST_ROW,NX))
    indices = np.concatenate([np.arange(int((360+WEST)*PPD),NX), np.arange(int(EAST*PPD))])
    native = np.asarray(z[:,indices])
    lon = WEST + (np.arange(native.shape[1])+.5)/PPD
    lat = NORTH - (np.arange(native.shape[0])+.5)/PPD
    assert native.min() >= -18251 and native.max() <= 21546
    np.savez_compressed(CROP,dn=native,longitude_degE=lon,latitude_degN=lat,
                        height_scale_m=np.array(.5),reference_radius_m=np.array(1737400.))
    old=ROOT/'data/raw/dem/ldem_64_float.img'
    metadata={
        'accessed':'2026-10-29','source_url':URL,'label_url':URL.replace('.img','.lbl'),
        'product':'LDEM_64','version':'V3.1','creation_date':'2019-03-15',
        'original_full_shape':[NY,NX],'expected_full_bytes':TOTAL,
        'download_is':'native full-longitude latitude strip, not full global IMG',
        'first_global_row_zero_based':FIRST_ROW,'stop_global_row_exclusive':STOP_ROW,
        'byte_range_inclusive':[FIRST_ROW*RECORD_BYTES, STOP_ROW*RECORD_BYTES-1],
        'downloaded_bytes':BAND.stat().st_size,'download_sha256':sha(BAND),
        'label_sha256':sha(RAW/'ldem_64.lbl'),'crop_sha256':sha(CROP),
        'crop_shape':list(native.shape),'crop_edges_degE_degN':[WEST,EAST,SOUTH,NORTH],
        'pixel_registration':'pixel centres; first global centre lon=0.0078125 E, lat=89.9921875 N',
        'input_longitude':'0 to 360, east positive','output_longitude':'-180 to 180, east positive; native columns concatenated at 0 E',
        'coordinate_frame':'Mean Earth/Polar Axis of DE421','sample_type':'little-endian signed int16',
        'height_conversion':'height_m = DN * 0.5; radius_m = height_m + 1737400',
        'native_grid_pixels_per_degree':PPD,'native_spacing_km_NS':math.pi*1737.4/180/PPD,
        'native_spacing_EW':'NS spacing * cos(latitude); ~0.474 km at equator',
        'native_height_min_max_m':[float(native.min()*.5),float(native.max()*.5)],
        'interpolation':'none in extraction; nearest-neighbour image rendering; no inferred sub-grid terrain',
        'product_caveat':'LOLA GDR is a gridded altimetry product; producer uses surface interpolation for coverage gaps; possible latitude-band artifacts described in label',
        'old_float_img':{'path':str(old.relative_to(ROOT)),'actual_bytes':old.stat().st_size,
                         'expected_bytes':NY*NX*4,'status':'REJECTED_SIZE_MISMATCH_NOT_USED'},
        'http_range_checks':sorted(logs,key=lambda x:x['chunk']),
        'geometry_input_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [
            ROOT/'results/impact_audit/events_and_domains.csv', ROOT/'results/impact_audit/event_station_domains.csv',
            ROOT/'results/impact_audit/stations.csv', ROOT/'results/impact_audit/local_simulation_candidates.csv']}}
    META.write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf8')
    print('Verified native crop',native.shape, metadata['native_height_min_max_m'],flush=True)

def arc(e,s):
    def xyz(lat,lon):
        p,l=np.deg2rad([lat,lon]); return np.array([np.cos(p)*np.cos(l),np.cos(p)*np.sin(l),np.sin(p)])
    a=xyz(e['lat'],e['lon']); b=xyz(s['lat'],s['lon']); w=np.arccos(np.clip(a@b,-1,1))
    t=np.linspace(0,1,201); q=(np.sin((1-t)*w)[:,None]*a+np.sin(t*w)[:,None]*b)/np.sin(w)
    return np.rad2deg(np.arctan2(q[:,1],q[:,0])),np.rad2deg(np.arcsin(q[:,2]))

def load_dem():
    d=np.load(CROP); return d['dn'].astype('f4')*.0005,d['longitude_degE'],d['latitude_degN']

def terrain(ax,bounds,dem):
    z,lon,lat=dem; w,e,s,n=bounds
    js=np.where((lon>=w-.02)&(lon<=e+.02))[0]; ii=np.where((lat>=s-.02)&(lat<=n+.02))[0]
    a=z[ii[0]:ii[-1]+1,js[0]:js[-1]+1]
    dx=math.pi*1737.4/180/PPD*np.cos(np.deg2rad((n+s)/2)); dy=math.pi*1737.4/180/PPD
    # Light is purely visual; no vertical exaggeration or data modification.
    shade=LightSource(azdeg=315,altdeg=45).hillshade(a,vert_exag=1,dx=dx,dy=dy)
    rgb=CMAP(NORM(a)); rgb[...,:3] *= (.65+.35*shade)[...,None]
    extent=[lon[js[0]]-.5/PPD,lon[js[-1]]+.5/PPD,lat[ii[-1]]-.5/PPD,lat[ii[0]]+.5/PPD]
    ax.imshow(rgb,extent=extent,origin='upper',interpolation='nearest',rasterized=True,zorder=0)
    ax.set_xlim(w,e);ax.set_ylim(s,n);ax.set_aspect(1/np.cos(np.deg2rad((s+n)/2)))
    ax.set_xlabel('东经 / °E');ax.set_ylabel('北纬 / °N')
    ax.grid(color='white',alpha=.23,lw=.5)

def box(ax,d,kind='all',lw=2.2):
    # Solid blue and dashed orange remain distinguishable in monochrome.
    ax.add_patch(Rectangle((d['west_degE'],d['south_degN']),d['east_degE']-d['west_degE'],
        d['north_degN']-d['south_degN'],fill=False,ec='#0072b2' if kind=='all' else '#d55e00',
        lw=lw,ls='-' if kind=='all' else (0,(5,2)),zorder=5))

def legend_handles():
    return [Line2D([],[],marker='*',ms=12,color='none',markerfacecolor='#e41a1c',markeredgecolor='white',label='撞击位置'),
      Line2D([],[],marker='^',ms=9,color='none',markerfacecolor='#161616',markeredgecolor='white',label='有记录台站'),
      Line2D([],[],color='#242424',lw=1.4,label='文献清晰路径'),
      Line2D([],[],color='#242424',lw=1.4,ls='--',label='低信噪比路径 / 台站 *'),
      Line2D([],[],color='#0072b2',lw=2,label='全部记录覆盖框'),
      Line2D([],[],color='#d55e00',lw=2,ls='--',label='近距模拟候选框')]

def event_overlay(ax,e,local_only=False,small=False):
    pairs=[p for p in PAIRS if p['event_id']==e['event_id']]
    if local_only: pairs=[p for p in pairs if p['station'] in LOCAL[e['event_id']]['receivers'].split(';')]
    for p in pairs:
        s=STATIONS[p['station']]; x,y=arc(e,s); clear=p['nunn2024_clear']=='True'
        ax.plot(x,y,color='#252525',lw=1.6 if not small else 1.1,ls='-' if clear else '--',zorder=3,
                path_effects=[])
        ax.scatter(s['lon'],s['lat'],marker='^',s=95 if not small else 60,c='#171717',edgecolors='white',lw=1,zorder=7)
        label=p['station']+('' if clear else ' *')
        ax.annotate(label,(s['lon'],s['lat']),xytext=(6,-13),textcoords='offset points',fontsize=10 if not small else 8,
                    bbox=dict(fc='white',ec='none',alpha=.82,pad=1.5),zorder=8)
    ax.scatter(e['lon'],e['lat'],marker='*',s=220 if not small else 140,c='#d91f26',edgecolors='white',lw=.8,zorder=8)
    right_edge=e['event_id'] in ['A15SIVB','A17SIVB','A17LM']
    ax.annotate(e['event_id'],(e['lon'],e['lat']),xytext=(-7,10) if right_edge else (7,10),
                ha='right' if right_edge else 'left',textcoords='offset points',fontsize=10 if not small else 8,
                color='#7d1014',weight='bold',bbox=dict(fc='white',ec='none',alpha=.84,pad=2),zorder=9)

def limits(d):
    dx=d['east_degE']-d['west_degE']; dy=d['north_degN']-d['south_degN']
    return d['west_degE']-max(.5,dx*.075),d['east_degE']+max(.5,dx*.075),d['south_degN']-max(.5,dy*.075),d['north_degN']+max(.5,dy*.075)

def cbar(fig,axes,shrink=.85):
    cb=fig.colorbar(cm.ScalarMappable(norm=NORM,cmap=CMAP),ax=axes,shrink=shrink,pad=.025)
    cb.set_label('高程 / km（相对 1737.4 km 参考球）');cb.set_ticks([-5,-2.5,0,2.5,5])

def footer(fig):
    fig.text(.5,.032,'LOLA LDEM_64 V3.1｜64 像元/度，原生约 474 m（赤道）｜颜色=高程；轻阴影仅辅助辨识起伏',ha='center',fontsize=9)
    fig.text(.5,.012,'蓝框包含全部有记录台站；橙虚线框仅含 <400 km 且文献清晰路径。均外加 50 km 规划缓冲，尚非收敛验证后的计算边界。',ha='center',fontsize=8)

def save(fig,name):
    fig.savefig(FIG/(name+'.png'),dpi=180,facecolor='white')
    fig.savefig(FIG/(name+'.pdf'),dpi=180,facecolor='white')
    plt.close(fig)

def make_plots():
    plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','DejaVu Sans'],'axes.unicode_minus':False,
                        'font.size':11,'pdf.fonttype':42,'ps.fonttype':42})
    dem=load_dem()
    for e in EVENTS:
        fig,ax=plt.subplots(figsize=(11.5,8.5));fig.subplots_adjust(left=.08,right=.86,top=.86,bottom=.22)
        terrain(ax,limits(e),dem);box(ax,e)
        if e['event_id'] in LOCAL:box(ax,LOCAL[e['event_id']],'local')
        event_overlay(ax,e)
        fig.suptitle(f"{e['event_id']}：撞击—台站路径与真实 LOLA 地形",fontsize=17,y=.97)
        title=f"{e['time_earth_received']} UT（地球接收时刻）｜{e['n_recorded_pairs']} 个有记录台站"
        ax.set_title(title,fontsize=11,pad=10)
        fig.legend(handles=legend_handles(),loc='lower center',bbox_to_anchor=(.49,.075),ncol=3,fontsize=9,frameon=False)
        cbar(fig,ax);footer(fig);save(fig,e['event_id']+'_terrain_domain')
    # Nine individual panels retain terrain at original sampling; smaller render is explicitly only a display overview.
    fig,axes=plt.subplots(3,3,figsize=(17,14));fig.subplots_adjust(left=.05,right=.88,top=.92,bottom=.18,hspace=.38,wspace=.3)
    for ax,e in zip(axes.flat,EVENTS):
        terrain(ax,limits(e),dem);box(ax,e,lw=1.7)
        if e['event_id'] in LOCAL:box(ax,LOCAL[e['event_id']],'local',lw=1.7)
        event_overlay(ax,e,small=True);ax.set_title(f"{e['event_id']}｜记录台站 {e['n_recorded_pairs']}",fontsize=12)
        ax.tick_params(labelsize=8);ax.xaxis.label.set_size(9);ax.yaxis.label.set_size(9)
    cbar(fig,list(axes.flat),.8)
    fig.suptitle('九次人工撞击的地形、接收台站与范围框',fontsize=20,y=.975)
    fig.legend(handles=legend_handles(),loc='lower center',bbox_to_anchor=(.5,.055),ncol=3,fontsize=11,frameon=False)
    footer(fig);save(fig,'nine_event_terrain_domains')
    # Overview with the full envelope for every event; pair-specific detail belongs in individual figures.
    fig,ax=plt.subplots(figsize=(16,10));fig.subplots_adjust(left=.07,right=.87,top=.91,bottom=.22)
    terrain(ax,(-35,38,-14,32),dem)
    for e in EVENTS:
        box(ax,e,lw=1.05)
        if e['event_id'] in LOCAL:box(ax,LOCAL[e['event_id']],'local',lw=1.2)
    for p in PAIRS:
        e=next(e for e in EVENTS if e['event_id']==p['event_id']);s=STATIONS[p['station']]
        x,y=arc(e,s);ax.plot(x,y,color='#252525',lw=.85,alpha=.65,ls='-' if p['nunn2024_clear']=='True' else '--',zorder=3)
    offsets={'A12LM':(5,-25),'A13SIVB':(-28,17),'A14SIVB':(-28,-21),'A14LM':(10,-13),
             'A15SIVB':(10,10),'A15LM':(-56,16),'A16SIVB':(-45,16),'A17SIVB':(10,-16),'A17LM':(9,8)}
    for e in EVENTS:
        ax.scatter(e['lon'],e['lat'],marker='*',s=180,c='#d91f26',edgecolors='white',lw=.6,zorder=7)
        ax.annotate(e['event_id'],(e['lon'],e['lat']),xytext=offsets[e['event_id']],textcoords='offset points',fontsize=10,
                    bbox=dict(fc='white',ec='none',alpha=.85,pad=1.5),zorder=8)
    for sid,s in STATIONS.items():
        ax.scatter(s['lon'],s['lat'],marker='^',s=100,c='#171717',edgecolors='white',lw=.8,zorder=7)
        dx,dy={'S12':(-35,1),'S14':(6,-23),'S15':(8,-13),'S16':(8,-3)}[sid]
        ax.annotate(sid,(s['lon'],s['lat']),xytext=(dx,dy),textcoords='offset points',fontsize=11,weight='bold',
                    bbox=dict(fc='white',ec='none',alpha=.9,pad=2),zorder=8)
    ax.set_title('全部撞击事件、实际接收台站与规划覆盖范围（真实 LOLA 地形底图）',fontsize=18,pad=15)
    fig.legend(handles=legend_handles(),loc='lower center',bbox_to_anchor=(.49,.065),ncol=3,fontsize=10,frameon=False)
    cbar(fig,ax);footer(fig);save(fig,'impact_station_terrain_overview')
    # Local candidate zooms and 8-panel overview, retaining the exact audited bounds.
    candidates=[e for e in EVENTS if e['event_id'] in LOCAL]
    for e in candidates:
        d=LOCAL[e['event_id']];fig,ax=plt.subplots(figsize=(10,7.5));fig.subplots_adjust(left=.09,right=.85,top=.88,bottom=.22)
        terrain(ax,limits(d),dem);box(ax,d,'local');event_overlay(ax,e,local_only=True)
        ax.set_title(f"{e['event_id']} 近距候选｜{d['receivers']}｜{d['width_at_midlat_km']:.0f} × {d['height_km']:.0f} km",fontsize=14)
        fig.legend(handles=[legend_handles()[0],legend_handles()[1],legend_handles()[2],legend_handles()[5]],
                   loc='lower center',bbox_to_anchor=(.48,.065),ncol=2,fontsize=9,frameon=False)
        cbar(fig,ax);footer(fig);save(fig,e['event_id']+'_local_terrain_domain')
    fig,axes=plt.subplots(4,2,figsize=(13,16));fig.subplots_adjust(left=.06,right=.86,top=.94,bottom=.13,hspace=.45,wspace=.28)
    for ax,e in zip(axes.flat,candidates):
        d=LOCAL[e['event_id']];terrain(ax,limits(d),dem);box(ax,d,'local',lw=1.8);event_overlay(ax,e,local_only=True,small=True)
        ax.set_title(f"{e['event_id']}｜{d['receivers']}｜{d['width_at_midlat_km']:.0f} × {d['height_km']:.0f} km",fontsize=11)
        ax.tick_params(labelsize=8);ax.xaxis.label.set_size(9);ax.yaxis.label.set_size(9)
    cbar(fig,list(axes.flat),.75);fig.suptitle('8 个近距模拟候选域：真实 LOLA 地形与 11 条清晰路径',fontsize=18,y=.98)
    fig.legend(handles=[legend_handles()[0],legend_handles()[1],legend_handles()[2],legend_handles()[5]],
               loc='lower center',bbox_to_anchor=(.48,.045),ncol=4,fontsize=9,frameon=False)
    footer(fig);save(fig,'local_candidate_terrain_domains')
    qa(dem)

def qa(dem):
    z,lon,lat=dem
    checks=[]
    points=[('S12',-3.0098,-23.4249),('S14',-3.64419,-17.47768),('S15',26.13406,3.62991),('S16',-8.9759,15.4986),
            ('Mare_Imbrium_interior',32,-17),('Apennine_ridge_context',24.5,4.5),('Ptolemaeus_crater_floor',-9.2,-1.8)]
    for name,y,x in points:
        i=np.argmin(abs(lat-y));j=np.argmin(abs(lon-x))
        checks.append({'site':name,'lat':y,'lon':x,'native_pixel_height_m':round(float(z[i,j]*1000),1),
                       'neighbourhood_3x3_median_m':round(float(np.median(z[max(0,i-1):i+2,max(0,j-1):j+2])*1000),1)})
    domains=[]
    for e in EVENTS:
        ps=[p for p in PAIRS if p['event_id']==e['event_id']]
        for p in ps:
            x,y=arc(e,STATIONS[p['station']])
            assert np.all((x>=e['west_degE'])&(x<=e['east_degE'])&(y>=e['south_degN'])&(y<=e['north_degN']))
        domains.append({'event':e['event_id'],'all_recorded_paths_inside_blue_frame':True})
    result={'date':'2026-10-29','n_events':9,'n_pairs':len(PAIRS),'n_local_candidate_domains':len(LOCAL),
            'old_float_rejected':True,'native_grid_shape':list(z.shape),'native_grid_spacing_deg':1/PPD,
            'image_encoding':'common elevation color scale [-5,+5] km; 315deg/45deg hillshade factor 0.65 to 1.00; vertical exaggeration 1',
            'within_color_limits_fraction':float(np.mean((z>=-5)&(z<=5))),
            'source_station_pixel_samples':checks,'domain_checks':domains,
            'png_files':sorted(p.name for p in FIG.glob('*.png')),'no_sub_2km_feature_labels':True,
            'not_established':'calculation-domain convergence, local scattering strength or detailed geological-unit boundaries'}
    (OUT/'terrain_figure_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    with (OUT/'site_height_checks.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(checks[0]));w.writeheader();w.writerows(checks)
    print(json.dumps({'figures':len(result['png_files']),'site_checks':checks},ensure_ascii=False),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--download-only',action='store_true');ap.add_argument('--plot-only',action='store_true')
    args=ap.parse_args()
    if not args.plot_only:download()
    if not args.download_only:make_plots()
