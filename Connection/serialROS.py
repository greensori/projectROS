# -*- coding: utf-8 -*-
"""
Created on Sat Nov  3 12:16:20 2018

@author: Green
"""

import serial

def closePort():
    try:
        device = serial.Serial('COM11', 9600)
        print ('connect')
    except:
        device.close()
        device = serial.Serial('COM11', 9600)
        print ('reconnect')
        
def gl():
    print ('enter')
    

if __name__ == '__main__':
    gl()