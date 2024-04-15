"""
most basic script for connecting a basler camera and reading images
based on the instruction by Aquiles
https://www.pythonforthelab.com/blog/getting-started-with-basler-cameras/

"""


from pypylon import pylon
import matplotlib
import matplotlib.pyplot as plt
import time
matplotlib.use('TkAgg')

fig, ax = plt.subplots()

tl_factory = pylon.TlFactory.GetInstance()
devices = tl_factory.EnumerateDevices()
for device in devices:
    print(device.GetFriendlyName())

camera = pylon.InstantCamera()
camera.Attach(tl_factory.CreateFirstDevice())
camera.Open()
camera.ExposureTime.SetValue(500)

print('Starting to acquire')

camera.StartGrabbing(1)
grab = camera.RetrieveResult(1000, pylon.TimeoutHandling_Return)
if grab.GrabSucceeded():
    image = grab.GetArray()
    print(f'Size of image: {image.shape}')
    im = ax.imshow(image)
    plt.show()

camera.Close()

#


