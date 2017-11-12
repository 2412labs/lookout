from __future__ import print_function
import sys
import os
import boto3
import time
# for local development
sys.path.append('common')
from lookout_helper import LookoutHelper, BotoHelper

#note: region is required parameter for iot-data client
REGION = os.environ['AWS_DEFAULT_REGION']
S3_FACE_PATH = os.environ['S3_FACE_PATH']
FACES_TABLE = os.environ['FACES_TABLE']
NOTIFY_TABLE = os.environ['NOTIFY_TABLE']
REK_COLLECTION = os.environ['REK_COLLECTION']
IOT_NOTIFY_TOPIC = os.environ['IOT_NOTIFY_TOPIC']
S3_BUCKET = os.environ['S3_BUCKET']

bh = BotoHelper(REGION, 's3', 'rekognition', 'dynamodb')
lh = LookoutHelper(bh, FACES_TABLE, NOTIFY_TABLE)

def handler(event, context):
    print("indexing faces from {}/{}".format(S3_BUCKET, S3_FACE_PATH))

    #get known faces from s3 path
    result = bh.s3.list_objects(
        Bucket=S3_BUCKET,
        Prefix=S3_FACE_PATH
    )

    imgsToIndex = []

    for f in result['Contents']:
        key = f['Key']
        if key.endswith(".jpg"):
            name = key.split("/")[-1][:-4]
            if "_" in name:
                name = name.split("_")[0]
            imgsToIndex.append({"name": name, "key": key})

    # index each image

    print("found {} images to index".format(len(imgsToIndex)))
    for i in imgsToIndex:
        faces = lh.rekIndexFace(REK_COLLECTION, bucket=S3_BUCKET, key=i['key'])
        for f in faces:
            print("indexed {} ({}) from {}/{}".format(i['name'], f['Face']['FaceId'], S3_BUCKET, i['key']))

            # updated dynamodb face record
            faceItem = buildDynamoFacesItem(
                f['Face']['FaceId'],
                S3_BUCKET,
                i['key'],
                name=i['name']
            )

            lh.dynPutItem(faceItem, FACES_TABLE, 'attribute_not_exists(faceId)')
            print("updated dynamo record for {}".format(f['Face']['FaceId']))

    return imgsToIndex

def buildDynamoFacesItem(faceId, s3Bucket, s3Key, name):
    return {
        'faceId': { 'S': faceId, },
        'rekCollection': { 'S': REK_COLLECTION },
        's3Bucket': { 'S': s3Bucket, },
        's3Key': { 'S': s3Key, },
        'name': { 'S': name, },
        'timestamp': {"N":str(int(time.time()))}
    }
