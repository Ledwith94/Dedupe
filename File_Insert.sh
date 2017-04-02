#!/usr/bin/env bash

if [ $1 = "/dev/zero" ]
then
    dd if=$1 of=$2 conv=notrunc seek=$3 count=1
else
    dd if=$1 of=$2 conv=notrunc seek=$3 count=$4

fi
