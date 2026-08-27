# -*- coding: utf-8 -*-
"""
Created on Tue Jun 25 20:32:46 2019

@author: Green
"""

import pygame
import guiSerial

pygame.init()
pygame.font.init()

myfont = pygame.font.SysFont('Comic Sans MS', 30)

text = ['Ahh, today so Cool', 'idk what to do now']

WHITE = (255, 255, 255)
size = [1200, 750]
    

'''
class newGUI:
    def __init__(self):
        self.app = pygame.display.set_mode(size)
        pygame.display.set_caption('portController')
        clock = pygame.time.Clock()
        clock.tick(30)  
        self.bg_img = pygame.image.load('C:\imgBox\zeldaPrincess.png').convert()
        self.serialOff_img = pygame.image.load('C:\imgBox\serialOff.png').convert_alpha()
        self.serialOn_img = pygame.image.load('C:\imgBox\serialOn.png').convert_alpha()
        
        (self.app).fill(WHITE)
        (self.app).blit(self.bg_img, [0, 0])
        (self.app).blit(self.serialOff_img, [10, 10])
        pygame.display.flip()
        return
    def serialButtonPress(self, input):
        print ('enter button')
        if input == 1:
            (self.app).blit(self.serialOff_img, [10, 10])
        else:
            (self.app).blit(self.serialOn_img, [10, 10])
        return
    def working(self):
        running = 1
        serialButton_counter = 0
        while running:
            for event in pygame.event.get():
                if event.type == pygame.MOUSEMOTION:
                    x, y = pygame.mouse.get_pos()
                    if x >= 10 and x <= 255 and y>= 10 and y <= 90:
                        (self.app).blit(self.serialOn_img, [10, 10])
                    else:
                        (self.app).blit(self.serialOff_img, [10, 10])
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_0:
                        print('pressed')
                    if event.key == pygame.K_1:
                        print('presse1d')
                        bg_img2 = pygame.image.load('C:\imgBOx\iori.png').convert()
                        (self.app).blit(bg_img2, [0, 0])
                    if event.key == pygame.K_2: #serial Connnection
                        print ('notin')
                    if event.key == pygame.K_3:
                        (self.app).fill(WHITE)
                        (self.app).blit(self.bg_img, [0, 0])
                        x = x + 50
                        (self.app).blit(self.serialOff_img, [x, 10])
                if event.type == pygame.QUIT:
                    running = False
                    pygame.quit()
            
'''

def pyGUI():
    buttonArray = 0
    app = pygame.display.set_mode(size)
    pygame.display.set_caption('portController')
    running = True
    clock = pygame.time.Clock()
    clock.tick(30) 
    bg_img = pygame.image.load('C:\imgBox\mikiBackground.png').convert()
    serialOff_img = pygame.image.load('C:\imgBox\serialOff.png').convert_alpha()
    serialOn_img = pygame.image.load('C:\imgBox\serialOn.png').convert_alpha()
    operationOff_img = pygame.image.load('C:\imgBox\operationOff.png').convert_alpha()
    operationOn_img = pygame.image.load('C:\imgBox\operationOn.png').convert_alpha()
    statusCheck = pygame.image.load('C:\imgBox\statusCheck.png').convert_alpha()
    
    app.fill(WHITE)
    app.blit(bg_img, [0, 0])
    app.blit(serialOff_img, [10, 10])
    app.blit(operationOff_img, [10, 100])
    app.blit(statusCheck, [750, 50])

    y_axis = 60
    for x in range(len(text)):
        textsurface = myfont.render(text[x], False, (0, 255, 0))        
        app.blit(textsurface, [810,y_axis])
        y_axis = y_axis + 30
            
    statusCheck = 1
    pygame.time.set_timer(statusCheck, 1000)
    
    pygame.display.flip()

    while running:   
        for event in pygame.event.get():
            if event.type == pygame.MOUSEMOTION:
                x, y = pygame.mouse.get_pos()
                if x >= 10 and x <= 223 and y>= 10 and y <= 89:
                    buttonArray = 1
                    app.blit(serialOn_img, [10, 10])
                elif x >= 10 and x <= 223 and y>= 100 and y <= 179:
                    buttonArray = 2
                    app.blit(operationOn_img, [10, 100])
                else:
                    buttonArray = 0
                    app.blit(serialOff_img, [10, 10])
                    app.blit(operationOff_img, [10, 100])
            if event.type == pygame.MOUSEBUTTONUP:
                if buttonArray == 1:
                    portlist = guiSerial.serialconnection()
                    print (portlist)
            if event.type == 1:
                print ('this')
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_0:
                    print('pressed')
                if event.key == pygame.K_1:
                    print('presse1d')
                    bg_img2 = pygame.image.load('C:\imgBOx\iori.png').convert()
                    app.blit(bg_img2, [0, 0])
                if event.key == pygame.K_2: #serial Connnection
                    print ('notin')
                if event.key == pygame.K_3:
                    app.fill(WHITE)
                    app.blit(bg_img, [0, 0])
                    x = x + 50
                    app.blit(serialOff_img, [x, 10])
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()
        pygame.display.flip()
    return


def serialprint():
    print ('ok')




if __name__ == '__main__':
    #aa()
    #device.close()
    #portlist = guiSerial.serialconnection()
    pyGUI()
    #print ('App close')
    #aa = pyGUI()
    #aa.working()
    