#!/bin/bash

if [ $# -lt 1 ]; then
    echo "usage: SE_job.sh -E EXPNUM -r RNUM -p PNUM -n NITE -b BAND [-j] [-s]" 
    exit 1
fi

OLDHOME=$HOME
export HOME=$PWD

ulimit -a
source /cvmfs/des.opensciencegrid.org/eeups/startupcachejob21i.sh
setup fitscombine yanny
setup finalcut              Y2A1+4
setup scamp 2.1.1+5
setup tcl 8.5.17+0
setup extralibs 1.0
setup wcstools 3.8.7.1+2
#to parallelize the ccd loops 
setup joblib
export MPLCONFIGDIR=$PWD/matplotlib
mkdir $MPLCONFIGDIR
mkdir qa
##testing a newer version of joblib
##mkdir joblib-0.9.0b4
##ifdh cp -r  /pnfs/des/scratch/marcelle/joblib-0.9.0b4 ./joblib-0.9.0b4
##export PYTHONPATH=$PYTHONPATH:$PWD/joblib-0.9.0b4


ARGS="$@"
while getopts "E:n:b:r:p:jhs" opt $ARGS
do case $opt in
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
    b)
            case $OPTARG in
                i|r|g|Y|z)
                    BAND=$OPTARG
                    shift 2
                    ;;
                *)
                    echo "Error: band option must be one of r,i,g,Y,z. You put $OPTARG"
                    exit 1
                    ;;
            esac
            ;;
    r)
            RNUM=$OPTARG
            shift 2
            ;;
    p)
            PNUM=$OPTARG
            shift 2
            ;;
    j)
            JUMPTOEXPCALIB=true
            shift 
            ;;
    s)
            SINGLETHREAD=true
            shift 
            ;;
    h)
	    echo "usage: SE_job.sh -E EXPNUM -r RNUM -p PNUM -n NITE -b BAND [-j] [-s]" 
	    exit 1
            ;;
    :)
            echo "Option -$OPTARG requires an argument."
            exit 1
            ;;
esac
done

if [ "x$EXPNUM" == "x" ]; then echo "Exposure number not set; exiting." ; exit 1 ; fi
if [ "x$NITE"   == "x" ]; then echo "NITE not set; exiting."            ; exit 1 ; fi
if [ "x$BAND"   == "x" ]; then echo "BAND not set; exiting."            ; exit 1 ; fi
if [ "x$RNUM"   == "x" ]; then echo "r number not set; exiting."        ; exit 1 ; fi
if [ "x$PNUM"   == "x" ]; then echo "p number not set; exiting."        ; exit 1 ; fi

ifdh cp -D /pnfs/des/persistent/desdm/code/desdmLiby1e2.py .

# serial processing of ccds
ifdh cp -D /pnfs/des/persistent/desdm/code/run_desdmy1e2.py .

# parallelized ccd loops 
ifdh cp -D /pnfs/des/scratch/marcelle/run_SEproc.py .

ifdh cp -D /pnfs/des/persistent/desdm/code/getcorners.sh .

rm -f confFile

# Automatically determine year and epoch based on exposure number
#  NAME MINNITE  MAXNITE   MINEXPNUM  MAXEXPNUM
# -------------------------------- -------- -------- ---------- ----------
# SVE1 20120911 20121228 133757 164457
# SVE2 20130104 20130228 165290 182695
# Y1E1 20130815 20131128 226353 258564
# Y1E2 20131129 20140209 258621 284018
# Y2E1 20140807 20141129 345031 382973
# Y2E2 20141205 20150518 383751 438346
# Y3   20150731 20160212 459984 516846
#######################################333


# need to implement here handling of different "epochs" within the same year
if [ $EXPNUM -lt 165290 ]; then
    YEAR=sv
    EPOCH=e1
elif [ $EXPNUM -lt 226353 ]; then
    YEAR=sv
    EPOCH=e2
elif [ $EXPNUM -lt 258621 ]; then
    YEAR=y1
    EPOCH=e1
elif [ $EXPNUM -lt 345031 ]; then
    YEAR=y1
    EPOCH=e2
elif [ $EXPNUM -lt 383751 ]; then
    YEAR=y2
    EPOCH=e1
elif [ $EXPNUM -lt 459984 ]; then
    YEAR=y2
    EPOCH=e2
else
    YEAR=y3
    EPOCH=e1
fi

cat <<EOF >> confFile

[General]
nite: 20141229
expnum: 393047
filter: z
r: 04
p: 11
chiplist: 1,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,62
data_dir: /pnfs/des/scratch/gw/dts/
corr_dir: /pnfs/des/persistent/desdm/calib/
conf_dir: /pnfs/des/persistent/desdm/config/
exp_dir: /pnfs/des/scratch/gw/exp/
template: D{expnum:>08s}_{filter:s}_{ccd:>02s}_r{r:s}p{p:s}
exp_template: D{expnum:>08s}_{filter:s}_r{r:s}p{p:s}
year: y2
yearb: y2
epoch: e1
epochb: e1
[crosstalk]
xtalk =  DECam_20130606.xtalk
template =  D{expnum:>08s}_{filter:s}_%02d_r{r:s}p{p:s}_xtalk.fits
replace = DES_header_update.20151120

[pixcorrect]
bias = D_n20141020t1030_c{ccd:>02s}_r1471p01_biascor.fits
bpm = bpm_Y2A1_Y2epoch1_c{ccd:>02s}.fits
linearity = lin_tbl_v0.4.fits
bf = bfmodel_20150305.fits
flat = D_n20141020t1030_{filter:s}_c{ccd:>02s}_r1471p01_norm-dflatcor.fits

[sextractor]
filter_name = sex.conv
filter_name2 = sex.conv
starnnw_name  = sex.nnw
parameters_name = sex.param_scamp_psfex
configfile  = sexforscamp.config
parameters_name2 = sex.param.finalcut
configfile2 = sexgain.config

[skyCombineFit]
pcafileprefix = pca_mini

[skysubtract]
pcfilename = skytemp_{year:>2s}_{epoch:>2s}_{filter:s}_n04_c{ccd:>02s}.fits
weight = sky

[scamp]
imagflags =  0x0700
flag_mask =   0x00fd
flag_astr =   0x0000
catalog_ref =   UCAC-4
default_scamp =  default2.scamp.20140423
head =  {filter:s}no2no61.head

[starflat]
starflat  = {year:s}{epoch:s}_{filter:s}_{ccd:>02s}.fits

[psfex]
configfile = configoutcat2.psfex

EOF

sed -i -e "/^nite\:/ s/nite\:.*/nite\: ${NITE}/" -e "/^expnum\:/ s/expnum\:.*/expnum\: ${EXPNUM}/" -e "/^filter\:/ s/filter:.*/filter\: ${BAND}/" -e "/^r\:/ s/r:.*/r\: ${RNUM}/" -e "/^p\:/ s/p:.*/p\: ${PNUM}/" -e "/^year\:/ s/year:.*/year\: ${YEAR}/" -e "/^yearb\:/ s/yearb:.*/yearb\: ${YEAR}/" -e "/^epoch\:/ s/epoch:.*/epoch\: ${EPOCH}/"  -e "/^epochb\:/ s/epochb:.*/epochb\: ${EPOCH}/" confFile

if [ "$JUMPTOEXPCALIB" == "true" ] ; then
    echo "jumping to the calibration step..."
    nfiles=`ls *_r${RNUM}p${PNUM}_sextractor_psf.fits *_r${RNUM}p${PNUM}_immask.fits | wc -l`
    nccds=`grep chiplist confFile | awk -F ':' '{print $2}' | sed 's/,/ /g' | wc -w`
    nccds2=`expr $nccds \* 2`
    if [  $nfiles -ne $nccds2 ] ; then
	echo "copying fits files from Dcache"
	filestocopy1="`ifdh findMatchingFiles /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/ '*_r'${RNUM}'p'${PNUM}'_sextractor_psf.fits' | awk '{print $1}'`"
	filestocopy2="`ifdh findMatchingFiles /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/ '*_r'${RNUM}'p'${PNUM}'_immask.fits' | awk '{print $1}'`"
	ifdh cp -D $filestocopy1 $filestocopy2 .
    fi
else
    if [ "$SINGLETHREAD" == "true" ] ; then
	python run_desdmy1e2.py confFile 
    else
	python run_SEproc.py confFile 
    fi
    RESULT=$?
    if [ $RESULT -ne 0 ] ; then exit $RESULT ; fi
fi

setup expCalib

make_red_catlist

#### copy to here the relevant calib files:
ifdh cp -D /pnfs/des/scratch/marcelle/apass_2massInDESplus2.sorted.csv .
#### for now, we only have it in the DES footprint. 

##### testing my own version of GGG-expCalib
ifdh cp -D /pnfs/des/scratch/marcelle/GGG-expCalib_Y3apass.py .
ifdh chmod 775 ./GGG-expCalib_Y3apass.py
./GGG-expCalib_Y3apass.py -s desoper --expnum $EXPNUM --reqnum $RNUM --attnum $PNUM
#GGG-expCalib_Y3apass.py -s desoper --expnum $EXPNUM --reqnum $RNUM --attnum $PNUM
##### make that  the default version if this works.

RESULT=$?
ifdh cp -D allZP*.csv Zero*.csv D*CCDsvsZPs.png D*deltaZP.png D*NumClipstar.png D*ZP.png /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}
if [ $RESULT -ne 0 ] ; then exit $RESULT ; fi

# apply_expCalib.py
# RESULT=$?
# ifdh cp -D THECALIBRATEDCATALOG /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}
# if [ $RESULT -ne 0 ] ; then exit $RESULT ; fi

du -sh .
#rm -f *.fits *.fits.fz *.ps *.psf *.xml full_1.cat *.head
#rm *.csv *.png

export HOME=$OLDHOME

RESULT=$?

exit $RESULT

