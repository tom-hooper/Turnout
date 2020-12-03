from rtlsdr import RtlSdr

sdr = RtlSdr()

# configure device
sdr.sample_rate = 12500  # Hz
sdr.center_freq = 148912500     # Hz
sdr.freq_correction = 10   # PPM
sdr.gain = 'auto'

print(sdr.read_samples(512))
