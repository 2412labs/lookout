from util.queue_worker import QueueWorker
from rpi_image_processor import RpiImageProcessor
from rpi_camera import RpiCamera
from contour import Contour
from motionstate import MotionState
import cv2
import numpy as np
import time
import base64
import uuid
import logging

class MotionDetector:
    _logger = logging.getLogger(__name__)

    def __init__(self, outQueue, camId, resolution, workers, sensorMode, fps, quality, downscale=None):
        self.out_queue = outQueue
        self.cam_id = camId
        self.resolution = resolution
        self.fps = fps
        self.fpsPer = int(fps/2)
        self.cam_scale = downscale
        self.low_res = None
        if downscale != None:
            self.low_res = (int(resolution[0]/downscale),int(resolution[1]/downscale))
        else:
            # scale required to crop images, when None scale should be 1
            self.cam_scale = 1
        self.imageCaptureQueue = QueueWorker("image_capture_queue", self.consumeImageCaptureQueue)
        self.processor = RpiImageProcessor(self.imageCaptureQueue, resize=self.low_res, maxlen=workers)
        self.camera = RpiCamera(image_processor=self.processor, sensor_mode=sensorMode, resolution=resolution, framerate=fps, quality=quality)
        self.img_avg = None
        self.current_frame = None

        #TODO make all the following values configuration
        self.minMotionArea = 2000
        self.ms = MotionState(camera_id=self.cam_id, minMotionFrames=7, activeTimeout=7, inactiveTimeout=2)

    def startCapture(self):
        self.imageCaptureQueue.startWorker()
        self.processor.startWorkers()
        self.camera.startCapture()
        time.sleep(1)

    def stopCapture(self):
        self.imageCaptureQueue.stopWorker()
        self.camera.stopCapture()
        self.processor.stopWorkers()

    def consumeImageCaptureQueue(self, data):
        self.current_frame_small = data['i_small']
        self.current_frame_large = data['i_large']

        if self.img_avg is None:
            self.img_avg = data['i_blur'].copy().astype("float")
            self._logger.info("initializing img avg ...")
            return

        motion_started = False
        motion_ended = False

        contours = self.img_get_contours(data['i_blur'], self.img_avg)
        if len(contours) > 1:
            contours = [max(contours, key= lambda x: x.area)]

        if len(contours) > 0:
            motion_started = self.ms.processMotionFrame(contours[0])

            if motion_started \
                or (self.ms.isMotionActive \
                and self.ms.sendStream == True \
                and self.ms.sendStreamCount <= 30 \
                and self.ms.frameCount%self.fpsPer == 0):

		direction = self.ms.getDirection()

		if direction != None:
               		# crop hi resolution image to the area of motion
               		crop = contours[0].cropFrame(data['i_large'], self.cam_scale)

               		# cropped image must have minimum of 80x80
               		if crop.shape[0] > 80 and crop.shape[1] > 80:
				self.ms.sendStreamCount += 1
				self.push_img(crop, data['i_large'].shape, contours[0], direction)
        else:
            motion_ended = self.ms.processNonMotionFrame()

    def push_img(self, img, originalSize, contour, direction):
            msg = self.getPushImgMsg(
                img,
                self.ms.sessionName,
                self.ms.frameCount,
                direction,
                originalSize,
                self.getBoundingJson(contour),
                contour.area
            )
            self.out_queue.put(msg)

    def push_test_img(self, img):
        msg = self.getPushImgMsg(img, "t-{0}".format(str(uuid.uuid4())[:8]), "1", { 'direction': 'S', 'dx': 10, 'dy': 50}, img.shape, self.getBoundingJson(None), 1)
        self.out_queue.put(msg)

    def getPushImgMsg(self, img, session, sequence, direction, originalSize, originalBoundingBox, motionContourArea):
        return {
            "imageNp": cv2.imencode('.jpg',img)[1],
            "imageName": "{}_{}.jpg".format(session, sequence),
            "event": { 
                "eventId": session,
                "eventTime": int(time.time()),
                "direction": direction,
                "captureSizeW": originalSize[1],
                "captureSizeH": originalSize[0],
                "motionSizeW": img.shape[1],
                "motionSizeH": img.shape[0],
                "originalBoundingBox": originalBoundingBox,
                "motionContourArea": motionContourArea
            }
        }

    def getBoundingJson(self, contour):
        if contour is None:
            return self._getBoundingJson(0,0,0,0,0,0)
        box = contour.getScaledBoundingBox(self.cam_scale)
        (rw,rh) = self.resolution
        return self._getBoundingJson(l=float(box.x/rw), t=float(box.y/rh), w=float(box.w/rw), h=float(box.h/rh), cx=float(box.cx/rw), cy=float(box.cy/rh))

    def _getBoundingJson(self, l, t, w, h, cx, cy):
        return { "Left": l, "Top": t, "Width": w, "Height": h, "CenterX": cx, "CenterY": cy}

    def img_get_contours(self, img_gray, img_avg):
        cv2_cnts = self.img_cv2_find_contours(img_gray, img_avg)
        contours = []
        for c in cv2_cnts:
            cnt = Contour(c)
            if cnt.area < self.minMotionArea:
                continue
            contours.append(cnt)
        return contours

    def img_cv2_find_contours(self, img_gray, img_avg):
    	cv2.accumulateWeighted(img_gray, img_avg, 0.5)
    	frameDelta = cv2.absdiff(img_gray, cv2.convertScaleAbs(img_avg))
    	thresh = cv2.threshold(frameDelta, 5, 255, cv2.THRESH_BINARY)[1]
    	thresh = cv2.dilate(thresh, None, iterations=2)
    	return cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

    def stats(self):
        return self.camera.stats()
