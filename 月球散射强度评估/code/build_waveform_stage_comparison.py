"""Preserve Apollo archive samples and compare explicit processing stages.

All outputs are separate from the earlier reference data. Run with system
Python 3.11; project-local ObsPy is added without changing the environment.
This is an exploratory display and audit, not an inversion-ready calibration.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.build/waveform_dependencies'))
import numpy as np
from scipy.signal import butter, sosfiltfilt
from obspy import read, read_inventory, UTCDateTime, Trace
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

DATA = ROOT / 'data/processed/waveform_comparison_v2'
FIG = ROOT / 'figures/waveform_comparison'
RES = ROOT / 'results/waveform_comparison'
CHANNELS = ('MHZ', 'MH1', 'MH2')
WINDOW = (-300, 3600)
COLORS = dict(raw='#253744', response='#126A91', filtered='#23664E', edge='#C47725', gap='#666666', short='#E6B66F')


def table(path):
    with (ROOT / path).open(encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def runs(mask):
    diff = np.diff(np.r_[False, mask, False].astype(int))
    return list(zip(np.where(diff == 1)[0], np.where(diff == -1)[0]))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def old_display_filter(t, velocity):
    """Exact old display rule for an audit of displayed blank samples."""
    fs = 1 / np.median(np.diff(t))
    work = velocity.copy()
    for a, b in runs(~np.isfinite(work)):
        if b - a <= 2 and a > 0 and b < len(work):
            work[a:b] = np.interp(np.arange(a, b), [a - 1, b], [work[a - 1], work[b]])
    output = np.full(len(work), np.nan)
    for a, b in runs(np.isfinite(work)):
        if b - a < 60 * fs:
            continue
        output[a:b] = sosfiltfilt(butter(4, [.3, .9], fs=fs, btype='bandpass', output='sos'), work[a:b])
        edge = int(10 * fs)
        output[a:a + edge] = np.nan
        output[b - edge:b] = np.nan
    output[~np.isfinite(velocity)] = np.nan
    return output


def process():
    for directory in (DATA, FIG, RES):
        directory.mkdir(parents=True, exist_ok=True)
    events = {r['event_id']: r for r in table('results/impact_audit/events_and_domains.csv')}
    pairs = table('results/impact_pairs_literature.csv')
    previous = {(r['event_id'], r['station'], r['channel']): r for r in table('results/impact_modern_trace_audit.csv')}
    inventory_path = ROOT / 'data/raw/impact_metadata/stationxml.xa.0.sxml'
    inventory = read_inventory(str(inventory_path))
    records = []
    all_segments = []
    raw_hashes = {}
    for pair in pairs:
        eid, station = pair['event_id'], pair['station']
        raw_path = ROOT / 'data/raw/impact_modern' / f'{eid}_{station}_MP_ATT.mseed'
        raw_hashes[str(raw_path.relative_to(ROOT))] = sha(raw_path)
        stream = read(str(raw_path))
        origin = UTCDateTime(events[eid]['time_earth_received'])
        for channel in CHANNELS:
            base = dict(event_id=eid, station=station, channel=channel, distance_km=float(pair['distance_published_km']), nunn2024_clear=pair['nunn2024_clear'])
            original = stream.select(channel=channel).copy()
            old_row = previous[(eid, station, channel)]
            if not original or not old_row.get('npz'):
                records.append(dict(base, status='archive_not_returned_known_fault_epoch' if not original else 'not_processed_known_fault_epoch', archive_channel_present=bool(original), npz='', note='S14 MHZ not returned by archive; known malfunction interval 1972-03-12 to 1976-11-17. No waveform substituted.'))
                continue
            original.merge(method=1, fill_value=None)
            assert len(original) == 1
            tr = original[0]
            merged = np.asarray(np.ma.filled(tr.data, -1), dtype=float)
            old_path = ROOT / old_row['npz']
            with np.load(old_path) as old:
                raw = old['raw_counts'].copy()
                gaps = old['original_gap_mask'].copy()
                t = old['t'].copy()
                old_velocity = old['velocity_m_s'].copy()
                old_meta = json.loads(str(old['metadataJSON']))
            assert np.array_equal(raw, merged)
            assert np.array_equal(gaps, (merged == -1) | ~np.isfinite(merged))
            t_nominal = float(tr.stats.starttime - origin) + np.arange(len(raw)) * tr.stats.delta
            clock = old_meta['clock']
            assert np.array_equal(t, t_nominal * clock['slope'] + clock['offset_at_event_s'])
            fs = float(1 / np.median(np.diff(t)))
            work = raw.copy()
            temporary = np.zeros(len(raw), dtype=bool)
            for a, b in runs(gaps):
                if b - a <= 2 and a > 0 and b < len(raw):
                    work[a:b] = np.interp(np.arange(a, b), [a - 1, b], [raw[a - 1], raw[b]])
                    temporary[a:b] = True
            remaining = (work == -1) | ~np.isfinite(work)
            response = np.full(len(raw), np.nan)
            filtered = np.full(len(raw), np.nan)
            narrow = np.full(len(raw), np.nan)
            displacement = np.full(len(raw), np.nan)
            edges = np.zeros(len(raw), dtype=bool)
            short = np.zeros(len(raw), dtype=bool)
            failed = np.zeros(len(raw), dtype=bool)
            displacement_failed = np.zeros(len(raw), dtype=bool)
            segment_log = []
            for a, b in runs(~remaining):
                duration = (b - a) / fs
                segment = dict(event_id=eid, station=station, channel=channel, start_index=int(a), stop_index_exclusive=int(b), start_ATT_s=float(t[a]), end_ATT_s=float(t[b - 1]), duration_s=float(duration), sample_count=int(b - a))
                if duration < 60:
                    short[a:b] = True
                    segment['status'] = 'unprocessed_shorter_than_60s'
                    segment_log.append(segment)
                    continue
                signal = Trace(data=work[a:b].astype(np.float64), header=dict(tr.stats))
                signal.stats.starttime = origin + float(t[a])
                signal.stats.sampling_rate = 6.625
                edge_seconds = max(20.0, .03 * duration)
                edge_samples = int(np.ceil(edge_seconds * fs))
                edges[a:min(a + edge_samples, b)] = True
                edges[max(a, b - edge_samples):b] = True
                segment.update(edge_flag_each_side_s=edge_seconds, edge_flag_each_side_samples=edge_samples)
                try:
                    signal.detrend('linear')
                    signal.detrend('demean')
                    signal.remove_response(inventory=inventory, output='VEL', pre_filt=[.05, .1, 1.5, 2.0], water_level=None, zero_mean=True, taper=True, taper_fraction=.03)
                    response[a:b] = signal.data
                    filtered[a:b] = sosfiltfilt(butter(4, [.3, .9], fs=fs, btype='bandpass', output='sos'), signal.data)
                    narrow[a:b] = sosfiltfilt(butter(4, [.3, .5], fs=fs, btype='bandpass', output='sos'), signal.data)
                    segment.update(status='computed_not_formally_validated')
                except Exception as exc:
                    response[a:b] = np.nan
                    filtered[a:b] = np.nan
                    narrow[a:b] = np.nan
                    failed[a:b] = True
                    segment.update(status='processing_failed', error=str(exc))
                # Independent displacement branch: its failure never erases velocity.
                try:
                    disp_signal = Trace(data=work[a:b].astype(np.float64), header=dict(tr.stats))
                    disp_signal.stats.starttime = origin + float(t[a])
                    disp_signal.stats.sampling_rate = 6.625
                    disp_signal.detrend('linear')
                    disp_signal.detrend('demean')
                    disp_signal.remove_response(inventory=inventory, output='DISP', pre_filt=[.1, .3, .9, 1.1], water_level=None, zero_mean=True, taper=True, taper_fraction=.03)
                    displacement[a:b] = sosfiltfilt(butter(4, [.3, .5], fs=fs, btype='bandpass', output='sos'), disp_signal.data)
                    segment['displacement_status'] = 'computed_not_formally_validated'
                except Exception as exc:
                    displacement[a:b] = np.nan
                    displacement_failed[a:b] = True
                    segment.update(displacement_status='processing_failed', displacement_error=str(exc))
                segment_log.append(segment)
            for values in (response, filtered, narrow, displacement):
                values[gaps] = np.nan
            edges[gaps] = False
            short[gaps] = False
            failed[gaps] = False
            displacement_failed[gaps] = False
            assert np.all(~np.isfinite(response[gaps])) and np.all(~np.isfinite(filtered[gaps]))
            assert not np.any(edges & short)
            old_filtered = old_display_filter(t, old_velocity)
            show = (t >= WINDOW[0]) & (t <= WINDOW[1])
            restored = show & np.isfinite(filtered) & ~np.isfinite(old_filtered)
            metadata = dict(base, source_file=str(raw_path.relative_to(ROOT)), source_sha256=sha(raw_path), previous_npz=str(old_path.relative_to(ROOT)), previous_npz_sha256=sha(old_path), stationxml=str(inventory_path.relative_to(ROOT)), stationxml_sha256=sha(inventory_path), origin_earth_received=events[eid]['time_earth_received'], raw_counts_exactly_equal_archive=True, raw_units='unaltered digital units (DU), -1 is a missing-data sentinel', response_and_filtered_units='m/s, nominal StationXML response, absolute gain unverified', original_time_axis='t_nominal_s: original MiniSEED nominal timestamps minus NASA Earth-received origin', comparison_time_axis='t_ATT_s (also t): same sample order, ATT affine time correction only; no amplitude changes or resampling', clock=clock, effective_fs_hz=fs, response_nominal_fs_hz=6.625, original_delta_s=float(tr.stats.delta), processing_order=['Temporary interpolation only for enclosed gaps of at most 2 samples; never displayed as observations.', 'Split at remaining gaps and process segments of at least 60 s.', 'Linear detrend; demean; nominal response removal to velocity with pre_filt 0.05/0.1/1.5/2.0 Hz, water_level=None, 3% cosine taper.', 'Four-pole Butterworth bandpass using sosfiltfilt (forward-backward zero phase), independently for 0.3-0.9 and 0.3-0.5 Hz.', 'Restore all original gap samples to NaN after the full chain; do not remove segment edges.'], edge_policy='Flag max(20 s, 3% segment duration) at each segment end. Project provisional visualization rule, not a validated safe-window guarantee. Orange samples retained for diagnosis, not certified for inversion.', preprocessing_not_done=['No automatic despiking or deglitching.', 'No reconstruction of longer gaps.', 'No full gain-command reconstruction.', 'No displacement calculation and no claim to reproduce Nunn 2024 processing.', 'No late-coda qualification or inference.'], short_segment_minimum_s=60.0, segments=segment_log)
            metadata['preprocessing_not_done'].remove('No displacement calculation and no claim to reproduce Nunn 2024 processing.')
            metadata['preprocessing_not_done'].append('No exact reproduction of Nunn 2024: no 25 s envelope smoothing, different gap and segment policy.')
            metadata['temporary_interpolation_caveat'] = 'Restoring interpolated positions to missing does not remove their influence on neighbouring processed samples. Filter impulse response and segment-edge effects require separate validation.'
            filter_description = 'SciPy butter(N=4, Wn=[flo,fhi], btype=bandpass, output=sos, fs=effective_fs), followed by sosfiltfilt forward-backward zero-phase; N=4 is the prototype order, not the total composite bandpass order.'
            metadata['processing_order'][3] = filter_description + ' Independently computed for 0.3-0.9 and 0.3-0.5 Hz.'
            metadata['literature_displacement_branch'] = dict(output='DISP', pre_filt_hz=[.1,.3,.9,1.1], water_level=None, taper_fraction=.03, taper_fraction_status='Inherited project setting, not an asserted exact published value', final_bandpass_hz=[.3,.5], filter=filter_description, units='m, nominally calibrated', reference_basis='Nunn 2022 official processing example and Nunn 2024 Figure 1 frequency band', Nunn2024_DOI='10.3847/PSJ/ad83d2', scope='Separate literature-oriented comparison; not full replication and not validated absolute displacement')
            metadata['literature_displacement_branch']['official_example_url'] = 'https://github.com/cerinunn/pdart/blob/master/getting_started.ipynb'
            output = DATA / f'{eid}_{station}_{channel}.npz'
            np.savez_compressed(output, t=t, t_nominal_s=t_nominal, t_ATT_s=t, raw_counts=raw, original_gap_mask=gaps, velocity_response=response, velocity_03_09=filtered, velocity_03_05=narrow, displacement_03_05_m=displacement, processing_edge_mask=edges, short_segment_mask=short, processing_failed_mask=failed, displacement_failed_mask=displacement_failed, temporary_interpolation_mask=temporary, metadataJSON=np.array(json.dumps(metadata, ensure_ascii=False)))
            r = dict(base, status='computed_exploratory_not_qualified', archive_channel_present=True, npz=str(output.relative_to(ROOT)), npz_sha256=sha(output), raw_counts_exact_equal=True, gap_mask_exact_equal=True, time_axes_exact_checked=True, sample_count=len(raw), display_sample_count=int(show.sum()), window_start_s=WINDOW[0], window_end_s=WINDOW[1], raw_gap_fraction=float(gaps[show].mean()), old_display_blank_fraction=float((~np.isfinite(old_filtered[show])).mean()), new_display_blank_fraction=float((~np.isfinite(filtered[show])).mean()), new_processing_edge_fraction=float(edges[show].mean()), short_unprocessed_fraction=float(short[show].mean()), processing_failure_fraction=float(failed[show].mean()), recovered_display_fraction=float(restored.sum()/show.sum()), restored_does_not_mean_validated=True, temporary_interpolation_samples=int(temporary.sum()), continuous_segment_count=len(segment_log), processed_segment_count=sum(s['status']=='computed_not_formally_validated' for s in segment_log), short_segment_count=sum(s['status']=='unprocessed_shorter_than_60s' for s in segment_log), failed_segment_count=sum(s['status']=='processing_failed' for s in segment_log), nominal_to_ATT_shift_start_s=float(t[0]-t_nominal[0]), nominal_to_ATT_shift_end_s=float(t[-1]-t_nominal[-1]))
            for label, values in [('response_velocity', response), ('filtered_velocity', filtered), ('literature_displacement', displacement)]:
                edge_values = values[show & edges & np.isfinite(values)]
                interior_values = values[show & ~edges & np.isfinite(values)]
                edge_peak = float(np.max(abs(edge_values))) if len(edge_values) else 0.0
                interior_peak = float(np.max(abs(interior_values))) if len(interior_values) else 0.0
                r[label + '_edge_peak_SI'] = edge_peak
                r[label + '_interior_peak_SI'] = interior_peak
                r[label + '_edge_to_interior_peak_ratio'] = edge_peak/interior_peak if interior_peak else None
            r['displacement_processing_failure_fraction'] = float(displacement_failed[show].mean())
            r['displacement_failed_segment_count'] = sum(s.get('displacement_status')=='processing_failed' for s in segment_log)
            records.append(r)
            all_segments.extend(segment_log)
        print(f'processed {eid} {station}', flush=True)
    fields = list(dict.fromkeys(k for r in records for k in r))
    with (RES / 'trace_stage_comparison.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    (RES / 'segment_processing_log.json').write_text(json.dumps(all_segments, ensure_ascii=False, indent=2), encoding='utf-8')
    valid = [r for r in records if r.get('npz')]
    summary = dict(event_count=len(events), pair_count=len(pairs), requested_component_slots=len(records), processed_trace_count=len(valid), unavailable_components=[r for r in records if not r.get('npz')], all_raw_counts_match_archive=all(r['raw_counts_exact_equal'] for r in valid), all_masks_match_archive=all(r['gap_mask_exact_equal'] for r in valid), all_time_axes_verified=all(r['time_axes_exact_checked'] for r in valid), total_failed_segments=sum(r['failed_segment_count'] for r in valid), total_successful_segments=sum(r['processed_segment_count'] for r in valid), total_short_segments=sum(r['short_segment_count'] for r in valid), source_archive_sha256=raw_hashes, stationxml_sha256=sha(inventory_path), note='Displaying computed edge samples reduces blank areas without establishing new reliable observations. All outputs remain nominally calibrated exploratory diagnostics.', raw_overview_time='Original MiniSEED nominal timestamps', comparison_and_processed_overview_time='ATT affine-corrected timestamps; no sample/amplitude resampling')
    summary['total_displacement_failed_segments'] = sum(r['displacement_failed_segment_count'] for r in valid)
    (RES / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'source_archive_sha256'}, ensure_ascii=False, indent=2), flush=True)


def load(eid, station, channel):
    path = DATA / f'{eid}_{station}_{channel}.npz'
    if not path.exists():
        return None
    with np.load(path) as d:
        return {k: d[k].copy() for k in d.files if k != 'metadataJSON'} | {'meta': json.loads(str(d['metadataJSON']))}


def select_limit(values, mask, symmetric=False):
    a = np.concatenate([v[mask & np.isfinite(v)] for v in values])
    if not len(a):
        return (-1, 1)
    if symmetric:
        peak = max(float(np.max(abs(a))) * 1.07, 1e-6)
        return (-peak, peak)
    lo, hi = float(np.min(a)), float(np.max(a))
    pad = max((hi-lo)*.07, .6)
    return lo-pad, hi+pad


def mask_strip(ax, t, mask, low, high, color, hatch=None):
    if not np.any(mask):
        return
    dt = float(np.median(np.diff(t)))
    spans = [(t[a] - dt/2, (b-a)*dt) for a,b in runs(mask)]
    ax.broken_barh(spans, (low,high-low), transform=ax.get_xaxis_transform(), facecolors=color, alpha=.8 if hatch is None else .5, linewidth=0, hatch=hatch, zorder=4)


def draw_trace(ax, d, stage, window=WINDOW, nominal=False, ylimit=None):
    if d is None:
        ax.text(.5, .55, '档案未返回 MHZ\nS14 已知故障时段\n不以其他分量替代', transform=ax.transAxes, ha='center', va='center', fontsize=10, color='#555555')
        ax.set(xlim=window, ylim=(-1, 1), yticks=[])
        ax.grid(alpha=.12)
        return
    t = d['t_nominal_s'] if nominal else d['t_ATT_s']
    show = (t >= window[0]) & (t <= window[1])
    gap = d['original_gap_mask']
    if stage == 'raw':
        y = d['raw_counts'].copy()
        y[gap] = np.nan
    elif stage == 'displacement':
        y = d['displacement_03_05_m'] * 1e9
    else:
        y = d['velocity_response' if stage == 'response' else 'velocity_03_09'] * 1e9
    if stage == 'raw':
        ax.plot(t[show], y[show], color=COLORS['raw'], lw=.47, rasterized=False)
    else:
        affected = y.copy()
        affected[~d['processing_edge_mask']] = np.nan
        ax.plot(t[show], y[show], color=COLORS['filtered' if stage=='displacement' else stage], lw=.48)
        ax.plot(t[show], affected[show], color=COLORS['edge'], lw=.6)
        mask_strip(ax, t[show], d['processing_edge_mask'][show], .015, .045, COLORS['edge'])
        mask_strip(ax, t[show], d['short_segment_mask'][show], .055, .085, COLORS['short'], hatch='///')
        failure_mask = d['displacement_failed_mask'] if stage=='displacement' else d['processing_failed_mask']
        if np.any(failure_mask[show]):
            mask_strip(ax, t[show], failure_mask[show], .095, .125, '#7B3C8E')
            ax.text(.98,.88,'紫条：该处理支路失败',ha='right',transform=ax.transAxes,color='#7B3C8E',fontsize=8)
    mask_strip(ax, t[show], gap[show], .96, .99, COLORS['gap'])
    ax.axvline(0, color='#777777', ls='--', lw=.7, zorder=0)
    ax.grid(alpha=.15)
    ax.set_xlim(window)
    ax.set_ylim(ylimit if ylimit is not None else select_limit([y], show, symmetric=stage!='raw'))
    ax.ticklabel_format(axis='y', style='sci' if stage!='raw' else 'plain', scilimits=(-3, 4), useOffset=False)
    ax.tick_params(labelsize=9)


def save(fig, name, kind, provenance, manifest):
    paths = []
    for extension in ('png', 'pdf'):
        path = FIG / f'{name}.{extension}'
        fig.savefig(path, dpi=200, facecolor='white', transparent=False)
        paths.append(dict(path=str(path.relative_to(ROOT)), bytes=path.stat().st_size, sha256=sha(path)))
    manifest.append(dict(name=name, kind=kind, size_inches=list(fig.get_size_inches()), dpi_png=200, provenance=provenance, outputs=paths))
    plt.close(fig)


def legend_items(processed=True):
    items = [Patch(facecolor=COLORS['gap'], label='顶部灰条：原始缺样')]
    if processed:
        items += [Line2D([0], [0], color=COLORS['edge'], lw=2, label='橙线/底条：处理影响区（暂定，未验证）'), Patch(facecolor=COLORS['short'], hatch='///', label='浅橙斜线底条：短段未处理')]
    return items


def plot(event_filter=None):
    pairs = table('results/impact_pairs_literature.csv')
    events = list(dict.fromkeys(p['event_id'] for p in pairs))
    if event_filter:
        events = [e for e in events if e == event_filter]
    manifest = []
    style = {'font.sans-serif': ['Microsoft YaHei', 'DejaVu Sans'], 'axes.unicode_minus': False, 'font.size': 10, 'pdf.fonttype': 42, 'ps.fonttype': 42, 'path.simplify': False}
    with plt.rc_context(style):
        for eid in events:
            pp = [p for p in pairs if p['event_id']==eid]
            for pair in pp:
                station = pair['station']
                fig, axs = plt.subplots(3, 3, figsize=(15.7, 10.0), sharex=True)
                fig.subplots_adjust(left=.075, right=.985, bottom=.15, top=.83, hspace=.35, wspace=.25)
                for i, channel in enumerate(CHANNELS):
                    d = load(eid, station, channel)
                    shared = None
                    if d is not None:
                        use = (d['t_ATT_s'] >= WINDOW[0]) & (d['t_ATT_s'] <= WINDOW[1])
                        shared = select_limit([d['velocity_response']*1e9, d['velocity_03_09']*1e9], use, True)
                    for j, stage in enumerate(('raw', 'response', 'filtered')):
                        draw_trace(axs[i,j], d, stage, ylimit=shared if j else None)
                        if i==0:
                            axs[i,j].set_title(('A  原始数字计数（未去均值/滤波）', 'B  名义去响应速度', 'C  再滤波 0.3–0.9 Hz')[j], fontsize=11, pad=14)
                        axs[i,j].set_ylabel(channel + (' / DU' if j==0 else ' / nm/s'), fontsize=10)
                for ax in axs[-1]:
                    ax.set_xlabel('相对地面接收源时 / s（ATT 校正轴）')
                fig.suptitle(f'{eid} → {station}  |  震中距 {float(pair["distance_published_km"]):g} km\n三阶段同分量对照：仅校时，原始幅值逐样点保持；B/C 同行同纵轴范围', fontsize=15, y=.97)
                fig.legend(handles=legend_items(), loc='lower center', bbox_to_anchor=(.52,.075), ncol=3, frameon=False, fontsize=9)
                fig.text(.5,.035,'不逐道归一化、不削峰；不同分量纵轴可不同。名义速度尚未完成增益履历核验；橙色样点显示恢复不代表可靠数据增加。',ha='center',fontsize=10)
                save(fig, f'{eid}_{station}_three_stages', 'three_stage_pair_ATT_time', pair, manifest)
            for stage, suffix in [('raw', 'raw_archive_overview'), ('filtered', 'processed_03_09_overview'), ('displacement', 'literature_displacement_03_05_overview')]:
                fig, axs = plt.subplots(len(pp), 3, figsize=(15.7, 2.5*len(pp)+2.5), sharex=True, squeeze=False)
                fig.subplots_adjust(left=.075,right=.985,bottom=.17 if len(pp)<3 else .12,top=.79 if len(pp)<3 else .87,hspace=.42,wspace=.25)
                for i,pair in enumerate(pp):
                    for j,channel in enumerate(CHANNELS):
                        d=load(eid,pair['station'],channel)
                        draw_trace(axs[i,j], d, stage, nominal=stage=='raw')
                        axs[i,j].set_title(f'{pair["station"]}  {channel}  |  {float(pair["distance_published_km"]):g} km',fontsize=11,pad=10)
                        axs[i,j].set_ylabel('数字计数 / DU' if stage=='raw' else ('名义位移 / nm' if stage=='displacement' else '名义速度 / nm/s'),fontsize=10)
                for ax in axs[-1]:
                    ax.set_xlabel('相对地面接收源时 / s（原始名义时间）' if stage=='raw' else '相对地面接收源时 / s（ATT 校正）')
                title='原始档案三分量：保留偏置、真实计数与缺口；未滤波' if stage=='raw' else '处理后三分量：名义去响应 + 0.3–0.9 Hz；保留并标明边缘'
                subtitle='MiniSEED 原始名义时间轴；各面板纵轴可不同，无归一化' if stage=='raw' else 'ATT 校正时间轴；各面板纵轴可不同，无归一化；增益履历尚未核验'
                if stage=='displacement':
                    title='文献窄带参照：名义位移 + 0.3–0.5 Hz'
                    subtitle='参考 Nunn 2022 示例 / 2024 Fig.1；未做 25 s 包络，非完整复现；ATT 轴，各道刻度不同'
                fig.suptitle(f'{eid}  |  {title}\n{subtitle}',fontsize=14,y=.98)
                fig.legend(handles=legend_items(stage!='raw'),loc='lower center',bbox_to_anchor=(.52,.02),ncol=3,frameon=False,fontsize=9)
                save(fig,f'{eid}_{suffix}',suffix,dict(event_id=eid,time_axis='original MiniSEED nominal' if stage=='raw' else 'ATT corrected'),manifest)
            print(f'plotted {eid}',flush=True)
        for eid,station,channel,window in [('A15LM','S15','MHZ',(2920,3140)),('A14SIVB','S12','MHZ',(-100,300))]:
            if eid not in events:
                continue
            d=load(eid,station,channel)
            fig,axs=plt.subplots(3,1,figsize=(13.8,9.5),sharex=True)
            fig.subplots_adjust(left=.11,right=.98,bottom=.14,top=.84,hspace=.33)
            use=(d['t_ATT_s']>=window[0])&(d['t_ATT_s']<=window[1])
            shared=select_limit([d['velocity_response']*1e9,d['velocity_03_09']*1e9],use,True)
            for i,stage in enumerate(('raw','response','filtered')):
                draw_trace(axs[i],d,stage,window,ylimit=None if i==0 else shared)
                axs[i].set_ylabel(('A 原始\nDU','B 名义去响应\nnm/s','C 0.3–0.9 Hz\nnm/s')[i],fontsize=11)
            axs[-1].set_xlabel('相对地面接收源时 / s（ATT 校正；原始幅值未改）')
            fig.suptitle(f'{eid} → {station} {channel}  |  缺口与处理影响放大诊断\n灰条只代表原始缺样；橙线保留计算结果，不代表边缘已可靠',fontsize=15,y=.96)
            fig.legend(handles=legend_items(),loc='lower center',bbox_to_anchor=(.52,.035),ncol=3,frameon=False,fontsize=9)
            save(fig,f'{eid}_{station}_{channel}_gap_zoom','gap_zoom_three_stage',dict(event_id=eid,station=station,channel=channel,window_ATT_s=list(window)),manifest)
    manifest_path=RES/('figure_manifest.json' if not event_filter else f'figure_manifest_{event_filter}.json')
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(figures=len(manifest),png_pdf_files=2*len(manifest),manifest=str(manifest_path)),ensure_ascii=False),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--process-only',action='store_true')
    mode.add_argument('--plot-only',action='store_true')
    parser.add_argument('--event',help='Restrict figures to a single event; processing still audits all traces.')
    args=parser.parse_args()
    if not args.plot_only:
        process()
    if not args.process_only:
        plot(args.event)


if __name__=='__main__':
    main()
