#-------------------------------------------------------------------------------
# Name:        Object bounding box label tool
# Purpose:     Label object bboxes for ImageNet Detection data
# Author:      Qiushi
# Created:     06/06/2014
# Editor:      shen0512
#
#-------------------------------------------------------------------------------

from operator import index

from matplotlib.pyplot import text
from MyDataStructure import *
import MyTools

import tkinter
import tkinter.ttk as ttk
from PIL import Image as PImage, ImageTk, ExifTags

import os
import sys
import glob
from os import getenv
# from collections import OrderedDict
import json
import platform
import numpy
import copy
import math
import logging
import configparser

if(sys.version_info[0] == 2):
    from Tkinter import *
    import tkMessageBox
elif(sys.version_info[0] == 3):
    from tkinter import *
    from tkinter import messagebox as tkMessageBox
    from tkinter import filedialog

MAIN_COLORS = ['red','blue','black','yellow','green','darkolivegreen', 'darkseagreen', 'darkorange', 'darkslategrey', 'darkturquoise', 'darkgreen', 'darkviolet', 'darkgray', 'darkmagenta', 'darkblue', 'darkkhaki','darkcyan', 'darkred',  'darksalmon', 'darkslategray', 'darkgoldenrod', 'darkgrey', 'darkslateblue', 'darkorchid','skyblue','orange','pink','violet','brown','gold','Olive','Maroon', 'cyan','olivedrab', 'lightcyan', 'silver']

selected_color = 'red'
general_color = 'blue'

home  = getenv("HOME")

class CurAnnData:
    def __init__(self, index, imgDir, filename, labels, boxes, text, showImgW, showImgH) -> None:
        self.index = index
        self.imgDir = imgDir
        self.filename = filename
        self.imgPath = os.path.join(imgDir, filename)
        self.tkImg = None
        self.imgOriW = None
        self.imgOriH = None
        self.labels:List[int] = labels
        self.boxes:List[MyBox] = boxes
        self.text:List[str] = text

        self.showImgW = showImgW
        self.showImgH = showImgH

        self.mouseLStatus = MouseStatus.leftRelease.value
        self.mouseRStatus = MouseStatus.rightRelease.value

        self.lastX = 0
        self.lastY = 0

        # self.annData:List[AnnData] = []
        self.boxIds = []
        self.boxId = None
        self.textIds = []
        self.textId = None
        self.textBoxIds = []
        self.textBoxId = None
        
        self.labelId = -1
        self.objId = -1
    
    def __call__(self) -> None:
        
        self.pilImg = PImage.open(self.imgPath)
        self.imgOriW = self.pilImg.width
        self.imgOriH = self.pilImg.height

        # box deconvert
        for i in range(len(self.boxes)):
            self.boxes[i] = MyTools.convert(self.boxes[i], self.imgOriW, self.showImgW, self.imgOriH, self.showImgH)
        
        # image rotation
        oriKey = None
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation]=='Orientation':
                oriKey = orientation
                break

        exif = self.pilImg._getexif()
        if oriKey is not None and exif is not None and oriKey in exif.keys():    
            if exif[orientation] == 3:
                self.pilImg = self.pilImg.rotate(180, expand=True)
            elif exif[orientation] == 6:
                self.pilImg = self.pilImg.rotate(270, expand=True)
            elif exif[orientation] == 8:
                self.pilImg = self.pilImg.rotate(90, expand=True)
        
        # image resize
        self.pilImg = self.pilImg.resize((self.showImgW, self.showImgH))
        self.tkImg = ImageTk.PhotoImage(self.pilImg)

class LabelTool():
    def __init__(self, master, configPath = 'config.ini'):
        # load config from ini file
        config = configparser.ConfigParser()
        config.read(configPath)
        self.allLabelsPath = config['DEFAULT']['allLabelsPath']
        self.showImgW = int(config['DEFAULT']['showImgW'])
        self.showImgH = int(config['DEFAULT']['showImgH'])
        self.imgFormat = config['DEFAULT']['imgFormat'].split(',')
        self.annDataName = config['DEFAULT']['annName']
        
        # set up the main frame
        self.parent = master
        self.parent.protocol("WM_DELETE_WINDOW", self.onClose)
        self.parent.title("Annotation Tool")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width = False, height = False)

        # setup labels mapping
        self.allLabels = MyTools.loadTxtFile(self.allLabelsPath)
        
        # initialize global state
        self.imageDir = ''
        self.total = 0
        self.hl = None
        self.vl = None

        self.annData:List[AnnData] = []
        self.curAnnData:CurAnnData = None

        # ----------------- GUI stuff ---------------------
        # dir entry & load
        self.label = Label(self.frame, text = "Image Dir:")
        self.label.grid(row=0, column=0, sticky=E)
        self.entry = Entry(self.frame)
        self.entry.grid(row=0, column=1, sticky=W+E)
        self.explBtn = Button(self.frame, text="Browser", command=self.loadData)
        self.explBtn.grid(row=0, column=2, sticky=W+S+E, columnspan=2)

        # main panel for labeling
        self.mainPanel = Canvas(self.frame, cursor='tcross')

        # <Button-2> Mac-->mouse right; Window-->mouse wheel
        # <Button-3> Mac-->mouse wheel right; Window-->mouse right
        if platform.system() == 'Windows':
            # windows
            self.mainPanel.bind("<Button-1>", self.mouseLeftClick)
            self.mainPanel.bind("<Button-3>", self.mouseRightClick)
            self.mainPanel.bind("<B1-Motion>", self.mouseLeftPressMove)
        else:
            # mac
            self.mainPanel.bind("<Button-1>", self.mouseLeftClick)
            self.mainPanel.bind("<Button-2>", self.mouseRightClick)
            self.mainPanel.bind("<B1-Motion>", self.mouseLeftPressMove)
        
        self.mainPanel.bind("<Motion>", self.mouseMove)
        
        self.parent.bind("<Escape>", self.cancelAnn)  # press <Espace> to cancel current bbox
        self.parent.bind("c", self.cancelAnn) # press 'c' to cancel current bbox
        self.parent.bind("a", self.prevImg) # press 'a' to go backforward
        self.parent.bind("d", self.nextImg) # press 'd' to go forward
        self.parent.bind("e", self.editAnn) # press 'e' to edit annotation
        self.parent.bind("r", self.removeAnn) # press 'r' to remove annotation

        #
        self.mainPanel.grid(row=1, column=0, rowspan=7, columnspan=2, sticky=W+N)
        self.lb1 = Label(self.frame, text = 'Bounding boxes:')
        self.lb1.grid(row=2, column=2,  sticky=W+N, columnspan=2)
        
        self.listbox = Listbox(self.frame, width=30, height=12, exportselection=False)
        self.listbox.grid(row=3, column=2, sticky=N, columnspan=2)
        self.listbox.bind('<<ListboxSelect>>',self.listboxSelect)
     
        self.btnDel = Button(self.frame, text = 'Delete', command = self.deleteAnn)
        self.btnDel.grid(row=4, column=2, sticky=W+E+N, columnspan=2)
        self.btnClear = Button(self.frame, text = 'ClearAll', command=self.clearALL)
        self.btnClear.grid(row=5, column=2, sticky=W+E+N, columnspan=2)

        self.btnSave = Button(self.frame, text='Save', command=self.saveData)
        self.btnSave.grid(row=6, column=2, sticky=W+E+N, columnspan=2)

        # control panel for image navigation
        self.filenameLabel = Label(self.frame, text = "filename")
        self.filenameLabel.grid(row=8, column=0, columnspan=2, sticky=W)

        self.ctrPanel = Frame(self.frame)
        self.ctrPanel.grid(row=9, column=1, columnspan=2, sticky=W+E)
        
        self.prevBtn = Button(self.ctrPanel, text='<< Prev', width = 10, command = self.prevImg)
        self.prevBtn.pack(side = LEFT, padx = 5, pady = 3)
        self.nextBtn = Button(self.ctrPanel, text='Next >>', width = 10, command = self.nextImg)
        self.nextBtn.pack(side = LEFT, padx = 5, pady = 3)
        self.progLabel = Label(self.ctrPanel, text = "Progress:     /    ")
        self.progLabel.pack(side = LEFT, padx = 5)
        self.tmpLabel = Label(self.ctrPanel, text = "Go to Image No.")
        self.tmpLabel.pack(side = LEFT, padx = 5)
        self.idxEntry = Entry(self.ctrPanel, width = 5)
        self.idxEntry.pack(side = LEFT)
        self.goBtn = Button(self.ctrPanel, text = 'Go', command = self.gotoImg)
        self.goBtn.pack(side = LEFT)
        self.findBtn = Button(self.ctrPanel, text = 'Find', command = self.findNoAnnImage)
        self.findBtn.pack(side = LEFT)
        self.frame.columnconfigure(1, weight = 1)
        self.frame.rowconfigure(4, weight = 1)

        # display mouse position
        self.disp = Label(self.ctrPanel, text='')
        self.disp.pack(side=RIGHT)
        self.disp.config(text='x: 000, y: 000')

        # pop menu (label)
        self.menu = Menu(root, tearoff=False)
        for label in self.allLabels:
            self.menu.add_command(label=label, command=self.menu_command(label))

        #
        self.infoWindow = None

    # Pop window
    def infoWindowHandler(self, tl:MyPoint, br:MyPoint, objId=None):
        def enterClick():
            inputText = textEntry.get()
            tmp_labelId = self.allLabels.index(textCombobox.get())

            if objId == None:
                self.curAnnData.boxes.append(MyBox(tl, br))
                self.curAnnData.labels.append(tmp_labelId)
                self.curAnnData.text.append(inputText)

                self.curAnnData.boxIds.append(self.curAnnData.boxId)
                self.curAnnData.boxId = None
                self.curAnnData.textIds.append(self.curAnnData.textId)
                self.curAnnData.textId = None
                self.curAnnData.textBoxIds.append(self.curAnnData.textBoxId)
                self.curAnnData.textBoxId = None
                
                self.listbox.insert(END, 'Label: %s, text: %s' %(textCombobox.get(), inputText))
                self.listbox.itemconfig(len(self.curAnnData.boxIds)-1, fg=general_color)
            else:
                self.curAnnData.labels[objId] = tmp_labelId
                self.curAnnData.text[objId] = inputText
                
                self.listbox.delete(objId)
                self.listbox.insert(objId, 'Label: %s, text: %s' %(textCombobox.get(), inputText))
                self.listbox.itemconfig(objId, fg=general_color)
                
                
            self.infoWindow.destroy()
            self.draw()
        
        def textEntryListener(event):
            enterClick()
        
        def cancelClick():
            self.infoWindowOnClose()
        
        self.infoWindow = tkinter.Toplevel(self.parent)
        self.infoWindow.title('Text Annontation')
        self.infoWindow.protocol("WM_DELETE_WINDOW", self.infoWindowOnClose)
        self.infoWindow.resizable(width=False, height=False)

        textCanvas = Canvas(self.infoWindow)
        textCanvas.grid(row=0, column=0, sticky=W+E, columnspan=2)
        tkimgCrop = numpy.array(self.curAnnData.pilImg).copy()
        if tl.x == None and tl.y == None and br.x == None and br.y == None:
            box = self.curAnnData.boxes[self.curAnnData.labelId]
            tkimgCrop = tkimgCrop[box.tl.y:box.br.y, box.tl.x:box.br.x]
        else:
            tkimgCrop = tkimgCrop[tl.y:br.y, tl.x:br.x]

        textCanvas.config(width = tkimgCrop.shape[1], height=tkimgCrop.shape[0])
        PIL_tkimgCrop = ImageTk.PhotoImage(PImage.fromarray(tkimgCrop))
        textCanvas.create_image(0, 0, image=PIL_tkimgCrop, anchor=NW)

        label = Label(self.infoWindow, text=f'label: ')
        label.grid(row=1, column=0, sticky=W)
        textCombobox = ttk.Combobox(self.infoWindow, values=self.allLabels, state='readonly', exportselection=False)
        textCombobox.grid(row=1, column=1, sticky=W)
        
        if objId != None:
            textCombobox.current(self.curAnnData.labels[objId])
        else:
            textCombobox.current(self.curAnnData.labelId)

        textLabel = Label(self.infoWindow, text=f'text: ')
        textLabel.grid(row=2, column=0, sticky=W)
        textEntry = Entry(self.infoWindow)
        textEntry.bind("<Return>", textEntryListener)
        textEntry.grid(row=2, column=1, sticky=W+E)
        textEntry.focus()
        
        if objId != None:
            textEntry.insert(0, self.curAnnData.text[objId])
        
        enterBtn = Button(self.infoWindow, text='Enter', command=enterClick)
        enterBtn.grid(row=2, column=2, sticky= W+E)
        cancelBtn = Button(self.infoWindow, text='Cancel', command=cancelClick)
        cancelBtn.grid(row=2, column=3, sticky= W+E)
        
        # reset global variable
        self.curAnnData.labelId = -1
        self.curAnnData.objId = -1

        self.infoWindow.mainloop()
        
    def infoWindowOnClose(self):
        self.checkInfoWindowExist()
    
    def checkInfoWindowExist(self):

        if self.infoWindow != None and self.infoWindow.winfo_exists():
            self.infoWindow.destroy()
            self.resetDrawing()
            self.draw()
            return True
        
        return False

    # Main window
    def menu_command(self, label):
        return lambda:self.labelSelect(label)

    def labelSelect(self, label):
        self.curAnnData.labelId = self.allLabels.index(label)
        
    def popupmenu(self, event):
        self.curAnnData.labelId = -1
        self.menu.post(event.x_root,event.y_root)
      
    def listboxSelect(self, event):
        
        self.checkInfoWindowExist()

        box_select = self.listbox.curselection()
        self.curObjId = -1
        if len(box_select) > 0:
            self.curAnnData.objId = box_select[0]
            self.curAnnData.mouseRStatus = MouseStatus.rightPress.value
            self.draw()


    # other
    def draw(self, x=None, y=None):
        '''
        
        '''
        if x != None and y != None:
            if self.curAnnData.labelId != -1:
                
                if self.curAnnData.boxId:
                    self.mainPanel.delete(self.curAnnData.boxId)
                self.curAnnData.boxId = self.mainPanel.create_rectangle(self.curAnnData.lastX, 
                                                                        self.curAnnData.lastY, 
                                                                        x, 
                                                                        y, 
                                                                        width=3, 
                                                                        outline=general_color)
                
                if self.curAnnData.textId:
                    self.mainPanel.delete(self.curAnnData.textId)
                self.curAnnData.textId = self.mainPanel.create_text(min(self.curAnnData.lastX, x), 
                                                                    min(self.curAnnData.lastY, y), 
                                                                    text=self.allLabels[self.curAnnData.labelId], 
                                                                    anchor='nw', 
                                                                    font=('Times', 18))
                
                if self.curAnnData.textBoxId:
                    self.mainPanel.delete(self.curAnnData.textBoxId)
                self.curAnnData.textBoxId = self.mainPanel.create_rectangle(self.mainPanel.bbox(self.curAnnData.textId), 
                                                                            fill=general_color, 
                                                                            outline=general_color)
                
                self.mainPanel.tag_lower(self.curAnnData.textBoxId, self.curAnnData.textId)
        else:
            if self.listbox.size() > 0:
                self.listbox.select_clear(0, 'end')
            
                for i in range(len(self.curAnnData.boxes)):
                    self.mainPanel.delete(self.curAnnData.boxIds[i])
                    self.mainPanel.delete(self.curAnnData.textBoxIds[i])
                    self.mainPanel.delete(self.curAnnData.textIds[i])
                    if i == self.curAnnData.objId:
                        self.curAnnData.boxIds[i] = self.mainPanel.create_rectangle(self.curAnnData.boxes[i].tl.x, 
                                                                                    self.curAnnData.boxes[i].tl.y, 
                                                                                    self.curAnnData.boxes[i].br.x, 
                                                                                    self.curAnnData.boxes[i].br.y, 
                                                                                    width=3, 
                                                                                    outline=selected_color, 
                                                                                    dash=(5,5))
                        
                        self.curAnnData.textIds[i] = self.mainPanel.create_text(self.curAnnData.boxes[i].tl.x, 
                                                                                self.curAnnData.boxes[i].tl.y, 
                                                                                text=self.allLabels[self.curAnnData.labels[i]], 
                                                                                anchor='nw', font=('Times', 18))

                        self.curAnnData.textBoxIds[i] = self.mainPanel.create_rectangle(self.mainPanel.bbox(self.curAnnData.textIds[i]), 
                                                                                        fill=selected_color, 
                                                                                        outline=selected_color)
                        self.mainPanel.tag_lower(self.curAnnData.textBoxIds[i], self.curAnnData.textIds[i])
                        self.listbox.select_set(i)

                    else:
                        self.curAnnData.boxIds[i] = self.mainPanel.create_rectangle(self.curAnnData.boxes[i].tl.x, 
                                                                                    self.curAnnData.boxes[i].tl.y,
                                                                                    self.curAnnData.boxes[i].br.x, 
                                                                                    self.curAnnData.boxes[i].br.y,
                                                                                    width=3,
                                                                                    outline=general_color)


                        self.curAnnData.textIds[i] = self.mainPanel.create_text(self.curAnnData.boxes[i].tl.x, 
                                                                                self.curAnnData.boxes[i].tl.y, 
                                                                                text=self.allLabels[self.curAnnData.labels[i]], 
                                                                                anchor='nw', 
                                                                                font=('Times', 18))

                        self.curAnnData.textBoxIds[i] = self.mainPanel.create_rectangle(self.mainPanel.bbox(self.curAnnData.textIds[i]), 
                                                                                        fill=general_color, 
                                                                                        outline=general_color)

                        self.mainPanel.tag_lower(self.curAnnData.textBoxIds[i], self.curAnnData.textIds[i])  

    def resetDrawing(self):
        if self.curAnnData.boxId:
            self.mainPanel.delete(self.curAnnData.boxId)
            self.curAnnData.boxId = None
        if self.curAnnData.textId:
            self.mainPanel.delete(self.curAnnData.textId)
            self.curAnnData.textId = None
        if self.curAnnData.textBoxId:
            self.mainPanel.delete(self.curAnnData.textBoxId)
            self.curAnnData.textBoxId = None
        
        self.curAnnData.labelId = -1
        self.curAnnData.objId = -1
        self.curAnnData.mouseLStatus = MouseStatus.leftRelease.value
        self.curAnnData.mouseRStatus = MouseStatus.rightRelease.value
        self.curAnnData.lastX = 0
        self.curAnnData.lastY = 0

    def delBBox(self, delId):
        self.mainPanel.delete(self.curAnnData.boxIds[delId])
        self.curAnnData.boxIds.pop(delId)
        self.curAnnData.boxes.pop(delId)
        self.curAnnData.labels.pop(delId)
        self.curAnnData.text.pop(delId)
        self.listbox.delete(delId)
        self.mainPanel.delete(self.curAnnData.textIds[delId])
        self.curAnnData.textIds.pop(delId)
        self.mainPanel.delete(self.curAnnData.textBoxIds[delId])
        self.curAnnData.textBoxIds.pop(delId)
        
        self.curAnnData.objId = -1
        self.curAnnData.mouseRStatus = MouseStatus.rightRelease.value
        self.curAnnData.mouseLStatus = MouseStatus.leftRelease.value
        
    def loadImg(self):
        # set current annotation data
        if self.curAnnData is not None:
            tmpIndex = self.curAnnData.index
            tmpFilename = self.curAnnData.filename

            oriImgW = self.curAnnData.imgOriW
            oriImgH = self.curAnnData.imgOriH

            tmpLabels = self.curAnnData.labels.copy()
            tmpText = self.curAnnData.text.copy()
            tmpBoxes = self.curAnnData.boxes.copy()
            for i in range(len(tmpBoxes)):
                tmpBoxes[i] = MyTools.convert(tmpBoxes[i], self.showImgW, oriImgW, self.showImgH, oriImgH)
            
            self.annData[tmpIndex].filename = tmpFilename
            self.annData[tmpIndex].labels = tmpLabels
            self.annData[tmpIndex].boxes = tmpBoxes
            self.annData[tmpIndex].text = tmpText
                


        self.curAnnData = CurAnnData(self.cur-1,
                                    self.imgDir, 
                                    self.annData[self.cur-1].filename, 
                                    self.annData[self.cur-1].labels.copy(),
                                    self.annData[self.cur-1].boxes.copy(),
                                    self.annData[self.cur-1].text.copy(),
                                    self.showImgW,
                                    self.showImgH)
        self.curAnnData()

        # set view
        self.mainPanel.config(width=self.showImgW, height=self.showImgH)
        self.mainPanel.create_image(0, 0, image=self.curAnnData.tkImg, anchor=NW)
        self.progLabel.config(text = "%04d/%04d" %(self.cur, self.total))
        self.filenameLabel.config(text=f'filename: {self.curAnnData.filename}')
        self.listbox.delete(0, END)
        for i in range(len(self.curAnnData.boxes)):
            # object rectangle
            tmpId = self.mainPanel.create_rectangle(self.curAnnData.boxes[i].tl.x, 
                                                    self.curAnnData.boxes[i].tl.y, 
                                                    self.curAnnData.boxes[i].br.x, 
                                                    self.curAnnData.boxes[i].br.y,
                                                    width=3,
                                                    outline=general_color)
            self.curAnnData.boxIds.append(tmpId)
            
            # label rectangle
            tmpTextId = self.mainPanel.create_text(self.curAnnData.boxes[i].tl.x, 
                                                    self.curAnnData.boxes[i].tl.y, 
                                                    text=self.allLabels[self.curAnnData.labels[i]], 
                                                    anchor='nw', 
                                                    font=('Times', 18))

            tmpTextBoxId = self.mainPanel.create_rectangle(self.mainPanel.bbox(tmpTextId), 
                                                            fill=general_color, 
                                                            outline=general_color)

            self.mainPanel.tag_lower(tmpTextBoxId, tmpTextId)
            self.curAnnData.textIds.append(tmpTextId)
            self.curAnnData.textBoxIds.append(tmpTextBoxId)

            # listbox
            self.listbox.insert(END, 'Label: %s, text: %s' %(self.allLabels[self.curAnnData.labels[i]], self.curAnnData.text[i]))
            self.listbox.itemconfig(len(self.curAnnData.boxIds)-1, fg=general_color)
    
    def cursorInBbox(self, event):
        '''
        
        '''

        self.curAnnData.objId = -1
        boxArea = {i: self.curAnnData.boxes[i].getArea() for i in range(len(self.curAnnData.boxes))}
        boxArea = dict(sorted(boxArea.items(), key= lambda item: item[1]))

        for key in boxArea.keys():
            tmpBox = self.curAnnData.boxes[key]
            if tmpBox.tl.x<event.x and event.x<tmpBox.br.x and tmpBox.tl.y<event.y and event.y<tmpBox.br.y:
                self.curAnnData.objId = key
                break

    def onClose(self):
        self.saveData()
        self.parent.destroy()

    def showPopWindow(self, msg:str, showType:str='info') -> None:
        assert type(msg) == str
        assert type(showType) == str and (showType == 'info' or showType == 'warning' or showType == 'error')

        if showType == 'info':
            tkMessageBox.showinfo('Info', message=msg)
        elif showType == 'warning':
            tkMessageBox.showwarning('Warning', message=msg)
        elif showType == 'error':
            tkMessageBox.showerror('Error', message=msg)



    # mouse listener
    def mouseLeftPressMove(self, event):
        if self.curAnnData is None or self.curAnnData.tkImg is None:
            return

        x = MyTools.checkValue(event.x, 0, self.showImgW)
        y = MyTools.checkValue(event.y, 0, self.showImgH)
        
        self.disp.config(text = 'x: %.3d, y: %.3d' %(x, y))

        if self.hl:
            self.mainPanel.delete(self.hl)
        self.hl = self.mainPanel.create_line(0, 
                                            y, 
                                            self.curAnnData.tkImg.width(), 
                                            y, 
                                            width=3, 
                                            fill='black')
        if self.vl:
            self.mainPanel.delete(self.vl)
        self.vl = self.mainPanel.create_line(x, 
                                            0, 
                                            x, 
                                            self.curAnnData.tkImg.height(), 
                                            width=3, 
                                            fill='black')


        if self.curAnnData.mouseRStatus == MouseStatus.rightPress.value:
            if self.curAnnData.objId != -1:             
                box = self.curAnnData.boxes[self.curAnnData.objId]()
                
                minIndex = -1
                minValue = 0
                for i in range(len(box)):
                    dif_value = math.sqrt(pow(event.x-box[i].x, 2) + pow(event.y-box[i].y, 2))
                    if i == 0 or dif_value < minValue:
                       minIndex = i
                       minValue = dif_value

                if minIndex == 0:
                    self.curAnnData.boxes[self.curAnnData.objId].tl = MyPoint(x, y)
                    self.curAnnData.boxes[self.curAnnData.objId].tr = MyPoint(self.curAnnData.boxes[self.curAnnData.objId].tr.x, y)
                    self.curAnnData.boxes[self.curAnnData.objId].bl = MyPoint(x, self.curAnnData.boxes[self.curAnnData.objId].bl.y)

                elif minIndex == 1:
                    self.curAnnData.boxes[self.curAnnData.objId].tr = MyPoint(x, y)
                    self.curAnnData.boxes[self.curAnnData.objId].tl = MyPoint(self.curAnnData.boxes[self.curAnnData.objId].tl.x, y)
                    self.curAnnData.boxes[self.curAnnData.objId].br = MyPoint(x, self.curAnnData.boxes[self.curAnnData.objId].br.y)

                elif minIndex == 2:
                    self.curAnnData.boxes[self.curAnnData.objId].br = MyPoint(x, y)
                    self.curAnnData.boxes[self.curAnnData.objId].tr = MyPoint(x, self.curAnnData.boxes[self.curAnnData.objId].tr.y)
                    self.curAnnData.boxes[self.curAnnData.objId].bl = MyPoint(self.curAnnData.boxes[self.curAnnData.objId].bl.x, y)

                elif minIndex == 3:
                    self.curAnnData.boxes[self.curAnnData.objId].bl = MyPoint(x, y)
                    self.curAnnData.boxes[self.curAnnData.objId].tl = MyPoint(x, self.curAnnData.boxes[self.curAnnData.objId].tl.y)
                    self.curAnnData.boxes[self.curAnnData.objId].br = MyPoint(self.curAnnData.boxes[self.curAnnData.objId].br.x, y)
                
                self.draw()

    def mouseRightClick(self, event):
        if self.curAnnData is None or self.curAnnData.tkImg is None:
            return
        
        if self.checkInfoWindowExist() or len(self.annData) == 0 :
            return
        
        self.cursorInBbox(event)
        if self.curAnnData.objId != -1:
            self.curAnnData.mouseRStatus = MouseStatus.rightPress.value
        else:
            self.curAnnData.mouseRStatus = MouseStatus.rightRelease.value

        self.draw()
        
    def mouseLeftClick(self, event):
        if self.curAnnData is None or self.curAnnData.tkImg is None:
            return

        x = MyTools.checkValue(event.x, 0, self.showImgW) 
        y = MyTools.checkValue(event.y, 0, self.showImgH)

        if self.checkInfoWindowExist() or self.curAnnData.mouseRStatus >= MouseStatus.rightPress.value or len(self.annData) == 0:
            return

        if self.curAnnData.mouseLStatus == MouseStatus.leftRelease.value:
            
            self.curAnnData.lastX = x 
            self.curAnnData.lastY = y
            self.popupmenu(event)
            self.curAnnData.mouseLStatus = MouseStatus.leftPress.value
        else:
            if self.curAnnData.labelId == -1:
                self.curAnnData.lastX = x
                self.curAnnData.lastY = y
                self.popupmenu(event)
                self.curAnnData.mouseLStatus = MouseStatus.leftPress.value

            else:
                x1 = min(self.curAnnData.lastX, event.x)
                y1 = min(self.curAnnData.lastY, event.y)
                x2 = max(self.curAnnData.lastX, event.x)
                y2 = max(self.curAnnData.lastY, event.y)

                self.infoWindowHandler(MyPoint(x1, y1), MyPoint(x2, y2))
                self.curAnnData.mouseLStatus = MouseStatus.leftRelease.value
                       
    def mouseMove(self, event):
        
        if self.curAnnData is None or self.curAnnData.tkImg is None:
            return

        x = MyTools.checkValue(event.x, 0, self.showImgW)
        y = MyTools.checkValue(event.y, 0, self.showImgH)

        self.disp.config(text = 'x: %.3d, y: %.3d' %(x, y))
        if self.hl:
            self.mainPanel.delete(self.hl)
        self.hl = self.mainPanel.create_line(0, 
                                            y, 
                                            self.curAnnData.tkImg.width(), 
                                            y, 
                                            width = 3, 
                                            fill='black')
        if self.vl:
            self.mainPanel.delete(self.vl)
        self.vl = self.mainPanel.create_line(x, 
                                            0, 
                                            x, 
                                            self.curAnnData.tkImg.height(), 
                                            width=3, 
                                            fill='black')
        
        self.draw(x, y)
    

    # button listener
    def deleteAnn(self):
        sel = self.listbox.curselection() 
        if self.checkInfoWindowExist() or len(sel) != 1 :
            return
        
        idx = int(sel[0])
        self.delBBox(idx)

    def gotoImg(self):
        self.checkInfoWindowExist()

        if self.idxEntry.get() != '':
            idx = int(self.idxEntry.get())
            if 1 <= idx and idx <= self.total:
                self.cur = idx
                self.loadImg()

    def saveData(self):
        self.checkInfoWindowExist()

        if len(self.annData) == 0:
            return

        if self.curAnnData is not None: 
            tmpIndex = self.curAnnData.index
            tmpFilename = self.curAnnData.filename

            oriImgW = self.curAnnData.imgOriW
            oriImgH = self.curAnnData.imgOriH

            tmpLabels = self.curAnnData.labels.copy()
            tmpText = self.curAnnData.text.copy()
            tmpBoxes = self.curAnnData.boxes.copy()
            for i in range(len(tmpBoxes)):
                tmpBoxes[i] = MyTools.convert(tmpBoxes[i], self.showImgW, oriImgW, self.showImgH, oriImgH)
            
            self.annData[tmpIndex].filename = tmpFilename
            self.annData[tmpIndex].labels = tmpLabels
            self.annData[tmpIndex].boxes = tmpBoxes
            self.annData[tmpIndex].text = tmpText
        
        output = []
        for tmp in self.annData:
            output.append(tmp.convert2Output())

        MyTools.saveToJS(os.path.join(self.imgDir, self.annDataName), output, override=True)
        tkMessageBox.showinfo("Information!", message = "Save all annotations")

    def loadData(self):
        directory = filedialog.askdirectory(initialdir=home)
        self.entry.delete(0, END)
        self.entry.insert(0, directory)

        try:
            self.imgDir = self.entry.get()
            self.parent.focus()
        except ValueError as ve:
            tkMessageBox.showerror("Error!", message = "The folder should be numbers")
            return

        self.cur = 1
        if os.path.isfile(os.path.join(self.imgDir, self.annDataName)):
            # load annotation from file
            tmpAnn = MyTools.loadJsonFile(os.path.join(self.imgDir, self.annDataName))
            
            for tmp in tmpAnn:
                filename = tmp['filename']
                boxes = tmp['boxes']
                
                for i in range(len(boxes)):
                    boxes[i] = MyBox(tl=MyPoint(boxes[i][0][0], boxes[i][0][1]),
                                    tr=MyPoint(boxes[i][1][0], boxes[i][1][1]),
                                    br=MyPoint(boxes[i][2][0], boxes[i][2][1]),
                                    bl=MyPoint(boxes[i][3][0], boxes[i][3][1]))

                labels = tmp['labels']
                text = tmp['text']
                self.annData.append(AnnData(filename, boxes, labels, text))
        else:
            # new annotation

            imgList = []
            for format in self.imgFormat:
                imgList += glob.glob(os.path.join(self.imgDir, f'*.{format}'))

            if len(imgList) == 0:
                print('[Error] No .jpg(.png/.jpeg) images found in the specified dir!')
                tkMessageBox.showerror("Error!", message = "No .jpg images found in the specified dir!")
                return

            for imgPath in imgList:
                self.annData.append(AnnData(os.path.basename(imgPath), [], [], []))
        
        self.total = len(self.annData)
        self.loadImg()

    def findNoAnnImage(self):
        self.checkInfoWindowExist()

        goImageIdx = -1
        for i in range(len(self.annData)):
            bboxes = self.annData[i]['bbox']
            
            if len(bboxes) == 0:
                goImageIdx = i + 1
                break
        
        if goImageIdx == -1:
            tkMessageBox.showinfo("Information!", message = "All images annotated")
        else:
            self.cur = goImageIdx
            self.loadImage()

    def clearALL(self):
        if self.checkInfoWindowExist() or len(self.annData) == 0:
            return
        
        self.curAnnData = CurAnnData(self.imgDir, 
                                    self.annData[self.cur-1].filename, 
                                    [],
                                    [],
                                    [],
                                    self.showImgW,
                                    self.showImgH)
        
    # keyboard listener
    def cancelAnn(self, event):
        self.checkInfoWindowExist()
        self.resetDrawing()
    
    def editAnn(self, event):
        if self.curAnnData is None:
            return

        if self.curAnnData.mouseRStatus == MouseStatus.rightPress.value and self.curAnnData.objId != -1:
            tmpBox = self.curAnnData.boxes[self.curAnnData.objId]
            self.infoWindowHandler(tmpBox.tl, tmpBox.br, self.curAnnData.objId)
    
    def removeAnn(self, event):
        if self.curAnnData is None:
            return

        if self.curAnnData.mouseRStatus == MouseStatus.rightPress.value and self.curAnnData.objId != - 1:
            self.delBBox(self.curAnnData.objId)
    
    def prevImg(self, event = None):
        if self.curAnnData is None:
            return

        self.checkInfoWindowExist()

        if self.cur > 1:
            self.cur -= 1
            self.loadImg()
        else:
            tkMessageBox.showinfo("Information!", message = "This is first image")

    def nextImg(self, event = None):
        if self.curAnnData is None:
            return

        self.checkInfoWindowExist()

        if self.cur < self.total:
            self.cur += 1
            self.loadImg()
        else:
            tkMessageBox.showinfo("Information!", message = "All images annotated")


if __name__ == '__main__':
    root = Tk()
    tool = LabelTool(root)
    # root.resizable(width = False, height = True)
    root.mainloop()
