"""Event/station geometry from NASA source coordinates and literature-confirmed pairs.

Geographic planning windows are not validated CGFD3D propagation boundaries.
No map background is needed to identify paths; do not reuse the old misregistered DEM.
"""
from pathlib import Path
import json, csv, math, hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/impact_audit'; OUT.mkdir(parents=True,exist_ok=True)
FIG=ROOT/'figures/impact_audit'; FIG.mkdir(parents=True,exist_ok=True)
R=1737.4
SITE_URL='https://nssdc.gsfc.nasa.gov/planetary/lunar/lunar_sites.html'
IMPACT_URL='https://nssdc.gsfc.nasa.gov/planetary/lunar/apollo_impact.html'
STATIONS={
 'S12':{'lat':-3.0098,'lon':-23.4249},
 'S14':{'lat':-3.64419,'lon':-17.47768},
 'S15':{'lat':26.13406,'lon':3.62991},
 'S16':{'lat':-8.9759,'lon':15.4986}}
# NASA impact table times are Earth-received times, not lunar origin UTC.
EVENT_ROWS=[
 ('A12LM','1969-11-20T22:17:17.7',-3.94,-21.20,'LM'),
 ('A13SIVB','1970-04-15T01:09:41.0',-2.5550,-27.8875,'SIVB'),
 ('A14SIVB','1971-02-04T07:40:55.4',-8.1810,-26.0305,'SIVB'),
 ('A14LM','1971-02-07T00:45:25.7',-3.42,-19.67,'LM'),
 ('A15SIVB','1971-07-29T20:58:42.9',-1.2897,-11.8245,'SIVB'),
 ('A15LM','1971-08-03T03:03:37.0',26.36,0.25,'LM'),
 ('A16SIVB','1972-04-19T21:02:04',1.9210,-24.6230,'SIVB'),
 ('A17SIVB','1972-12-10T20:32:42.3',-4.1681,-12.3307,'SIVB'),
 ('A17LM','1972-12-15T06:50:20.8',19.97,30.49,'LM')]
EVENTS={x[0]:dict(event_id=x[0],time_earth_received=x[1],lat=x[2],lon=x[3],impactor=x[4],source_url=IMPACT_URL,
    time_caveat='Earth-received; about 1.3 s later than lunar time; A16 uncertainty about 4 s' if x[0]=='A16SIVB' else 'Earth-received; about 1.3 s later than lunar time') for x in EVENT_ROWS}

def write_csv(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def xyz(lat,lon):
    p,l=np.deg2rad([lat,lon]);return np.array([np.cos(p)*np.cos(l),np.cos(p)*np.sin(l),np.sin(p)])

def arc(event,station):
    a=xyz(event['lat'],event['lon']);b=xyz(station['lat'],station['lon'])
    omega=np.arccos(np.clip(np.dot(a,b),-1,1));t=np.linspace(0,1,201)
    p=(np.sin((1-t)*omega)[:,None]*a+np.sin(t*omega)[:,None]*b)/np.sin(omega)
    return np.rad2deg(np.arctan2(p[:,1],p[:,0])),np.rad2deg(np.arcsin(np.clip(p[:,2],-1,1))),float(omega)

def window(xs,ys,buffer=50):
    padlat=np.rad2deg(buffer/R);padlon=padlat/np.cos(np.deg2rad(max(abs(np.min(ys)),abs(np.max(ys)))+padlat))
    lo,hi=float(np.min(xs)-padlon),float(np.max(xs)+padlon)
    bot,top=float(np.min(ys)-padlat),float(np.max(ys)+padlat)
    return {'west_degE':round(lo,5),'east_degE':round(hi,5),'south_degN':round(bot,5),'north_degN':round(top,5),
            'width_at_midlat_km':round(R*np.deg2rad(hi-lo)*np.cos(np.deg2rad((top+bot)/2)),1),
            'height_km':round(R*np.deg2rad(top-bot),1),'planning_buffer_km':buffer,
            'boundary_status':'geographic planning envelope; PML/late-coda domain not validated'}

def load_pairs():
    with (ROOT/'results/impact_pairs_literature.csv').open(encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
    assert len(rows)==21
    for row in rows:
        row['clear']=str(row['nunn2024_clear']).lower() in ['true','1','yes']
    return rows

def main():
    pairs=load_pairs();pair_rows=[];events=[]
    for event_id,event in EVENTS.items():
        selected=[p for p in pairs if p['event_id']==event_id];xs=[];ys=[]
        for p in selected:
            x,y,w=arc(event,STATIONS[p['station']]);xs.extend(x);ys.extend(y)
            d=R*w
            pair_rows.append({'pair_id':event_id+'_'+p['station'],'event_id':event_id,'station':p['station'],
               'distance_deg':round(np.rad2deg(w),4),'distance_km':round(d,2),
               'distance_published_km':p['distance_published_km'],'nunn2024_clear':p['clear'],
               'component_caveat':p.get('component_caveat',''),
               'domain_role':'local_candidate_pending_QC' if p['clear'] and d<400 else 'far_path_validation' if p['clear'] else 'low_SNR_audit_only',
               'sphere_chord_sag_km':round(R*(1-np.cos(w/2)),2),**window(x,y),
               'geometry_source':IMPACT_URL+' ; '+SITE_URL})
        events.append({**event,'recorded_stations':';'.join(p['station'] for p in selected),
             'clear_stations':';'.join(p['station'] for p in selected if p['clear']),
             'n_recorded_pairs':len(selected),'n_clear_literature':sum(p['clear'] for p in selected),
             'domain_role':'all_recorded_station_coverage_not_production_domain',**window(xs,ys)})
    write_csv(OUT/'events_and_domains.csv',events);write_csv(OUT/'event_station_domains.csv',pair_rows)
    write_csv(OUT/'stations.csv',[dict(station=s,**v,source_url=SITE_URL) for s,v in STATIONS.items()])
    (OUT/'coordinate_provenance.json').write_text(json.dumps({'date':'2026-10-29','radius_km':R,'station_reference':'ALSEP, ME/PA DE421',
      'impact_reference':'NASA table; SIVB LRO Wagner 2017, LM legacy locations; mixed precision retained',
      'source_urls':[SITE_URL,IMPACT_URL],'time_reference':'NASA Earth-received; do not silently subtract 1.3 seconds from legacy SAC',
      'map_projection':'geographic longitude/latitude; local aspect corrections; distances spherical, not ruler measurements',
      'geographic_buffer_km':50,'sphere_effect':'chord sag is a geometry diagnostic, not a correction to data',
      'differences_to_old_catalog':['A16SIVB absent in Nakamura1983 AI coordinate CSV','A14LM old CSV time 00:45:26.7 versus NASA 00:45:25.7; retain both in audit','SIVB coordinates updated by LRO; old SAC source coordinates retained in raw files','A15 ALSEP longitude is positive 3.62991 E'],
      'pairs':len(pair_rows),'events':len(events),'clear_pairs_literature':sum(p['clear'] for p in pairs)},ensure_ascii=False,indent=2),encoding='utf8')
    plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','DejaVu Sans'],'axes.unicode_minus':False,'font.size':11})
    colors=dict(zip(EVENTS,plt.get_cmap('tab10').colors))
    fig,ax=plt.subplots(figsize=(12,8),layout='constrained')
    for p in pairs:
        x,y,w=arc(EVENTS[p['event_id']],STATIONS[p['station']]);ax.plot(x,y,color=colors[p['event_id']],ls='-' if p['clear'] else '--',lw=1.3,alpha=.65)
    offsets={'A12LM':(-65,-45),'A13SIVB':(-52,17),'A14SIVB':(-40,-26),'A14LM':(15,19),'A15SIVB':(12,17),'A15LM':(-40,15),'A16SIVB':(-60,18),'A17SIVB':(12,-20),'A17LM':(12,12)}
    for eid,e in EVENTS.items():
        ax.scatter(e['lon'],e['lat'],marker='*',s=170,c=[colors[eid]],edgecolor='black',zorder=5)
        ax.annotate(eid,(e['lon'],e['lat']),xytext=offsets[eid],textcoords='offset points',fontsize=10,fontweight='bold',color=colors[eid],bbox=dict(fc='white',ec='none',alpha=.8,pad=1),arrowprops=dict(arrowstyle='-',lw=.5,color=colors[eid]))
    for s,v in STATIONS.items():
        ax.scatter(v['lon'],v['lat'],marker='^',s=115,c='black',zorder=6)
        ax.annotate(s,(v['lon'],v['lat']),xytext=(-28,8) if s=='S12' else (4,-20),textcoords='offset points',weight='bold',fontsize=12,bbox=dict(fc='white',ec='none',alpha=.85,pad=1))
    ax.set(xlim=(-34,36),ylim=(-15,33),xlabel='经度 / °E',ylabel='纬度 / °N',title='9 次人工撞击与 4 个 PSE 台站：21 条已发表记录路径')
    ax.set_aspect(1/np.cos(np.deg2rad(9)));ax.grid(alpha=.25)
    ax.legend(handles=[Line2D([],[],marker='*',color='none',markerfacecolor='gray',markeredgecolor='black',markersize=13,label='撞击事件（任务编号）'),Line2D([],[],marker='^',color='none',markerfacecolor='black',markersize=10,label='接收台站'),Line2D([],[],color='gray',lw=2,label='文献清晰记录 16 对'),Line2D([],[],color='gray',ls='--',lw=2,label='文献低信噪比 5 对')],loc='lower right',fontsize=10)
    fig.savefig(FIG/'impact_station_overview.png',dpi=190);fig.savefig(FIG/'impact_station_overview.pdf');plt.close(fig)
    fig,axs=plt.subplots(3,3,figsize=(16,13),layout='constrained')
    for ax,e in zip(axs.flat,events):
        eid=e['event_id'];c=colors[eid]
        for p in pairs:
            if p['event_id']!=eid:continue
            v=STATIONS[p['station']];x,y,w=arc(e,v)
            ax.plot(x,y,color=c,ls='-' if p['clear'] else '--',lw=1.6)
            ax.scatter(v['lon'],v['lat'],marker='^',s=55,c='black',zorder=6)
            ax.annotate(p['station']+('' if p['clear'] else ' *'),(v['lon'],v['lat']),xytext=(4,6),textcoords='offset points',fontsize=10,weight='bold',bbox=dict(fc='white',ec='none',alpha=.8,pad=1))
        ax.scatter(e['lon'],e['lat'],marker='*',s=130,c=[c],edgecolor='black',zorder=7)
        ax.add_patch(Rectangle((e['west_degE'],e['south_degN']),e['east_degE']-e['west_degE'],e['north_degN']-e['south_degN'],fill=False,edgecolor=c,lw=2))
        dx=e['east_degE']-e['west_degE'];dy=e['north_degN']-e['south_degN']
        ax.set_xlim(e['west_degE']-.1*dx,e['east_degE']+.1*dx);ax.set_ylim(e['south_degN']-.12*dy,e['north_degN']+.12*dy)
        ax.set_aspect(1/np.cos(np.deg2rad((e['south_degN']+e['north_degN'])/2)))
        ax.set_title(f"{eid}：{e['n_recorded_pairs']} 站（清晰 {e['n_clear_literature']}）\n约 {e['width_at_midlat_km']:.0f} × {e['height_km']:.0f} km",fontsize=11)
        ax.set(xlabel='经度 / °E',ylabel='纬度 / °N');ax.grid(alpha=.2)
    fig.suptitle('各撞击事件的全部记录覆盖框：包含远距及低信噪比台站\n彩框在路径外加 50 km 地理缓冲；* / 虚线为低信噪比；这是覆盖审计，不是已确定的生产模拟域',fontsize=15)
    fig.savefig(FIG/'nine_event_simulation_domains.png',dpi=190);fig.savefig(FIG/'nine_event_simulation_domains.pdf');plt.close(fig)
    local=[]
    for e in events:
        pp=[p for p in pair_rows if p['event_id']==e['event_id'] and p['domain_role']=='local_candidate_pending_QC']
        if not pp:continue
        xx=[];yy=[]
        for p in pp:
            x,y,w=arc(e,STATIONS[p['station']]);xx.extend(x);yy.extend(y)
        local.append({'event_id':e['event_id'],'receivers':';'.join(p['station'] for p in pp),'domain_role':'local_model_candidate_pending_waveform_QC_and_domain_convergence',**window(xx,yy)})
    write_csv(OUT/'local_simulation_candidates.csv',local)
    fig,axs=plt.subplots(2,4,figsize=(16,8),layout='constrained')
    def draw_local(ax,eid,row):
        e=EVENTS[eid];c=colors[eid]
        for s in row['receivers'].split(';'):
            v=STATIONS[s];x,y,w=arc(e,v);ax.plot(x,y,color=c,lw=1.5)
            ax.scatter(v['lon'],v['lat'],marker='^',s=65,c='black',zorder=5)
            ax.annotate(s,(v['lon'],v['lat']),xytext=(3,7),textcoords='offset points',weight='bold',fontsize=10)
        ax.scatter(e['lon'],e['lat'],marker='*',s=140,c=[c],edgecolor='black',zorder=6)
        dx=row['east_degE']-row['west_degE'];dy=row['north_degN']-row['south_degN']
        ax.add_patch(Rectangle((row['west_degE'],row['south_degN']),dx,dy,fill=False,ec=c,lw=2))
        ax.set_xlim(row['west_degE']-.12*dx,row['east_degE']+.12*dx);ax.set_ylim(row['south_degN']-.12*dy,row['north_degN']+.12*dy)
        ax.set_aspect(1/np.cos(np.deg2rad((row['south_degN']+row['north_degN'])/2)))
        ax.set_title(f"{eid} → {row['receivers'].replace(';',' / ')}\n约 {row['width_at_midlat_km']:.0f} × {row['height_km']:.0f} km",fontsize=11)
        ax.set(xlabel='经度 / °E',ylabel='纬度 / °N');ax.grid(alpha=.2)
    for ax,row in zip(axs.flat,local):draw_local(ax,row['event_id'],row)
    fig.suptitle('近距候选模拟域：8 次事件、11 条文献清晰路径（<400 km）\n仅为首轮几何与计算量设计；记录质控、地形曲率、底界及长尾波边界仍需验证',fontsize=15)
    fig.savefig(FIG/'local_candidate_simulation_domains.png',dpi=190);fig.savefig(FIG/'local_candidate_simulation_domains.pdf');plt.close(fig)
    for row in local:
        fig,ax=plt.subplots(figsize=(5.4,4.5),layout='constrained');draw_local(ax,row['event_id'],row)
        fig.savefig(FIG/(row['event_id']+'_local_domain.png'),dpi=170);plt.close(fig)
    for e in events:
        assert e['west_degE']<e['lon']<e['east_degE'] and e['south_degN']<e['lat']<e['north_degN']
        for s in e['recorded_stations'].split(';'):
            v=STATIONS[s];assert e['west_degE']<v['lon']<e['east_degE'] and e['south_degN']<v['lat']<e['north_degN']
    print(json.dumps({'events':len(events),'pairs':len(pair_rows),'clear':sum(p['clear'] for p in pairs),'containment_checks':'passed'},ensure_ascii=False))

if __name__=='__main__':main()
