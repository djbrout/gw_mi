#!/bin/bash

umask 002 

# check for an input argument

echo "Node information: `uname -a`"

if [ $# -lt 1 ]; then
echo "usage: RUN_DIFFIMG_PIPELINE.sh -E EXPNUM -r RPNUM -p DIFFPROCNUM -n NITE -b BAND -c CCDNUM [-v DIFFIMG_VERSION]"
exit 1
fi

ARGS="$@"
# we need to pull out expnum, chip, and band : KRH needs to double check syntax here

#rpnum="r1p1"
#procnum="dp91"
DIFFIMG_VERSION="gwdevel10" # can change this with parameter -v <diffimg_version>

##### Don't forget to shift the args after you pull these out #####
while getopts "E:c:b:n:r:p:v:" opt $ARGS
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
    c)
	    [[ $OPTARG =~ ^[0-9]+$ ]] || { echo "Error: CCD number must be an integer! You put $OPTARG" ; exit 1; }
	    [[ $OPTARG -lt 70 ]] || { echo "Error: the chip number must be less than 70. You entered $OPTARG." ; exit 1; }  
	    CCDNUM_LIST=$OPTARG
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
    :)
	    echo "Option -$OPTARG requires an argument."
	    exit 1
	    ;;
esac
done

ARGS="$@"

if [ "x$EXPNUM" == "x" ]; then
echo "Exposure number not set; exiting."
exit 1
fi
if [ "x$CCDNUM_LIST" == "x" ]; then
echo "CCD number not set; exiting."
exit 1
fi
if [ "x$BAND" == "x" ]; then
echo "Band not set; exiting."
exit 1
fi
if [ "x$rpnum" == "x" ]; then
echo "rpnum not set; exiting."
exit 1
fi
if [ "x$procnum" == "x" ]; then
echo "procnum not set; exiting."
exit 1
fi

OLDHOME=$HOME

export HOME=$PWD

### Force use of SLF6 versions for systems with 3.x kernels
case `uname -r` in
    3.*) export UPS_OVERRIDE="-H Linux64bit+2.6-2.12";;
    4.*) export UPS_OVERRIDE="-H Linux64bit+2.6-2.12";;
esac

#for IFDH
export EXPERIMENT=des
export PATH=${PATH}:/cvmfs/fermilab.opensciencegrid.org/products/common/db/../prd/cpn/v1_7/NULL/bin:/cvmfs/fermilab.opensciencegrid.org/products/common/db/../prd/ifdhc/v1_8_11/Linux64bit-2-6-2-12/bin
export PYTHONPATH=/cvmfs/fermilab.opensciencegrid.org/products/common/db/../prd/ifdhc/v1_8_11/Linux64bit-2-6-2-12/lib/python:${PYTHONPATH}
export IFDH_NO_PROXY=1
export IFDHC_LIB=/cvmfs/fermilab.opensciencegrid.org/products/common/prd/ifdhc/v1_8_11/Linux64bit-2-6-2-12/lib
export IFDH_GRIDFTP_EXTRA="-st 3600"
# for debugging

export IFDH_CP_MAXRETRIES=2


### now we want to make the local directory structure by copying in 

#copy some of the top dir list files and such


filestocopy="`ifdh findMatchingFiles /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/ 'SN_mon*.list' | awk '{print $1}'` `ifdh findMatchingFiles /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/ 'FILTERCHIP.LIST' | awk '{print $1}'` /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/PROCFILES.LIST  `ifdh findMatchingFiles /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/${BAND}_$(printf %02d ${CCDNUM_LIST})/ '*.lis' | awk '{print $1}'` /pnfs/des/scratch/gw/db-tools/desservices.ini /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/WS_diff.list /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/${EXPNUM}_run_inputs.tar.gz /pnfs/des/scratch/gw/code/WideSurvey_20150908.tar.gz"
# /pnfs/des/scratch/gw/code/makeWSTemplates_STARCUT_MAG.sh"

# we do not need /pnfs/des/scratch/gw/code/fakeLib_SNscampCatalog_SNautoScanTrainings_relativeZP.tar.gz as of 20 Sep 2015

#echo filestocopy = $filestocopy
 ifdh cp -D $filestocopy ./ || { echo "ifdh cp failed for SN_mon* and such" ; exit 1 ; }

#### makeWSTemplates.sh hack
#mkdir makeWSTemplates_STARCUT_MAG
#mv makeWSTemplates_STARCUT_MAG.sh makeWSTemplates_STARCUT_MAG/makeWSTemplates.sh
#chmod a+x  makeWSTemplates_STARCUT_MAG/makeWSTemplates.sh

datadirs=$(ifdh ls /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/data)

for dir in $datadirs
do
dpath=`echo $dir | sed -e 's/.*scratch\/gw\/exp\/'${NITE}'\/'${EXPNUM}'\///g'`
echo "dpath = $dpath"
case $dpath in
*/)
 mkdir -p $dpath
;;
*)
ifdh cp -D /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/data/$dir ./ || exit 2
;;
esac

done


#mkdir -p ${procnum}/${BAND}_`printf %02d $CCDNUM_LIST`
tar zxf ${EXPNUM}_run_inputs.tar.gz

LOCDIR="${procnum}/${BAND}_`printf %02d $CCDNUM_LIST`"

mkdir -p ${procnum}/input_files

# move the files from the first ifdh cp into the r1p1 dir to match what is in dCache
mv SN_mon*.list FILTERCHIP* PROCFILES.LIST ${procnum}/



inputfiles=$(ifdh ls /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/input_files/ )


for ifile in $inputfiles 
do
basefile=`basename $ifile`
#echo "basefile = $basefile"
if [ "${basefile}" == "input_files" ] || [ -z "$basefile" ]; then
    echo "skipping dir itself"
else
    ifdh cp -D /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/input_files/${basefile} ./${procnum}/input_files/ || exit 2
fi
done


#echo "check input_files:"
# ls -l r1p1/input_files/

# make symlinks to these files
ln -s ${procnum}/input_files/* .

###
#bandfiles=$(ifdh ls  /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${LOCDIR}/ )

#for ifile in $bandfiles
#do

#basefile=`basename $ifile`
#echo "basefile = $basefile"
#if [ "${basefile}" == "${BAND}_`printf %02d $CCDNUM_LIST`" ] || [ -z "$basefile" ]; then
#    echo "skipping dir itself"
#else
#    if [ "$basefile" == "headers" ] || [ "$basefile" == "ingest" ] || [[ "$basefile" == "stamps"* ]]; then
#	mkdir ${LOCDIR}/${basefile}
#    else
#	ifdh cp -D /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${LOCDIR}/${basefile}  ./${LOCDIR}/ || exit 2
#    fi
#fi
#done

mkdir ${LOCDIR}/headers ${LOCDIR}/ingest ${LOCDIR}/$(ifdh ls  /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${LOCDIR}/stamps* )

#echo "and how about $LOCDIR?"
#ls -l ./${LOCDIR}


 ln -s ${LOCDIR}/ingest ${LOCDIR}/stamps* ${LOCDIR}/headers .

#if [ -e ${CONDOR_DIR_INPUT}/templates_for_${EXPNUM}.sh ]; then
#    source ${CONDOR_DIR_INPUT}/templates_for_${EXPNUM}.sh
#else
#    echo "error, the template intput file is missing"
#fi


/cvmfs/grid.cern.ch/util/cvmfs-uptodate /cvmfs/des.opensciencegrid.org
source /cvmfs/des.opensciencegrid.org/2015_Q2/eeups/SL6/eups/desdm_eups_setup.sh
export EUPS_PATH=/cvmfs/des.opensciencegrid.org/eeups/fnaleups:$EUPS_PATH

# setup a specific version of perl so that we know what we're getting
setup perl 5.18.1+6 || exit 134

###### any additional required setups go here #####

#we will want the GW version of diffimg for sure
setup Y2Nstack 1.0.6+18
setup diffimg $DIFFIMG_VERSION #whatever the version number ends up being
setup ftools v6.17  # this is the heasoft stuff
export HEADAS=$FTOOLS_DIR
setup autoscan
setup easyaccess
setup extralibs 1.0
#export DIFFIMG_DIR=/data/des40.b/data/kherner/Diffimg-devel/diffimg-trunk
#export PATH=`echo $PATH | sed -e s#\/cvmfs\/des.opensciencegrid.org\/eeups\/fnaleups\/Linux64\/diffimg\/gwdevel#\/data\/des40.b\/data/kherner\/Diffimg-devel\/diffimg-trunk#`
#export DIFFIMG_DIR=/data/des41.a/data/marcelle/diffimg/DiffImg-trunk
#export PATH=`echo $PATH | sed -e s#\/cvmfs\/des.opensciencegrid.org\/eeups\/fnaleups\/Linux64\/diffimg\/gwdevel8#\/data\/des41.a\/data/marcelle\/diffimg\/DiffImg-trunk#`

echo "EUPS setup complete"


export DES_SERVICES=${PWD}/desservices.ini
export DES_DB_SECTION=db-sn-test
export DIFFIMG_HOST=FNAL
export SCAMP_CATALOG_DIR=/cvmfs/des.opensciencegrid.org/fnal/SNscampCatalog
export AUTOSCAN_PYTHON=$PYTHON_DIR/bin/python
export DES_ROOT=${PWD}/SNDATA_ROOT/INTERNAL/DES
export TOPDIR_SNFORCEPHOTO_IMAGES=${PWD}/data/DESSN_PIPELINE/SNFORCE/IMAGES
export TOPDIR_SNFORCEPHOTO_OUTPUT=${PWD}/data/DESSN_PIPELINE/SNFORCE/OUTPUT
export TOPDIR_DATAFILES_PUBLIC=${PWD}/data/DESSN_PIPELINE/SNFORCE/DATAFILES_TEST
export TOPDIR_WSTEMPLATES=${PWD}/WSTemplates
export TOPDIR_TEMPLATES=${PWD}/WSTemplates
export TOPDIR_SNTEMPLATES=${PWD}/SNTemplates
export TOPDIR_WSRUNS=${PWD}/data/WSruns
export TOPDIR_SNRUNS=${PWD}/data/SNruns

# these vars are for the make pair function that we pulled out of makeWSTemplates.sh
TOPDIR_WSDIFF=${TOPDIR_WSTEMPLATES}
DATADIR=${TOPDIR_WSDIFF}/data             # DECam_XXXXXX directories
CORNERDIR=${TOPDIR_WSDIFF}/pairs          # output XXXXXX.out and XXXXXX-YYYYYY.out
ETCDIR=${DIFFIMG_DIR}/etc                 # parameter files
CALDIR=${TOPDIR_WSDIFF}/relativeZP        # relative zeropoints
MAKETEMPLDIR=${TOPDIR_WSDIFF}/makeTempl   # templates are made in here

XY2SKY=${WCSTOOLS_DIR}/bin/xy2sky
AWK=/bin/awk

# snana stuff for fakes KRH: do we need this? comment out for now on sep 8
# export SNANA_DIR=/data/des20.b/data/kessler/snana/snana
# export SNDATA_ROOT=/data/des20.b/data/SNDATA_ROOT
# export PATH=${PATH}:${SNANA_DIR}/bin 
# export PATH=${PATH}:${SNANA_DIR}/util 

mkdir -p ${TOPDIR_SNFORCEPHOTO_IMAGES}
mkdir -p WSTemplates/data
mkdir SNTemplates
mkdir -p data/WSruns
mkdir -p data/SNruns
mkdir -p SNDATA_ROOT/INTERNAL/DES
mkdir -p ${TOPDIR_WSDIFF}/makeTempl
mkdir -p ${TOPDIR_WSDIFF}/pairs

mkdir -p ${TOPDIR_SNFORCEPHOTO_IMAGES}/${NITE} $DES_ROOT $TOPDIR_SNFORCEPHOTO_OUTPUT $TOPDIR_DATAFILES_PUBLIC



# now copy in the template files

#echo "source input copy"


# so now what we are going to do is copy in the .out files from the overlap_CCD part, and then use those to build the pairs, only 

#source ./r1p1/input_files/templates_for_${EXPNUM}.sh

echo "executing copy_pairs.sh at `date`"
source ./${procnum}/input_files/copy_pairs_for_${EXPNUM}.sh || { echo "Error in copy_pairs_for_${EXPNUM}.sh. Exiting..." ; exit 2 ; }

#show output of copy
echo "contents of pairs directory:"
ls $TOPDIR_WSTEMPLATES/pairs/

echo "------"

create_pairs() {
sexp=$EXPNUM
dtorad=`echo 45 | ${AWK} '{printf "%12.9f\n",atan2(1,1)/$1}'`
twopi=`echo 8 | ${AWK} '{printf "%12.9f\n",atan2(1,1)*$1}'`
echo "now in create_pairs: sexp = $sexp texp = $texp"
    outpair=${CORNERDIR}/${sexp}-${texp}.out
    outpairno=${CORNERDIR}/${sexp}-${texp}.no
  rm -f ${outpair}

      # loop over search CCDs
      nccd=`wc -l ${CORNERDIR}/${sexp}.out | ${AWK} '{print $1}'`
      i=1
      while [[ $i -le $nccd ]]
      do
    
        sccd=`${AWK} '(NR=='$i'){print $3}' ${CORNERDIR}/${sexp}.out`
         # Search CCD RA Dec corner coordinates coverted to radians
        info1=( `${AWK} '($3=='${sccd}'){printf "%10.7f %10.7f  %10.7f %10.7f  %10.7f %10.7f  %10.7f %10.7f\n",$4*"'"${dtorad}"'",$5*"'"${dtorad}"'",$6*"'"${dtorad}"'",$7*"'"${dtorad}"'",$8*"'"${dtorad}"'",$9*"'"${dtorad}"'",$10*"'"${dtorad}"'",$11*"'"${dtorad}"'"}' ${CORNERDIR}/${sexp}.out` )
   
        rm -f tmp.tmp1
        touch tmp.tmp1
 
       j=1
        while [[ $j -le  4 ]]  # loop over 4 corners of the search image chip
        do
   
          thisa=`echo $j | ${AWK} '{print 2*($1-1)}'`
          thisd=`echo $j | ${AWK} '{print 1+2*($1-1)}'`
   
          a1=${info1[$thisa]}
          d1=${info1[$thisd]}
   
          # calculate angular distance (in degrees) of the 4 sides of each CCD
          # ${texp}.out -> ${texp}.sides
          (${AWK} '{printf "%11.8f %11.8f  %11.8f %11.8f  %11.8f %11.8f  %11.8f %11.8f\n",$4*"'"${dtorad}"'",$5*"'"${dtorad}"'",$6*"'"${dtorad}"'",$7*"'"${dtorad}"'",$8*"'"${dtorad}"'",$9*"'"${dtorad}"'",$10*"'"${dtorad}"'",$11*"'"${dtorad}"'"}' ${CORNERDIR}/${texp}.out | ${AWK} '{printf "%10.8f %10.8f %10.8f %10.8f\n",sin($2)*sin($4)+cos($2)*cos($4)*cos($3-$1),sin($2)*sin($6)+cos($2)*cos($6)*cos($5-$1),sin($6)*sin($8)+cos($6)*cos($8)*cos($7-$5),sin($4)*sin($8)+cos($4)*cos($8)*cos($7-$3)}' | ${AWK} '{printf "%11.8f %11.8f %11.8f %11.8f\n",atan2(sqrt(1-$1*$1),$1),atan2(sqrt(1-$2*$2),$2),atan2(sqrt(1-$3*$3),$3),atan2(sqrt(1-$4*$4),$3)}' > ${texp}.sides) >& /dev/null
   
          # calculate angular distance from a1 d1 to each corner of template image
          # ${texp}.out -> ${texp}.dist
         (${AWK} '{printf "%11.8f %11.8f  %11.8f %11.8f  %11.8f %11.8f  %11.8f %11.8f   %2d\n",$4*"'"${dtorad}"'",$5*"'"${dtorad}"'",$6*"'"${dtorad}"'",$7*"'"${dtorad}"'",$8*"'"${dtorad}"'",$9*"'"${dtorad}"'",$10*"'"${dtorad}"'",$11*"'"${dtorad}"'",$3}' ${CORNERDIR}/${texp}.out | ${AWK} '{printf "%10.8f %10.8f %10.8f %10.8f  %2d\n",sin("'"${d1}"'")*sin($2)+cos("'"${d1}"'")*cos($2)*cos("'"${a1}"'"-$1),sin("'"${d1}"'")*sin($4)+cos("'"${d1}"'")*cos($4)*cos("'"${a1}"'"-$3),sin("'"${d1}"'")*sin($6)+cos("'"${d1}"'")*cos($6)*cos("'"${a1}"'"-$5),sin("'"${d1}"'")*sin($8)+cos("'"${d1}"'")*cos($8)*cos("'"${a1}"'"-$7),$9}' | ${AWK} '{printf "%11.8f %11.8f %11.8f %11.8f  %2d\n",atan2(sqrt(1-$1*$1),$1),atan2(sqrt(1-$2*$2),$2),atan2(sqrt(1-$3*$3),$3),atan2(sqrt(1-$4*$4),$4),$5}' > ${texp}.dist) >& /dev/null
   
          # 
          (paste ${texp}.sides ${texp}.dist | ${AWK} '{printf "%11.8f %11.8f %11.8f %11.8f  %2d\n",(cos($1)-cos($5)*cos($6))/(sin($5)*sin($6)),(cos($2)-cos($5)*cos($7))/(sin($5)*sin($7)),(cos($3)-cos($7)*cos($8))/(sin($7)*sin($8)),(cos($4)-cos($6)*cos($8))/(sin($6)*sin($8)),$9}' | ${AWK} '{printf "%11.8f %11.8f %11.8f %11.8f  %2d\n",atan2(sqrt(1-$1*$1),$1),atan2(sqrt(1-$2*$2),$2),atan2(sqrt(1-$3*$3),$3),atan2(sqrt(1-$4*$4),$4),$5}' | ${AWK} '($1<10)&&($2<10)&&($3<10)&&($4<10)&&($1+$2+$3+$4>"'"${twopi}"'"*0.95){printf "%6d  %2d  %6d  %2d\n","'"${sexp}"'","'"${sccd}"'","'"${texp}"'",$5}' >> tmp.tmp1) >& /dev/null
   
#          echo "template exposure = $texp; search CCD = $sccd; corner = $j"
    
          j=$[$j+1]

        done # while j [[ ...

        cat tmp.tmp1 | uniq > tmp.tmp2
	mv tmp.tmp2 tmp.tmp1
        n=`wc -l tmp.tmp1 | ${AWK} '{print $1}'`
        if [[ $n -eq 1 ]]
        then
          ${AWK} '(NR==1){printf "%6d  %2d  %6d %2d    %2d\n",$1,$2,$3,'${n}',$4}' tmp.tmp1 >> ${outpair}
        elif [[ $n -gt 1 ]]
        then
          ${AWK} '(NR==1){printf "%6d  %2d  %6d %2d    %2d",$1,$2,$3,'${n}',$4}' tmp.tmp1 >> ${outpair}
          ${AWK} '(NR>1){printf "  %2d",$4}' tmp.tmp1 >> ${outpair}
          echo hi | ${AWK} '{printf "\n"}' >> ${outpair}
        fi
	rm -f ${texp}.{sides,dist} tmp.tmp1
        i=$[$i+1]
      done #  sccd
   
     if [[ -f ${outpair} ]]
      then
        echo " ... has overlaps"
        haspairs[$e]=1
      else
        echo " ... has NO overlaps"
        touch ${outpairno}
        haspairs[$e]=0
      fi

  e=$[$e+1]

}  # end create_pairs


# figure out how many out files we have and make the pairs (exclude the search exposure.out from this list)


dotoutfiles=$(ls ${TOPDIR_WSDIFF}/pairs/*.out | grep -v "${EXPNUM}-" )
echo $dotoutfiles

if [ -z "$dotoutfiles" ]; then
 echo "Error, no .out files to make templates!!!"
fi

for dotoutfile in $dotoutfiles
do
texp=`basename $dotoutfile | sed -e s/\.out//`
echo "texp = $texp"

### link necessary as of diffimg gwdevel7
mkdir -p ${TOPDIR_WSDIFF}/pairs/$texp
ln -s $dotoutfile   ${TOPDIR_WSDIFF}/pairs/$texp/

#make the DECam_$temp_empty directory by default and remove it later if we actually have an overlap for this CCD
mkdir  ${TOPDIR_WSDIFF}/data/DECam_${texp}_empty
create_pairs
done

# now we have the searchexp-overlapexp.out files in the pairs directory so we parse them to see which template/CCD files we actually need in this job

ls ${TOPDIR_WSDIFF}/pairs/
# link necessary as of diffimg gwdevel7
    ln -s  ${TOPDIR_WSDIFF}/pairs/${EXPNUM}-*.out ${TOPDIR_WSDIFF}/pairs/${EXPNUM}-*.no ${TOPDIR_WSDIFF}/pairs/${EXPNUM}/

for overlapfile in `ls ${TOPDIR_WSDIFF}/pairs/${EXPNUM}-*.out`
do

    echo "Starting overlap file $overlapfile:"
    cat $overlapfile
    overlapexp=`basename $overlapfile | sed -e s/${EXPNUM}\-// -e s/\.out//`
    overlapccds=`awk '$2=='${CCDNUM_LIST}'{ for( f=5; f<=NF; f++) print $f}' $overlapfile`
    for overlapccd in $overlapccds
    do


	if [ -d  ${TOPDIR_WSDIFF}/data/DECam_${overlapexp}_empty ]; then
	    rmdir  ${TOPDIR_WSDIFF}/data/DECam_${overlapexp}_empty
	    fi
	if [ ! -d ${TOPDIR_WSDIFF}/data/DECam_${overlapexp} ]; then
	    mkdir  -p ${TOPDIR_WSDIFF}/data/DECam_${overlapexp}
	fi
	file2copy=$(ifdh ls /pnfs/des/scratch/gw/exp/*/${overlapexp}/D`printf %08d $overlapexp`_${BAND}_`printf %02d $overlapccd`_${rpnum}_immask.fits | grep fits)
	if [ -z "$file2copy" ] ; then
	    echo "WARNING: file for $overlapexp CCD $overlapccd did not appear in ifdh ls and was thus not copied in. Could be a problem."
	else
	    ifdh cp -D $file2copy ${TOPDIR_WSDIFF}/data/DECam_${overlapexp}/ || echo "Error in ifdh cp /pnfs/des/scratch/gw/exp/*/${overlapexp}/D`printf %08d $overlapexp`_${BAND}_`printf %02d $overlapccd`_${rpnum}_immask.fits WSTemplates/data/DECam_${overlapexp}/ !!!" 
	    cd  ${TOPDIR_WSDIFF}/data/DECam_${overlapexp}/
	    ln -s D`printf %08d $overlapexp`_${BAND}_`printf %02d $overlapccd`_${rpnum}_immask.fits DECam_`printf %08d ${overlapexp}`_`printf %02d $overlapccd`.fits
	    ln -s D`printf %08d $overlapexp`_${BAND}_`printf %02d $overlapccd`_${rpnum}_immask.fits DECam_`printf %06d ${overlapexp}`_`printf %02d $overlapccd`.fits
#### run delhead file DYOT to get around problem in image where the first part of the header is full and can't accept the FLXSCALE addition in RUN03
	    delhead  D`printf %08d $overlapexp`_${BAND}_`printf %02d $overlapccd`_${rpnum}_immask.fits DOYT
	fi
	cd ../../../
    done
done

# needed wide survey files
#ifdh cp -D /pnfs/des/scratch/gw/code/WideSurvey_20150908.tar.gz data/WSruns/

mv WideSurvey_20150908.tar.gz data/WSruns/
cd data/WSruns
tar xzf WideSurvey_20150908.tar.gz
cd -

#if [ "${procnum:0:3}" == "dp1" ]; then
#    ifdh cp -D /pnfs/des/scratch/gw/code/fakeLib_kherner_KNFakes_57279_noHost.tar.gz ./ || { echo "failure to copy fakeLib tarball!" ; exit 2; }
#    tar xzfm fakeLib_kherner_KNFakes_57279_noHost.tar.gz
#elif [  "${procnum:0:3}" == "dp2" ]; then
#    ifdh cp -D /pnfs/des/scratch/gw/code/fakeLib_kherner_KNFakes_57382_noHost.tar.gz ./ || { echo "failure to copy fakeLib tarball!" ; exit 2; }
#    tar xzfm fakeLib_kherner_KNFakes_57382_noHost.tar.gz
#else 
#    echo "No match to procnum! It should begin with dp1 or dp2 but it begins with ${procnum:0:3}"
#    exit 1
#fi

#untar fakeLib_SNscampCatalog_SNautoScanTrainings.tar.gz 2015-09-20 no longer needed ans it is all in CVMFS now. Just make a link in the relativeZP case
#tar xzf fakeLib_SNscampCatalog_SNautoScanTrainings_relativeZP.tar.gz
#mv relativeZP ${TOPDIR_WSDIFF}/
ln -s /cvmfs/des.opensciencegrid.org/fnal/relativeZP ${TOPDIR_WSDIFF}/

# we need a tarball of /data/des30.a/data/WSruns/WideSurvey, which should unwind in data/WSruns
echo "We are in $PWD"
cp ${LOCDIR}/RUN* ${LOCDIR}/run* ./
chmod a+x RUN[0-9]* RUN_ALL* RUN*COMPRESS*
rm *.DONE *.LOG

for runfile in `ls RUN* | grep -v DONE | grep -v LOG | grep -v ".sh"`
do
    sed -i -e "s@JOBDIR@${PWD}@g" $runfile
done

# have to set the PFILES variable to be a local dir and not something in CVMFS
cp -r ${FTOOLS_DIR}/syspfiles ./
export PFILES=${PWD}/syspfiles

# The WSp1_EXPNUM_FIELD_tileTILE_BAND_CCDNUM_LIST_mh.fits file MUST be in the CWD *and* it MUST be a file, not a symlink!!!!

# cp the list to WSTemplates 

# need to get the _diff.list* files in too! They go in WSTemplates/EXPNUM_LISTS/

mkdir WSTemplates/EXPNUM_LISTS
mv WS_diff.list WSTemplates/EXPNUM_LISTS/
# the list file WSTemplates/EXPNUM_LISTS

# for some reason SEXCAT.LIST is empty when created on des41. Touch it first and then link to it
touch ${LOCDIR}/INTERNAL_WSTemplates_SEXCAT.LIST
ln -s ${LOCDIR}/INTERNAL*.LIST .
ln -s ${LOCDIR}/INTERNAL*.DAT .


copyback() {


OUTFILES=""
for file in `ls ./RUN[0-9]* *.cat *.fits *out *LIST *numList *_ORIG ./RUN_ALL.LOG *.lis *.head INTERNAL*.DAT *.psf *.xml`
do
# only add files with non-zero size to copyback list: comment out for now 10-23-15
#if [ `stat -c %s $file` -gt 0 ]; then
    OUTFILES="$file $OUTFILES"
#fi
done

#set group write permission on the outputs just to be safe
chmod -R 664 $LOCDIR/*fits*

if [ $RESULT -ne 0 ]; then
    echo "FAILURE: Pipeline exited with status $RESULT "
# at least try to get the log files back
    if [ -z "${OUTFILES}" ]; then
	echo "No outfiles to copy back!"
    else
	ifdh cp -D $OUTFILES /pnfs/des/scratch/gw/exp/$NITE/$EXPNUM/$LOCDIR/
    fi
#exit $RESULT
fi

#make list of output files

export HOME=$OLDHOME

echo "outfiles = $OUTFILES"

ifdh cp -D $OUTFILES /pnfs/des/scratch/gw/exp/$NITE/$EXPNUM/$LOCDIR/ || echo "FAILURE: Error $? when trying to copy outfiles back" 

if [ `ls ${TOPDIR_SNFORCEPHOTO_OUTPUT} | wc -l` -gt 0 ]; then
    ifdh cp -r -D ${TOPDIR_SNFORCEPHOTO_OUTPUT} /pnfs/des/scratch/gw/exp/$NITE/$EXPNUM/$LOCDIR/ || echo "FAILURE: Error $? when copying  ${TOPDIR_SNFORCEPHOTO_OUTPUT}"
fi

if [ `ls ${TOPDIR_SNFORCEPHOTO_IMAGES}/${NITE} | wc -l` -gt 0 ]; then 
    copies=`ls ${TOPDIR_SNFORCEPHOTO_IMAGES}/${NITE}/ ` 
    ifdh mkdir /pnfs/des/scratch/gw/forcephoto/images/${procnum}/${NITE}/
    ifdh cp -D $copies /pnfs/des/scratch/gw/forcephoto/images/${procnum}/${NITE}/ || echo "FAILURE: Error $? when copying  ${TOPDIR_SNFORCEPHOTO_IMAGES}"
fi

### also copy back the stamps
###dp44/z_25/stamps_20150917_666-643_z_25
STAMPSDIR=`ls -d $LOCDIR/stamps_*`
echo "stamps dir: $STAMPSDIR"

if [ `ls $STAMPSDIR | wc -l` -gt 0 ] ; then
    copies=`ls $STAMPSDIR`
    cd  $STAMPSDIR
    ifdh cp -D $copies /pnfs/des/scratch/gw/exp/$NITE/$EXPNUM/$STAMPSDIR || echo "FAILURE: Error $? when copying  ${STAMPSDIR}"
    cd -
fi


IFDH_RESULT=$?
[[ $IFDH_RESULT -eq 0 ]] || echo "FAILURE: IFDH failed with status $IFDH_RESULT." 

} # end copyback


### makeWSTemplates.sh hack
#export PATH=${PWD}/makeWSTemplates_STARCUT_MAG:${PATH}
#echo "proof this is really here: "
#ls ${PWD}/makeWSTemplates_STARCUT_MAG
#echo "path to makeWSTemplates.sh is `which makeWSTemplates.sh`"

./RUN_ALL-${BAND}_`printf %02d ${CCDNUM_LIST}` $ARGS

#eventually we want
# perl ${DIFFIMG_DIR}/bin/RUN_DIFFIMG_PIPELINE.pl $ARGS NOPROMPT -writeDB
# we will leave -writeDB off for testing 1-Jul-2015
RESULT=$?



# now check the log files and find the first non-zero RETURN CODE

for logfile in `ls RUN[0-9]*.LOG`
do
CODE=`grep "RETURN CODE" $logfile | grep -v ": 0" | head -1`
if [ ! -z "${CODE}" ]; then
    echo $logfile $CODE
    exitcode=`echo $CODE | cut -d ":" -f 2`
    touch tmp.fail
    echo "$logfile : $CODE " >> tmp.fail
### uncomment this to enable failure on non-zero exit codes
#    exit $exitcode
fi
done
touch RUN_ALL.FAIL
if [ -f tmp.fail ] ; then 
    head -1 tmp.fail >> RUN_ALL.FAIL
    rm -f tmp.fail
else
    echo "NONE" >> RUN_ALL.FAIL
fi

copyback

exit $RESULT
