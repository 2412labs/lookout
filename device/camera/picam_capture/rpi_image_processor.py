from datetime import datetime as dt
from threading import Thread
import os
import numpy as np
import cv2
import time
import io
import logging
import sys
if sys.version_info[0] >= 3:
    import queue
else:
    import Queue as queue
import traceback

class RpiImageProcessor(object):
    _logger = logging.getLogger(__name__)

    def __init__(self, q_img, resize, maxlen=3):
        self.last = None
        self.q_out = q_img
        self.resize = resize
        self.maxlen=maxlen
        self.q_in = queue.Queue()
        self.workers = []

    def startWorkers(self):
        self._logger.info("RpiImageProcessor created with settings [maxlen, resize]: {0}".format([self.maxlen, self.resize]))
        self._logger.info("starting RpiImageProcessor workers")
        for i in range(self.maxlen):
            t = Thread(target=self.process_image, args=(i,))
            self.workers.append(t)
            t.start()

    def stopWorkers(self):
        self._logger.info("stopping RpiImageProcessor workers")
        # wait until Queue is empty
        self.q_in.join()
        # signal each worker to stop with None value
        for i in range(self.maxlen):
            self.q_in.put(None)
        # join each worker
        for t in self.workers:
            t.join()
        self._logger.info("RpiImageProcessor workers are stopped")

    def process(self, img, fc):
        self.current_raw = img
        self.q_in.put({'i':img, 'fc':fc})

    def check_queue_size(self):
        if self.q_in.qsize() > self.maxlen*3:
            self._logger.info("RpiImageProcessor max queue length exceeded.  Add more workers or reduce framerate, resolution, or quality.")
            self._logger.info("dumping RpiImageProcessor internal queue")
            # clearing this way because q_in.mutex does not appear to work .. (a q_in.join after a clear blocks forever)
            while self.q_in.qsize() > self.maxlen:
                self.q_in.get()
                self.q_in.task_done()

    def process_image(self, id):
        while True:
            try:
                self.check_queue_size()

                item = self.q_in.get()

                if item is None:
                    break

                self.add_to_queue(item)

                self.q_in.task_done()
            except KeyboardInterrupt:
                pass
            except Exception as e:
                self._logger.error(repr(e))
                self._logger.error("stack trace:\n{}".format(traceback.format_exc()))

    def add_to_queue(self, item):
        img_large = cv2.imdecode(np.fromstring(item['i'], dtype=np.uint8), 1)
        img_gray_large = cv2.cvtColor(img_large, cv2.COLOR_BGR2GRAY)
        img_gray_small = img_gray_large
        if self.resize != None:
            img_gray_small = cv2.resize(img_gray_large, self.resize)
        img_blur = cv2.GaussianBlur(img_gray_small, (21, 21), 0)
        msg = {'fc': item['fc'], 'i_blur': img_blur, 'i_small': img_gray_small, 'i_large': img_gray_large}
        self.q_out.put(msg)
