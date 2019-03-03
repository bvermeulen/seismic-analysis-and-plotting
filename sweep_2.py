import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.mlab import window_none

dt = 0.001
df = 1/dt # sampling frequency
time = np.arange(0, 2, dt)
amplitude = np.zeros(len(time))
amplitude[1010:1015] = 50
# amplitude[1800:2000] = 50

fig, ax = plt.subplots(nrows=4, ncols=1, figsize=(12, 7))

ax[0].set_title('pilot')
# ax[0].set_xlim(0, 200) 
ax[0].set_ylim(-100, 100)
ax[0].plot(time, amplitude)

ax[1].set_title('autocorrelation')
max_lag = 500
corr_function = np.correlate(amplitude, amplitude, mode='full')
corr_function = corr_function[(len(amplitude)-1)-(max_lag-1):(len(amplitude)-1)+max_lag]
time_lags = np.arange(-(max_lag-1), max_lag)
ax[1].plot(time_lags, corr_function)


ax[2].set_title('magnitude')
# ax[2].set_xlim(0, 100)
scale = 'dB'  #  'dB' # or 'default'
ax[2].magnitude_spectrum(corr_function, Fs=df, scale=scale, window=window_none)

ax[3].set_title('phase')
# ax[3].set_xlim(0, 100)
# ax[3].set_ylim(-4, 4)
ax[3].phase_spectrum(corr_function, Fs=df, window=window_none)

plt.tight_layout()
plt.show()

