from picamera import PiCamera
from datetime import datetime as dt
from threading import Thread
import os
import time
import io
import logging
import traceback

class RpiCamera(object):
    _logger = logging.getLogger(__name__)

    def __init__(self, image_processor, sensor_mode, resolution, framerate, quality):
        self.start = None
        self.end = None
        self.processor = image_processor
        self.cam_settings = [sensor_mode, resolution, framerate, quality]
        self.done = False
        self.last_fc = 0
        self.last_check = None

    def startCapture(self, splitter_port=0, encoding='jpeg', stopat=None):
        self.stopat = stopat
        self.t = Thread(target=self.cam_loop, args=(splitter_port, self.cam_settings[3], encoding))
        self.t.start()
        # block until first frame is read ...
        while self.end is None:
            time.sleep(.1)
            pass

    def stopCapture(self):
        self._logger.info("stopping camera capture ...")
        self.done = True
        self.t.join()
        self._logger.info("camera capture stopped")

    def cam_loop(self, splitter_port, quality, encoding):
        try:
            self.frame_count = 0
            self.camera = PiCamera(sensor_mode=self.cam_settings[0])
            self.camera.resolution = self.cam_settings[1]
            self.camera.framerate = self.cam_settings[2]
            time.sleep(2)
            self._logger.info("camera started with settings (sensor_mode, resolution, framerate, quality): {0}".format(self.cam_settings))
            self._logger.info("starting capture_sequence with settings (splitter_port, encoding): {0}".format([splitter_port, encoding]))
            if self.stopat != None:
                self._logger.info("stopping at {0} frames".format(self.stopat))
            self.camera.capture_sequence(self.streamgen(), splitter_port=splitter_port, format=encoding, use_video_port=True, quality=quality)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            self._logger.error(repr(e))
            self._logger.error("stack trace:\n{}".format(traceback.format_exc()))
        finally:
            self._logger.info("closing picamera ...")
            self.camera.close()
            self._logger.info("picamera closed")

    def streamgen(self):
        s = io.BytesIO()
        self.start = dt.now()

        while True:
            try:
                if self.done:
                    break
                if self.stopat != None:
                    if self.frame_count == self.stopat:
                        self.done = True
                        break

                yield s

                self.frame_count += 1
                img = s.getvalue()
                if not img.startswith(b'\xff\xd8'):
                    continue

                self.processor.process(img, self.frame_count)

                s.seek(0)
                s.truncate()
                self.end = dt.now()

            except KeyboardInterrupt:
                pass
            except Exception as e:
                self._logger.error(repr(e))
                self._logger.error("stack trace:\n{}".format(traceback.format_exc()))

    def stats(self, total=False):
        # make sure at least 1 frame has been read
        if self.end is None:
            return "stats not available yet"

        start = self.last_check or self.start
        fc = self.frame_count-self.last_fc

        if total:
            start = self.start
            fc = self.frame_count

        delta = (dt.now()-start).total_seconds()
        fps = fc/delta

        self.last_fc = self.frame_count
        self.last_check = dt.now()

        return {
            "msg": "{} frames in {}s, fps {}".format(fc, delta, fps),
            "fps": fps,
            "frame_count": fc,
            "seconds": delta
        }
