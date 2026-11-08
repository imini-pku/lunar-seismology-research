% Generate 3-layer low velocity basin model with 3D von Karman random perturbation
% 最终修复版：解决所有运算符错误 + 分块扰动优化
clear all; close all; clc;

%% -------------------------- 0. 分块配置 -------------------------- %
block_size = 500;        % Z方向子块大小
use_single = true;      % 单精度
enable_visual = false;  % 关闭可视化

%% -------------------------- 1. 网格参数（保持不变） -------------------------- %
nghost = 3;
ni = 1200;
nj = 1200;
dx = 500;
dy = 500;
dz = 500;

nx = ni + 2 * nghost;
ny = nj + 2 * nghost;

x0 = 0.0 - nghost * dx;
y0 = 0.0 - nghost * dy;
x1d_regu = (0:nx-1) * dx + x0;
y1d_regu = (0:ny-1) * dy + y0;

%% -------------------------- 2. 地层结构与背景参数 -------------------------- %
num_of_intfce = 4;
num_of_point_per_lay = [12,10,33, 43];
dep = [2.5e3, 8.5e3, 13.5e3, 3e4,5e4];
Vp_bg = [1380,1380, 3200, 5500, 7550,7550];
Vs_bg = [600,600, 1600, 2700, 3700,3700];
rho_bg = [2600,2600, 2760, 2760, 3360,3360];

%% -------------------------- 3. von Karman参数 -------------------------- %
vk_params = [
    0.25, 1000, 1000, 1000, 5;
    0.25, 1000, 1000, 1000, 5;
    0.25, 1000, 1000, 1000, 5;
    0.25, 1000, 1000, 1000, 5;
    0.25, 1000, 1000, 1000, 5;
    0.25, 1000, 1000, 1000, 5
];
std_Vp = vk_params(:,5) ./ 100 .* Vp_bg;
std_Vs = vk_params(:,5) ./ 100 .* Vs_bg;
std_rho = vk_params(:,5) ./ 100 .* rho_bg;

%% -------------------------- 4. 界面高程 -------------------------- %
lay_elev = zeros(ny, nx, num_of_intfce);
% lay_elev(:,:,1) = 1e3 * load('rel_Z_20_60_topo.txt');
% lay_elev(:,:,2) = lay_elev(:,:,1) - 1e3;
% lay_elev(:,:,3) = 1e3 * load('rel2_Z_20_60_reg.txt');
% lay_elev(:,:,4) = 1e3 * load('rel2_Z_20_60_Mreg.txt');
% lay_elev(:,:,5) = 1e3 * load('rel2_Z_20_60_cmi.txt');
% lay_elev_6 = -dep(6) * ones(ny, nx);
lay_elev(:,:,1) = 1e2 * load('rel_Z_20_60_topo.txt');
lay_elev(:,:,2) = 1e3 * load('rel2_Z_20_60_reg.txt');
lay_elev(:,:,3) = 1e3 * load('rel2_Z_20_60_Mreg.txt');
lay_elev(:,:,4) = 1e3 * load('rel2_Z_20_60_cmi.txt');
lay_elev_5 = -dep(5) * ones(ny, nx);
if use_single
    lay_elev = single(lay_elev);
    lay_elev_5 = single(lay_elev_5);
end

%% -------------------------- 5. 分块生成扰动（最终修复） -------------------------- %
md.media_type = 'elastic_isotropic';
md.num_of_intfce = num_of_intfce;
md.num_of_point_per_lay = num_of_point_per_lay;
md.nx = nx; md.ny = ny; md.dx = dx; md.dy = dy; md.x0 = x0; md.y0 = y0;
md.elev = cell(1,5);
md.Vp = cell(1,5);
md.Vs = cell(1,5);
md.density = cell(1,5);

for ilay = 1:4
    nz_lay = num_of_point_per_lay(ilay);
    fprintf('处理第%d层（nz_lay=%d）...\n', ilay, nz_lay);
    
    % -------------------------- 修复：if-else替代三元运算符 -------------------------- %
    if ilay <= num_of_intfce
        elev_top = lay_elev(:,:,ilay);
        if ilay < num_of_intfce
            elev_bot = lay_elev(:,:,ilay+1);
        else
            elev_bot = lay_elev_5;
        end
    else
        elev_top = lay_elev_5;
        elev_bot = elev_top - (nz_lay - 1) * dz;
    end
    
    % -------------------------- 垂向高程计算（维度匹配） -------------------------- %
    ipt_vec = (0:nz_lay-1) / (nz_lay - 1);  % 1×nz_lay
    elev_top_3d = reshape(elev_top, ny, nx, 1);  % ny×nx×1
    elev_bot_3d = reshape(elev_bot, ny, nx, 1);  % ny×nx×1
    ipt_vec_3d = reshape(ipt_vec, 1, 1, nz_lay); % 1×1×nz_lay
    point_elev = elev_top_3d + (elev_bot_3d - elev_top_3d) .* ipt_vec_3d;
    
    % -------------------------- 修复：if-else替代三元运算符（dtype赋值） -------------------------- %
    if use_single
        dtype = 'single';
    else
        dtype = 'double';
    end
    point_Vp = Vp_bg(ilay) * ones(ny, nx, nz_lay, dtype);
    point_Vs = Vs_bg(ilay) * ones(ny, nx, nz_lay, dtype);
    point_rho = rho_bg(ilay) * ones(ny, nx, nz_lay, dtype);
    
    % -------------------------- Z方向分块生成扰动 -------------------------- %
    num_blocks = ceil(nz_lay / block_size);
    for b = 1:num_blocks
        z_start = (b - 1) * block_size + 1;
        z_end = min(b * block_size, nz_lay);
        z_len = z_end - z_start + 1;
        fprintf('  子块%d/%d：Z范围[%d,%d]（长度=%d）\n', b, num_blocks, z_start, z_end, z_len);
        
        % 分块生成von Karman扰动
        [field_vp_block, field_vs_block, field_rho_block] = generate_von_karman_3d_block(...
            vk_params(ilay,1), vk_params(ilay,2), vk_params(ilay,3), vk_params(ilay,4), ...
            nx, ny, z_len, dx, dy, dz, use_single);
        
        % 叠加扰动
        point_Vp(:,:,z_start:z_end) = point_Vp(:,:,z_start:z_end) + std_Vp(ilay) * field_vp_block;
        point_Vs(:,:,z_start:z_end) = point_Vs(:,:,z_start:z_end) + std_Vs(ilay) * field_vs_block;
        point_rho(:,:,z_start:z_end) = point_rho(:,:,z_start:z_end) + std_rho(ilay) * field_rho_block;
        
        % 释放子块内存
        clear field_vp_block field_vs_block field_rho_block;
    end
    
    % -------------------------- 维度置换与存储 -------------------------- %
    md.elev{ilay} = permute(point_elev, [2,1,3]);
    md.Vp{ilay} = permute(point_Vp, [2,1,3]);
    md.Vs{ilay} = permute(point_Vs, [2,1,3]);
    md.density{ilay} = permute(point_rho, [2,1,3]);
    
    % 释放该层内存
    clear point_elev point_Vp point_Vs point_rho elev_top elev_bot;
    fprintf('第%d层处理完成，已释放内存\n', ilay);
end

%% -------------------------- 6. 导出文件 -------------------------- %
fnm_ou = 'rel_nolow_VK_topo_1200_5_1000_block.md3grd';
disp('导出md3grd文件...');
md3grd_export(fnm_ou, md);
clear md;
fprintf('文件保存至：%s\n', fullfile(pwd, fnm_ou));

%% -------------------------- 核心函数：分块版3D von Karman -------------------------- %
function [field_vp, field_vs, field_rho] = generate_von_karman_3d_block(nu, ax, ay, az, nx, ny, nz_block, dx, dy, dz, use_single)
    % 修复：if-else替代三元运算符
    if use_single
        dtype = 'single';
    else
        dtype = 'double';
    end
    
    % 生成子块随机噪声
    noise_vp = randn(nx, ny, nz_block, dtype);
    noise_vs = randn(nx, ny, nz_block, dtype);
    noise_rho = randn(nx, ny, nz_block, dtype);
    
    % FFT
    fft_vp = fftn(noise_vp);
    fft_vs = fftn(noise_vs);
    fft_rho = fftn(noise_rho);
    
    % 波数网格
    kx = (0:nx-1)/nx*(2*pi/dx) - pi/dx;
    ky = (0:ny-1)/ny*(2*pi/dy) - pi/dy;
    kz = (0:nz_block-1)/nz_block*(2*pi/dz) - pi/dz;
    kx = fftshift(kx);
    ky = fftshift(ky);
    kz = fftshift(kz);
    [kx_grid, ky_grid, kz_grid] = ndgrid(kx, ky, kz);
    
    % von Karman谱
    k_scaled_sq = (ax*kx_grid).^2 + (ay*ky_grid).^2 + (az*kz_grid).^2;
    S = (1 + k_scaled_sq).^(-nu - 1.5);
    S(k_scaled_sq == 0) = 0;
    
    % 逆FFT与归一化
    field_vp = real(ifftn(fft_vp .* sqrt(S)));
    field_vs = real(ifftn(fft_vs .* sqrt(S)));
    field_rho = real(ifftn(fft_rho .* sqrt(S)));
    
    field_vp = (field_vp - mean(field_vp(:))) / std(field_vp(:));
    field_vs = (field_vs - mean(field_vs(:))) / std(field_vs(:));
    field_rho = (field_rho - mean(field_rho(:))) / std(field_rho(:));
    
    % 释放临时内存
    clear noise_vp noise_vs noise_rho fft_vp fft_vs fft_rho kx_grid ky_grid kz_grid S;
end

%% -------------------------- 辅助函数：可视化 -------------------------- %
function plot_visualization(lay_elev, lay_elev_6, num_of_point_per_lay, Vp_bg, Vs_bg, x1d_regu, y1d_regu)
    figure('Position', [100, 100, 1000, 600]);
    slice_x = round(length(x1d_regu)/2);
    slice_y = round(length(y1d_regu)/2);
    
    subplot(2,2,1);
    z1 = round(num_of_point_per_lay(1)/2);
    xlabel('X (km)'); ylabel('Y (km)'); title('Layer 1 Vp (X-Y)');
    colorbar; axis equal; caxis([Vp_bg(1)*0.9, Vp_bg(1)*1.1]);
    
    subplot(2,2,2);
    z2 = round(num_of_point_per_lay(2)/2);
    xlabel('X (km)'); ylabel('Y (km)'); title('Layer 2 Vp (X-Y)');
    colorbar; axis equal; caxis([Vp_bg(2)*0.9, Vp_bg(2)*1.1]);
    
    subplot(2,2,3);
    xlabel('X (km)'); ylabel('Z (km)'); title('Layer 1 Vs (X-Z)');
    colorbar; axis equal; caxis([Vs_bg(1)*0.9, Vs_bg(1)*1.1]);
    
    subplot(2,2,4);
    xlabel('X (km)'); ylabel('Z (km)'); title('Layer 2 Vs (X-Z)');
    colorbar; axis equal; caxis([Vs_bg(2)*0.9, Vs_bg(2)*1.1]);
    
    drawnow;
end

%% -------------------------- 辅助函数：分布绘图 -------------------------- %
function plot_distribution(data, name)
    data = data(:);
    [counts, edges] = histcounts(data, 50, 'Normalization', 'pdf');
    bin_centers = (edges(1:end-1) + edges(2:end))/2;
    
    mu = mean(data);
    sigma = std(data);
    gaussian = normpdf(bin_centers, mu, sigma);
    
    bar(bin_centers, counts, 'FaceAlpha', 0.6);
    hold on;
    plot(bin_centers, gaussian, 'r-', 'LineWidth', 2);
    xlabel('Value'); ylabel('Probability Density');
    legend('Sample', 'Normal Fit'); grid on;
    text(0.05, 0.9, sprintf('Mean=%.2f\nStd=%.2f', mu, sigma), ...
        'Units', 'normalized', 'BackgroundColor', 'w');
end