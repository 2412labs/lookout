import math

class MotionPath:
    def __init__(self, cnt):
        self.cnt = cnt
        self.x = cnt.cxframe
        self.y = cnt.cyframe
        self.score = 1
        self.dx = 0
        self.dy = 0

    def contourMatchesPath(self, cnt):
        dist = math.hypot(cnt.cxframe - self.cnt.cxframe, cnt.cyframe - self.cnt.cyframe)
        if dist < 40:
            self.cnt = cnt
            self.dx = self.cnt.cxframe - self.x
            self.dy = self.cnt.cyframe - self.y
            self.score += 1
            return True
        else:
            self.score -= 1
            return False

    def getDirection(self):
        d1 = None
        d2 = None
        if self.dy < -10:
            d1 = 'N'
        elif self.dy > 10:
            d1 = 'S'
        if self.dx < -10:
            d2 = 'W'
        elif self.dx > 10:
            d2 = 'E'
        if d1 and d2:
            return "{}{}".format(d1,d2)
        if d1:
            return d1 
        return d2

    @property
    def ismotion(self):
        if self.score > 5 and (abs(self.dx) > 30 or abs(self.dy) > 30):
            return True
        return False
