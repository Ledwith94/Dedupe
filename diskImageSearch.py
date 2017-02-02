#!/usr/bin/python
import argparse
import datetime
import hashlib
import os
import pyvhdi

import paramiko
import pytsk3
from pymongo import MongoClient


class Server:
    def __init__(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect('xxx', username='xxx', password='xxx')

    def send_file(self, filepath, filedata, name):
        sftp = self.ssh.open_sftp()
        serverpath = '/home/paul/Testing/' + args.acquisition + filepath[len(filepath)-1]
        try:
            sftp.chdir(serverpath)
        except IOError:
            sftp.mkdir(serverpath)
            sftp.chdir(serverpath)
        serverpath = '/home/paul/Testing/' + args.acquisition + filepath[len(filepath)-1] + name
        tmp_path = "/tmp/xyzzy"
        file_obj = filesystemObject.open_meta(inode=filedata)
        tha = open(tmp_path, "wb")
        tha.write(file_obj.read_random(0, file_obj.info.meta.size))
        tha.close()

        rha = open(tmp_path, "rb")
        sftp.putfo(rha, serverpath)
        rha.close()


class Metrics:
    def __init__(self):
        self.name = None
        self.total_files = 0
        self.failed_files = {}
        self.memory = 0
        self.time_taken = 0
        self.black_listed = {}
        self.insert_list = []
        self.startTime = datetime.datetime.now()
        self.final_block = 0
        self.block_tuple = []
        self.total_block = 0
        self.slack_space = []


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
            return True
        else:
            return False

    def blacklisted(self, insert):
        client = MongoClient()
        db = client['blacklist']
        files = db.files
        print "Blacklisted File Found"
        print insert
        metric.black_listed += {insert}


def shahash_file(filedata):
    md5hash = hashlib.md5()
    return md5hash.update(filedata)


def directoryRecurse(directoryObject, parentPath):
    for entryObject in directoryObject:
        if entryObject.info.name.name in [".", ".."]:
            continue

        try:
            f_type = entryObject.info.meta.type

        except:
            # print "Cannot retrieve type of", entryObject.info.name.name
            metric.total_files += 1
            metric.failed_files += 1
            continue

        try:

            filepath = '/%s/%s' % ('/'.join(parentPath), entryObject.info.name.name)
            if str(parentPath) is None:
                outputPath = '/%s' % (str(partition.addr))
            else:
                outputPath = '/%s/%s/' % (str(partition.addr), '/'.join(parentPath))

            if f_type == pytsk3.TSK_FS_META_TYPE_DIR:
                sub_directory = entryObject.as_directory()
                parentPath.append(entryObject.info.name.name)
                directoryRecurse(sub_directory, parentPath)
                parentPath.pop(-1)

            elif f_type == pytsk3.TSK_FS_META_TYPE_REG and entryObject.info.meta.size != 0:
                metric.total_files += 1
                metric.memory += int(entryObject.info.meta.size)
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
                        start_block = run.addr
                        block_length = run.len
                        finish_block = run.addr + run.len

                insert = {"SHA1 Hash": sha1hash.hexdigest(),
                          "MD5 Hash": md5hash.hexdigest(),
                          "inode": int(entryObject.info.meta.addr),
                          "Name": '/'.join(parentPath) + entryObject.info.name.name,
                          "Type": str(entryObject.info.meta.type),
                          "Creation Time": datetime.datetime.fromtimestamp(entryObject.info.meta.crtime).strftime(
                              '%Y-%m-%d %H:%M:%S'),
                          "Size": int(entryObject.info.meta.size),
                          "File Path": "Extracted_files" + outputPath + entryObject.info.name.name,
                          "Acquisition": [outname],
                          "Start Block": int(start_block),
                          "Finish Block": int(finish_block),
                          "Block Length": int(block_length)
                          }
                metric.block_tuple.append(int(start_block))
                metric.block_tuple.append(int(finish_block))
                metric.total_block += int(block_length)
                if int(finish_block) > metric.final_block:
                    metric.final_block = int(finish_block)
                metric.insert_list.append(insert)
                if mongo.already_exists(sha1hash.hexdigest()) is True:
                    mongo.mongo_insert(insert)
                    #remote.send_file(outputPath, int(entryObject.info.meta.addr), entryObject.info.name.name)
                    if not os.path.exists("Extracted_files/" + outputPath):
                        os.makedirs("Extracted_files/" + metric.name + "/" + outputPath)
                    extractFile = open("Extracted_files/" + metric.name + "/" + outputPath + entryObject.info.name.name, 'w')
                    extractFile.write(filedata)
                    extractFile.close()

        except IOError as e:
            print e
            continue


metric = Metrics()
remote = Server()
mongo = Data()
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
    default=False,
    required=True,
    help='Specify image type e01 or raw'
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
i = 0

while mongo.acquisition_exists(outname):
    outname += str(i)
    i += 1
print "Acquisition Name: " + outname
outname = args.acquisition #Comment this out when not testing
metric.name = outname
if args.imagetype == "raw":
    print "Raw Type"
    imagehandle = pytsk3.Img_Info(url=args.imagefile)
else:
    print "Virtual Hard Disk"
    vhdi_file = pyvhdi.file()
    vhdi_file.open(args.imagefile)
    imagehandle = vhdi_Img_Info(vhdi_file)

partitionTable = pytsk3.Volume_Info(imagehandle)
for partition in partitionTable:
    print partition.addr, partition.desc, "%ss(%s)" % (partition.start, partition.start * 512), partition.len
    try:
        filesystemObject = pytsk3.FS_Info(imagehandle, offset=(partition.start * 512))
    except:
        print "Partition has no supported file system"
        continue
    print "File System Type Dectected ", filesystemObject.info.ftype
    directoryObject = filesystemObject.open_dir(path=dirPath)
    print "Directory:", dirPath
    directoryRecurse(directoryObject, [])
j = 2
i = 1
while j < len(metric.block_tuple):
    if (int(metric.block_tuple[i]) - int(metric.block_tuple[j])) != 0:
        metric.slack_space.append((metric.block_tuple[i], metric.block_tuple[j]))
    i += 2
    j += 2
metric.startTime = datetime.datetime.now() - metric.startTime
metric.block_tuple.sort()
metric.total_block = metric.final_block - metric.total_block

print "Total files: " + str(metric.total_files)
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

insert = {"Name": outname,
          "Time taken: ": str(metric.startTime),
          "Total files": metric.total_files,
          "Failed files": metric.failed_files,
          "MB uploaded": metric.memory,
          "Image Size": str(pytsk3.Img_Info.get_size(imagehandle)),
          "All Files": metric.insert_list,
          "Slack Space": metric.slack_space
          }

mongo.acq_insert(insert)
