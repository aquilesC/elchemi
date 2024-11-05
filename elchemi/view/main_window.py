from pathlib import Path

import numpy as np
import pyqtgraph as pg
from PyQt5 import uic
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog, QFileDialog, QMainWindow, QMessageBox, QScrollBar
from threading import Thread, Event

from elchemi.experiments.harmonic_analysis import AnalyzeModel
from elchemi.experiments.live_acquisition import LiveAcquisition
from elchemi.view import VIEW_FOLDER
from elchemi.view.config_widget import ConfigWidget
from elchemi.view.roi_plots import RoiWindow
from elchemi.devices.camera.basler import BaslerCamera


home_path = Path.home()


class DisplayWindow(QMainWindow):
    def __init__(self, model: AnalyzeModel = None, live_model: LiveAcquisition = None, refresh_rate = 500, fft_refresh_rate = 10000, fft_images_window = 500):
        """
        :param measurement model: Model used to analyze the data

        .. TODO:
            + add button in live view for connecting to devices
            + add buttons for start and stop aquisition
            + add button for starting the digilent (separate from camera) waveforms
            + add toggle button for switching between real time view and FFT calculated harmonic view
        """
        super().__init__(parent=None)
        uic.loadUi(str(VIEW_FOLDER / 'GUI' / 'main_window.ui'), self)
        self.setWindowTitle('Potentiodynamic Data Exploration')

        # Menu actions
        self.action_open.triggered.connect(self.load_data)
        self.action_connect.triggered.connect(self.connect_camera)
        self.action_close.triggered.connect(self.disconnect_basler)

        self.analyze_model = model
        self.live_model = live_model
        self.refresh_rate = refresh_rate

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
        self.filter_data_button.clicked.connect(self.handle_fft)
        self.roi = None
        self.is_open = False
        self.freerun_checkbox.stateChanged.connect(self.start_freerun)
        self.update_config.clicked.connect(self.update_cam)
        self.gain_freerun.setText("10")
        self.exposure_freerun.setText("5000")
        self.framerate_freerun.setText("200")
        self.height_freerun.setText('600')
        self.width_freerun.setText('600')
        self.xcenter_freerun.setText('204')
        self.ycenter_freerun.setText('204')
        self.pixel_format_box.currentIndexChanged.connect(self.change_pixel_format)

        self.fft_image_widget = pg.ImageView()
        self.fft_image_widget.setPredefinedGradient('thermal')
        self.fft_phase_widget = pg.ImageView()
        self.fft_phase_widget.setPredefinedGradient('cyclic')
        self.fft_selector = QScrollBar(Qt.Vertical)
        self.fft_selector.valueChanged.connect(self.update_fft)
        self.fft_images_window = fft_images_window
        self.fft_refresh_rate = fft_refresh_rate
        self.fft_thread = None

        layout = self.fft_widget.layout()
        layout.addWidget(self.fft_selector)
        layout.addWidget(self.fft_image_widget)
        layout.addWidget(self.fft_phase_widget)

        self.config_widget = ConfigWidget()
        self.config_widget.update_text(self.live_model.config)
        self.config_widget.updated_config.connect(self.update_live_config)
        self.update_live_params()
        self.button_config_edit.clicked.connect(self.config_widget.show)
        
    def update_live_config(self, config):
        self.live_model.config.update(config)
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

    def connect_camera(self): #FIXME: Why is only the pixel format updated?
        self.live_model.camera.initialize()
        self.pixel_format_box.clear()
        for pixel_fmt in self.basler.supported_pixel_formats:
            self.pixel_format_box.addItem(pixel_fmt)
    
    def start_freerun(self): #FIXME: Why is the refresh rate defined in the UI?
        if self.refresh_rate_value.text():
            try:
                self.refresh_rate = float(self.refresh_rate_value.text())
            except ValueError as e:
                warning = QMessageBox(self)
                warning.setWindowTitle('Error')
                warning.setText('Invalid refresh rate specified')
                warning.exec()


        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_raw_data)
        self.timer.start(self.refresh_rate)

        self.basler.start_continuous_reads()


    def disconnect_basler(self):
        self.basler.finalize() #FIXME: Why accessing the camera directly from the view?
        self.timer.stop()
        self.timer.timeout.disconnect()
        del self.timer

        if hasattr(self, 'fft_timer'): #FIXME: Wrong pattern. Why would the UI not have the timer?
            self.fft_timer.stop()
            self.fft_timer.timeout.disconnect() #FIXME: Why would it be disconnected?
            del self.fft_timer #FIXME: Why deleting the timer? Isn't it better just to stop it?

    def update_raw_data(self):
        '''Method to update the image displayed in the raw data window. It could be merged with update_image in the future.'''
        if hasattr(self.basler, 'temp_image'):
            self.image_widget.setImage(self.basler.temp_image)
        else:
            self.basler.logger.info('Tried to fetch image when none were available.')

    def update_cam(self): #FIXME: Wrong pattern. Why checking .text() and not do anything if false?
        if self.exposure_freerun.text():
            try:
                self.basler.set_exposue(float(self.exposure_freerun.text()))
            except ValueError as e:
                raise Warning(f'Exposure not updated, value-error exception raised: {e}')
        if self.gain_freerun.text():
            try:
                self.basler.set_gain(float(self.gain_freerun.text()))
            except ValueError as e:
                raise Warning(f'Gain not updated, value-error exception raised: {e}')
        if self.framerate_freerun.text():
            try:
                self.basler.set_framerate(float(self.framerate_freerun.text()))
            except ValueError as e:
                raise Warning(f'Framerate not updated, value-error exception raised: {e}')
        if self.width_freerun.text() and self.height_freerun.text() and self.xcenter_freerun.text() and self.ycenter_freerun.text():
            X = (float(self.xcenter_freerun.text()), float(self.xcenter_freerun.text())+float(self.width_freerun.text()))
            Y = (float(self.ycenter_freerun.text()), float(self.ycenter_freerun.text())+float(self.height_freerun.text()))
            try:
                self.basler.set_ROI((X,Y))
            except ValueError as e:
                raise Warning(f'Image Width not updated, value-error exception raised: {e}')
    
    def load_data(self):
        self.loaded_data = True
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

    def handle_fft(self):
        if hasattr(self, 'loaded_data'): # If data was loaded run standard fft
            self.calculate_fft(frame_rate=None)
        else:
            self.fft_timer = QTimer(self) #FIXME: Should be defined in the __init__
            self.fft_timer.timeout.connect(self.update_fft_data) #FIXME: Should be connected in the __init__
            self.fft_timer.start(self.fft_refresh_rate) #FIXME: This is the important thing

    def update_fft_data(self):
        img_list = []
        self.basler.external_buffer.pause_storage.set()
        while not self.basler.external_buffer.get_buffer().empty():
            img_list.append(self.basler.external_buffer.get_buffer().get()) #FIXME: Not sure this belongs in the VIEW
        img_list.reverse() #FIXME: why reversing the list?
        self.analyze_model.data = np.array(img_list)
        self.analyze_model.frame_rate = np.mean(np.array(self.basler.external_buffer.frame_rates)) #FIXME:
        # Calculations should be done in the model, not in the view.
        self.basler.external_buffer.pause_storage.clear()
        print(f'Average Camera Frame Rate: {self.analyze_model.frame_rate} \nStandard Deviation Frame Rate: {np.array(np.std(self.basler.external_buffer.frame_rates))}')

        if self.fft_thread is None or not self.fft_thread.is_alive():
            self._stop_fft = Event() #FIXME: This should be defined in the __init__
            self.fft_thread = Thread(target=self.calculate_fft, args=[np.mean(np.array(self.basler.external_buffer.frame_rates))])
            self.fft_thread.start()
        else:
            self.fft_timer.stop()
            self._stop_fft.wait()
            self.fft_timer.start(self.fft_refresh_rate)
            self._stop_fft.clear()        
        
        # Here we have a thread starter and runner 

        # Thread need to wait for previous

        # Then make_full_fft in live analysis will handle the different types of images and data

    def change_pixel_format(self):
        self.basler.set_pixelformat(self.pixel_format_box.currentText()) #FIXME: Camera should not be accessed directly

    def calculate_fft(self, frame_rate):
        freq = float(self.frequency_line.text())
        cycles = int(self.min_cycles_line.text())

        self.analyze_model.make_full_fft(freq, cycles, frame_rate = frame_rate, pixel_format= self.basler.get_pixelformat())

        self.fft_selector.setMinimum(0)
        self.fft_selector.setMaximum(self.analyze_model.fft_data.shape[0] - 1)

        self.close_freq = (np.abs(self.analyze_model.freqs - freq)).argmin()

        self.fft_image_widget.setImage(np.abs(self.analyze_model.fft_data[0, :, :]))
        self.fft_phase_widget.setImage(np.angle(self.analyze_model.fft_data[0, :, :]))
        if hasattr(self, 'loaded_data'):
            self._stop_read.set()
            self.fft_thread.join()
            del self.fft_thread


    def close_data(self):
        self.frame_selector.setEnabled(False)
        try:
            self.stackedWidget.removeWidget(self.fft_widget)
        except Exception as e:
            print(e)
        self.is_open = False
