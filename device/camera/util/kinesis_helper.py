import boto3
import logging
import json

class KinesisHelper:
    _logger = logging.getLogger(__name__)

    def __init__(self, stream, partition, region=None, client=None):
        if client is None:
            if region is None:
                raise Exception("must provide existing boto3 kinesis client or specify a region to create client")
            self.client = boto3.client("kinesis", region_name=region)
        else:
            self.client = client
        self.stream = stream
        self.partition = partition

    def write(self, payload):
        self._logger.debug("writing {} bytes to stream {} partition {}".format(len(payload), self.stream, self.partition))
        if type(payload) is dict:
            payload = json.dumps(payload)
        self.client.put_record(StreamName=self.stream, Data=payload, PartitionKey=self.partition)
        self._logger.debug("completed record {} bytes to stream {} partition {}".format(len(payload), self.stream, self.partition))
