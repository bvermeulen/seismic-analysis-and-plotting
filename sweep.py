import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.mlab import window_none

file_name = 'pilot_signal.csv'
dt = 2/1000 # sampling interval is 2 ms
df = 1/dt # sampling frequency

pilot_df = pd.read_csv(file_name)
time = pilot_df['Time']
amplitude = pilot_df['Amplitude']

fig, ax = plt.subplots(nrows=4, ncols=1, figsize=(12, 7))

ax[0].set_title('pilot')
ax[0].set_xlim(0, 30000) # first 3 seconds only
ax[0].set_ylim(-175, 175)
ax[0].plot(time, amplitude)

ax[1].set_title('autocorrelation')
max_lag = 250
corr_function = np.correlate(amplitude, amplitude, mode='full')
corr_function = corr_function[(len(amplitude)-1)-(max_lag-1):(len(amplitude)-1)+max_lag]
time_lags = np.arange(-(max_lag-1), max_lag)
ax[1].plot(time_lags, corr_function)

ax[2].set_title('magnitude')
ax[2].set_xlim(0, 100)
scale = 'linear'  #  'dB' # or 'default'
ax[2].magnitude_spectrum(corr_function, Fs=df, scale=scale, window=window_none)

ax[3].set_title('phase')
ax[3].set_xlim(0, 100)
ax[3].phase_spectrum(corr_function, Fs=df, window=window_none)

plt.tight_layout()
plt.show()

