#-------------------------------------------------------------------------------
# Name:        Object bounding box label tool
# Purpose:     Label object bboxes for ImageNet Detection data
# Author:      Qiushi
# Created:     06/06/2014

#
#-------------------------------------------------------------------------------
from __future__ import division
from PIL import Image as PImage, ImageTk
import os
import sys
import glob
import random
from os import getenv
from collections import OrderedDict

if(sys.version_info[0] == 2):
    from Tkinter import *
    import tkMessageBox
elif(sys.version_info[0] == 3):
    from tkinter import *
    from tkinter import messagebox as tkMessageBox
    from tkinter import filedialog

MAIN_COLORS = ['red','blue','black','yellow','green','darkolivegreen', 'darkseagreen', 'darkorange', 'darkslategrey', 'darkturquoise', 'darkgreen', 'darkviolet', 'darkgray', 'darkmagenta', 'darkblue', 'darkkhaki','darkcyan', 'darkred',  'darksalmon', 'darkslategray', 'darkgoldenrod', 'darkgrey', 'darkslateblue', 'darkorchid','skyblue','orange','pink','violet','brown','gold','Olive','Maroon', 'cyan','olivedrab', 'lightcyan', 'silver']
print(type(MAIN_COLORS))
home  = getenv("HOME")
# image sizes for the examples
window_w = 1280
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
COLORS = MAIN_COLORS#set(MAIN_COLORS)#, len(classes)


class LabelTool():
    def __init__(self, master):
        # set up the main frame
        self.curimg_h = 0
        self.curimg_w = 0
        self.cur_cls_id = -1
        self.parent = master
        self.parent.title("Yolo Annotation Tool")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width = FALSE, height = FALSE)

        # initialize global state
        self.imageDir = ''
        self.imageList= []
        self.egDir = ''
        self.egList = []
        self.outDir = ''
        self.cur = 0
        self.total = 0
        self.category = 0
        self.imagename = ''
        self.labelfilename = ''
        self.tkimg = None

        # initialize mouse state
        self.STATE = {}
        self.STATE['click'] = 0 # 0->click 1->select a class 2->last click
        self.STATE['x'], self.STATE['y'] = 0, 0

        # reference to bbox
        self.bboxIdList = []
        self.bboxId = None
        self.bboxList = []
        self.bboxListCls = []
        self.hl = None
        self.vl = None

        # ----------------- GUI stuff ---------------------
        # dir entry & load
        self.label = Label(self.frame, text = "Image Dir:")
        self.label.grid(row = 0, column = 0, sticky = E)
        self.entry = Entry(self.frame)
        self.entry.grid(row = 0, column = 1, sticky = W+E)
        self.explBtn = Button(self.frame,  
                        text = "b", 
                        command = self.dispPath)
        self.explBtn.grid(row = 0, column = 2, sticky = W+S+E)

        # main panel for labeling
        self.mainPanel = Canvas(self.frame, cursor='tcross')
        self.mainPanel.bind("<Button-1>", self.mouseClick)
        self.mainPanel.bind("<Motion>", self.mouseMove)
        self.parent.bind("<Escape>", self.cancelBBox)  # press <Espace> to cancel current bbox
        self.parent.bind("c", self.cancelBBox)
        self.parent.bind("a", self.prevImage) # press 'a' to go backforward
        self.parent.bind("d", self.nextImage) # press 'd' to go forward
        self.mainPanel.grid(row = 1, column = 1, rowspan = 6, sticky = W+N)
        
        self.lb1 = Label(self.frame, text = 'Bounding boxes:')
        self.lb1.grid(row = 2, column = 2,  sticky = W+N,columnspan=2)
        
        
        self.listbox = Listbox(self.frame, width = 30, height = 12)
        self.listbox.grid(row = 3, column = 2, sticky = N,columnspan=2)

        self.btnDel = Button(self.frame, text = 'Delete', command = self.delBBox)
        self.btnDel.grid(row = 4, column = 2, sticky = W+E+N,columnspan=2)
        self.btnClear = Button(self.frame, text = 'ClearAll', command = self.clearBBox)
        self.btnClear.grid(row = 5, column = 2, sticky = W+E+N,columnspan=2)

        # control panel for image navigation
        self.ctrPanel = Frame(self.frame)
        self.ctrPanel.grid(row = 6, column = 1, columnspan = 2, sticky = W+E)
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
        # example pannel for illustration
        self.egPanel = Frame(self.frame, border = 10)
        self.egPanel.grid(row = 1, column = 0, rowspan = 5, sticky = N)
        self.tmpLabel2 = Label(self.egPanel, text = "Examples:")
        self.tmpLabel2.pack(side = TOP, pady = 5)
        self.egLabels = []
        for i in range(3):
            self.egLabels.append(Label(self.egPanel))
            self.egLabels[-1].pack(side = TOP)

        # display mouse position
        self.disp = Label(self.ctrPanel, text='')
        self.disp.pack(side = RIGHT)
        self.disp.config(text = 'x: 000, y: 000')

        self.frame.columnconfigure(1, weight = 1)
        self.frame.rowconfigure(4, weight = 1)

        self.menu = Menu(root, tearoff=False)
        
        for cla in classes:
            self.menu.add_command(label=cla, command=self.menu_command(cla))

    def menu_command(self, cla):
        return lambda:self.menu_label_select(cla)

    def menu_label_select(self, label):
        # if self.STATE['click'] == 1:
        ind = classes.index(label)
        self.cur_cls_id = ind
        self.STATE['click'] = 2

    def popupmenu(self, event):
        self.menu.post(event.x_root,event.y_root)

    def dispPath(self):
        directory = filedialog.askdirectory(initialdir = home)
        self.entry.delete(0,END)
        self.entry.insert(0,directory)
        self.loadDir()
    
    def loadDir(self, dbg = False):
        if not dbg:
            try:
                s = self.entry.get()
                print(s)
                self.parent.focus()
                self.category = s
                # directory = filedialog.askdirectory(initialdir = home)
            except ValueError as ve:
                tkMessageBox.showerror("Error!", message = "The folder should be numbers")
                return
        if not os.path.isdir('%s' % self.category):
           tkMessageBox.showerror("Error!", message = "The specified dir doesn't exist!")
           return
        # get image list
        self.imageDir = os.path.join(r'./Images', '%s' %(self.category))
        self.imageList = glob.glob(os.path.join(self.imageDir, '*.jpg'))
        if len(self.imageList) == 0:
            print('No .jpg images found in the specified dir!')
            tkMessageBox.showerror("Error!", message = "No .jpg images found in the specified dir!")
            return

        # default to the 1st image in the collection
        self.cur = 1
        self.total = len(self.imageList)

        # set up output dir
        if not os.path.exists('./Labels'):
            os.mkdir('./Labels')
        self.outDir = os.path.join(r'./Labels', '%s' %(self.category))
        if not os.path.exists(self.outDir):
            os.mkdir(self.outDir)
        self.loadImage()
        print('%d images loaded from %s' %(self.total, s))

    def loadImage(self):
        # load image
        imagepath = self.imageList[self.cur - 1]
        self.img = PImage.open(imagepath)
        self.img = self.img.resize((window_w, window_h))
        self.curimg_w, self.curimg_h = self.img.size
        self.tkimg = ImageTk.PhotoImage(self.img)
        self.mainPanel.config(width = max(self.tkimg.width(), window_w), height = max(self.tkimg.height(), window_h))
        self.mainPanel.create_image(0, 0, image = self.tkimg, anchor=NW)
        self.progLabel.config(text = "%04d/%04d" %(self.cur, self.total))

        # load labels
        self.clearBBox()
        # self.imagename = os.path.split(imagepath)[-1].split('.')[0]
        self.imagename = os.path.splitext(os.path.basename(imagepath))[0]
        labelname = self.imagename + '.txt'
        self.labelfilename = os.path.join(self.outDir, labelname)
        if os.path.exists(self.labelfilename):
            with open(self.labelfilename) as f:
                for (i, line) in enumerate(f):
                    yolo_data = line.strip().split()
                    # print(yolo_data)
                    tmp = self.deconvert(yolo_data[1:])
                    self.bboxList.append(tuple(tmp))
                    self.bboxListCls.append(yolo_data[0])
                    tmpId = self.mainPanel.create_rectangle(tmp[0], tmp[1], \
                                                            tmp[2], tmp[3], \
                                                            width = 2, \
                                                            outline = COLORS[int(yolo_data[0])])
                    
                    self.bboxIdList.append(tmpId)
                    self.listbox.insert(END, '(%d, %d) -> (%d, %d) -> (%s)' %(tmp[0], tmp[1], tmp[2], tmp[3], classes[int(yolo_data[0])]))
                    self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[int(yolo_data[0])])
        
    def saveImage(self):
        with open(self.labelfilename, 'w') as f:
            for bbox,bboxcls in zip(self.bboxList,self.bboxListCls):
                xmin,ymin,xmax,ymax = bbox
                b = (float(xmin), float(xmax), float(ymin), float(ymax))
                bb = self.convert((self.curimg_w,self.curimg_h), b)
                f.write(str(bboxcls) + " " + " ".join([str(a) for a in bb]) + '\n')
        print('Image No. %d saved' %(self.cur))

    def cursorInBox(self, x, y):
        boxIndex = -1

        for box in self.bboxList:
            tlx, tly, brx, bry = box

            if tlx<x and x<brx and tly<y and y<bry:
                boxIndex =self.bboxList.index(box)
                break
        
        return boxIndex
    
    def mouseClick(self, event):
        print(f'state: {self.STATE["click"]}')
        # if self.STATE['click'] == 0:
        
        boxIndex = self.cursorInBox(event.x, event.y)
        print(f'boxIndex: {boxIndex}')
        if self.STATE['click'] == 0:
            for i in range(len(self.bboxList)):
                tlx, tly, brx, bry = self.bboxList[i]
                self.mainPanel.delete(self.bboxIdList[i])
                if i == boxIndex:
                    self.bboxIdList[i] = self.mainPanel.create_rectangle(tlx, tly,
                                                                brx, bry,
                                                                width = 2,
                                                                outline = COLORS[self.bboxListCls[i]],
                                                                dash=(4,4))
                else:
                    self.bboxIdList[i] = self.mainPanel.create_rectangle(tlx, tly,
                                                                brx, bry,
                                                                width = 2,
                                                                outline = COLORS[self.bboxListCls[i]]
                                                                )
        if self.STATE['click'] == 0 and boxIndex == -1:
            self.STATE['x'], self.STATE['y'] = event.x, event.y
            self.popupmenu(event)
            # self.STATE['click'] = 1

        elif self.STATE['click'] == 2:
            x1, x2 = min(self.STATE['x'], event.x), max(self.STATE['x'], event.x)
            y1, y2 = min(self.STATE['y'], event.y), max(self.STATE['y'], event.y)
            self.bboxList.append((x1, y1, x2, y2))
            self.bboxListCls.append(self.cur_cls_id)
            self.bboxIdList.append(self.bboxId)
            self.bboxId = None
            self.listbox.insert(END, '(%d, %d) -> (%d, %d) -> (%s)' %(x1, y1, x2, y2, classes[self.cur_cls_id]))
            self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[self.cur_cls_id])
        
            self.STATE['click'] = 0

    # def mouseClick(self, event):
    #     print(f'state: {self.STATE["click"]}')
    #     # if self.STATE['click'] == 0:
        
    #     boxIndex = self.cursorInBox(event.x, event.y)
    #     print(f'boxIndex: {boxIndex}')
    #     if boxIndex != -1:
    #         self.mainPanel.delete(self.bboxIdList[boxIndex])
    #         del self.bboxIdList[boxIndex]
    #         tlx, tly, brx, bry = self.bboxList[boxIndex]

    #         self.bboxId = self.mainPanel.create_rectangle(tlx, tly,
    #                                                         brx, bry,
    #                                                         width = 2,
    #                                                         outline = COLORS[self.bboxListCls[boxIndex]],
    #                                                         dash=(4,4))
            
    #         self.bboxIdList.insert(boxIndex, self.bboxId)
    #         self.bboxId = None
    #     else:
    #         for i in range(len(self.bboxList)):
    #             tlx, tly, brx, bry = self.bboxList[i]
    #             self.mainPanel.delete(self.bboxIdList[i])
    #             self.bboxIdList[i] = self.mainPanel.create_rectangle(tlx, tly,
    #                                                         brx, bry,
    #                                                         width = 2,
    #                                                         outline = COLORS[self.bboxListCls[i]])

    #         if self.STATE['click'] == 0:
    #             self.STATE['x'], self.STATE['y'] = event.x, event.y
    #             self.popupmenu(event)
    #             # self.STATE['click'] = 1

    #         elif self.STATE['click'] == 2:
    #             x1, x2 = min(self.STATE['x'], event.x), max(self.STATE['x'], event.x)
    #             y1, y2 = min(self.STATE['y'], event.y), max(self.STATE['y'], event.y)
    #             self.bboxList.append((x1, y1, x2, y2))
    #             self.bboxListCls.append(self.cur_cls_id)
    #             self.bboxIdList.append(self.bboxId)
    #             self.bboxId = None
    #             self.listbox.insert(END, '(%d, %d) -> (%d, %d) -> (%s)' %(x1, y1, x2, y2, classes[self.cur_cls_id]))
    #             self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[self.cur_cls_id])
            
    #             self.STATE['click'] = 0

    def mouseMove(self, event):
        self.disp.config(text = 'x: %.3d, y: %.3d' %(event.x, event.y))
        
        if 2 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
            self.bboxId = self.mainPanel.create_rectangle(self.STATE['x'], self.STATE['y'], \
                                                            event.x, event.y, \
                                                            width = 2, \
                                                            outline = COLORS[self.cur_cls_id])

    def cancelBBox(self, event):
        if 2 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
                self.bboxId = None
                self.STATE['click'] = 0

    def delBBox(self):
        sel = self.listbox.curselection()
        

        if len(sel) != 1 :
            return
        idx = int(sel[0])
        self.mainPanel.delete(self.bboxIdList[idx])
        self.bboxIdList.pop(idx)
        self.bboxList.pop(idx)
        print(self.bboxListCls,idx)
        self.bboxListCls.pop(idx)
        self.listbox.delete(idx)

    def clearBBox(self):
        for idx in range(len(self.bboxIdList)):
            self.mainPanel.delete(self.bboxIdList[idx])
        self.listbox.delete(0, len(self.bboxList))
        self.bboxIdList = []
        self.bboxList = []
        self.bboxListCls = []

    def prevImage(self, event = None):
        self.saveImage()
        if self.cur > 1:
            self.cur -= 1
            self.loadImage()
        else:
            tkMessageBox.showerror("Information!", message = "This is first image")

    def nextImage(self, event = None):
        self.saveImage()
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()
        else:
            tkMessageBox.showerror("Information!", message = "All images annotated")

    def gotoImage(self):
        idx = int(self.idxEntry.get())
        if 1 <= idx and idx <= self.total:
            self.saveImage()
            self.cur = idx
            self.loadImage()

    def convert(self,size, box):
        dw = 1./size[0]
        dh = 1./size[1]
        x = (box[0] + box[1])/2.0
        y = (box[2] + box[3])/2.0
        w = box[1] - box[0]
        h = box[3] - box[2]
        x = x*dw
        w = w*dw
        y = y*dh
        h = h*dh
        return (x,y,w,h)
    
    def deconvert(self,annbox):
        ox = float(annbox[0])
        oy = float(annbox[1])
        ow = float(annbox[2])
        oh = float(annbox[3])
        x = ox*self.curimg_w
        y = oy*self.curimg_h
        w = ow*self.curimg_w
        h = oh*self.curimg_h
        xmax = (((2*x)+w)/2)
        xmin = xmax-w
        ymax = (((2*y)+h)/2)
        ymin = ymax-h
        return [int(xmin),int(ymin),int(xmax),int(ymax)]

if __name__ == '__main__':
    root = Tk()
    tool = LabelTool(root)
    root.resizable(width = False, height = False)
    root.mainloop()
