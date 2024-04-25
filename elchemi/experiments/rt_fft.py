"""
Real-Time FFT experiment
========================

This experiment synchronizes a DAQ Card and a Camera. A continuous acquisition of images is then transformed using
the FFT algorithm.
"""
import yaml

from elchemi.devices.camera.basler import BaslerCamera


class RealTimeFFT:
    def __init__(self):
        self.daq = None
        self.camera = None

    def parse_config(self, filename):
        self.config = yaml.load(filename, Loader=yaml.FullLoader)

    def initialize(self):
        self.initialize_daq()
        self.initialize_camera()

    def initialize_camera(self):
        camera_settings = self.config['camera']
        self.camera = BaslerCamera(self.config['camera']['name'])
        self.camera.set_autogain('Off')
        self.camera.set_autoexposure('Off')
        self.camera.set_gain(camera_settings['gain'])
        self.camera.set_exposue(camera_settings['exposure'])
        ROI = (int(camera_settings['xcenter']-camera_settings['width']/2),
               int(camera_settings['xcenter']+camera_settings['width']/2),
               int(camera_settings['ycenter']-camera_settings['height']/2),
               int(camera_settings['ycenter']+camera_settings['height']/2))
        self.camera.set_ROI(ROI)
        self.camera.set_acquisition_mode(self.camera.MODE_CONTINUOUS)

    def initialize_daq(self):
        pass

    def start_daq(self):
        pass

    def start_free_run_camera(self):
        pass

    def start_rt_fft(self):
        pass

    def stop_rt_fft(self):
        pass

    def stop_free_run_camera(self):
        pass

    def stop_daq(self):
        pass

    def finalize(self):
        pass