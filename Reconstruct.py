import os
from pymongo import MongoClient
import subprocess
import argparse
import unicodedata


class ImageInfo:
    def __init__(self):
        self.memory = 0.0
        self.insert_list = []
        self.final_block = 0
        self.block_tuple = []
        self.slack_space = []
        self.all_files = {}
        self.file_tuple = []
        self.total_files = 0

argparser = argparse.ArgumentParser("Specify the aquisition to reconstruct")
argparser.add_argument(
    '-a', '--acquisition',
    dest='acquisition',
    action="store",
    type=str,
    default=False,
    required=True,
    help='Specify acquisition name'
)

args = argparser.parse_args()
info = ImageInfo()
client = MongoClient()
db = client['Acquisition']
files = db.files
obj = files.find_one({"Name": args.acquisition})

inode = None
path = None
sizes = None


for key, val in obj.items():
    if "Image Size" in key:
        info.memory = int(val)
    if "Slack Space" in key:
        info.slack_space = val
    if "All Files" in key:
        info.all_files = val
    if "Total files" in key:
        info.total_files = val

for i in info.all_files:
    for key, val in i.items():
        if "Start Block" in key:
            inode = str(val)
        if "File Path" in key:
            path = unicodedata.normalize('NFKD', val).encode('ascii', 'ignore')
        if "Size" in key:
            sizes = str(val)
        if path and inode and sizes is not None:
            tup = (inode + ", " + path + ", " + sizes)
            info.file_tuple.append(tup)
            path = None
            inode = None
            sizes = None

info.memory /= 512

subprocess.Popen(args=['./Construct.sh', "{0}".format(str(args.acquisition)), "{0}".format(str(info.memory))])

target = str(args.acquisition)+".dmg"

while not os.path.exists(target):
    print "Waiting For disk"

for all in info.file_tuple:
    str(all).split(", ")
    # source=$1 target=$2 byte size=$3 Start Block=$4
    subprocess.Popen(args=['./File_Insert.sh', '%s' % str(all.split(", ")[1]), '%s' % str(target),
                           '%s' % (str(str(all).split(", ")[0])), '%s' % (str(info.total_files))])
subprocess.Popen(args=['./File_Insert.sh', '%s' % str("/dev/zero"), '%s' % str(target), '%s' % str(info.memory)])
