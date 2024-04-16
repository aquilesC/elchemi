from pathlib import Path

import numpy as np
import pyqtgraph as pg
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog, QMainWindow, QScrollBar

from elchemi.experiments.analysis import AnalyzeModel
from elchemi.experiments.live_acquisition import LiveAcquisition
from elchemi.view import VIEW_FOLDER
from elchemi.view.roi_plots import RoiWindow

home_path = Path.home()


class ScatteringMainWindow(QMainWindow):
    def __init__(self, model: AnalyzeModel = None, live_model: LiveAcquisition = None):
        """
        :param measurement model: Model used to analyze the data
        """
        super().__init__(parent=None)
        uic.loadUi(str(VIEW_FOLDER / 'GUI' / 'main_window.ui'), self)
        self.setWindowTitle('Potentiodynamic Data Exploration')
        self.action_open.triggered.connect(self.open)
        self.analyze_model = model
        self.live_model = live_model

        self.frame_selector = QScrollBar(Qt.Vertical)
        self.image_widget = pg.ImageView()
        self.image_widget.setPredefinedGradient('thermal')
        layout = self.raw_data.layout()
        layout.addWidget(self.frame_selector)
        layout.addWidget(self.image_widget)

        self.frame_selector.setEnabled(False)
        self.frame_selector.valueChanged.connect(self.update_image)
        self.add_roi_button.clicked.connect(self.add_roi)
        self.plot_roi_button.clicked.connect(self.plot_roi)
        self.filter_data_button.clicked.connect(self.calculate_fft)
        self.roi = None
        self.is_open = False

        self.fft_image_widget = pg.ImageView()
        self.fft_image_widget.setPredefinedGradient('thermal')
        self.fft_phase_widget = pg.ImageView()
        self.fft_phase_widget.setPredefinedGradient('cyclic')
        self.fft_selector = QScrollBar(Qt.Vertical)
        self.fft_selector.valueChanged.connect(self.update_fft)

        layout = self.fft_widget.layout()
        layout.addWidget(self.fft_selector)
        layout.addWidget(self.fft_image_widget)
        layout.addWidget(self.fft_phase_widget)

        self.update_live_params()

    def update_live_params(self):
        config_camera = self.live_model.config['camera']
        self.line_exposure.setText(str(config_camera['exposure']))
        self.line_gain.setText(str(config_camera['gain']))
        self.line_width.setText(str(config_camera['width']))
        self.line_height.setText(str(config_camera['height']))
        self.line_xcenter.setText(str(config_camera['xcenter']))
        self.line_ycenter.setText(str(config_camera['ycenter']))

        config_daq = self.live_model.config['daq']
        self.line_frequencyw1.setText(str(config_daq['frequencyw1']))
        self.line_amplitudew1.setText(str(config_daq['amplitudew1']))
        self.line_frequencyw2.setText(str(config_daq['frequencyw2']))
        self.line_amplitudew2.setText(str(config_daq['amplitudew2']))

        config_data = self.live_model.config['data']
        self.line_mincycles.setText(str(config_data['min_cycles']))
        self.line_filename.setText(str(config_data['filename']))
        self.line_totalframes.setText(str(config_data['total_frames']))

    def open(self):
        if self.is_open:
            self.close_data()

        last_dir = self.analyze_model.metadata.get('last_dir', home_path)
        file = QFileDialog.getOpenFileName(self, 'Open Data', str(last_dir), filter='*.mp')[0]
        if file != '':
            file = Path(file)
        else:
            return

        self.analyze_model.open(str(file))

        self.filename_name.setText(str(file.stem))

        self.image_widget.setImage(self.analyze_model.data[0, :, :], autoLevels=True)

        self.setWindowTitle(f'Potentiodynamic Analysis: {file.name}')
        self.frame_selector.setMinimum(0)
        self.frame_selector.setMaximum(self.analyze_model.data.shape[0] - 1)
        self.frame_selector.setEnabled(True)
        self.is_open = True

    def update_image(self, frame_no):
        self.image_widget.setImage(self.analyze_model.data[frame_no, :, :], autoLevels=False, autoRange=False)

    def update_fft(self, frame_no):
        self.fft_image_widget.setImage(np.abs(self.analyze_model.fft_data[frame_no, :, :]), autoLevels=False,
                                       autoRange=False)
        self.fft_phase_widget.setImage(np.angle(self.analyze_model.fft_data[frame_no, :, :]), autoLevels=False,
                                       autoRange=False)

    def add_roi(self):
        if self.roi is not None:
            return

        self.roi = pg.RectROI([0, 0], size=pg.Point(10, 10))
        self.image_widget.addItem(self.roi)

    def plot_roi(self):
        coords = [int(i) for i in self.roi.parentBounds().getCoords()]
        X = [coords[0], coords[2]]
        Y = [coords[1], coords[3]]

        self.roi_window = RoiWindow(self.analyze_model, title=f'Analysis on x=({X[0]}, {X[1]}), y=({Y[0]}, {Y[1]})')
        self.roi_window.set_roi(X, Y)
        self.roi_window.show()

    def calculate_fft(self):
        freq = float(self.frequency_line.text())
        cycles = int(self.min_cycles_line.text())
        self.analyze_model.make_full_fft(freq, cycles)

        self.fft_selector.setMinimum(0)
        self.fft_selector.setMaximum(self.analyze_model.fft_data.shape[0] - 1)

        self.close_freq = (np.abs(self.analyze_model.freqs - freq)).argmin()

        self.fft_image_widget.setImage(np.abs(self.analyze_model.fft_data[0, :, :]))
        self.fft_phase_widget.setImage(np.angle(self.analyze_model.fft_data[0, :, :]))

    def close_data(self):
        self.frame_selector.setEnabled(False)
        try:
            self.stackedWidget.removeWidget(self.fft_widget)
        except Exception as e:
            print(e)
        self.is_open = False
