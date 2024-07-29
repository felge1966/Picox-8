#!/bin/sh

set -ex

hex=$1
bin=$2

if [ "$bin" == "" ]
then
    echo "usage: $0 <hex> <bin>"
    exit 1
fi

perl -pi -e 's/\r//' $hex
perl -ni -e 'print unless (/^$/)' $hex
arm-none-eabi-objcopy --input-target=ihex --output-target=binary $hex $bin
python tools/readrom.py $bin
