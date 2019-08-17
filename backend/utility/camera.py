#!/usr/bin/python
# -*- coding: utf8 -*-


import os
import base64
import time
import platform

if platform.system().lower() == 'windows':
    import cv2
elif platform.system().lower() == 'linux':
    import picamera
else:
    pass


# 拍照
def capturePicture(picFile):
    if platform.system().lower() == 'windows':
        cap = None
        ret = False
        try:
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                ret, frame = cap.read()
                if ret:
                    cv2.imwrite(picFile, frame)
        finally:
            cap.release()
            cv2.destroyAllWindows()
            return ret
    elif platform.system().lower() == 'linux':
        with picamera.PiCamera() as camera:
            camera.resolution = (640, 480)
            camera.start_preview()
            time.sleep(2)
            camera.capture(picFile)
            return True
        return False
    else:
        return False


# 将图片转换为 Base64 格式
def pictureToBase64(picFile):
    x = ''
    with open(picFile, 'rb') as f:
        x = base64.b64encode(f.read())
    return x


if __name__ == '__main__':
    picFile = 'test.jpg'
    if os.path.isfile(picFile):
        try:
            os.remove(picFile)
        except:
            pass
    capturePicture(picFile)
