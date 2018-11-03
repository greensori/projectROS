# -*- coding: utf-8 -*-
"""
Created on Mon Oct 22 23:25:38 2018

@author: Green

Controller for using in jetson tx1 with cti carrier

uart0 /dev/ttyS0

uart1 /dev/ttyTHS2



Port - ttyS0 (UART0)
Stat - open
I/O - 

Port - ttyTHS2 (UART1)
stat - open

Port - i2c (master)
stat - Open Drain
input(0-7) : 0x00
input(8-15) : 0x01

port - cap(CMOS)
stat - camera
resolution

port - GPIO (H13)
stat - gpio_pq4_pi4

port - GPIO (G14)
stat - can_gpio2_paa2

port - GPIO (A22)
stat - gpio_mdm7_py6

port -GPIO (A23)
stat - gpio_mdm1_py0


i2c registers

0x00 = Input 0 – 7  Status Register (Not all inputs/outputs are implemented on all carriers see the GPIO Reference Table)
0x01 = Input  8 – 15 Status Register (Not all inputs/outputs are implemented on all carriers see the GPIO Reference Table)
0x02 = Output 0-7 Register – Default = 0xFF, 0 = GND, 1 = 3.3V HIGH (only valid if I/O set to an output in register 0x06)
0x03 = Output 8-15 Register – Default = 0xFF, 0 = GND, 1 = 3.3V HIGH (only valid if I/O set to an output in register 0x06)
0x06 = I/O Mode 0-7 set register – Default = 0xFF (all inputs), (0 = output, 1 = input)
0x07 = I/O Mode 8-15 set register – Default = 0xFF (all inputs), (0 = output, 1 = input)

#add this line


"""

import serial
import time

import cv2

import tkinter as tk
from PIL import ImageGrab, Image, ImageTk

portName = ['portName', 'ttyS0 (UART0)', 'ttyTHS2 (UART1)', 'i2c (master)', 'USB 3.0 (CMOS)', 'USB OTG', 'GPIO (H13)', 'GPIO (G14)'
            , 'GPIO (A22)', 'GPIO (A23)']

initStat = ['status', 'connect', 'connect', 'openDrain', 'connect', 'notin', 'OUTPUT', 'OUTPUT', 'OUTPUT', 'OUTPUT']

initBuffer = ['bufferSize', '0', '0', '0', '0', '0', '0', '0', '0', '0']

c0Label = []
c1Label = []
c2Label = []

#img = Image.open('temp.jpg')

def closePort():
    try:
        device = serial.Serial('COM11', 9600)
        print ('connect')
    except:
        device.close()
        device = serial.Serial('COM11', 9600)
        print ('reconnect')


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

def serialConnect():
    print ('you click serialConnect butotn')
    return

def serialDisconnect():
    return

def serialClose():
    return


def autoupdate():
    return

App = tk.Tk()
App.title('myController')
App.resizable(width = True, height = False)
App.geometry('800x550+500+250')

#making menu
topmenu = tk.Menu(App)
filemenu = tk.Menu(topmenu, tearoff = 0)
filemenu.add_command(label = 'connect', command = serialConnect)
filemenu.add_command(label = 'disconnect', command = serialDisconnect)
#filemenu.add_seperator()
filemenu.add_command(label = 'close', command = serialClose)
topmenu.add_cascade(label = 'portManager', menu = filemenu)

topmenu.add_cascade(label = 'ImageDetect', menu = filemenu)
App.config(menu = topmenu)
Entry1 = tk.Entry(App, width = 12)
Entry1.insert(0, '11222')
Entry1.grid(row = 0, column = 99)

#making colum0label 

myLF1 = tk.LabelFrame(App, text = 'yukiho', padx = 2, pady = 2, labelanchor = 'n')
myLF1.grid(row = 0, column = 0, padx = 15, pady = 5)
#myLF1.place(x = 10, y = 10)
count = 0
for i in portName:
    print (count)
    c0Label.append(int(count))
    c0Label[count]= tk.Label(myLF1, text = i, padx = 5, pady = 5)
    c0Label[count].grid(row = count, column = 0)
    count = count + 1
count = 0
for i in initStat:
    c1Label.append(int(count))
    c1Label[count] = tk.Label(myLF1, text = i, padx = 5, pady = 5)
    c1Label[count].grid(row = count, column = 1)
    count = count + 1
count = 0
for i in initBuffer:
    c2Label.append(i)
    c2Label[count] = tk.Label(myLF1, text = i, padx = 5, pady = 5)
    c2Label[count].grid(row = count, column = 2)
    count = count + 1

#making 2nd labelframe
myLF2 = tk.LabelFrame(App, text = 'yukiho2', padx = 2, pady = 2, labelanchor = 'n')
myLF2.grid(row = 0, column = 1, padx = 15, pady = 5)
Entry2 = tk.Entry(myLF2, width = 12)
Entry2.insert(0, '11222')
Entry2.grid(row = 0, column = 99)


T1var = tk.IntVar()
T1check = tk.Checkbutton(App, text = 'starter', variable = T1var)
T1check.grid(row = 11, column = 0)
App.after(1, autoupdate)
    

if __name__ == '__main__':
    #aa()
    App.mainloop()
    print ('App close')
    #getCam()