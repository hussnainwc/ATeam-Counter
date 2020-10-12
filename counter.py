#!/usr/bin/env python
from __future__ import print_function
import time
import datetime
from threading import Thread
import cv2
from threading import Thread
#from picamera.array import PiRGBArray
#from picamera import PiCamera

#----------------------------------CONTROLS------------------------------------#

WINDOW_ON = True       # Set to True displays opencv windows (GUI desktop reqd)
CENTER_LINE_VERT = True # True=Vert False=horiz centerline trigger orientation
INOUT_REVERSE = False   # reverse Enter and Leave orientation
MOVE_LIST_TIMEOUT = 0.5  # wait seconds with no motion then clear movelist

#------------------------------------BUFFER SETTINGS-----------------------------------#
BUFFER_SETTING = 5   # This controls value for x_buf and y_buf for buffer space prior to
                     # crossing line. Avoids counting something turning around or variations
                     # in contour tracking.
if BUFFER_SETTING <= 3:  # Make sure value is Not Too Small
    BUFFER_SETTING = 3

#-------------------------------USB CAMERA-------------------------------# 

WEBCAM_SRC = 0        # default = 0   USB opencv connection number
WEBCAM_WIDTH = 320    # default = 320 USB Webcam Image width
WEBCAM_HEIGHT = 240   # default = 240 USB Webcam Image height
WEBCAM_HFLIP = False  # default = False USB Webcam flip image horizontally
X_CENTER = WEBCAM_WIDTH/2
Y_CENTER = WEBCAM_HEIGHT/2
X_MAX = WEBCAM_WIDTH
Y_MAX = WEBCAM_HEIGHT
X_BUF = int(WEBCAM_WIDTH/BUFFER_SETTING)
Y_BUF = int(WEBCAM_HEIGHT/BUFFER_SETTING)

#---------------------------------------PI CAMERA----------------------------------------#

CAMERA_WIDTH = 320    # default = 320 PiCamera image width can be greater if quad core RPI
CAMERA_HEIGHT = 240   # default = 240 PiCamera image height
CAMERA_HFLIP = False  # True=flip camera image horizontally
CAMERA_VFLIP = False  # True=flip camera image vertically
CAMERA_ROTATION = 0   # Rotate camera image valid values 0, 90, 180, 270
CAMERA_FRAMERATE = 25 # default = 25 lower for USB Web Cam. Try different settings
X_CENTER = CAMERA_WIDTH/2
Y_CENTER = CAMERA_HEIGHT/2
X_MAX = CAMERA_HEIGHT
Y_MAX = CAMERA_WIDTH
X_BUF = int(CAMERA_WIDTH/BUFFER_SETTING)
Y_BUF = int(CAMERA_HEIGHT/BUFFER_SETTING)

#--------------------------------OPENCV SETTING--------------------------------#

MIN_AREA = 700            # excludes all contours less than or equal to this Area
DIFF_WINDOW_ON = False    # Show OpenCV image difference window
THRESH_WINDOW_ON = False  # Show OpenCV image Threshold window
SHOW_CIRCLE = True        # True= show circle False= show rectancle on biggest motion
CIRCLE_SIZE = 5           # diameter of circle for SHOW_CIRCLE
LINE_THICKNESS = 2        # thickness of bounding line in pixels
FONT_SCALE = .5           # size opencv text
THRESHOLD_SENSITIVITY = 25
BLUR_SIZE = 10

#-------------------------------------END OF CONTROLS----------------------------------#

#-----------------------------------------MAIN-----------------------------------------#

#------------------------------------COLOR CONTROLS-----------------------------------#
# Color data for OpenCV lines and text
CV_WHITE = (255, 255, 255)
CV_BLACK = (0, 0, 0)
CV_BLUE = (255, 0, 0)
CV_GREEN = (0, 255, 0)
CV_RED = (0, 0, 255)
COLOR_MO = CV_RED  # color of motion circle or rectangle
COLOR_TEXT = CV_BLUE   # color of openCV text and centerline
TEXT_FONT = cv2.FONT_HERSHEY_SIMPLEX

#------------------------------------PICAMERA MODULE-----------------------------------#
#class PiVideoStream:
#    def __init__(self, resolution=(CAMERA_WIDTH, CAMERA_HEIGHT),
#                 framerate=CAMERA_FRAMERATE, rotation=0,
#                 hflip=False, vflip=False):
#        self.camera = PiCamera()
#        self.camera.resolution = resolution
#        self.camera.rotation = rotation
#        self.camera.framerate = framerate
#        self.camera.hflip = hflip
#        self.camera.vflip = vflip
#        self.rawCapture = PiRGBArray(self.camera, size=resolution)
#        self.stream = self.camera.capture_continuous(self.rawCapture,
#                                                     format="bgr",
#                                                     use_video_port=True)
#        # initialize the frame and the variable used to indicate
#        # if the thread should be stopped
#        self.frame = None
#        self.stopped = False
#
#    def start(self):
#        t = Thread(target=self.update, args=())
#        t.daemon = True
#        t.start()
#        return self
#
#    def update(self):
#        for f in self.stream:
#            # grab the frame from the stream and clear the stream in
#            # preparation for the next frame
#            self.frame = f.array
#            self.rawCapture.truncate(0)
#
#            # if the thread indicator variable is set, stop the thread
#            # and resource camera resources
#            if self.stopped:
#                self.stream.close()
#                self.rawCapture.close()
#                self.camera.close()
#                return
#
#    def read(self):
#        return self.frame
#
#    def stop(self):
#        self.stopped = True
#
#
#------------------------------------WEBCAM MODULE-----------------------------------#
class WebcamVideoStream:
    def __init__(self, CAM_SRC=WEBCAM_SRC, CAM_WIDTH=WEBCAM_WIDTH,
                 CAM_HEIGHT=WEBCAM_HEIGHT):
        self.stream = CAM_SRC
        self.stream = cv2.VideoCapture(CAM_SRC)
        self.stream.set(3, CAM_WIDTH)
        self.stream.set(4, CAM_HEIGHT)
        (self.grabbed, self.frame) = self.stream.read()
        # initialize the variable used to indicate if the thread should
        # be stopped
        self.stopped = False

    def start(self):
        t = Thread(target=self.update, args=())
        t.daemon = True
        t.start()
        return self

    def update(self):
        while True:
            # if the thread indicator variable is set, stop the thread
            if self.stopped:
                return
            # otherwise, read the next frame from the stream
            (self.grabbed, self.frame) = self.stream.read()

    def read(self):
        return self.frame

    def stop(self):
        self.stopped = True

#--------------------------------------------------------------------------------#
def crossed_x_centerline(enter, leave, movelist):
    if len(movelist) > 1:  # Are there two entries
        if (movelist[0] <= X_CENTER and movelist[-1] > X_CENTER + X_BUF):
            leave += 1
            movelist = []
        elif (movelist[0] > X_CENTER and  movelist[-1] < X_CENTER - X_BUF):
            enter += 1
            movelist = []
    return enter, leave, movelist

#---------------------------------------------------------------------------------#
def crossed_y_centerline(enter, leave, movelist):
    if len(movelist) > 1:  # Are there two entries
        if (movelist[0] <= Y_CENTER and movelist[-1] > Y_CENTER + Y_BUF):
            leave += 1
            movelist = []
        elif (movelist[0] > Y_CENTER and  movelist[-1] < Y_CENTER - Y_BUF):
            enter += 1
            movelist = []
    return enter, leave, movelist

#----------------------------------------------------------------------------------#
def track():
    image1 = vs.read()   # initialize image1 (done once)
    grayimage1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
    cx, cy, cw, ch = 0, 0, 0, 0   # initialize contour center variables
    still_scanning = True
    movelist = []
    move_time = time.time()
    enter = 0
    leave = 0
    while still_scanning:
        # initialize variable
        motion_found = False
        biggest_area = MIN_AREA
        image2 = vs.read()  # initialize image2
        if WINDOW_ON:
            if CENTER_LINE_VERT:
                cv2.line(image2, (X_CENTER, 0), (X_CENTER, Y_MAX), COLOR_TEXT, 2)
            else:
                cv2.line(image2, (0, Y_CENTER), (X_MAX, Y_CENTER), COLOR_TEXT, 2)
        grayimage2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)
        # Get differences between the two greyed images
        difference_image = cv2.absdiff(grayimage1, grayimage2)
        # save grayimage2 to grayimage1 ready for next image2
        grayimage1 = grayimage2
        difference_image = cv2.blur(difference_image, (BLUR_SIZE, BLUR_SIZE))
        # Get threshold of difference image based on
        # THRESHOLD_SENSITIVITY variable
        retval, thresholdimage = cv2.threshold(difference_image,
                                               THRESHOLD_SENSITIVITY, 255,
                                               cv2.THRESH_BINARY)
        # Try python2 opencv syntax and fail over to
        # python3 opencv syntax if required
        #try:
        contours, hierarchy = cv2.findContours(thresholdimage,
                                                   cv2.RETR_EXTERNAL,
                                                   cv2.CHAIN_APPROX_SIMPLE)
        #except ValueError:
        #    thresholdimage, contours, hierarchy = cv2.findContours(thresholdimage,
        #                                                           cv2.RETR_EXTERNAL,
        #                                                           cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            total_contours = len(contours)  # Get total number of contours
            for c in contours:              # find contour with biggest area
                found_area = cv2.contourArea(c)  # get area of next contour
                # find the middle of largest bounding rectangle
                if found_area > biggest_area:
                    motion_found = True
                    biggest_area = found_area
                    (x, y, w, h) = cv2.boundingRect(c)
                    cx = int(x + w/2)   # put circle in middle of width
                    cy = int(y + h/2)   # put circle in middle of height
                    cw, ch = w, h
            if motion_found:
                move_timer = time.time() - move_time
                if move_timer >= MOVE_LIST_TIMEOUT:
                    movelist = []
                move_time = time.time()
                old_enter = enter
                old_leave = leave
                if CENTER_LINE_VERT:
                    movelist.append(cx)
                    enter, leave, movelist = crossed_x_centerline(enter, leave, movelist)
                else:
                    movelist.append(cy)
                    enter, leave, movelist = crossed_y_centerline(enter, leave, movelist)
                if not movelist:
                    if enter > old_enter:
                        if INOUT_REVERSE:   # reverse enter leave if required
                            prefix = "leave"
                        else:
                            prefix = "enter"
                    elif leave > old_leave:
                        if INOUT_REVERSE:
                            prefix = enter
                        else:
                            prefix = "leave"
                    else:
                        prefix = "error"
                if WINDOW_ON:
                    # show small circle at motion location
                    if SHOW_CIRCLE and motion_found:
                        cv2.circle(image2, (cx, cy), CIRCLE_SIZE,
                                   COLOR_MO, LINE_THICKNESS)
                    else:
                        cv2.rectangle(image2, (cx, cy), (x+cw, y+ch),
                                      COLOR_MO, LINE_THICKNESS)
        if WINDOW_ON:
            if INOUT_REVERSE:
                img_text = ("LEAVE %i          ENTER %i" % (leave, enter))
            else:
                img_text = ("ENTER %i          LEAVE %i" % (enter, leave))
            cv2.putText(image2, img_text, (35, 15),
                        TEXT_FONT, FONT_SCALE, (COLOR_TEXT), 1)
            cv2.imshow('Window',image2)
            if DIFF_WINDOW_ON:
                cv2.imshow('Difference Image', difference_image)
            if THRESH_WINDOW_ON:
                cv2.imshow('OpenCV Threshold', thresholdimage)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                vs.stop()
                print("End Motion Tracking")
                quit(0)
#------------------------------------WEBCAM MAIN-----------------------------------#
if __name__ == '__main__':
    try:
        while True:
            # Save images to an in-program stream
            # Setup video stream on a processor Thread for faster speed
            vs = WebcamVideoStream().start()
            vs.CAM_SRC = WEBCAM_SRC
            vs.CAM_WIDTH = WEBCAM_WIDTH
            vs.CAM_HEIGHT = WEBCAM_HEIGHT
            time.sleep(4.0)  # Allow WebCam to initialize
            track()
    except KeyboardInterrupt:
        pass
    vs.stop()
    quit(0)
#------------------------------------PI CAMERA MAIN-----------------------------------#
#if __name__ == '__main__':
#    try:
#        while True:
#            # Save images to an in-program stream
#            # Setup video stream on a processor Thread for faster speed
#            vs = PiVideoStream().start()
#            vs.camera.rotation = CAMERA_ROTATION
#            vs.camera.hflip = CAMERA_HFLIP
#            vs.camera.vflip = CAMERA_VFLIP
#            time.sleep(2.0)  # Allow PiCamera to initialize
#            track()
#    except KeyboardInterrupt:
#        pass
#    vs.stop()
#    quit(0)
