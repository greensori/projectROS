# -*- coding: utf-8 -*-
"""
Created on Tue Jun 25 13:30:06 2019

@author: Green
"""

from Tkinter import *
from PIL import ImageGrab, Image, ImageTk
import serial
import time
import numpy as np

resultGy = np.zeros((10,), dtype = np.int)

tkpos = []

operationtime = 0
stepwork = 0

portno = []
portlist = ['portlist']
portgroup = ['connect']
portentry = ['connect']
portlabel = ['connect']
TBlabel = ['testboard']
mainframe = ['main']
maintester = ['main']
gyroH1 = ['headRpt']
gyroH2 = ['headLpt']
gyroBr = ['BreastPt']
gyroWa = ['waistPt']
temprow = 0
tempcol = 0
PDA = 0 

bodypoint = ['Tester', 'shoulderjoint', 'R_hand', 'breast', 'R_ankle',  'R_cochlea', 'R_shoulder', 'R_wrist', 'R_pelvis', 'R_Knee', 'L_cochlea', 'L_shoulder', 'L_wrist', 'waist', 'L_knee', 'emotion', 'neck', 'L_hand', 'L_pelvis', 'L_ankle']
TBlabelname = ['notin', 'portNo : ', 'Accelation : ', 'PWM : ', 'Times : ']
maintestername = ['notin', 'workon : ', 'steps : ', 'potentio : ']
gyroScope = ['notin', 'yaw', 'pitch', 'roll', 'Ax', 'Ay', 'Az', 'Mx', 'My', 'Mz']
tagword = ['ax', 'ay', 'az', 'gx', 'gy', 'gz', 'mx', 'my', 'mz', 'end']

##gyroscopesetting
for i in range(1, 10):
    gyroH1.append('gyh1%d' %i)
    gyroH2.append('gyh2%d' %i)
    gyroBr.append('gybr%d' %i)
    gyroWa.append('gywa%d' %i)
    
#mainframe setting
for i in range(1, 10):
    mainframe.append('mainF%d' %i)

for i in range(1, 4):
    maintester.append('mtester%d' %i)


#for using port status
for i in range(1, 9):
    portlist.append('port%d' %i)
    portentry.append('P_entry%d' %i)
    portlabel.append('P_label%d' %i)
    portgroup.append('P_grouop%d' %i)

#for using in testboarder
for i in range(1, 5):
    TBlabel.append('TBlabel%d' %i)

def serialconnection():
    global portlist
    for i in range(1, 9):
        try:
            baudrate = portentry[i].get()
            portlist[i] = serial.Serial('COM%d' %i, baudrate)
            portno.append(i)
            portlabel[i].config(text = 'connected') 
            print ('connected port %d' %i)
        except:
            portlabel[i].config(text = 'disconnected')
            print ('cant conect com%d' %i)


##need to modify
def serialread():
    count = 0
    gycount = 0
    while count < 5:
        time.sleep(0.01)
        count += 1
        msg = portlist[6].readline(portlist[6].inWaiting()) [:-2]
        '''
        if msg <> '':
            try:
                for i in tagword:
                    if msg.index(i):
                        resultGy[gycount] = msg.index(i)
                        gycount+= 1
                        print (i, resultGy[gycount])
            except:
                gycount = 0
                print ('noword')
                
                ////////////////////////////////
            if count == 10:
                try:
                    for i in range(gycount - 1):
                        pos = [resultpt[i] + 3, (resultpt[(i + 1)] - 1)]
                        agm[i] = msg[pos[0]: pos[1]]
                        agm_mean[meancount][i] = agm[i]
                except:
                    pass
                '''

def autowriter():
    delaytimer = 200
    global stepwork
    global PDA
    global operationtime
    if (T1var.get() == 1):
        if PDA == 0:
            operationtime = time.time()
            delaytimer = T4scale.get()
            PDA = 1
            stepwork = 1
            portlist[int(T1scale.get())].write(str(T2scale.get()))
            portlist[int(T1scale.get())].write(str(T3scale.get()))
        elif PDA == 1:
            stepwork += 1
            delaytimer = T4scale.get()
            portlist[int(T1scale.get())].write(str(T4scale.get()))
    else:
        PDA = 0
        delaytimer = 200
    maintester[1].configure(text = ('work on : %d' %(time.time() - operationtime)))
    maintester[2].configure(text = ('steps : %d' %stepwork))
    App.after(delaytimer, autowriter)
    return

def Breader():
    return

def Bworker():
    count = 0
    stime = time.time()
    print (T2scale.get(), T3scale.get(), T4scale.get())
    while (time.time() - stime) < 0.1:
        portlist[int(T1scale.get())].write(str(count))
        count += 1
    print (count)
    return

def openfn2():
    try:
        portlabel[1].config(text = 'ok') 
        print ('changed')
    except:
        pass
    
def openfn3(label1):
    sstime = time.time()
    label1.configure(text = (time.time() - sstime))
    app.after(1000, openfn(label1))
    app.config()
    print ('changed')

def labelchanger():
    label1.configure(text = time.time()) 
    App.after(1000, labelchanger)

def main_move(event):
    if tkpos:
        connect.geometry('+{0}+{1}'.format(tkpos[0], tkpos[1]))

def sub_move(event):
    min_w = App.winfo_rootx()
    min_h = App.winfo_rooty()
    max_w = App.winfo_rootx() + App.winfo_width() - 15
    max_h = App.winfo_rooty() + App.winfo_height() - 35
    # Conditional statements to keep sub window inside main
    if event.x < min_w:
        connect.geometry("+{0}+{1}".format(min_w, event.y))
    elif event.y < min_h:
        connect.geometry("+{0}+{1}".format(event.x, min_h))
    elif event.x + event.width > max_w:
        connect.geometry("+{0}+{1}".format(max_w - event.width, event.y))
    elif event.y + event.height > max_h:
        connect.geometry("+{0}+{1}".format(event.x, max_h - event.height))
    global tkpos
    # Set the current sub window position
    tkpos = [event.x, event.y]  
    return



img = Image.open('img_title4.png')

##tkinter menu
App = Tk()
App.title('smartGUI')
App.resizable(width = False, height = False)
App.geometry('800x550+1000+500')
T1var = IntVar()
msg = str('hello')
photo = ImageTk.PhotoImage(img)
##testerport
'''
label2 = Label(App, image = photo)
label2.image = photo
label2.pack()
label1 = Label(App, text = msg)
label1.place(x = 10, y = 10)
'''
## add the tester status frame
mainframe[1] = LabelFrame(App, text = 'tester', padx = 5, pady = 5)
mainframe[1].grid(row = 0, column = 0, padx = 5, pady = 5)
for i in range(1, 4):
    maintester[i] = Label(mainframe[1], text = maintestername[i])
    maintester[i].grid(row = (i - 1), column = 0)

##start to making menu
topmenu = Menu(App)
filemenu = Menu(topmenu, tearoff = 0)
filemenu.add_command(label = 'connect', command = serialconnection)
filemenu.add_command(label = 'testmsg2', command = openfn2)
filemenu.add_command(label = 'testmsg3', command = openfn2)
filemenu.add_separator()
filemenu.add_command(label = 'close', command = App.destroy)
topmenu.add_cascade(label = 'port', menu = filemenu)
editmenu = Menu(topmenu, tearoff = 0)
editmenu.add_command(label = 'testmsg3', command = serialread)
topmenu.add_cascade(label = 'running', menu = editmenu)
App.config(menu = topmenu)
##complete making menubar // start setting label
#canvas = Canvas(App, width = 300, height = 300)
#canvas.pack()
##add toplevel(connection)
connect = Toplevel(App)
connect.title("connection setting")
connect.geometry('225x320+1050+550')
connect.resizable(width=False, height = False)
connect.transient(App)
for i in range(1, 9):
    if i % 2 == 0:
        portgroup[i] = LabelFrame(connect, text = 'port%d' %i, padx = 5, pady = 5)
        portgroup[i].grid(row = (i - 1), column = 1, padx = 5, pady = 5)
        portentry[i] = Entry(portgroup[i], width = 12)
        portentry[i].pack()
        portentry[i].insert(0, '19200')
        portlabel[i] = Label(portgroup[i], text = 'ready')
        portlabel[i].pack()
    else:
        portgroup[i] = LabelFrame(connect, text = 'port%d' %i, padx = 5, pady = 5)
        portgroup[i].grid(row = (i), column = 0, padx = 5, pady = 5)
        portentry[i] = Entry(portgroup[i], width = 12)
        portentry[i].pack()
        portentry[i].insert(0, '19200')
        portlabel[i] = Label(portgroup[i], text = 'ready')
        portlabel[i].pack()
##end setting connection part
##add toplevel to control sample board
tester = Toplevel(App)
tester.title("tester")
tester.geometry('150x165+1050+550')
tester.resizable(width=False, height = False)
tester.transient(App)
for i in range(1, 5):
    TBlabel[i] = Label(tester, text = TBlabelname[i])
    TBlabel[i].grid(row = i, column = 0, padx = 2, pady = 2)
T1scale = Spinbox(tester, from_ = 1, to = 8, width = 6)
T1scale.grid(row = 1, column = 1, padx = 2, pady = 2)
T2scale = Spinbox(tester, from_ = -4, to = 4, width = 6)
T2scale.grid(row = 2, column = 1, padx = 2, pady = 2)
T3scale = Spinbox(tester, from_ = 570, to = 20000, width = 6)
T3scale.grid(row = 3, column = 1, padx = 2, pady = 2)
T4scale = Spinbox(tester, from_ = 0, to = 500, width = 6)
T4scale.grid(row = 4, column = 1, padx = 2, pady = 2)
T1check = Checkbutton(tester, text = 'autowrite', variable = T1var)
T1check.grid(row = 5, column = 0, padx = 2, pady = 2)
Button1 = Button(tester, text = 'Reader', width = 7, command = Breader)
Button1.grid(row = 6, column = 0, padx = 2, pady = 2)
Button2 = Button(tester, text = 'RUN', width = 7, command = Bworker)
Button2.grid(row = 6, column = 1, padx = 2, pady = 2)
App.bind('<Configure>', main_move)
connect.bind('<Configure>',sub_move)
#App.after(1, labelchanger)
App.after(1, autowriter)


def start():
    App.mainloop()
    return

if __name__ == '__main__':
    start()