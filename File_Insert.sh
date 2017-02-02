#!/usr/bin/env bash

if [ $1 = "/dev/zero" ]
then
    dd if=$1 of=$2 count=0 seek=$3 files=$4
else
    dd if=$1 of=$2 seek=$3 files=$4

fi