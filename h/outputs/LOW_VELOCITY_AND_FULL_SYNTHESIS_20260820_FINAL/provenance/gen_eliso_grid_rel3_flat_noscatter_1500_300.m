% Generate a low velocity basin model 
clear all;
close all;
% 兜底：切换软件渲染，不占用显卡显存
opengl('save','software');

%------------------------------------------------------------------------------
%-- x and y sampling
%------------------------------------------------------------------------------
nghost = 3;
nx = 1506;
ny = 1506;
dx = 200;
dy = 200;
x0 = 0.0 - nghost * dx;
y0 = 0.0 - nghost * dy;
Lx = nx * dx;
Ly = ny * dy;

x1d = [0 : nx-1] * dx + x0;
y1d = [0 : ny-1] * dy + y0;

%------------------------------------------------------------------------------
%-- velocity structures
%------------------------------------------------------------------------------
num_of_intfce = 34;
% 批量定义33层每层采样点数，替代逐行赋值
num_of_point_per_lay = [2,2,2,2,2, ...
    5,5,5,5,5,5,5,5, ...
    10,10,10,10,10,10,10,10,10,10,10,10,10,10,10, ...
    20,20,20,20,20];
dz = 100;

%-- backround 1D structure
%- roughly depth of each interface
dep     = [0, 2e2, 4e2,6e2,8e2,10e2,15e2,2e3,2.5e3,3e3,3.5e3,4e3,4.5e3,5e3,6e3,7e3,8e3,9e3,1e4,11e3,12e3,13e3,14e3,15e3,16e3,17e3,18e3,19e3,20e3,22e3,24e3,26e3,28e3,3e4];
Vp      = [2541, 2613, 2685, 2756, 2826, 2896, 3068, 3236, 3400, 3559, 3713, 3862, 4006, 4146, 4409, 4653, 4878, 5084, 5274, 5447, 5605, 5750, 5881, 6001, 6109, 6208, 6298, 6379, 6452, 6580, 6684, 6769, 6839, 6896];
Vs      = [1271, 1307, 1342, 1378, 1413, 1448, 1534, 1618, 1700, 1779, 1856, 1931, 2003, 2073, 2205, 2327, 2439, 2542, 2637, 3145, 3236, 3320, 3395, 3464, 3527, 3584, 3636, 3683, 3725, 3799, 3859, 3908, 3948, 3981];
den     = [2308.0, 2323.9, 2339.4, 2354.7, 2369.6, 2384.2, 2419.6, 2453.1, 2485.0, 2515.3, 2544.1, 2571.4, 2597.4, 2622.1, 2667.9, 2709.2, 2746.5, 2780.3, 2810.7, 2838.2, 2863.0, 2885.4, 2905.6, 2923.9, 2940.4, 2955.3, 2968.8, 2980.9, 2991.9, 3010.7, 3026.1, 3038.6, 3048.9, 3057.2];

%-- set interface topography (all flat)
lay_elev = zeros(ny, nx, num_of_intfce);
for n = 1 : num_of_intfce
    lay_elev(:,:,n) = -dep(n);
end

%------------------------------------------------------------------------------
%-- Initialize md struct cell storage, 仅存md，不缓存全局point数组
%------------------------------------------------------------------------------
num_layer = num_of_intfce - 1;
md.elev     = cell(num_layer, 1);
md.Vp       = cell(num_layer, 1);
md.Vs       = cell(num_layer, 1);
md.density  = cell(num_layer, 1);

% 分层循环：计算一层存入md，立刻清空临时三维变量，无全局point缓存
for ilay = 1 : num_layer
    elev_top_mat = lay_elev(:,:,ilay);      % [ny,nx]
    elev_bot_mat = lay_elev(:,:,ilay+1);    % [ny,nx]
    Npt = num_of_point_per_lay(ilay);
    
    weight = linspace(0, 1, Npt);
    dz_mat = elev_bot_mat - elev_top_mat;
    
    % 临时生成 [ny,nx,Npt]，转置直接得到目标 [nx,ny,Npt]，删除permute
    tmp_ny_nx_npt = elev_top_mat + dz_mat .* reshape(weight,1,1,Npt);
    tmp_elev = permute(tmp_ny_nx_npt, [2,1,3]);
    
    % 物性矩阵直接生成目标维度 [nx,ny,Npt]
    tmp_Vp  = Vp(ilay+1)  * ones(nx, ny, Npt);
    tmp_Vs  = Vs(ilay+1)  * ones(nx, ny, Npt);
    tmp_den = den(ilay+1) * ones(nx, ny, Npt);
    
    % 直接存入md，不再额外拷贝
    md.elev{ilay}    = tmp_elev;
    md.Vp{ilay}      = tmp_Vp;
    md.Vs{ilay}      = tmp_Vs;
    md.density{ilay} = tmp_den;
    
    % 强制清空本层临时大数组，释放内存
    clear tmp_ny_nx_npt tmp_elev tmp_Vp tmp_Vs tmp_den;
    drawnow;
end

%------------------------------------------------------------------------------
%-- plot 绘图段完全保留，默认关闭不占用内存
%------------------------------------------------------------------------------
flag_plot = 0;
if flag_plot
    % 绘图才生成x2d，不绘图不创建大网格数组省内存
    [x2d, y2d] = meshgrid(x1d,y1d);
    ds = 10; 
    xs = x2d(1:ds:end,1:ds:end);
    ys = y2d(1:ds:end,1:ds:end);
    for n = 1 : num_layer
        figure;
        surf(xs, ys, permute(md.elev{n}(:,:,1),[2,1]), md.Vp{n}(:,:,1));
        colorbar; title(['Layer ',num2str(n),' Vp top']);
        exportgraphics(gcf,['vp_layer_',num2str(n),'.png'],'Resolution',120);
        close(gcf);
    end
    clear x2d y2d xs ys;
end

%------------------------------------------------------------------------------
%-- fill md3grd metadata
%------------------------------------------------------------------------------
md.media_type = 'elastic_isotropic';
md.num_of_intfce = num_layer;  % md内该字段代表地层数量33
md.num_of_point_per_lay = num_of_point_per_lay;

md.nx = nx;
md.ny = ny;
md.dx = dx;
md.dy = dy;
md.x0 = x0;
md.y0 = y0;

%------------------------------------------------------------------------------
%-- export, 导出前清理无关大数组
%------------------------------------------------------------------------------
fnm_ou = 'rel3_flat_noscatter_1500_300_el_iso.nc';
clear lay_elev;
drawnow;
func_export_md3grd_nc(fnm_ou, md);