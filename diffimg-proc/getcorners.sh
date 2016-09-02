#!/bin/bash

#call as:  getcorners.sh $EXPNUM $RPNUM $DATADIR 

source /cvmfs/des.opensciencegrid.org/2015_Q2/eeups/SL6/eups/desdm_eups_setup.sh

setup wcstools 3.8.7.1+2

umask 002

e=$1
RPNUM=$2
CORNERDIR=$3
DATADIR=$3
AWK=/bin/awk

# echo Getting corner coordinates for exposure ${e} ...
rm -f ${CORNERDIR}/${e}.out
for f in ${DATADIR}/D*_${RPNUM}_immask.fits
do
    echo f is $f
    filt=`gethead FILTER ${f} | cut -c1`
    ccd=`gethead CCDNUM ${f}`
    echo "16 16" > cornerxy.dat
    echo "16 4081" >> cornerxy.dat
    echo "2033 16" >> cornerxy.dat
    echo "2033 4081" >> cornerxy.dat
    ${WCSTOOLS_DIR}/bin/xy2sky -d ${f} @cornerxy.dat > tmp.tmp${e}
    coord=( `${AWK} '{printf "%10.5f %10.5f  ",$1,$2}' tmp.tmp${e}` )
    # output = ( Expo Band CCD RA1 Dec1 RA2 Dec2 RA3 Dec3 RA4 Dec4 )
    echo ${e} ${filt} ${ccd} ${coord[0]} ${coord[1]} ${coord[2]} ${coord[3]} ${coord[4]} ${coord[5]} ${coord[6]} ${coord[7]} | \
	${AWK} '{printf "%6d   %s   %2d  %10.5f %10.5f  %10.5f %10.5f  %10.5f %10.5f  %10.5f %10.5f\n",$1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11}' >> ${CORNERDIR}/${e}.out    
done
rm -f tmp.tmp${e}
ls ${CORNERDIR}/${e}.out


