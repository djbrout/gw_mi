import os
import sys, getopt
import numpy as np
import triggerpages as tp
import getHexObservations
import recycler_config as config
import subprocess


class event:
    def __init__(self, skymap_filename, outfolder, trigger_id, mjd):
        # print skymap_filename
        # raw_input()
        self.skymap = skymap_filename
        self.mjd = mjd
        self.outfolder = outfolder
        self.trigger_id = trigger_id

        # Setup website directories
        self.mapspath = outfolder + "/maps/"
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

    def mapMaker(self, hours_available=None):

        try:
            distance = self.event_params['MaxDistance']
            distance = np.float((distance.tostring()).replace("Mpc", ""))
            if distance < 0.:
                distance = 60.
        except:
            distance = 60.  # hardcode unknown distance to 60Mpc

        # if exposure_length is None:
        # exposure_list = config.exposure_list
        # filter_list = config.filter_list
        if hours_available is None:
            hours_available = config.hours_available

        outputDir = self.mapspath
        if not os.path.exists(outputDir):
            os.makedirs(outputDir)
        trigger_id = self.trigger_id
        skymap = self.skymap.strip('\n')

        # make the maps
        probs, times, slotDuration, hoursPerNight = getHexObservations.prepare(
            skymap, mjd, trigger_id,
            self.outfolder, outputDir,
            exposure_list=config.exposure_list,
            filter_list=config.filter_list,
            distance=distance)

        # figure out how to divide the night
        n_slots, first_slot = getHexObservations.contemplateTheDivisionsOfTime(
            probs, times, hoursAvailable=hours_available)

        # compute the best observations
        best_slot = getHexObservations.now(
            n_slots, mapDirectory=outputDir, simNumber=trigger_id,
            mapZero=first_slot)

        # make obsrvation plots
        n_plots = getHexObservations.makeObservingPlots(
            n_slots, trigger_id, best_slot, self.outfolder, outputDir)

        self.best_slot = best_slot
        self.n_slots = n_slots
        self.first_slot = first_slot

    def getContours(self, exposure_length=None):
        import matplotlib.pyplot as plt

        if exposure_length is None:
            exposure_length = config.exposure_length
        image_dir = self.website_imagespath
        map_dir = self.mapspath

        if self.n_slots > 0:
            iname = self.trigger_id + "-" + str(self.best_slot) + "-maglim-eq.png"
            oname = self.trigger_id + "_limitingMagMap.png"
            os.system('cp ' + os.path.join(self.outfolder, 'maps', iname) + ' ' + os.path.join(image_dir, oname))
            iname = self.trigger_id + "-" + str(self.best_slot) + "-prob-eq.png"
            oname = self.trigger_id + "_sourceProbMap.png"
            os.system('cp ' + os.path.join(self.outfolder, 'maps', iname) + ' ' + os.path.join(image_dir, oname))
            iname = self.trigger_id + "-" + str(self.best_slot) + "-ligo-eq.png"
            oname = self.trigger_id + "_LIGO.png"
            os.system('cp ' + os.path.join(self.outfolder, 'maps', iname) + ' ' + os.path.join(image_dir, oname))
            iname = self.trigger_id + "-" + str(self.best_slot) + "-probXligo-eq.png"
            oname = self.trigger_id + "_sourceProbxLIGO.png"
            os.system('cp ' + os.path.join(self.outfolder, 'maps', iname) + ' ' + os.path.join(image_dir, oname))
            # DESGW observation map
            inname = self.trigger_id + "-observingPlot-{}.png".format(
                self.best_slot)
            outname = self.trigger_id + "-observingPlot.png"
            os.system('cp ' + os.path.join(map_dir, inname) + ' ' + os.path.join(image_dir, outname))
            # probability plot
            name = self.trigger_id + "-probabilityPlot.png"
            os.system('cp ' + os.path.join(map_dir, name) + ' ' + image_dir)

            # oname = 'observingPlots.gif'
            # giffile = os.path.join(self.outfolder,iname)+' '+ os.path.join(image_dir,oname)
            # oname = self.trigger_id+'-observingPlot-*.png'
            # pngs = os.path.join(self.outfolder,iname)+' '+ os.path.join(image_dir,oname)
            # os.system('convert -delay 10 -loop 0 '+pngs+' '+giffile)

        else:
            # there is nothing to observe, make default plots
            ra, dec, ligo, maglim, probMap = \
                getHexObservations.nothingToObserveShowSomething( \
                    self.skymap, self.mjd, exposure_length)
            print "================ >>>>>>>>>>>>>>>>>>>>> =================== "
            print "================ >>>>>>>>>>>>>>>>>>>>> =================== "
            print "faking it with getHexObservations.nothingToObserveShowSomething("
            print self.skymap, self.mjd, exposure_length
            print "================ >>>>>>>>>>>>>>>>>>>>> =================== "
            print "================ >>>>>>>>>>>>>>>>>>>>> =================== "

            figure = plt.figure(1)

            # computing limiting mag
            # plot as ra,dec map 
            plt.clf()
            plt.hexbin(ra, dec, maglim, vmin=15)
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

    def makeJSON(self):
        # DESGW json file (to be files once that is done)
        json_dir = self.website_jsonpath
        map_dir = self.mapspath
        jsonname = self.trigger_id + ".json"
        jsonFile = os.path.join(map_dir, jsonname)

        if self.n_slots > 0:
            # get statistics
            ra, dec, prob, mjd, slotNum = \
                getHexObservations.readObservingRecord(self.trigger_id, map_dir)

            # adding integrated probability to paramfile
            integrated_prob = np.sum(prob)
            nHexes = str(prob.size)
        else:
            integrated_prob = 0
            nHexes = str(0)

        from time import gmtime, strftime
        timeprocessed = strftime("%H:%M:%S GMT \t %b %d, %Y", gmtime())

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
                     nHexes=nHexes,
                     time_processed=timeprocessed,
                     boc=self.event_params['boc'],
                     CentralFreq=self.event_params['CentralFreq']
                     )
        else:
            np.savez(self.event_paramfile,
                     MJD='NAN',
                     ETA='NAN',
                     FAR='NAN',
                     ChirpMass='NAN',
                     MaxDistance='NAN',
                     integrated_prob='NAN',
                     M1='NAN',
                     M2='NAN',
                     nHexes=nHexes,
                     time_processed=timeprocessed,
                     boc='NAN',
                     CentralFreq='NAN',
                     )

        # Copy json file to web server for public download
        if not os.path.exists(jsonFile):
            if integrated_prob == 0:
                print "zero probability, thus no jsonFile at ", jsonFile
            else:
                print "no jsonFile at ", jsonFile
        else:
            os.system('cp ' + jsonFile + ' ' + self.website_jsonpath)
        return

    def send_nonurgent_Email(self):
        import smtplib
        from email.mime.text import MIMEText

        text = 'New event trigger. See \nhttp://des-ops.fnal.gov:8080/desgw/Triggers/' + self.trigger_id + '/' + self.trigger_id + '_trigger.html'

        # Create a text/plain message
        msg = MIMEText(text)

        # me == the sender's email address
        # you == the recipient's email address#
        me = 'automated-desGW@fnal.gov'
        yous = ['djbrout@gmail.com','marcelle@fnal.gov']
        for you in yous:
            msg['Subject'] = 'New GW Trigger ' + self.trigger_id
            msg['From'] = me
            msg['To'] = you

            # Send the message via our own SMTP server, but don't include the
            # envelope header.
            s = smtplib.SMTP('localhost')
            s.sendmail(me, [you], msg.as_string())
            s.quit()
        print 'Email sent...'
        return

    def updateTriggerIndex(self):
        l = open('./DES_GW_Website/trigger_list.txt', 'r')
        lines = l.readlines()
        l.close()
        a = open('./DES_GW_Website/trigger_list.txt', 'a')
        triggers = []
        for line in lines:
            triggers.append(line.split(' ')[0])
        if not self.trigger_id in np.unique(triggers):
            a.write(self.trigger_id + ' ' + self.outfolder + '\n')
        a.close()
        tp.make_index_page('./DES_GW_Website')
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
        tp.makeNewPage(os.path.join(self.outfolder, self.trigger_id + '_trigger.html'), self.trigger_id,
                       self.event_paramfile)
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

    # Set defaults to config
    trigger_path = config.trigger_path
    # skymap_filename = config.trigger_path
    skymap_filename = None
    # print skymap_filename
    # skymap_filename = '/data/des41.a/data/desgw/maininjector/real-triggers/G184098/G184098_bayestar.fits'

    trigger_ids = [config.trigger_id]
    mjd = config.test_mjd
    hours_available = config.hours_available

    force_mjd = config.force_mjd

    # Override defaults with command line arguments
    for o, a in opt:
        print 'Option'
        print o
        print a
        print '-----'
        if o in ["-tp", "--triggerpath"]:
            trigger_path = str(a)
        elif o in ["-tid", "--triggerid"]:
            trigger_ids = [str(a)]
        elif o in ["-mjd", "--mjd"]:
            mjd = float(a)
        # elif o in ["-exp","--exposure_length"]:
        #    exposure_length = float(a)
        elif o in ["-hours", "--hours_available"]:
            hours_available = float(a)
        elif o in ["-sky", "--skymapfilename"]:
            skymap_filename = str(a)
        else:
            print "Warning: option", o, "with argument", a, "is not recognized"

    badtriggers = open('badtriggers.txt', 'w')
    badtriggers.close()

    ####### BIG MONEY NO WHAMMIES ###############################################
    if config.wrap_all_triggers:
        trigger_ids = os.listdir(config.trigger_path)
    for trigger_id in trigger_ids:
        if skymap_filename is None:
            try:
                skymap_urlt = open(os.path.join(trigger_path,
                                                trigger_id,
                                                trigger_id + '_skymapURL.txt'), 'r').read().split('/')[-1]
                skymap_filename = os.path.join(trigger_path,
                                               trigger_id, trigger_id + '_' + skymap_urlt)
                # print skymap_urlt
                # print skymap_filename
            except:
                badtriggers = open('badtriggers.txt', 'a')
                badtriggers.write(trigger_id + '\n')
                print 'Could not find skymap url file'
        try:
            if not force_mjd:
                mjd = open(os.path.join(trigger_path,
                                        trigger_id,
                                        trigger_id + '_eventMJD.txt'), 'r').read()
                try:
                    mjd = float(mjd)
                except:
                    badtriggers = open('badtriggers.txt', 'a')
                    badtriggers.write(trigger_id + '\n')
                    print 'Could not convert mjd to float'
            e = event(skymap_filename,
                      os.path.join(trigger_path,
                                   trigger_id),
                      trigger_id, mjd)
            e.mapMaker(hours_available=hours_available)
            e.getContours()
            e.makeJSON()
            e.make_cumulative_probs()
            e.updateTriggerIndex()
            e.updateWebpage()

            e.send_nonurgent_Email()
        # except IOError:
        #    print "Unexpected error:", sys.exc_info()
        #    badtriggers = open('badtriggers.txt','a')
        #    badtriggers.write(trigger_id+'\n')
        except KeyError:
            print "Unexpected error:", sys.exc_info()
            badtriggers = open('badtriggers.txt', 'a')
            badtriggers.write(trigger_id + '\n')
    #############################################################################

    print 'Done'
