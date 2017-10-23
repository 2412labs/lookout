from threading import Thread
import Queue
import logging
import traceback

class QueueWorker:
    _logger = logging.getLogger(__name__)

    def __init__(self, name, targetMethod, warnThreshold=10, dumpThreshold=30):
        self.name = name
        self.dump = dumpThreshold
        self.warn = warnThreshold
        self.q_in = Queue.Queue()
        self.targetMethod = targetMethod
        self.t = Thread(target=self._consume)

    def startWorker(self):
        self._logger.debug("starting queue worker for {}".format(self.name))
        self.t.start()

    def stopWorker(self):
        self._logger.debug("stopping queue worker for {}".format(self.name))
        self.q_in.put(None)
        self.t.join()
        self._logger.debug("queue worker for {} is stopped".format(self.name))

    def put(self, data):
        self.q_in.put(data)

    def _consume(self):
        while True:
            try:
                data = self.q_in.get()

                self.checkQueueWait()

                if data is None:
                    break

                self.targetMethod(data)

            except Exception as e:
                self._logger.error("error procesing queue item for queue {}: {}".format(self.name, repr(e)))
                self._logger.error("stack trace:\n{}".format(traceback.format_exc()))
            finally:
                self.q_in.task_done()

    def checkQueueWait(self):
    	size = self.q_in.qsize()
    	if size > self.warn:
    		self._logger.warning("{} queue wait warning: {}".format(self.name, size))
    	if size > self.dump:
    		self._logger.warning("dumping queue {} ({} items)".format(self.name, size))
    		# clearing this way because q.mutex: q.queue.clear causes the q to block forever on next join call
    		while self.q_in.qsize() > 0:
    			self.q_in.get()
    			self.q_in.task_done()
