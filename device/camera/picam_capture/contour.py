import cv2

#TODO include scale with constructor and eliminate scaling concept ... if we needed 2 contours for
# different scales we should just create 2 contour objects to simplify things
class Contour:
    def __init__(self, contour):
        self.contour = contour
        self.area = cv2.contourArea(contour)
        (self.x, self.y, self.w, self.h) = cv2.boundingRect(contour)
        (self.cx, self.cy) = (self.w/2, self.h/2)
        (self.cxframe, self.cyframe) = (self.x+self.cx, self.y+self.cy)

    def drawBoundingRect(self, frame, scale=1):
        box = self.getScaledBoundingBox(scale)
        cv2.rectangle(frame, (box.x, box.y), (box.x + box.w, box.y + box.h), (0, 255, 0), 2)
        cv2.circle(frame, (box.x+box.cx, box.y+box.cy), 3, (0,0,255), -1)
        cv2.putText(frame, str(self.area*scale), (box.x+5, box.y+20), cv2.FONT_HERSHEY_SIMPLEX, .5, (255,255,255),2)

    def cropFrame(self, frame, scale=1):
        box = self.getScaledBoundingBox(scale)
        return frame[box.y:box.y+box.h, box.x:box.x+box.w]

    def getScaledBoundingBox(self, scale=1):
        return ScaledBoundingBox(self.x, self.y, self.w, self.h, scale)

class ScaledBoundingBox:
    def __init__(self, x, y, w, h, scale):
        (self.x,self.y,self.w,self.h,self.cx,self.cy) = (int(x*scale),int(y*scale),int(w*scale),int(h*scale),int((w/2)*scale), int((h/2)*scale))
