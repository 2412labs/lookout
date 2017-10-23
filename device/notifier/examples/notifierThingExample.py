from AwsIotNotifierThing import AwsIotNotifierThing
from datetime import datetime as dt
import argparse
import json
import logging
import time

ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True, help="json config file")
conf = json.load(open(vars(ap.parse_args())["conf"]))

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] [%(name)s] [%(message)s]')
logger = logging.getLogger(__name__)

thing = AwsIotNotifierThing(conf["iotConfig"], conf['notifyTopic'], conf['pollyVoiceId'])

try:
    # this call is blocking
    thing.startThing()
except KeyboardInterrupt:
	logger.info("caught keyboard interrupt, shutting down ...")
finally:
    thing.stopThing()
