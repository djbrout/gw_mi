# Alex & Yuanyan's Anaconda                                                                                                                                                      \
                                                                                                                                                                                  
export CONDA_DIR=/cvmfs/des.opensciencegrid.org/fnal/anaconda2/
export PATH=/cvmfs/des.opensciencegrid.org/fnal/anaconda2/bin:$PATH
alias alexpy="source activate default"
alexpy
source /cvmfs/des.opensciencegrid.org/eeups/startupcachejob21i.sh
setup python
setup numpy
setup scipy
setup matplotlib
setup astropy
setup fitsio

setup healpy #MUST BE LAST                                                                                                                                                        


# tHis is for kcorrect c scripts                                                                                                                                                  
KCORRECT_DIR=$HOME/kcorrect
PATH=$KCORRECT_DIR/bin:$PATH
LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$KCORRECT_DIR/lib
export KCORRECT_DIR
export LD_LIBRARY_PATH



echo ''
echo ''
echo "Setting up DESGW environment..."

cd /data/des41.a/data/desgw/gw_mi

source /cvmfs/des.opensciencegrid.org/eeups/startup.sh

export EUPS_PATH=${EUPS_PATH}:/data/des41.a/data/desgw/osgsetup/eeups/fnaleups

export DES_SERVICES=/data/des41.a/data/desgw/maininjector_devel_dillon/diffim_db_files/desservices.ini
export PYTHON_PATH=${PYTHON_PATH}:/data/des41.a/data/desgw/

export DESGW_DIR=/data/des41.a/data/desgw/osgsetup/eeups/fnaleups/Linux64/gw/v2.3
export DESGW_DATA_DIR=/data/des41.a/data/desgw/osgsetup/eeups/fnaleups/Linux64/gw/v2.3/data/

setup --nolocks pyslalib
setup --nolocks pygcn
setup --nolocks requests
setup --nolocks matplotlib
setup --nolocks healpy
setup --nolocks scipy 0.14.0+5
setup --nolocks gw
setup --nolocks gwpost
setup --nolocks wget
setup --nolocks easyaccess
setup --nolocks yaml

source /cvmfs/fermilab.opensciencegrid.org/products/common/etc/setup
setup jobsub_client

echo $GW_DIR