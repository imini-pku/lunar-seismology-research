%% Compare release-wave waveforms from four simulations.
% The station ordering is rebuilt from gen_rel_station.py:
% r1 is the standalone S12 station; r2-r606 belong to rays 1-3 in order.

clear; close all; clc;

modelNames = { ...
    'Flat, no scatter', ...
    'Flat, scatter', ...
    'Topography, no scatter', ...
    'Topography, scatter'};
modelFiles = { ...
    'E:\project_releasy_flat_noscatter\output\station.nc', ...
    'E:\project_releasy_flat_scatter\output\station.nc', ...
    'E:\project_releasy_topo_noscatter\output\station.nc', ...
    'E:\project_releasy_topo_scatter\output\station.nc'};

component = 'Vz';
timeWindow = [];             % seconds; use [tStart tEnd] to crop all figures
stationStride = 20;          % make one offset figure per 20 stations on each ray
outputDir = fullfile(fileparts(mfilename('fullpath')), 'releasy_waveform_figures');
if ~exist(outputDir, 'dir'), mkdir(outputDir); end

colors = [0.00 0.45 0.74; 0.85 0.33 0.10; 0.49 0.18 0.56; 0.47 0.67 0.19];
[stationXY, rayStations] = buildStationGeometry();
sourceXY = [50000, 50000];  % from cgfd3d.revise.releasy.flat.noscatter.1500.400.sh
epicentralDistanceKm = hypot(stationXY(:, 1) - sourceXY(1), ...
                            stationXY(:, 2) - sourceXY(2)) / 1000;

models = cell(1, numel(modelFiles));
for modelIndex = 1:numel(modelFiles)
    models{modelIndex} = loadStationWaveforms(modelFiles{modelIndex}, component);
    assert(size(models{modelIndex}.waveforms, 2) == 606, ...
        '%s contains %d stations; 606 were expected.', modelFiles{modelIndex}, ...
        size(models{modelIndex}.waveforms, 2));
end

[commonTime, waveforms] = alignModelTimes(models, timeWindow);

% Figure 1: S12 (r1) waveform overlays.
figure('Color', 'w', 'Position', [80 80 1400 820]);
tiledlayout(2, 2, 'TileSpacing', 'compact', 'Padding', 'compact');
pairSets = {[1 2], [1 3], [2 4], [1 2 3 4]};
pairTitles = {'Model 1 + Model 2', 'Model 1 + Model 3', ...
              'Model 2 + Model 4', 'All four models'};
for panelIndex = 1:numel(pairSets)
    nexttile; hold on; box on; grid on;
    stationScale = max(abs(reshape(waveforms(1, :, :), [], 1)));
    for modelIndex = pairSets{panelIndex}
        plot(commonTime, waveforms(:, 1, modelIndex) / stationScale, ...
            'LineWidth', 1.15, 'Color', colors(modelIndex, :));
    end
    xlabel('Time (s)'); ylabel('Normalized V_z'); title(pairTitles{panelIndex});
    legend(modelNames(pairSets{panelIndex}), 'Location', 'best', 'Interpreter', 'none');
end
sgtitle('S12 (r1) waveform comparison');
saveFigure(gcf, fullfile(outputDir, 'figure1_S12_comparison'));

% Figures 2-4: four model traces offset vertically at every 20th station.
for rayIndex = 1:3
    stationNumbers = rayStations{rayIndex};
    selectedStations = stationNumbers(1:stationStride:end);
    if selectedStations(end) ~= stationNumbers(end)
        selectedStations(end + 1) = stationNumbers(end);
    end
    for stationNumber = selectedStations
        plotOffsetWaveforms(commonTime, squeeze(waveforms(:, stationNumber, :)), ...
            stationNumber, rayIndex, epicentralDistanceKm(stationNumber), ...
            modelNames, colors);
        saveFigure(gcf, fullfile(outputDir, sprintf('figure%d_ray%d_r%03d_offset', ...
            rayIndex + 1, rayIndex, stationNumber)));
        close(gcf);
    end
end

% Figure 5: time of peak waveform energy versus epicentral distance.
% For a velocity trace, maximum instantaneous energy is proportional to V_z^2;
% therefore its arrival time is the time of maximum absolute V_z.
riseTime = nan(606, 4);
for stationNumber = 1:606
    for modelIndex = 1:4
        trace = waveforms(:, stationNumber, modelIndex);
        [~, peakIndex] = max(abs(trace));
        riseTime(stationNumber, modelIndex) = commonTime(peakIndex);
    end
end

figure('Color', 'w', 'Position', [100 100 1250 900]);
tiledlayout(3, 1, 'TileSpacing', 'compact', 'Padding', 'compact');
for rayIndex = 1:3
    nexttile; hold on; box on; grid on;
    stationNumbers = rayStations{rayIndex};
    for modelIndex = 1:4
        plot(epicentralDistanceKm(stationNumbers), riseTime(stationNumbers, modelIndex), ...
            '-o', 'Color', colors(modelIndex, :), 'LineWidth', 1.15, ...
            'MarkerSize', 3, 'DisplayName', modelNames{modelIndex});
    end
    xlabel('Epicentral distance (km)'); ylabel('Peak-energy time (s)');
    title(sprintf('Ray %d', rayIndex));
    legend('Location', 'best', 'Interpreter', 'none');
end
sgtitle('Peak-energy arrival time versus epicentral distance');
saveFigure(gcf, fullfile(outputDir, 'figure5_peak_energy_time_vs_epicentral_distance'));

fprintf('Finished. Figures were saved in:\n%s\n', outputDir);

function model = loadStationWaveforms(ncFile, component)
    assert(isfile(ncFile), 'File not found: %s', ncFile);
    model.time = double(ncread(ncFile, 'time'));
    model.time = model.time(:);
    waveformData = double(ncread(ncFile, component));
    if size(waveformData, 1) ~= numel(model.time) && size(waveformData, 2) == numel(model.time)
        waveformData = waveformData.';
    end
    assert(size(waveformData, 1) == numel(model.time), ...
        'Unexpected %s dimensions in %s.', component, ncFile);
    model.waveforms = waveformData;
end

function [commonTime, alignedWaveforms] = alignModelTimes(models, timeWindow)
    startTime = max(cellfun(@(model) model.time(1), models));
    endTime = min(cellfun(@(model) model.time(end), models));
    if ~isempty(timeWindow)
        startTime = max(startTime, timeWindow(1));
        endTime = min(endTime, timeWindow(2));
    end
    assert(endTime > startTime, 'The selected time range is empty.');
    sampleIntervals = cellfun(@(model) median(diff(model.time)), models);
    commonDt = max(sampleIntervals);
    commonTime = (startTime:commonDt:endTime).';
    alignedWaveforms = zeros(numel(commonTime), 606, numel(models));
    for modelIndex = 1:numel(models)
        alignedWaveforms(:, :, modelIndex) = interp1(models{modelIndex}.time, ...
            models{modelIndex}.waveforms, commonTime, 'linear');
    end
end

function plotOffsetWaveforms(time, traces, stationNumber, rayIndex, distanceKm, modelNames, colors)
    figure('Color', 'w', 'Position', [120 120 1200 620]); hold on; box on; grid on;
    scale = max(abs(traces(:)));
    if scale == 0, scale = 1; end
    traces = traces / scale;
    offset = 2.4;
    for modelIndex = 1:4
        plot(time, traces(:, modelIndex) + (modelIndex - 1) * offset, ...
            'Color', colors(modelIndex, :), 'LineWidth', 1.05);
    end
    xlabel('Time (s)'); ylabel('Model (offset traces)');
    yticks((0:3) * offset); yticklabels(modelNames);
    title(sprintf('Ray %d, r%d, epicentral distance %.2f km', ...
        rayIndex, stationNumber, distanceKm));
end

function [stationXY, rayStations] = buildStationGeometry()
    sourceRayStart = [161310.0, 207630.0];
    rayTargets = [197256.0, 59703.0; 100000.0, 140000.0; 213000.0, 247000.0];
    stationStep = 1000.0;
    stationXY = [197256.0, 59703.0];  % r1: standalone S12
    rayStations = cell(1, 3);
    stationNumber = 2;
    for rayIndex = 1:3
        direction = rayTargets(rayIndex, :) - sourceRayStart;
        direction = direction / norm(direction);
        rayStations{rayIndex} = [];
        distanceAlongRay = stationStep;
        while true
            point = sourceRayStart + direction * distanceAlongRay;
            if point(1) < 0 || point(1) > 300000 || point(2) < 0 || point(2) > 300000
                break;
            end
            stationXY(end + 1, :) = round(point);
            rayStations{rayIndex}(end + 1) = stationNumber;
            stationNumber = stationNumber + 1;
            distanceAlongRay = distanceAlongRay + stationStep;
        end
    end
    assert(size(stationXY, 1) == 606, 'Generated %d stations, not 606.', size(stationXY, 1));
end

function saveFigure(figureHandle, filenameBase)
    savefig(figureHandle, [filenameBase, '.fig']);
    exportgraphics(figureHandle, [filenameBase, '.png'], 'Resolution', 250);
end
