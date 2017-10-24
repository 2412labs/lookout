from __future__ import print_function
import sys
# for local development
sys.path.append('common')
import image_utils as iu
from lookout_helper import LookoutHelper, BotoHelper
import boto3
import json
import uuid
from datetime import datetime, timedelta
import time
import os

#note: region is required parameter for iot-data client
REGION = os.environ['AWS_DEFAULT_REGION']
FACES_TABLE = os.environ['FACES_TABLE']
NOTIFY_TABLE = os.environ['NOTIFY_TABLE']
REK_COLLECTION = os.environ['REK_COLLECTION']
IOT_NOTIFY_TOPIC = os.environ['IOT_NOTIFY_TOPIC']
S3_BUCKET = os.environ['S3_BUCKET']

bh = BotoHelper(REGION, 'rekognition', 'dynamodb', 's3')
lh = LookoutHelper(bh, FACES_TABLE, NOTIFY_TABLE)

def handler(event, context):
    eventId = lh.updateEventIdIfTest(event)
    print("processing event {}".format(eventId))

    notify = lh.getDynNotify(NOTIFY_TABLE, eventId)

    if notify is None:
        print("notify record not found for event {}".format(eventId))
        return

    if 'detectedUnsubs' not in notify:
        print("no unsubs for event {}".format(eventId))
        return

    if 'detectedFaceId' in notify:
        print("discarding {} unsubs due to face match".format(len(notify['detectedUnsubs'])))
        return

    # detectedUnsubs is a string, convert to json
    unsubs = [json.loads(u) for u in lh.unmarshal_dynamodb_json(notify['detectedUnsubs'])]

    # find the largest face in the collection
    theUnsub = [max(unsubs, key= lambda x: x['faceArea'])][0]

    # search faces in case this face has already been indexed
    matches = lh.rekSearchFacesByImage(REK_COLLECTION, s3Bucket=S3_BUCKET, s3Key=event['s3Key'])
    if len(matches['FaceMatches']) > 0:
        print("aborting, face {} has already been indexed".format(matches['FaceMatches'][0]['Face']['FaceId']))
        return

    if matches['SearchedFaceConfidence'] < 90:
        print("aborting, face confidence less than 90%")
        return

    # if not found, index the face, create faces record, save face to s3
    imgBytes = lh.s3GetFileBody(S3_BUCKET, event['s3Key'], 'image/jpeg')

    indexFace(event, imgBytes, matches['SearchedFaceBoundingBox'])


def indexFace(event, imgBytes, box):
    npimg = iu.getNpImgFromBytesOrString(imgBytes)
    crop = iu.cropFromBoundingBox(npimg, box)

    if crop is None:
        print("aborting, failed to create crop")
        return

    img = iu.np2bytes(crop)
    faceRecords = lh.rekIndexFace(REK_COLLECTION, img)

    if len(faceRecords) == 0:
        print("aborting, face index failed")
        return

    face = faceRecords[0]
    key = "faces/{}.jpg".format(face['Face']['FaceId'])
    lh.s3PutObject(img, S3_BUCKET, key, 'image/jpeg')

    # create dynamo record
    faceItem = buildDynamoFacesItem(
        face['Face']['FaceId'],
        S3_BUCKET,
        key,
        name="unsub{0}".format(str(uuid.uuid4())[:8])
    )
    lh.dynPutItem(faceItem, FACES_TABLE, 'attribute_not_exists(faceId)')

def buildDynamoFacesItem(faceId, s3Bucket, s3Key, name):
    return {
        'faceId': { 'S': faceId, },
        'rekCollection': { 'S': REK_COLLECTION },
        's3Bucket': { 'S': s3Bucket, },
        's3Key': { 'S': s3Key, },
        'name': { 'S': name, },
        'timestamp': {"N":str(int(time.time()))}
    }
