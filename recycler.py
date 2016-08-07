import os
import sys, getopt, traceback
import numpy as np
#import triggerpages2 as tp
import triggerpagesfinal as tp
import getHexObservations
import subprocess
import datetime
import yaml
import jobmanager
from threading import Thread
sys.path.append("/data/des41.a/data/desgw/")


class event:
    def __init__(self, skymap_filename, outfolder, trigger_id, mjd, config):

        self.skymap = skymap_filename
        self.outfolder = outfolder
        self.trigger_id = trigger_id
        self.mjd = mjd
        self.config = config

        season_start_date = datetime.datetime.strptime(config["start_of_season_date"], "%m/%d/%Y")
        now = datetime.datetime.now()
        self.now = now
        if config["force_recycler_mjd"]:
            self.recycler_mjd = config["recycler_mjd"]
        else:
            self.recycler_mjd = config["start_of_season"] + (now - season_start_date).days

        # Setup website directories
        self.mapspath = os.path.join(outfolder, "maps/")
        if not os.path.exists(self.mapspath):
            os.makedirs(self.mapspath)
        self.website_jsonpath = "./DES_GW_Website/Triggers/" + trigger_id + "/"
        self.website_imagespath = "./DES_GW_Website/Triggers/" + trigger_id + "/images/"
        if not os.path.exists(self.website_imagespath):
            os.makedirs(self.website_imagespath)

        self.event_paramfile = os.path.join(outfolder, trigger_id + '_params.npz')
        self.weHaveParamFile = True
        try:
            self.event_params = np.load(self.event_paramfile)
        except:
            self.event_params = {}
            self.weHaveParamFile = False
        os.system('cp recycler.yaml ' + os.path.join(outfolder, 'strategy.yaml'))
        print '***** Copied recycler.yaml to ' + os.path.join(outfolder,
                                                              'strategy.yaml') + ' for future reference *****'
        '''
        krbdir = '/usr/krb5/bin'
        ticket_cache = '/var/keytab/desgw.keytab'
        pid = os.getpid()
        krb_cache = '/tmp/krb5cc_desgw_%s' % pid
        os.environ['KRB5CCNAME']='FILE:%s' % krb_cache
        principal = 'desgw/des/des41.fnal.gov@FNAL.GOV'
        kinit_cmd = '%s/kinit -A -c %s -k -t %s %s' % (krbdir,krb_cache,ticket_cache,principal)
        os.system(kinit_cmd)
        '''
        os.system('kinit -k -t /var/keytab/desgw.keytab desgw/des/des41.fnal.gov@FNAL.GOV')

    def mapMaker(self, trigger_id, skymap, exposure_length, config):
        import os
        import yaml
        import getHexObservations

        filter_list = config["exposure_filter"]
        overhead = config["overhead"]
        maxHexesPerSlot = config["maxHexesPerSlot"]
        hoursAvailable = config["time_budget"]
        maxHexesPerSlot = config["maxHexesPerSlot"]
        nvisits = config["nvisits"]
        area_per_hex = config["area_per_hex"]
        start_of_season = config["start_of_season"]
        end_of_season = config["end_of_season"]
        events_observed = config["events_observed"]
        skipAll = config["skipAll"]
        exposure_length = np.array(exposure_length)
        mjd = self.mjd
        outputDir = self.outfolder
        mapDir = self.mapspath
        recycler_mjd = self.recycler_mjd

        # If distance is not set in config use xml distance
        if config["force_distance"]:
            distance = config["distance"]
        else:
            if self.weHaveParamFile:
                distance = self.event_params["MaxDistance"]
            else:
                print 'THERE IS NO PARAMFILE, HARDCODING THE DISTANCE TO THE CONFIG DIST.'
                distance = config["distance"]

        self.distance = distance

        if not os.path.exists(outputDir):
            os.makedirs(outputDir)

        # make the maps
        try:
            where = 'getHexObservations'
            line = '103'
            try:
                probs, times, slotDuration, hoursPerNight = getHexObservations.prepare(
                    skymap, mjd, trigger_id, outputDir, mapDir, distance=distance,
                    exposure_list=exposure_length, filter_list=filter_list,
                    overhead=overhead, maxHexesPerSlot=maxHexesPerSlot, skipAll=skipAll)
            except ValueError:
                skymap = os.path.join(outputDir,config['default_map_name'])
                probs, times, slotDuration, hoursPerNight = getHexObservations.prepare(
                    skymap, mjd, trigger_id, outputDir, mapDir, distance=distance,
                    exposure_list=exposure_length, filter_list=filter_list,
                    overhead=overhead, maxHexesPerSlot=maxHexesPerSlot, skipAll=skipAll)
            # figure out how to divide the night
            # where = 'getHexObservations.contemplateTheDivisionsOfTime()'
            # line = '102'
            n_slots, first_slot = getHexObservations.contemplateTheDivisionsOfTime(
                probs, times, hoursPerNight=hoursPerNight,
                hoursAvailable=hoursAvailable)

            # compute the best observations
            # where = 'getHexObservations.now()'
            # line = '109'
            best_slot = getHexObservations.now(
                n_slots, mapDirectory=mapDir, simNumber=trigger_id,
                maxHexesPerSlot=maxHexesPerSlot, mapZero=first_slot,
                exposure_list=exposure_length, filter_list=filter_list,
                skipJson=True)
        except:
            e = sys.exc_info()
            trace = traceback.format_exc(sys.exc_info())
            print trace
            self.send_processing_error(e, where, line, trace)
            sys.exit()

        if n_slots > 0:
            print "================ N_SLOTS > 0 =================== "
            #   area_left is th enumber of hexes we have left to observe this season
            #   T_left is the number of days left in the season
            #   rate is the effective rate of triggers
            #
            # in seconds
            time_cost_per_hex = nvisits * np.sum(overhead + exposure_length)
            area_left = area_per_hex * \
                        (hoursAvailable * 3600) / (time_cost_per_hex)
            time_left = end_of_season - start_of_season
            rate = len(events_observed) / (recycler_mjd - start_of_season)

            # do Hsun-yu Chen's 
            try:
                where = 'getHexObservations.economics()'
                line = '136'
                econ_prob, econ_area, need_area, quality = \
                    getHexObservations.economics(trigger_id,
                                                 best_slot, mapDirectory=mapDir,
                                                 area_left=area_left, days_left=time_left,
                                                 rate=rate)

                hoursOnTarget = (econ_area / area_per_hex) * (time_cost_per_hex / 3600.)

                # figure out how to divide the night, 
                # given the new advice on how much time to spend
                where = 'getHexObservations.contemplateTheDivisionsOfTime()'
                line = '148'
                n_slots, first_slot = \
                    getHexObservations.contemplateTheDivisionsOfTime(
                        probs, times, hoursPerNight=hoursPerNight,
                        hoursAvailable=hoursOnTarget)

                where = 'getHexObservations.now()'
                line = '156'
                best_slot = getHexObservations.now(
                    n_slots, mapDirectory=mapDir, simNumber=trigger_id,
                    maxHexesPerSlot=maxHexesPerSlot, mapZero=first_slot,
                    exposure_list=exposure_length, filter_list=filter_list,
                    skipJson=False)
            except:
                e = sys.exc_info()
                trace = traceback.format_exc(sys.exc_info())
                print trace
                self.send_processing_error(e, where, line, trace)
                sys.exit()
        else:
            econ_prob = 0
            econ_area = 0
            best_slot = 0
            need_area = 11734.0
            quality = 1.0

        # make observation plots
        try:
            where = 'getHexObservations.makeObservingPlots()'
            line = '176'
            print '888' * 20
            print n_slots, trigger_id, best_slot, outputDir, mapDir
            print '888' * 20
            n_plots = getHexObservations.makeObservingPlots(
                n_slots, trigger_id, best_slot, outputDir, mapDir)

        except:
            e = sys.exc_info()
            trace = traceback.format_exc(sys.exc_info())
            print trace
            self.send_processing_error(e, where, line, trace)
            sys.exit()

        self.best_slot = best_slot
        self.n_slots = n_slots
        self.first_slot = first_slot
        self.econ_prob = econ_prob
        self.econ_area = econ_area
        self.need_area = need_area
        self.quality = quality

        np.savez(os.path.join(self.outfolder, 'mapmaker_results.npz')
                 , best_slot=best_slot
                 , n_slots=n_slots
                 , first_slot=first_slot
                 , econ_prob=econ_prob
                 , econ_area=econ_area
                 , need_area=need_area
                 , quality=quality
                 )

        ra, dec, self.prob, mjd, slotNum = \
            getHexObservations.readObservingRecord(self.trigger_id, mapDir)

        integrated_prob = np.sum(self.prob)
        if self.weHaveParamFile:
            np.savez(self.event_paramfile,
                     MJD=self.event_params['MJD'],
                     ETA=self.event_params['ETA'],
                     FAR=self.event_params['FAR'],
                     ChirpMass=self.event_params['ChirpMass'],
                     MaxDistance=self.event_params['MaxDistance'],
                     integrated_prob=integrated_prob,
                     M1=self.event_params['M1'],
                     M2=self.event_params['M2'],
                     nHexes=self.prob.size,
                     time_processed=self.now.strftime("%H:%M %B %d, %Y "),
                     boc=self.event_params['boc'],
                     CentralFreq=self.event_params['CentralFreq'],
                     best_slot=self.best_slot,
                     n_slots=self.n_slots,
                     first_slot=self.first_slot,
                     econ_prob=self.econ_prob,
                     econ_area=self.econ_area,
                     need_area=self.need_area,
                     quality=self.quality,
                     codeDistance=self.distance,
                     exposure_times=exposure_length,
                     exposure_filter=filter_list,
                     hours=config['time_budget'],
                     nvisits=config['nvisits'],
                     mapname='NAN'
                     )
        else:
            np.savez(self.event_paramfile,
                     MJD='NAN',
                     ETA='NAN',
                     FAR='NAN',
                     ChirpMass='NAN',
                     MaxDistance='NAN',
                     integrated_prob=integrated_prob,
                     M1='NAN',
                     M2='NAN',
                     nHexes=self.prob.size,
                     time_processed=self.now.strftime("%H:%M %B %d, %Y "),
                     boc=self.event_params['boc'],
                     CentralFreq='NAN',
                     best_slot=self.best_slot,
                     n_slots=self.n_slots,
                     first_slot=self.first_slot,
                     econ_prob=self.econ_prob,
                     econ_area=self.econ_area,
                     need_area=self.need_area,
                     quality=self.quality,
                     codeDistance=self.distance,
                     exposure_times=exposure_length,
                     exposure_filter=filter_list,
                     hours=config['time_budget'],
                     nvisits=config['nvisits'],
                     mapname='NAN'
                     )

    def getContours(self, exposure_length, config):
        import matplotlib.pyplot as plt

        if exposure_length is None:
            exposure_length = config["exposure_length"]
        image_dir = self.website_imagespath
        map_dir = self.mapspath

        if self.n_slots > 0:
            print 'Converting Observing Plots to .gif'
            os.system('convert $(for ((a=0; a<50; a++)); do printf -- "-delay 50 '+os.path.join(map_dir,self.trigger_id)+'-observingPlot-%s.png " $a; done;) '+os.path.join(map_dir, self.trigger_id) + '-observingPlot.gif')
            #os.system('convert -delay 70 -loop 0 '+os.path.join(map_dir,self.trigger_id)+'-observingPlot-*.png '+
            #          os.path.join(map_dir, self.trigger_id) + '-observingPlot.gif')
            os.system('cp '+os.path.join(map_dir, self.trigger_id) + '-observingPlot.gif '+ image_dir)
            iname = self.trigger_id + "-" + str(self.best_slot) + "-maglim-eq.png"
            oname = self.trigger_id + "_limitingMagMap.png"
            os.system('cp ' + os.path.join(self.outfolder, iname) + ' ' + os.path.join(image_dir, oname))
            iname = self.trigger_id + "-" + str(self.best_slot) + "-prob-eq.png"
            oname = self.trigger_id + "_sourceProbMap.png"
            os.system('cp ' + os.path.join(self.outfolder, iname) + ' ' + os.path.join(image_dir, oname))
            iname = self.trigger_id + "-" + str(self.best_slot) + "-ligo-eq.png"
            oname = self.trigger_id + "_LIGO.png"
            os.system('cp ' + os.path.join(self.outfolder, iname) + ' ' + os.path.join(image_dir, oname))
            iname = self.trigger_id + "-" + str(self.best_slot) + "-probXligo-eq.png"
            oname = self.trigger_id + "_sourceProbxLIGO.png"
            os.system('cp ' + os.path.join(self.outfolder, iname) + ' ' + os.path.join(image_dir, oname))
            # DESGW observation map
            inname = self.trigger_id + "-observingPlot-{}.png".format(
                self.best_slot)
            outname = self.trigger_id + "-observingPlot.png"
            os.system('cp ' + os.path.join(map_dir, inname) + ' ' + os.path.join(image_dir, outname))
            # probability plot
            name = self.trigger_id + "-probabilityPlot.png"
            os.system('cp ' + os.path.join(self.outfolder, name) + ' ' + image_dir)

        # oname = 'observingPlots.gif'
        # giffile = os.path.join(self.outfolder,iname)+' '+ os.path.join(image_dir,oname)
        # oname = self.trigger_id+'-observingPlot-*.png'
        # pngs = os.path.join(self.outfolder,iname)+' '+ os.path.join(image_dir,oname)
        # os.system('convert -delay 10 -loop 0 '+pngs+' '+giffile)

        else:
            # there is nothing to observe, make default plots
            try:
                where = 'getHexObservations.nothingToObserveShowSomething()'
                line = '240'
                ra, dec, ligo, maglim, probMap = \
                    getHexObservations.nothingToObserveShowSomething( \
                        self.skymap, self.mjd, exposure_length[0])
            except:
                e = sys.exc_info()
                trace = traceback.format_exc(sys.exc_info())
                print trace
                self.send_processing_error(e, where, line, trace)
                sys.exit()

            print "================ >>>>>>>>>>>>>>>>>>>>> =================== "
            print "================ >>>>>>>>>>>>>>>>>>>>> =================== "
            print "faking it with getHexObservations.nothingToObserveShowSomething("
            print self.skymap, self.mjd, exposure_length
            print "================ >>>>>>>>>>>>>>>>>>>>> =================== "
            print "================ >>>>>>>>>>>>>>>>>>>>> =================== "

            figure = plt.figure(1,figsize=(8.5*1.618,8.5))
            plt.figure(figsize=(8.5*1.618,8.5))
            # computing limiting mag
            # plot as ra,dec map 
            plt.clf()
            print 'ra', ra
            print 'dec', dec
            print 'maglim', maglim

            plt.hist(maglim, bins=np.arange(-11, -7, .2))
            plt.xlabel('maglim')
            plt.ylabel('counts')
            name = self.trigger_id + "_limitingMagHist.png"
            plt.savefig(os.path.join(self.outfolder, name))

            # plt.hexbin( ra, dec, maglim, vmin=15)
            plt.hexbin(ra, dec, maglim)
            plt.colorbar()
            plt.xlabel('RA')
            plt.ylabel('DEC')
            name = self.trigger_id + "_limitingMagMap.png"
            plt.savefig(os.path.join(self.outfolder, name))
            os.system('cp ' + os.path.join(self.outfolder, name) + ' ' + image_dir)

            # Calculate source probability map
            plt.clf()
            plt.hexbin(ra, dec, probMap, )
            plt.colorbar()
            plt.xlabel('RA')
            plt.ylabel('DEC')
            name = self.trigger_id + "_sourceProbMap.png"
            plt.savefig(os.path.join(self.outfolder, name))
            os.system('cp ' + os.path.join(self.outfolder, name) + ' ' + image_dir)

            # DES Source Prob Map x Ligo Sky Map
            plt.clf()
            plt.hexbin(ra, dec, probMap * ligo)
            plt.colorbar()
            plt.xlabel('RA')
            plt.ylabel('DEC')
            name = self.trigger_id + "_sourceProbxLIGO.png"
            plt.savefig(os.path.join(self.outfolder, name))
            os.system('cp ' + os.path.join(self.outfolder, name) + ' ' + image_dir)

            plt.clf()
            plt.hexbin(ra, dec, ligo)
            plt.colorbar()
            plt.xlabel('RA')
            plt.ylabel('DEC')
            name = self.trigger_id + "_LIGO.png"
            plt.savefig(os.path.join(self.outfolder, name))
            os.system('cp ' + os.path.join(self.outfolder, name) + ' ' + image_dir)

        return

    def makeJSON(self, config):

        mapmakerresults = np.load(os.path.join(self.outfolder, 'mapmaker_results.npz'))

        self.best_slot = mapmakerresults['best_slot']
        self.n_slots = mapmakerresults['n_slots']
        self.first_slot = mapmakerresults['first_slot']
        self.econ_prob = mapmakerresults['econ_prob']
        self.econ_area = mapmakerresults['econ_area']
        self.need_area = mapmakerresults['need_area']
        self.quality = mapmakerresults['quality']

        # DESGW json file (to be files once that is done)
        json_dir = self.website_jsonpath
        map_dir = self.mapspath
        jsonname = self.trigger_id + "_JSON.zip"
        jsonFile = os.path.join(map_dir, jsonname)
        jsonfilelistld = os.listdir(map_dir)
        jsonfilelist = []
        for f in jsonfilelistld:
            if '-tmp' in f:
                os.remove(os.path.join(map_dir, f))
            elif '.json' in f:
                jsonfilelist.append(f)

        if self.n_slots > 0:
            # get statistics
            ra, dec, self.prob, mjd, slotNum = \
                getHexObservations.readObservingRecord(self.trigger_id, map_dir)

            # adding integrated probability to paramfile
            integrated_prob = np.sum(self.prob)
            nHexes = str(self.prob.size)
        else:
            integrated_prob = 0
            nHexes = str(0)

        from time import gmtime, strftime
        timeprocessed = strftime("%H:%M:%S GMT \t %b %d, %Y", gmtime())

        exptimes = ', '.join(map(str, config['exposure_length']))
        expf = ', '.join(map(str, config['exposure_filter']))

        try:
            boc = self.event_params['boc']
        except:
            boc = 'NA'

        # Copy json file to web server for public download
        if not os.path.exists(jsonFile):
            if integrated_prob == 0:
                print "zero probability, thus no jsonFile at ", jsonFile
            else:
                # try:
                os.chmod(self.mapspath, 0o777)
                for js in os.listdir(self.mapspath):
                    os.chmod(os.path.join(self.mapspath,js), 0o777)

                os.system('zip -j ' + jsonFile + ' ' + self.mapspath + '/*0.json')
                # except:
                #    print "no jsonFiles at ", jsonFile
        else:
            os.remove(jsonFile)
            os.system('zip -j ' + jsonFile + ' ' + self.mapspath + '/*0.json')
            os.system('cp ' + jsonFile + ' ' + self.website_jsonpath)
        return jsonfilelist

    def send_nonurgent_Email(self):
        import smtplib
        from email.mime.text import MIMEText

        text = 'New event trigger. See \nhttp://des-ops.fnal.gov:8080/desgw/Triggers/' + self.trigger_id + '/' + self.trigger_id + '_trigger.html'

        # Create a text/plain message
        msg = MIMEText(text)

        # me == the sender's email address
        # you == the recipient's email address
        me = 'automated-desGW@fnal.gov'
        if self.config['sendEmailsToEveryone']:
            yous = ['djbrout@gmail.com', 'marcelle@fnal.gov', 'annis@fnal.gov']
        else:
            yous = ['djbrout@gmail.com']
        msg['Subject'] = 'Finished Processing GW Trigger ' + self.trigger_id
        msg['From'] = me
        for you in yous:
            msg['To'] = you

            s = smtplib.SMTP('localhost')
            s.sendmail(me, [you], msg.as_string())
            s.quit()
        print 'Email sent...'
        return

    def send_processing_error(self, error, where, line, trace):
        import smtplib
        from email.mime.text import MIMEText

        message = 'Processing Failed for Trigger ' + str(self.trigger_id) + '\n\nFunction: ' + str(
            where) + '\n\nLine ' + str(line) + ' of recycler.py\n\nError: ' + str(error) + '\n\n'
        message += '-' * 60
        message += '\n'
        message += trace
        message += '\n'
        message += '-' * 60
        message += '\n'

        # Create a text/plain message                                                                                                                                                                      
        msg = MIMEText(message)

        me = 'automated-desGW@fnal.gov'
        if self.config['sendEmailsToEveryone']:
            yous = ['djbrout@gmail.com', 'marcelle@fnal.gov', 'annis@fnal.gov']
        else:
            yous = ['djbrout@gmail.com']
        msg['Subject'] = 'Trigger ' + self.trigger_id + ' Processing FAILED!'
        msg['From'] = me
        for you in yous:
            msg['To'] = you
            s = smtplib.SMTP('localhost')
            s.sendmail(me, [you], msg.as_string())
            s.quit()
        print 'Email sent...'
        return

    def updateTriggerIndex(self, real_or_sim=None):
        if real_or_sim == 'real':
            fff = './DES_GW_Website/real-trigger_list.txt'
        if real_or_sim == 'sim':
            fff = './DES_GW_Website/test-trigger_list.txt'
        l = open(fff, 'r')
        lines = l.readlines()
        l.close()
        a = open(fff, 'a')
        triggers = []
        for line in lines:
            triggers.append(line.split(' ')[0])
        if not self.trigger_id in np.unique(triggers):
            a.write(self.trigger_id + ' ' + self.outfolder + '\n')
        a.close()
        tp.make_index_page('./DES_GW_Website', real_or_sim=real_or_sim)
        return

    def make_cumulative_probs(self):
        print ['python', './sims_study/cumulative_plots.py', '-d',
               '/data/des41.a/data/desgw/maininjector/sims_study/data', '-p', self.outfolder, '-e', self.trigger_id,
               '-f', os.path.join(self.outfolder, 'maps', self.trigger_id + '-ra-dec-prob-mjd-slot.txt')]
        subprocess.call(['python', './sims_study/cumulative_plots.py', '-d',
                         '/data/des41.a/data/desgw/maininjector/sims_study/data', '-p', self.outfolder, '-e',
                         self.trigger_id, '-f',
                         os.path.join(self.outfolder, 'maps', self.trigger_id + '-ra-dec-prob-mjd-slot.txt')])
        os.system('scp ' + os.path.join(self.outfolder,
                                        self.trigger_id + '-and-sim-cumprobs.png') + ' ./DES_GW_Website/Triggers/' + self.trigger_id + '/images/')

    def updateWebpage(self):
        os.system('scp -r DES_GW_Website/* codemanager@desweb.fnal.gov:/des_web/www/html/desgw/')
        tp.makeNewPage(os.path.join(self.outfolder, self.trigger_id + '_trigger.html'), self.trigger_id,self.event_paramfile)
        os.system('scp -r ' + os.path.join(self.outfolder,
                                           self.trigger_id + '_trigger.html') + ' codemanager@desweb.fnal.gov:/des_web/www/html/desgw/Triggers/' + self.trigger_id + '/')
        return


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
    with open("recycler.yaml", "r") as f:
        config = yaml.safe_load(f);
    # Set defaults to config
    trigger_path = config["trigger_path"]

    real_or_sim = config["real_or_sim"]

    if config["skymap_filename"] == 'Default':
        skymap_filename = None
    else:
        skymap_filename = config["skymap_filename"]

    trigger_ids = [config["trigger_id"]]

    force_mjd = config["force_mjd"]

    exposure_length = config["exposure_length"]

    # Override defaults with command line arguments
    # THESE NOT GUARANTEED TO WORK EVER SINCE WE SWITCHED TO YAML
    '''
    for o,a in opt:
        print 'Option'
        print o
        print a
        print '-----'
        if o in ["-tp","--triggerpath"]:
            trigger_path = str(a)
        elif o in ["-tid","--triggerid"]:
            trigger_ids = [str(a)]
        elif o in ["-mjd","--mjd"]:
            mjd = float(a)
        elif o in ["-exp","--exposure_length"]:
            exposure_length = float(a)
        elif o in ["-hours","--hours_available"]:
            hours_available = float(a)
        elif o in ["-sky","--skymapfilename"]:
            skymap_filename = str(a)
        else:
            print "Warning: option", o, "with argument", a, "is not recognized"
    '''
    # Clear bad triggers, only used for wrapping all triggers...
    badtriggers = open('badtriggers.txt', 'w')
    badtriggers.close()

    ####### BIG MONEY NO WHAMMIES ###############################################
    if config["wrap_all_triggers"]:
        trigger_ids = os.listdir(trigger_path)
        trigger_ids = trigger_ids[2:]
    for trigger_id in trigger_ids:
        if force_mjd:
            mjd = config["mjd"]
        else:
            try:
                mjd = open(os.path.join(trigger_path, trigger_id, trigger_id + '_eventMJD.txt'), 'r').read()
            except:
                mjd = '99999'
        if skymap_filename is None:
            try:
                mapname = open(os.path.join(trigger_path,
                                            trigger_id,
                                            'default_skymap.txt'), 'r').read()
                skymap_filename = os.path.join(trigger_path,
                                               trigger_id, mapname)
            except:
                badtriggers = open('badtriggers.txt', 'a')
                badtriggers.write(trigger_id + '\n')
                print 'Could not find skymap url file'
        try:
            try:
                mjd = float(mjd)
            except:
                badtriggers = open('badtriggers.txt', 'a')
                badtriggers.write(trigger_id + '\n')
                print 'WARNING: Could not convert mjd to float. Trigger: ' + trigger_id + ' flagged as bad.'
            e = event(skymap_filename,
                      os.path.join(trigger_path,
                                   trigger_id),
                      trigger_id, mjd, config)

            e.mapMaker(trigger_id, skymap_filename, exposure_length, config)
            e.getContours(exposure_length, config)
            jsonfilelist = e.makeJSON(config)
            e.make_cumulative_probs()
            e.updateTriggerIndex(real_or_sim=real_or_sim)
            e.updateWebpage()

            #eventmngr = Thread(target=jobmanager.eventmanager, args=(trigger_id, jsonfilelist,os.path.join(trigger_path,trigger_id),
            #                                                os.path.join(trigger_path, trigger_id, 'maps')))
            #eventmngr.start()

            e.send_nonurgent_Email()
            #eventmngr.join()

        except KeyError:
            print "Unexpected error:", sys.exc_info()
            badtriggers = open('badtriggers.txt', 'a')
            badtriggers.write(trigger_id + '\n')
    #############################################################################

    print 'Done'
