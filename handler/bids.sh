#!/bin/bash

set -e
set -x

if [ -z $1 ]; then
    echo "please specify root dir"
    exit 1
fi
root=$1

datasetName=`jq -r '.datasetDescription.Name' $root/finalized.json`

rootDir=$root/bids/$datasetName

rm -rf $rootDir

#echo "making deface list"
#./make_deface_list.py $root
#
#echo "running defacing"
#if [ ! -f $root/deface.out ]; then
#    touch $root/deface.out
#fi
#
#chmod -R 777 $root

#function deface {
#    deface_info=$1 
#    ./deface.py $deface_info
#}
#export -f deface
#cat $root/deface_list.txt | parallel -j 12 deface {}

echo "converting output to bids"
./convert.js $root


echo "output bids directory structure"
tree $rootDir > $root/tree.log

echo "running bids validator"
bids-validator $rootDir > $root/validator.log || true

