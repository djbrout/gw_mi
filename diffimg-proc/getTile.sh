#!/bin/bash

umask 002

##export LD_PRELOAD=/usr/lib64/libpdcap.so.1

# give an exposure number and generate a DAG to do our full chain. The structure is like so: 

# 1) Given exposure number, calculate which templates we need to run SE procoessing for. Store those in some list.
#
#  2) Check to see which of the templates has already been through SE processing, if any. Remove them from the list.
#
# 3) Set up standard output directory space in dCache and give appropriate permissions to the dirs
#
# 4) Start making the first stage of the DAG
# a) Create a set of parallel jobs that does the SE processing for the new exposure and all of its dependencies that haven't run yet (the list from steps 1-2.)
#    If all templates have already been through SE processing, this section will consist only of the SE processing for the new exposure
# b) at the end add a "dummy" serial jbos that does nothing except set up the proper dependency. It could send a mail or something saying that the SE steps are done
#
# 5) Make the second stage of the DAG
# a) now create 60 parallel jobs (one per chip) and run the full diffimg pipeline within that job
# b) each parallel job runs the same script, but takes the appropriate chip number (templates too?) as arguments
#
# 6) final stage of the DAG: single Runmon job to finalize everything
#
#
#   Visually, DAG is like this:
#
#
#   SEnewexp  SEtemplate1  SEtemplate2 ... SEtemplateN     (could be only SNnewexp if templates are already done)
#     \            |            |              /
#      \           |            |             /
#       \          |            |            /
#        \         |            |           /
#                
#                   dummy job
#                 /     |     \
#                /      |      \
#     Diffimg chip1   .....    Diffimg chip 62              
#                \      |      /
#                 \     |     /
#                RUNEND_monDiffimg  
#
#
#
#
#.

##### helper functions ######

fetch_noao() {

# first we need the RA and DEC of the image in question
full_imageline=$(egrep "^\s?${overlapnum}" exposures_${BAND}.list)

imageline=$(echo $full_imageline | awk '{print $4,$5}' )
PROPID=$( echo  $full_imageline | awk '{print $8}' )
SEARCHRA=`echo $imageline | cut -d " " -f 1`
SEARCHDEC=`echo $imageline | cut -d " " -f 2`

fetchurl="http://nsaserver.sdm.noao.edu:7001/?instrument=decam&obstype=object&proctype=raw&date=${overlapnite:0:4}-${overlapnite:4:2}-${overlapnite:6:2}&PROPOSAL=${PROPID}&FORMAT=image/fits&RELEASE_STATUS=public"

echo "fetchurl = $fetchurl"
curl -s $fetchurl -o votable_${overlapnum}.xml

sed -i -e s/datatype=\"date\"/datatype=\"char\"/ -e 's/\,/ /g' votable_${overlapnum}.xml

cat <<EOF > get_images_${overlapnum}.py
#!/usr/bin/python
from astropy.io.votable import parse_single_table
from subprocess import Popen
import sys
import os
import math
import subprocess
table=parse_single_table("votable_${overlapnum}.xml")
RA =  $SEARCHRA
DEC = $SEARCHDEC
SEARCHEXP = $overlapnum
j=0
k=0
not_end=1
s_url =[]
s_crval = []
dists = []
while not_end:
    s_url0 = None
    s_crval0 = None
    try:
       s_url0=table.array['access url'][j]
       s_crval0=table.array['CRVAL'][j]
#       print s_url0, s_crval0
    except IndexError:
       not_end=0
#    print s_url0
    if s_url0 != None:    
        s_url1=s_url0.replace("7006","7003")
#        s_url1=s_url0.replace("7506","7003")
        i=s_url1.find("&extension")
        s_url2=s_url1[0:i]
        RADIFF = float(s_crval0[0]) - RA
        # beware the wraparound problem...
        if RADIFF > 180.0 : RADIFF -= 360.0 
        if RADIFF < -180.0 : RADIFF += 360.0 
        DECDIFF = float(s_crval0[1]) - DEC
        if abs(RADIFF) <= 0.1 and abs(DECDIFF) <= 0.1 :
            if s_url2 not in s_url:
                dist=math.hypot(RADIFF,DECDIFF)
                insert_index = 0
                for ii in range(0,len(dists)):
                    if dists[ii] < dist: insert_index +=1
                dists.insert(insert_index, dist)
                s_url.insert(insert_index, s_url2)
                s_crval.insert(insert_index, s_crval0)
 #               print j,  s_url[k], s_crval[k]
                k=k+1
    j=j+1
#
##download files using curl
n_files=0
n_files=k
if n_files < 1:
    print('Error, no images to download!\n')
    sys.exit(1)
print "There are %d image files"  % n_files 
for ifile in range(0,n_files):
     i_fname=s_url[ifile].find("=")
     fname=s_url[ifile][i_fname+1:]
     print "\n **********retreiving image %d " % ifile, s_url[ifile]
     finfile=s_url[ifile]
     print finfile, fname
     expstring=""
     try:
         os.system("curl "+ finfile +" -o " + fname)
     except:
         print("Error downloading file from noao!\n" )
         continue
     #### check if this is really the image that we want
     funhead=subprocess.Popen(["/home/s1/marcelle/bin/funhead",fname],stdout=subprocess.PIPE)
     grepcmd=subprocess.Popen(["grep","EXPNUM"],stdin=funhead.stdout,stdout=subprocess.PIPE)
     funhead.stdout.close()
     expstring=grepcmd.communicate()[0]
     try:
         expstring=expstring.split()[2]
     except:
         print("No EXPNUM in header\n")
         expstring="-1"
     print expstring + "\n"  
     if int(expstring) == SEARCHEXP :
         try:
             os.system("cp " + fname + " /pnfs/des/scratch/gw/dts/${overlapnite}/DECam_00${overlapnum}.fits.fz")
         except:
             print("Error copying file into dCache!\n")
         finally:
             os.system("rm " + fname)
             break # we found the right exposure; no point in looking at the others

     os.system("rm " + fname)   

EOF

python get_images_${overlapnum}.py

return $?

}

check_header() {

# we need to see if the "OBJECT" field in the image header in dCache contains the word "hex". If it does not then we need to 
# replace that field in the header with "DESGW hex $FIELD tiling 1"

IMGOBJECT=$(gethead /pnfs/des/scratch/gw/dts/${NITE}/DECam_`printf %08d ${EXPNUM}`.fits.fz OBJECT)
IMGTILING=$(gethead /pnfs/des/scratch/gw/dts/${NITE}/DECam_`printf %08d ${EXPNUM}`.fits.fz TILING)

if [ -z "`echo $IMGOBJECT | grep hex`" ] || [ -z "${IMGTILING}" ]; then
    
   ### first copy the file down
    $COPYDCMD /pnfs/des/scratch/gw/dts/${NITE}/DECam_`printf %08d ${EXPNUM}`.fits.fz ./ && rm -f /pnfs/des/scratch/gw/dts/${NITE}/DECam_`printf %08d ${EXPNUM}`.fits.fz
    if [ -z "${IMGTILING}" ]; then
	sethead DECam_`printf %08d ${EXPNUM}`.fits.fz TILING=${tiling}
    fi
    if [ -z "`echo $IMGOBJECT | grep hex`" ]; then
	NEWOBJECT="DESGW hex $FIELD tiling $tiling"	
	sethead DECam_`printf %08d ${EXPNUM}`.fits.fz OBJECT="${NEWOBJECT}" 
    fi

    $COPYCMD DECam_`printf %08d ${EXPNUM}`.fits.fz /pnfs/des/scratch/gw/dts/${NITE}/DECam_`printf %08d ${EXPNUM}`.fits.fz

    if [ $? -eq 0 ]; then
	rm DECam_`printf %08d ${EXPNUM}`.fits.fz
    else
        echo "Error copying edited file DECam_`printf %08d ${EXPNUM}`.fits.fz back to dCache!"
	rm DECam_`printf %08d ${EXPNUM}`.fits.fz
	exit 1 
    fi
fi # if [ -z "`echo $IMGOBJECT | grep hex`" ] || [ -z"${TILING}" ]; then

# no else because if hex is already in the OBJECT field in the image header, we are satisfied
}

#### making the dag ####

# read the search exposure number
if [ $# -lt 1 ]; then echo "Error, an exposure number must be supplied" ; exit 1; fi
ALLEXPS="$@"
EXPNUM=$1
[[ $EXPNUM =~ ^[0-9]+$ ]] || { echo "Error, exposure number must be a number; you entered $EXPNUM." ; exit 1; }
echo "EXPNUM = $EXPNUM"

# check that all necessary files exist:
requiredfiles=( ~/.pgpass ~/.desservices.ini ~/.wgetrc-desdm )
for requiredfile in ${requiredfiles[*]}
do
    if [ ! -f $requiredfile ] ; then echo "Error: $requiredfile not found." ; exit 2 ; fi
done

# check also the optional files:
optionalfiles=( ./dagmaker.rc )
if [ ! -f $optionalfile ] ; then echo "Warning: $optionalfile not found." ; fi 

# set default parameters
RNUM="2"
PNUM="01"
SEASON="11"
JOBSUB_OPTS="--mail_on_error --email-to=kherner@fnal.gov"
RESOURCES="DEDICATED,OPPORTUNISTIC,OFFSITE,SLOTTEST"
DIFFIMG_EUPS_VERSION="gwdevel10"
JOBSUB_OPTS_SE="--memory=3000MB --expected-lifetime=medium --cpu=4"
WRITEDB="off"
IGNORECALIB="false"

# overwrite defaults if user provides a .rc file
DAGMAKERRC=./dagmaker.rc
if [ -f $DAGMAKERRC ] ; then
    echo "Reading params from config file: $DAGMAKERRC"
    source $DAGMAKERRC
fi

# set processing versions
procnum="dp$SEASON"
rpnum="r"$RNUM"p"$PNUM

# print params used in this run
echo "----------------"
echo "SEASON = $SEASON => DIFFIMG proc. version is $procnum"
echo "RNUM = $RNUM , PNUM = $PNUM  => SE proc. version is $rpnum"
echo "WRITEDB = $WRITEDB (default is WRITEDB=off; set WRITEDB=on if you want outputs in db)"  
echo "IGNORECALIB = $IGNORECALIB (default is false)"
echo "JOBSUB_OPTS = $JOBSUB_OPTS"
echo "JOBSUB_OPTS_SE = $JOBSUB_OPTS_SE"
echo "RESOURCES = $RESOURCES"
echo "DIFFIMG_EUPS_VERSION = $DIFFIMG_EUPS_VERSION"
echo "----------------"

### dummy job
cat <<EOF > dummyjob.sh
echo "I do not actually do anything except say hello."
exit 0
EOF
chmod a+x dummyjob.sh

echo "set up environment, and handy commands"

# pull the setps from setup-diffImg
. /cvmfs/des.opensciencegrid.org/2015_Q2/eeups/SL6/eups/desdm_eups_setup.sh
export EUPS_PATH=/cvmfs/des.opensciencegrid.org/eeups/fnaleups:$EUPS_PATH

# setup a specific version of perl so that we know what we're getting
setup perl 5.18.1+6 || exit 134

# setup other useful packages and env variables
setup Y2Nstack
setup diffimg $DIFFIMG_EUPS_VERSION
setup ftools v6.17
export HEADAS=$FTOOLS_DIR
setup autoscan
setup astropy
export DIFFIMG_HOST=FNAL
#for IFDH
export EXPERIMENT=des
export PATH=${PATH}:/cvmfs/fermilab.opensciencegrid.org/products/common/db/../prd/cpn/v1_7/NULL/bin:/cvmfs/fermilab.opensciencegrid.org/products/common/prd/ifdhc/v1_8_11/Linux64bit-2-6-2-12/bin
export PYTHONPATH=${PYTHONPATH}:/cvmfs/fermilab.opensciencegrid.org/products/common/prd/ifdhc/v1_8_11/Linux64bit-2-6-2-12/lib/python
export IFDH_NO_PROXY=1

# setup handy  commands
COPYCMD="ifdh cp"
COPYDCMD="ifdh cp -D"
CHMODCMD="ifdh chmod 775"
RMCMD="ifdh rm"
#allow people logged in as desgw to do a straight cp to /pnfs to avoid long lock times
if [ "${USER}" == "desgw" ]; then
COPYCMD="cp"
COPYDCMD="cp"
CHMODCMD="chmod g+w"
RMCMD="rm -f"
fi

echo "prep the list files"

# create the exposures.list file, if it doesn't already exist
if [ ! -f exposures.list ]; then
    ./getExposureInfo.sh
    # and remove the diff.list2 to make sure it stays in sync with the new .list file
    rm -f ./mytemp_${EXPNUM}/KH_diff.list2
fi
BAND=`egrep "^\s?${EXPNUM}" exposures.list | awk '{print $6}'`
if [ -z "${BAND}" ]; then
    echo "Error with setting band. Check exposures.list to see if there is a problem with this exposure. Exiting..."
    exit 1
fi

echo "figure out overlaps"

# now run the single exposure script to get the overlaps
if [ ! -d mytemp_${EXPNUM} ] ; then
    mkdir mytemp_${EXPNUM}
fi
cd mytemp_${EXPNUM}
ln -s ../exposures_${BAND}.list .
if [ ! -f KH_diff.list2 ] ; then 
    ../getOverlaps_single_expo.csh ../exposures_${BAND}.list $EXPNUM
fi
cd ..

echo "start composing the dag"

# create the output dag file (empty)
outfile=desgw_pipeline_${EXPNUM}.dag
if [ -f $outfile ]; then
    rm $outfile   # maybe we don't want to overwrite? think about that a bit
fi
touch $outfile

# create the output copy_pairs file (empty)
templatecopyfile="copy_pairs_for_${EXPNUM}.sh"
if [ -f $templatecopyfile ]; then
    rm $templatecopyfile   # maybe we don't want to overwrite? think about that a bit
fi
touch $templatecopyfile

# begin composing the dag 
echo "<parallel>" >> $outfile

# stick a dummy job in here so that there is something just in case there ends up being nothing to do for parallel processing
echo "jobsub -n --group=des --OS=SL6  --resource-provides=usage_model=${RESOURCES} --memory=500MB --disk=100MB --expected-lifetime=600s $JOBSUB_OPTS file://dummyjob.sh" >> $outfile

# initialize empty list of files for the copy pairs output
DOTOUTFILES=""

echo "loop over the diff list of exposures"

NOVERLAPS=$(awk '{print NF-2}' mytemp_${EXPNUM}/KH_diff.list1)
# now loop over the diff list, get info about the overlaping exposures, and set the SE portion of the dag
for((i=1; i<=${NOVERLAPS}; i++)) 
do
    # get expnum, nite info
    overlapnum=$(awk "NR == $i {print \$1}" mytemp_${EXPNUM}/KH_diff.list2)
    overlapnite=$(awk "NR == $i {print \$2}" mytemp_${EXPNUM}/KH_diff.list2)

    # try to use this exposure 
    SKIP=false

    # check that exposure is 30 seconds or longer
    explength=$(egrep "^\s?${overlapnum}" exposures.list | awk '{print $7}')
    explength=$(echo $explength | sed -e 's/\.[0-9]*//' )
    if [ $explength -lt 30 ]; then SKIP=true ; fi

    # check that exposure's t_eff is greater than 0.25
    # need to implement this at some point, for now just set it to 1 and move on
    teff="1.0"
    if (( $(echo "$teff < 0.25" | bc -l) )); then SKIP=true ; fi

    # the first image in the list is the search image itself
    if [ $i == 1 ]; then 
	if [ "$SKIP" == "true" ] ; then echo "Cannot proceed without the search image!" ; exit 1 ; fi
	NITE=$overlapnite  # capitalized NITE is the search image nite
    fi
    
    # image failed quality tests ; try the next exposure in the list
    if [ "$SKIP" == "true" ] ; then echo "Overlap exposure $overlapnum failed quality criteria. Skipping." ; continue ; fi

    #### at this point, the image passed basic quality cuts. let's now check if it was not already SE processed:

    echo -e "\noverlapnum = ${overlapnum} , overlapnite = ${overlapnite} , explength = $explength, teff = $teff"

    # ls in the dcache scratch area to see if images are already there
    nfiles=0    
    for file in `ls /pnfs/des/scratch/gw/exp/${overlapnite}/${overlapnum}/*_${rpnum}_immask.fits*`
    do
	if [ `stat -c %s $file` -gt 0 ]; then nfiles=`expr $nfiles + 1` ; touch $file ; fi	
    done

    # ls in the dcache scratch area to see if sextractor files are already there
    mfiles=0    
    for file in `ls /pnfs/des/scratch/gw/exp/${overlapnite}/${overlapnum}/*_${rpnum}_sextractor_psf.fits*`
    do
	if [ `stat -c %s $file` -gt 0 ]; then mfiles=`expr $mfiles + 1` ; touch $file ; fi	
    done

    # if number of reduced images and sextractor catalogs is not the same, something looks fishy. set nfiles=0 to force reprocessing 
    if [ $mfiles -ne $nfiles ] ; then nfiles=0 ; fi

    # check the .out file too
    if [ -e /pnfs/des/scratch/gw/exp/${overlapnite}/${overlapnum}/${overlapnum}.out ]; then
	touch /pnfs/des/scratch/gw/exp/${overlapnite}/${overlapnum}/${overlapnum}.out 
    else
	# if all the fits files are there, try to produce the missing .out file quickly
	if [ $nfiles -ge 59 ] ; then
	    ./getcorners.sh $EXPNUM $rpnum /pnfs/des/scratch/gw/exp/${overlapnite}/${overlapnum}
	    if [ $? -ne 0 ] ; then 
		echo "Warning: Missing .out file: /pnfs/des/scratch/gw/exp/${overlapnite}/${overlapnum}/${overlapnum}.out" 
		# assume something went wrong with the previous SE proc for this image. set nfiles=0 to force reprocessing
		nfiles=0
	    fi
	fi
    fi

    # check if calibration outputs are present
    JUMPTOEXPCALIBOPTION=""
    if [ -e /pnfs/des/scratch/gw/exp/${overlapnite}/${overlapnum}/allZP_D`printf %08d ${overlapnum}`_${rpnum}.csv ]; then
	touch /pnfs/des/scratch/gw/exp/${overlapnite}/${overlapnum}/allZP_D`printf %08d ${overlapnum}`_${rpnum}.csv 
    else
        # if only the expCalib outputs are missing and we are not allowed to ignore them
        if [ $nfiles -ge 59 ] && [ "$IGNORECALIB" == "false" ] ; then
            # assume something went wrong with the previous SE proc for this image (set nfiles=0 to force reprocessing)
	    nfiles=0
	    # but assume that only calibration step needs to be done for this exposure
            JUMPTOEXPCALIBOPTION="-j"
            echo "Warning: Missing outputs of expCalib. Will jump directly to the calibration step for this image."
        fi
    fi
        
    # if there are 59+ files with non-zero size, a .out file, and expCalib outputs, then don't do the SE job again for that exposure     
    if [ $nfiles -ge 59 ]; then
	echo "SE proc. already complete for exposure $overlapnum"
        echo "Add the .out file for this overlap image to the list to be copied"
	DOTOUTFILES="${DOTOUTFILES} /pnfs/des/scratch/gw/exp/$overlapnite/$overlapnum/${overlapnum}.out"
	continue
    fi

    #### at this point we have determined that we need to run SE proc for this exposure. so let's add it to the dag:

    # make sure that the directory for the raw image exists and has the appropriate permissions
    if [ ! -d /pnfs/des/scratch/gw/dts/${overlapnite}/ ]; then
	mkdir /pnfs/des/scratch/gw/dts/${overlapnite}/
	chmod 775  /pnfs/des/scratch/gw/dts/${overlapnite}/
    fi

    # check if the raw image is present so that the SE processing can run. If it isn't, try to pull it over from des30.b, des51.b, NCSA DESDM, NOAO archive		
    if [ -e /pnfs/des/scratch/gw/dts/${overlapnite}/DECam_`printf %08d ${overlapnum}`.fits.fz ]; then
	echo "Raw image present in dCache"
    else	    
	if [ -e /data/des30.b/data/DTS/src/${overlapnite}/src/DECam_`printf %08d ${overlapnum}`.fits.fz ]; then
	    echo "Raw image not present in dcache; transferring from /data/des30.b"		
	    $COPYCMD /data/des30.b/data/DTS/src/${overlapnite}/src/DECam_`printf %08d ${overlapnum}`.fits.fz /pnfs/des/scratch/gw/dts/${overlapnite}/DECam_`printf %08d ${overlapnum}`.fits.fz || { echo "cp failed!" ; exit 2 ; }
	else 
	    if [ -e /data/des51.b/data/DTS/src/${overlapnite}/DECam_`printf %08d ${overlapnum}`.fits.fz ]; then
		echo "Raw image not present in dCache or /data/des30.b; trying from des51.b"
		$COPYCMD /data/des51.b/data/DTS/src/${overlapnite}/DECam_`printf %08d ${overlapnum}`.fits.fz /pnfs/des/scratch/gw/dts/${overlapnite}/DECam_`printf %08d ${overlapnum}`.fits.fz || { echo "cp failed!" ; exit 2 ; }
	    else 
		echo " Raw image for exposure $overlapnum not in dcache and not in /data/des30.b or /data/des51.b. Try to tansfer from NCSA..."
		export WGETRC=$HOME/.wgetrc-desdm
		if [ ! -f $WGETRC ] ; then echo "Warning: Missing file $HOME/.wgetrc-desdm may cause wget authentication error." ; fi
		wget --no-check-certificate -nv https://desar2.cosmology.illinois.edu/DESFiles/desarchive/DTS/raw/${overlapnite}/DECam_`printf %08d ${overlapnum}`.fits.fz 
		if [ $? -eq 0 ] ; then
		    $COPYDCMD DECam_`printf %08d ${overlapnum}`.fits.fz /pnfs/des/scratch/gw/dts/${overlapnite}/ && rm DECam_`printf %08d ${overlapnum}`.fits.fz
		else
		    echo "wget failed! Will try to get image $overlapnum $overlapnite from NOAO."			
		    fetch_noao
		    if [ $? -ne 0 ]; then
			echo "Failure in fetching from NOAO!"
			if [ $i == 1 ] ; then echo "Cannot proceed without the search image!" ; exit 2 ; fi
			SKIP=true
			echo "Unable to find raw image for overlapping exposure: $overlapnum ; will try to proceed without it."

			###### remove the overlap from the diff.list file
			sed -i -e "s/${overlapnum}//"  mytemp_${EXPNUM}/KH_diff.list1
			# we also need to reduce the count in the first field of KH_diff.list1 by one
			OLDCOUNT=`awk '{print $1}'  mytemp_${EXPNUM}/KH_diff.list1`
			NEWCOUNT=$((${OLDCOUNT}-1))
			sed -i -e s/${OLDCOUNT}/${NEWCOUNT}/  mytemp_${EXPNUM}/KH_diff.list1 
			continue
		    fi
		fi
	    fi
	fi
    fi

    # add the SE_job to the dag
####################
# the old way was to create one file per job, using sed to change the relevant variables: 
#    sed -e "/^nite\:/ s/nite\:.*/nite\: ${overlapnite}/" -e "/^expnum\:/ s/expnum\:.*/expnum\: ${overlapnum}/" -e "/^filter\:/ s/filter:.*/filter\: ${BAND}/" -e "/^r\:/ s/r:.*/r\: ${RNUM}/" -e "/^p\:/ s/p:.*/p\: ${PNUM}/" -e s/THEEXP/${overlapnum}/ -e s/THER/${RNUM}/ -e s/THEP/${PNUM}/ -e s/THENITE/${overlapnite}/ job_SNy1e2.in > SE_job_${overlapnum}_${overlapnite}.sh
#    chmod a+x SE_job_${overlapnum}_${overlapnite}.sh
#    echo "jobsub -n --group=des --OS=SL6 --resource-provides=usage_model=${RESOURCES} $JOBSUB_OPTS $JOBSUB_OPTS_SE file://SE_job_${overlapnum}_${overlapnite}.sh " >> $outfile
# the new way is to use one single SE_job.sh file and pass the values as parameters:
    echo "jobsub -n --group=des --OS=SL6 --resource-provides=usage_model=${RESOURCES} $JOBSUB_OPTS $JOBSUB_OPTS_SE file://SE_job.sh -r $RNUM -p $PNUM -E $overlapnum -b $BAND -n $overlapnite $JUMPTOEXPCALIBOPTION" >> $outfile
####################

    # add the .out file for this overlap image to the list to be copied
    DOTOUTFILES="${DOTOUTFILES} /pnfs/des/scratch/gw/exp/$overlapnite/$overlapnum/${overlapnum}.out"

done # end of loop over list of overlapping exposures

echo "end of loop over list of overlapping exposures"

# close the SE portion of the dag
echo "</parallel>" >> $outfile

# write the full copy command for the .out files and other auxfiles
echo "ifdh cp -D $DOTOUTFILES \$TOPDIR_WSTEMPLATES/pairs/" > $templatecopyfile

# copy over the desservices.ini file, if not already there
if [ -e /pnfs/des/scratch/gw/db-tools/desservices.ini ] ; then
    touch /pnfs/des/scratch/gw/db-tools/desservices.ini
else
    $COPYDCMD ~/.desservices.ini /pnfs/des/scratch/gw/db-tools
fi

# copy over the run_SEproc.py file. 
if [ -e /pnfs/des/scratch/marcelle/run_SEproc.py ] ; then
    $RMCMD  /pnfs/des/scratch/marcelle/run_SEproc.py
fi
$COPYDCMD run_SEproc.py /pnfs/des/scratch/marcelle
$CHMOD /pnfs/des/scratch/marcelle/run_SEproc.py

# copy over the run_SEproc_noSkySub.py file. 
if [ -e /pnfs/des/scratch/marcelle/run_SEproc_noSkySub.py ] ; then
    $RMCMD  /pnfs/des/scratch/marcelle/run_SEproc_noSkySub.py
fi
$COPYDCMD run_SEproc_noSkySub.py /pnfs/des/scratch/marcelle
$CHMOD /pnfs/des/scratch/marcelle/run_SEproc_noSkySub.py

# compose the "catalog prep" portion of the dag, which jobs to run after all SE jobs are done
# need to replace the dummyjob.sh with the real thing at some point!
echo "<serial>" >> $outfile
echo "jobsub -n --group=des --OS=SL6  --resource-provides=usage_model=${RESOURCES} --memory=500MB --disk=100MB --expected-lifetime=600s $JOBSUB_OPTS file://dummyjob.sh" >> $outfile
echo "</serial>" >> $outfile

# start the diffimg portion of the dag
echo "<parallel>" >> $outfile

# One paraellel job for each of the chips in the new image
for (( ichip=1;ichip<63;ichip++ ))
do
    if [ $ichip -ne 2 ] && [ $ichip -ne 31 ] && [ $ichip -ne 61 ] ; then
	echo "jobsub -n --group=des --OS=SL6  --resource-provides=usage_model=${RESOURCES} $JOBSUB_OPTS --expected-lifetime=18000s file://RUN_DIFFIMG_PIPELINE.sh -r $rpnum -p $procnum -E $EXPNUM -c $ichip -b $BAND -n $NITE -v $DIFFIMG_EUPS_VERSION" >> $outfile
    fi    
done

# close the diffimg portion of the dag
echo "</parallel>" >> $outfile

echo "run RUN_DIFFIMG_PIPELINE.pl with no nodelist to set up the directory structure and make the scripts"

#### Now we run RUN_DIFFIMG_PIPELINE.pl with no nodelist to set up the directory structure and make the scripts

#export DIFFIMG_DIR=/data/des40.b/data/kherner/Diffimg-devel/diffimg-trunk
#export PATH=`echo $PATH | sed -e s#\/cvmfs\/des.opensciencegrid.org\/eeups\/fnaleups\/Linux64\/diffimg\/gwdevel[0-9][0-9]#\/data\/des40.b\/data/kherner\/Diffimg-devel\/diffimg-trunk#`
#export DIFFIMG_DIR=/data/des41.a/data/marcelle/diffimg/DiffImg-trunk
#export PATH=`echo $PATH | sed -e s#\/cvmfs\/des.opensciencegrid.org\/eeups\/fnaleups\/Linux64\/diffimg\/gwdevel8#\/data\/des41.a\/data/marcelle\/diffimg\/DiffImg-trunk#`

export DES_SERVICES=~/.desservices.ini
export DES_DB_SECTION=db-sn-test
export SCAMP_CATALOG_DIR=/cvmfs/des.opensciencegrid.org/fnal/SNscampCatalog
export AUTOSCAN_PYTHON=$PYTHON_DIR/bin/python

#this gets the fake DB version file
### make sure that this is still there!!! if not check des41
export DES_ROOT=/data/des20.b/data/SNDATA_ROOT/INTERNAL/DES

export TOPDIR_SNFORCEPHOTO_IMAGES=data/DESSN_PIPELINE/SNFORCE/IMAGES
export TOPDIR_SNFORCEPHOTO_OUTPUT=data/DESSN_PIPELINE/SNFORCE/OUTPUT
export TOPDIR_DATAFILES_PUBLIC=data/DESSN_PIPELINE/SNFORCE/DATAFILES_TEST
export TOPDIR_TEMPLATES=/data/des30.a/data/WSTemplates

FIELD_TILING=$( egrep "^\s?${EXPNUM}" exposures.list | sed -e 's/.*DES.*hex //' -e 's/tiling//' -e s/\"// )

############ check and do something special if the word hex is not present ############

if [ `echo $FIELD_TILING | awk '{print $1}'` == $EXPNUM ]; then
# In this case field will be GW(RA*10)(DEC*10) with either + or - for the dec.   and the tiling will be 1

echo "FIELD is currently set to the exposure number. This is mostly likely because the image doesn't have \"hex\" in the description. Setting FIELD according to new scheme."
imageline=$(egrep "^\s?${EXPNUM}" exposures_${BAND}.list | awk '{print $4,$5}' )
SEARCHRA=`echo $imageline | cut -d " " -f 1`
SEARCHDEC=`echo $imageline | cut -d " " -f 2`
RA10=$(echo "${SEARCHRA}*10" | bc | cut -d "." -f 1)
DEC10=$(echo "$SEARCHDEC * 10" | bc | cut -d "." -f 1)
if [ $DEC10 -ge 0 ]; then 
    DEC10="+${DEC10}"
fi
FIELD="GW${RA10}${DEC10}"
TILING=1
FIELD_TILING="${FIELD} ${TILING}"
check_header

######### 

else
FIELD=$( echo $FIELD_TILING | cut -d " " -f 1)
TILING=$( echo $FIELD_TILING | cut -d " " -f 2)
echo "FIELD = $FIELD"
echo "TILING = $TILING"
if [ "x${TILING}" == "x" ]; then
    echo "TILING not set because it was not in the database. Defaulting to 1."
    TILING=1
fi
if [ "$FIELD" == "$TILING" ]; then
    echo "FIELD and TILING are the same value ($FIELD)! This is probably because the field doesn't say 'something tiling something'."
    echo " Setting TILING to 1 in this case."
    TILING=1
fi
fi

# Add the runmon step at the end of the dag. wait until now because we need to determine the field first
echo "<serial>" >> $outfile
echo "jobsub -n --group=des --OS=SL6  --resource-provides=usage_model=$RESOURCES $JOBSUB_OPTS --expected-lifetime=7200 file://RUNMON.sh -r $rpnum -p $procnum -E $EXPNUM -n $NITE -f $FIELD" >> $outfile
echo "</serial>" >> $outfile

# edit the template files to match this exposure

sed -e s/THENITE/$NITE/ -e s/THEBAND/${BAND}/ -e s/THEEXP/${EXPNUM}/ -e s/THEFIELD/${FIELD}/ -e s/THEPROCNUM/${procnum}/ -e s/THESEASON/${SEASON}/ MAKESCRIPT_DIFFIMG_TEMPLATE.INPUT > MAKE_DIFFIMG_DIRS_${EXPNUM}.INPUT

sed -e s/THENITE/$NITE/ -e s/THEBAND/${BAND}/ -e s/THEEXP/${EXPNUM}/ -e s/THEFIELD/${FIELD}/ -e s/THETILE/${TILING}/ -e s/CCD2DIGIT/\$CCD/ -e "s/ALLEXP/${ALLEXPS}/" INTERNAL_INFO_TEMPLATE.DAT > INTERNAL_INFO_${EXPNUM}_tile${TILING}.DAT

# create dir for this exposure, and put relevant files there

mkdir -p mytemp_${EXPNUM}/${procnum}
mkdir -p mytemp_${EXPNUM}/${procnum}/input_files/
chmod -R g+w mytemp_${EXPNUM}

cd mytemp_${EXPNUM}

if [ -e JOBDIR ]; then rm JOBDIR ; fi
if [ -e mytemp_${EXPNUM} ]; then 
    rm mytemp_${EXPNUM}
    ln -s . mytemp_${EXPNUM}
fi
ln -s . JOBDIR

mv ../INTERNAL_INFO_${EXPNUM}_tile${TILING}.DAT ./INTERNAL_INFO_${EXPNUM}_tile${TILING}.KH

lisfile=WSinput_${NITE}_${FIELD}.lis
if [ -f $lisfile ]; then 
rm $lisfile
fi
touch $lisfile

for myexp in $ALLEXPS
do
#echo "ROOT: /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}" > $lisfile
#echo "FILE: $FIELD $BAND $TILING $EXPNUM D00${EXPNUM}_${BAND}_\$CCD_${rpnum}_immask.fits " >> $lisfile
echo "ROOT: /pnfs/des/scratch/gw/exp/${NITE}/${myexp}" >> $lisfile
echo "FILE: $FIELD $BAND $TILING $myexp D00${myexp}_${BAND}_\$CCD_${rpnum}_immask.fits " >> $lisfile
done

OPWD=$PWD

echo "now in $PWD"

mv ../MAKE_DIFFIMG_DIRS_${EXPNUM}.INPUT .

#writeDB on/off
if [ "$WRITEDB" == "on" ] ; then 
    RUN_DIFFIMG_PIPELINE.pl  MAKE_DIFFIMG_DIRS_${EXPNUM}.INPUT NOPROMPT -writeDB
else
    RUN_DIFFIMG_PIPELINE.pl  MAKE_DIFFIMG_DIRS_${EXPNUM}.INPUT NOPROMPT
fi


#### KRH temp hack on 2016-08-28 to fix autoscan path until there is a new version of diffimg in cvmfs
for ascanfile in `ls ${procnum}/${BAND}_[0-9][0-9]/RUN24_combined_autoScan`
do
#echo "in autoscan edit"
sed -i -e s#/data/des40.b/data/kherner/Diffimg-devel/diffimg-trunk#/cvmfs/des.opensciencegrid.org/eeups/fnaleups/Linux64/diffimg/gwdevel12# $ascanfile

done

#### ugly hack !!!!! add new scamp file into the input_files dir and rename it to match the expected filename:
#cp /data/des40.b/data/kherner/Diffimg-devel/diffimg-trunk/etc/GW_astrom_v1.scamp  ./${procnum}/input_files/GW_astrom_v1.scamp
#cp ${DIFFIMG_DIR}/etc/GW_astrom_v2.scamp ./${procnum}/input_files/GW_astrom_v1.scamp
#cp /data/des40.b/data/kherner/Diffimg-devel/diffimg-trunk/etc/GW_astrom_v3.scamp ./${procnum}/input_files/GW_astrom_v1.scamp
#####

# now we have to do some ugly hack of RUN01 in order to change 
# the ln -s ... command to be an ifdh cp command, since the 
# source file will likely not be mounted 

for ((iccd=1;iccd<=62;iccd++))
do
    if [ $iccd -ne 2 ] && [ $iccd -ne 31 ] && [ $iccd -ne 61 ]; then
#	newlink=$(awk '$1=="ln" {print $4}' ./${procnum}/${BAND}_`printf %02d ${iccd}`/RUN01_expose_prepData)

#	sed -i -e '/ln -sf/ s/ln -sf/ifdh cp/' -e '/ifdh cp\s.*\s(.*)/a ln -sf '$newlink' JOBDIR' ./${procnum}/${BAND}_`printf %02d ${iccd}`/RUN01_expose_prepData
	sed -i -e '/ln -sf/ s/ln -sf/ifdh cp/' ./${procnum}/${BAND}_`printf %02d ${iccd}`/RUN01_expose_prepData
	newlink="$(egrep "^ifdh"  ./${procnum}/${BAND}_`printf %02d ${iccd}`/RUN01_expose_prepData | awk '{print $4}')"
	echo "newlink = $newlink"
	for mylink in $newlink
	do
	    nicelink=$(echo $mylink | sed -e 's/\//\\\//g')
	    sed -i -e '/ifdh cp\s.*\s'$nicelink'/a ln -sf '$mylink' JOBDIR' ./${procnum}/${BAND}_`printf %02d ${iccd}`/RUN01_expose_prepData
	done
    fi
done


cd ../

mv $templatecopyfile  mytemp_${EXPNUM}/${procnum}/input_files/

files2copy=$(ifdh ls mytemp_${EXPNUM}/${procnum}/ )
outlist=""
dirlist=""
for file in $files2copy
do
    case $file in
	*//)
	    :
	    ;;
	*/)
	    dirlist="$dirlist $file"
	    ;;
	*)
# do not copy zero-length files
	    if [ `stat -c %s $file` -gt 0 ]; then
		outlist="$outlist $file"
	    else
		echo "File $file has zero length; skipping copy"
	    fi
	    ;;
    esac
done

if [ "${USER}" == "desgw" ] ; then
    MKDIRCMD="mkdir"
    CHMODCMD="chmod g+w"
else
    MKDIRCMD="ifdh mkdir"
    CHMODCMD="ifdh chmod 775"
fi


if [ ! -d /pnfs/des/scratch/gw/exp/${NITE}/ ]; then
    echo "Creating output directory for search night"
    $MKDIRCMD /pnfs/des/scratch/gw/exp/${NITE}/
    $CHMODCMD /pnfs/des/scratch/gw/exp/${NITE}/
fi

if [ ! -d /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM} ]; then
    echo "Creating output directory for search image"
    $MKDIRCMD /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}
    $CHMODCMD /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}
fi
if [ ! -d /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum} ]; then
    $MKDIRCMD /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}
    $CHMODCMD /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}
fi
if [ ! -d /pnfs/des/scratch/gw/forcephoto/images/${procnum} ]; then
    $MKDIRCMD /pnfs/des/scratch/gw/forcephoto/images/${procnum}
    $CHMODCMD /pnfs/des/scratch/gw/forcephoto/images/${procnum} 
fi

for (( ichip=1;ichip<63;ichip++))
do
    if [ $ichip -ne 2 ] && [ $ichip -ne 31 ] && [ $ichip -ne 61 ]; then
	
	if [ ! -d /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/${BAND}_`printf %02d $ichip` ]; then
	    $MKDIRCMD /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/${BAND}_`printf %02d $ichip`
	    $CHMODCMD /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/${BAND}_`printf %02d $ichip`
	fi
	if [ ! -d /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/${BAND}_`printf %02d $ichip`/ingest ]; then
	    $MKDIRCMD /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/${BAND}_`printf %02d $ichip`/ingest
	    $CHMODCMD /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/${BAND}_`printf %02d $ichip`/ingest
	fi
	if [ ! -d /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/${BAND}_`printf %02d $ichip`/stamps_${NITE}_${FIELD}_${BAND}_`printf %02d $ichip` ]; then
	    $MKDIRCMD /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/${BAND}_`printf %02d $ichip`/stamps_${NITE}_${FIELD}_${BAND}_`printf %02d $ichip`
	    $CHMODCMD /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/${BAND}_`printf %02d $ichip`/stamps_${NITE}_${FIELD}_${BAND}_`printf %02d $ichip`
	fi
    fi
done

PREVDIR=$PWD
cd mytemp_${EXPNUM}
tar czf  ${EXPNUM}_run_inputs.tar.gz ${procnum}/${BAND}_[0-9][0-9]
cd $PREVDIR

rm -f  /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/${BAND}_`printf %02d $ichip`/${EXPNUM}_${BAND}_`printf %02d ${ichip}`_run_inputs.tar.gz  /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/${EXPNUM}_run_inputs.tar.gz

rm -rf /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/input_files

### modify VETOMAG in SN_cuts.filterObj ##### 
sed -i -e '/VETOMAG/ s/21/20/'  mytemp_${EXPNUM}/${procnum}/input_files/SN_cuts.filterObj
#sed -i -e '/MIN_MLSCORE/ s/0.3/0.25/'  mytemp_${EXPNUM}/${procnum}/input_files/SN_cuts.filterObj

echo "now doing coy of input_files directory"
echo "copydcmd = $COPYDCMD"
echo "ls first:"
ls /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/ 
$COPYDCMD -r mytemp_${EXPNUM}/${procnum}/input_files /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/  ||  echo "Error copying data dir!!!!"

rmlist=""
for file in $outlist
do
rmlist="$rmlist /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/`basename $file`"
done

echo rmlist= $rmlist

rm -rf $rmlist
$COPYDCMD $outlist mytemp_${EXPNUM}/${EXPNUM}_run_inputs.tar.gz /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/${procnum}/ ||  echo "Error copying input files to dCache!!!!"
#ifdh cp -r -D mytemp_${EXPNUM}/data /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/ ||  echo "Error copying data dir!!!!"

#ifdh rename 
if [ "${USER}" == "desgw" ]; then
    COPYCMD="cp"
else
    COPYCMD="ifdh cp"
fi
rm -f /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/WS_diff.list
$COPYCMD mytemp_${EXPNUM}/KH_diff.list1  /pnfs/des/scratch/gw/exp/${NITE}/${EXPNUM}/WS_diff.list

echo "To submit this DAG do"
echo "jobsub_submit_dag -G des --role=DESGW file://${outfile}"

touch mytemp_${EXPNUM}/DAGMaker.DONE
echo "jobsub_submit_dag -G des --role=DESGW file://${outfile}" >> mytemp_${EXPNUM}/DAGMaker.DONE
