echo ''
echo ''
echo "Setting up DESGW environment..."

cd /data/des41.a/data/desgw/gw_mi

source /cvmfs/des.opensciencegrid.org/eeups/startup.sh

export EUPS_PATH=${EUPS_PATH}:/data/des41.a/data/desgw/osgsetup/eeups/fnaleups
export DES_SERVICES=/data/des41.a/data/desgw/maininjector_devel_dillon/diffim_db_files/desservices.ini
export PYTHON_PATH=${PYTHON_PATH}:/data/des41.a/data/desgw/

setup --nolocks pyslalib
setup --nolocks pygcn
setup --nolocks requests
setup --nolocks matplotlib
setup --nolocks healpy
setup --nolocks scipy 0.14.0+5
setup --nolocks gw
setup --nolocks wget
setup --nolocks easyaccess
setup --nolocks yaml
setup --nolocks ligo-gracedb

echo $GW_DIR