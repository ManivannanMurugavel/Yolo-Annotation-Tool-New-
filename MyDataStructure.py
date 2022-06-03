from typing import Dict, List, Tuple
from enum import Enum

class MouseStatus(Enum):
    rightPress = 1
    rightRelease = 0
    leftPress = 1
    leftRelease = 0


class MyPoint:
    def __init__(self, x, y) -> None:
        self.x = x
        self.y = y

    def __call__(self) -> tuple:
        return (self.x, self.y)

class MyBox:
    def __init__(self, tl:MyPoint, br:MyPoint, tr:MyPoint=None, bl:MyPoint=None) -> None:
        assert type(tl) == MyPoint
        assert type(br) == MyPoint
        assert type(tr) == MyPoint or tr is None
        assert type(bl) == MyPoint or bl is None

        self.tl = tl
        self.br = br
        self.tr = tr if tr is not None else MyPoint(br.x, tl.y)
        self.bl = bl if bl is not None else MyPoint(tl.x, br.y)
    
    def __call__(self) -> Tuple[MyPoint, MyPoint, MyPoint, MyPoint]:
        return (self.tl, self.tr, self.br, self.bl)
    
    def getW(self):
        return self.br.x - self.tl.x
    
    def getH(self):
        return self.br.y - self.tl.y

    def getArea(self):
        return self.getW() * self.getH()

class AnnData:
    def __init__(self, filename:str, boxes:List[MyBox], labels:List[int], text:List[str]) -> None:
        self.filename = filename
        self.boxes:List[MyBox] = boxes
        self.labels:List[int] = labels
        self.text:List[str] = text
    
    def __call__(self, box:MyBox, label:str, text:str='') -> None:
        assert type(box) == MyBox
        assert type(label) == int
        assert type(text) == str

        self.boxes.append(box)
        self.labels.append(label)
        self.text.append(text)
    
    def __repr__(self) -> str:
        # https://blog.csdn.net/zzq900503/article/details/106427009
        tmpBox = []
        for tmp in self.boxes:
            tmpBox.append((tmp.tl(), tmp.tr(), tmp.br(), tmp.bl()))
        
        return ((self.filename, tmpBox, self.labels, self.text))
    
    def convert2Output(self) -> Dict:
        tmpBox = []
        for tmp in self.boxes:
            tmpBox.append([(tmp.tl.x, tmp.tl.y), (tmp.tr.x, tmp.tr.y), (tmp.br.x, tmp.br.y), (tmp.bl.x, tmp.bl.y)])
        
        output = {}
        output['filename'] = self.filename
        output['boxes'] = tmpBox
        output['labels'] = self.labels
        output['text'] = self.text

        return output
