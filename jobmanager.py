import os
import subprocess
from subprocess import PIPE
import time
import easyaccess as ea
import json
import yaml
import jobmanager_config
import numpy as np
import dilltools
import sys, getopt, traceback
import candidatepages as cp


from datetime import datetime as dt
from datetime import timedelta as td

# propid = "'2012B-0001'" # des
propid = "'2015B-0187'"  # desgw

DATABASE = 'desoper'  # read only

PRDDATABASE = 'decam_prd'

# DATABASE = 'destest' #We can write here

class eventmanager:
    def __init__(self, trigger_id, jsonfilelist, triggerdir, datadir):
        self.connection = ea.connect(DATABASE)
        self.cursor = self.connection.cursor()
        #self.prdconnection = ea.connect(PRDDATABASE)
        #self.prdcursor = self.prdconnection.cursor()
        self.jsonfilelist = jsonfilelist
        self.trigger_id = trigger_id
        self.datadir = datadir
        self.triggerdir = triggerdir
        dire = './processing/' + trigger_id + '/'
        if not os.path.exists(dire):
            os.makedirs(dire)

        with open(os.path.join(triggerdir, "strategy.yaml"), "r") as f:
            self.strategy = yaml.safe_load(f)

        file_firedlist = open('./processing/firedlist.txt', 'w')
        file_firedlist.close()

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

        #self.submit_all_images_in_LIGOxDES_footprint()
        #self.monitor_images_from_mountain()
        self.submit_post_processing()

    # USE JSON TO FIND ALL EXISTING DES IMAGES THAT OVERLAP WITH LIGOXDES AND SUBMIT THEM IF THEY ARE NOT
    #  ALREADY IN FIREDLIST
    def submit_all_images_in_LIGOxDES_footprint(self):

        obsStartTime = self.getDatetimeOfFirstJson(self.jsonfilelist[0])#THIS IS A DATETIME OBJ
        currentTime = dt.utcnow()
        ras = []
        decs = []
        filts = []
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
                        filts.append(js[u'filter'])

            exposurenums = self.getNearbyImages(ras,decs,filts)
            iii = 0
            for exp in exposurenums:
                iii += 1
                print iii
                self.submit_SEjob(exp)

            #unique list of hexes and filters and find the closest exposures for each hex

            #sort hexes by ra and then make a list of all exposure ids in exposures.list within 3 degrees of each hex
            #submit that list self.submit_SEjob().
        else:
            print '***** The time delta is too small, we dont have time for SE jobs ******\n***** Waiting for first ' \
                  'images to come off the mountain *****'

    def getNearbyImages(self,ras,decs,filts):

        allexposures = dilltools.read('./processing/exposures.list',1, 2, delim=' ')

        EXPTIME =np.array(map(float, map(lambda x: x if not x in ['plate','EXPTIME'] else '-999',
                                         allexposures['EXPTIME'])))
        EXPNUM = np.array(map(float, map(lambda x: x if not x in ['plate', 'EXPNUM'] else '-999',
                                          allexposures['EXPNUM'])))
        TELRA =np.array(map(float, map(lambda x: x if not x in ['plate','RADEG'] else '-999',
                                         allexposures['TELRA'])))
        TELDEC =np.array(map(float, map(lambda x: x if not x in ['plate','DECDEG'] else '-999',
                                         allexposures['TELDEC'])))
        FILT = np.array(allexposures['BAND'],dtype='str')

        TELRA[TELRA>180] = TELRA[TELRA>180] - 360.

        ww = EXPTIME >= jobmanager_config.min_template_exptime
        exposedRAS = TELRA[ww]
        exposedDECS = TELDEC[ww]
        exposedNUMS = EXPNUM[ww]
        FILT = FILT[ww]

        # print min(exposedRAS),max(exposedRAS)
        # print min(ras),max(ras)
        # print min(exposedDECS),max(exposedDECS)
        # print min(decs),max(decs)
        # print 'exposedRAS',exposedRAS,exposedRAS.shape

        submitexpnums = []

        for ra,dec,filt in zip(ras,decs,filts):
            dist = np.array(np.sqrt((ra-exposedRAS)**2 + (dec-exposedDECS)**2))
            #print min(dist),max(dist)
            nearby = (dist < jobmanager_config.SE_radius) & (FILT == filt)
            submitexpnums.extend(exposedNUMS[nearby])
        submitexpnums = np.array(submitexpnums)
        _, idx = np.unique(submitexpnums, return_index=True)
        uniquesubmitexpnums = submitexpnums[np.sort(idx)]

        return uniquesubmitexpnums

    def submit_SEjob(self,expnum):
        print 'subprocess.call(["sh", "jobsub_submit --role=DESGW --group = des --OS = SL6 --resource - ' \
              'provides = usage_model = DEDICATED, OPPORTUNISTIC, OFFSITE, FERMICLOUD - M --email - to = ' \
              'marcelle @ fnal.ogv - -memory = 3 GB --disk = 94 GB --cpu = 4 --expected-lifetime = long ' \
              'file://SE_job.sh -r 2 -p 05 -b z -n 20121025 -e '+str(expnum)+'"])'
        #THIS WILL BE REPLACED BY MINIDAGMAKER

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



    # Loop queries for images from mountain and submits them
    # Need to add complexity that monitors filter strategy and waits for entire groups of images to be co-added
    def monitor_images_from_mountain(self):
        #NEED TO ADD COADD LOGIC USING STRATEGY FROM CONFIG

        exposure_filter = np.array(self.strategy['exposure_filter'],dtype='str')
        uniquefilts = np.unique(self.strategy['exposure_filter'])

        filterstrategy = {}
        for f in uniquefilts:
            filterstrategy[f] = len(exposure_filter[exposure_filter == f])

        print 'filter strategy dictionary', filterstrategy

        starttime = time.time()
        pptime = time.time()
        keepgoing = True
        index = -1
        submission_counter = 0
        maxsub = 10000
        postprocessingtime = 1800 #every half hour fire off Tim's code for post-processing
        while keepgoing:
            index += 1
            newfireds = []
            if time.time() - starttime > 50000:
                keepgoing = False
                continue

            ofile = open(os.path.join(self.triggerdir , 'latestquery.txt'), 'w')

            ofile.write(
                "--------------------------------------------------------------------------------------------------\n")
            ofile.write("EXPNUM\tNITE\tBAND\tEXPTIME\tRADEG\t DECDEG\tPROPID\tOBJECT\n")
            ofile.write(
                "--------------------------------------------------------------------------------------------------\n")

            print "--------------------------------------------------------------------------------------------------"
            print "EXPNUM\tNITE\tBAND\tEXPTIME\tRADEG\t DECDEG\tPROPID\tOBJECT"
            print "--------------------------------------------------------------------------------------------------"

            query = "SELECT expnum,nite,band,exptime,radeg,decdeg,propid,object FROM prod.exposure@desoper WHERE " \
                    "expnum > 475900 and propid=" + propid + "and obstype='object' ORDER BY expnum"  # latest

            #
            # find out how much total time used with gw prop id and pass that to annis code
            # insure it comes along with one of these two tags
            #
            # 477001
            # 20150920
            # z
            # 90.0
            # 112.782517 - 70.0374
            # 2015
            # B - 01
            # 87
            # DES
            # wide
            # hex
            # 1130 - -700
            # 507412
            # 20151231
            # z
            # 90.0
            # 31.445925
            # 5.09265
            # 2015
            # B - 01
            # 87
            # DESGW: LIGO
            # event
            # G211117: 8
            # of
            # 30

            self.cursor.execute(query)

            for s in self.cursor:
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
                            #print 'subprocess.call(["sh", "DAGMaker.sh", expnum]) ' # create dag
                            #print 'created dag for ' + str(expnum)
                            #print 'subprocess.call(["sh", "jobsub_submit_dag -G des --role=DESGW ' \
                            #      'file://desgw_pipeline_00"' + expnum + '".dag"])'  # submit to the grid
                            #print 'subprocess.call(["./RUN_DIFFIMG_PIPELINE_LOCAL.sh","-E "' + nite + '" -b "' +\
                            #      band + '" -n "+nite]) #submit local'
                            #print 'SUBMITTED JOB FOR EXPOSURE: ' + expnum
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
            sys.exit()
            time.sleep(120)

            cfiles = os.listdir(os.path.join(trigger_path,trigger_id,'candidates'))
            for f in cfiles:
                if f.split('.')[-1] == 'npz':
                    cp.makeNewPage(f)

    def submit_post_processing(self):
        firedlist = open('./processing/firedlist.txt', 'r')
        fl = firedlist.readlines()
        firedlist.close()
        print fl
        fl = ['475914','475915','475916','482859','482860','482861']
        expnumlist = ''
        for f in fl:
            expnumlist += f.strip()+' '

        print 'FIRING TIMs CODE'

        gwpostdir = os.environ['GWPOST_DIR']
        print 'source ' + os.path.join(gwpostdir, 'diffimg_setup.sh') + '; \
                        python '+os.path.join(gwpostdir,'postproc.py')\
                         +' --expnums ' + expnumlist\
                         + ' --outputdir ' + os.path.join(trigger_path,trigger_id,'candidates')\
                         + ' --triggerid '+trigger_id+' --season 46 --ups True'
        # os.system('source ' + os.path.join(gwpostdir, 'diffimg_setup.sh') + '; \
        #                  python '+os.path.join(gwpostdir,'postproc.py')\
        #                  +' --expnums ' + expnumlist\
        #                  + ' --outputdir ' + os.path.join(trigger_path,trigger_id,'candidates')\
        #                  + ' --triggerid '+trigger_id+' --season 46 --ups True' )

        #pid = os.spawnlp(os.P_WAIT, "source", os.path.join(gwpostdir, 'diffimg_setup.sh'))
        args = ["source "+ os.path.join(gwpostdir, 'diffimg_setup.sh')]
        print args

        p = subprocess.Popen(args,stdout=PIPE, stderr=PIPE,shell=True)

        stdout, stderr = p.communicate()
        print stdout
        print stderr

        return



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


def sendEmail(trigger_id):
    import smtplib
    from email.mime.text import MIMEText

    text = 'Job Manager for Trigger ' + trigger_id + ' Has Ended!'
    msg = MIMEText(text)

    me = 'automated-desGW@fnal.gov'
    if jobmanager_config.sendEveryoneEmails:
        you = ['djbrout@gmail.com', 'marcelle@fnal.gov', 'annis@fnal.gov']
    else:
        you = ['djbrout@gmail.com']

    for y in you:
        msg['Subject'] = text
        msg['From'] = me
        msg['To'] = y

        s = smtplib.SMTP('localhost')
        s.sendmail(me, y, msg.as_string())
        s.quit()
    print 'Trigger email sent...'

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

        # Read in config
    with open("jobmanager.yaml", "r") as f:
        config = yaml.safe_load(f);
    # Set defaults to config
    trigger_path = config["trigger_path"]
    trigger_id = config["trigger_id"]


    for o, a in opt:
        print 'Option'
        print o
        print a
        print '-----'
        if o in ["-tp", "--triggerpath"]:
            trigger_path = str(a)
        elif o in ["-tid", "--triggerid"]:
            trigger_id = str(a)

    trigger_dir = os.path.join(trigger_path,trigger_id)
    thisevent = eventmanager(trigger_id=trigger_id,triggerdir=trigger_dir,datadir='',jsonfilelist='')

    sendEmail(trigger_id)