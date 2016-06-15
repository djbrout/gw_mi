import os
import subprocess
import time
import easyaccess as ea
import json
import yaml
import jobmanager_config
import numpy as np
import dilltools

from datetime import datetime as dt
from datetime import timedelta as td

# propid = "'2012B-0001'" # des
propid = "'2015B-0187'"  # desgw

DATABASE = 'desoper'  # read only


# DATABASE = 'destest' #We can write here

class eventmanager:
    def __init__(self, trigger_id, jsonfilelist,triggerdir, datadir):
        self.connection = ea.connect(DATABASE)
        self.cursor = self.connection.cursor()
        self.jsonfilelist = jsonfilelist
        self.trigger_id = trigger_id
        self.datadir = datadir
        dire = './processing/' + trigger_id + '/'
        if not os.path.exists(dire):
            os.makedirs(dire)

        with open(os.path.join(triggerdir, "strategy.yaml"), "r") as f:
            self.strategy = yaml.safe_load(f)

        file_firedlist = open('./processing/firedlist.txt', 'r')
        firedlist = file_firedlist.readlines()
        file_firedlist.close()
        self.firedlist = map(str.strip, firedlist)

        q1 = "select expnum,nite,mjd_obs,telra,teldec,band,exptime,propid,obstype,object from exposure where " \
             "nite>20130828 and nite<20150101 and expnum<300000 and obstype='object' order by expnum"  # y1 images
        self.connection.query_and_save(q1, './processing/exposuresY1.tab')

        q2 = "select expnum,nite,mjd_obs,radeg,decdeg,band,exptime,propid,obstype,object from prod.exposure where " \
             "nite>20150901 and obstype='object' order by expnum"  # y2 and later
        self.connection.query_and_save(q2, './processing/exposuresCurrent.tab')

        os.system('cat ./processing/exposuresY1.tab ./processing/exposuresCurrent.tab > ./processing/exposures.list')

        self.submit_all_images_in_LIGOxDES_footprint()
        #self.monitor_images_from_mountain()

    # USE JSON TO FIND ALL EXISTING DES IMAGES THAT OVERLAP WITH LIGOXDES AND SUBMIT THEM IF THEY ARE NOT
    #  ALREADY IN FIREDLIST
    def submit_all_images_in_LIGOxDES_footprint(self):

        obsStartTime = self.getDatetimeOfFirstJson(self.jsonfilelist[0])#THIS IS A DATETIME OBJ
        currentTime = dt.utcnow()
        ras = []
        decs = []
        print '***** The current time is UTC',currentTime,'*****'
        delt = obsStartTime-currentTime

        timedelta = td(days=delt.days,seconds=delt.seconds).total_seconds()/3600.
        print '***** The time delta is ',timedelta,'hours *****'
        #if timedelta > np.pi:
        if timedelta > -9999999:
            print '***** Firing off all SE jobs near our planned hexes... *****'
            for jsonfile in self.jsonfilelist:
                with open(os.path.join(self.datadir, jsonfile)) as data_file:
                    jsondata = json.load(data_file)
                    for js in jsondata:
                        ras.append(js[u'RA'])
                        decs.append(js[u'dec'])

            exposurenums = self.getNearbyImages(ras,decs)
            for exp in exposurenums:
                self.submit_SEjob(exp)

            #unique list of hexes and filters and find the closest exposures for each hex

            #sort hexes by ra and then make a list of all exposure ids in exposures.list within 3 degrees of each hex
            #submit that list self.submit_SEjob().
        else:
            print '***** The time delta is too small, we dont have time for SE jobs ******\n***** Waiting for first ' \
                  'images to come off the mountain *****'

    def getNearbyImages(self,ras,decs):

        allexposures = dilltools.read('./processing/exposures.list',1, 2, delim=' ')

        EXPTIME =np.array(map(float, map(lambda x: x if not x in ['plate','EXPTIME'] else '-999',
                                         allexposures['EXPTIME'])))
        EXPNUM = np.array(map(float, map(lambda x: x if not x in ['plate', 'EXPNUM'] else '-999',
                                          allexposures['EXPNUM'])))
        TELRA =np.array(map(float, map(lambda x: x if not x in ['plate','RADEG'] else '-999',
                                         allexposures['TELRA'])))
        TELDEC =np.array(map(float, map(lambda x: x if not x in ['plate','DECDEG'] else '-999',
                                         allexposures['TELDEC'])))

        ww = EXPTIME >= jobmanager_config.min_template_exptime
        exposedRAS = TELRA[ww]
        exposedDECS = TELDEC[ww]
        exposedNUMS = EXPNUM[ww]

        print 'exposedRAS',exposedRAS,exposedRAS.shape

        submitexpnums = []

        for ra,dec in zip(ras,decs):
            dist = np.sqrt((ra-exposedRAS)**2 + (dec-exposedDECS)**2)
            nearby = dist < jobmanager_config.SE_radius
            submitexpnums.extend(exposedNUMS[nearby])



    def submit_SEjob(self,expnum):
        print 'subprocess.call(["sh", "jobsub_submit -G des --role=DESGW file://SE_job.sh -e '+str(expnum)+'"])'

    def submit_images_to_dagmaker(self,explist):
        submission_counter = 0
        maxsub = 1
        if len(explist) > 1:
            print '***** SUBMITTING IMAGES AS CO-ADDS *****'
            if not explist[0] in self.firedlist:
                try:
                    if submission_counter < maxsub:
                        # subprocess.call(["sh", "DAGMaker.sh", '00'+expnum]) #create dag
                        subprocess.call(["sh", "DAGMaker.sh", [str(exp)+' ' for exp in explist]])  # create dag
                        print 'created dag for ' + str(explist)
                        print 'subprocess.call(["sh", "jobsub_submit_dag -G des --role=DESGW file://desgw_pipeline_00"' \
                              + expnum + '".dag"])'  # submit to the grid
                        #print 'submitting to grid'
                        #print 'subprocess.call(["./RUN_DIFFIMG_PIPELINE_LOCAL.sh","-E "' + nite + '" -b "' + band + '"
                        # -n "+nite]) #submit local'
                        print 'SUBMITTED JOB FOR EXPOSURES: ',explist
                        newfireds.extend(explist)
                        submission_counter += 1
                except:
                    print 'SUBMISSION FAILED EXPNUMS', explist

        else:
            print '***** SUBMITTING IMAGE AS SE JOB (using dagmaker) *****'
            expnum = explist[0]
            if not expnum in self.firedlist:
                try:
                    if submission_counter < maxsub:
                        # subprocess.call(["sh", "DAGMaker.sh", '00'+expnum]) #create dag
                        subprocess.call(["sh", "DAGMaker.sh", expnum])  # create dag
                        print 'created dag for ' + str(expnum)
                        print 'subprocess.call(["sh", "jobsub_submit_dag -G des --role=DESGW file://desgw_pipeline_00"'\
                              + expnum + '".dag"])'  # submit to the grid
                        #print 'submitting to grid'
                        #print 'subprocess.call(["./RUN_DIFFIMG_PIPELINE_LOCAL.sh","-E "' + nite + '" -b "' + band +
                        # '" -n "+nite]) #submit local'
                        print 'SUBMITTED JOB FOR EXPOSURE: ' + expnum
                        newfireds.append(expnum)
                        submission_counter += 1
                except:
                    print 'SUBMISSION FAILED EXPNUM',expnum



    # Loop queries for images frommountain and submits them
    # Need to add complexity that monitors filter strategy and waits for entire groups of images to be co-added
    def monitor_images_from_mountain(self):

        starttime = time.time()
        pptime = time.time()
        keepgoing = True
        index = -1
        submission_counter = 0
        maxsub = 1
        postprocessingtime = 1800 #every half hour fire off Tim's code for post-processing
        while keepgoing:
            index += 1
            newfireds = []
            if time.time() - starttime > 50000:
                keepgoing = False
                continue

            ofile = open(dire + 'latestquery.txt', 'w')

            ofile.write(
                "--------------------------------------------------------------------------------------------------\n")
            ofile.write("EXPNUM\tNITE\tBAND\tEXPTIME\tTELRA\t TELDEC\tPROPID\tOBJECT\n")
            ofile.write(
                "--------------------------------------------------------------------------------------------------\n")

            print "--------------------------------------------------------------------------------------------------"
            print "EXPNUM\tNITE\tBAND\tEXPTIME\tTELRA\t TELDEC\tPROPID\tOBJECT"
            print "--------------------------------------------------------------------------------------------------"

            query = "SELECT expnum,nite,band,exptime,telra,teldec,propid,object FROM prod.exposure@desoper WHERE " \
                    "expnum > 475900 and propid=" + propid + "and obstype='object'"  # latest

            self.cursor.execute(query)

            for s in cursor:
                ofile.write(
                    str(s[0]) + "\t" + str(s[1]) + "\t" + str(s[2]) + "\t" + str(s[3]) + "\t" + str(s[4]) + "\t" + str(
                        s[5]) + "\t" + str(s[6]) + "\t" + str(s[7]) + '\n')
                print str(s[0]) + "\t" + str(s[1]) + "\t" + str(s[2]) + "\t" + str(s[3]) + "\t" + str(
                    s[4]) + "\t" + str(s[5]) + "\t" + str(s[6]) + "\t" + str(s[7])

                expnum = str(s[0])
                nite = str(s[1])
                band = str(s[2])
                if not expnum in self.firedlist:
                    try:
                        if submission_counter < maxsub:
                            # subprocess.call(["sh", "DAGMaker.sh", '00'+expnum]) #create dag
                            subprocess.call(["sh", "DAGMaker.sh", expnum])  # create dag
                            print 'created dag for ' + str(expnum)
                            print 'subprocess.call(["sh", "jobsub_submit_dag -G des --role=DESGW ' \
                                  'file://desgw_pipeline_00"' + expnum + '".dag"])'  # submit to the grid
                            #print 'submitting to grid'
                            #print 'subprocess.call(["./RUN_DIFFIMG_PIPELINE_LOCAL.sh","-E "' + nite + '" -b "' +\
                            #      band + '" -n "+nite]) #submit local'
                            print 'SUBMITTED JOB FOR EXPOSURE: ' + expnum
                            newfireds.append(expnum)
                            submission_counter += 1
                    except:
                        print 'SUBMISSION FAILED'

            # write newfireds to file
            ofile.close()
            file_firedlist = open('./processing/firedlist.txt', 'a')
            for f in newfireds:
                print 'New Fired: ' + str(f)
                file_firedlist.write(str(f) + '\n')
            file_firedlist.close()
            #sys.exit()

            if time.time() - pptime > postprocessingtime:
                pptime = time.time()
                print '***** Firing post processing script *****'
                self.submit_post_processing()

            time.sleep(120)

    def submit_post_processing(self):
        # FIRE TIM'S CODE
        pass

    def getDatetimeOfFirstJson(self,jsonstring):
        js = jsonstring.split('UTC')[1]#-2015-12-27-3:2:00.json
        date_object = dt.strptime(js, '-%Y-%m-%d-%H:%M:%S.json')
        print '***** Datetime of first observation UTC',date_object,'*****'
        return date_object

    def sortHexes(self):
        pass


    # LIST OF EXPOSURES

    # CANDIDATE FILE

    # EXCLUSIONFILE WHICH IS LIST_OF_EXPOSRES-CANDIDATE_FILE


if __name__ == "__main__":

    try:
        args = sys.argv[1:]
        opt, arg = getopt.getopt(
            args, "tp:tid:mjd:exp:sky",
            longopts=["triggerpath=", "triggerid=", "mjd=", "exposure_length=", "skymapfilename="])

    except getopt.GetoptError as err:
        print str(err)
        print "Error : incorrect option or missing argument."
        print __doc__
        sys.exit(1)
