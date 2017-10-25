from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
import boto3
import os
from datetime import datetime as dt
import time
import json
import io
import traceback
import simpleaudio as sa
import logging
if sys.version_info[0] >= 3:
    import queue
else:
    import Queue as queue
import uuid

class AwsIotNotifierThing:
    _logger = logging.getLogger(__name__)
    DEFAULT_NAME = "Someone"

    def __init__(self, iotConfig, notifyTopic, pollyVoiceId):
        (this_dir, this_filename) = os.path.split(__file__)
        self.chime = sa.WaveObject.from_wave_file("{}/audio/chime.wav".format(this_dir))
        (self.mqShadowClient, self.mqClient) = self.createMqttClients(iotConfig)
        self.pollyPhrases = {}
        self.audioHandle = None
        self.notifyTopic = notifyTopic
        self.pollyVoiceId = pollyVoiceId
        self.polly = polly = boto3.client('polly', region_name=iotConfig["region"])
        self.notifications = {}
        self.mqttQueue = queue.Queue()
        self.stopped = False

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

    def mainLoop(self):
        try:
            while not self.stopped:
                time.sleep(.1)
                while self.mqttQueue.qsize() > 0:
                    payload = self.mqttQueue.get(False)
                    if payload is None:
                        break
                    self.handleNotification(payload)
        except Exception as e:
            self._logger.error(repr(e))

    def startThing(self):
        self.mqClient.subscribe(self.notifyTopic, 1, self.notifyHandler)
        self.mainLoop()

    def stopThing(self):
        self.stopped = True

    def notifyHandler(self, client, userdata, message):
        try:
            payload = json.loads(message.payload.decode('utf-8'))
            self._logger.debug("received {}".format(payload))
            self.mqttQueue.put(payload)
        except Exception as e:
            self._logger.error(repr(e))

    def handleNotification(self, payload):
        try:
            eventId = payload['eventId']
            has_person = payload['has_person']
            name = None
            car = "Vehicle" if payload['has_car']==True else None

            if 'detectedFace' in payload:
                name = payload['detectedFace']['name']

            if eventId not in self.notifications:
                notify = {
                    'eventId': eventId,
                    'created': time.time(),
                    'name': name,
                    'car': car,
                    'has_person': has_person,
                    'event': payload
                }
                self.notifications[eventId] = notify
                self.announce(chime=True, name=name, car=car,  notify=notify)
            else:
                # after the initial event, if the name was none but now exists
                # announce the name only
                notify = self.notifications[eventId]
                if notify['name'] is None and name:
                    notify['name'] = name
                    self.notifications[eventId] = notify
                    self.announce(chime=False, name=name, notify=notify)
        except Exception as e:
            self._logger.error(repr(e))

    def announce(self, chime, notify, name=None, car=None):
        self._logger.info("announcing chime={}, name={}, event={}".format(chime, name, json.dumps(notify)))
        wav = None

        if chime:
            self.audioHandle = self.chime.play()
            self.audioHandle.wait_done()
        if name is not None:
            wav = self.getPhraseWaveObj(name, self.createNamePhrase(name))
        elif car is not None:
            wav = self.getPhraseWaveObj(car, self.createCarPhrase(car))
        else:
            name = self.DEFAULT_NAME
            wav = self.getPhraseWaveObj(self.DEFAULT_NAME, self.createNamePhrase(self.DEFAULT_NAME))

        if wav is not None:
            self.audioHandle = wav.play()
            self.audioHandle.wait_done()

    def createCarPhrase(self, car):
        return "I see a {}".format(car)

    def createNamePhrase(self, name):
        return "{} is here.".format(name)

    def getPhraseWaveObj(self, key, phrase):
        if key not in self.pollyPhrases:
            self.pollyPhrases[key] =  sa.WaveObject(self.getPollyPhrase(phrase), 1, 2, 16000)
        return self.pollyPhrases[key]

    def getPollyPhrase(self, phrase):
        response = self.polly.synthesize_speech(
            OutputFormat='pcm',
            SampleRate='16000',
            Text=phrase,
            VoiceId=self.pollyVoiceId
        )
        return response['AudioStream'].read()
