# Yolo-Annotation-Tool-New

This is new yolo annotation tool which is added new features. I have posted three blogs for how to train yolov2 and v3 using our custom images.

You can follow three steps for annotate the image to yolo.<br>
Steps:
```
run main.py
run convert.py
run process.py
```

Now i have implemented the convert.py process in main.py. So you don't run the convert.py for yolo annotating.<br>
Do steps:
```
run main.py
run process.py
```

NOTE: Images must be in .JPEG format. To convert images to this format you can use the following command(Ubuntu):<br>
`mogrify -format jpg *.JPEG` or `mogrify -format jpg *.jpeg` or `mogrify -format jpg *.png`

NOTE: If you use new annotation tool, please create classes.txt file and write all classes what you train the objects. Because i read the all classes from classes.txt.

The dataset is ready for yolo training.
