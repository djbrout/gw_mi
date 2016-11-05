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
from copy import copy
import candidatepages as cp

from blitzdb import Document
from blitzdb import FileBackend

import yaml

class Trigger(Document):
    pass
#class SEimageProcessing(Document):
#    pass
class hexes(Document):
    pass
class exposures(Document):
    pass
class preprocessing(Document):
    pass


from datetime import datetime as dt
from datetime import timedelta as td

# propid = "'2012B-0001'" # des
propid = "'2015B-0187'"  # desgw

DATABASE = 'desoper'  # read only

PRDDATABASE = 'decam_prd'

hardjson = True
hj = ['M249148-6-UTC-2016-8-17-5_23_00-test.json']


# DATABASE = 'destest' #We can write here

class eventmanager:
    def __init__(self, trigger_id, jsonfilelist, triggerdir, datadir, real):

        os.system('kinit -k -t /var/keytab/desgw.keytab desgw/des/des41.fnal.gov@FNAL.GOV')


        if real:
            self.backend = FileBackend("./realdb")
        else:
            self.backend = FileBackend("./testdb")

        try:
            thisevent = self.backend.get(Trigger, {'id': trigger_id})
            print 'Found this event in desgw database...'
        except Trigger.DoesNotExist:
            thisevent = Trigger({
                'id':trigger_id,
                'jsonfilelist':jsonfilelist,
                'triggerpath':triggerdir,
                'mapspath':datadir,
                'jobids':[
                    (0,'jsonfile_corresponding_to_jobid.json'),
                ],
            })
            print 'Database entry created!'


        self.backend.save(thisevent)
        self.backend.commit()

        with open(os.path.join(triggerdir,"strategy.yaml"), "r") as f:
            self.config = yaml.safe_load(f);
        self.filterobslist = np.array(self.config['exposure_filter'],dtype='str')
        self.strategydict = {}

        for f in np.unique(self.filterobslist):
            self.strategydict[f] = len(self.filterobslist[self.filterobslist == f])

        self.connection = ea.connect(DATABASE)
        self.cursor = self.connection.cursor()

        self.jsonfilelist = jsonfilelist

        print self.jsonfilelist
        if hardjson:
            self.jsonfilelist = hj

        self.trigger_id = trigger_id
        self.datadir = datadir
        self.triggerdir = triggerdir
        self.processingdir = os.path.join(self.triggerdir,'PROCESSING')
        if not os.path.exists(self.processingdir):
            os.makedirs(self.processingdir)

        dire = './processing/' + trigger_id + '/'
        if not os.path.exists(dire):
            os.makedirs(dire)

        with open(os.path.join(triggerdir, "strategy.yaml"), "r") as f:
            self.strategy = yaml.safe_load(f)

        with open("jobmanager.yaml", "r") as g:
            self.jmconfig = yaml.safe_load(g);


        q1 = "select expnum,nite,mjd_obs,telra,teldec,band,exptime,propid,obstype,object from exposure where " \
             "nite>20130828 and nite<20150101 and expnum<300000 and obstype='object' order by expnum"  # y1 images
        self.connection.query_and_save(q1, './processing/exposuresY1.tab')

        q2 = "select expnum,nite,mjd_obs,radeg,decdeg,band,exptime,propid,obstype,object from prod.exposure where " \
             "nite>20150901 and obstype='object' order by expnum"  # y2 and later
        self.connection.query_and_save(q2, './processing/exposuresCurrent.tab')

        os.system('cat ./processing/exposuresY1.tab ./processing/exposuresCurrent.tab > ./processing/exposures.list')

        self.submit_all_jsons_for_sejobs()#preps all DES images that already exist
        self.monitor_images_from_mountain()#A loop that waits for images off mountain and submits for processing

    def submit_all_jsons_for_sejobs(self):
        obsStartTime = self.getDatetimeOfFirstJson(self.jsonfilelist[0])  # THIS IS A DATETIME OBJ
        currentTime = dt.utcnow()
        print '***** The current time is UTC', currentTime, '*****'
        delt = obsStartTime - currentTime

        timedelta = td(days=delt.days, seconds=delt.seconds).total_seconds() / 3600.
        print '***** The time delta is ', timedelta, 'hours *****'
        # if timedelta > np.pi:

        sejob_timecushion = self.jmconfig["sejob_timecushion"]

        if timedelta > sejob_timecushion:
            for jsonfile in self.jsonfilelist:
                print 'json',jsonfile
                try: #check if this json file is already in the submitted preprocessing database
                    thisjson = self.backend.get(preprocessing, {'jsonfilename': os.path.join(self.datadir, jsonfile)})
                    print 'Found this json in desgw database...'
                except preprocessing.DoesNotExist: #do submission and then add to database

                    print 'cd diffimg-proc; source SEMaker_RADEC.sh '+os.path.join(self.datadir, jsonfile)
                    os.chdir("diffimg-proc")
                    out = os.popen('source SEMaker_RADEC.sh '+os.path.join(self.datadir, jsonfile)).read()
                    os.chdir("..")

                    print out
                    if 'non-zero exit status' in out:
                        dt.sendEmailSubject(self.trigger_id,'Error in creating dag for .json: '+out)
                    else:
                        for o in out.split('\n'):
                            if 'file://' in o:
                                dagfile = o.split('/')[-1]
                                self.dagfile = os.path.join(self.processingdir,jsonfile.split('/')[-1].split('.')[0]+'_'+dagfile)
                                os.system('cp '+dagfile+' '+self.dagfile)
                                jobsubmitline = copy(o)
                        print self.dagfile

                    print 'source /cvmfs/fermilab.opensciencegrid.org/products/common/etc/setup; setup jobsub_client; jobsub_submit_dag -G des --role=DESGW file://'+self.dagfile

                    out = os.popen(
                        'source /cvmfs/fermilab.opensciencegrid.org/products/common/etc/setup; setup jobsub_client; '
                        'jobsub_submit_dag -G des --role=DESGW file://'+self.dagfile).read()
                    print out
                    if 'non-zero exit status' in out:
                        dt.sendEmailSubject(self.trigger_id, 'Error in submitting .json for preprocessing: ' + out)
                    else:
                        for o in out.split('\n'):
                            if 'Use job id' in o:
                                jobid = o.split()[3]
                        out = os.popen(
                            'source /cvmfs/fermilab.opensciencegrid.org/products/common/etc/setup; setup jobsub_client; '
                            'jobsub_rm --jobid=' + jobid + ' --group=des --role=DESGW').read()
                        print out

                    thisjson = preprocessing({
                        'jsonfilename': os.path.join(self.datadir, jsonfile),
                        'jobid': jobid,
                        'dagfile': self.dagfile,
                        'status' : 'Submitted'
                    })

                    self.backend.save(thisjson)
                    self.backend.commit()
                    print 'saved'
                #raw_input()
                #runProcessingIfNotAlready(image, self.backend)

                #sys.exit()

        print 'Finished submitting minidagmaker with all json files'
        #sys.exit()
        #raw_input()

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
            os.system('kinit -k -t /var/keytab/desgw.keytab desgw/des/des41.fnal.gov@FNAL.GOV')
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


            self.cursor.execute(query)

            for s in self.cursor:
                ofile.write(
                    str(s[0]) + "\t" + str(s[1]) + "\t" + str(s[2]) + "\t" + str(s[3]) + "\t" + str(s[4]) + "\t" + str(
                        s[5]) + "\t" + str(s[6]) + "\t" + str(s[7]) + '\n')
                print str(s[0]) + "\t" + str(s[1]) + "\t" + str(s[2]) + "\t" + str(s[3]) + "\t" + str(
                    s[4]) + "\t" + str(s[5]) + "\t" + str(s[6]) + "\t" + str(s[7])

                if not 'DESGW' in str(s[7]): continue
                #print 'exptime',float(s[3])
                if not float(s[3]) > 29.: continue #exposure must be longer than 30 seconds

                expnum = str(s[0])
                nite = str(s[1])
                band = str(s[2])
                exptime = str(s[3])


                #FIRST CHECK HERE THAT THE EXPOSURE NUMBER ISNT ALREADY IN THE DATABASE
                try:
                    exposure = self.backend.get(exposures, {'expnum': expnum})
                    print 'Found this exposure in desgw database...'
                    # print exposure.attributes
                    # if expnum == 506432:
                    #     sys.exit()
                    # self.backend.delete(exposure)
                    # self.backend.commit()
                    # exposure = self.backend.get(exposures, {'expnum': expnum})

                except exposures.DoesNotExist:  # add to database
                    #runProcessingIfNotAlready(image,self.backend)

                    print './diffimg-proc/getTiling.sh '+expnum

                    res = os.popen('./diffimg-proc/getTiling.sh '+expnum).readlines()
                    print res
                    #sys.exit()
                    field,tiling =res[-2],res[-1]
                    #print 'field_tiling',field_tiling
                    hexnite = field.strip()+'_'+tiling.strip()+'_'+str(nite)
                    #print hexnite
                    #sys.exit()
                    #print 'hexnite',hexnite
                    print 'Creating exposure in database...',hexnite
                    raw_input()
                    if '--' in hexnite:
                        print 'found bad example'
                        raw_input()

                    exposure = exposures({
                        'expnum':expnum,
                        'nite':nite,
                        'field':field,
                        'tiling':tiling,
                        'hexnite':hexnite,
                        'band':band,
                        'jobid':np.nan,
                        'exptime':exptime,
                        'status':'Awaiting additional exposures',
                        'triggerid': self.trigger_id,
                        'object':str(s[7])
                    })

                    self.backend.save(exposure)
                    self.backend.commit()

                hexnite = exposure.hexnite
                print 'hexnite',hexnite
                if '--' in hexnite:
                    print exposure.attributes
                    #raw_input()
                #raw_input()
                #sys.exit()
                try:
                    hex = self.backend.get(hexes, {'hexnite': hexnite})
                    #self.backend.delete(hex)
                    #self.backend.commit()
                    #hex = self.backend.get(hexes, {'hexnite': hexnite})

                    #print 'Found this hex in desgw database...'
                except hexes.DoesNotExist:
                    hex = hexes({
                        'hexnite': hexnite,
                        'strategy': self.strategy['exposure_filter'],
                        'num_target_g': len(exposure_filter[exposure_filter == 'g']),
                        'num_target_r': len(exposure_filter[exposure_filter == 'r']),
                        'num_target_i': len(exposure_filter[exposure_filter == 'i']),
                        'num_target_z': len(exposure_filter[exposure_filter == 'z']),
                        'observed_g': [],
                        'observed_r': [],
                        'observed_i': [],
                        'observed_z': [],
                        'exposures': [],
                        'status': 'Awaiting additional exposures',
                        'dagfile' : None,
                    })

                    self.backend.save(hex)
                    self.backend.commit()
                    print hex.attributes
                    print 'created new hex'
                    raw_input()

                if hex.status == 'Submitted for processing':
                    print 'This hex has already been submitted for processing'
                    continue

                # if '--' in hexnite:
                #     print hex.attributes
                #     raw_input()
                # if hex.status == 'Submitted for processing':
                #     print 'Hex ',hexnite,' band',band,'exposure',expnum,'has already been submitted for processing'
                #     #raw_input()
                #     continue

                if band == 'g':
                    if not expnum in hex.observed_g:
                        hex.observed_g.append(expnum)
                        hex.exposures.append(expnum)
                if band == 'r':
                    if not expnum in hex.observed_r:
                        hex.observed_r.append(expnum)
                        hex.exposures.append(expnum)
                if band == 'i':
                    if not expnum in hex.observed_i:
                        hex.observed_i.append(expnum)
                        hex.exposures.append(expnum)
                if band == 'z':
                    if not expnum in hex.observed_z:
                        hex.observed_z.append(expnum)
                        hex.exposures.append(expnum)

                self.backend.save(hex)
                self.backend.commit()

                print hex.attributes

                didwork = False
                if len(hex.observed_g) == hex.num_target_g:
                    if len(hex.observed_r) == hex.num_target_r:
                        if len(hex.observed_i) == hex.num_target_i:
                            if len(hex.observed_z) == hex.num_target_z:
                                print 'All exposures in strategy satisfied! '
                                raw_input()
                                submissionPassed = True

                                exposurestring = ''
                                logstring = ''
                                for exps in hex.exposures:
                                    exposurestring += exps+' '
                                    logstring += exps+'_'

                                print 'cd diffimg-proc; source DAGMaker.sh ' + exposurestring
                                os.chdir("diffimg-proc")
                                out = os.popen('source DAGMaker.sh ' + exposurestring ).read()
                                os.chdir("..")
                                print out
                                f = open(os.path.join(self.processingdir,logstring+hexnite+'.log'),'w')
                                f.write(out)
                                f.close()
                                if not 'To submit this DAG do' in out:
                                    dt.sendEmailSubject(self.trigger_id, 'Error in creating dag for desgw hex: ' + out)
                                    submissionPassed = False
                                else:
                                    for o in out.split('\n'):
                                        if 'file://' in o:
                                            dagfile = o.split('/')[-1]
                                            self.dagfile = os.path.join(self.processingdir,logstring+'job.dag')
                                            os.system('cp ' + dagfile + ' ' + self.dagfile)
                                    print self.dagfile

                                print 'source /cvmfs/fermilab.opensciencegrid.org/products/common/etc/setup; setup jobsub_client; jobsub_submit_dag -G des --role=DESGW file://' + self.dagfile

                                out = os.popen(
                                    'source /cvmfs/fermilab.opensciencegrid.org/products/common/etc/setup; setup jobsub_client; '
                                    'jobsub_submit_dag -G des --role=DESGW file://' + self.dagfile).read()
                                print out
                                if 'non-zero exit status' in out:
                                    dt.sendEmailSubject(self.trigger_id,
                                                        'Error in submitting hex dag for processing: ' + out)
                                    submissionPassed = False
                                else:
                                    for o in out.split('\n'):
                                        if 'Use job id' in o:
                                            jobid = o.split()[3]
                                    out = os.popen(
                                        'source /cvmfs/fermilab.opensciencegrid.org/products/common/etc/setup; setup jobsub_client; '
                                        'jobsub_rm --jobid=' + jobid + ' --group=des --role=DESGW').read()
                                    print out
                                #if '--' in hexnite:
                                #    print 'Stopped for debug'
                                #    sys.exit()
                                raw_input()
                                if submissionPassed:

                                    hex.status = 'Submitted for processing'
                                    hex.dagfile = self.dagfile
                                    self.backend.save(hex)
                                    self.backend.commit()

                                    for expn in hex.exposures:
                                        print expn, 'updated in database to Submitted For Processing'
                                        exp = self.backend.get(exposures, {'expnum': expn})
                                        exp.status = 'Submitted for processing'
                                        self.backend.save(exp)
                                        self.backend.commit()
                                    didwork = True
                                print 'didwork',didwork
                                print 'dagfile',self.dagfile
                                raw_input()
                                #sys.exit()
                                #SUBMIT THE IMAGE NOW

                if not didwork:
                    print 'Could not find all images in strategy for this hex... Added hex', hexnite,' to database ' \
                        'and will continue waiting...'
                    raw_input()

                #sys.exit()




                #field = field_tiling.split([-2])
                #tiling = field_tiling.split([-1])
                #print 'field tiling',field,tiling
                #raw_input()
                #sys.exit()

                #NOW ADD THAT FIELD TILING ENTRY TO THE FIELD TILING DATABASE IF IT DOESNT ALREADY EXIST

                #THEN ADD THE FILTER OBSERVED (AND EXP NUM) TO THE FIELD TILING DICTINOARY INSID ETHE FIELD TILING DATABASE

            print 'Done checking mountaintop database...'
            sys.exit()


            #HERE YOU NEED TO ADD TO HEXSTRATEGYDICT DATABASE

            if time.time() - pptime > postprocessingtime: #happens every 30 minutes or so...
                pptime = time.time()
                print '***** Firing post processing script *****'
                sys.exit()
                self.submit_post_processing()
            #sys.exit()
            print 'Waiting 2 minutes to check from mountain...'
            sys.exit()
            time.sleep(120)#looping over checking the mountain top

            # cfiles = os.listdir(os.path.join(trigger_path,trigger_id,'candidates'))
            # for f in cfiles:
            #     if f.split('.')[-1] == 'npz':
            #         cp.makeNewPage(f)

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
        args = ['ssh -t desgw@des41.fnal.gov "source '+ os.path.join(gwpostdir, 'mi_setup.sh')+'; '+
                        'yes | python '+os.path.join(gwpostdir,'postproc.py')\
                         +' --expnums ' + expnumlist\
                         + ' --outputdir ' + os.path.join(trigger_path,trigger_id,'candidates')\
                         + ' --triggerid '+trigger_id+' --season 46 --ups True"'
                ]
        print args

        #p = subprocess.Popen(args,stdout=PIPE, stderr=PIPE,shell=True)
        #print p.communicate()
        #p = subprocess.Popen(args,stdin=None, stdout=None, stderr=None, close_fds=True,shell=True)
        return



    def getDatetimeOfFirstJson(self,jsonstring):
        js = jsonstring.split('UTC')[1]#-2015-12-27-3:2:00.json
        #date_object = dt.strptime(js, '-%Y-%m-%d-%H_%M_%S.json')
        date_object = dt.strptime(js, '-%Y-%m-%d-%H_%M_%S-test.json')
        print '***** Datetime of first observation UTC',date_object,'*****'
        return date_object

    def sortHexes(self):
        pass




    # LIST OF EXPOSURES

    # CANDIDATE FILE

    # EXCLUSIONFILE WHICH IS LIST_OF_EXPOSRES-CANDIDATE_FILE


# def runProcessingIfNotAlready(image,backend):
#     try:
#         #print 'this image.expnum', image.expnum
#         #print image.expnum
#         images = backend.filter(SEimageProcessing, {'expnum': image.expnum})
#         if len(images) == 0:
#             submit_SEjob(image,backend)
#             print 'Expnum', image.expnum, 'was just submitted for processing'
#         else:
#             print 'Expnum', image.expnum, 'has already been submitted for processing'
#         raw_input()
#     except SEimageProcessing.DoesNotExist:
#         submit_SEjob(image,backend)
#         print 'Expnum', image.expnum, 'was just submitted for processing'


def submit_SEjob(image,backend):
    expnum = image.expnum

    # print 'subprocess.call(["sh", "jobsub_submit --role=DESGW --group=des --OS=SL6 --resource - ' \
    #       'provides = usage_model = DEDICATED, OPPORTUNISTIC, OFFSITE, FERMICLOUD - M --email - to = ' \
    #       'marcelle @ fnal.ogv - -memory = 3000MB --disk = 94 GB --cpu = 4 --expected-lifetime = long ' \
    #       'file://SE_job.sh -r 2 -p 05 -b z -n 20121025 -e '+str(expnum)+'"])'

    print 'jobsub_submit --role=DESGW --group=des --OS=SL6 --resource-provides=usage_model=' \
          'DEDICATED,OPPORTUNISTIC,OFFSITE,FERMICLOUD -M --email-to=marcelle@fnal.ogv' \
          ' --memory=3000MB --disk=94GB --cpu=4 --expected-lifetime=long file://SE_job.sh' \
          ' -r 2 -p 05 -b z -n 20121025 -e ' + str(expnum)
    # sys.exit()
    out = os.popen( 'source /cvmfs/fermilab.opensciencegrid.org/products/common/etc/setup; setup jobsub_client; '
                    'jobsub_submit --role=DESGW --group=des --OS=SL6 --resource-provides=usage_model=' \
                    'DEDICATED,OPPORTUNISTIC,OFFSITE,FERMICLOUD -M --email-to=djbrout@gmail.com' \
                    ' --memory=3000MB --disk=94GB --cpu=4 --expected-lifetime=long file://SE_job.sh' \
                    ' -r 2 -p 05 -b z -n 20121025 -e ' + str(expnum)).read()  # STILL NEED TO PARSE FOR JOBID
    print out
    print '-' * 20
    jobid = 'NA'
    for o in out.split('\n'):
        if 'Use job id' in o:
            jobid = o.split()[3]
    out = os.popen('jobsub_rm --jobid=' + jobid + ' --group=des --role=DESGW').read()
    print out
    image.jobid = jobid
    image.status = 'Processing'
    backend.save(image)
    backend.commit()
    #sys.exit()


# def submitProcessing_STANDALONE(expnum,triggerid,real,band='NA',nite='NA'):
#     image = SEimageProcessing({
#         'expnum': expnum,
#         'nite': nite,
#         'band': band,
#         'jobid': np.nan,
#         'triggerid': triggerid,
#         'status': 'Not Submitted'
#     })
#
#     if real:
#         backend = FileBackend("./realdb")
#     else:
#         backend = FileBackend("./testdb")
#
#     print 'self.runProcessingIfNotAlready(image)'
#     runProcessingIfNotAlready(image,backend)

# def removeExposureFromProcessingDB(expnum,real):
#     if real:
#         backend = FileBackend("./realdb")
#     else:
#         backend = FileBackend("./testdb")
#
#     image = backend.filter(SEimageProcessing, {'expnum': expnum})
#     backend.delete(image)
#     'Exposure',expnum,'removed from database'

def cleardb(real=False):
    password = 'djb123'
    user_input = raw_input('Please Enter Password: ')

    if user_input != password:
        sys.exit('Incorrect Password, terminating... \n')

    if real:
        backend = FileBackend("./realdb")
    else:
        backend = FileBackend("./testdb")

    images = backend.filter(preprocessing, {'status': 'Submitted'})
    images.delete()
    hexen = backend.filter(hexes,{'num_target_g':0})
    hexen.delete()
    exposuren = backend.filter(exposures,{'status':'Awaiting additional exposures'})
    exposuren.delete()
    backend.commit()




def removeHexFromProcessingDB(hexnite,real):
    if real:
        backend = FileBackend("./realdb")
    else:
        backend = FileBackend("./testdb")

    hex = backend.filter(hexes, {'hexnite': hexnite})
    backend.delete(hex)
    'Hexnite',hexnite,'removed from database'

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
