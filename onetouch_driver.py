

""" 

    Driver for Ingenious Technology Co Ltd "OneTouch" transparent touchscreen overlay

    Copyright 2011, Joe Koberg <joe@osoft.us>


    Data format is a 3 or 5 byte report sent at 19200 8N1, either
        0xFF 0xFE 0xFE    - Sent upon touch release and sometimes alone on taps/short touches.
        0xFF X0 X1 Y0 Y1  - Where X and Y are little-endian 2-byte integers. Position is the high bits so divide by 64.

    There is significant position noise at the start and end of each raw touch event.    
    We wait for DISCARD_START reports to come in after a touch, then start putting them into a buffer.
    When AVG_COUNT + DISCARD_END have accumulated, we output the average of the earliest AVG_COUNT samples.
    When the touch is released the fifo is cleared. Thus the final DISCARD_END samples are ignored.
    The panel reports at 200Hz.

    There is also an attempt at auto-calibration/scaling. The edges of the panel are intermittent
    and it's best to use a smaller active screen area.
"""


import struct, time
from collections import deque

import serial

from ctypes import *

import win32con
import win32api

user = windll.user32

AVG_COUNT = 6
DISCARD_START = 4
DISCARD_END = 4
SCREEN_H = 1280.0
SCREEN_W = 1024.0



class OneTouch(object):
    def __init__(self, port="COM1"):
        self.portname = port
        self.drag_start_time = None
        self.dragcount = 0
        self.fifo = deque()
        self.moving = 0
        self.cmin = None #(SCREEN_H /2.0, SCREEN_W/2.0)
        self.cmax = None #(SCREEN_H /2.0, SCREEN_W/2.0)
        time.clock() # initialize on windows 
    
    def open(self):
        self.port = serial.Serial(self.portname, baudrate=19200)
        print "port opened"

    def left_click(self):
        #print "click"
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0)

    def mouse_pos(self, x,y):
        #print "    %d, %d"%(x, y)
        user.SetCursorPos(x,y)

    def loop(self):
        print "driver started"
        while 1:
            self.loop_char()
    
    def loop_char(self):
        c = self.port.read(1)
        if c == '\xff':
            now = time.clock()
            delta = 0.0
            if self.drag_start_time:
                delta = now - self.drag_start_time
            x = self.port.read(2)
            if x == '\xfe\xfe':
                if self.dragcount:
                    delta = now - self.drag_start_time
                    print "released %0.3fs later"%(delta,),
                    print "(%0.3f reports/s)"%((self.dragcount)/delta,)
                    if self.moving:
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0)
                    #if self.moving:
                    #    self.left_click()
                self.fifo.clear()
                self.moving = 0
                self.dragcount = 0
                self.drag_start_time = None
                #self.dragcount = 0                
            else:
                if not self.dragcount:
                    print "touch"
                    self.drag_start_time = now
                self.dragcount += 1
                xraw = struct.unpack('<H', x)[0]
                xpos = xraw >> 6
                xflags = xraw & 0x3F
                y = self.port.read(2)
                yraw = struct.unpack('<H', y)[0]
                ypos = yraw >> 6
                yflags = yraw & 0x3F
                if xflags or yflags:
                    print "flags: %x %x"%(xflags, yflags)
                if self.dragcount > DISCARD_START: # delta > FIFO_START
                    self.fifo.append((xpos,ypos))
                    while len(self.fifo) >= (AVG_COUNT+DISCARD_END): #delta > MOTION_START:
                        xtot, ytot = 0.0, 0.0
                        for i in range(AVG_COUNT):
                            xc,yc = self.fifo[i]
                            xtot += xc
                            ytot += yc
                        x = xtot/AVG_COUNT
                        y = ytot/AVG_COUNT
                        if self.cmin:
                            self.cmin = (min(self.cmin[0], x), min(self.cmin[1], y))
                        else:
                            self.cmin = (x,y)
                            
                        if self.cmax:
                            self.cmax = (max(self.cmax[0], x), max(self.cmax[1], y))
                        else:
                            self.cmax = (x+0.1,y+0.1)
                        xoffset, yoffset = self.cmin
                        xscale = SCREEN_H / (self.cmax[0] - self.cmin[0]) 
                        yscale = SCREEN_W / (self.cmax[1] - self.cmin[1])
                        self.fifo.popleft()
                        self.mouse_pos((int((x-xoffset)*xscale)), int(((y-yoffset)*yscale)))
                        if not self.moving:
                            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0)
                        self.moving = 1
                        


if __name__=="__main__":
    t = OneTouch()
    t.open()
    t.loop()

