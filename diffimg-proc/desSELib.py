import numpy as np
import pyfits
import os
import ConfigParser
import sys
import argparse
from despyfits.DESImage import DESImage
import subprocess
from scipy import stats

#######
#deprecated.


################  USAGE ##############

parser = argparse.ArgumentParser()
parser.add_argument("confFile",help="Need a configuration file.")
args = parser.parse_args()


###########  Configuration ############

Config = ConfigParser.ConfigParser()
configFile = args.confFile 
Config.read(configFile)

def ConfigSectionMap(section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                DebugPrint("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1

####### Setting general stuffs #######

template_file = ConfigSectionMap("General")['template']
chiplist = ConfigSectionMap("General")['chiplist']
data_dir = ConfigSectionMap("General")['data_dir']
data_conf = ConfigSectionMap("General")['conf_dir']
correc_dir =  ConfigSectionMap("General")['corr_dir']
year =  ConfigSectionMap("General")['year']
epoch =  ConfigSectionMap("General")['epoch']


FILTER = ConfigSectionMap("General")['filter']
############  FUNCTIONS  ##############

#---------------------------#
#     copy functions       #
#---------------------------#

def copy_from_Dcash(file):
        cmd = 'ifdh cp -D ' + file + ' . '

	print 'getting '+ file +' from dcache'
        retval = subprocess.call(cmd.split(),stderr=subprocess.STDOUT)
        if retval != 0:
                sys.exit(1)

        return

def copy_to_Dcash(file, dir):
	cmd = 'ifdh cp -D ' + file + dir
	
	retval = subprocess.call(cmd.split(),stderr=subprocess.STDOUT)
        if retval != 0:
                sys.exit(1)

        return


#----------------------------------------------------------#
#     this function runs crosstalk trough a flat-field     #
#----------------------------------------------------------#

xtalk_file = ConfigSectionMap("crosstalk")['xtalk']
xtalk_template = ConfigSectionMap("crosstalk")['template']
replace_file = ConfigSectionMap("crosstalk")['replace']

copy_from_Dcash(data_conf+replace_file)

def crosstalk(EXPFILE,NITE,**args):

	copy_from_Dcash(data_conf+xtalk_file) #copy xtalk file
	copy_from_Dcash(data_dir + NITE + '/' + EXPFILE)  #copy data

	cmd = 'DECam_crosstalk ' + EXPFILE + \
        ' ' + xtalk_template.format(**args) +\
	' -crosstalk ' + xtalk_file + \
	' -ccdlist ' + chiplist +\
        ' -overscanfunction 0 -overscansample 1 -overscantrim 5 ' + \
        ' -photflag 1 -verbose 0' +\
	' -replace '+ replace_file 

	print '\n',cmd,'\n'

	retval = subprocess.call(cmd.split(),stderr=subprocess.STDOUT)
    	if retval != 0:
        	sys.exit(1)

	return


#---------------------------------------------------------------#
#     this function runs pixcorrect trough crosstalk output     #
#---------------------------------------------------------------#

bias = ConfigSectionMap("pixcorrect")['bias']
bpm = ConfigSectionMap("pixcorrect")['bpm']
linearity = ConfigSectionMap("pixcorrect")['linearity']
bf = ConfigSectionMap("pixcorrect")['bf']
flat = ConfigSectionMap("pixcorrect")['flat']

copy_from_Dcash(correc_dir+'lin_'+str(year)+'/'+linearity)
copy_from_Dcash(correc_dir+'bf_'+str(year)+'/'+bf)

def pixcorrect(CCD, **args):
	args['ccd']=CCD	

	copy_from_Dcash(correc_dir+'superflat_'+str(year)+'_'+str(epoch)+'/biascor/'+bias.format(**args))
        copy_from_Dcash(correc_dir+'superflat_'+str(year)+'_'+str(epoch)+'/norm-dflatcor/'+flat.format(**args) )
        copy_from_Dcash(correc_dir+'bpm_'+str(year)+'_'+str(epoch)+'/'+bpm.format(**args))
	

	cmd = 'pixcorrect_im --verbose --in ' + template_file.format(**args)+'_xtalk.fits' + \
	      ' -o ' +template_file.format(**args)+'_detrend.fits' \
	      ' --bias ' + bias.format(**args) + \
	      ' --bpm ' + bpm.format(**args) + \
	      ' --lincor ' +  linearity + \
	      ' --bf ' + bf + \
	      ' --gain '  + \
    	      ' --flat ' + flat.format(**args) + \
	      ' --mini ' + template_file.format(**args)+'_mini.fits'+ \
              ' --resaturate --fixcols --addweight'	

	print '\n',cmd,'\n'	
	
	retval = subprocess.call(cmd.split(),stderr=subprocess.STDOUT)
	if retval != 0:
		sys.exit(1)

	
	return


#----------------------------------------#
#     this function runs mkbleedmask     #
#----------------------------------------#

def bleedmask(CCD,name,**args):
	args['ccd']=CCD
	
	cmd = 'mkbleedmask ' + template_file.format(**args)+'_'+name+'.fits' + \
	' ' + template_file.format(**args)+'_bleedmasked.fits' + \
	'   -m -b 5 -f 1.0 -l 7 -n 7 -r 5 -s 40 -t 20 -v 3 -w 2.0 -y 1.0 -s 100 -v 3 -E 10'

	print '\n',cmd,'\n'	

	retval = subprocess.call(cmd.split(),stderr=subprocess.STDOUT)
	if retval != 0:
        	sys.exit(1)
    	return	

#----------------------------------------#
#     this function runs immask          #
#----------------------------------------#
def immask(CCD, name, **args):
	args['ccd']=CCD
	
	cmd = 'immask all ' + template_file.format(**args)+'_'+name+'.fits' +\
 	' ' +  template_file.format(**args)+'_immask.fits' +\
	'   --minSigma 7.0 --max_angle 360  --max_width 240 --nsig_detect 18 --nsig_mask 12 --nsig_merge 12'+\
	'   --write_streaks  --streaksfile ' + template_file.format(**args)+'_steafile.fits' 

	print '\n',cmd,'\n'	

	retval = subprocess.call(cmd.split(),stderr=subprocess.STDOUT)
        if retval != 0:
                sys.exit(1)
        return	
	

#---------------------------------------#
#            skyCombine                 #
#---------------------------------------#
PCFILENAMEPREFIX = ConfigSectionMap("skyCombineFit")['pcafileprefix']
PCFILENAME = PCFILENAMEPREFIX+'_'+str(year)+'_'+str(epoch)+'_'+FILTER+'_n04.fits'
copy_from_Dcash(correc_dir+'skytemp_'+str(year)+'_'+str(epoch)+'/'+PCFILENAME)


def skyCombineFit(inputFile):

        #-----------------------
        cmd = 'ls  *'+inputFile+'.fits > listpcain'
        print cmd 
	retval = subprocess.call(cmd, shell=True)

        if retval != 0:
                sys.exit(1)

        del cmd, retval

        #------------------------
        cmd = 'sky_combine --miniskylist listpcain -o skycombine.fits'
        print cmd
	retval = subprocess.call(cmd.split(),stderr=subprocess.STDOUT)

        if retval != 0:
                sys.exit(1)

        del cmd, retval

        #----------------------
        cmd = 'sky_fit --infilename skycombine.fits --outfilename skyfitinfo.fits --pcfilename  '+ PCFILENAME
	print cmd
	retval = subprocess.call(cmd.split(),stderr=subprocess.STDOUT)

        if retval != 0:
                sys.exit(1)


#------------------------------------------#
#              scamp                       #
#------------------------------------------#

imagflags = ConfigSectionMap("scamp")['imagflags']
flag_mask = ConfigSectionMap("scamp")['flag_mask']
flag_astr = ConfigSectionMap("scamp")['flag_astr']
catalog_ref = ConfigSectionMap("scamp")['catalog_ref']
default_scamp = ConfigSectionMap("scamp")['default_scamp']
head_file = ConfigSectionMap("scamp")['head']


farg = {'filter': FILTER}
head_FILE =  head_file.format(**farg)

copy_from_Dcash(data_conf+default_scamp)
copy_from_Dcash(data_conf+head_FILE)

def scamp(inputFile):
        cmd = 'scamp ' + inputFile +\
        ' ' + '-AHEADER_GLOBAL ' + head_FILE + ' -IMAFLAGS_MASK ' +imagflags+\
        ' ' + ' -FLAGS_MASK '  +flag_mask + ' -ASTR_FLAGSMASK ' +flag_astr+\
        ' -ASTRINSTRU_KEY DUMMY -AHEADER_SUFFIX .aheadnoexist -ASTREFMAG_LIMITS -99,17 ' +\
        ' -ASTREF_CATALOG ' +catalog_ref +' -c ' +default_scamp +\
        ' -WRITE_XML Y -XML_NAME scamp.xml -MOSAIC_TYPE SAME_CRVAL -ASTREF_BAND DEFAULT'

        print '\n',cmd,'\n'

        retval = subprocess.call(cmd.split(),stderr=subprocess.STDOUT)
        if retval != 0:
                sys.exit(1)
        return

#-----------------------------------------#
#           combineFiles                          
#----------------------------------------#-
def combineFiles(inputFile, outputFile):

        cmd = 'fitscombine *'+inputFile+' ' +outputFile
        retval = subprocess.call(cmd, shell=True)

        if retval != 0:
                sys.exit(1)
        return


#-----------------------------------------#
#             sextractor                  #
#-----------------------------------------#
sexnnwFile = ConfigSectionMap("sextractor")['starnnw_name']
sexconvFile = ConfigSectionMap("sextractor")['filter_name']
sexparamFile  = ConfigSectionMap("sextractor")['parameters_name']
configFile = ConfigSectionMap("sextractor")['configfile']

copy_from_Dcash(data_conf+sexnnwFile)
copy_from_Dcash(data_conf+sexconvFile)
copy_from_Dcash(data_conf+sexparamFile)
copy_from_Dcash(data_conf+configFile)
copy_from_Dcash(data_conf+'default.psf')


def sextractor(name, CCD, **args):
        args['ccd']=CCD

        cmd = 'sex ' + template_file.format(**args)+'_'+name+'.fits[0]'+\
        ' -c  ' + configFile + ' -FILTER_NAME ' + sexconvFile + ' -STARNNW_NAME ' +sexnnwFile + ' -CATALOG_NAME  ' + template_file.format(**args)+'_sextractor.fits'+\
        ' -FLAG_IMAGE '  + template_file.format(**args)+'_'+name+'.fits[1] -PARAMETERS_NAME ' + sexparamFile +\
        ' -DETECT_THRESH 10 -SATUR_KEY SATURATE  -CATALOG_TYPE FITS_LDAC -WEIGHT_IMAGE  ' + template_file.format(**args)+'_'+name+'.fits[2]'+\
        '  -WEIGHT_TYPE  MAP_WEIGHT  '

	print '\n',cmd,'\n'

        retval = subprocess.call(cmd.split(),stderr=subprocess.STDOUT)
        if retval != 0:
                sys.exit(1)
        return



#--------------------------------------#
#     fwhm routine from Wrappers      #
#--------------------------------------#

debug = 0
def fwhm(incat):
    """
    Get the median FWHM and ELLIPTICITY from the scamp catalog (incat)
    """
    CLASSLIM = 0.75      # class threshold to define star
    MAGERRLIMIT = 0.1  # mag error threshold for stars

    if debug: print "!!!! WUTL_STS: (fwhm): Opening scamp_cat to calculate median FWHM & ELLIPTICITY.\n"
    hdu = pyfits.open(incat,"readonly")

    if debug: print "!!!! WUTL_STS: (fwhm): Checking to see that hdu2 in scamp_cat is a binary table.\n"
    if 'XTENSION' in hdu[2].header:
        if hdu[2].header['XTENSION'] != 'BINTABLE':
            print "!!!! WUTL_ERR: (fwhm): this HDU is not a binary table"
            exit(1)
    else:
        print "!!!! WUTL_ERR: (fwhm): XTENSION keyword not found"
        exit(1)

    if 'NAXIS2' in hdu[2].header:
        nrows = hdu[2].header['NAXIS2']
        print "!!!! WUTL_INF: (fwhm): Found %s rows in table" % nrows
    else:
        print "!!!! WUTL_ERR: (fwhm): NAXIS2 keyword not found"
        exit(1)

    tbldct = {}
    for colname in ['FWHM_IMAGE','ELLIPTICITY','FLAGS','MAGERR_AUTO','CLASS_STAR']:
        if colname in hdu[2].columns.names:
            tbldct[colname] = hdu[2].data.field(colname)
        else:
            print "!!!! WUTL_ERR: (fwhm): No %s column in binary table" % colname
            exit(1)

    hdu.close()

    flags = tbldct['FLAGS']
    cstar = tbldct['CLASS_STAR']
    mgerr = tbldct['MAGERR_AUTO']
    fwhm = tbldct['FWHM_IMAGE']
    ellp = tbldct['ELLIPTICITY']

    fwhm_sel = []
    ellp_sel = []
    count = 0
    for i in range(nrows):
        if flags[i] < 1 and cstar[i] > CLASSLIM and mgerr[i] < MAGERRLIMIT and fwhm[i]>0.5 and ellp[i]>=0.0:
            fwhm_sel.append(fwhm[i])
            ellp_sel.append(ellp[i])
            count+=1

    fwhm_sel.sort()
    ellp_sel.sort()

    # allow the no-stars case count = 0 to proceed without crashing
    if count <= 0:
      fwhm_med = 4.0
      ellp_med = 0.0
    else:
      if count%2:
        # Odd number of elements
        fwhm_med = fwhm_sel[count/2]
        ellp_med = ellp_sel[count/2]
      else:
        # Even number of elements
        fwhm_med = 0.5 * (fwhm_sel[count/2]+fwhm_sel[count/2-1])
        ellp_med = 0.5 * (ellp_sel[count/2]+ellp_sel[count/2-1])

    if debug:
        print "FWHM=%.4f" % fwhm_med
        print "ELLIPTIC=%.4f" % ellp_med
        print "NFWHMCNT=%s" % count

    return (fwhm_med,ellp_med,count)	
	

#------------------------------------#
#        changing head               #
#------------------------------------#

def change_head(File, catalog, image, CCD, **args):

        ccdLen = len(CCD)

        #Getting the data and saving into an array
        o = open(File,'r').read().splitlines()
        info_array = ['CRVAL1','CRVAL2','CRPIX1','CRPIX2','CD1_1','CD1_2','CD2_1','CD2_2',\
                      'PV1_0','PV1_1 ','PV1_2','PV1_4','PV1_5','PV1_6','PV1_7','PV1_8','PV1_9','PV1_10',\
                      'PV2_0','PV2_1 ','PV2_2','PV2_4','PV2_5','PV2_6','PV2_7','PV2_8','PV2_9','PV2_10']

        n = len(info_array)
        matrix = []
        for ii in o:
                for oo in info_array:
                        if oo in ii.split('=')[0] :
                                #print ii.split('=')[0], ii.split('=')[1].split('/')[0]
                                matrix.append(ii.split('=')[1].split('/')[0])

        matrix = np.array(matrix)

	#changing the header
	cont = 0
        for i in range(ccdLen):
		ccdstring="%02d"%int(CCD[i])
                args['ccd']=ccdstring
                catalog1 = template_file.format(**args)+'_'+catalog+'.fits'
                image1 = template_file.format(**args)+'_'+image+'.fits'

                fwhm_, ellip, count = fwhm(catalog1)

                h=DESImage.load(image1)
                h.header['FWHM'] = fwhm_
                h.header['ELLIPTIC'] = ellip
		h.header['SCAMPFLG'] = 0		


		h1=pyfits.open(image1)
                im=h1[0].data
                iterate1=stats.sigmaclip(im,5,5)[0]
                iterate2=stats.sigmaclip(iterate1,5,5)[0]
                iterate3=stats.sigmaclip(iterate2,3,3)[0]
                skybrite=np.median(iterate3)
                skysigma=np.std(iterate3)


                h.header['SKYBRITE'] = skybrite
                h.header['SKYSIGMA'] = skysigma
                h.header['CAMSYM'] = 'D'
                h.header['SCAMPCHI'] = 0.0
                h.header['SCAMPNUM'] = 0

                for j in range(n):
                        h.header[info_array[j]] = float(matrix[cont])
			cont =  cont + 1

                h.save(template_file.format(**args)+'_wcs.fits')


