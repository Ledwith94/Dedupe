#!/usr/bin/python

import argparse
import datetime
import hashlib
import os
import subprocess
import time
import pyvhdi
import string

import paramiko
import pytsk3
from pymongo import MongoClient


class Server:
    def __init__(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect('xxxx', username='xxx', password='xxxx')
        self.sub = None

    def make_dir(self):
        sftp = self.ssh.open_sftp()
        serverpath = '/home/paul/Testing/' + args.acquisition
        try:
            sftp.chdir(serverpath)
        except IOError:
            sftp.mkdir(serverpath)
            sftp.chdir(serverpath)

    def send_file(self, filepath, filedata, name, slack):
        sftp = self.ssh.open_sftp()
        if slack is False:
            serverpath = '/home/paul/Testing/' + args.acquisition + "/"+ filepath
        else:
            serverpath = '/home/paul/Testing/' + filepath
        try:
            sftp.chdir(serverpath)
        except IOError:
            sftp.mkdir(serverpath)
            sftp.chdir(serverpath)

        if slack is False:
            serverpath = serverpath + "/" + name
            tmp_path = "/tmp/xyzzy"
            tha = open(tmp_path, "wb")
            file_obj = filesystemObject.open_meta(inode=filedata)
            tha.write(file_obj.read_random(0, file_obj.info.meta.size))
            tha.close()
            rha = open(tmp_path, "rb")
            sftp.putfo(rha, serverpath)
            rha.close()
        else:
            serverpath = '/home/paul/Testing/' + str(filepath) + name
            sftp.put(filedata, serverpath)
        return serverpath


class Metrics:
    def __init__(self):
        self.name = None
        self.total_files = 0
        self.total_slack_files = 0
        self.memory = 0
        self.image_size = 0
        self.time_taken = 0
        self.black_listed = {}
        self.insert_list = []
        self.startTime = datetime.datetime.now()
        self.final_block = 0
        self.block_tuple = []
        self.total_block = 0
        self.slack_space = []
        self.slack_files = []
        self.failed_files = 0
        self.block_size = 4096
        self.os_list = {"windows": 4096, "mac": 512, "linux": 512}
        self.duplicated_files = 0
        self.dedupe_amount = 0
        self.dedupe_number = 0

    def get_block_size(self, os):
        if os in self.os_list:
            return self.os_list.get(os)
        else:
            print "Could not retrieve block size for " + str(os) + "defaulting to 512 bytes"
            return 512


class vhdi_Img_Info(pytsk3.Img_Info):
    def __init__(self, vhdi_file):
        self._vhdi_file = vhdi_file
        super(vhdi_Img_Info, self).__init__(
            url='', type=pytsk3.TSK_IMG_TYPE_EXTERNAL)

    def close(self):
        self._vhdi_file.close()

    def read(self, offset, size):
        self._vhdi_file.seek(offset)
        return self._vhdi_file.read(size)

    def get_size(self):
        return self._vhdi_file.get_media_size()


class ewf_Img_Info(pytsk3.Img_Info):
    def __init__(self, ewf_handle):
        self._ewf_handle = ewf_handle
        self.memory = 0
        super(ewf_Img_Info, self).__init__(
            url="", type=pytsk3.TSK_IMG_TYPE_EXTERNAL)

    def close(self):
        self._ewf_handle.close()

    def read(self, offset, size):
        self._ewf_handle.seek(offset)
        return self._ewf_handle.read(size)

    def get_size(self):
        return self._ewf_handle.get_media_size()


class Data:
    def mongo_insert(self, insert):
        client = MongoClient()
        db = client['dedupe']
        files = db.files
        file_id = files.insert_one(insert).inserted_id

    def acq_insert(self, insert):
        client = MongoClient()
        db = client['Acquisition']
        files = db.files
        file_id = files.insert_one(insert).inserted_id

    def aqui_push(self, insert):
        client = MongoClient()
        db = client['Acquisition']
        files = db.files
        file_id = files.update({"Name": metric.name}, {'$push': {"All Files": insert}})
        #remote.on_fly_reconstruct(insert)

    def acquisition_exists(self, name):
        client = MongoClient()
        db = client['Acquisition']
        files = db.files
        if bool(files.find_one({"Name": name})):
            return True
        else:
            return False

    def already_exists(self, hash):
        client = MongoClient()
        db = client['dedupe']
        files = db.files
        if bool(files.find_one({"SHA1 Hash": hash})):
            files.update_one({"SHA1 Hash": hash}, {'$addToSet': {"Acquisition": outname}})
            metric.duplicated_files += 1
            text = files.find({"SHA1 Hash": hash}).distinct("File Path")
            return text[0]
        else:
            return False

    def blacklisted(self, insert):
        client = MongoClient()
        db = client['blacklist']
        files = db.files
        print "Blacklisted File Found"
        print insert
        metric.black_listed += {insert}


def directoryRecurse(directoryObject, parentPath):
    insert_count = 0
    for entryObject in directoryObject:
        if (not hasattr(entryObject, "info") or
                not hasattr(entryObject.info, "name") or
                not hasattr(entryObject.info.name, "name") or
                entryObject.info.name.name in [".", ".."]):
            continue

        try:
            f_type = entryObject.info.meta.type

        except:
            #print "Cannot retrieve type of", entryObject.info.name.name
            metric.total_files += 1
            metric.failed_files += 1
            continue

        try:

            filepath = '/%s/%s' % ('/'.join(parentPath), entryObject.info.name.name)
            outputPath = '/%s/%s/%s/' % (metric.name, str(partition.addr), '/'.join(parentPath))

            if f_type == pytsk3.TSK_FS_META_TYPE_DIR:
                sub_directory = entryObject.as_directory()
                parentPath.append(entryObject.info.name.name)
                directoryRecurse(sub_directory, parentPath)
                parentPath.pop(-1)

            elif f_type == pytsk3.TSK_FS_META_TYPE_REG and entryObject.info.meta.size != 0:
                metric.total_files += 1
                filedata = entryObject.read_random(0, entryObject.info.meta.size)
                md5hash = hashlib.md5()
                md5hash.update(filedata)
                sha1hash = hashlib.sha1()
                sha1hash.update(filedata)
                start_block = None
                finish_block = None
                block_length = None
                for attr in entryObject:
                    for run in attr:
                        start_block = run.addr + 1
                        block_length = run.len
                        finish_block = start_block + run.len
                printable = set(string.printable)
                insert = {"SHA1 Hash": sha1hash.hexdigest(),
                          "MD5 Hash": md5hash.hexdigest(),
                          "inode": int(entryObject.info.meta.addr),
                          "Name": '/'.join(parentPath) + filter(lambda x: x in printable, entryObject.info.name.name),
                          "Type": str(entryObject.info.meta.type),
                          "Creation Time": datetime.datetime.fromtimestamp(entryObject.info.meta.crtime).strftime(
                              '%Y-%m-%d %H:%M:%S'),
                          "Size": int(entryObject.info.meta.size),
                          "File Path": None,
                          "Acquisition": [outname],
                          "Start Block": start_block,
                          "Finish Block": finish_block,
                          "Block Length": block_length
                          }
                if start_block is not None:
                    metric.block_tuple.append((int(start_block), int(finish_block)))
                    metric.total_block += int(block_length)
                    if int(finish_block) > metric.final_block:
                        metric.final_block = int(finish_block)
                    if metric.final_block < int(finish_block):
                        metric.final_block = int(finish_block)
                server_check = mongo.already_exists(sha1hash.hexdigest())
                if server_check is False:
                    metric.memory += int(entryObject.info.meta.size)
                    # path = remote.send_file(str(partition.addr), int(entryObject.info.meta.addr), entryObject.info.name.name, False)
                    # insert["File Path"] = path
                    if not os.path.exists("Extracted_files/" + outputPath):
                        os.makedirs("Extracted_files/" + outputPath)
                    file_location = "Extracted_files/" + outputPath + \
                                    filter(lambda x: x in printable, entryObject.info.name.name)
                    extractFile = open(file_location,
                                       'w')
                    extractFile.write(filedata)
                    extractFile.close()
                    insert["File Path"] = file_location
                    mongo.mongo_insert(insert)

                else:
                    insert["File Path"] = server_check
                    metric.dedupe_amount += int(entryObject.info.meta.size)
                    metric.dedupe_number += 1

                metric.insert_list.append(insert)
                insert_count += 1
                # if insert_count > 600:
                #     mongo.aqui_push(metric.insert_list)
                #     metric.insert_list = []
                #     insert_count = 0
                # if metric.total_files > 400:
                #     print datetime.datetime.now() - metric.startTime
                #     print metric.total_files
                #     print metric.memory
                #     exit()
        except IOError as e:
            print e
            continue

metric = Metrics()
remote = Server()
mongo = Data()
# fly = Construct()
argparser = argparse.ArgumentParser(
    description='Hash files recursively from a forensic image and optionally extract them')
argparser.add_argument(
    '-i', '--image',
    dest='imagefile',
    action="store",
    type=str,
    default=None,
    required=True,
    help='E01 to extract from'
)
argparser.add_argument(
    '-t', '--type',
    dest='imagetype',
    action="store",
    type=str,
    default=None,
    required=True,
    help='Specify image type e01 or raw'
)
argparser.add_argument(
    '-o', '--os',
    dest='os',
    action="store",
    type=str,
    default="512",
    required=False,
    help='Specify OS name e.g. windows, mac, linux'
)
argparser.add_argument(
    '-a', '--acquisition',
    dest='acquisition',
    action="store",
    type=str,
    default=False,
    required=True,
    help='Specify acquisition name'
)
argparser.add_argument(
    '--enable-automation',
    dest='blacklist',
    action="store",
    type=bool,
    default=False,
    required=False,
    help='Enable auto file discovery'
)
args = argparser.parse_args()
dirPath = '/'
outname = args.acquisition
if not os.path.exists("Slack_Files/" + args.acquisition):
    os.makedirs("Slack_Files/" + args.acquisition)
i = 0

while mongo.acquisition_exists(outname):
    outname += str(i)
    i += 1
print "Acquisition Name: " + outname

outname = args.acquisition #Comment this out when not testing
metric.name = outname
if args.os is not "512":
    metric.block_size = metric.get_block_size(args.os)
else:
    metric.block_size = int(args.os)

if args.imagetype == "raw":
    print "Raw Type"
    imagehandle = pytsk3.Img_Info(url=args.imagefile)
else:
    print "Virtual Hard Disk"
    vhdi_file = pyvhdi.file()
    vhdi_file.open(args.imagefile)
    imagehandle = vhdi_Img_Info(vhdi_file)
metric.image_size = pytsk3.Img_Info.get_size(imagehandle)
partitionTable = pytsk3.Volume_Info(imagehandle)
print "Block Size: " + str(metric.block_size)

# insert = {"Name": outname,
#           "Image Size": str(metric.image_size)
#           }

#mongo.acq_insert(insert)
#remote.image_touch()
remote.make_dir()
for partition in partitionTable:
    print partition.addr, partition.desc, "%ss(%s)" % (partition.start, partition.start * metric.block_size), partition.len
    try:
        filesystemObject = pytsk3.FS_Info(imagehandle, offset=(partition.start * metric.block_size))
    except:
        print "Partition has no supported file system"
        continue
    print "File System Type Dectected ", filesystemObject.info.ftype
    directoryObject = filesystemObject.open_dir(path=dirPath)
    print "Directory:", dirPath
    directoryRecurse(directoryObject, [])
metric.block_tuple.sort(key=lambda tup: tup[1])
j = 0
prev = None
last_block = int(pytsk3.Img_Info.get_size(imagehandle))/512

for i in metric.block_tuple:
    if metric.block_tuple.index(i) is 0:
        if i[0] == 0:
            continue
        elif i[0] > 0:
            metric.slack_space.append([0, i[0]])
            j += 1
    else:
        if prev < i[0]:
            metric.slack_space.append([prev, i[0]])
            j += 1
    if i == metric.block_tuple[-1]:
        metric.slack_space.append([i[1], last_block])
    prev = i[1]

metric.block_tuple.sort()
metric.total_block = metric.final_block - metric.total_block

j = 0
outpath = str(metric.name) + "/Slack_Files/"
for i in metric.slack_space:
    run_blocks = int(i[1]) - int(i[0])
    name = "file_" + str(j)
    outfile = "Slack_Files/" + str(metric.name) + "/" + name
    subprocess.Popen(
        args=['./Construct.sh', '%s' % str(args.imagefile), '%s' % str(outfile), '%s' % str(i[0]),
              '%s' % str(run_blocks), '%s' % str(metric.block_size)])
    time.sleep(.05)
    sha1hash = hashlib.sha1()
    sha1hash.update(outfile)
    md5hash = hashlib.md5()
    md5hash.update(outfile)
    insert = {"SHA1 Hash": sha1hash.hexdigest(),
              "MD5 Hash": md5hash.hexdigest(),
              "inode": "None",
              "Name": str(outfile.split('/')[-1]),
              "Type": "SLACK",
              "Creation Time": os.path.getctime(outfile),
              "Size": int(os.path.getsize(outfile)),
              "File Path": '/home/paul/Testing/' + str(metric.name)+str(outfile),
              "Acquisition": [outname],
              "Start Block": int(i[0]),
              "Finish Block": int(i[1]),
              "Block Length": int(int(i[1]) - int(i[0]))
              }
    metric.insert_list.append(insert)
    metric.total_slack_files += 1
    server_check = mongo.already_exists(sha1hash.hexdigest())
    if mongo.already_exists(sha1hash.hexdigest()) is False:
        metric.memory += int(os.path.getsize(outfile))
        # path = remote.send_file(outpath, outfile, name, True)
        # insert["File Path"] = path
        insert["File Path"] = outfile
        mongo.mongo_insert(insert)
    else:
        insert["File Path"] = server_check
    metric.slack_files.append([outfile, i[0], run_blocks])
    j += 1
total_blocks = metric.image_size/metric.block_size
run_blocks = total_blocks - metric.final_block



metric.startTime = datetime.datetime.now() - metric.startTime
print "Total files: " + str(metric.total_files)
print "Image Size: " + str(metric.image_size)
print "Total Slack files: " + str(metric.total_slack_files)
print "Number Duplicated" + str(metric.dedupe_number)
print "Failed files: " + str(metric.failed_files)
print "Time Taken: " + str(metric.startTime)
print "MB uploaded: " + str(metric.memory) + " MB"
print "Final block: " + str(metric.final_block)
print "Slack space amount: " + str(metric.total_block)
print "Slack space between: "
for p in metric.slack_space:
    print p
if metric.black_listed:
    print "Black listed: "
    print str(metric.black_listed)
print "Percentage Duplicates: " + str(float(metric.dedupe_number)/float(metric.total_files)*100.0) + "%"
print "Percentage Aquired: " + \
      str(((float(metric.total_files) - float(metric.failed_files))/float(metric.total_files)*100.0)) + "%"

#mongo.aqui_push(metric.insert_list)

sha1hash = hashlib.sha1()
sha1hash.update(args.imagefile)
md5hash = hashlib.md5()
md5hash.update(args.imagefile)
insert = {"Name": outname,
          "Image Size": str(metric.image_size),
          "Time taken": str(metric.startTime),
          "Total files": str(metric.total_files),
          "Total Slack files: ": str(metric.total_slack_files),
          "Percentage Duplicates: ": float(metric.dedupe_number)/float(metric.total_files)*100.0,
          "Failed files": str(metric.failed_files),
          "MB uploaded": str(metric.memory),
          "Block Size": str(metric.block_size),
          "Slack Space": metric.slack_space,
          "All Files": metric.insert_list,
          "SHA1 Hash": sha1hash.hexdigest(),
          "MD5 Hash": md5hash.hexdigest(),
          "Number Duplicated": metric.dedupe_number,
          "Total Duplicate Data": metric.dedupe_amount
          }

mongo.acq_insert(insert)
#construct = Main()
