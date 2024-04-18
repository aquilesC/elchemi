from elchemi.devices.exceptions import DeviceException


class CameraException(DeviceException):
    pass


class CameraNotFound(CameraException):
    pass

class WrongCameraState(CameraException):
    pass
