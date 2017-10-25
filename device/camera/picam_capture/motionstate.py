from .motion_path import MotionPath
import time
import datetime
import math
import json
import logging

class MotionState:
	_logger = logging.getLogger(__name__)

	def __init__(self, camera_id, minMotionFrames, activeTimeout, inactiveTimeout):
		self.reset()
		self.cam = camera_id
		self.sessionName = None
		self.minMotionFrames = minMotionFrames
		self.activeTimeout = activeTimeout
		self.inactiveTimeout = inactiveTimeout

	def reset(self):
		self.lastMotionTime = None
		self.frameCount = 0
		self.isMotionActive = False
		self.paths = []
		self.maxdist = 0
		self.sendStream = True
		self.sendStreamCount = 0

	def setMotion(self):
		self.lastMotionTime = datetime.datetime.now()
		self.sessionName = "{0}-{1}".format(self.cam, time.strftime("%Y%m%d-%H%M%S"))
		self.isMotionActive = True
		self._logger.info("({}) started motion state".format(self.sessionName))

	def processNonMotionFrame(self):
		if self.lastMotionTime is not None:
			current = datetime.datetime.now()
			if self.isMotionActive == False:
				if self.lastMotionTime is not None and self.frameCount > 0:
					if (current - self.lastMotionTime).seconds > self.inactiveTimeout:
						#for n,p in enumerate(self.paths):
						#	print "path {0} count {1}, dx {2} dy {3}".format(str(n), str(p.score), p.dx, p.dy)
						self.motionStateReset()
			else:
				if (current - self.lastMotionTime).seconds > self.activeTimeout:
					self._logger.info("({}) ended motion state, frames {}, stream count {}, direction {}".format(self.sessionName, self.frameCount, self.sendStreamCount, self.getDirection()))
					self.reset()
					return True
		return False

	def motionStateReset(self):
		self.reset()

	def processMotionFrame(self, contour):
		self.frameCount += 1

		self.attachToPath(contour)

		# if all paths become inactive during a motion state, return before
		# setting the last motion time to help trigger inactive motion state
		hasActivePaths = any(p.ismotion for p in self.paths)
		if self.isMotionActive and hasActivePaths == False:
			return False

		self.lastMotionTime = datetime.datetime.now()

		# bail out if getting too many frames without detecting motion state
		if self.isMotionActive == False and self.frameCount > self.minMotionFrames*3:
			self.motionStateReset()
			return False


		if self.isMotionActive == False and self.frameCount > self.minMotionFrames:
			if any(p.ismotion for p in self.paths):
				self.setMotion()
				return True
		return False

	def getDirection(self):
		motionPaths = [p for p in self.paths if p.ismotion]
		if len(motionPaths) > 0:
			thePath = [max(motionPaths, key= lambda x: x.score)][0]
			return { 'direction' : thePath.getDirection(), 'dx': thePath.dx, 'dy': thePath.dy }
		return None

	def attachToPath(self, contour):
		if len(self.paths) is 0:
			self.paths.append(MotionPath(contour))
			return
		else:
			# attach contour to an existing path if matches
			matched = False
			for p in self.paths:
				matched = p.contourMatchesPath(contour)

			# create a new path if contour matches no existing paths
			if not matched:
				self.paths.append(MotionPath(contour))
