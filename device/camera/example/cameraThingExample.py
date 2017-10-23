from AwsIotCameraThing import AwsIotCameraThing
from util.s3_helper import S3Helper
from datetime import datetime as dt
import argparse
import json
import logging
import time

# parse arg and read thing configurations from conf file
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True, help="json config file")
conf = json.load(open(vars(ap.parse_args())["conf"]))

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] [%(name)s] [%(message)s]')
logger = logging.getLogger(__name__)

s3 = S3Helper(conf["s3Bucket"], "images", region=conf["iotConfig"]["region"])
thing = AwsIotCameraThing(conf["iotConfig"], s3, conf["deviceTopic"], conf["eventTopic"])

try:
    # this call is blocking
    thing.startThing()
except KeyboardInterrupt:
	logger.info("caught keyboard interrupt, shutting down ...")
finally:
    thing.stopThing()
