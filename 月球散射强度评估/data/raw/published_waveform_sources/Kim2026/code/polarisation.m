clear; clc; close all;

addpath('/home/usr/code/matlab/Tools/rotating_3d_globe/bin_geoid_3d')
addpath('/home/usr/code/matlab/Tools/Colormaps/')
addpath('/home/usr/code/matlab/Tools/m_map1.4/'); addpath('/home/usr/Lunar');
datpath = '/home/usr/Lunar/proc_lp12_inc/S4B-13_a12/'

show_fig = false;

addpath(datpath);
idx = 1;
evtlist = dir([datpath 'S4B-13_a12_uniform.mat']);
load([datpath evtlist(idx).name]);

Zwf = Z;
Nwf = N; 
Ewf = E;
clear Z N E

evtlons = [-27.86];
evtlats = [-2.75];

evtlon = evtlons(idx);
evtlat = evtlats(idx);

sta12 = [-23.4246 -3.0094];
sta14 = [-17.4775 -3.644];
sta15 = [3.6298 26.1341];
sta16= [15.4981 -8.9754];

Rmoon = 1737.4;
sperdeg_to_sperkm = 180/(pi*Rmoon);

% Time for SH 1976-03-06 in Lognonne et al., 2003

tp = [28];ts = [0];

tp = tp(1);
ts = ts(1);

% Confirm BAZ to previous BAZ estimates
%a12
spheroid = 'moon_sphere';[distance_m,a12_deg,a21_deg] = m_idist(sta12(1),sta12(2),evtlon,evtlat,spheroid); 
distance_km = distance_m/1000
%%
%%model='LOLA_16';  %resolution: 1/16 degree = 3.75 arcmin
%%fprintf('Loading Moon data: %s\n',model);
%%load(model);
fprintf('Station:  lat = %.4f deg, lon = %.4f deg\n', sta12(2), sta12(1));
fprintf('Event:    lat = %.4f deg, lon = %.4f deg\n', evtlat, evtlon);
fprintf('Distance (deg) = %.4f m\n', distance_m);
fprintf('Distance (km)  = %.4f km\n', distance_km);
fprintf('BAZ sta->evt = %.2f deg\n', a12_deg);
fprintf('BAZ evt->sta = %.2f deg\n', a21_deg);
model = 'moon-topography-10arcmin';
% Moon topography as 2D map
%figure;
ncfile = 'moon-topography-10arcmin.nc';
lat = ncread(ncfile,'latitude');      % [-90 .. 90]
lon = ncread(ncfile,'longitude');     % [0 .. 360]
topo = ncread(ncfile,'topography');   % meters, (lat, lon)

latd_moon = double(lat(:));            % column
lond_moon = double(lon(:))';           % row
elev_moon_km = double(topo)' / 1000;    % m → km
lond_moon(lond_moon > 180) = lond_moon(lond_moon > 180) - 360;

[lond_moon, idx_lon] = sort(lond_moon);
elev_moon_km = elev_moon_km(:, idx_lon);
latd_moon = flipud(latd_moon);
elev_moon_km = flipud(elev_moon_km);

size(elev_moon_km)
length(latd_moon)
length(lond_moon)
s = referenceSphere('Moon');
[mesh_lola_lon, mesh_lola_lat] = meshgrid(lond_moon,latd_moon);

[aspect,slope,gradN,gradE] = gradientm( ...
    mesh_lola_lat, mesh_lola_lon, ...
    elev_moon_km.*1000, s, 'degrees');

rotang = -90;
tmp = gradE.*cosd(rotang) + gradN.*sind(rotang);

% flip for station12
Nwf = -Nwf; Ewf = -Ewf;

%% Resample waveforms with a higher sampling rate

Flo = 0.1; Fhi = 1.1;

[tmp_z,tmp_p,tmp_k] = butter(4,[Flo/Fnyq Fhi/Fnyq],'bandpass'); 
[SOS,G] = zp2sos(tmp_z,tmp_p,tmp_k); 


Zfilt = filtfilt(SOS,G,(Zwf)); 
Efilt = filtfilt(SOS,G,(Ewf)); 
Nfilt = filtfilt(SOS,G,(Nwf)); 

if show_fig
    fig1 = figure;
else
    fig1 = figure('Visible','off');
end

plot(time, Zfilt); hold on; plot(time, Efilt); plot(time, Nfilt); 
title('Filtered Apollo Waveforms'); legend('Z','E','N'); xlabel('Time [s]'); ylabel('Amplitude [DU]');set(gcf,'Color','w');

% Save as PDF
exportgraphics(fig1, 'Filtered_Waveforms_A12_S4B-13_a12.pdf', 'ContentType','vector');
if ~show_fig; close(fig1); end

P_time = -45:dt:45; S_time = -45:dt:45;

Zp = interp1(time,Zfilt,P_time+tp,'nearest',0).*tukeywin(length(P_time),0.03)'; Zp = detrend(Zp); 
Np = interp1(time,Nfilt,P_time+tp,'nearest',0).*tukeywin(length(P_time),0.03)'; Np = detrend(Np); 
Ep = interp1(time,Efilt,P_time+tp,'nearest',0).*tukeywin(length(P_time),0.03)'; Ep = detrend(Ep); 

Zs = interp1(time,Zfilt,S_time+ts,'nearest',0).*tukeywin(length(S_time),0.03)'; Zs = detrend(Zs); 
Ns = interp1(time,Nfilt,S_time+ts,'nearest',0).*tukeywin(length(S_time),0.03)'; Ns = detrend(Ns); 
Es = interp1(time,Efilt,S_time+ts,'nearest',0).*tukeywin(length(S_time),0.03)'; Es = detrend(Es); 

%%

if show_fig
    fig100 = figure(100);
else
    fig100 = figure(100);
    set(fig100,'Visible','off');
end
dataP = [P_time(:) Ep(:) Np(:) Zp(:)];writematrix(dataP,'P_window_waveform.txt','Delimiter',' ');
plot(P_time, Ep, 'k', P_time, Np, 'b', P_time, Zp, 'r'); legend('EW','NS','UD'); xlim([-10 15]); xlabel('Time [s]'); ylabel('Amplitude (DU)'); title('Windowed Apollo Segment');
exportgraphics(fig100, 'Windowed_Segment_A12_S4B-13_a12.pdf', 'ContentType','vector');
if ~show_fig; close(fig100); end

%% run polarization analysis
deci_fac = 5;

Zp_tmp = decimate(Zp, deci_fac); 
Np_tmp = decimate(Np, deci_fac); 
Ep_tmp = decimate(Ep, deci_fac); 

Zs_tmp = decimate(Zs, deci_fac); 
Ns_tmp = decimate(Ns, deci_fac); 
Es_tmp = decimate(Es, deci_fac); 

Ep_tmp = Ep_tmp./max(abs(Zp_tmp)); Np_tmp = Np_tmp./max(abs(Zp_tmp)); Zp_tmp = Zp_tmp./max(abs(Zp_tmp));
Es_tmp = Es_tmp./max(abs(Zs_tmp)); Ns_tmp = Ns_tmp./max(abs(Zs_tmp)); Zs_tmp = Zs_tmp./max(abs(Zs_tmp));


[all_phiVH, all_ThetaH, all_phiHH, all_ThetaV, all_dop, all_planarity, all_linearity, all_specscale, all_ellip, freqs] =  fdpa_stransform(Zp_tmp,Ep_tmp,Np_tmp,1/(deci_fac*dt),P_time(1):deci_fac*dt:P_time(end),0.9);
[all_phiVH_S, all_ThetaH_S, all_phiHH_S, all_ThetaV_S, all_dop_S, all_planarity_S, all_linearity_S, all_specscale_S, all_ellip_S, freqs_S] =  fdpa_stransform(Zs_tmp,Es_tmp,Ns_tmp,1/(deci_fac*dt),S_time(1):deci_fac*dt:S_time(end),0.9);


movmeddur = 2; % Duration of moving median smoothing applied to HRM & VRM
N_pwr = 1/4; % Power to take when weighting

HRM = movmean(abs(cosd(all_phiHH)).*sind(all_ThetaV).*all_linearity.*(all_specscale.^N_pwr),movmeddur/(dt*deci_fac),2,'omitnan');
VRM = movmean(abs(cosd(all_phiVH)).*cosd(all_ThetaV).*all_linearity.*(all_specscale.^N_pwr),movmeddur/(dt*deci_fac),2,'omitnan'); 

HRM_S = movmean(abs(cosd(all_phiHH_S)).*sind(all_ThetaV_S).*all_linearity_S.*(all_specscale_S.^N_pwr),movmeddur/(dt*deci_fac),2,'omitnan');
VRM_S = movmean(abs(cosd(all_phiVH_S)).*cosd(all_ThetaV_S).*all_linearity_S.*(all_specscale_S.^N_pwr),movmeddur/(dt*deci_fac),2,'omitnan'); 

time_pol = P_time(1):deci_fac*dt:P_time(end);
timeplot = time_pol;
[TT, FF] = meshgrid(timeplot, freqs); 
if show_fig
    fig4 = figure(4); clf; hold on;
else
    fig4 = figure(4); clf;
    set(fig4,'Visible','off'); hold on;
end
set(fig4,'Units','pixels');
set(fig4,'Position',[100 50 600 900]); 
hold on;
Flo = 0.4
Fhi = 0.6

tmin = 0
tmax = 10
tmin_maxk=-10;tmax_mask=20;tmask = timeplot >= tmin_maxk & timeplot <= tmax_mask;
subplot(5,1,1); title('VRM');
contourf(timeplot, freqs, VRM,10,'edgecolor','none'); set(gca,'yscale','linear');
xlim([-10 20]);
ylabel('Frequency [Hz]'); VRM_orig=VRM;
VRM_ref = VRM(:,tmask);VRM_mean_ref = nanmean(VRM_ref(:));VRM_std_ref = nanstd(VRM_ref(:));
tmpV = VRM; tmpV(abs(tmpV)<VRM_mean_ref) = nan; VRM = tmpV;
VRM_mask = VRM; VRM_mask(isnan(VRM_mask)) = 0; VRM_mask(find(VRM_mask)) = 1;

bazvals = all_ThetaH.*VRM_mask; bazvals(find(bazvals==0)) = nan;

%% --- incidence angle (P-wave) ---
incvals = all_ThetaV .* VRM_mask;
incvals(incvals==0) = nan;

inc_use = incvals(freqs>Flo & freqs<Fhi,:);

inc_avg = nanmean(inc_use,1);
inc_std_time = nanstd(inc_use,0,1);

baz_use = bazvals(freqs>Flo & freqs<Fhi, :);
C = nanmean(cosd(baz_use), 1);   
S = nanmean(sind(baz_use), 1);
avgbaz = atan2d(S, C);   % [-180, 180]
avgbaz(avgbaz < 0) = avgbaz(avgbaz < 0) + 360;  % [0, 360]


subplot(5,1,2); 
contourf(timeplot, freqs, bazvals,10,'edgecolor','none'); set(gca,'yscale','linear');title('Direction of Propagation');xlim([-10 20]); ylim([0 1]);

subplot(5,1,3);
plot(timeplot, avgbaz); xlim([-10 20]); ylim([0 360]); xlabel('Time [s]'); ylabel('Angle'); title('Average direction');
colormap(cmocean('thermal'));

subplot(5,1,4);
contourf(timeplot, freqs, incvals,10,'edgecolor','none'); set(gca,'yscale','linear');title('Incidence');xlim([-10 20]); ylim([0 1]);

subplot(5,1,5);
plot(timeplot, inc_avg); xlim([-10 20]); ylim([0 90]); xlabel('Time [s]'); ylabel('Angle'); title('Average P-wave incidence');
colormap(cmocean('thermal'));
[TT, FF] = meshgrid(timeplot, freqs); writematrix([TT(:), FF(:), VRM_orig(:)],'subplot_510_VRMorig.txt','Delimiter','tab');
writematrix([TT(:), FF(:), VRM(:)], ...
    'subplot_511_VRM.txt','Delimiter','tab');
writematrix([TT(:), FF(:), bazvals(:)], ...
    'subplot_512_BAZ.txt','Delimiter','tab');
writematrix([timeplot(:), avgbaz(:)], ...
    'subplot_513_AvgBAZ.txt','Delimiter','tab');
writematrix([TT(:), FF(:), incvals(:)], ...
    'subplot_514_INC.txt','Delimiter','tab'); writematrix([timeplot(:), inc_avg(:)], 'subplot_515_AvgInc.txt','Delimiter','tab');
% Apply colormap to whole figure
colormap(fig4, cmocean('thermal'));
set(fig4,'Color','w');
exportgraphics(fig4, 'Polarization_VRM_Direction_S4B-13_a12.pdf','ContentType','vector');

if ~show_fig; close(fig4); end

if show_fig

    fig5 = figure(5); clf; hold on;
else
    fig5 = figure(5); clf;
    set(fig5,'Visible','off'); hold on;
end
plotavgbaz = avgbaz(timeplot>tmin & timeplot<tmax);
plotavgbaz(find(plotavgbaz==0)) = nan;
refang = atan2d( nanmean(sind(plotavgbaz)), ...
                 nanmean(cosd(plotavgbaz)) );
if refang < 0
    refang = refang + 360;
end
R = sqrt( nanmean(cosd(plotavgbaz))^2 + nanmean(sind(plotavgbaz))^2 );
sigma_u = sqrt(-2*log(R)) * (180/pi); baz_hist = plotavgbaz; edges = 0:20:360; 
baz_hist(baz_hist < refang-180) = baz_hist(baz_hist < refang-180) + 360; baz_plot = baz_hist; baz_plot(baz_plot >= 360) = baz_plot(baz_plot >= 360) - 360;
histogram(baz_plot, edges,'Normalization','pdf');hold on;
xlim([refang-3*sigma_u, refang+3*sigma_u]);
hold on;
x = linspace(0, 360, 720);
y  = normpdf(x, refang,        sigma_u) + ...
     normpdf(x, refang-360,    sigma_u) + ...
     normpdf(x, refang+360,    sigma_u);

gauss_curve = [x(:), y(:)];
writematrix(gauss_curve, 'hist_gaussian_curve.txt', 'Delimiter','tab');

plot(x, y, 'r', 'LineWidth', 2);
[counts, edges] = histcounts(plotavgbaz, 36);   % 10-deg bins

bin_centers = (edges(1:end-1) + edges(2:end)) / 2;
hist_data = [bin_centers(:), counts(:)];
writematrix(hist_data, 'histogram_bar_data.txt', 'Delimiter','tab');

[~, imax] = max(counts);
peak_angle = mean(edges(imax:imax+1));
pad = 10;  % deg margin
xlim([ ...
    min(plotavgbaz)-pad, ...
    max(plotavgbaz)+pad ]);
xlabel('Angle [deg]');
ylabel('PDF');
title('Histogram of Average BAZ');
xlabel('Angle [deg]'); ylabel('PDF'); title('Histogram of Average BAZ');
exportgraphics(fig5, 'Histogram_Avg_BAZ_S4B-13_a12.pdf','ContentType','vector');

if ~show_fig; close(fig5); end

fig_inc = figure;
if ~show_fig
    set(fig_inc,'Visible','off');
end

plot(timeplot, inc_avg,'k','LineWidth',2)
xlabel('Time [s]')
ylabel('Incidence angle (deg)')
title('Average P-wave incidence angle')
ylim([0 90])
grid on

exportgraphics(fig_inc, ...
    'Incidence_vs_Time_S4B-13_a12.pdf',...
    'ContentType','vector');

if ~show_fig
    close(fig_inc)
end

fig_inc_hist = figure;
if ~show_fig
    set(fig_inc_hist,'Visible','off');
end

inc_plot = inc_avg(timeplot>tmin & timeplot<tmax);

inc_mean = mean(inc_plot,'omitnan');
inc_std  = std(inc_plot,'omitnan');

histogram(inc_plot,20,'Normalization','pdf');
hold on

x = linspace(0,90,200);
y = normpdf(x,inc_mean,inc_std);

plot(x,y,'r','LineWidth',2)

xlabel('Incidence angle (deg)')
ylabel('PDF')

title(sprintf('Incidence angle mean %.2f deg, std %.2f deg', ...
    inc_mean, inc_std))

exportgraphics(fig_inc_hist, ...
    'Histogram_Incidence_S4B-13_a12.pdf',...
    'ContentType','vector');

if ~show_fig
    close(fig_inc_hist)
end

% Moon Topography

fig = figure('Color','w');
if ~show_fig
    set(fig,'Visible','off');
end
hold on

% Mollweide projection
m_proj('Mollweide','clongitude',0);
m_grid('xticklabels',[],'yticklabels',[], ...
       'linestyle','none','box','on');

ax = gca;       
hold(ax,'on');


%% Stations & Event
m_plot(sta12(1), sta12(2), 'b^', ...
    'LineWidth',2,'MarkerSize',16,'MarkerFaceColor',[1 1 0]);

m_plot(sta14(1), sta14(2), 'b^', ...
    'LineWidth',2,'MarkerSize',16,'MarkerFaceColor',[1 1 1]);

m_plot(sta15(1), sta15(2), 'b^', ...
    'LineWidth',2,'MarkerSize',16,'MarkerFaceColor',[1 1 1]);

m_plot(sta16(1), sta16(2), 'b^', ...
    'LineWidth',2,'MarkerSize',16,'MarkerFaceColor',[1 1 1]);

m_plot(evtlon, evtlat, 'ro', ...
    'LineWidth',2,'MarkerSize',16,'MarkerFaceColor',[1 1 0]);

%% Concentric circle
deg2km_lat = pi/180 * Rmoon;
deg2km_lon = pi/180 * Rmoon * cosd(sta12(2));

theta = linspace(0, 2*pi, 720);
X = sta12(1) + distance_km / deg2km_lon .* cos(theta);
Y = sta12(2) + distance_km / deg2km_lat .* sin(theta);
d = abs(diff(X)); idx = find(d>180); X2=X; Y2=Y;
X2(idx+1)=NaN; Y2(idx+1)=NaN;


m_plot(X, Y, 'c--', 'LineWidth', 2);

%theta = deg2rad(med);
%dtheta = deg2rad(sigma);
theta0 = deg2rad(refang);        % center angle
dtheta = deg2rad(sigma_u);     % half-width (± sigma)
% local EN coordinates
lat0 = deg2rad(sta12(2));
dLon = deg2rad(X2 - sta12(1));
dLat = deg2rad(Y2 - sta12(2));

%latcr = deg2rad(sta12(2));
%dLon = deg2rad(X2-sta12(1));
%dLat = deg2rad(Y2-sta12(2));
%E = Rmoon * cos(latcr) .* dLon; N = Rmoon .* dLat;
E = Rmoon * cos(lat0) .* dLon; N = Rmoon .* dLat;
ang = atan2(E, N);
%dang_to_target = atan2(sin(ang - theta), cos(ang - theta));
dang = atan2( sin(ang - theta0), cos(ang - theta0) );

% mask within ±sigma
mask = abs(dang) <= dtheta;

% keep only arc
Xr = X2; Yr = Y2;
Xr(~mask) = NaN;
Yr(~mask) = NaN;

% break connections where mask switches
ii = find(diff(mask) ~= 0);
Xr(ii+1) = NaN;
Yr(ii+1) = NaN;

m_plot(Xr, Yr, 'r-', 'LineWidth', 3);

%% --- Mark best direction point ---

[~, idx0] = min(abs(dang));
m_plot(X(idx0), Y(idx0), 'mo', ...
       'MarkerFaceColor','k', 'MarkerSize',12);

% Set renderer for vector export
set(fig,'Renderer','painters');

exportgraphics(fig, ...
    'Concentric_Circle_Projection_S4B-13_a12.pdf', ...
    'ContentType','vector');

if ~show_fig; close(fig); end


fig_zoom = figure('Color','w');
if ~show_fig
    set(fig_zoom,'Visible','off');
end
hold on

% Mollweide projection
m_proj('Mollweide','clongitude',sta12(1));
m_grid('xticklabels',[],'yticklabels',[], ...
       'linestyle','none','box','on');

axz = gca;
hold(axz,'on');

%% Plot only station & event
m_plot(sta12(1), sta12(2), 'b^', ...
    'LineWidth',2,'MarkerSize',18,'MarkerFaceColor',[1 1 0]);

m_plot(evtlon, evtlat, 'ro', ...
    'LineWidth',2,'MarkerSize',18,'MarkerFaceColor',[1 1 0]);

%% Concentric circle (same as before)
m_plot(X, Y, 'c--', 'LineWidth', 2);

%% BAZ arc
m_plot(Xr, Yr, 'r-', 'LineWidth', 3);
m_plot(X(idx0), Y(idx0), 'mo', ...
    'MarkerFaceColor','k','MarkerSize',12);

%% Zoom limits (IMPORTANT)

dlon_evt = (evtlon - sta12(1)) * cosd(sta12(2));
dlat_evt = (evtlat - sta12(2));
deg_evt = sqrt(dlon_evt.^2 + dlat_evt.^2);

% concentric circle radius in degrees
deg_circle_lon = distance_km / (pi/180 * Rmoon * cosd(sta12(2)));
deg_circle_lat = distance_km / (pi/180 * Rmoon);
deg_circle = max(deg_circle_lon, deg_circle_lat);

% final zoom radius (add margin)
deg_zoom = max(deg_circle, deg_evt) * 1.15;
lonlim = sta12(1) + [-deg_zoom deg_zoom];
latlim = sta12(2) + [-deg_zoom deg_zoom];
[xp, yp] = m_ll2xy(lonlim, latlim);
xlim(sort(xp));
ylim(sort(yp));


%% Export
set(fig_zoom,'Renderer','painters');
exportgraphics(fig_zoom, ...
    'Concentric_Circle_Zoom_Station_Event_S4B-13_a12.pdf', ...
    'ContentType','vector');

if ~show_fig
    close(fig_zoom);
end

circle_all = [X(:), Y(:)];
writematrix(circle_all, 'concentric_circle_all.txt','Delimiter','tab');

circle_arc = [Xr(:), Yr(:)];
writematrix(circle_arc, 'concentric_circle_arc.txt','Delimiter','tab');

best_point = [X(idx0), Y(idx0)];
writematrix(best_point, 'concentric_circle_best_point.txt','Delimiter','tab');

fid = fopen('final_event_baz_uncertainty.txt','w');
fprintf(fid, 'Average_BAZ_deg     %.3f\n', refang);
fprintf(fid, 'Sigma_deg           %.3f\n', sigma_u);
fprintf(fid, 'Resultant_R         %.3f\n', R);
fprintf(fid, 'Time_window_s       %.1f  %.1f\n', tmin, tmax);
fprintf(fid, 'Frequency_band_Hz   %.2f  %.2f\n', Flo, Fhi);
fclose(fid);

fid = fopen('final_event_incidence_stats.txt','w');

fprintf(fid,'Mean_incidence_deg    %.3f\n', inc_mean);
fprintf(fid,'Std_incidence_deg     %.3f\n', inc_std);
fprintf(fid,'Time_window_s         %.2f  %.2f\n', tmin, tmax);
fprintf(fid,'Frequency_band_Hz     %.2f  %.2f\n', Flo, Fhi);

fclose(fid);

writematrix([timeplot(:), inc_avg(:)], ...
    'incidence_vs_time.txt','Delimiter','tab');






Flo_list  = 0.3:0.02:0.45;
Fhi_list  = 0.7:0.02:0.95;

tmin_list  = -0.5:0.1:0.5;
tmax_list  = 3.82:0.2:6.08;

cnt = 1;

results = struct( ...
    'Flo',[], 'Fhi',[], ...
    'tmin',[], 'tmax',[], ...
    'refang',[], ...
    'sigma_u',[], ...
    'R',[], ...
    'Nsample',[], ...
    'dBAZ',[], ...
    'abs_dBAZ',[], ...
    'snr_Z',[], 'snr_N',[], 'snr_E',[], ...
    'snr_Z_dB',[], 'snr_N_dB',[], 'snr_E_dB',[], ...
    'inc_mean',[], ...
    'inc_std',[] ...
);

for iF = 1:length(Flo_list)
    for jF = 1:length(Fhi_list)

        Flo = Flo_list(iF);
        Fhi = Fhi_list(jF);

        % frequency mask
        fmask = freqs >= Flo & freqs <= Fhi;
        if sum(fmask) < 2
            continue
        end

	[b,a] = butter(4, [Flo Fhi]/Fnyq, 'bandpass');

        Zf = filtfilt(b,a, Zwf);
        Nf = filtfilt(b,a, Nwf);
        Ef = filtfilt(b,a, Ewf);

        for it1 = 1:length(tmin_list)
            for it2 = 1:length(tmax_list)

                tmin = tmin_list(it1);
                tmax = tmax_list(it2);

                if tmin >= tmax
                    continue
                end

                % time mask
                tmask = timeplot >= tmin & timeplot <= tmax;
                if sum(tmask) < 5
                    continue
                end

                % extract baz values
                baz_use = bazvals(fmask, tmask);
                baz_use = baz_use(:);
                baz_use(isnan(baz_use)) = [];

                if numel(baz_use) < 10
                    continue
                end

		inc_use = incvals(fmask, tmask);
		inc_use = inc_use(:);
		inc_use(isnan(inc_use)) = [];

		if numel(inc_use) < 10
		    continue
		end

		inc_mean = mean(inc_use);
		inc_std  = std(inc_use);
                % ---- circular statistics ----
                C = mean(cosd(baz_use));
                S = mean(sind(baz_use));

                refang = atan2d(S, C);
                if refang < 0
                    refang = refang + 360;
                end

                R = sqrt(C^2 + S^2);
                sigma_u = sqrt(-2*log(R)) * (180/pi);

		dBAZ = atan2d( ...
                    sind(refang - a12_deg), ...
                    cosd(refang - a12_deg) );    % [-180, 180]

                abs_dBAZ = abs(dBAZ);

		                % -------------------------
                % SNR calculation
                % -------------------------
                Lwin = tmax - tmin;

                % signal window
                sigmask = time >= tmin+tp & time <= tmax+tp;

                % noise window (before signal)
                noise_end   = tmin - 3+tp;
                noise_start = noise_end - Lwin;
                noisemask   = time >= noise_start & time <= noise_end;

                if sum(sigmask) < 5 || sum(noisemask) < 5
                    continue
                end

		                rms_sig_Z = rms(Zf(sigmask));
                rms_sig_N = rms(Nf(sigmask));
                rms_sig_E = rms(Ef(sigmask));

                rms_noi_Z = rms(Zf(noisemask));
                rms_noi_N = rms(Nf(noisemask));
                rms_noi_E = rms(Ef(noisemask));

                snr_Z = rms_sig_Z / rms_noi_Z;
                snr_N = rms_sig_N / rms_noi_N;
                snr_E = rms_sig_E / rms_noi_E;

                snr_Z_dB = 20*log10(snr_Z);
                snr_N_dB = 20*log10(snr_N);
                snr_E_dB = 20*log10(snr_E);

                % ---- store ----
                results(cnt).Flo      = Flo;
                results(cnt).Fhi      = Fhi;
                results(cnt).tmin     = tmin;
                results(cnt).tmax     = tmax;

                results(cnt).refang   = refang;
                results(cnt).sigma_u  = sigma_u;
                results(cnt).R        = R;
                results(cnt).Nsample  = numel(baz_use);

		results(cnt).dBAZ      = dBAZ;       % signed BAZ error [deg]
                results(cnt).abs_dBAZ  = abs_dBAZ;

                results(cnt).snr_Z    = snr_Z;
                results(cnt).snr_N    = snr_N;
                results(cnt).snr_E    = snr_E;

                results(cnt).snr_Z_dB = snr_Z_dB;
                results(cnt).snr_N_dB = snr_N_dB;
                results(cnt).snr_E_dB = snr_E_dB;		

		results(cnt).inc_mean = inc_mean;
		results(cnt).inc_std  = inc_std;

                cnt = cnt + 1;

            end
        end
    end
end

%% save results
T = struct2table(results);

writetable(T, ...
    'BAZ_sensitivity_Frequency_Time_Sweep.txt', ...
    'Delimiter','tab');

disp('=== Sensitivity sweep completed ===');
disp(['Total valid parameter sets: ', num2str(height(T))]);


sigma_all    = [results.sigma_u];
abs_dBAZ_all = [results.abs_dBAZ];

metric_all1 = abs_dBAZ_all;
metric_all2 = sigma_all + abs_dBAZ_all;

[metric_ref, iref] = min(metric_all1);
metric_ref = results(iref).sigma_u+results(iref).abs_dBAZ

fprintf('Reference metric (sigma_u + abs_dBAZ) = %.3f deg\n', metric_ref);
fprintf('  ref sigma_u   = %.3f deg\n', results(iref).sigma_u);
fprintf('  ref abs_dBAZ  = %.3f deg\n', results(iref).abs_dBAZ);
fprintf('  ref Flo/Fhi   = %.2f / %.2f Hz\n', ...
        results(iref).Flo, results(iref).Fhi);
fprintf('  ref tmin/tmax = %.2f / %.2f s\n', ...
        results(iref).tmin, results(iref).tmax);

%% ---- select robust cases ----
tol=1e-6
robust_idx = metric_all2 <= metric_ref +tol;
robust = results(robust_idx);

fprintf('Number of robust cases: %d\n', numel(robust));

%% ---- save robust cases separately (recommended) ----
Trobust = struct2table(robust);

writetable(Trobust, ...
    'BAZ_robust_cases_metricSigmaPlusBAZ.txt', ...
    'Delimiter','tab');

disp('Saved robust cases: BAZ_robust_cases_metricSigmaPlusBAZ.txt');

%% ---- density grid definition ----
df = 0.01;   % Hz resolution
dt = 0.05;   % s resolution

fgrid = 0.1:df:1.0;    
tgrid = -10:dt:20;

[FGRID, TGRID] = meshgrid(fgrid, tgrid);

density_TF = zeros(size(FGRID));
%% ---- accumulate robust window density ----
for k = 1:numel(robust)

    Flo  = robust(k).Flo;
    Fhi  = robust(k).Fhi;
    tmin = robust(k).tmin;
    tmax = robust(k).tmax;

    mask = (FGRID >= Flo & FGRID <= Fhi & ...
            TGRID >= tmin & TGRID <= tmax);

    density_TF(mask) = density_TF(mask) + 1;
end
density_norm = density_TF / max(density_TF(:));
out_raw = [TGRID(:), FGRID(:), density_TF(:)];
writematrix(out_raw, ...
    'robust_TF_density_raw.txt', ...
    'Delimiter','tab');
out_norm = [TGRID(:), FGRID(:), density_norm(:)];
writematrix(out_norm, ...
    'robust_TF_density_normalized.txt', ...
    'Delimiter','tab');


function [X,Y] = concentric_circle_coord(xc, yc, R, r)
    theta = linspace(0, 2*pi, 360);
    X = xc + r * cos(theta);
    Y = yc + r * sin(theta);
end

