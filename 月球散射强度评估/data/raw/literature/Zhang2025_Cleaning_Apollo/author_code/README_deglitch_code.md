# Apollo_seismic_deglitch_single

This Matlab code is for remove the glitches in Apollo passive seismic data. One should run 'Transfer_Function' first to generate an array of different parameter transfer functions convolute with different step signal. Then, run 'Apollo_deglitch_single' to deglitch.
The array of different transfer functions should be very large, because it's multidimensional. You can try to reduce the dimension when you test the code (e.g. frozen f0 and h). 
When you do deglitches, you can load the data you want. Please declare the date of the data to determine the operating mode of the Apollo seismometer. In addition, you need input the indexes of glitch.

The Lagrangian method is based on Grégory Sainton (https://github.com/GregS1t/seisdeglitch/blob/main/subroutines_GS/fit_one_glitch_lagrange_v2_ff.m).

Please contact the auther if you have any question (zxiang@ipgp.fr).
 
