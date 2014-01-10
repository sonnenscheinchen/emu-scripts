#!/usr/bin/env python3

import os
import pdb

rootdir = '/tmp/AmiKit'
filelist = []
errors = []

print('building filelist...')
for root, folders, files in os.walk(rootdir):
    for file in files:
        #filelist.append(os.path.join(root, file).lower())
        filelist.append(os.path.join(root, file))

#print('checking for dupes...')
#while filelist:
#    item = filelist.pop()
#    if item in filelist:
#        try:
#            print(item)
#        except UnicodeEncodeError:
#            errors.append(item)
#repr(errors)

for item in filelist:
    try:
        item.encode(encoding='ISO-8859-1')
    except UnicodeEncodeError:
        errors.append(item)
#        os.remove(item)

with open('/tmp/errors.txt', 'wt') as f:
    for error in errors:
        f.write(repr(error) + os.linesep)
#        f.write(os.linesep)

#if len(filelist) != len(set(filelist)):
#    print('dupes!!')
#pdb.set_trace()
