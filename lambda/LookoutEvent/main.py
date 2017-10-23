from __future__ import print_function
import sys
import os
# for local development
sys.path.append('common')
from lookout_helper import LookoutHelper, BotoHelper
import base64
import json
import binascii
import uuid
import time
from datetime import datetime, timedelta
from decimal import Decimal

#note: region is required parameter for iot-data client
REGION = os.environ['AWS_DEFAULT_REGION']
FACES_TABLE = os.environ['FACES_TABLE']
NOTIFY_TABLE = os.environ['NOTIFY_TABLE']
REK_COLLECTION = os.environ['REK_COLLECTION']
IOT_NOTIFY_TOPIC = os.environ['IOT_NOTIFY_TOPIC']
S3_BUCKET = os.environ['S3_BUCKET']

bh = BotoHelper(REGION, 's3', 'rekognition', 'dynamodb', 'iot-data')
lh = LookoutHelper(bh, FACES_TABLE, NOTIFY_TABLE)

def handler(event, context):
    eventId = lh.updateEventIdIfTest(event)
    print("processing {}/{} for event {}".format(S3_BUCKET, event['s3Key'], eventId))

    notify = lh.getDynNotify(NOTIFY_TABLE, eventId)

    if not canUpdate(notify):
        return

    if notify is None:
        labels = lh.rekGetLabels(S3_BUCKET, event['s3Key'])
        person = lh.hasPersonLabels(labels)
        car = lh.hasVehicleLabels(labels)
        if person or car:
            print("labels found: {}".format(labels))
            notify = notifyLabels(event, labels, person, car)

    if notify is not None and notify['has_person']['BOOL'] == True:
        notify = detectFaces(event)

def detectFaces(event):
    # this only uses the largest face in the image
    (faceBounds, faceMatches) = searchFaces(event)

    if not faceBounds:
        print("aborting, no face detected in image")
        return

    # notify and exit if a face match was found
    if len(faceMatches) > 0:
        theFace = getFaceRecord(faceMatches)
        if theFace is None:
            print("error, faces found in collection do not have dbynamodb record: {}".format(faceMatches))
            return
        print("face found: {}".format(theFace))
        return notifyFaces(event, theFace)

    # add the detected face to the unsub list for this event
    print("adding unsub to detected unsubs")
    unsub = {
      "bucket": S3_BUCKET,
      "eventImageKey": event['s3Key'],
      "faceBounds": faceBounds,
      "faceArea": (faceBounds['Top']+faceBounds['Height']) * (faceBounds['Left']+faceBounds['Width'])
    }
    return lh.updateNotifyUnsub(event['eventId'], unsub)

def searchFaces(event):
	result = lh.rekSearchFacesByImage(REK_COLLECTION, s3Bucket=S3_BUCKET, s3Key=event['s3Key'])
	if result is None:
		return (None,None)
	return (result['SearchedFaceBoundingBox'], result['FaceMatches'])

def getFaceRecord(faceMatches):
    faces = lh.dynGetFacesById([f['Face']['FaceId'] for f in faceMatches])
    if len(faces) == 0:
        return None
    # if more than 1 matched they should be the same person
    return faces[0]

def notifyFaces(event, theFace):
    notify = lh.updateDynNotify(eventId=event['eventId'], faceId=theFace['faceId'], event=event)
    if notify != None:
        print("notifying detection of {} to {}".format(theFace['name'], IOT_NOTIFY_TOPIC))
        event['detectedFace'] = theFace
        lh.iotPublish(IOT_NOTIFY_TOPIC, json.dumps(event))
    return notify

def notifyLabels(event, labels, person, car):
    notify = lh.updateDynNotify(eventId=event['eventId'], hasPerson=person, hasCar=car, event=event)
    if notify != None:
        event['labels'] = labels
        event['has_person'] = person
        event['has_car'] = car
        print("publishing label event to {} for event {}".format(IOT_NOTIFY_TOPIC, event['eventId']))
        lh.iotPublish(topic=IOT_NOTIFY_TOPIC, payload=json.dumps(event))
    return notify

def canUpdate(notify):
    if notify != None:
        if notify['has_person']['BOOL'] == False:
            print("can't update notificaiton, labels exist and has_person is false")
            return False
        if 'detectedFaceId' in notify:
            print("can't update notification, detectedFaceId exists")
            return False
    return True
