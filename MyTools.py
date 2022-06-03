from MyDataStructure import *
from typing import List
import json
import sys
import os

def loadTxtFile(path) -> List[str]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = f.readlines()
        data = [d.strip() for d in data]
        return data

    except IOError as io:
        print("[ERROR] txt file is not exist")
        sys.exit(1)

def loadJsonFile(path) -> dict:
    assert os.path.isfile(path)

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data

def saveToJS(path:str, data, indent:int=2, override:bool=False)->None:
    '''
    save data to json file

    param path: output file path
    param data: json format data
    param indent:
    param override: override the existion file
    '''

    assert type(indent) == int
    assert type(override) == bool

    if os.path.isfile(path) and not override:
        print(f'The file exists.')
        return
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, indent=indent))

def convert(box:MyBox, fromWidth, toWidth, fromHeight, toHeight) -> MyBox:
    
    tl = MyPoint(int(box.tl.x*1.0*toWidth/fromWidth), int(box.tl.y*1.0*toHeight/fromHeight))
    tr = MyPoint(int(box.tr.x*1.0*toWidth/fromWidth), int(box.tr.y*1.0*toHeight/fromHeight))
    br = MyPoint(int(box.br.x*1.0*toWidth/fromWidth), int(box.br.y*1.0*toHeight/fromHeight))
    bl = MyPoint(int(box.bl.x*1.0*toWidth/fromWidth), int(box.bl.y*1.0*toHeight/fromHeight))
    
    tl = checkPoint(tl, MyPoint(0,0), MyPoint(toWidth, toHeight))
    tr = checkPoint(tr, MyPoint(0,0), MyPoint(toWidth, toHeight))
    br = checkPoint(br, MyPoint(0,0), MyPoint(toWidth, toHeight))
    bl = checkPoint(bl, MyPoint(0,0), MyPoint(toWidth, toHeight))

    return MyBox(tl=tl, tr=tr, br=br, bl=bl)

def checkPoint(point:MyPoint, minValue:MyPoint, maxValue:MyPoint) -> MyPoint:
    assert type(point) == MyPoint
    assert type(minValue) == MyPoint
    assert type(maxValue) == MyPoint

    x = checkValue(point.x, minValue.x, maxValue.x)
    y = checkValue(point.y, minValue.y, maxValue.y)

    return MyPoint(x, y)

def checkValue(value, minValue, maxValue):
    return min(max(value, minValue), maxValue-1)