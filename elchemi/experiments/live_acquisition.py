import threading
import time
from queue import Queue

import numpy as np
import yaml
from pypylon import pylon  # Python wrapper for Basler pylon Camera Software Suite
from scipy.fft import rfft

from elchemi.devices.camera.basler import BaslerCamera


# from elchemi.devices.DAQ.waveforms import DwfController as dwfc


class LiveAcquisition:
    def __init__(self, config_file):
        """
        :: ToDo..
            + none of the methods are tested, only copied from other code as placeholder
        """

        self.config_file = config_file
        self.config = {}
        self.camera = None
        self.daq = None

    def load_config(self):
        with open(self.config_file, 'r') as f:
            self.config = yaml.load(f, Loader=yaml.FullLoader)

    def connect_devices(
            self):  # FIXME: Perhaps this can be moved to the experiment. As I understand it, the idea is to be able to use the program even if the camera and DAQ are not connected.
        self.camera = BaslerCamera(self.config['camera']['name'])
        self.camera.initialize()
        self.daq = dwfc(self.config['daq']['device'], self.config['daq']['config_number'])  # FIXME: dwfc si not defined

    def daq_signal_on(self):
        """
        sets up the digilent board and truns the signal according to the given parameter
        this function can be used for testing the digilent output and sample response

        :: ToDo..
        1. the following code has to be rewritten based on the methods of the wavefrom.py wrapper.

        dwf.FDwfAnalogOutNodeEnableSet(hdwf, c_int(0), AnalogOutNodeCarrier, c_int(1))
        # dwf.FDwfAnalogOutNodeFunctionSet(hdwf, c_int(0), AnalogOutNodeCarrier, funcSine)
        dwf.FDwfAnalogOutNodeFunctionSet(hdwf, c_int(0), AnalogOutNodeCarrier, funcSquare)
        dwf.FDwfAnalogOutNodeFrequencySet(hdwf, c_int(0), AnalogOutNodeCarrier, c_double(frequency))
        dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, c_int(0), AnalogOutNodeCarrier, c_double(amplitude))
        dwf.FDwfAnalogOutConfigure(hdwf, c_int(0), c_int(1))

        2. the following code has to be replaced with triggering in one of the digital outputs with a TTL pulse of desired frequency

        dwf.FDwfAnalogOutNodeEnableSet(hdwf, c_int(1), AnalogOutNodeCarrier, c_int(1))
        dwf.FDwfAnalogOutNodeFunctionSet(hdwf, c_int(1), AnalogOutNodeCarrier, funcSquare)
        dwf.FDwfAnalogOutNodeFrequencySet(hdwf, c_int(1), AnalogOutNodeCarrier, c_double(frequency))
        dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, c_int(1), AnalogOutNodeCarrier, c_double(amplitude))
        dwf.FDwfAnalogOutConfigure(hdwf, c_int(1), c_int(1))

        3. The modulation potential and the TTL pulse should be internally synced in the DWF card
        """
        return

    def grab_and_acquire_images(self, circular_buffer, total_frames, start_event):
        self.camera.StartGrabbing(
            pylon.GrabStrategy_LatestImageOnly)  # FIXME: Why LatestImageOnly? This quickly leads to frame drops
        counter = 0
        start_time_pictures = time.time()  # Measure time it takes for first 100 pictures to be taken
        try:
            for i in range(total_frames):
                grab_result = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                circular_buffer.put(grab_result.Array)  # Grab images and store them in a buffer
                counter += 1
                if counter == nr_data_points:  # FIXME: Variable not defined
                    end_time_pictures = time.time()
                    elapsed_time = end_time_pictures - start_time_pictures
                    print("Time to take 100 pictures =", elapsed_time, "seconds")
                    start_event.set()  # Start analysis thread
        except pylon.TimeoutException as e:
            print("TimeoutException: ", str(e))
        finally:
            self.camera.StopGrabbing()  # Stop grabbing images
            print("Thread one is finished")
            print("Filled up queue size:", circular_buffer.qsize())

    def start_live_acquisition(self):
        # starts acquiring images and displaying the FFT live images
        circular_buffer = Queue(maxsize=1000)  # FIXME: Why using a Queue directly and not the buffer?
        # Create an event to signal when Thread 1 has captured 100 images
        start_event = threading.Event()  # FIXME: Event could be an attribute of the class, and automatically becomes available in the thread
        # Create Thread 1 (image capture) and start it
        thread1 = threading.Thread(target=self.grab_and_acquire_images, args=(
            circular_buffer, total_frames, start_event, dwf))  # FIXME: Variables not defined
        thread1.start()
        # Create Thread 2 (image analysis) and start it
        thread2 = threading.Thread(target=generate_new_data_fft, args=(circular_buffer, start_event))
        thread2.start()

        # Wait for both threads to finish (this won't happen in this example as threads run indefinitely)
        thread1.join()
        thread2.join()  # FIXME: This means the start_live_acquisition is blocking  # FIXME: Shouldn't stop_live_acquisition be called as well?

    def toggle_real_fourier(self):
        # toggling the live view between grapped images and the harmonic component
        return

    def stop_live_acquisition(self):
        # stops live view
        self.camera.StopGrabbing()  # Stop grabbing images
        print("Thread one is finished")  # FIXME: Better use logging than print
        print("Filled up queue size:", circular_buffer.qsize())  # FIXME: Wrong variable

    def update_camera_param(
            camera):  # FIXME: There are several mistakes (self missing, for example, many undefined variables)
        """
        :: ToDo..
        + the parameters should be either read from the GUI or config file.
        + the ROI parameters should be given as input on the GUI live acquisition page
        """
        # updating the camera and digilent parameters in the live acquisition
        camera.ExposureTime.SetValue(exposure_time)  # Set exposure time to 800 us
        camera.Gamma.SetValue(1.0)  # Try different gamma values
        camera.GainAuto.SetValue("Off")  # Turn off automatic gain
        camera.Gain.SetValue(19.0)  # Increase the gain value
        camera.OffsetX.SetValue(0)
        camera.OffsetY.SetValue(0)
        camera.Width.SetValue(camera.WidthMax.GetValue())
        camera.Height.SetValue(camera.HeightMax.GetValue())
        # Configure the camera for trigger mode
        # Set trigger mode to "On"
        self.camera.TriggerMode.SetValue("On")
        # Set the trigger source to Line 1 (external trigger)
        self.camera.TriggerSource.SetValue("Line1")
        # Set trigger selector to "FrameStart" (trigger before image capture)
        self.camera.TriggerSelector.SetValue("FrameStart")
        # Set camera ROI settings
        width = int(roi_width - roi_width % 4)
        height = int(roi_height - roi_height % 4)
        camera.Width.SetValue(width)
        camera.Height.SetValue(height)
        camera.OffsetX.SetValue(center_x)
        camera.OffsetY.SetValue(center_y)

    def save_last_grabbed_sequence(self):
        # saves the raw data from the camera in the memory for offline analysis
        return

    def update_fft_param(self):
        # updating the fourier analysis parameters in the live acquisition mode
        return

    def generate_new_data_fft(circular_buffer, plot_widget, cycle_frames, close_freq, data_set, iterate,
                              total_fft_frames):  # FIXME: Missing self, the logic is confusing.

        # definition that grabs number of cycled frames from buffer, fft analyses them and updates the plot window with the new image
        image_list = []
        treshold = 5  # Set treshold value for when buffer is empty so the analysis part of the code is skipped
        consecutive_counter = 0
        new_data_available = True
        while len(
                image_list) < cycle_frames and new_data_available:  # Add number of cycled frames of buffer images to the list
            if circular_buffer.empty():
                time.sleep(0.25)  # Wait for buffer to be updated with new images
                consecutive_counter += 1
                if consecutive_counter >= treshold:
                    new_data_available = False
            if not circular_buffer.empty():
                image_capture = circular_buffer.get()
                # image_list.append(image_capture[0:ROI_fft_size[0], 0:ROI_fft_size[1]]) # Crop image to desired ROI
                image_list.append(image_capture[125:248, 150:248])  # Crop image to desired ROI
                consecutive_counter = 0
        if int(len(image_list)) == cycle_frames:  # perform fft when list is exactly filled with number of cycled frames
            fft_data = rfft(image_list, axis=0)[close_freq]
            if plot_amplitude == 1:
                processed_image = np.abs(fft_data)
            elif plot_phase == 1:
                processed_image = np.angle(fft_data)
            update_fft_plot(plot_widget,
                            processed_image)  # FIXME: Why is the experiment taking care of updating a plot?
            data_set[iterate, :,
            :] = fft_data  # iterate[0] += 1  # if iterate[0] == int(total_fft_frames):  # Save collection array with fft analysed images  #     np.save(save_directory + file_title, data_set)  #     print(str(iterate[0]))  #     print('Saved')
