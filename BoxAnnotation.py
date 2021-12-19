#-------------------------------------------------------------------------------
# Name:        Object bounding box label tool
# Purpose:     Label object bboxes for ImageNet Detection data
# Author:      Qiushi
# Created:     06/06/2014
# Editor:      shen0512
#
#-------------------------------------------------------------------------------
from __future__ import division
from posixpath import split
import tkinter
import tkinter.ttk as ttk
from PIL import Image as PImage, ImageTk
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
# image sizes for the examples
window_w = 720
window_h = 720
labels_root = 'classes.txt'

all_label = []
try:
    with open(labels_root, 'r', encoding='utf-8') as f:
        all_label = f.readlines()
    all_label = [label.strip() for label in all_label]
except IOError as io:
    print("[ERROR] labels_root is not exist")
    sys.exit(1)


class LabelTool():
    def __init__(self, master):
        # set up the main frame
        self.parent = master
        self.parent.protocol("WM_DELETE_WINDOW", self.on_close)

        self.parent.title("Annotation Tool - text")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width = False, height = False)

        # initialize global state
        self.imageDir = ''
        self.cur = 0
        self.total = 0
        self.tkimg = None
        self.annData = []

        self.left_state = 0
        self.right_state = 0
        self.cur_labelId = -1
        self.cur_objId = -1
        self.tmp_x = 0
        self.tmp_y = 0

        # reference to bbox
        self.hl = None
        self.vl = None
        self.bboxIdList = []
        self.bboxId = None
        self.textIdList = []
        self.textId = None
        self.textBboxIdList = []
        self.textBboxId = None

        # ----------------- GUI stuff ---------------------
        # dir entry & load
        self.label = Label(self.frame, text = "Image Dir:")
        self.label.grid(row = 0, column = 0, sticky = E)
        self.entry = Entry(self.frame)
        self.entry.grid(row = 0, column = 1, sticky = W+E)
        self.explBtn = Button(self.frame, text = "Browser", command = self.loadData)
        self.explBtn.grid(row = 0, column = 2, sticky = W+S+E,columnspan=2)

        # main panel for labeling
        self.mainPanel = Canvas(self.frame, cursor='tcross')

        # <Button-2> Mac-->mouse right; Window-->mouse wheel
        # <Button-3> Mac-->mouse wheel right; Window-->mouse right
        if platform.system() == 'Windows':
            # windows
            self.mainPanel.bind("<Button-1>", self.mouseLeftClick)
            self.mainPanel.bind("<Button-3>", self.mouseRightClick)
            # self.mainPanel.bind("<Button-2>", self.mouseWheelClick)
            self.mainPanel.bind("<B1-Motion>", self.mouseLeftPressMove)
        else:
            # mac
            self.mainPanel.bind("<Button-1>", self.mouseLeftClick)
            self.mainPanel.bind("<Button-2>", self.mouseRightClick)
            # self.mainPanel.bind("<Button-3>", self.mouseWheelClick)
            self.mainPanel.bind("<B1-Motion>", self.mouseLeftPressMove)
        
        self.mainPanel.bind("<Motion>", self.mouseMove)
        
        self.parent.bind("<Escape>", self.cancelBBox)  # press <Espace> to cancel current bbox
        self.parent.bind("c", self.cancelBBox) # press 'c' to cancel current bbox
        self.parent.bind("a", self.prevImage) # press 'a' to go backforward
        self.parent.bind("d", self.nextImage) # press 'd' to go forward
        self.parent.bind("e", self.editAnnotation) # press 'e' to edit annotation
        self.parent.bind("r", self.removeAnnotation) # press 'r' to remove annotation


        self.mainPanel.grid(row = 1, column = 1, rowspan = 7, sticky = W+N)
        
        self.lb1 = Label(self.frame, text = 'Bounding boxes:')
        self.lb1.grid(row = 2, column = 2,  sticky = W+N,columnspan=2)
        
        
        self.listbox = Listbox(self.frame, width = 30, height = 12, exportselection=False)
        self.listbox.grid(row = 3, column = 2, sticky = N,columnspan=2)
        self.listbox.bind('<<ListboxSelect>>',self.listboxSelect)
     
        self.btnDel = Button(self.frame, text = 'Delete', command = self.btnDel_lisenter)
        self.btnDel.grid(row = 4, column = 2, sticky = W+E+N,columnspan=2)
        self.btnClear = Button(self.frame, text = 'ClearAll', command = self.clearALL)
        self.btnClear.grid(row = 5, column = 2, sticky = W+E+N,columnspan=2)

        #
        self.btnSave = Button(self.frame, text = 'Save', command = self.saveData)
        self.btnSave.grid(row = 6, column = 2, sticky = W+E+N,columnspan=2)

        # control panel for image navigation
        self.ctrPanel = Frame(self.frame)
        self.ctrPanel.grid(row = 7, column = 1, columnspan = 2, sticky = W+E)
        self.filenameLabel = Label(self.ctrPanel, text = "filename")
        self.filenameLabel.pack(side = LEFT, padx = 5)
        self.prevBtn = Button(self.ctrPanel, text='<< Prev', width = 10, command = self.prevImage)
        self.prevBtn.pack(side = LEFT, padx = 5, pady = 3)
        self.nextBtn = Button(self.ctrPanel, text='Next >>', width = 10, command = self.nextImage)
        self.nextBtn.pack(side = LEFT, padx = 5, pady = 3)
        self.progLabel = Label(self.ctrPanel, text = "Progress:     /    ")
        self.progLabel.pack(side = LEFT, padx = 5)
        self.tmpLabel = Label(self.ctrPanel, text = "Go to Image No.")
        self.tmpLabel.pack(side = LEFT, padx = 5)
        self.idxEntry = Entry(self.ctrPanel, width = 5)
        self.idxEntry.pack(side = LEFT)
        self.goBtn = Button(self.ctrPanel, text = 'Go', command = self.gotoImage)
        self.goBtn.pack(side = LEFT)
        self.findBtn = Button(self.ctrPanel, text = 'Find', command = self.findNoAnnImage)
        self.findBtn.pack(side = LEFT)
        
        # display mouse position
        self.disp = Label(self.ctrPanel, text='')
        self.disp.pack(side = RIGHT)
        self.disp.config(text = 'x: 000, y: 000')

        #
        self.frame.columnconfigure(1, weight = 1)
        self.frame.rowconfigure(5, weight = 1)

        # pop menu (label)
        self.menu = Menu(root, tearoff=False)
        for label in all_label:
            self.menu.add_command(label=label, command=self.menu_command(label))

    # Main annotation window
    def menu_command(self, label):
        return lambda:self.menu_label_select(label)

    def menu_label_select(self, label):
        self.cur_labelId = all_label.index(label)

    def popupmenu(self, event):
        self.cur_labelId = -1
        self.menu.post(event.x_root,event.y_root)

    def loadData(self):
        directory = filedialog.askdirectory(initialdir = home)
        self.entry.delete(0, END)
        self.entry.insert(0, directory)

        try:
            self.imageDir = self.entry.get()
            self.parent.focus()
        except ValueError as ve:
            tkMessageBox.showerror("Error!", message = "The folder should be numbers")
            return

        imageFormat = ['*.jpg', '*.png', '*.jpeg']
        imageList = []
        for format in imageFormat:
            imageList += glob.glob(os.path.join(self.imageDir, format))

        if len(imageList) == 0:
            print('[Error] No .jpg(.png/.jpeg) images found in the specified dir!')
            tkMessageBox.showerror("Error!", message = "No .jpg images found in the specified dir!")
            return

        self.cur = 1
        self.total = len(imageList)
        
        if os.path.isfile(os.path.join(self.imageDir, 'annData.json')):
            with open(os.path.join(self.imageDir, 'annData.json'), 'r', encoding='utf-8') as f:
                self.annData = json.load(f)

            for i in range(len(self.annData)):
                img_width = self.annData[i]['width']
                img_height = self.annData[i]['height']

                for j in range(len(self.annData[i]['bbox'])):
                    self.annData[i]['bbox'][j] = self.deconvert(self.annData[i]['bbox'][j], img_width, img_height)

        
        if len(imageList) != len(self.annData):
            self.annData = []
            for imagepath in imageList:
                tmpDict={}
                tmpDict['file_path'] = imagepath
                tmpImg = PImage.open(imagepath)
                tmpDict['width'] = tmpImg.width
                tmpDict['height'] = tmpImg.height
                tmpDict['bbox'] = []
                tmpDict['label'] = []
                
                self.annData.append(tmpDict.copy())
        
        self.loadImage()
    
    def loadImage(self):
        imagepath = self.annData[self.cur - 1]['file_path']

        self.img = PImage.open(imagepath)
        self.img = self.img.resize((window_w, window_h))
        self.tkimg = ImageTk.PhotoImage(self.img)
        self.mainPanel.config(width = window_w, height = window_h)
        self.mainPanel.create_image(0, 0, image = self.tkimg, anchor=NW)
        self.progLabel.config(text = "%04d/%04d" %(self.cur, self.total))
        self.filenameLabel.config(text=f'filename: {os.path.basename(imagepath)}')

        for idx in range(len(self.bboxIdList)):
            self.mainPanel.delete(self.bboxIdList[idx])
            self.mainPanel.delete(self.textIdList[idx])
            self.mainPanel.delete(self.textBboxIdList[idx])

        self.listbox.delete(0, self.listbox.size())
        self.bboxIdList = []
        self.textIdList = []
        self.textBboxIdList = []
        self.right_state = 0
        self.left_state = 0

        bboxes = self.annData[self.cur - 1]['bbox']
        labels = self.annData[self.cur - 1]['label']
        for i in range(len(bboxes)):
            tmpId = self.mainPanel.create_rectangle(bboxes[i][0], bboxes[i][1], \
                                                    bboxes[i][2], bboxes[i][3], \
                                                    width = 3, \
                                                    outline = general_color)
            
            self.bboxIdList.append(tmpId)
            self.listbox.insert(END, '(%s)-->(%d, %d, %d, %d)' %(all_label[labels[i]], bboxes[i][0], bboxes[i][1], bboxes[i][2], bboxes[i][3]))
            self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = general_color)
            
            # label text
            tmpTextId = self.mainPanel.create_text(bboxes[i][0], bboxes[i][1], text=all_label[labels[i]], anchor='sw', font=('Times', 18))
            tmpTextBboxId = self.mainPanel.create_rectangle(self.mainPanel.bbox(tmpTextId), fill = general_color, outline =general_color)
            self.mainPanel.tag_lower(tmpTextBboxId, tmpTextId)
            
            self.textIdList.append(tmpTextId)
            self.textBboxIdList.append(tmpTextBboxId)

    def cursorInBbox(self, event):

        self.cur_objId = -1
        bboxes = self.annData[self.cur - 1]['bbox']
        bboxArea = {i: (bboxes[i][2]-bboxes[i][0])*(bboxes[i][3]-bboxes[i][1]) for i in range(len(bboxes))}
        bboxArea = dict(sorted(bboxArea.items(), key= lambda item: item[1]))

        for key in bboxArea.keys():
            tlx, tly, brx, bry = bboxes[key]
            if tlx<event.x and event.x<brx and tly<event.y and event.y<bry:
                self.cur_objId = key
                break

    def draw(self, x=None, y=None):
        if x != None and y != None:
            if self.cur_labelId != -1:
                
                if self.bboxId:
                    self.mainPanel.delete(self.bboxId)
                self.bboxId = self.mainPanel.create_rectangle(self.tmp_x, self.tmp_y, x, y, width = 3, outline = general_color)
                
                if self.textId:
                    self.mainPanel.delete(self.textId)
                self.textId = self.mainPanel.create_text(min(self.tmp_x, x), min(self.tmp_y, y), text=all_label[self.cur_labelId], anchor='sw', font=('Times', 18))
                
                if self.textBboxId:
                    self.mainPanel.delete(self.textBboxId)
                self.textBboxId = self.mainPanel.create_rectangle(self.mainPanel.bbox(self.textId), fill = general_color, outline =general_color)
                
                self.mainPanel.tag_lower(self.textBboxId, self.textId)
        else:
            if self.listbox.size() > 0:
                self.listbox.select_clear(0, 'end')
            
                bboxes = self.annData[self.cur - 1]['bbox']
                labels = self.annData[self.cur - 1]['label']
                for i in range(len(bboxes)):
                    tlx, tly, brx, bry = bboxes[i]
                    self.mainPanel.delete(self.bboxIdList[i])
                    self.mainPanel.delete(self.textBboxIdList[i])
                    self.mainPanel.delete(self.textIdList[i])
                    if i == self.cur_objId:
                        self.bboxIdList[i] = self.mainPanel.create_rectangle(tlx, tly, \
                                                                    brx, bry, \
                                                                    width = 3, \
                                                                    outline = selected_color, \
                                                                    dash=(5,5))
                        
                        self.textIdList[i] = self.mainPanel.create_text(bboxes[i][0], bboxes[i][1], text=all_label[labels[i]], anchor='sw', font=('Times', 18))
                        self.textBboxIdList[i] = self.mainPanel.create_rectangle(self.mainPanel.bbox(self.textIdList[i]), fill = selected_color, outline = selected_color)
                        self.mainPanel.tag_lower(self.textBboxIdList[i], self.textIdList[i])
                        self.listbox.select_set(i)

                    else:
                        self.bboxIdList[i] = self.mainPanel.create_rectangle(tlx, tly, \
                                                                    brx, bry, \
                                                                    width = 3, \
                                                                    outline = general_color)

                        self.textIdList[i] = self.mainPanel.create_text(bboxes[i][0], bboxes[i][1], text=all_label[labels[i]], anchor='sw', font=('Times', 18))
                        self.textBboxIdList[i] = self.mainPanel.create_rectangle(self.mainPanel.bbox(self.textIdList[i]), fill = general_color, outline = general_color)
                        self.mainPanel.tag_lower(self.textBboxIdList[i], self.textIdList[i])            
            
    def listboxSelect(self, event):
        box_select = self.listbox.curselection()
        self.cur_objId = -1
        if len(box_select) > 0:
            self.cur_objId = box_select[0]
            self.right_state = 1
            self.draw()

    def mouseLeftPressMove(self, event):
        self.disp.config(text = 'x: %.3d, y: %.3d' %(event.x, event.y))

        tmp_width = self.tkimg.width() if self.tkimg else window_w
        tmp_height = self.tkimg.height() if self.tkimg else window_h

        if self.hl:
            self.mainPanel.delete(self.hl)
        self.hl = self.mainPanel.create_line(0, event.y, tmp_width, event.y, width = 3, fill='black')
        if self.vl:
            self.mainPanel.delete(self.vl)
        self.vl = self.mainPanel.create_line(event.x, 0, event.x, tmp_height, width = 3, fill='black')


        if self.right_state == 1:            
            if self.cur_objId != -1:
                bboxes = self.annData[self.cur - 1]['bbox']

                tlx, tly, brx, bry = bboxes[self.cur_objId]
                minIndex = -1
                minValue = 0
                tmpPoint=[[tlx, tly], [brx, tly], [brx, bry], [tlx, bry]]
                for i in range(len(tmpPoint)):
                    dif_value = math.sqrt(pow(event.x - tmpPoint[i][0], 2) + pow(event.y - tmpPoint[i][1], 2))
                    if i == 0 or dif_value < minValue:
                       minIndex = i
                       minValue = dif_value
                
                if minIndex == 0:
                    tlx = event.x
                    tly = event.y
                elif minIndex == 1:
                    brx = event.x
                    tly = event.y
                elif minIndex == 2:
                    brx = event.x
                    bry = event.y
                elif minIndex == 3:
                    tlx = event.x
                    bry = event.y

                self.annData[self.cur - 1]['bbox'][self.cur_objId]=[tlx, tly, brx, bry]
                self.draw()

    def mouseRightClick(self, event):
        if len(self.annData) == 0 :
            return
        
        self.cursorInBbox(event)
        if self.cur_objId != -1:
            self.right_state = 1
        else:
            self.right_state = 0    

        self.draw()
        
    def mouseLeftClick(self, event):
        if self.right_state >= 1 or len(self.annData) == 0:
            return

        if self.left_state == 0:
            
            self.tmp_x, self.tmp_y = event.x, event.y
            self.popupmenu(event)
            self.left_state = 1
        else:
            if self.cur_labelId == -1:
                
                self.tmp_x, self.tmp_y = event.x, event.y
                self.popupmenu(event)
                self.left_state = 1
            else:
                
                x1, x2 = min(self.tmp_x, event.x), max(self.tmp_x, event.x)
                y1, y2 = min(self.tmp_y, event.y), max(self.tmp_y, event.y)
                self.left_state = 0

                self.annData[self.cur - 1]['bbox'].append((x1, y1, x2, y2))
                self.annData[self.cur - 1]['label'].append(self.cur_labelId)

                self.bboxIdList.append(self.bboxId)
                self.bboxId = None
                self.textIdList.append(self.textId)
                self.textId = None
                self.textBboxIdList.append(self.textBboxId)
                self.textBboxId = None
                
                self.listbox.insert(END, '(%s)-->(%d, %d, %d, %d)' %(all_label[self.cur_labelId], x1, y1, x2, y2))
                self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = general_color)

                self.cur_labelId = -1
                self.cur_objId = -1
                
                


    def mouseMove(self, event):
        self.disp.config(text = 'x: %.3d, y: %.3d' %(event.x, event.y))

        tmp_width = self.tkimg.width() if self.tkimg else window_w
        tmp_height = self.tkimg.height() if self.tkimg else window_h

        if self.hl:
            self.mainPanel.delete(self.hl)
        self.hl = self.mainPanel.create_line(0, event.y, tmp_width, event.y, width = 3, fill='black')
        if self.vl:
            self.mainPanel.delete(self.vl)
        self.vl = self.mainPanel.create_line(event.x, 0, event.x, tmp_height, width = 3, fill='black')

        self.draw(event.x, event.y)
            
    def cancelBBox(self, event):
        self.resetDrawing()

    def resetDrawing(self):
        if self.bboxId:
            self.mainPanel.delete(self.bboxId)
            self.bboxId = None
        if self.textId:
            self.mainPanel.delete(self.textId)
            self.textId = None
        if self.textBboxId:
            self.mainPanel.delete(self.textBboxId)
            self.textBboxId = None
        
        self.cur_labelId = -1
        self.cur_objId = -1
        self.left_state = 0
        self.right_state = 0
        self.tmp_x = 0
        self.tmp_y = 0

    def delBBox(self, delId):
        self.mainPanel.delete(self.bboxIdList[delId])
        self.bboxIdList.pop(delId)
        self.annData[self.cur - 1]['bbox'].pop(delId)
        self.annData[self.cur - 1]['label'].pop(delId)
        self.listbox.delete(delId)
        self.mainPanel.delete(self.textIdList[delId])
        self.textIdList.pop(delId)
        self.mainPanel.delete(self.textBboxIdList[delId])
        self.textBboxIdList.pop(delId)
        
        self.cur_objId = -1
        self.right_state = 0
        self.left_state = 0
        

    def btnDel_lisenter(self):
        
        sel = self.listbox.curselection() 
        if len(sel) != 1 :
            return
        
        idx = int(sel[0])
        self.delBBox(idx)
        

    def clearALL(self):

        if len(self.annData) == 0:
            return
        
        for idx in range(len(self.bboxIdList)):
            self.mainPanel.delete(self.bboxIdList[idx])
            self.mainPanel.delete(self.textIdList[idx])
            self.mainPanel.delete(self.textBboxIdList[idx])

        self.listbox.delete(0, len(self.annData[self.cur - 1]['bbox']))
        self.bboxIdList = []
        self.annData[self.cur - 1]['bbox'] = []
        self.annData[self.cur - 1]['label'] = []
        self.textIdList = []
        self.textBboxIdList = []
        self.left_state = 0
        self.right_state = 0
        self.cur_labelId = -1
        self.cur_objId = -1
        self.tmp_x = 0
        self.tmp_y = 0

    def prevImage(self, event = None):
        if self.cur > 1:
            self.cur -= 1
            self.loadImage()
        else:
            tkMessageBox.showinfo("Information!", message = "This is first image")

    def nextImage(self, event = None):
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()
        else:
            tkMessageBox.showinfo("Information!", message = "All images annotated")

    def editAnnotation(self, event):
        if self.right_state == 1 and self.cur_objId != -1:
            tmp_box = self.annData[self.cur - 1]['bbox'][self.cur_objId]
            self.textWindowHandler(tmp_box[0], tmp_box[1], tmp_box[2], tmp_box[3], self.cur_objId)
    
    def removeAnnotation(self, event):
        if self.right_state == 1 and self.cur_objId != - 1:
            self.delBBox(self.cur_objId)

    def gotoImage(self):
        if self.idxEntry.get() != '':
            idx = int(self.idxEntry.get())
            if 1 <= idx and idx <= self.total:
                self.cur = idx
                self.loadImage()

    def findNoAnnImage(self):
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

    def on_close(self):
        self.saveData()
        self.parent.destroy()


    # File process
    def convert(self, annBbox, img_w, img_h):
        tlx = int(annBbox[0] * 1. * img_w / window_w)
        tly = int(annBbox[1] * 1. * img_h / window_h)
        brx = int(annBbox[2] * 1. * img_w / window_w)
        bry = int(annBbox[3] * 1. * img_h / window_h)

        return [min(tlx, brx), min(tly, bry), max(tlx, brx), max(tly, bry)]
    
    def deconvert(self, annBbox, img_w, img_h):
        tlx = int(annBbox[0] * 1. * window_w / img_w)
        tly = int(annBbox[1] * 1. * window_h / img_h)
        brx = int(annBbox[2] * 1. * window_w / img_w)
        bry = int(annBbox[3] * 1. * window_h / img_h)

        return [min(tlx, brx), min(tly, bry), max(tlx, brx), max(tly, bry)]
    
    def saveData(self):
        if len(self.annData) == 0:
            return

        # save annData
        tmpOutput = copy.deepcopy(self.annData)
        for i in range(len(tmpOutput)):
            img_width = tmpOutput[i]['width']
            img_height = tmpOutput[i]['height']
            for j in range(len(tmpOutput[i]['bbox'])):
                tmpOutput[i]['bbox'][j] = self.convert(tmpOutput[i]['bbox'][j], img_width, img_height)
        
        with open(os.path.join(self.imageDir, 'annData.json'), 'w', encoding='utf-8') as f:
            f.write(json.dumps(tmpOutput, indent=2))

        tkMessageBox.showinfo("Information!", message = "Save all annotations")


if __name__ == '__main__':
    root = Tk()
    tool = LabelTool(root)
    # root.resizable(width = False, height = True)
    root.mainloop()
