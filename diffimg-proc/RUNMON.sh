#!/bin/bash

umask 002

# check for an input argument

if [ $# -lt 1 ]; then
echo "usage: RUNMON.sh -E EXPNUM -r RPNUM -p DIFFPROCNUM -n NITE -f FIELD [-v DIFFIMG_VERSION]"
exit 1
fi

ARGS="$@"
# we need to pull out expnum, chip, and band : KRH needs to double check syntax here

#rpnum="r1p1"
#procnum="dp91"
DIFFIMG_VERSION="gwdevel10" # can change this with parameter -v <diffimg_version>

##### Don't forget to shift the args after you pull these out #####
while getopts "E:n:f:r:p:v:" opt $ARGS
do case $opt in
    r)
            rpnum=$OPTARG
            shift 2
            ;;
    p)
            procnum=$OPTARG
            shift 2
            ;;
    E)
	    [[ $OPTARG =~ ^[0-9]+$ ]] || { echo "Error: exposure number must be an integer! You put $OPTARG" ; exit 1; }
	    EXPNUM=$OPTARG
	    shift 2
	    ;;   
    n)
	    [[ $OPTARG =~ ^[0-9]+$ ]] || { echo "Error: Night must be an integer! You put $OPTARG" ; exit 1; }
	    NITE=$OPTARG
	    shift 2
	    ;;
    v)
            DIFFIMG_VERSION=$OPTARG
            shift 2

            ;;
    f)
	    FIELD=$OPTARG
	    shift 2
	    ;;
    :)
	    echo "Option -$OPTARG requires an argument."
	    exit 1
	    ;;
esac
done

if [ "x$rpnum" == "x" ]; then echo "rpnum not set; exiting." ; exit 1 ; fi
if [ "x$procnum" == "x" ]; then echo "procnum not set; exiting." ; exit 1 ; fi
if [ "x$EXPNUM" == "x" ]; then echo "Exposure number not set; exiting." ; exit 1 ; fi
if [ "x$NITE" == "x" ]; then echo "night not set; exiting." ; exit 1 ; fi
if [ "x$FIELD" == "x" ]; then echo "field not set; exiting." ; exit 1 ; fi

#echo $rpnum
#echo $procnum
#echo $EXPNUM
#echo $NITE
#echo $FIELD
#echo $DIFFIMG_VERSION
#exit


### Force use of SLF6 versions for systems with 3.x kernels
case `uname -r` in
    3.*) export UPS_OVERRIDE="-H Linux64bit+2.6-2.12";;
    4.*) export UPS_OVERRIDE="-H Linux64bit+2.6-2.12";;
esac

export OLDHOME=$HOME
export HOME=$PWD

/cvmfs/grid.cern.ch/util/cvmfs-uptodate /cvmfs/des.opensciencegrid.org
. /cvmfs/des.opensciencegrid.org/2015_Q2/eeups/SL6/eups/desdm_eups_setup.sh
export EUPS_PATH=/cvmfs/des.opensciencegrid.org/eeups/fnaleups:$EUPS_PATH

# setup a specific version of perl so that we know what we're getting
setup perl 5.18.1+6 || exit 134

###### any additional required setups go here #####

#we will want the GW version of diffimg for sure
setup Y2Nstack
setup diffimg $DIFFIMG_VERSION #whatever the version number ends up being
setup autoscan


#for IFDH
export EXPERIMENT=des
export PATH=${PATH}:/cvmfs/fermilab.opensciencegrid.org/products/common/db/../prd/cpn/v1_7/NULL/bin:/cvmfs/fermilab.opensciencegrid.org/products/common/db/../prd/ifdhc/v1_8_11/Linux64bit-2-6-2-12/bin
export PYTHONPATH=${PYTHONPATH}:/cvmfs/fermilab.opensciencegrid.org/products/common/db/../prd/ifdhc/v1_8_11/Linux64bit-2-6-2-12/lib/python
export IFDH_NO_PROXY=1
export DES_SERVICES=~/.deservices.ini
export DES_DB_SECTION=db-sn-test
export AUTOSCAN_PYTHON=$PYTHON_DIR/bin/python
export IFDH_CP_MAXRETRIES=2

# copy the list files and cut config files in first
LISTFILES="/pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/input_files/SN_cuts.filterObj `ifdh findMatchingFiles /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/ "SN_mon_${NITE}_${FIELD}*.list" | awk '{print $1}'`"

ifdh cp -D $LISTFILES ./ || echo "FAILURE: unable to copy input list files."

mkdir input_files
mv SN_cuts.filterObj input_files/

INFILES=""

#for cpfile in `cat SN_mon_${NITE}_${FIELD}_filterObj.list SN_mon_${NITE}_${FIELD}_fakeMatch.list SN_mon_${NITE}_${FIELD}_autoScan.list SN_mon_${NITE}_${FIELD}_makeCand.list`

for cpfile in filterObj fakeMatch autoScan makeCand
do

INFILES="$INFILES `ifdh ls '/pnfs/des/scratch/gw/exp/'${NITE}'/'${EXPNUM}'/'${procnum}'/*_[0-6][0-9]/*'${cpfile}'.out' | grep out` "

done

ifdh cp -D $INFILES ./

IFDH_RESULT=$?

[[ $IFDH_RESULT -eq 0 ]] || { echo "ifdh input copy failed with status $IFDH_RESULT. Aborting." ; exit $IFDH_RESULT ; }

# make symlinks to get  SN_mon_EXPNUM*.list files, which is what monDiffim wants



for file in `cat SN_mon_${NITE}_${FIELD}_filterObj.list SN_mon_${NITE}_${FIELD}_fakeMatch.list SN_mon_${NITE}_${FIELD}_autoScan.list SN_mon_${NITE}_${FIELD}_makeCand.list`
do
basefile=`basename $file`

if [ -f $basefile ]; then
# check if directory exists
    filedir=`echo $file | cut -d "/" -f 1`
    if [ -d $filedir ]; then
	mv $basefile $filedir
    else
	mkdir $filedir
	mv $basefile $filedir
    fi
else
    echo "$basefile not present; the diffimg job probably failed."
fi

done

echo "Done copying in; looking for files now"
ls .


monDiffim  \
  -inFile_objList   SN_mon_${NITE}_${FIELD}_filterObj.list \
  -inFile_fakeList  SN_mon_${NITE}_${FIELD}_fakeMatch.list \
  -inFile_autoList  SN_mon_${NITE}_${FIELD}_autoScan.list \
  -inFile_candList  SN_mon_${NITE}_${FIELD}_makeCand.list \
  -inFile_monPar    input_files/SN_cuts.filterObj \
  -field            ${FIELD} \
  -nite             $NITE \
  -outFile_log      RUNEND_monDiffimg.LOG \
  -outFile_fakeOutliers  FAKE_OUTLIERS.LOG

# copy output back

MONDIFFIM_RESULT=$?

echo "monDiffim exited with status $MONDIFFIM_RESULT" 

export HOME=$OLDHOME

OUTFILES=`ls RUNEND_monDiffimg.LOG FAKE_OUTLIERS.LOG *.stdout` 2> /dev/null
ifdh cp -D $OUTFILES /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/

IFDH_RESULT=$?

[[ $IFDH_RESULT -eq 0 ]] || { echo "ifdh output copyback failed with status $IFDH_RESULT. Aborting." ; exit $IFDH_RESULT ; }

exit $MONDIFFIM_RESULT

