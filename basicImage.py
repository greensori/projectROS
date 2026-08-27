  # -*- coding: utf-8 -*-
"""
Created on Tue Jul 23 16:43:46 2019

@author: Green
"""

#making background image
#types. background, tiles, character, woods

import cv2
import pygame
import numpy as np

pygame.init()
pygame.font.init()

pRad = 0 #this is pointer, pitch, yaw, roll values
yRad = 0
rRad = 0

myfont = pygame.font.SysFont('Comic Sans MS', 30)

def nothing(x):
    pass

def buttonTemp(x):
    pass

def masking(img):
    rows, cols, channels = img.shape
    roi = img[0:rows, 0:cols]
    img2gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, mask = cv2.threshold(img2gray, 10, 255, cv2.THRESH_BINARY)
    mask_inv = cv2.bitwise_not(mask)
    img1_fg = cv2.bitwise_and(img, img, mask=mask)
    img2_bg = cv2.bitwise_and(roi, roi, mask=mask_inv)
    dst = cv2.add(img1_fg, img2_bg)
    return rows, cols, dst

cv2.namedWindow('image')
cv2.createTrackbar('W', 'image', 0, 100, nothing)
#w = cv2.getTrackbarPos('W','image')

filepath = "C:\workSpace\sampleImg\"

img = cv2.imread('{}sample1.png'.format(filepath))
img_build = cv2.imread('C:\workSpace\sampleImg\sample_wall.png')
img_build = cv2.cvtColor(img_build, cv2.COLOR_BGR2GRAY)
print (img_build.shape)

img_rad0 = cv2.imread('C:\workSpace\sampleImg\sm_0.png')
img_rad90 = cv2.imread('C:\workSpace\sampleImg\sm_90.png')
img_rad180 = cv2.imread('C:\workSpace\sampleImg\sm_180.png')
img_rad270 = cv2.imread('C:\workSpace\sampleImg\sm_270.png')

#img_build = cv2.cvtColor(img_build, cv2.COLOR_BGR2RGB)
#img_build = cv2.GaussianBlur(img_build, (5, 5), 0)
#img_build = cv2.Canny(img_build, 10, 70)

#row, col, new_dst = masking(img_build)

#img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
img_1 = cv2.GaussianBlur(img, (5, 5), -2)
img_2 = cv2.GaussianBlur(img, (5, 5), 10)
img_1 = cv2.Canny(img_1, 5, 70)
img_2 = cv2.Canny(img_2, 80, 70)
print (img_1.shape)
ret, img_1 = cv2.threshold(img_1, 70, 255, cv2.THRESH_BINARY_INV)
ret, img_2 = cv2.threshold(img_2, 70, 255, cv2.THRESH_BINARY_INV)
#img_1[0:rows, 0:cols] = new_dst


print (ret)

emptyImage = np.zeros(shape = [1024, 1024, 3], dtype = np.uint8)

GaussianPointer = 0
cannyP = 0

def perspectiveChanger():
    rows, cols = img_build.shape
    img_1[0:rows, 0:cols] = img_build
    pts1 = np.float32([[0,0], [200,0], [0,200], [200,200]])
    pts2 = np.float32([[50,50], [150,50], [0,150], [100,100]])
    M = cv2.getPerspectiveTransform(pts1, pts2)
    dst = cv2.warpPerspective(img_build, M, (200, 200))
    print (dst.shape)    
    cv2.imshow('er', dst) 
    return




while(1):
    cv2.imshow('filter1', img_1)
    #cv2.imshow('filter2', img_2)
    k = cv2.waitKey(0)
    if k == 27:
        break
    elif k == 119:
        print ('w')
        print (GaussianPointer)
        GaussianPointer = (GaussianPointer + 1)
        img_1 = cv2.GaussianBlur(img, (5, 5), GaussianPointer)
        img_1 = cv2.Canny(img_1, 5, 70)
        ret, img_1 = cv2.threshold(img_1, 70, 255, cv2.THRESH_BINARY_INV)
        cv2.imshow('filter1', img_1)
    elif k == 115:
        print ('s')
        GaussianPointer = (GaussianPointer - 1)
        print (GaussianPointer)
        img_1 = cv2.GaussianBlur(img, (5, 5), GaussianPointer)
        img_1 = cv2.Canny(img_1, 5, 70)
        ret, img_1 = cv2.threshold(img_1, 70, 255, cv2.THRESH_BINARY_INV)
        cv2.imshow('filter1', img_1)
    elif k == 97:
        print ('a')
        print ('rRad : %d' %(rRad))

        rRad = (rRad + 1)
        img_1 = cv2.GaussianBlur(img, (5, 5), 0)
        img_1 = cv2.Canny(img_1, 1, 70)
        ret, img_1 = cv2.threshold(img_1, 70, 255, cv2.THRESH_BINARY_INV)
        cv2.imshow('filter1', img_1)
        
        '''
        cannyP = (cannyP + 1)
        print (cannyP)
        img_1 = cv2.GaussianBlur(img, (5, 5), GaussianPointer)
        img_1 = cv2.Canny(img_1, 1, cannyP)
        ret, img_1 = cv2.threshold(img_1, 70, 255, cv2.THRESH_BINARY_INV)
        cv2.imshow('filter1', img_1)
        '''
    elif k == 100:
        print ('d')
        cannyP = (cannyP - 1)
        print (cannyP)
        img_1 = cv2.GaussianBlur(img, (5, 5), GaussianPointer)
        img_1 = cv2.Canny(img_1, 1, cannyP)
        ret, img_1 = cv2.threshold(img_1, 70, 255, cv2.THRESH_BINARY_INV)
        cv2.imshow('filter1', img_1)
    else:
        img_1[200:400, 200:400] = img_build
        cv2.imshow('filter1', img_1)
        #cv2.imshow('filter2', img_2)
        print ('renew')


cv2.destroyAllWindows()    