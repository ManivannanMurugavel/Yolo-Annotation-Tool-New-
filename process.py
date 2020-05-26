import glob
import os
import argparse


ap = argparse.ArgumentParser()
ap.add_argument("-a", "--annotation", type=str, default="annotated-files",
	help="path to input image")
ap.add_argument("-p", "--percentage", type=int, default=10,
	help="path to input EAST text detector")
args = ap.parse_args()

annotation_dir = args.annotation
percentage = args.percentage

print(annotation_dir,percentage)

root_dir = os.getcwd()
current_dir=annotation_dir
# Percentage of images to be used for the test set
percentage_test = percentage
# Create and/or truncate train.txt and test.txt
file_train = open('train.txt', 'w')
file_test = open('test.txt', 'w')
# Populate train.txt and test.txt
counter = 1
index_test = round(100 / percentage_test)
for pathAndFilename in glob.iglob(os.path.join(current_dir, "*.jpg")):
    title, ext = os.path.splitext(os.path.basename(pathAndFilename))
    if counter == index_test:
        counter = 1
        file_test.write(root_dir + "/" + current_dir + "/" + title + '.jpg' + "\n")
    else:
        file_train.write(root_dir + "/" + current_dir + "/" + title + '.jpg' + "\n")
        counter = counter + 1