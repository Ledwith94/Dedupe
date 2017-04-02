import argparse

import datetime
from pymongo import MongoClient
import subprocess
import unicodedata


class Main:
    def __init__(self):
        self.memory = 0.0
        self.insert_list = []
        self.final_block = 0
        self.block_tuple = []
        self.slack_space = []
        self.all_files = {}
        self.file_tuple = []
        self.total_files = 0
        self.startTime = datetime.datetime.now()


    def construct(self, acquisition):
        name = None
        memory = 0.0
        all_files = {}
        file_tuple = []
        final_block = 0
        client = MongoClient()
        db = client['Acquisition']
        files = db.files
        obj = files.find_one({"Name": acquisition})
        inode = None
        path = None
        run = None
        for key, val in obj.items():
            if "Name" in key:
                name = str(val)
                print name
            if "Image Size" in key:
                memory = int(val)
            if "All Files" in key:
                all_files = val

        for i in all_files:
            for key, val in i.items():
                if "Start Block" in key:
                    inode = str(val)
                if "Block Length" in key:
                    x = int(val) + 1
                    run = str(x)
                if "File Path" in key:
                    path = unicodedata.normalize('NFKD', val).encode('ascii', 'ignore')
                if "Finish Block" in key:
                    if val > final_block:
                        final_block = val
                if path and inode and run is not None:
                    tup = (path + ", " + inode + ", " + run)
                    file_tuple.append(tup)
                    path = None
                    inode = None
                    run = None
        memory /= 512
        target = name + ".dmg"
        subprocess.Popen(args=['./File_Insert.sh', '%s' % str("/dev/zero"), '%s' % str(target), '%s' % str(memory - 1)])
        for x in file_tuple:
            str(all).split(", ")
            subprocess.Popen(args=['./File_Insert.sh', '%s' % str(x.split(", ")[0]), '%s' % str(target),
                                   '%s' % (str(x.split(", ")[1])), '%s' % (str(x.split(", ")[2]))])
        print datetime.datetime.now() - self.startTime


argparser = argparse.ArgumentParser(
    description='Hash files recursively from a forensic image and optionally extract them')
argparser.add_argument(
    '-a', '--acquisition',
    dest='imagefile',
    action="store",
    type=str,
    default=None,
    required=True,
    help='E01 to extract from'
)
args = argparser.parse_args()

main = Main()

main.construct(args.imagefile)
