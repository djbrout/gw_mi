diffimg-proc 

------------- EXAMPLE 1: Processing exposure number 475914

git clone git@bitbucket.org:marcelle/diffimg-proc.git 
cd diffimg-proc
source setup.sh 
./DAGMaker.sh 475914
jobsub_submit_dag -G des file://desgw_pipeline_475914.dag

------------- EXAMPLE 2: Processing only the single epoch job for exposure number 482836

git clone git@bitbucket.org:marcelle/diffimg-proc.git 
cd diffimg-proc
source setup.sh 
./DAGMaker.sh 482836
jobsub_submit --group=des --OS=SL6 --resource-provides=usage_model=DEDICATED,OPPORTUNISTIC,OFFSITE,SLOTTEST,FERMICLOUD -M --email-to=someone@somewhere.com --memory=3GB --disk=94GB --expected-lifetime=long file://SE_job.sh -r 2 -p 1 -E 482836 -b z -n 20151007

------------- EXAMPLE 3: Test diffimg processing locally for exposure number 482836, ccd number 11

git clone git@bitbucket.org:marcelle/diffimg-proc.git
cd diffimg-proc
source setup.sh
./DAGMaker.sh 482836
if [ `grep SE_job.sh desgw_pipeline_482836.dag | wc -l` -eq 0 ] ; then ./RUN_DIFFIMG_PIPELINE.sh -r r2p1 -p dp41 -E 482836 -c 11 -b z -n 20151007 -v gwdevel8 ; else echo "SE_jobs not completed!" ; fi

-------------- Notes:

Pre-requisites:

* A valid kerberos ticket, and FermiGrid credentials -- to submit jobs 
* ~/.desservices.ini -- login information for desdm db
* ~/.pgpass -- login information for sispi db
* ~/.wgetrc-desdm -- to retrieve images from desdm

Configuration:

* dagmaker.rc -- edit this file before you run the DAGMAker
* ~/.desservices.ini -- edit this file to pick a different db schema: e.g. "GWDIFF"
* Add option "--role=DESGW" to jobsub_submit_dag line, to submit jobs as user desgw

Outputs of DAGMaker.sh:

* desgw_pipeline_EXPNUM.dag -- the dag to submit all jobs of this bunch
* mytemp_EXPNUM -- contains the directory structure and aux files
* dummyjob.sh -- used in portions of the dag that would otherwise be empty

Job submission:

* Submit all jobs for exposure number EXPNUM as yourself (see EXAMPLE 1):
jobsub_submit_dag -G des file://desgw_pipeline_EXPNUM.dag

* Submit all jobs for exposure number EXPNUM user desgw:
jobsub_submit_dag -G des --role=DESGW file://desgw_pipeline_EXPNUM.dag

* Submit one individual job:
Pick the job you want to submit from the dag and run that line by hand, 
replacing "jobsub -n" for "jobsub_submit" (see EXAMPLE 2).

* Running test jobs locally:
Pick the job you want to test from the dag and run it by hand, replacing everything
before "file://" with "./" (see EXAMPLE 3). Note that some jobs might require 
previous jobs to be completed first. Check the dag to see if there are jobs to do 
in the sections above the job you are trying to run (not counting dummyjobs).