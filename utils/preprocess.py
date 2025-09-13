import numpy as np
from scipy.signal import butter, filtfilt

def get_used_subcarriers():
    # Define the full range of 256 subcarrier indices, centered around 0 (like in FFT)
    subcarrier_indices = np.fft.fftshift(np.arange(-128, 128))

    # Define subcarriers to remove
    pilots = [-53, -25, -11, 11, 25, 53]
    nulls = [0, -1, 1, -59, -60, -61, -62, -63, -64, 59, 60, 61, 62, 63, 64]
    unused = [ -3, -2, 2, 3, -126, -127, -128 ]
    #middle_noise_zone = [125, 126, 127, -125, -126, -127, -128]

    # Combine all to remove
    remove_indices = set(pilots + nulls + unused)

    # Create a mask of subcarriers to keep
    return np.array([idx not in remove_indices for idx in subcarrier_indices])

def filter_remove_subcarriers(csi):
    keep_mask = get_used_subcarriers()
    return csi[:, keep_mask]

def filter_diff(csi):
    """
    Apply a difference filter to the CSI data.
    This function computes the difference between consecutive subcarriers.
    """
    return np.diff(csi, axis=0)

def to_db(csi):
    """Convert complex CSI to dB scale."""
    amp = np.abs(csi)
    amp[amp == 0] = 1  # Avoid log(0)
    return 20 * np.log10(amp)

def lowpass_filter(csi, cutoff=3.0, fs=100.0, order=4):
    """
    Apply a low-pass Butterworth filter to CSI data.
    
    Parameters:
        csi (ndarray): CSI data (samples, subcarriers) or (samples,) 1D.
        cutoff (float): Cutoff frequency in Hz.
        fs (float): Sampling rate (frames per second).
        order (int): Filter order.
    
    Returns:
        ndarray: Smoothed CSI data of same shape.
    """
    nyq = 0.5 * fs  # Nyquist frequency
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)

    # Apply along time (axis=0)
    return filtfilt(b, a, csi, axis=0)
