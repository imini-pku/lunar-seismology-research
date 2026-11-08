"""Solver-neutral, physically defined lunar random-media previews and run manifest.

These files are NOT validated CGFD3D production inputs. No wave solver is run.
FFT fields are generated in physical metres on a padded regular grid; cropping
avoids treating opposite faces of the delivered block as adjacent material.
"""
from pathlib import Path
import argparse, csv, hashlib, json, tempfile, shutil
import numpy as np
from scipy import fft
from netCDF4 import Dataset

ROOT = Path(__file__).resolve().parents[1]

def random_field(shape, spacing_m, lengths_m, nu, seed, pad=24):
    """Order z,y,x; PSD proportional to (1+sum((a_i*k_i)^2))^(-nu-3/2)."""
    padded = tuple(n + 2*pad for n in shape)
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(padded, dtype=np.float32)
    spec = fft.rfftn(noise, workers=2)
    k = [2*np.pi*fft.fftfreq(n, d=spacing_m) for n in padded[:2]]
    k.append(2*np.pi*fft.rfftfreq(padded[2], d=spacing_m))
    q = ((lengths_m[0]*k[0][:,None,None])**2
         + (lengths_m[1]*k[1][None,:,None])**2
         + (lengths_m[2]*k[2][None,None,:])**2)
    spec *= (1+q)**(-(nu+1.5)/2)
    spec[0,0,0] = 0
    field = fft.irfftn(spec, s=padded, workers=2)
    cuts = tuple(slice(pad, pad+n) for n in shape)
    field = field[cuts].copy()
    field -= field.mean(dtype=np.float64)
    field /= field.std(dtype=np.float64)
    return field.astype('f4')

def background(depth_m):
    """A12-inspired smooth upper-crust reference, not a regional inversion.
    Density/porosity/velocity relation: Onodera2022 equations 1-4, xi=7.
    Vp/Vs transition 10-12 km is OUR smoothing choice, separately testable.
    No Moho/mantle or thin site layers are included in the preview block.
    """
    z = np.asarray(depth_m, dtype=float)
    rho = 2308 + 786*(1-np.exp(-z/9800))
    phi = 1-rho/(2308+786)
    vp = 7150*np.sqrt(1-phi)*np.exp((phi/2-7)*phi/(2*(1-phi)))
    blend = np.clip((z-10000)/2000,0,1)
    ratio = 2 + (np.sqrt(3)-2)*blend
    return vp, vp/ratio, rho

def depth_weight(depth_m, family, H_m=10000):
    z=np.asarray(depth_m)
    if family == 'R2':
        return np.exp(-z/5000) * np.clip((24000-z)/1000,0,1)
    u=np.clip((z-(H_m-500))/1000,0,1)
    return .5*(1+np.cos(np.pi*u))

def acf_axis(field, axis, maxlag):
    # Linear (non-wrapping) pairs and separate denominator for each lag.
    out=[]
    for lag in range(maxlag+1):
        a=[slice(None)]*3; b=a.copy()
        if lag: a[axis]=slice(None,-lag); b[axis]=slice(lag,None)
        u=field[tuple(a)]; v=field[tuple(b)]
        out.append(float(np.mean(u*v)/np.sqrt(np.mean(u*u)*np.mean(v*v))))
    return out

def build():
    out=ROOT/'results/scattering_models';out.mkdir(parents=True,exist_ok=True)
    shape=(256,96,96); spacing=100.; z=np.arange(shape[0])*spacing
    vp0,vs0,rho0=background(z)
    report={'status':'material_generation_QA_only_no_wave_propagation',
            'shape_zyx':shape,'spacing_m':spacing,'models':[],
            'not_production_input_reasons':['CGFD3D test.json and md3grd exporter absent',
            'preview domain is smaller than source receiver paths',
            'production grid and CFL need solver convergence tests']}
    for name,lengths in [('R1',(650,650,650)),('R2',(650,650,650)),('R4',(650,1300,1300))]:
        eta=random_field(shape,spacing,lengths,.5,20261029)
        w=depth_weight(z,name)
        dv=.1*w[:,None,None]*eta
        vp=(vp0[:,None,None]*(1+dv)).astype('f4')
        vs=(vs0[:,None,None]*(1+dv)).astype('f4')
        rho=(rho0[:,None,None]*(1+.8*dv)).astype('f4')
        bulk=rho*(vp*vp-4/3*vs*vs)
        assert np.isfinite(vp).all() and min(vp.min(),vs.min(),rho.min(),bulk.min())>0
        p=out/f'{name}_preview.nc'
        tmpdir=tempfile.TemporaryDirectory(prefix='lunar_medium_')
        temporary_path=Path(tmpdir.name)/'medium.nc'
        with Dataset(temporary_path,'w') as ds:
            for dim,n in zip(('depth','y','x'),shape): ds.createDimension(dim,n)
            for dim,n in zip(('depth','y','x'),shape):
                c=ds.createVariable(dim,'f4',(dim,));c[:]=np.arange(n)*spacing;c.units='m'
            ds['depth'].positive='down';ds['depth'].long_name='depth beneath nominal flat reference surface'
            for key,arr,unit in [('vp',vp,'m s-1'),('vs',vs,'m s-1'),('rho',rho,'kg m-3'),('eta',eta,'1')]:
                v=ds.createVariable(key,'f4',('depth','y','x'),zlib=True,complevel=2)
                v[:]=arr;v.units=unit
            ds.description='CGFD3D-adapter-neutral material preview; no actual lunar topography; not production input'
            ds.family=name;ds.seed=20261029;ds.nu=.5;ds.sigma_v=.1
            ds.lengths_zyx_m=json.dumps(lengths);ds.density_scale=.8
            ds.background_source='10.1029/2022JE007558 eq1-4 plus project-defined Vp/Vs smoothing'
        shutil.copyfile(temporary_path,p)
        tmpdir.cleanup()
        report['models'].append({'id':name,'file':str(p.relative_to(ROOT)),
            'eta_mean':float(eta.mean()),'eta_std':float(eta.std()),
            'min_bulk_modulus_Pa':float(bulk.min()),'vp_min_m_s':float(vp.min()),
            'vs_min_m_s':float(vs.min()),'rho_min_kg_m3':float(rho.min()),
            'target_sigma_v':(.1*w).tolist(),'realized_sigma_v_by_depth':dv.std(axis=(1,2)).tolist(),
            'acf_x':acf_axis(eta,2,25),'acf_z':acf_axis(eta,0,25),
            'lengths_zyx_m':lengths,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    # Same realization identifier across amplitude/geometry controls prevents seed confounding.
    settings=[('B',.1,.65,10),('S05',.05,.65,10),('S15',.15,.65,10),
              ('A03',.1,.3,10),('A13',.1,1.3,10),('H035',.1,.65,3.5),('H20',.1,.65,20)]
    rows=[]
    for event in ['Apollo14_SIVB_to_S12','Apollo16_SIVB_to_S12']:
        for terrain in ['flat','LOLA_real_amplitude']:
            rows.append(dict(run_id=f'{event}_{terrain}_R0',event_path=event,terrain=terrain,
                model='R0',sigma_v=0,a_km='',H_km='',seed='',status='awaiting_CGFD3D_configuration'))
            for label,sig,a,H in settings:
                for seed in [20261029,20261030,20261031]:
                    rows.append(dict(run_id=f'{event}_{terrain}_{label}_{seed}',event_path=event,
                        terrain=terrain,model='R1',sigma_v=sig,a_km=a,H_km=H,seed=seed,
                        status='awaiting_CGFD3D_configuration'))
    with (ROOT/'config/scattering_run_manifest.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    report['stage_A_run_count']=len(rows)
    (out/'material_QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'preview_files':len(report['models']),'planned_runs':len(rows),
                      'wave_solver_executed':False},ensure_ascii=False))

if __name__=='__main__': build()
