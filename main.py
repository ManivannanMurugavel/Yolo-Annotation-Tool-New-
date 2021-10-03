#-------------------------------------------------------------------------------
# Name:        Object bounding box label tool
# Purpose:     Label object bboxes for ImageNet Detection data
# Author:      Qiushi
# Created:     06/06/2014
# Editor:      shen0512
#
#-------------------------------------------------------------------------------
from __future__ import division
from PIL import Image as PImage, ImageTk
import os
import sys
import glob
import random
from os import getenv
# from collections import OrderedDict

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

classes = []

try:
    with open('classes.txt','r') as cls:
        classes = cls.readlines()
    classes = [cls.strip() for cls in classes]
except IOError as io:
    print("[ERROR] Please create classes.txt and put your all classes")
    sys.exit(1)
# COLORS = random.sample(set(MAIN_COLORS), len(classes))
COLORS = MAIN_COLORS #set(MAIN_COLORS)#, len(classes)


class LabelTool():
    def __init__(self, master):
        # set up the main frame
        self.parent = master
        self.parent.protocol("WM_DELETE_WINDOW", self.on_close)

        self.parent.title("Yolo Annotation Tool")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width = FALSE, height = FALSE)

        # initialize global state
        self.imageDir = ''
        self.imageList= []
        self.cur = 0
        self.total = 0
        self.tkimg = None
        
        self.select_box_id = -1
        self.cur_label_id = -1
        self.annData = []

        # initialize mouse state
        self.STATE = {}
        self.STATE['x'], self.STATE['y'] = 0, 0
        self.STATE['click'] = 0

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
        self.mainPanel.bind("<Button-1>", self.mouseClick)
        self.mainPanel.bind("<Button-2>", self.mouseRightClick)
        self.mainPanel.bind("<Button-3>", self.mouseWheelClick)
        self.mainPanel.bind("<Motion>", self.mouseMove)

        # self.mainPanel.configure(bg='cyan') # for test
        
        self.parent.bind("<Escape>", self.cancelBBox)  # press <Espace> to cancel current bbox
        self.parent.bind("c", self.cancelBBox) # press 'c' to cancel current bbox
        self.parent.bind("a", self.prevImage) # press 'a' to go backforward
        self.parent.bind("d", self.nextImage) # press 'd' to go forward
        self.mainPanel.grid(row = 1, column = 1, rowspan = 7, sticky = W+N)
        
        self.lb1 = Label(self.frame, text = 'Bounding boxes:')
        self.lb1.grid(row = 2, column = 2,  sticky = W+N,columnspan=2)
        
        
        self.listbox = Listbox(self.frame, width = 30, height = 12)
        self.listbox.grid(row = 3, column = 2, sticky = N,columnspan=2)
        self.listbox.bind('<<ListboxSelect>>',self.listboxSelect)
     
        self.btnDel = Button(self.frame, text = 'Delete', command = self.delBBox)
        self.btnDel.grid(row = 4, column = 2, sticky = W+E+N,columnspan=2)
        self.btnClear = Button(self.frame, text = 'ClearAll', command = self.clearBBox)
        self.btnClear.grid(row = 5, column = 2, sticky = W+E+N,columnspan=2)
        self.btnSave = Button(self.frame, text = 'Save', command = self.saveData)
        self.btnSave.grid(row = 6, column = 2, sticky = W+E+N,columnspan=2)

        # control panel for image navigation
        self.ctrPanel = Frame(self.frame)
        self.ctrPanel.grid(row = 8, column = 1, columnspan = 2, sticky = W+E)
        # self.filenameText = StringVar(self.parent) 888
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

        self.frame.columnconfigure(1, weight = 1)
        self.frame.rowconfigure(4, weight = 1)

        #
        self.menu = Menu(root, tearoff=False)
        for cla in classes:
            self.menu.add_command(label=cla, command=self.menu_command(cla))

    def menu_command(self, cla):
        return lambda:self.menu_label_select(cla)

    def menu_label_select(self, label):
        self.cur_label_id = classes.index(label)

    def popupmenu(self, event):
        self.cur_label_id = -1
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
        
        if not os.path.isdir('%s' % self.imageDir):
           tkMessageBox.showerror("Error!", message = "The specified dir doesn't exist!")
           return

        imageFormat = ['*.jpg', '*.JPG', '*.png', '*.PNG', '*.jpeg', '*.JPEG']
        for format in imageFormat:
            self.imageList += glob.glob(os.path.join(self.imageDir, format))

        if len(self.imageList) == 0:
            print('No .jpg images found in the specified dir!')
            tkMessageBox.showerror("Error!", message = "No .jpg images found in the specified dir!")
            return

        self.cur = 1
        self.total = len(self.imageList)

        # chech train file
        if os.path.isfile(os.path.join(self.imageDir, 'train.txt')):
            with open(os.path.join(self.imageDir, 'train.txt'), 'r', encoding='utf-8') as f:
                data = f.readlines()
            
            for d in data:
                d = d.replace('\n', '')
                d_splite = d.split(' ')
                tmpDict={}
                tmpDict['file_path'] = d_splite[0]
                tmpDict['width'] = -1
                tmpDict['height'] = -1
                tmpDict['bbox'] = []
                tmpDict['label'] = []
                tmpDict['isDeconvert'] = []

                for i in range(1, len(d_splite)):
                    tmpList = [int(b) for b in d_splite[i].split(',')]
                    tmpDict['bbox'].append(tmpList[0:4].copy())
                    tmpDict['label'].append(tmpList[4])
                    tmpDict['isDeconvert'].append(False)
                
                self.annData.append(tmpDict.copy())
            
            # check 
            if len(self.annData) != len(self.imageList):
                self.annData = []
                for imagepath in self.imageList:
                    tmpDict={}
                    tmpDict['file_path'] = imagepath
                    tmpDict['width'] = -1
                    tmpDict['height'] = -1
                    tmpDict['bbox'] = []
                    tmpDict['label'] = []
                    tmpDict['isDeconvert'] = []

                    self.annData.append(tmpDict.copy())
        else:
            # file not exist
            for imagepath in self.imageList:
                tmpDict={}
                tmpDict['file_path'] = imagepath
                tmpDict['width'] = -1
                tmpDict['height'] = -1
                tmpDict['bbox'] = []
                tmpDict['label'] = []
                tmpDict['isDeconvert'] = []

                self.annData.append(tmpDict.copy())
        
        self.loadImage()
    
    def loadImage(self):
        imagepath = self.annData[self.cur - 1]['file_path']

        self.img = PImage.open(imagepath)
        self.annData[self.cur - 1]['width'] = self.img.size[0]
        self.annData[self.cur - 1]['height'] = self.img.size[1]

        self.img = self.img.resize((window_w, window_h))
        self.tkimg = ImageTk.PhotoImage(self.img)
        self.mainPanel.config(width = window_w, height = window_h)
        self.mainPanel.create_image(0, 0, image = self.tkimg, anchor=NW)
        self.progLabel.config(text = "%04d/%04d" %(self.cur, self.total))
        self.filenameLabel.config(text=f'filename: {os.path.basename(imagepath)}')

        # load labels
        self.resetView()
        
        bboxes = self.annData[self.cur - 1]['bbox']
        labels = self.annData[self.cur - 1]['label']
        isDeconvert = self.annData[self.cur - 1]['isDeconvert']
        for i in range(len(bboxes)):
            if not isDeconvert[i]:
                bboxes[i] = self.deconvert(bboxes[i], self.annData[self.cur - 1]['width'], self.annData[self.cur - 1]['height'])
                isDeconvert[i] = True

            tmpId = self.mainPanel.create_rectangle(bboxes[i][0], bboxes[i][1], \
                                                    bboxes[i][2], bboxes[i][3], \
                                                    width = 3, \
                                                    outline = general_color)
            
            self.bboxIdList.append(tmpId)
            self.listbox.insert(END, '(%s): (%d, %d) -> (%d, %d)' %(classes[labels[i]], bboxes[i][0], bboxes[i][1], bboxes[i][2], bboxes[i][3]))
            self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = general_color)
            
            # label text
            tmpTextId = self.mainPanel.create_text(bboxes[i][0], bboxes[i][1], text=classes[labels[i]], anchor='nw', font=('Times', 24))
            tmpTextBboxId = self.mainPanel.create_rectangle(self.mainPanel.bbox(tmpTextId), fill = general_color, outline =general_color)
            self.mainPanel.tag_lower(tmpTextBboxId, tmpTextId)
            
            self.textIdList.append(tmpTextId)
            self.textBboxIdList.append(tmpTextBboxId)
    
    def cursorInBbox(self, event):

        self.select_box_id = -1
        
        bboxes = self.annData[self.cur - 1]['bbox']
        bboxArea = {i: (bboxes[i][2]-bboxes[i][0])*(bboxes[i][3]-bboxes[i][1]) for i in range(len(bboxes))}
        bboxArea = dict(sorted(bboxArea.items(), key= lambda item: item[1]))

        for key in bboxArea.keys():
            tlx, tly, brx, bry = bboxes[key]
            if tlx<event.x and event.x<brx and tly<event.y and event.y<bry:
                self.select_box_id = key
                break

    def drawBbox(self):
        if self.listbox.size() > 0:
            self.listbox.select_clear(0, 'end')
        
        bboxes = self.annData[self.cur - 1]['bbox']
        for i in range(len(bboxes)):
            tlx, tly, brx, bry = bboxes[i]
            self.mainPanel.delete(self.bboxIdList[i])
            self.mainPanel.delete(self.textBboxIdList[i])

            if i == self.select_box_id:
                self.bboxIdList[i] = self.mainPanel.create_rectangle(tlx, tly,
                                                            brx, bry,
                                                            width = 3,
                                                            outline = selected_color,
                                                            dash=(5,5))
                
                self.textBboxIdList[i] = self.mainPanel.create_rectangle(self.mainPanel.bbox(self.textIdList[i]), fill = selected_color, outline = selected_color)
                self.mainPanel.tag_lower(self.textBboxIdList[i], self.textIdList[i])
                self.listbox.select_set(i)
                
            
            else:
                self.bboxIdList[i] = self.mainPanel.create_rectangle(tlx, tly,
                                                            brx, bry,
                                                            width = 3,
                                                            outline = general_color
                                                            )
                
                self.textBboxIdList[i] = self.mainPanel.create_rectangle(self.mainPanel.bbox(self.textIdList[i]), fill = general_color, outline = general_color)
                self.mainPanel.tag_lower(self.textBboxIdList[i], self.textIdList[i])

    def listboxSelect(self, event):
        sel = self.listbox.curselection()
        self.select_box_id = -1
        
        if len(sel) > 0:
            self.select_box_id = sel[0]
        
            self.drawBbox()

    def mouseWheelClick(self, event):      
        if len(self.annData) == 0:
            return

        bboxes = self.annData[self.cur - 1]['bbox']
        labels = self.annData[self.cur - 1]['label']
        isDeconvert = self.annData[self.cur - 1]['isDeconvert']

        if self.select_box_id != -1:
            tlx, tly, brx, bry = bboxes[self.select_box_id]

            if tlx<event.x and event.x<brx and tly<event.y and event.y<bry:
                self.mainPanel.delete(self.bboxIdList[self.select_box_id])
                self.bboxIdList.pop(self.select_box_id)
                bboxes.pop(self.select_box_id)
                labels.pop(self.select_box_id)
                isDeconvert.pop(self.select_box_id)
                self.listbox.delete(self.select_box_id)
                self.mainPanel.delete(self.textIdList[self.select_box_id])
                self.textIdList.pop(self.select_box_id)
                self.mainPanel.delete(self.textBboxIdList[self.select_box_id])
                self.textBboxIdList.pop(self.select_box_id)

        self.select_box_id = -1
        self.drawBbox()

    def mouseRightClick(self, event):        
        if len(self.annData) == 0:
            return

        self.select_box_id = -1
        self.cursorInBbox(event)
        self.drawBbox()

    def mouseClick(self, event):
        if len(self.annData) == 0:
            return
        
        self.select_box_id = -1
        self.drawBbox()

        if self.STATE['click'] == 0:
            self.STATE['x'], self.STATE['y'] = event.x, event.y
            self.popupmenu(event)

        elif self.STATE['click'] == 1 and self.cur_label_id == -1:
            self.STATE['click'] = 0
            self.STATE['x'], self.STATE['y'] = event.x, event.y
            self.popupmenu(event)

        elif self.STATE['click'] == 1 and self.cur_label_id != -1:
            x1, x2 = min(self.STATE['x'], event.x), max(self.STATE['x'], event.x)
            y1, y2 = min(self.STATE['y'], event.y), max(self.STATE['y'], event.y)
            self.annData[self.cur - 1]['bbox'].append((x1, y1, x2, y2))
            self.annData[self.cur - 1]['isDeconvert'].append(True)
            self.annData[self.cur - 1]['label'].append(self.cur_label_id)
            self.bboxIdList.append(self.bboxId)
            self.bboxId = None
            self.textIdList.append(self.textId)
            self.textId = None
            self.textBboxIdList.append(self.textBboxId)
            self.textBboxId = None

            self.listbox.insert(END, '(%s): (%d, %d) -> (%d, %d)' %(classes[self.cur_label_id], x1, y1, x2, y2))
            self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = general_color)
            
        
        self.STATE['click'] = 1 - self.STATE['click']

    def mouseMove(self, event):
        self.disp.config(text = 'x: %.3d, y: %.3d' %(event.x, event.y))

        if self.tkimg:
            if self.hl:
                self.mainPanel.delete(self.hl)
            self.hl = self.mainPanel.create_line(0, event.y, self.tkimg.width(), event.y, width = 3, fill='black')
            if self.vl:
                self.mainPanel.delete(self.vl)
            self.vl = self.mainPanel.create_line(event.x, 0, event.x, self.tkimg.height(), width = 3, fill='black')
            
        
        if self.STATE['click'] == 1 and self.cur_label_id != -1:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
        
            self.bboxId = self.mainPanel.create_rectangle(self.STATE['x'], self.STATE['y'], \
                                                            event.x, event.y, \
                                                            width = 3, \
                                                            outline = general_color)
            if self.textId:
                self.mainPanel.delete(self.textId)
            self.textId = self.mainPanel.create_text(min(self.STATE['x'], event.x), min(self.STATE['y'], event.y), text=classes[self.cur_label_id], anchor='nw', font=('Times', 24))
            
            if self.textBboxId:
                self.mainPanel.delete(self.textBboxId)
            self.textBboxId = self.mainPanel.create_rectangle(self.mainPanel.bbox(self.textId), fill = general_color, outline =general_color)
            
            self.mainPanel.tag_lower(self.textBboxId, self.textId)
            
    def cancelBBox(self, event):
        if len(self.annData) == 0:
            return

        if self.bboxId:
            self.mainPanel.delete(self.bboxId)
            self.bboxId = None
        if self.textId:
            self.mainPanel.delete(self.textId)
            self.textId = None
        if self.textBboxId:
            self.mainPanel.delete(self.textBboxId)
            self.textBboxId = None
        
        self.select_box_id= -1
        self.drawBbox()

        self.STATE['click'] = 0

    def delBBox(self):
        sel = self.listbox.curselection()
        
        if len(sel) != 1 :
            return
        idx = int(sel[0])
        self.mainPanel.delete(self.bboxIdList[idx])
        self.bboxIdList.pop(idx)
        self.annData[self.cur - 1]['bbox'].pop(idx)
        self.annData[self.cur - 1]['label'].pop(idx)
        self.annData[self.cur - 1]['isDeconvert'].pop(idx)
        self.listbox.delete(idx)
        self.mainPanel.delete(self.textIdList[idx])
        self.textIdList.pop(idx)
        self.mainPanel.delete(self.textBboxIdList[idx])
        self.textBboxIdList.pop(idx)
    
    def resetView(self):
        for idx in range(len(self.bboxIdList)):
            self.mainPanel.delete(self.bboxIdList[idx])
            self.mainPanel.delete(self.textIdList[idx])
            self.mainPanel.delete(self.textBboxIdList[idx])

        self.listbox.delete(0, len(self.annData[self.cur - 1]['bbox']))
        self.bboxIdList = []

        self.textIdList = []
        self.textBboxIdList = []

    def clearBBox(self):
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
        self.annData[self.cur - 1]['isDeconvert'] = []
        self.textIdList = []
        self.textBboxIdList = []

        tkMessageBox.showerror("Information!", message = "Clear")

    def prevImage(self, event = None):
        if self.cur > 1:
            self.cur -= 1
            self.loadImage()
        else:
            tkMessageBox.showerror("Information!", message = "This is first image")

    def nextImage(self, event = None):
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()
        else:
            tkMessageBox.showerror("Information!", message = "All images annotated")

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
            tkMessageBox.showerror("Information!", message = "All images annotated")
        else:
            self.cur = goImageIdx
            self.loadImage()


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
        
        with open(os.path.join(self.imageDir,'train.txt'), 'w', encoding='utf-8') as f:
            for data in self.annData:
                tmpOutput = data['file_path']
                for i in range(len(data['bbox'])):
                    if data['isDeconvert'][i]:
                        bbox = self.convert(data['bbox'][i], data['width'], data['height'])
                    else:
                        bbox = data['bbox'][i].copy()

                    label = data['label'][i]

                    tmpOutput += f' {bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},{label}'

                f.write(tmpOutput)
                f.write('\n')
        
        tkMessageBox.showerror("Information!", message = "Save all annotations")

    def on_close(self):
        self.saveData()
        self.parent.destroy()


if __name__ == '__main__':
    root = Tk()
    tool = LabelTool(root)
    # root.resizable(width = False, height = True)
    root.mainloop()
