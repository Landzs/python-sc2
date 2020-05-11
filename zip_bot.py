# create a ZipFile object
from zipfile import ZipFile
import os


def zip_folder(dirname):
    # Iterate over all the files in directory
    for folderName, filenames in os.walk(dirname):
        for filename in filenames:
            # create complete filepath of file in directory
            filePath = os.path.join(folderName, filename)
            # Add file to zip
            zip_file.write(filePath)


with ZipFile('Fire.zip', 'w') as zip_file:
    zip_file.write("__init__.py")
    zip_file.write("ladderbots.json")
    zip_file.write("run.py")

    zip_folder(r"./sc2")
    zip_folder(r"./bot")
    zip_folder(r"./basic_manager")
