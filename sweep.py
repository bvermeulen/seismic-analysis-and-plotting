import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.mlab import window_none

# values of the sweep are stored in pilot_signal.csv with following parameters:
# - sweep length: 64 seconds
# - start frequency: 2 Hz
# - end frequency: 90 Hz
# - amplitude between -100 and 100

file_name = 'pilot_signal.csv'
dt = 2/1000 # sampling interval is 2 ms
df = 1/dt # sampling frequency
pi = np.pi

pilot_df = pd.read_csv(file_name)
time = pilot_df['Time']
amplitude = pilot_df['Amplitude']

fig, ax = plt.subplots(nrows=5, ncols=1, figsize=(12, 7))

ax[0].set_title('pilot')
ax[0].set_xlim(0, 30000) # first 3 seconds only (expressed in ms)
ax[0].set_ylim(-150, 150)
ax[0].plot(time, amplitude)

ax[1].set_title('autocorrelation')
max_lag = 257
corr_function = np.correlate(amplitude, amplitude, mode='full') / len(amplitude)
corr_function = corr_function[(len(amplitude)-1)-(max_lag-1):(len(amplitude)-1)+max_lag]
time_lags = np.arange(-(max_lag-1), max_lag)
ax[1].plot(time_lags, corr_function)

ax[2].set_title('autocorrelation re-ordered')
cf_reordered = np.concatenate((corr_function[max_lag-1:], corr_function[0:max_lag-1]))
time_lags = np.arange(0, 2*max_lag-1)
ax[2].plot(time_lags, cf_reordered)
print(len(corr_function))
print(len(cf_reordered))

ax[3].set_title('magnitude')
ax[3].set_xlim(0, 100)
scale = 'linear'  #  'dB' # or 'default'
ax[3].magnitude_spectrum(corr_function, Fs=df, scale=scale, window=window_none)

ax[4].set_title('phase')
ax[4].set_ylim(-4, +4)
ax[4].set_xlim(0, 100)
# get the phase spectrum values and frequencies values; plot invisible and use a non default color
cf_phase_values, cf_freq, _ = ax[4].phase_spectrum(cf_reordered, Fs=df, window=window_none, visible=False, color='r')

# check for modulus 2*pi and keep values between -pi and pi
cf_phase_values = np.mod(cf_phase_values, 2*pi)
cf_phase_values[cf_phase_values>pi] -= 2*pi

ax[4].plot(cf_freq, cf_phase_values)

plt.tight_layout()
plt.show()

