from pathlib import Path

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog, QMainWindow

from elchemi.experiments.analysis import AnalyzeModel
from elchemi.view import VIEW_FOLDER

home_path = Path.home()

class RoiWindow(QMainWindow):
    def __init__(self, model:AnalyzeModel=None, title=''):
        """
        :param measurement model: Model used to analyze the data
        """
        super().__init__(parent=None)
        uic.loadUi(str(VIEW_FOLDER / 'GUI' / 'roi_data.ui'), self)
        self.analysis_model = model
        self.setWindowTitle(title)

        self.plot = MplCanvas(parent=self)
        self.plot_widget.layout().addWidget(self.plot)

        self.spectrogram = MplCanvas(parent=self)
        self.spectrogram_widget.layout().addWidget(self.spectrogram)

        self.fft = MplCanvas(parent=self)
        self.fft_widget.layout().addWidget(self.fft)

        self.action_save_plots.triggered.connect(self.save_plots)

    def set_roi(self, X, Y):
        data = self.analysis_model.calculate_data_on_roi(X, Y)
        freqs, power, max_freq, max_power = self.analysis_model.calculate_fft_on_roi(X, Y)
        f, t, Sxx = self.analysis_model.calculate_spectrogram_on_roi(X, Y)
        x = np.linspace(0, len(data)/self.analysis_model.frame_rate, len(data))

        self.plot.axes.plot(x, data)
        self.plot.axes.set_xlabel('Time (s)')
        self.plot.axes.set_ylabel('Integrated intensity')
        self.spectrogram.axes.pcolormesh(t, f, np.abs(Sxx), shading='gouraud')
        self.spectrogram.axes.set_xlabel('Time (s)')
        self.spectrogram.axes.set_ylabel('Frequency (Hz)')
        self.fft.axes.plot(freqs, power)
        self.fft.axes.plot(max_freq, max_power, 'o')
        self.fft.axes.grid()
        self.fft.axes.set_yscale('log')
        self.fft.axes.set_xscale('log')
        self.fft.axes.set_xlabel('Frequency (Hz)')
        self.fft.axes.set_ylabel('Power')

        self.max_freq_line.setText(f'{max_freq:.3f} Hz')

    def save_plots(self):
        last_dir = self.analysis_model.metadata.get('last_roi_dir', home_path)

        save_dir = QFileDialog.getExistingDirectory(self, 'Save Data', str(last_dir))
        self.analysis_model.metadata.update({
            'last_roi_dir': save_dir,
            })
        save_dir = Path(save_dir)
        save_dir.mkdir(exist_ok=True)

        self.fft.figure.savefig(save_dir/'fft.png')
        self.spectrogram.figure.savefig(save_dir/'spectrogram.png')
        self.plot.figure.savefig(save_dir/'plot.png')

class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        fig.set_tight_layout(True)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)