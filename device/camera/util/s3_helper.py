import boto3
import logging
import json
import io

class S3Helper:
    _logger = logging.getLogger(__name__)

    def __init__(self, bucket, path=None, region=None, client=None):
        if client is None:
            if region is None:
                raise Exception("must provide existing s3 kinesis client or specify a region to create client")
            self.client = boto3.client("s3", region_name=region)
        else:
            self.client = client
        self.bucket = bucket
        self.path = path

    def writeImage(self, name, data):
        stream = io.BytesIO(data)
        stream.seek(0) 
        if self.path != None:
            name = "{}/{}".format(self.path, name)
        self._logger.debug("writing {} bytes to key {}".format(len(data), name)) 
        self.client.upload_fileobj(stream, self.bucket, name)
        return (self.bucket, name)
