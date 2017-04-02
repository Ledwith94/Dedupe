#!/usr/bin/python

import paramiko


class Server:
    def __init__(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect('xxx', username='xxx', password='xxxx')
        self.sub = None

    def make_dir(self, acquisition):
        sftp = self.ssh.open_sftp()
        serverpath = '/home/paul/Testing/' + acquisition
        try:
            sftp.chdir(serverpath)
        except IOError:
            sftp.mkdir(serverpath)
            sftp.chdir(serverpath)

    def send_file(self, filepath, filedata, name, slack, acquisition, fso):
        sftp = self.ssh.open_sftp()
        if slack is False:
            serverpath = '/home/paul/Testing/' + acquisition + "/"+ filepath
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
            file_obj = fso.open_meta(inode=filedata)
            tha.write(file_obj.read_random(0, file_obj.info.meta.size))
            tha.close()
            rha = open(tmp_path, "rb")
            sftp.putfo(rha, serverpath)
            rha.close()
        else:
            serverpath = '/home/paul/Testing/' + str(filepath) + name
            sftp.put(filedata, serverpath)
        return serverpath
