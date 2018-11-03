# -*- coding: utf-8 -*-
"""
Created on Sat Nov  3 21:50:35 2018

@author: Green
"""

import cv2

def getCam():
    cap = cv2.VideoCapture(0)
    while(True):
        # Capture frame-by-frame
        ret, frame = cap.read()
    
        # Our operations on the frame come here
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
        # Display the resulting frame
        cv2.imshow('frame',gray)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
    
def gl():
    print ('gl')
    
if __name__ == '__main__':
    gl()
    #getCam()