""" This script uses threading to simulatneously capture camera images and process them live to project the fft analyzed images"""
# import libraries
import numpy as np
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
from scipy.fft import fft
import matplotlib.pyplot as plt


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

plot_amplitude = 1
plot_phase = 0


total_frames = 500  # Total number of frames to acquire before run stops

# parameters for AD2
frequency_W1 = 0.5 # Flickering lamp frequency
amplitude_W1 = 0.1
frequency_W2 = 10 # Camera image grabbing frequency
amplitude_W2 = 5


exposure_time = 50000

Sample = "Sprayed_ITO"
file_title = "Live_fft_" + str(amplitude_W1) + "V_" + str(frequency_W1) + "Hz_" + str(frequency_W2) + "Hz_" + Sample 

nr_data_points = 100 # Total images used for frequency determination of flickering lamp
# parameters for Basler camera
ROI_size = (600, 600) # Camera pixel area
roi_width = ROI_size[0]
roi_height = ROI_size[1]
roi_fft_width = 600 # Analyzable pixel width for fft projection
roi_fft_height = 600 # Analyzable pixel height for fft projection
ROI_fft_size = (roi_fft_width, roi_fft_height) # Analyzable pixel area for fft projection
center_x = 204
center_y = 204

min_cycles = 6 # minimum number of periods used for fft analysis of images
save_directory = r"INSERT_SAVE_LOCATION_HERE"

# Set your Region Of Interest (ROI) eg: nr. pixels to analyse during fft analysis

# definition to update the live plot window
def update_plot(plot_widget, x, y):
    plot_widget.plot(x, y, clear=True)
# definitioni to sent a square wave from the AD2 to the lamp
def generate_square_wave_W1(hdwf, frequency, amplitude):
    dwf.FDwfAnalogOutNodeEnableSet(hdwf, c_int(0), AnalogOutNodeCarrier, c_int(1))
    # dwf.FDwfAnalogOutNodeFunctionSet(hdwf, c_int(0), AnalogOutNodeCarrier, funcSine)
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
    start_time_pictures = time.time() # Measure time it takes for first 100 pictures to be taken
    try:  
        for i in range(total_frames):
            grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            circular_buffer.put(grab_result.Array) # Grab images and store them in a buffer 
            counter += 1
            if counter == nr_data_points:
                end_time_pictures = time.time()
                elapsed_time = end_time_pictures - start_time_pictures
                print("Time to take 100 pictures =", elapsed_time, "seconds")
                start_event.set() # Start analysis thread          
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

# definition to wait for first 100 images before the plot is created and starts showing the live data points
def find_dominant_frequency(circular_buffer, start_event):
    start_event.wait() # Wait for first 100 images to be captured and stored in buffer
    data = []
    for n in range(nr_data_points):
        data.append(circular_buffer.get()) # Collect all 100 images in a list
    x_data, y_data, dominant_frequency = perform_fft_analysis(data) # Extract dominant frequency 
    # Create a figure for the second plot
    plt.figure(figsize=(10, 6))
    
    # Plot the Fourier Transform of the acquired signal
    plt.plot(x_data, y_data, linestyle="-", color="blue")
    # plt.xlim(frequency2 - 5, frequency2 + 5)  # Set x-axis limit around the expected peak frequency
    plt.xlabel("Frequency [Hz]")
    plt.ylabel("Amplitude [au]")
    plt.title("Fourier Transform of first 100 images", fontsize=14)
    plt.grid(True)
    
    # Show both plots
    plt.show()
    
    print("The dominant frequency is", dominant_frequency, "Hz")
    
    # dominant_frequency = frequency_W1
    
    min_frames = int(frequency_W2/ dominant_frequency) # Number of images taken for one full oscilating period of dominating frequency of flickering lamp
    cycle_frames = min_frames*min_cycles # Number of images that will be used for fft analysis 
    freqs = np.fft.fftfreq(cycle_frames, 1/frequency_W2) 
    close_freq = (np.abs(freqs-dominant_frequency)).argmin()
    total_fft_frames = (total_frames-nr_data_points) / cycle_frames # Total number of fft analyses that will be performed 
    print("There will be " + str(int(total_fft_frames)) + " fft_images plotted and saved")
    # data_set = np.zeros((int(total_fft_frames), ROI_fft_size[0], ROI_fft_size[1]), dtype=complex) # Set up collection array for fft analyzed images
    data_set = np.zeros((int(total_fft_frames), 123, 98), dtype=complex) # Set up collection array for fft analyzed images

    iterate = [0] 
    # Set up plotting window
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Live fft images")
    plot_widget = pg.PlotWidget()
    window.setCentralWidget(plot_widget)
    timer = QTimer()
    # Updat plot window with new data every 50 miliseconds
    timer.timeout.connect(lambda: generate_new_data_fft(circular_buffer, plot_widget, cycle_frames, close_freq, data_set, iterate, total_fft_frames))
    timer.start(50)
    window.show()
    sys.exit(app.exec_())
    
# definition that returns all the frequencies present in the first 100 images, with their intensity plus the extracted dominant frequency present in the signal
def perform_fft_analysis(circular_buffer):
    intensity_data = extract_intensity_data(circular_buffer)
    flickering_frequency, fft_freq, magnitude_spectrum = calculate_flickering_frequency(intensity_data)
    magnitude_spectrum[0] = 0
    return fft_freq, magnitude_spectrum, flickering_frequency    
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

# definition that grabs number of cycled frames from buffer, fft analyses them and updates the plot window with the new image
def generate_new_data_fft(circular_buffer, plot_widget, cycle_frames, close_freq, data_set, iterate, total_fft_frames):
    image_list = []
    treshold = 5 # Set treshold value for when buffer is empty so the analysis part of the code is skipped
    consecutive_counter = 0
    new_data_available = True
    while len(image_list) < cycle_frames and new_data_available: # Add number of cycled frames of buffer images to the list 
        if circular_buffer.empty():
            time.sleep(0.25) # Wait for buffer to be updated with new images
            consecutive_counter += 1
            if consecutive_counter >= treshold:
                new_data_available = False
        if not circular_buffer.empty():
            image_capture = circular_buffer.get()
            # image_list.append(image_capture[0:ROI_fft_size[0], 0:ROI_fft_size[1]]) # Crop image to desired ROI
            image_list.append(image_capture[125:248, 150:248]) # Crop image to desired ROI
            consecutive_counter = 0
    if int(len(image_list)) == cycle_frames: # perform fft when list is exactly filled with number of cycled frames
        fft_data = fft(image_list, axis = 0)[close_freq] 
        if plot_amplitude == 1:
            processed_image = np.abs(fft_data) 
        elif plot_phase == 1:
            processed_image = np.angle(fft_data)
        update_fft_plot(plot_widget, processed_image)
        data_set[iterate, :, :] = fft_data
        iterate[0] += 1
        if iterate[0] == int(total_fft_frames): # Save collection array with fft analysed images
            np.save(save_directory + file_title, data_set)
            print(str(iterate[0]))
            print('Saved')
# definition to update plotting window
def update_fft_plot(plot_widget, magnitude_spectrum):
    plot_widget.clear()
    image_item = pg.ImageItem(image=magnitude_spectrum)
    plot_widget.addItem(image_item)
    
# Generate square waves on W1 and W2 channels of AD2
generate_square_wave_W1(hdwf, frequency_W1, amplitude_W1)
generate_square_wave_W2(hdwf, frequency_W2, amplitude_W2)
# Configure Basler camera
camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
camera.Open()
#Adjust camera
camera.ExposureTime.SetValue(exposure_time)  # Set exposure time to 800 us
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
    thread2 = threading.Thread(target=find_dominant_frequency, args=(circular_buffer, start_event))
    thread2.start()
    
    # Wait for both threads to finish (this won't happen in this example as threads run indefinitely)
    thread1.join()
    thread2.join()
    
    
if __name__ == "__main__":
    main()
    
