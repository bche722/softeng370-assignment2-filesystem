
#!/usr/bin/env python
#Author: Vincent Chen UPI:bche722

from __future__ import print_function, absolute_import, division

import logging

import os
import sys
import errno

from collections import defaultdict
from errno import ENOENT
from stat import S_IFDIR, S_IFLNK, S_IFREG
from sys import argv, exit
from time import time

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn
from passthrough import Passthrough
from memory import Memory

class A2Fuse2(LoggingMixIn, Passthrough):
    def __init__(self, root):
        self.root = root
	self.files = {}
        self.data = defaultdict(bytes)
        self.fd = 0
        now = time()
        self.files['/'] = dict(st_mode=(S_IFDIR | 0o755), st_ctime=now,st_mtime=now, st_atime=now, st_nlink=2)

    def getattr(self, path, fh=None):
	if path not in self.files:
            full_path = self._full_path(path)
            st = os.lstat(full_path)
            return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                     'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

        return self.files[path]

    def readdir(self, path, fh):
	full_path = self._full_path(path)

	dirents = ['.', '..'] + [x[1:] for x in self.files if x != '/']
        if os.path.isdir(full_path):
            dirents.extend(os.listdir(full_path))
        for r in dirents:
            yield r

    def open(self, path, flags):
        if path not in self.files:
            full_path = self._full_path(path)
            return os.open(full_path, flags)

        self.fd += 1
        return self.fd

    def create(self, path, mode):
        self.files[path] = dict(st_mode=(S_IFREG | mode), st_nlink=1,
                                st_size=0, st_ctime=time(), st_mtime=time(),
                                st_atime=time())
        self.fd += 1
        return self.fd

    def unlink(self, path):
	if path not in self.files:
            return os.unlink(self._full_path(path))

	self.files.pop(path)

    def write(self, path, data, offset, fh):
	if path not in self.files:
            os.lseek(fh, offset, os.SEEK_SET)
            return os.write(fh, data)

        self.data[path] = self.data[path][:offset] + data
        self.files[path]['st_size'] = len(self.data[path])
        return len(data)
        
    def read(self, path, size, offset, fh):
	if path not in self.files:
            os.lseek(fh, offset, os.SEEK_SET)
            return os.read(fh, size)

        return self.data[path][offset:offset + size]

    def flush(self, path, fh):
	if path not in self.files:
            return os.fsync(fh)

        return 0

def main(mountpoint, root):
    FUSE(A2Fuse2(root), mountpoint, nothreads=True, foreground=True)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main(sys.argv[2], sys.argv[1])
