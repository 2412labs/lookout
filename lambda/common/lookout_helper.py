from datetime import datetime, timedelta
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
import time
import logging
import json
import uuid

class BotoHelper:
	_logger = logging.getLogger(__name__)

	def __init__(self, region_name, *clients):
		self.region_name = region_name
		self.createClient(*clients)

	def createClient(self, *clients):
		for c in clients:
			self._logger.info("creating {} boto3 client in region {}".format(c, self.region_name))
			if c == 'iot-data':
				self.__dict__[c] = boto3.client(c, region_name=self.region_name)
			else:
				self.__dict__[c] = boto3.client(c)

class LookoutHelper:
	def __init__(self, bh, facesTable, notifyTable):
		self.bh = bh
		self.facesTable = facesTable
		self.notifyTable = notifyTable

	def iotPublish(self, topic, payload, qos=1):
		self.bh.__dict__['iot-data'].publish(topic=topic, payload=payload, qos=qos)

	###########################
	# rekognition helpers

	def hasPersonLabels(self, labels):
	    matches = [l for l in labels if l in ('Human', 'People', 'Person')]
	    return len(matches) > 0

	def hasVehicleLabels(self, labels):
	    matches = [l for l in labels if l in ('Car', 'Automobile', 'Vehicle', 'Suv', 'Van', 'Truck', 'Motorcycle')]
	    return len(matches) > 0

	def rekGetLabels(self, bucket, key, confidence=90):
		response = self.bh.rekognition.detect_labels(
		    Image={
		        'S3Object': {
		            'Bucket': bucket,
		            'Name': key
		        }
		    },
		    MaxLabels=15,
		    MinConfidence=confidence
		)
		return [l['Name'] for l in response['Labels']]

	def rekGetFaceDetails(self, imgBytes = None, bucket=None, key=None):
		if imgBytes != None:
			return self._rekGetFaceDetails({ 'Bytes': imgBytes })
		else:
			return self._rekGetFaceDetails({ 'S3Object': { 'Bucket': bucket, 'Name': key } })

	def _rekGetFaceDetails(self, request):
		return self.bh.rekognition.detect_faces(Image=request)['FaceDetails']

	def rekSearchFacesByImage(self, collectionId, s3Bucket=None, s3Key=None):
		try:
			return self.bh.rekognition.search_faces_by_image(
				CollectionId=collectionId,
				Image={
			        'S3Object': {
			            'Bucket': s3Bucket,
			            'Name': s3Key
			        }
				},
				MaxFaces=1,
				FaceMatchThreshold=80
			)
		except ClientError as e:
			if e.response['Error']['Code'] == 'ResourceNotFoundException':
				print("rekognition collection {} not found, creating".format(collectionId))
				self.rekCreateCollection(collectionId)
				return None
			elif e.response['Error']['Code'] == 'InvalidParameterException':
				return None
			else:

				raise e

	def rekIndexFace(self, collectionId, imgData=None, bucket=None, key=None):
		if imgData is None:
			return self.bh.rekognition.index_faces(
				CollectionId=collectionId,
				Image={
					'S3Object': {
						'Bucket': bucket,
						'Name': key
					}
				}
			)['FaceRecords']

		return self.bh.rekognition.index_faces(
			CollectionId=collectionId,
			Image={
				'Bytes': imgData
			}
		)['FaceRecords']

	def rekCreateCollection(self, collectionId):
		response = self.bh.rekognition.create_collection(
			CollectionId=collectionId
		)
		print("created rekognition collection {}".format(collectionId))

	def rekRecreateCollection(self, collectionId):
		try:
			response = self.bh.rekognition.delete_collection(
				CollectionId=collectionId
			)
			print("deleted rekognition collection {}".format(collectionId))
		except:
			return
		self.rekCreateCollection(collectionId)


	###########################
	# s3 helpers

	def s3GetFileBody(self, bucket, key, contentType):
		response=self.bh.s3.get_object(
			Bucket=bucket,
			Key=key,
			ResponseContentType=contentType
		)
		return response['Body'].read()


	def s3PutObject(self, data, bucket, key, contentType):
		response=self.bh.s3.put_object(
			Body=data,
			Bucket=bucket,
			Key=key,
			ContentType=contentType
		)



	###########################
	# general purpose helpers

	def jprint(self, data):
	        print(json.dumps(data, indent=2, sort_keys=True))

	def updateEventIdIfTest(self, event):
	        if event['eventId'] == 't-generate':
	                event['eventId'] = "t-{0}".format(str(uuid.uuid4())[:8])
	        return event['eventId']




	###########################
	# dynamodb helpers

	def dynPutItem(self, item, table, condition):
		try:
			dbresponse = self.bh.dynamodb.put_item(
				Item=item,
				TableName=table,
				ConditionExpression=condition
			)
		except ClientError as e:
			if e.response['Error']['Code'] == "ConditionalCheckFailedException":
				return None
			else:
				raise

	def getDynNotify(self, table, eventId):
	    result = self.bh.dynamodb.get_item(
	        TableName=table,
	        Key={
	            'id': { 'S': eventId }
	        },
	        ConsistentRead=True
	    )

	    if 'Item' in result:
	        return result['Item']
	    else:
	        return None

	def dynGetFacesById(self, faceIds):
	    response = self.bh.dynamodb.batch_get_item(
	        RequestItems={
	            self.facesTable: {
	                'Keys': [{'faceId': {'S': f}} for f in faceIds],
	                'ProjectionExpression': 'faceId,#name',
	                'ExpressionAttributeNames': {'#name': 'name'}
	            }
	    })

	    return [self.unmarshal_dynamodb_json(f) for f in response['Responses'][self.facesTable]]


	def updateNotifyUnsub(self, eventId, unsub):
	    response = self.bh.dynamodb.update_item(
	        TableName=self.notifyTable,
	        Key={ 'id': { 'S': eventId } },
	        UpdateExpression="SET detectedUnsubs = list_append(if_not_exists(detectedUnsubs, :empty_list), :unsub)",
	        ExpressionAttributeValues={ ":unsub":{"L": [{"S": json.dumps(unsub)}] }, ":empty_list": {"L": []} },
	        ReturnValues="ALL_NEW"
	    )
	    return response['Attributes']

	def updateDynNotify(self, eventId, hasPerson=False, hasCar=False, faceId=None, unsub=None, event=None):
		try:
			expression = "SET expires = :expires"
			expireOn = datetime.now() + timedelta(days=7)
			seconds = int((expireOn-datetime(1970,1,1)).total_seconds())
			expressionValues = { ":expires": {"N":str(seconds)} }
			condition = None

			if hasPerson or hasCar:
				expression = expression + ", has_person = :has_person"
				expressionValues[':has_person'] = {"BOOL":hasPerson}
				expression = expression + ", has_car = :has_car"
				expressionValues[':has_car'] = {"BOOL":hasCar}

				if event:
					expression = expression + ", event = :event"
					expressionValues[':event'] = {"S":json.dumps(event)}

			if faceId != None:
				expression = expression + ", detectedFaceId = :faceId"
				expressionValues[':faceId'] = {"S": faceId}
				condition = "attribute_not_exists(detectedFaceId)"

			if hasPerson or hasCar:
				condition = "attribute_not_exists(id)"

			response = self.bh.dynamodb.update_item(
				TableName=self.notifyTable,
				Key={ 'id': { 'S': eventId } },
				UpdateExpression=expression,
				ExpressionAttributeValues=expressionValues,
				ConditionExpression=condition,
				ReturnValues="ALL_NEW"
			)

			return response['Attributes']

		except ClientError as e:
			if e.response['Error']['Code'] == "ConditionalCheckFailedException":
				return None
			raise

	def unmarshal_dynamodb_json(self, node):
	        data = dict({})
	        data['M'] = node
	        return self.unmarshal_value(data)


	def unmarshal_value(self, node):
	        if type(node) is not dict:
	            return node

	        for key, value in node.items():
	            key = key.lower()
	            if key == 'bool':
	                return value
	            if key == 'null':
	                return None
	            if key == 's':
	                return value
	            if key == 'n':
	                if '.' in str(value):
	                    return float(value)
	                return int(value)
	            if key in ['m', 'l']:
	                if key == 'm':
	                    data = {}
	                    for key1, value1 in value.items():
	                        if key1.lower() == 'l':
	                            data = [self.unmarshal_value(n) for n in value1]
	                        else:
	                            if type(value1) is not dict:
	                                return self.unmarshal_value(value)
	                            data[key1] = self.unmarshal_value(value1)
	                    return data
	                data = []
	                for item in value:
	                    data.append(self.unmarshal_value(item))
	                return data
