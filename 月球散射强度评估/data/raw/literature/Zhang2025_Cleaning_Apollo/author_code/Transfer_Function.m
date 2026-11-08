%% Transfer function
clear; clc

intp = 8;
in_sps  = 6.625;        %The input sampling rate
NS = 1500;
dti=1/in_sps;
dt = dti/intp; % dt after interp
NSi=intp*NS;

signal=zeros(1,NSi);
signal(1000:end)=10^-7; % step signal

%% parameters
K1=500000;  K3=31.6; K=204.8;
fa=0.0628; fl=8.72665; fd=47.62; ff=0.000997;

%h=0.85;
h=0.6:0.01:1.1;
%f0=0.06667;
f0=0.045:0.001:0.085;
f0=f0*2*pi;
%K2=0.000016;
K2=0.000013:0.0000001:0.000019;

G=(2680/(2680+1800));  G2=23700;  fb=0.31416;  fp=57.1199;
%G1=175;
G1=150:1:200;
%f0_sp=1;
f0_sp=0.5:0.1:1.5;
f0_sp=f0_sp*2*pi;


fs=1/dt;
f=linspace(-fs/2,fs/2,NSi)*2*pi;

%% set up matrices
sysvel_acc_p=cell(length(f0),length(h),length(K2));
sysvel_acc_f=cell(length(f0),length(h),length(K2));
sysvel_acc_sp=cell(length(f0_sp),length(h),length(G1));
ifft_sysvel_acc_p=cell(length(f0),length(h),length(K2));
ifft_sysvel_acc_f=cell(length(f0),length(h),length(K2));
ifft_sysvel_acc_sp=cell(length(f0_sp),length(h),length(G1));
green_acc_p=cell(length(f0),length(h),length(K2));
green_acc_f=cell(length(f0),length(h),length(K2));
green_acc_sp=cell(length(f0),length(h),length(K2));
gr_acc_p=cell(length(f0),length(h),length(K2));
gr_acc_f=cell(length(f0),length(h),length(K2));
gr_acc_sp=cell(length(f0_sp),length(h),length(G1));

%% Acceleration step convolute with transfer function
for jjj=1:length(f0)
    for jj=1:length(h)
        for j=1:length(K2)
            sysvel_acc_p{jjj,jj,j}(:)=K*K3*((f*1i)./(fa+f*1i)).*(fl^2./((f*1i).^2+2*cos(pi/8)*fl*f*1i+fl^2)).^2.*(fl^2./((f*1i).^2+2*cos(3*pi/8)*fl*f*1i+fl^2)).^2.*(K1*(1./((f*1i).^2+2*h(jj)*f0(jjj)*f*1i+f0(jjj)^2)).*(fd./(fd+f*1i))./(1+K1*K2(j)*(1./((f*1i).^2+2*h(jj)*f0(jjj)*f*1i+f0(jjj)^2))*fd./(fd+f*1i)));
        end
    end
end

for jjj=1:length(f0)
    for jj=1:length(h)
        for j=1:length(K2)
            sysvel_acc_f{jjj,jj,j}(:)=K*K3*((f*1i)./(fa+f*1i)).*(fl^2./((f*1i).^2+2*cos(pi/8)*fl*f*1i+fl^2)).^2.*(fl^2./((f*1i).^2+2*cos(3*pi/8)*fl*f*1i+fl^2)).^2.*(K1*(1./((f*1i).^2+2*h(jj)*f0(jjj)*f*1i+f0(jjj)^2)).*(fd./(fd+f*1i))./(1+K1*K2(j)*(1./((f*1i).^2+2*h(jj)*f0(jjj)*f*1i+f0(jjj)^2))*fd./(fd+f*1i)*ff./(ff+f*1i)));
        end
    end
end


for jjj=1:length(f0_sp)
    for jj=1:length(h)
        for j=1:length(G1)
            sysvel_acc_sp{jjj,jj,j}(:)=K*G*G1(j)*G2*((f*1i)./((f*1i).^2+2*h(jj)*f0_sp(jjj)*f*1i+f0_sp(jjj)^2)).*((f*1i)./(fb+f*1i)).*(fp^2./((f*1i).^2+2*cos(pi/8)*fp*f*1i+fp^2)).^2.*(fp^2./((f*1i).^2+2*cos(3*pi/8)*fp*f*1i+fp^2)).^2;
        end
    end
end

for jjj=1:length(f0)
    for jj=1:length(h)
        for j=1:length(K2)
            ifft_sysvel_acc_p{jjj,jj,j}(:)=ifft(ifftshift(sysvel_acc_p{jjj,jj,j}(:)),'symmetric');
        end
    end
end
for jjj=1:length(f0)
    for jj=1:length(h)
        for j=1:length(K2)
            ifft_sysvel_acc_f{jjj,jj,j}(:)=ifft(ifftshift(sysvel_acc_f{jjj,jj,j}(:)),'symmetric');
        end
    end
end
for jjj=1:length(f0_sp)
    for jj=1:length(h)
        for j=1:length(G1)
            ifft_sysvel_acc_sp{jjj,jj,j}(:)=ifft(ifftshift(sysvel_acc_sp{jjj,jj,j}(:)),'symmetric');
        end
    end
end

clear sysvel_acc_sp sysvel_acc_p sysvel_acc_f
for jjj=1:length(f0)
    for jj=1:length(h)
        for j=1:length(K2)
            gr_acc_p{jjj,jj,j}(:)=conv(signal,ifft_sysvel_acc_p{jjj,jj,j}(:));
            green_acc_p{jjj,jj,j}(:)=gr_acc_p{jjj,jj,j}(1:NSi);
        end
    end
end

clear gr_acc_p ifft_sysvel_acc_p
for jjj=1:length(f0)
    for jj=1:length(h)
        for j=1:length(K2)
            gr_acc_f{jjj,jj,j}(:)=conv(signal,ifft_sysvel_acc_f{jjj,jj,j}(:));
            green_acc_f{jjj,jj,j}(:)=gr_acc_f{jjj,jj,j}(1:NSi);
        end
    end
end

clear gr_acc_f ifft_sysvel_acc_f
for jjj=1:length(f0_sp)
    for jj=1:length(h)
        for j=1:length(G1)
            gr_acc_sp{jjj,jj,j}(:)=conv(signal,ifft_sysvel_acc_sp{jjj,jj,j}(:));
            green_acc_sp{jjj,jj,j}(:)=gr_acc_sp{jjj,jj,j}(1:NSi);
        end
    end
end
clear gr_acc_sp ifft_sysvel_acc_sp

save('transfer_function1.mat','green_acc_sp','green_acc_f','green_acc_p','h','k2','f0','f0_sp','G1','-v7.3')
clear green_acc_f  green_acc_p green_acc_sp

%% set up matrices
sysvel_vel_p=cell(length(f0),length(h),length(K2));
sysvel_vel_f=cell(length(f0),length(h),length(K2));
sysvel_vel_sp=cell(length(f0_sp),length(h),length(G1));
ifft_sysvel_vel_p=cell(length(f0),length(h),length(K2));
ifft_sysvel_vel_f=cell(length(f0),length(h),length(K2));
ifft_sysvel_vel_sp=cell(length(f0_sp),length(h),length(G1));
green_vel_p=cell(length(f0),length(h),length(K2));
green_vel_f=cell(length(f0),length(h),length(K2));
green_vel_sp=cell(length(f0_sp),length(h),length(G1));
gr_vel_p=cell(length(f0),length(h),length(K2));
gr_vel_f=cell(length(f0),length(h),length(K2));
gr_vel_sp=cell(length(f0_sp),length(h),length(G1));

%% Velocity step convolute with transfer function
for jjj=1:length(f0)
    for jj=1:length(h)
        for j=1:length(K2)
            sysvel_vel_p{jjj,jj,j}(:)=(f*1i).*K*K3.*((f*1i)./(fa+f*1i)).*(fl^2./((f*1i).^2+2*cos(pi/8)*fl*f*1i+fl^2)).^2.*(fl^2./((f*1i).^2+2*cos(3*pi/8)*fl*f*1i+fl^2)).^2.*(K1*(1./((f*1i).^2+2*h(jj)*f0(jjj)*f*1i+f0(jjj)^2)).*(fd./(fd+f*1i))./(1+K1*K2(j)*(1./((f*1i).^2+2*h(jj)*f0(jjj)*f*1i+f0(jjj)^2))*fd./(fd+f*1i)));
        end
    end
end

for jjj=1:length(f0)
    for jj=1:length(h)
        for j=1:length(K2)
            sysvel_vel_f{jjj,jj,j}(:)=(f*1i).*K*K3.*((f*1i)./(fa+f*1i)).*(fl^2./((f*1i).^2+2*cos(pi/8)*fl*f*1i+fl^2)).^2.*(fl^2./((f*1i).^2+2*cos(3*pi/8)*fl*f*1i+fl^2)).^2.*(K1*(1./((f*1i).^2+2*h(jj)*f0(jjj)*f*1i+f0(jjj)^2)).*(fd./(fd+f*1i))./(1+K1*K2(j)*(1./((f*1i).^2+2*h(jj)*f0(jjj)*f*1i+f0(jjj)^2))*fd./(fd+f*1i)*ff./(ff+f*1i)));
        end
    end
end

for jjj=1:length(f0_sp)
    for jj=1:length(h)
        for j=1:length(G1)
            sysvel_vel_sp{jjj,jj,j}(:)=(f*1i).*K*G*G1(j)*G2.*((f*1i)./((f*1i).^2+2*h(jj)*f0_sp(jjj)*f*1i+f0_sp(jjj)^2)).*((f*1i)./(fb+f*1i)).*(fp^2./((f*1i).^2+2*cos(pi/8)*fp*f*1i+fp^2)).^2.*(fp^2./((f*1i).^2+2*cos(3*pi/8)*fp*f*1i+fp^2)).^2;
        end
    end
end

for jjj=1:length(f0)
    for jj=1:length(h)
        for j=1:length(K2)
            ifft_sysvel_vel_p{jjj,jj,j}(:)=ifft(ifftshift(sysvel_vel_p{jjj,jj,j}(:)),'symmetric');
        end
    end
end
for jjj=1:length(f0)
    for jj=1:length(h)
        for j=1:length(K2)
            ifft_sysvel_vel_f{jjj,jj,j}(:)=ifft(ifftshift(sysvel_vel_f{jjj,jj,j}(:)),'symmetric');
        end
    end
end

for jjj=1:length(f0_sp)
    for jj=1:length(h)
        for j=1:length(G1)
            ifft_sysvel_vel_sp{jjj,jj,j}(:)=ifft(ifftshift(sysvel_vel_sp{jjj,jj,j}(:)),'symmetric');
        end
    end
end

clear sysvel_vel_sp sysvel_vel_p sysvel_vel_f
for jjj=1:length(f0)
    for jj=1:length(h)
        for j=1:length(K2)
            gr_vel_p{jjj,jj,j}(:)=conv(signal,ifft_sysvel_vel_p{jjj,jj,j}(:));
            green_vel_p{jjj,jj,j}(:)=gr_vel_p{jjj,jj,j}(1:NSi);
        end
    end
end
clear gr_vel_p ifft_sysvel_vel_p
for jjj=1:length(f0)
    for jj=1:length(h)
        for j=1:length(K2)
            gr_vel_f{jjj,jj,j}(:)=conv(signal,ifft_sysvel_vel_f{jjj,jj,j}(:));
            green_vel_f{jjj,jj,j}(:)=gr_vel_f{jjj,jj,j}(1:NSi);
        end
    end
end
clear gr_vel_f ifft_sysvel_vel_f
for jjj=1:length(f0_sp)
    for jj=1:length(h)
        for j=1:length(G1)
            gr_vel_sp{jjj,jj,j}(:)=conv(signal,ifft_sysvel_vel_sp{jjj,jj,j}(:));
            green_vel_sp{jjj,jj,j}(:)=gr_vel_sp{jjj,jj,j}(1:NSi);
        end
    end
end
clear gr_vel_sp ifft_sysvel_vel_sp
save('transfer_function2.mat','green_vel_sp','green_vel_f','green_vel_p','-v7.3')
clear green_vel_f  green_vel_p green_vel_sp

%% set up matrices
sysvel_dis_p=cell(length(f0),length(h),length(K2));
sysvel_dis_f=cell(length(f0),length(h),length(K2));
sysvel_dis_sp=cell(length(f0_sp),length(h),length(G1));
ifft_sysvel_dis_p=cell(length(f0),length(h),length(K2));
ifft_sysvel_dis_f=cell(length(f0),length(h),length(K2));
ifft_sysvel_dis_sp=cell(length(f0_sp),length(h),length(G1));
green_dis_p=cell(length(f0),length(h),length(K2));
green_dis_f=cell(length(f0),length(h),length(K2));
green_dis_sp=cell(length(f0_sp),length(h),length(G1));
gr_dis_p=cell(length(f0),length(h),length(K2));
gr_dis_f=cell(length(f0),length(h),length(K2));
gr_dis_sp=cell(length(f0_sp),length(h),length(G1));

%% Displacement step convolute with transfer function
for jjj=1:length(f0)
    for jj=1:length(h)
        for j=1:length(K2)
            sysvel_dis_p{jjj,jj,j}(:)=(f*1i).^2.*K*K3.*((f*1i)./(fa+f*1i)).*(fl^2./((f*1i).^2+2*cos(pi/8)*fl*f*1i+fl^2)).^2.*(fl^2./((f*1i).^2+2*cos(3*pi/8)*fl*f*1i+fl^2)).^2.*(K1*(1./((f*1i).^2+2*h(jj)*f0(jjj)*f*1i+f0(jjj)^2)).*(fd./(fd+f*1i))./(1+K1*K2(j)*(1./((f*1i).^2+2*h(jj)*f0(jjj)*f*1i+f0(jjj)^2))*fd./(fd+f*1i)));
        end
    end
end

for jjj=1:length(f0)
    for jj=1:length(h)
        for j=1:length(K2)
            sysvel_dis_f{jjj,jj,j}(:)=(f*1i).^2.*K*K3.*((f*1i)./(fa+f*1i)).*(fl^2./((f*1i).^2+2*cos(pi/8)*fl*f*1i+fl^2)).^2.*(fl^2./((f*1i).^2+2*cos(3*pi/8)*fl*f*1i+fl^2)).^2.*(K1*(1./((f*1i).^2+2*h(jj)*f0(jjj)*f*1i+f0(jjj)^2)).*(fd./(fd+f*1i))./(1+K1*K2(j)*(1./((f*1i).^2+2*h(jj)*f0(jjj)*f*1i+f0(jjj)^2))*fd./(fd+f*1i)*ff./(ff+f*1i)));
        end
    end
end

for jjj=1:length(f0_sp)
    for jj=1:length(h)
        for j=1:length(G1)
            sysvel_dis_sp{jjj,jj,j}(:)=(f*1i).^2.*K*G*G1(j)*G2.*((f*1i)./((f*1i).^2+2*h(jj)*f0_sp(jjj)*f*1i+f0_sp(jjj)^2)).*((f*1i)./(fb+f*1i)).*(fp^2./((f*1i).^2+2*cos(pi/8)*fp*f*1i+fp^2)).^2.*(fp^2./((f*1i).^2+2*cos(3*pi/8)*fp*f*1i+fp^2)).^2;
        end
    end
end

for jjj=1:length(f0)
    for jj=1:length(h)
        for j=1:length(K2)
            ifft_sysvel_dis_p{jjj,jj,j}(:)=ifft(ifftshift(sysvel_dis_p{jjj,jj,j}(:)),'symmetric');
        end
    end
end
for jjj=1:length(f0)
    for jj=1:length(h)
        for j=1:length(K2)
            ifft_sysvel_dis_f{jjj,jj,j}(:)=ifft(ifftshift(sysvel_dis_f{jjj,jj,j}(:)),'symmetric');
        end
    end
end

for jjj=1:length(f0_sp)
    for jj=1:length(h)
        for j=1:length(G1)
            ifft_sysvel_dis_sp{jjj,jj,j}(:)=ifft(ifftshift(sysvel_dis_sp{jjj,jj,j}(:)),'symmetric');
        end
    end
end

clear sysvel_dis_sp sysvel_dis_p sysvel_dis_f
for jjj=1:length(f0)
    for jj=1:length(h)
        for j=1:length(K2)
            gr_dis_p{jjj,jj,j}(:)=conv(signal,ifft_sysvel_dis_p{jjj,jj,j}(:));
            green_dis_p{jjj,jj,j}(:)=gr_dis_p{jjj,jj,j}(1:NSi);
        end
    end
end
clear gr_dis_p ifft_sysvel_dis_p
for jjj=1:length(f0)
    for jj=1:length(h)
        for j=1:length(K2)
            gr_dis_f{jjj,jj,j}(:)=conv(signal,ifft_sysvel_dis_f{jjj,jj,j}(:));
            green_dis_f{jjj,jj,j}(:)=gr_dis_f{jjj,jj,j}(1:NSi);
        end
    end
end
clear gr_dis_f ifft_sysvel_dis_f
for jjj=1:length(f0_sp)
    for jj=1:length(h)
        for j=1:length(G1)
            gr_dis_sp{jjj,jj,j}(:)=conv(signal,ifft_sysvel_dis_sp{jjj,jj,j}(:));
            green_dis_sp{jjj,jj,j}(:)=gr_dis_sp{jjj,jj,j}(1:NSi);
        end
    end
end
clear gr_dis_sp ifft_sysvel_dis_sp
save('transfer_function3.mat','green_dis_sp','green_dis_f','green_dis_p','-v7.3')
