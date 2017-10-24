import os
import cv2
import numpy as np
import uuid
import base64
import binascii
import json
import logging

_logger = logging.getLogger(__name__)

def getNpImgFromBytesOrString(data):
	nparr = np.fromstring(data, np.uint8)
	return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

def cropFromBoundingBox(npimg, box):
	(h,w) = npimg.shape[:2]
	crop = getCrop(box, npimg, h, w)
	_logger.debug("crop shape {}".format(crop.shape))
	if len(crop) > 0:
		return crop
	return None

def cropFromFaceDetails(npimg, faceDetails):
	(h,w) = npimg.shape[:2]
	crops = []
	for f in faceDetails:
		if f['Confidence'] < 90:
			continue
		crop = getCrop(f['BoundingBox'], npimg, h, w)
		_logger.debug("crop shape {}".format(crop.shape))
		if len(crop) > 0:
			crops.append(crop)
	return crops

def np2b64(npimg):
	return base64.encodestring(cv2.imencode('.jpeg',npimg)[1]).rstrip()

def np2bytes(npimg):
	return cv2.imencode('.jpeg',npimg)[1].tobytes()

def getCrop(box, npimg, h, w):
	left = int(float(box['Left']) * w)
	top = int(float(box['Top']) * h)
	boxw = int(float(box['Width']) * w)
	boxh = int(float(box['Height']) * h)

	_logger.debug("cropping to x {0}+{1}, y {2}+{3}".format(left, boxw, top, boxh))

	if boxw < 80 or boxh < 80:
		_logger.debug("increasing crop to 80x80")
		increaseBy = 81-boxw
		boxw = boxw + increaseBy
		boxh = boxh + increaseBy
		left = left-int(increaseBy/2)
		top = top-int(increaseBy/2)
		_logger.debug("cropping to x {0}+{1}, y {2}+{3}".format(left, boxw, top, boxh))

	if (left < 0) or (left+boxw > w) or (top < 0) or (top+boxh > h):
		_logger.debug("crop is out of bounds")
		return []

	return npimg[top:top+boxh, left:left+boxw]
