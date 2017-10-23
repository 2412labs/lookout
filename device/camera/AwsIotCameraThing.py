from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
from util.queue_worker import QueueWorker
from picam_capture.motion_detector import MotionDetector
from threading import Thread
from datetime import datetime as dt
import Queue
import logging
import json
import time
import uuid

class AwsIotCameraThing:
    _logger = logging.getLogger(__name__)

    def __init__(self, iotConfig, sendHelper, deviceTopic, eventTopic):
        (self.mqShadowClient, self.mqClient) = self.createMqttClients(iotConfig)
        self.thingName = iotConfig["thingName"]
        self.deviceTopic = deviceTopic
        self.eventTopic = eventTopic
        self.sh = sendHelper
        self.stopped = False
        self.imageSendQueue = QueueWorker("image_send_queue", self.processImageSendQueue)
        self.mqttQueue = Queue.Queue()
        #(1600,1200), 2.5 (1400,1050)
        self.motionDetector = MotionDetector(
            self.imageSendQueue,
            self.thingName,
            (1600,1200),
            workers=3,
            sensorMode=2,
            fps=5,
            quality=80,
            downscale=2.5)

    def createMqttClients(self, iotConfig):
        mqShadowClient = AWSIoTMQTTShadowClient(iotConfig['thingName'])
        mqShadowClient.configureEndpoint(iotConfig["iotHost"], iotConfig["iotPort"])
        mqShadowClient.configureCredentials(iotConfig["rootCert"], iotConfig["thingPrivateKey"], iotConfig["thingCert"])
        mqShadowClient.configureAutoReconnectBackoffTime(1, 32, 20)
        mqShadowClient.configureConnectDisconnectTimeout(10)
        mqShadowClient.configureMQTTOperationTimeout(10)
        mqShadowClient.connect()
        mqClient = mqShadowClient.getMQTTConnection()
        self._logger.info("mqtt client connected to iot host {}".format(iotConfig["iotHost"]))
        return (mqShadowClient, mqClient)

    def startThing(self):
        # create queues and start worker threads to process them
        self.imageSendQueue.startWorker()
        self.mqClient.subscribe(str(self.deviceTopic), 1, self.mqttSubscribeHandler)
        self.motionDetector.startCapture()

        # enter main loop, use main thread to process mqtt messages
        while not self.stopped:
            time.sleep(0.1)

            while self.mqttQueue.qsize() > 0:
                msg = self.mqttQueue.get(False)
                self._logger.info("rx mq {}".format(msg))

                if msg is None:
                    break

                if msg['cmd'] == "push_frame":
                    self._logger.info("pushing a frame")
                    self.motionDetector.push_test_img(self.motionDetector.current_frame_small)
                if msg['cmd'] == "labels":
                    self._logger.info("got labels: {}".format(msg))

    def stopThing(self):
        self.stopped = True
        self.motionDetector.stopCapture()
        self.imageSendQueue.stopWorker()

    def processImageSendQueue(self, data):
        (b,k) = self.sh.writeImage(data['imageName'], data['imageNp'])

        #todo .. do something with msg
        data["event"]["s3Bucket"] = b
        data["event"]["s3Key"] = k
        data["event"]["thingName"] = self.thingName
        self.mqClient.publish(self.eventTopic, json.dumps(data["event"]), 0)


    def mqttSubscribeHandler(self, client, userdata, message):
        self._logger.debug("queueing mqtt message received from topic {}".format(message.topic))
        if message.topic == self.deviceTopic:
            msg = json.loads(message.payload)
            msg['topic'] = message.topic
            self.mqttQueue.put(msg)
