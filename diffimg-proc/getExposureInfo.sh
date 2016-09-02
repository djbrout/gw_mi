#!/bin/bash

source /cvmfs/des.opensciencegrid.org/eeups/startup.sh

setup easyaccess
setup psycopg2
python getExposureInfo.py

for band in g r i z Y
do
awk '($6 == "'$band'")' exposures.list > exposures_${band}.list
done

exit