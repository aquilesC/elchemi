from pypylon import pylon
import numpy as np
from PIL import Image

def test_camera():
    camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
    camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
    i=0
    while camera.IsGrabbing():
        i+=1
        grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        if grabResult.GrabSucceeded():
            img = grabResult.Array
            image = Image.fromarray(img)
            print("Captured image", img.shape)
            image.show()
        else:
            print("Error: ", grabResult.ErrorCode, grabResult.ErrorDescription)
        grabResult.Release()
        if i == 5:
            break  # Capture only one image for test purposes
    
    camera.StopGrabbing()

if __name__ == "__main__":
    test_camera()
