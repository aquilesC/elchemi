""" This script uses threading to simulatneously capture camera images and process them live to project the dominant frequency component.
    Here, a Basler camera captures images of a flickering lamp and then plots the frequency of the flickering lamp."""
# import libraries
import numpy as np
import cv2
import threading
import time
from collections import deque
with open(r'GIVE_FILE_LOCATION_TO_DWF_CONSTANTS_SCRIPT_HERE, 'r') as file:
    code_to_run = file.read()
exec(code_to_run) # used to import dwfconstants
import dwfconstants
from pypylon import pylon  # Python wrapper for Basler pylon Camera Software Suite
from dwfconstants import *  # Constants and enumerations related to the dwf library
from queue import Queue
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QTimer
import pyqtgraph as pg


""" Extract variables and constants"""
# configue AD2
hdwf = c_int()
dfw = cdll.dwf
# Open device
dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))
# check if succesfully opened
if hdwf.value == hdwfNone.value:
    print("Failed to open device")
    exit()

"""Parameters for analysis:
    1. Set total number of frames you want the camera to acquire
    2. Set frequency of both camera capturing and of waveform generator
    3. Determine how many images are used for fft analysis
    4. Set size of images (number of pixels to analyze)"""
total_frames = 1000  # Total number of frames to acquire before run stops

# parameters for AD2
frequency_W1 = 25
amplitude_W1 = 3.3
frequency_W2 = 100
amplitude_W2 = 5

nr_data_points = 100
# parameters for Basler camera
ROI_size = (100, 100)
roi_width = ROI_size[0]
roi_height = ROI_size[1]
roi_fft_width = 50
roi_fft_height = 50
center_x = 8
center_y = 4

# Set your Region Of Interest (ROI) eg: nr. pixels to analyse during fft analysis
# ROI_size = (100, 100) # Number of rowes x number of pixels per row

# definition to update the live plot window
def update_plot(plot_widget, x, y):
    plot_widget.plot(x, y, clear=True)
# definitioni to sent a square wave from the AD2 to the lamp
def generate_square_wave_W1(hdwf, frequency, amplitude):
    dwf.FDwfAnalogOutNodeEnableSet(hdwf, c_int(0), AnalogOutNodeCarrier, c_int(1))
    dwf.FDwfAnalogOutNodeFunctionSet(hdwf, c_int(0), AnalogOutNodeCarrier, funcSquare)
    dwf.FDwfAnalogOutNodeFrequencySet(hdwf, c_int(0), AnalogOutNodeCarrier, c_double(frequency))
    dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, c_int(0), AnalogOutNodeCarrier, c_double(amplitude))
    dwf.FDwfAnalogOutConfigure(hdwf, c_int(0), c_int(1))
# definition to sent a square wave from the AD2 to the camera
def generate_square_wave_W2(hdwf, frequency, amplitude):
    dwf.FDwfAnalogOutNodeEnableSet(hdwf, c_int(1), AnalogOutNodeCarrier, c_int(1))
    dwf.FDwfAnalogOutNodeFunctionSet(hdwf, c_int(1), AnalogOutNodeCarrier, funcSquare)
    dwf.FDwfAnalogOutNodeFrequencySet(hdwf, c_int(1), AnalogOutNodeCarrier, c_double(frequency))
    dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, c_int(1), AnalogOutNodeCarrier, c_double(amplitude))
    dwf.FDwfAnalogOutConfigure(hdwf, c_int(1), c_int(1))
# definition to set up camera for trigger mode (picture is taken when square wave reaches amplitude)  
def configure_camera_for_trigger(camera):
    # Set trigger mode to "On"
    camera.TriggerMode.SetValue("On")
    # Set the trigger source to Line 1 (external trigger)
    camera.TriggerSource.SetValue("Line1")
    # Set trigger selector to "FrameStart" (trigger before image capture)
    camera.TriggerSelector.SetValue("FrameStart")
# definition to store the camera images in a queue 
def grab_and_acquire_images(camera, circular_buffer, total_frames, start_event, dwf):
    camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
    counter = 0
    start_time_pictures = time.time()
    try:  
        for i in range(total_frames):
            grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            circular_buffer.put(grab_result.Array)
            counter += 1
            if counter == nr_data_points:
                end_time_pictures = time.time()
                elapsed_time = end_time_pictures - start_time_pictures
                print("Time to take 100 pictures =", elapsed_time, "seconds")
                # array_fft = []
                # j = 0
                # while j < 6:
                #     array_fft.append(circular_buffer.get())
                #     j += 1
                # np.save(r"C:\Users\roman\OneDrive\Documenten\Roman\UU positie\Sanli project\FinalCodes\Data/Test_fft_images", array_fft)
                start_event.set()                
    except pylon.TimeoutException as e:
        print("TimeoutException: ", str(e))
    finally:
        camera.StopGrabbing()  # Stop grabbing images
        print("Thread one is finished")
        print("Filled up queue size:", circular_buffer.qsize())
        # Close AD2 device
        dwf.FDwfDeviceCloseAll()
        # Close camera
        camera.Close()
# definition to grab the queued images, analyse them and sent plot them in the live plot window
def generate_new_data(x_data, y_data, data, circular_buffer, plot_widget):
    if circular_buffer.empty():
        time.sleep(0.1)
    while not circular_buffer.empty():
        # print("Queue size:", circular_buffer.qsize())
        image = circular_buffer.get()
        data.append(image)
        if len(data) > nr_data_points:
            data.pop(0)
    x_data, y_data = perform_fft_analysis(data)
    update_plot(plot_widget, x_data, y_data)
# definition to wait for first 100 images before the plot is created and starts showing the live data points
def create_live_plot(circular_buffer, start_event):
    start_event.wait()
    data = []
    for n in range(nr_data_points):
        data.append(circular_buffer.get())
    x_data, y_data = perform_fft_analysis(data)
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Live Magnitue Spectrum")
    plot_widget = pg.PlotWidget()
    window.setCentralWidget(plot_widget)
    update_plot(plot_widget, x_data, y_data)  # Initialize plot with initial data
    timer = QTimer()
    timer.timeout.connect(lambda: generate_new_data(x_data, y_data, data, circular_buffer, plot_widget))
    timer.start(50)
    window.show()
    sys.exit(app.exec_())
# definition to 
def perform_fft_analysis(circular_buffer):
    intensity_data = extract_intensity_data(circular_buffer)
    flickering_frequency, fft_freq, magnitude_spectrum = calculate_flickering_frequency(intensity_data)
    magnitude_spectrum[0] = 0
    return fft_freq, magnitude_spectrum    
# definition to extract the mean intensity from each ROI 
def extract_intensity_data(circular_buffer):
    pixel_intensity_time_series = []
    for circ_buffer in circular_buffer:
        intensity = np.mean(circ_buffer)#[pixel_start_point[0]:pixel_end_point[0], pixel_start_point[1]:pixel_end_point[1]])
        pixel_intensity_time_series.append(intensity)
    return pixel_intensity_time_series
# definition to calculate the frequency with which the lamp flickers with respect to the frequency of the camera
def calculate_flickering_frequency(intensity_data):
    fft_result = np.fft.fft(intensity_data)
    fft_freq = np.fft.fftfreq(len(fft_result), d=1.0/frequency_W2)
    magnitude_spectrum = np.abs(fft_result)
    magnitude_spectrum[0] = 0
    dominant_frequency_index = np.argmax(magnitude_spectrum)
    dominant_frequency = np.sqrt(np.square(fft_freq[dominant_frequency_index]))
    return dominant_frequency, fft_freq, magnitude_spectrum
    
# Generate square waves on W1 and W2 channels of AD2
generate_square_wave_W1(hdwf, frequency_W1, amplitude_W1)
generate_square_wave_W2(hdwf, frequency_W2, amplitude_W2)
# Configure Basler camera
camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
camera.Open()
#Adjust camera
camera.ExposureTime.SetValue(800)  # Set exposure time to 800 us
camera.Gamma.SetValue(1.0)  # Try different gamma values
camera.GainAuto.SetValue("Off")  # Turn off automatic gain
camera.Gain.SetValue(19.0)  # Increase the gain value
camera.OffsetX.SetValue(0)
camera.OffsetY.SetValue(0)
camera.Width.SetValue(camera.WidthMax.GetValue())
camera.Height.SetValue(camera.HeightMax.GetValue())
# Configure the camera for trigger mode
configure_camera_for_trigger(camera)
# Set camera ROI settings
width = int(roi_width - roi_width %4)
height = int(roi_height - roi_height %4)
camera.Width.SetValue(width)
camera.Height.SetValue(height)
camera.OffsetX.SetValue(center_x)
camera.OffsetY.SetValue(center_y)

# main code
def main():
    circular_buffer = Queue(maxsize=1000)
    # Create an event to signal when Thread 1 has captured 100 images
    start_event = threading.Event()
    # Create Thread 1 (image capture) and start it
    thread1 = threading.Thread(target=grab_and_acquire_images, args=(camera, circular_buffer, total_frames, start_event, dwf))
    thread1.start()
    # Create Thread 2 (image analysis) and start it
    test_nr = 0
    thread2 = threading.Thread(target=create_live_plot, args=(circular_buffer, start_event))
    thread2.start()
    # Wait for both threads to finish (this won't happen in this example as threads run indefinitely)
    thread1.join()
    thread2.join()
    
if __name__ == "__main__":
    main()


