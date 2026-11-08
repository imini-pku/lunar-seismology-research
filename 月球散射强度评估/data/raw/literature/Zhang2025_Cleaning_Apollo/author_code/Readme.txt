
This is an Apollo passive seismic sub-dataset, which contain 116 larger impact events in 
Nakamura's catalog (Nakamura et al., 1981). Each event contains 3 hours LP data and 2 hours 
SP data which 30min before the start time list in Nakamura's catalog, and 150min or 90min after. 
You can check 'Impact_catalog_116' for the details of each event date.

We download the ASCII format raw data from JAXA Data Archives and Transmission System, we 
removed the invalid data and fix the 'Amplitude offset' of the data in Apollo 14 station. We 
removed the glitches and calibration signals for LPZ component which overlap with the lager 
impact events (peak to peak amplitudes larger than 20 DU). And we manually remove some spikes
for LPZ component. Please check file 'Impact_catalog_116' for details about removing of 
glitches, calibration signals and spikes.

The processed data archived in mseed format, but we didn't interpolate the data to a constant 
time step, each file contain one component and a timestamp. The filename 'XA.S14.8.MHZ.1971.293' 
means the 8th impact event list in my catalog, LPZ component that recorded on Apollo 14 station,
this event recorded on the 293th day of 1971. If an event spans a new day, it will be saved in two files.

