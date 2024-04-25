"""
most basic script for connecting a basler camera and reading images
based on the instruction by Aquiles
https://www.pythonforthelab.com/blog/getting-started-with-basler-cameras/

the main purpose of this script is to test the readout modes of basler and
find the fastest way of grabbing data.
"""
import numpy as np
from pypylon import pylon
import time

tl_factory = pylon.TlFactory.GetInstance()
devices = tl_factory.EnumerateDevices()
for device in devices:
    print(device.GetFriendlyName())

#defining camera

exptime = 2 #exposure time in ms

t00 = time.time()

#initializing camera
camera = pylon.InstantCamera()
camera.Attach(tl_factory.CreateFirstDevice())
camera.Open()
#setting camera parameters
camera.OffsetX.SetValue(0)
camera.OffsetY.SetValue(0)
camera.Width.SetValue(camera.WidthMax.GetValue())
camera.Height.SetValue(camera.HeightMax.GetValue())
camera.GainAuto.SetValue('Off')
camera.ExposureAuto.SetValue('Off')

camera.ExposureTime.SetValue(exptime*1000)
camera.Height.SetValue(64)

pixel_format = camera.PixelFormat.GetValue()
print('format:', pixel_format)
if pixel_format == 'Mono8':
    cam_dtype = np.uint8
elif pixel_format == 'Mono12' or pixel_format == 'Mono12p':
    cam_dtype = np.uint16

camera.StartGrabbing(1)
grab = camera.RetrieveResult(1000, pylon.TimeoutHandling_Return)
if grab.GrabSucceeded():
    image = grab.GetArray()
    print(f'Size of image: {image.shape}')
    #im = ax.imshow(image, cmap=plt.cm.hot, origin='upper')
else:
    image=[]
    print('unable to grab an image')

ypix, xpix = camera.Height.Value, camera.Width.Value

def multiframe1(i, size, tproc):
    """

    :param i: desired number of frames to capture
    :param size: array size set on the camera
    :param tproc: max time reserved for processing
    :return:
    """

    [xp, yp] = size
    if camera.IsGrabbing():
        camera.StopGrabbing()
    imgarray = np.zeros((xpix, ypix, i), dtype= cam_dtype)
    camera.StartGrabbingMax(i)
    t0 = time.time()   #note that system time is given in seconds
    rf = 0
    while camera.IsGrabbing():
        grab = camera.RetrieveResult(exptime+50, pylon.TimeoutHandling_ThrowException)
        if grab.GrabSucceeded():
            tempimg = grab.GetArray().T
            imgarray[:, :, rf] = tempimg
            rf += 1
            #basler-video.pyprint(rf, 'success')
        tlap = (time.time() - t0) * 1000
        #if rf >= i or tlap > tproc:
        #    camera.StopGrabbing()

    #grab.Release()
    print(f'Acquired {rf} of {i} possible frames in {tlap} ms')

    return imgarray

def multiframe2(i, size, tproc):
    """

    :param i: desired number of frames to capture
    :param size: array size set on the camera
    :param tproc: max time reserved for processing
    :return:
    """

    [xp, yp] = size
    if camera.IsGrabbing():
        camera.StopGrabbing()
    camera.MaxNumBuffer = i+1
    camera.OutputQueueSize = camera.MaxNumBuffer.Value
    camera.StartGrabbing(pylon.GrabStrategy_OneByOne)
    imgarray = np.zeros((xpix, ypix, i), dtype= cam_dtype)
    t0 = time.time()   #note that system time is given in seconds
    rf = 0
    for rf in range(i):
        grab = camera.RetrieveResult(exptime+50, pylon.TimeoutHandling_ThrowException)
        if grab and grab.GrabSucceeded():
            imgarray[:, :, rf] = grab.GetArray().T
            # basler-video.pyprint(rf, 'success')
            grab.Release()
        tlap = (time.time() - t0) * 1000

    camera.StopGrabbing()

    print(f'Acquired {rf+1} of {i} possible frames in {tlap} ms')

    return imgarray

tproc = 3000     #time duration in ms of grabbing an array

for j in range (15):
    dat = multiframe1(j+1, [xpix, ypix], tproc)
    dat = multiframe2(j+1, [xpix, ypix], tproc)
    print(dat.shape)

# closing the camera processes
# print(f'Acquired {imgcount} frames in {time.time()-t00:.0f} seconds')

camera.Close()



