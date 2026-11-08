"""Compare physical velocity waveforms on matched origin-time Z/R/T grids.
No time warping, phase picking, calibration, or response removal is performed.
This is a scoring interface, not an inversion result or a waveform solver.
"""
import argparse, json
from pathlib import Path
import numpy as np
from scipy.signal import butter,sosfiltfilt,hilbert
from scipy.ndimage import uniform_filter1d

def score(t,obs,syn,band=(.3,.9),start=50,end=3000,smoothing_s=30):
    t=np.asarray(t);obs=np.asarray(obs);syn=np.asarray(syn)
    if obs.shape!=syn.shape or obs.shape!=(len(t),3): raise ValueError('Require time x 3 ZRT arrays')
    if not np.isfinite(obs).all() or not np.isfinite(syn).all(): raise ValueError('Gaps must be QCed, never zero-filled')
    dt=float(np.median(np.diff(t)))
    if dt<=0 or not np.allclose(np.diff(t),dt,rtol=1e-4,atol=1e-8): raise ValueError('Uniform common time grid required')
    if band[1]>=.5/dt:raise ValueError('Band exceeds Nyquist')
    # Additional data around the score window protect filtering and smoothing edges.
    margin=max(smoothing_s,6/band[0])
    if t[0]>start-margin or t[-1]<end+margin: raise ValueError('Insufficient shared window / filter padding; coda may be censored')
    sos=butter(4,band,fs=1/dt,btype='bandpass',output='sos')
    env=[];fractions=[]
    mask=(t>=start)&(t<=end)
    for arr in [obs,syn]:
        filt=sosfiltfilt(sos,arr,axis=0)
        power=np.abs(hilbert(filt,axis=0))**2
        smooth=uniform_filter1d(power,size=max(1,round(smoothing_s/dt)),axis=0,mode='nearest')[mask]
        if smooth.sum()<=0:raise ValueError('Zero energy trace')
        fractions.append(smooth.sum(axis=0)/smooth.sum())
        env.append(smooth.sum(axis=1)/smooth.sum())
    a,b=env; tt=t[mask];floor=max(a.max(),b.max())*1e-6
    log_rms=float(np.sqrt(np.mean((np.log(a+floor)-np.log(b+floor))**2)))
    peak_error=float(abs(tt[a.argmax()]-tt[b.argmax()]))
    cdf_error=float(np.mean(abs(np.cumsum(a)-np.cumsum(b))))
    component_error=float(np.linalg.norm(fractions[0]-fractions[1]))
    # Provisional scaling; fit uncertainties on training events before scientific ranking.
    total=.4*log_rms+.2*peak_error/100+.2*cdf_error/.1+.2*component_error/.1
    return dict(total_provisional=total,log_envelope_rms=log_rms,peak_error_s=peak_error,
        normalized_energy_cdf_error=cdf_error,component_fraction_L2=component_error,
        component_fraction_observed=fractions[0].tolist(),component_fraction_synthetic=fractions[1].tolist(),
        window_s=[start,end],band_hz=list(band),smoothing_s=smoothing_s,
        amplitude_normalization='one total-energy scale across all three components',
        caution='weights/scales are project choices; use held-out events and seed distributions')

def load(path):
    with np.load(path,allow_pickle=False) as d:
        m=json.loads(str(d['metadata_json']))
        for k,v in {'units':'m/s','response_removed':True,'time_reference':'origin','frame':'ZRT'}.items():
            if m.get(k)!=v:raise ValueError(f'{path}: metadata {k} must be {v!r}')
        return d['t'].copy(),d['velocity'].copy()

def main():
    p=argparse.ArgumentParser();p.add_argument('--observed',required=True);p.add_argument('--synthetic',required=True)
    p.add_argument('--output',required=True);p.add_argument('--start',type=float,default=50)
    p.add_argument('--end',type=float,default=3000);args=p.parse_args()
    t,a=load(args.observed);ts,b=load(args.synthetic)
    if t.shape!=ts.shape or not np.allclose(t,ts):raise ValueError('Align on origin and resample explicitly before scoring')
    result=score(t,a,b,start=args.start,end=args.end)
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
