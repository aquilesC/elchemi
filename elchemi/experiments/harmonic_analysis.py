from pathlib import Path

import h5py
import numpy as np
import yaml
from numpy.fft import fftfreq
from scipy.fft import fft
from scipy.signal import spectrogram

# from elchemi import param_folder  #uncomment if necessary

class AnalyzeModel:
    metadata = {}
    data = None
    frame_rate = 0
    filename = ''
    fft_data = None

    def __init__(self):
        if (param_folder / '.metadata').exists():
            with open(param_folder / '.metadata') as f:
                self.metadata = yaml.load(f, Loader=yaml.UnsafeLoader)

    def open(self, filename):
        """ Opens a data file. Currently, works only with Refeyn iSCAT data
        Parameters
        ----------
        filename : str or Path
            Relative or absolute position of the file to open. It will be transformed to a Path before attempting to
            open the file.
        """
        self.filename = Path(filename)
        with h5py.File(filename, 'r') as data_file:
            self.data = data_file["movie/frame"][()]
            self.frame_rate = data_file["movie/configuration/acq_camera"]["frame_rate"][()]

        self.metadata.update({
            'filename': str(self.filename.name),
            'last_dir': str(self.filename.parent),
            })

    def calculate_data_on_roi(self, X, Y):
        """ Calculates the integrated intensity over time in a given region of interest (ROI)
        Parameters
        ----------
        X : tuple or list
            Pixel-range for the X dimension
        Y : tuple or list
            Pixel-range for the Y dimension
        Returns
        -------
        np.array
            The integrated intensity over the range of pixels for all the available frames
        """
        return np.sum(np.sum(self.data[:, X[0]:X[1], Y[0]:Y[1]], axis=1), axis=1)

    def calculate_fft_on_roi(self, X, Y):
        """ Calculates the Fourier transform over a range of pixels. It first integrates the intensity in the ROI and
        then performs the FFT. See `meth:~calculate_data_on_roi` for more infor on ROI definition.

        Parameters
        ----------
        X : tuple or list
            Range of pixels for X dimension
        Y : tuple or list
            Range of pixels for Y dimension

        Returns
        -------
        freqs : np.array
            Frequencies over which the FFT was calculated. It is the result of applying `numpy.fft.fftfreq`
        power : np.array
            The power of the FFT only on the positive range of frequencies
        max_freq : float
            The frequency with the largest power value of the FFT without considering 0Hz
        max_power : float
            The maximum power at the given maximum frequency, without considering 0Hz

        .. Todo:: check if rfft is better option, could be 2x faster.
        """


        added = self.calculate_data_on_roi(X, Y)
        transformed = fft(added)
        N = len(added)
        freqs = fftfreq(N, 1 / self.frame_rate)[:N // 2]
        power = 2.0 / N * np.abs(transformed[0:N // 2])
        n_max = np.argmax(power[1:]) + 1
        max_freq = freqs[n_max]
        max_power = power[n_max]

        return freqs, power, max_freq, max_power

    def calculate_spectrogram_on_roi(self, X, Y, overlap=128):
        """ Calculates the spectrogram on a given region of interest. It uses a base overlap of 128 data points,
        meaning that the sliding window used for the spectrogram will have some concatenation. Depending on the
        modulation frequency, the overlap can be changed to improve the resolution or to lower the computational effort

        Parameters
        ----------
        X : tuple or list
            X-range for the ROI
        Y : tuple or list
            Y-range for the ROI
        overlap : int
            Number of frames that will overlap while calculating the spetrogram

        Returns
        -------
        f : numpy.array
            The frequencies over which the FFT is calculated
        t : numpy.array
            The times at which the FFT was calculated
        Sxx : numpy.array
            The spectrogram itself. This is the direct result of using `scipy.signal.spectrogram`
        """
        added = self.calculate_data_on_roi(X, Y)
        f, t, Sxx = spectrogram(added, fs=self.frame_rate, axis=0, mode='complex', noverlap=overlap)
        return f, t, Sxx

    def make_full_fft(self, freq, min_cycles):
        """ Calculates the FFT on the entire image stack. It splits the data into "cycles" which is the number of
        frames that it takes for a full oscillation, based on the external driving frequency. It grabs a minimum
        number of oscillations before calculating the FFT, and it makes a sliding window that jumps one cycle at a
        time.

        Parameters
        ----------
        freq : float
            Frequency (in Hertz) to calculate the number of frames and to extract from the FFT
        min_cycles : int
            Number of cycles to use to calculate the FFT

        .. todo::
            The FFT calculates all the frequencies, but only one is key. Perhaps this should be extended to avoid
            recalculating when the user wants to explore other frequencies.
        .. todo::
            The code forces a sliding window that jumps one cycle each time. It may be wise of give flexibility to
            select the window.
        """
        min_frames = int(self.frame_rate / freq)  # How many frames to record a full oscillation
        cycle_frames = min_frames * min_cycles  # How many frames there are in the total integration period

        self.metadata.update({
            'freq': min_frames,
            'min_cycles': min_cycles
            })

        self.freqs = fftfreq(cycle_frames, 1 / self.frame_rate)  # [:cycle_frames // 2]
        close_freq = (np.abs(self.freqs - freq)).argmin()

        num_calculations = int(self.data.shape[0] / min_frames)  # jump a cycle to speed up FFT calculation

        self.fft_data = np.zeros((num_calculations, self.data.shape[1], self.data.shape[2]),
                                 dtype=complex)

        for i in range(num_calculations):
            print(f'{100 * i / num_calculations:.4} %\r')
            to_analyze = self.data[i:i + cycle_frames, :, :]
            self.fft_data[i, :, :] = fft(to_analyze, axis=0)[close_freq]

    def close(self):
        """ Cleans up the memory used by the data and the fft data.

        .. todo::
            It is not clear wether setting data to None actually triggers the garbage collector or if there is a risk of
            a memory leak by creating hanging arrays without a reference.
        """
        self.data = None
        self.fft_data = None

    def __del__(self):
        with open(param_folder / '.metadata', 'w') as f:
            yaml.dump(self.metadata, f)
