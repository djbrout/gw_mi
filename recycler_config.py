trigger_path  = '/data/des41.a/data/desgw/maininjector/test-triggers'
exposure_length = 180. #sec
hours_available = 3.  # how many hours are we going to observe on night 1

####Only used for testing####
test_mjd = 55458.4629
trigger_id = "M186994"
wrap_all_triggers = False
force_mjd = False
#############################

#############################
import os
os.environ['DESGW_DIR'] = "/data/des41.a/data/desgw/osgsetup/eeups/fnaleups/Linux64/gw/v2.1"
os.environ['GW_DIR'] = "/data/des41.a/data/desgw/osgsetup/eeups/fnaleups/Linux64/gw/v2.1"
os.environ['DESGW_DATA_DIR'] = os.path.join(os.environ['DESGW_DIR'],"data/")
#############################
