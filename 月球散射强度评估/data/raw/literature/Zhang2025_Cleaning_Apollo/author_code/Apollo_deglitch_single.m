clc; clear all; close all;
warning('off','all')

dt1=1/6.625; % LP sampling interval
dt2=1/53; % SP sampling interval

flatdate12=[19741016:19750409,19750628:19770327];
flatdate14=[19760918:19761108];
flatdate15=[19711024:19711108,19750628:19770327];
flatdate16=[19720513:19720514,19750629:19770326]; % Flat mode work period of Apollo passive seismic stations

%% Transfer_Function;
load('transfer_function1.mat'); % Acceleration
load('transfer_function2.mat'); % Velocity
load('transfer_function3.mat'); % Displacement

%% load data

[X,I] = rdmseed('XA.S12.8.MHX.1971.293'); % load mseed data
k = I(1).XBlockIndex;
eventdate=19711020; % for determine the mode

%% remove glitch

intp=8; % interpolation number for LP
ND2=15; % window before glitch


index_list_2_deglitch = 17774;  % index of glitch

lia12 = ismember(eventdate,flatdate12); % select mode (peak or flat)

if lia12==1
    green_acc=green_acc_f;
    green_vel=green_vel_f;
    green_dis=green_dis_f;
    NDS=1000; % flat mode window after glitch
elseif lia12==0
    green_acc=green_acc_p;
    green_vel=green_vel_p;
    green_dis=green_dis_p;
    NDS=600; % peak mode window after glitch
end

for i_ind=1:length(index_list_2_deglitch) % began loop
    
    if lia12==1 && i_ind<length(index_list_2_deglitch)  % change the window if glitches overlap
        NDS=1000;
        if index_list_2_deglitch(i_ind+1)-index_list_2_deglitch(i_ind)<NDS
            NDS=index_list_2_deglitch(i_ind+1)-index_list_2_deglitch(i_ind)-ND2;
        end
    elseif lia12==0 && i_ind<length(index_list_2_deglitch)
        NDS=600;
        if index_list_2_deglitch(i_ind+1)-index_list_2_deglitch(i_ind)<NDS
            NDS=index_list_2_deglitch(i_ind+1)-index_list_2_deglitch(i_ind)-ND2;
        end
    end
    if i_ind==length(index_list_2_deglitch)
        if lia12==1
            NDS=1000;
        elseif lia12==0
            NDS=600;
        end
    end
    
    data2fit=cat(1,X(k).d);
    time2fit=cat(1,X(k).t); 
    time2fit=(time2fit-time2fit(1))*86400;
    aver=mean(data2fit);
    
    y = data2fit(index_list_2_deglitch(i_ind)-ND2:index_list_2_deglitch(i_ind)+NDS); %select the data
    t = time2fit(index_list_2_deglitch(i_ind)-ND2:index_list_2_deglitch(i_ind)+NDS);
    time_int= [0:length(t)*intp-1]*dt2+t(1); % interpolation
    data_int=interp1(t,y,time_int,'spline');
    data_int(1)=data_int(2);
    data_int(end)=data_int(end-1);
    
    data_fp=data_int-aver;
    [~, index_max]=max(abs(data_fp)); % detect the peak
        
    d2_old=1e10;
    % grid search
    for i_f0=1:length(f0) % f0
        for i_h=1:length(h) % h
            for i_K2=1:length(K2) % K2
                
                [~,index_tf]=max(abs(green_acc{i_f0,i_h,i_K2}));
                
                for n=1:intp*10 % source time
                    
                    green01 = green_acc{i_f0,i_h,i_K2}(index_tf-index_max+n-5*intp:index_tf-index_max+(NDS+ND2+1)*intp-1+n-5*intp);
                    green1 = interp1(time_int,green01,t,'spline');
                    green02 = green_vel{i_f0,i_h,i_K2}(index_tf-index_max+n-5*intp:index_tf-index_max+(NDS+ND2+1)*intp-1+n-5*intp);
                    green2 = interp1(time_int,green02,t,'spline');
                    green03 = green_dis{i_f0,i_h,i_K2}(index_tf-index_max+n-5*intp:index_tf-index_max+(NDS+ND2+1)*intp-1+n-5*intp);
                    green3 = interp1(time_int,green03,t,'spline');
                    
                    green_fn_list1 = green1';
                    green_fn_list2 = green2';
                    green_fn_list3 = green3';
                    
                    typefit='g'; % 'g' for glitch, 'c' for calibration signal
                    
                    if lia12==1
                        ntweight=400;
                    else
                        ntweight=200;
                    end
                    weight1=zeros(1,length(green_fn_list1(:)));
                    weight1(1:length(green_fn_list1(:)))=1.;
                    weight1(1:index_max+ntweight)=100.;
                    
                    x1 = green_fn_list1(:);
                    x2 = green_fn_list2(:);
                    x3 = green_fn_list3(:);
                    x5 = ones((ND2+NDS+1), 1);
                    x6 = [0:(ND2+NDS)]'*1.0;
                    
                    if typefit == "c"                          % 
                        X = [x1, x5, x6];
                        A = [[x1(1), x5(1), x6(1)];...
                            [ x1(end), x5(end), x6(end)]];
                    elseif typefit == "g"                  % 
                        X = [x1, x2, x3, x5,x6];
                        A = [[x1(1),x2(1),x3(1), x5(1),x6(1)];...
                            [x1(end),x2(end),x3(end), x5(end), x6(end)]];
                    end
                    
                    b = [y(1); y(end)];                   % force the fisrt and end points to be
                    %b = [0; 0];                           % equal to those of the input signal
                    
                    % Linear system to solve in case of Lagrange multipliers
                    % [ 2X'X    A' ] [ a      ]  = [ 2X'y ]
                    % [   A       0 ] [  lbda ]     [ b      ]
                    
                    M = [[2*X'.*weight1*X, A'];[A, zeros(2)]];
                    R = [2*X'.*weight1*y ; b];
                    
                    theta = M\R;        % theta = inv(M)*R
                    theta = theta(1:size(X,2));size(X,2);
                    
                    yhat1 = X*theta; % Fitted model
                    drift=[x5,x6]*theta(end-1:end);
                    % Variance
                    d1=y-yhat1;
                    d1(1:index_max+ntweight)=d1(1:index_max+ntweight)*10;
                    d2=sum(d1.^2);
                    
                    if d2>=d2_old
                        yhat1=yhat1_old;
                        drift=drift_old;
                        d2=d2_old;
                        theta=theta_old;
                    end
                    
                    yhat1_old=yhat1;
                    drift_old=drift;
                    d2_old=d2;
                    theta_old=theta;
                    
                end
            end
        end
    end
    
    
    if d2_old>1e7 % fitting threshold
        out=[num2str(eventdate) ,  ' not fit']
        continue
    end
    
    % save deglitch data if within threshold
    yhat_no_drift1 = yhat1-drift;
    data2save=data2fit;
    data2save(index_list_2_deglitch(i_ind)-ND2:index_list_2_deglitch(i_ind)+NDS)=data2save(index_list_2_deglitch(i_ind)-ND2:index_list_2_deglitch(i_ind)+NDS)-yhat_no_drift1;
    
end

% check the data
figure()
plot(t,y)
hold on
plot(t,yhat1)

figure()
plot(time2fit,data2save)


