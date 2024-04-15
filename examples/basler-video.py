"""
most basic script for connecting a basler camera and reading images
based on the instruction by Aquiles
https://www.pythonforthelab.com/blog/getting-started-with-basler-cameras/

"""
import numpy as np
from pypylon import pylon
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time
import matplotlib
matplotlib.use('TkAgg')

tl_factory = pylon.TlFactory.GetInstance()
devices = tl_factory.EnumerateDevices()
for device in devices:
    print(device.GetFriendlyName())

#defining camera and gui parameters



t00 = time.time()

#initializing camera
camera = pylon.InstantCamera()
camera.Attach(tl_factory.CreateFirstDevice())
camera.Open()
camera.OffsetX.SetValue(0)
camera.OffsetY.SetValue(0)
camera.Width.SetValue(camera.WidthMax.GetValue())
camera.Height.SetValue(camera.HeightMax.GetValue())
camera.GainAuto.SetValue('Off')
camera.ExposureAuto.SetValue('Off')


#setting camera parameters
exptime = 2 #exposure time in ms

camera.ExposureTime.SetValue(exptime*1000)
#camera.Height.SetValue(350)

pixel_format = camera.PixelFormat.GetValue()
print('format:', pixel_format)
if pixel_format == 'Mono8':
    cam_dtype = np.uint8
elif pixel_format == 'Mono12' or pixel_format == 'Mono12p':
    cam_dtype = np.uint16

fig, ax = plt.subplots()

camera.StartGrabbing(1)
grab = camera.RetrieveResult(1000, pylon.TimeoutHandling_Return)
if grab.GrabSucceeded():
    image = grab.GetArray()
    print(f'Size of image: {image.shape}')
    im = ax.imshow(image, cmap=plt.cm.hot, origin='upper')
else:
    image=[]
    print('unable to grab an image')

ypix, xpix = camera.Height.Value, camera.Width.Value

def update(i, image, nf):
    if camera.IsGrabbing():
        camera.StopGrabbing()
    imgarray = np.zeros((xpix, ypix, nf), dtype= cam_dtype)
    camera.MaxNumBuffer = nf+1
    camera.OutputQueueSize = camera.MaxNumBuffer.Value
    camera.StartGrabbing(pylon.GrabStrategy_OneByOne)

    t0 = time.time()   #note that system time is given in seconds
    rf = 0
    for n in range(nf):
        grab = camera.RetrieveResult(exptime+180, pylon.TimeoutHandling_ThrowException)
        if grab and grab.GrabSucceeded():
            imgarray[:, :, rf] = grab.GetArray().T
            rf += 1
            grab.Release()

    tlap = (time.time() - t0) * 1000
    print(f'Acquired {rf} of {nf} possible frames in {tlap} ms')
    image = np.mean(imgarray,axis=2)
    im.set_data(image)
    fig.canvas.draw()
    fig.canvas.flush_events()

nf = 2   # number of frames to grab an analyze between views
tproc = nf * exptime + 200   #time duration in ms of image processing, empirically adjusted
ani = animation.FuncAnimation(fig, update, fargs=(image, nf), interval=tproc)
plt.show()


#closing the camera processes

camera.Close()
