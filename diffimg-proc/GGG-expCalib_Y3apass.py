#!/usr/bin/env python
"""
    expCalib_Y3a.py
    Express Calibration, 
    This code will estimate the zero-points   
    v.3 Apr20, 2016
   NOW using apass_2massInDES.sorted.csv via APASS/2MASS.
    v.2 Feb25, 2016:
    Now use APASS Dr7 and tested with ALex.. MagsLite
    Date Thu Sep 24, 2015
    NOTE that this catalog is only for the officical DES-foot print, some ccd will have no ZP
    Example:   
    expCalib_Y3apass.py --help

    GGG-expCalib_Y3apass.py -s db-desoper --expnum 475956 --reqnum 04 --attnum 11 --verbose 1
    
    """
import despydb.desdbi
import os
import time
import datetime
import numpy as np
#from qatoolkit import oracle_util as orautil
#TEST
#####from oracle_util import *
#####import oracle_util as orautil
#from qatoolkit import oracle_util as orautil
##################################

def main():
    import argparse
    import time

    """Create command line arguments"""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--section','-s',default='db-desoper',
                        help='section in the .desservices file w/ DB connection information')
    parser.add_argument('--expnum', help='expnum is queried', default=350245, type=int)
    parser.add_argument('--reqnum', help='reqnum is queried', default=922, type=str)
    parser.add_argument('--attnum', help='attnum is queried', default=1, type=int)
    parser.add_argument('--magType', help='mag type to use (mag_psf, mag_auto, mag_aper_8, ...)', default='mag_psf')
    parser.add_argument('--sex_mag_zeropoint', help='default sextractor zeropoint to use to convert fluxes to sextractor mags (mag_sex = -2.5log10(flux) + sex_mag_zeropoint)', type=float, default=25.0)
    parser.add_argument('--verbose', help='verbosity level of output to screen (0,1,2,...)', default=0, type=int)
    parser.add_argument('--debug', help='debugging option', dest='debug', action='store_true', default=False)
                        
    args = parser.parse_args()
                        
    if args.verbose > 0: print args

#    sys.exit()

    # Open connection to database...
    #dbh = call_openconnectDB(args)

    #--
    #Get FITS TABLE ONLY if needed
    status = Wget_data_home(args)

    #
    #Get data from  PROD tables EXPOSURE IMAGE, WDF, and CATALOG 
    # --and Convert the Fits table to csv --

    #status = call_createcataloglistfromDB(args,dbh)

    #-- ADDED NEW
    #GET STD from APASS-DR9 and 2MASS
    status= getallccdfromAPASS9(args)

    #-- ADDED NEW
    status = doset(args)

    #WHEN NEEDED
    #plot ra,dec of Sex-vs Y2Q1 for each CCD
    if args.verbose >0 :
        status = plotradec_sexvsY2Q1(args)
    #--

    #Estimate 3sigma Clipped Zeropoint for each CCD
    status = sigmaClipZP(args)

    #--

    #plot ra,dec of matched stars for ALL CCDs

    status = plotradec_ZP(args)

    #-
    status=sigmaClipZPallCCDs(args)
    # Close connection to database...
    #call_closeconnectDB(dbh)
    #--

##################################
def call_openconnectDB(args):
    desdmfile = os.path.join(os.getenv("HOME"),".desservices.ini")
    dbh = despydb.desdbi.DesDbi(desdmfile,args.section)
    return dbh

##################################
def call_closeconnectDB(dbh):
    dbh.close()
    return 0

##################################
# Get data from  PROD tables EXPOSURE IMAGE, WDF, and CATALOG,
# then Convert the Fits table to csv and save it

def call_createcataloglistfromDB(args,dbh):
    import os
    import csv
    import time
    import healpy as hp    
    import sys

#    catname="""D%08d_%s_%s_r%sp%02d_sextractor_psf.fits""" % (args.expnum,"%","%",args.reqnum,args.attnum)
    
    #print catname

#    queryText ="""SELECT e.expnum, c.filename, e.nite, e.band, i.ccdnum,i.airmass, e.exptime, i.ra_cent,i.dec_cent, i.rac1,i.decc1,i.rac2,decc2,i.rac3,i.decc3,i.rac4,i.decc4 FROM  PROD.EXPOSURE E, PROD.IMAGE i, PROD.WDF, PROD.CATALOG c WHERE e.expnum=i.expnum AND  i.filename=wdf.parent_name AND wdf.child_name=c.filename AND  c.filename like '%s'  ORDER BY c.filename""" % (catname)
 
    '''  
    if args.verbose > 0: print queryText        
    #print 'Running query...'
    t0=time.time()
    cur = dbh.cursor()
    cur.execute(queryText)
    
    if args.verbose > 0: print "query took", time.time()-t0, "seconds"
    
    dtypeList=orautil.NumpyDescriptor(cur.description,lower=False)
    hdr = [col[0] for col in cur.description]

    aaa=cur.fetchall()
    data = np.array(aaa,dtype=dtypeList)
    '''
    catlistFile="""D%08d_r%sp%02d_red_catlist.csv""" % (args.expnum,args.reqnum,args.attnum)

    '''
    with open(catlistFile,'w') as csvFile:
        writer = csv.writer(csvFile,delimiter=',',  quotechar='|',
                            lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        #First output header...
        hdr = [col[0] for col in cur.description]
        
        writer.writerow(hdr)
        for i in range(data['FILENAME'].size):          
            line=data['EXPNUM'][i],data['FILENAME'][i],data['NITE'][i],data['BAND'][i],data['CCDNUM'][i],data['AIRMASS'][i],data['EXPTIME'][i], data['RA_CENT'][i], data['DEC_CENT'][i], data['RAC1'][i], data['DECC1'][i], data['RAC2'][i], data['DECC2'][i], data['RAC3'][i], data['DECC3'][i], data['RAC4'][i], data['DECC4'][i]
            #print line
            writer.writerow(line) 
    '''

    #call_closeconnectDB(dbh)  
    return 0

#############################################

def doset(args):
    import os
    import csv
    import time
    import healpy as hp    
    import sys
    
    if args.verbose >0 : print args

    catlistFile="""D%08d_r%sp%02d_red_catlist.csv""" % (args.expnum,args.reqnum,args.attnum)

    if not os.path.isfile(catlistFile):
        print '%s does not seem to exist... exiting now...' % catlistFile
        sys.exit(1)

    data=np.genfromtxt(catlistFile,dtype=None,delimiter=',',names=True)
        
    for i in range(data['FILENAME'].size):
        if os.path.isfile(data['FILENAME'][i]):
            Read_Sexcatalogfitstocsv(args,data['FILENAME'][i],data['BAND'][i])

            minra=min(data['RA_CENT'][i],data['RAC1'][i],data['RAC2'][i],data['RAC3'][i],data['RAC4'][i])
            maxra=max(data['RA_CENT'][i],data['RAC1'][i],data['RAC2'][i],data['RAC3'][i],data['RAC4'][i])
            mindec=min(data['DEC_CENT'][i],data['DECC1'][i],data['DECC2'][i],data['DECC3'][i],data['DECC4'][i])
            maxdec=max(data['DEC_CENT'][i],data['DECC1'][i],data['DECC2'][i],data['DECC3'][i],data['DECC4'][i])

            rac  = data['RA_CENT'][i]
            decc = data['DEC_CENT'][i]
            desipixc=getipix(data['RA_CENT'][i], data['DEC_CENT'][i])
            desipix1=getipix(data['RAC1'][i],data['DECC1'][i])
            desipix2=getipix(data['RAC2'][i],data['DECC2'][i])
            desipix3=getipix(data['RAC3'][i],data['DECC3'][i])
            desipix4=getipix(data['RAC4'][i],data['DECC4'][i])

            desipix12=getipix(data['RAC1'][i],data['DEC_CENT'][i])
            desipix23=getipix(data['RA_CENT'][i],data['DECC2'][i])
            desipix34=getipix(data['RAC3'][i],data['DEC_CENT'][i])
            desipix14=getipix(data['RA_CENT'][i],data['DECC4'][i]) 

            desipixlist= desipixc,desipix1,desipix2,desipix3,desipix4,desipix12,desipix23,desipix34,desipix14
            desipixlist=uniqlist(desipixlist)
        
            #getallccdfromY2QHPX(data['FILENAME'][i],desipixlist,minra,maxra,mindec,maxdec,dbh,data['BAND'][i])
############
           ####getallccdfromAPASS(data['FILENAME'][i],minra,maxra,mindec,maxdec,dbh,data['BAND'][i])
############

            ra1=[];ra2=[];dec1=[];dec2=[]
            matchlistout="""%s_match.csv""" % (data['FILENAME'][i])
            objlistFile ="""%s_Obj.csv"""   % (data['FILENAME'][i])
            stdlistFile ="""%s_std.csv"""   % (data['FILENAME'][i])        

            if not os.path.isfile(objlistFile):
                print '%s does not seem to exist... exiting now...' % objlistFile            
                sys.exit(1)

            if not os.path.isfile(stdlistFile):
                print '%s does not seem to exist... exiting now...' % stdlistFile
                sys.exit(1)

            stdracol=1
            stddeccol=2
            obsracol=1
            obsdeccol=2 
            matchTolArcsec=1.0 #1.0arcsec
            verbose=2
            matchSortedStdwithObsCats(stdlistFile,objlistFile,matchlistout,stdracol,stddeccol,obsracol,obsdeccol,matchTolArcsec,verbose)

    return 0
      
##################################
#get_data_home for NOW it is for all CCDs:
#
def Wget_data_home(args):
    import csv
    from despyserviceaccess import serviceaccess
    import os
    import glob
    import sys

    catname="""D%08d_%s_%s_r%sp%02d_sextractor_psf.fits""" % (args.expnum,"%","%",args.reqnum,args.attnum)
    myfile="""D%08d_*_r%sp%02d_sextractor_psf.fits""" % (args.expnum,args.reqnum,args.attnum)

    #Check first if file exists...
    if  glob.glob(myfile):
        #Print '%s does seem to exist... exiting now...' % catname
        print "relevant cat files already exist in the current directory... no need to wget..."
        #sys.exit(1)
        return 1
    else:
        print "relevant cat files are not in directory... wgetting them from archive..."

        queryText = """ select 'https://desar2.cosmology.illinois.edu/DESFiles/desarchive//'||fai.PATH||'/'||fai.FILENAME from prod.file_archive_info fai where filename like   '%s'  order by fai.filename """ % (catname)

        #new database
    
        if args.verbose > 0: print queryText

        creds = serviceaccess.parse(os.path.join(os.environ['HOME'], '.desservices.ini'),args.section)
        USERNAME = creds['user']
        PASSWORD = creds['passwd']
        dbh= despydb.desdbi.DesDbi(os.path.join(os.getenv("HOME"),".desservices.ini"),args.section)

        t0=time.time()
        cur = dbh.cursor()
        cur.execute(queryText)
    
        if args.verbose > 0: print "query took", time.time()-t0, "seconds"

        for line in cur:
            #print USERNAME,PASSWORD,line[0]
            line2= '--no-check-certificate --quiet --http-user=%s --http-password=%s %s' %(USERNAME,PASSWORD,line[0])
            #print line2
            os.system('wget %s' %line2 )   

        return 0
    
##################################
# Quick Read SEX_table filemane_sextractor_psf.fits then select subsame
# and write it as filemane_sextractor_psf.fits_Obj.csv
def Read_Sexcatalogfitstocsv(args,fitsname,band):

    import fitsio
    import string
    import numpy as np
    import math
    import csv

    catFilename=fitsname
    outFile="""%s_Obj.csv""" % (catFilename)

    extension=2
    hdr = ["OBJECT_NUMBER","RA","DEC","MAG","MAGERR","ZEROPOINT","MAGTYPE","BAND"]

    magType = args.magType.upper()
    magType = magType.strip()
    fluxType = magType.replace('MAG','FLUX')
    fluxerrType = magType.replace('MAG','FLUXERR') 

    SEXdata=[]
    columns=['NUMBER','ALPHAWIN_J2000','DELTAWIN_J2000',fluxType,fluxerrType,'SPREAD_MODEL','SPREADERR_MODEL','FWHM_WORLD', 'CLASS_STAR', 'FLAGS']

    Fdata = fitsio.read(catFilename,  columns=columns, ext=extension)[:]
    #w0=( Fdata['FLUX_PSF'] > 2000) _OLD  
    w0=( Fdata['FLUX_PSF'] > 1000)  #NEW
    w1=( Fdata['FLAGS'] <= 3)
    #w2=( (Fdata['CLASS_STAR'] > 0.8 ) | (np.abs(Fdata['SPREAD_MODEL'] + 3.*Fdata['SPREADERR_MODEL'] <0.003 )))
    # NEW May16,16
    w2=( (Fdata['CLASS_STAR'] > 0.8 ) & (Fdata['SPREAD_MODEL']  <0.01 ) )

    SEXdata = Fdata[w0 & w1 & w2]
    SEXdata = SEXdata[np.argsort(SEXdata['ALPHAWIN_J2000'])]
    fwhm_arcsec=3600.*SEXdata['FWHM_WORLD']
    mag= -2.5*np.log10(SEXdata[fluxType]) + args.sex_mag_zeropoint
    magerr = (2.5/math.log(10.))*(SEXdata[fluxerrType]/SEXdata[fluxType])
    zeropoint=args.sex_mag_zeropoint*(SEXdata[fluxType]/SEXdata[fluxType])
  
    with open(outFile,'w') as csvFile:
            writer = csv.writer(csvFile,delimiter=',',  quotechar='|',
                                lineterminator='\n', quoting=csv.QUOTE_MINIMAL)

            writer.writerow(hdr)
            line=[]
            for i in range(SEXdata.size):
                line=SEXdata['NUMBER'][i],SEXdata['ALPHAWIN_J2000'][i], SEXdata['DELTAWIN_J2000'][i], mag[i], magerr[i], zeropoint[i], magType,band 
                writer.writerow(line)

    SEXdata=[]
    Fdata=[]

##################################
def radec2thetaphi(ra, dec):
    import numpy as np
    return (90-dec)*np.pi/180., ra*np.pi/180.

##################################
#for DES--nside=128
def getipix(ra,dec):
    import healpy as hp
    nside=128
    theta, phi = radec2thetaphi(ra, dec)
    ipix = hp.pixelfunc.ang2pix(nside, theta, phi, nest=True)
    return ipix

##################################
#Uniq List with order preserving
def uniqlist(seq): 
   noDupes = []
   [noDupes.append(i) for i in seq if not noDupes.count(i)]
   return noDupes

##################################
#NEW
#use APASS_DR7, filters are V,B,G,R and I
#################################
#
def getallccdfromAPASS(catFilename,minra,maxra,mindec,maxdec,dbh,band):
    import csv
    import numpy as np
    import string
    import sys
    import os
    
    stdlistout="""%s_std.csv""" % (catFilename)
    queryText = """SELECT NOBS,ra,dec,%s as wavg_mag_psf, %s_ERR as wavg_magerr_psf FROM APASS_DR7 where %s between 13 and 19 and RA between %s and %s and DEC between %s and %s ORDER BY RA""" %(band,band,band,minra,maxra,mindec,maxdec)
    
    y2t0=time.time()
    cur = dbh.cursor()
    cur.execute(queryText)
    
    #print time.time()-y2t0, "seconds"

    dtypeList=orautil.NumpyDescriptor(cur.description,lower=False)
    hdr = [col[0] for col in cur.description]
    aaa=cur.fetchall()
    APASSdata = np.array(aaa,dtype=dtypeList)

    #print "Outputting query results to file",  stdlistout
    with open(stdlistout,'w') as csvFile:
        writer = csv.writer(csvFile,delimiter=',',  quotechar='|',
                            lineterminator='\n', quoting=csv.QUOTE_MINIMAL)

        hdr = [col[0] for col in cur.description]
        writer.writerow(hdr)
                            
        for i in range(APASSdata.size):
            line=APASSdata['NOBS'][i],APASSdata['RA'][i],APASSdata['DEC'][i],APASSdata['WAVG_MAG_PSF'][i],APASSdata['WAVG_MAGERR_PSF'][i]
            writer.writerow(line)
    

##################################
#NEW 
#use APASS_DR9, and 2mass file NAME apass_2massInDES.sorted-P9-CUT.csv
#filters are gmag_des,rmag_des,imag_des,zmag_des,Ymag_des
#################################
#def getallccdfromAPASS9(catlistFile):
def getallccdfromAPASS9(args):
    import csv
    import numpy as np
    import pandas as pd
    import string,sys,os

    #print NEED Round RA

    catlistFile="""D%08d_r%sp%02d_red_catlist.csv""" % (args.expnum,args.reqnum,args.attnum)

    if not os.path.isfile(catlistFile):
	print '%s does not seem to exist... exiting now...' % catlistFile
        sys.exit(1)

    data=np.genfromtxt(catlistFile,dtype=None,delimiter=',',names=True) #% (catlistFile)

    BAND=data['BAND'][0]
    minra=min(min(data['RA_CENT']),min(data['RAC1']),min(data['RAC2']),min(data['RAC3']),min(data['RAC4']))-0.1
    mindec=min(min(data['DEC_CENT']),min(data['DECC1']),min(data['DECC2']),min(data['DECC3']),min(data['DECC4']))-0.1
    maxra=max(max(data['RA_CENT']),max(data['RAC1']),max(data['RAC2']),max(data['RAC3']),max(data['RAC4']))+0.1
    maxdec=max(max(data['DEC_CENT']),max(data['DECC1']),max(data['DECC2']),max(data['DECC3']),max(data['DECC4']))+0.1

    #print minra,mindec

    df=pd.DataFrame()
    #myfile ="""/data/des40.a/data/dtucker/Y2A1/General/apass_2massInDESplus2.sorted.csv"""
    myfile ="""apass_2massInDESplus2.sorted.csv"""
    outfile="""STD%s""" % catlistFile

    BANDname=BAND+"mag_des"
    names=["MATCHID","RAJ2000_2mass","DEJ2000_2mass",BANDname,"SEPARCSEC"]

    chunksize = 10 ** 6
    good_data = []
    for chunk in pd.read_csv(myfile,usecols=names, chunksize=chunksize,low_memory=False,index_col=False):
        w0 = ( chunk['SEPARCSEC'] < 1.5 )
        w1 = ( chunk['RAJ2000_2mass'] > minra ) ;w2 = ( chunk['RAJ2000_2mass'] < maxra )
        w3 = ( chunk['DEJ2000_2mass'] > mindec );w4 = ( chunk['DEJ2000_2mass'] < maxdec )
        df = chunk[ w0 & w1 &  w2 & w3 & w4 ]
        if len(df)>0:
            good_data.append(df)
	
    datastd = pd.concat(good_data, ignore_index=True)

    datastd1= pd.DataFrame({'MATCHID':datastd['MATCHID'],'RA':datastd['RAJ2000_2mass'],'DEC':datastd['DEJ2000_2mass'],'WAVG_MAG_PSF':datastd[BANDname]})

    col=["MATCHID", "RA","DEC", "WAVG_MAG_PSF"]

    datastd1.to_csv(outfile,columns=col,sep=',',index=False)

    hdr=["MATCHID","RA","DEC","wavg_mag_psf"]

    for i in range(data['RA_CENT'].size):
        stdlistFile ="""%s_std.csv"""   % (data['FILENAME'][i])    
        minra=min(data['RA_CENT'][i],data['RAC1'][i],data['RAC2'][i],data['RAC3'][i],data['RAC4'][i])-.1
        maxra=max(data['RA_CENT'][i],data['RAC1'][i],data['RAC2'][i],data['RAC3'][i],data['RAC4'][i])+.1
        mindec=min(data['DEC_CENT'][i],data['DECC1'][i],data['DECC2'][i],data['DECC3'][i],data['DECC4'][i])-.1
        maxdec=max(data['DEC_CENT'][i],data['DECC1'][i],data['DECC2'][i],data['DECC3'][i],data['DECC4'][i])+.1
        w1 = ( datastd['RAJ2000_2mass'] > minra ) ;w2 = ( datastd['RAJ2000_2mass'] < maxra )
        w3 = ( datastd['DEJ2000_2mass'] > mindec );w4 = ( datastd['DEJ2000_2mass'] < maxdec )
        df = datastd1[ w0 & w1 &  w2 & w3 & w4 ].sort(['RA'], ascending=True)
        df.to_csv(stdlistFile,columns=col,sep=',',index=False)

    
##################################
#
##################################
#use HPX and added cuts around the center
def getallccdfromY2QHPX(catFilename,desipixlist,minra,maxra,mindec,maxdec,dbh,band):
    import csv
    import numpy as np
    import string
    import sys
    import os
    
    minpix=256*(min(desipixlist)-1)
    maxpix=256*(max(desipixlist)+1)
    stdlistout="""%s_std.csv""" % (catFilename)

    queryText = """SELECT QUICK_OBJECT_ID,ra,dec, wavg_mag_psf_%s as  wavg_mag_psf ,wavg_magerr_psf_%s as wavg_magerr_psf FROM Y2Q1_OBJECTS@DESsci where HPX2048 between %s and %s and WAVG_MAG_PSF_%s between 14 and 20  and (WAVG_SPREAD_MODEL_I + 3.*spreaderr_model_i) between -0.003 and 0.003 and RA between %s and %s and DEC between %s and %s ORDER BY RA""" %(band,band,minpix,maxpix,band,minra,maxra,mindec,maxdec)
    
    y2t0=time.time()
    cur = dbh.cursor()
    cur.execute(queryText)
    
    #print time.time()-y2t0, "seconds"

    dtypeList=orautil.NumpyDescriptor(cur.description,lower=False)
    hdr = [col[0] for col in cur.description]
    aaa=cur.fetchall()
    Y2Q1data = np.array(aaa,dtype=dtypeList)

    #print "Outputting query results to file",  stdlistout
    with open(stdlistout,'w') as csvFile:
        writer = csv.writer(csvFile,delimiter=',',  quotechar='|',
                            lineterminator='\n', quoting=csv.QUOTE_MINIMAL)

        hdr = [col[0] for col in cur.description]
        writer.writerow(hdr)
                            
        for i in range(Y2Q1data.size):
            line=Y2Q1data['QUICK_OBJECT_ID'][i],Y2Q1data['RA'][i],Y2Q1data['DEC'][i],Y2Q1data['WAVG_MAG_PSF'][i],Y2Q1data['WAVG_MAGERR_PSF'][i]
            writer.writerow(line)
    
          
##################################
#New plots ONLY if NEEDED!!
def plotradec_sexvsY2Q1(args):
    import numpy as np
    import string
    import sys
    import matplotlib.pyplot as plt

    if args.verbose >0 : print args

    catlistFile="""D%08d_r%sp%02d_red_catlist.csv""" % (args.expnum,args.reqnum,args.attnum)

    if not os.path.isfile(catlistFile):
        print '%s does not seem to exist... exiting now...' % catlistFile
        sys.exit(1)

    data=np.genfromtxt(catlistFile,dtype=None,delimiter=',',names=True)

    for i in range(data['FILENAME'].size):
        ra1=[];ra2=[];dec1=[];dec2=[]
        catFilename = os.path.basename(data['FILENAME'][i])
        rac  = data['RA_CENT'][i] ;     decc = data['DEC_CENT'][i]
        rac1 = data['RAC1'][i] ;        decc1= data['DECC1'][i]
        rac2 = data['RAC2'][i] ;        decc2= data['DECC2'][i]
        rac3 = data['RAC3'][i] ;        decc3= data['DECC3'][i]
        rac4 = data['RAC4'][i] ;        decc4= data['DECC4'][i]
        CCDpoints=[[rac2,decc2],[rac,decc2],[rac3,decc3],[rac3,decc],[rac4,decc4],[rac,decc4],[rac1,decc1],[rac1,decc]]
        ccdline = plt.Polygon(CCDpoints,  fill=None, edgecolor='g')

        pnglistout="""%s.png""" % (catFilename)
        objlistFile="""%s_Obj.csv""" % (catFilename)
        stdlistFile="""%s_std.csv""" % (catFilename)        

        if not os.path.isfile(objlistFile):
            print '%s does not seem to exist... exiting now...' % objlistFile
            sys.exit(1)

        if not os.path.isfile(stdlistFile):
            print '%s does not seem to exist... exiting now...' % stdlistFile
            sys.exit(1)

        # Read in the file...
        ra1=np.genfromtxt(stdlistFile,dtype=float,delimiter=',',skiprows=1,usecols=(1))
        dec1=np.genfromtxt(stdlistFile,dtype=float,delimiter=',',skiprows=1,usecols=(2))
        ra2=np.genfromtxt(objlistFile,dtype=float,delimiter=',',skiprows=1,usecols=(1))
        dec2=np.genfromtxt(objlistFile,dtype=float,delimiter=',',skiprows=1,usecols=(2))
        plt.axes()
        plt.gca().add_patch(ccdline)
        plt.scatter(ra1,dec1,marker='.')
        plt.scatter(ra2,dec2,c='r', marker='+')
        line = plt.Polygon(CCDpoints,  fill=None, edgecolor='r')

        plt.title(catFilename, color='#afeeee') 
        plt.savefig(pnglistout, format="png" )

        ra1=[];ra2=[];dec1=[];dec2=[]
        
        plt.clf() 

##################################
#Matching FILES MAKE SURE the Cols are still in the same order
#
def matchSortedStdwithObsCats(inputStdFile,inputObsFile,outputMatch,racolStdFile,deccolStdFile,racolObsFile,deccolObsFile,matchArcsec,verbose):

    import math
    import sys
    
    f1=inputStdFile
    f2=inputObsFile
    outfile=outputMatch
    stdracol=racolStdFile
    stddeccol=deccolStdFile
    obsracol=racolObsFile
    obsdeccol=deccolObsFile
    matchTolArcsec=matchArcsec
    verbose=verbose

    #print f1,f2,outfile,stdracol,stddeccol,obsracol,obsdeccol,matchTolArcsec,verbose

    # Initialize "dictionaries"...
    # Each element of a "dictionary" is associated with a standard star.
    # Each element is a list of information from the potential matches from the
    #  observed data.
    raDict=[]
    decDict=[]
    obslineDict=[]
    
    # Initialize lists of standard stars...
    # These are actually lists of standards within a given sliding window of RA.
    stdra_win=[]
    stddec_win=[]
    stdline_win=[]
    
    # Open the output file for the standard star/observed star matches...
    ofd=open(outfile,'w')

    # Initialize running match id
    matchid=0
    
    # Open the standard star CSV file...
    fd1=open(f1)
    
    # Read header line of standard star CSV file...
    h1=fd1.readline()
    h1n=h1.strip().split(',')
    
    # Open CSV file of observed data...
    fd2=open(f2)
    
    # Read header line of observed data CSV file...
    h2=fd2.readline()
    h2n=h2.strip().split(',')

    # Create and output header for the output CSV file...
    #  Note that the column names from the standard star file
    #  now have a suffix of "_1", and that column names from
    #  the observed star file now have a suffix of "_2".
    outputHeader='MATCHID'
    for colhead in h1n:
        outputHeader=outputHeader+','+colhead.upper()+'_1'
    for colhead in h2n:
        outputHeader=outputHeader+','+colhead.upper()+'_2'
    outputHeader=outputHeader+'\n'
    ofd.write(outputHeader)
    

    # initialize some variables
    #  done_std = "are we done reading the standard stars file?"
    #  done_obs = "are we done reading the observations file?"
    #  stdra, stddec = "current values for standard star RA,DEC"
    #  obsra, obsdec = "current values for observed star RA,DEC"
    #  tol = sky angular separation tolerance (in degrees)
    #  tol2 = square of tol
    #  tolrawin = half-range of RA window (in degrees)
    #  linecnt = "line count"
    done_std=0
    done_obs=0
    stdra=-999
    stddec=-999
    obsra=-999
    obsdec=-999
    tol=matchTolArcsec/3600.0
    tol2=tol*tol
    tolrawin=3.*tol

    linecnt=0
    
    # Loop through file of observed data...
    while (done_obs == 0):

        # Increment line count from observed data file...
        linecnt += 1
        if ( (linecnt/1000.0 == int(linecnt/1000.0)) and (verbose > 1) ):
            print '\r'+'Progress (lines read from observed catalog):  ',linecnt,
            sys.stdout.flush()

        # Read line from observed data file...
        l2=fd2.readline()

        # Are we done reading through the file of observed data yet?
        # If so, set done_obs=1 and ignore the rest of the loop;
        # otherwise, process the data line and continue with the
        # rest of the loop...
        if l2 == "":
            done_obs = 1
            continue
        else:
            #obsline2 holds the whole line of information for this entry for
            # future use...
            obsline2=l2.strip()
            l2s=l2.strip().split(',')
            obsra=float(l2s[obsracol])
            obsdec=float(l2s[obsdeccol])
        #endif


        # Update the sliding RA window of standard stars...
        #  ... but only if stdra-obsra <= tolrawin, 
        #  ... and only if we haven't previously finished
        #      reading the standard star file...
        while ( (stdra-obsra <= tolrawin) and (done_std == 0) ):

            # Read the next line from the standard star file...
            l1=fd1.readline()
        
            # if we have reached the end of the standard star file,
            # set done_std=1 and skip the rest of this code block; 
            # otherwise, process the new line...
            if l1 ==  "":

                done_std=1

            else:

                l1s=l1.strip().split(',')
                stdra_new=float(l1s[stdracol])
                stddec_new=float(l1s[stddeccol])

                # if the new standard star RA (stdra_new) is at or above the 
                #  lower bound, add this standard star to the sliding RA 
                #  window...
                if ((stdra_new-obsra) >= -tolrawin):

                    # update values of stdra, stddec...
                    stdra = stdra_new
                    stddec = stddec_new

                    # add the standard star info to lists of ra, dec, and general
                    #  data for this sliding window...
                    stdra_win.append(stdra)
                    stddec_win.append(stddec)
                    stdline_win.append(l1.strip())
            
                    # initialize lists for possible observed star/standard star 
                    #  matches and add these (still empty) lists to "dictionaries" 
                    #  associated with this sliding window of standard stars...
                    raDict.append([])
                    decDict.append([])
                    obslineDict.append([])
            
                #endif
            
            #endif

        #endwhile -- inner "while" loop

        
        # Find the first good match (not necessarily the best match) between this
        # observed star and the set of standard stars within the sliding RA
        # window... 
        # (We might want to revisit this choice -- i.e., of first match vs. best
        #  match -- in the future.)
        
        cosd=math.cos(math.radians(obsdec))

        # Loop through all standards stars i in the sliding RA window for that
        #  observed star...
        for i in range(0,len(stdra_win)):

            delta2=(obsra-stdra_win[i])*(obsra-stdra_win[i])*cosd*cosd+(obsdec-stddec_win[i])*(obsdec-stddec_win[i])

            # Is the sky position of standard star i (in the sliding RA window)
            #  within the given radial tolerance of the observed star?  If so, 
            #  add the observed info to that standard star's dictionaries...
            if float(delta2) < float(tol2):
                raDict[i].append(obsra)
                decDict[i].append(obsdec)
                obslineDict[i].append(obsline2)
                # if we found one match, we take it and break out of this "for"
                #  loop...
                break
            #endif 

        #endfor


        # Do some cleanup of the lists and "dictionaries" associated with the 
        #  sliding RA window and output matches to output file...
        #  For each iteration of this while loop, we look at the "zeroth"
        #  standard star in the sliding RA window and remove it if it
        #  turns out to be now outside the RA tolerance window.
        while ( (len(stdra_win) > 1) and (obsra-stdra_win[0] > tolrawin) ):

            # Loop through all the observations matched with this standard 
            # star...
            # (Note that many standard stars may have zero matches...)
            for j in range(0,len(raDict[0])):

                # increment the running star id
                matchid += 1
                        
                # output line to the match file...
                outputLine = """%d,%s,%s\n""" % (matchid,stdline_win[0],obslineDict[0][j])
                ofd.write(outputLine)

            #endfor

            # Delete the dictionaries associated with this standard star
            #  (star "0" in the sliding RA window)...
            del raDict[0]
            del decDict[0]
            del obslineDict[0]
    
            # Delete the lists associated with standard star
            #  (star "0" in the sliding RA window)...
            del stdra_win[0]
            del stddec_win[0]
            del stdline_win[0]

        #endwhile -- inner "while" loop

    #endwhile -- outer "while" loop
        

    # Do some cleanup of the lists and "dictionaries" associated with the sliding 
    #  RA window after reading last line of observed data file and output matches
    #  to output file...
    while (len(stdra_win) > 0):

        # Loop through all the observations matched with this standard star...
        # (Note that many standard stars may have zero matches...)
        for j in range(0,len(raDict[0])):

            # increment the running star id
            matchid += 1

            # output line to the match file...
            outputLine = """%d,%s,%s\n""" % (matchid,stdline_win[0],obslineDict[0][j])
            ofd.write(outputLine)

        #endfor

        # Delete the dictionaries associated with this standard star
        #  (star "0" in the sliding RA window)...
        del raDict[0]
        del decDict[0]
        del obslineDict[0]
    
        # Delete the lists associated with standard star
        #  (star "0" in the sliding RA window)...
        del stdra_win[0]
        del stddec_win[0]
        del stdline_win[0]
            
    #endwhile
        
    # close the input and output files...
    fd1.close()
    fd2.close()
    ofd.close()

    return 0

##################################
# Get 3sigma clipped Zero point and iterater
##################################

def sigmaClipZP(args):
    import astropy 
    from astropy.stats import sigma_clip
    import numpy as np
    from numpy import mean
    import numpy.ma as ma 
    import string
    import sys
    import math

    if args.verbose >0 : print args

    catlistFile="""D%08d_r%sp%02d_red_catlist.csv""" % (args.expnum,args.reqnum,args.attnum)

    if not os.path.isfile(catlistFile):
        print '%s does not seem to exist... exiting now...' % catlistFile
        sys.exit(1)

    data1=np.genfromtxt(catlistFile,dtype=None,delimiter=',',names=True)
    
    ZeroListFile="""Zero_D%08d_r%sp%02d.csv""" % (args.expnum,args.reqnum,args.attnum)
    fout=open(ZeroListFile,'w')
    hdr = "FILENAME,Nall,Nclipped,ZP,ZPrms,magType\n"
    fout.write(hdr)

    for i in range(data1['FILENAME'].size):
        catFilename = os.path.basename(data1['FILENAME'][i])
        matchListFile="""%s_match.csv""" % (catFilename)        
        if not os.path.isfile(matchListFile):
            print '%s does not seem to exist... exiting now...' % matchListFile
            sys.exit(1)

        try:
            #add new cuts for Apass9-2mass data set
            data11=np.genfromtxt(matchListFile,dtype=None,delimiter=',',names=True)
            #New CUTS
            w0=(data11['MAG_2']-data11['WAVG_MAG_PSF_1']-25.0) < -10
            w1=(data11['MAG_2']-data11['WAVG_MAG_PSF_1']-25.0) > -40
            data=data11[ w0 & w1 ]

            # Identify band...      It is now BAND_2!!
            bandList = data['BAND_2'].tolist()
            band = bandList[0].upper()

            WAVG_MAG_PSF_1       =data['WAVG_MAG_PSF_1']
            MAG_2                =data['MAG_2']
            delt_mag_data        =MAG_2 -WAVG_MAG_PSF_1 -25.0
            filtered_data        =sigma_clip(delt_mag_data, 3, 3, np.mean, copy=True)
            NumStarsClipped      =(filtered_data).count()
            NumStarsAll          =len(filtered_data)

            if  NumStarsClipped >2:
                sigclipZP=np.mean(filtered_data)
                stdsigclipzp=np.std(filtered_data)/math.sqrt(NumStarsClipped)

            else:
                sigclipZP=-999
                stdsigclipzp=-999
        except:
            sigclipZP      =-999
            stdsigclipzp   =-999
            NumStarsClipped=0
            NumStarsAll    =0

        line = """%s,%d,%d,%f,%f,%s""" % (catFilename, NumStarsAll,NumStarsClipped,sigclipZP,stdsigclipzp,args.magType)

        fout.write(line+'\n')

##################################
#Given two csv join both output to MergedFile
def jointwocsv(file1,file2,MergedFile):
    
    import csv
    from collections import OrderedDict

    filenames = file1, file2
    data = OrderedDict()
    fieldnames = []
    for filename in filenames:
        with open(filename, "rb") as fp: 
            reader = csv.DictReader(fp)
            fieldnames.extend(reader.fieldnames)
            for row in reader:
                data.setdefault(row["FILENAME"], {}).update(row)

    fieldnames = list(OrderedDict.fromkeys(fieldnames))
    with open(MergedFile, "wb") as fp:
        writer = csv.writer(fp)
        writer.writerow(fieldnames)
        for row in data.itervalues():
            writer.writerow([row.get(field, '') for field in fieldnames])

##################################
# round ra 360.0--0.0
def roundra(ra):
    if ra < 357:
        return ra
    return ra-360.

##################################            
#New plots for Zero-Points
def plotradec_ZP(args):
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    import sys

    if args.verbose >0 : print args

    catlistFile="""D%08d_r%sp%02d_red_catlist.csv""" % (args.expnum,args.reqnum,args.attnum)

    if not os.path.isfile(catlistFile):
        print '%s does not seem to exist... exiting now...' % catlistFile
        sys.exit(1)

    ZeroListFile="""Zero_D%08d_r%sp%02d.csv""" % (args.expnum,args.reqnum,args.attnum)
    if not os.path.isfile(catlistFile):
        print '%s does not seem to exist... exiting now...' % ZeroListFile
        sys.exit(1)

    MergedFile="""Merged_D%08d_r%sp%02d.csv""" % (args.expnum,args.reqnum,args.attnum)

    jointwocsv(catlistFile,ZeroListFile,MergedFile)

    data=np.genfromtxt(MergedFile,dtype=None,delimiter=',',names=True)
    
    while ( np.std(data['RA_CENT']) >10 ) :
        data['RA_CENT']=[roundra(x) for x in data['RA_CENT']]
        data['RAC1']   =[roundra(x) for x in data['RAC1']]
        data['RAC2']   =[roundra(x) for x in data['RAC2']]
        data['RAC3']   =[roundra(x) for x in data['RAC3']]
        data['RAC4']   =[roundra(x) for x in data['RAC4']]
    
    w0=(data['ZP']==-999) 
    w1=(data['ZP']>-999)

    data0=data[w0]
    data1=data[w1]

    if (len(data1)==0):
         sys.exit(1)

    zpmin=np.min(data1['ZP'])
    zpmax=np.max(data1['ZP'])
    nmin=np.min(data1['Nclipped'])
    nmax=np.max(data1['Nclipped'])

    BAND=data1['BAND'][0]
    zpmedian=np.median(data1['ZP'])

    pnglistout0="""%s_ZP.png""" % (catlistFile)
    pnglistout1="""%s_deltaZP.png""" % (catlistFile)
    pnglistout2="""%s_NumClipstar.png""" % (catlistFile)
    pnglistout4="""%s_CCDsvsZPs.png""" % (catlistFile)

    minra=min(min(data['RA_CENT']),min(data['RAC1']),min(data['RAC2']),min(data['RAC3']),min(data['RAC4']))-.075
    mindec=min(min(data['DEC_CENT']),min(data['DECC1']),min(data['DECC2']),min(data['DECC3']),min(data['DECC4']))-.075
    maxra=max(max(data['RA_CENT']),max(data['RAC1']),max(data['RAC2']),max(data['RAC3']),max(data['RAC4']))+.075
    maxdec=max(max(data['DEC_CENT']),max(data['DECC1']),max(data['DECC2']),max(data['DECC3']),max(data['DECC4']))+.075

    ################
    #New plot the RA, DEC vs the expCal Zero-point mag 
    ################
    l1=plt.scatter(data0['RA_CENT'], data0['DEC_CENT'], c=data0['ZP'], s=15, marker=(25,0), cmap=mpl.cm.spectral,vmin=zpmin, vmax=zpmax)
    l2=plt.scatter(data1['RA_CENT'], data1['DEC_CENT'], c=data1['ZP'], s=500, marker=(5,0), cmap=mpl.cm.spectral,vmin=zpmin, vmax=zpmax)
    cbar=plt.colorbar(ticks=np.linspace(zpmin,zpmax, 4))    
    cbar.set_label('Zero-Point Mag')
    #plt.legend((l1,l2),('No Y2Q1 data','ExpCal'),scatterpoints=1,loc='upper left',ncol=1, fontsize=9)
    plt.legend((l1,l2),('No APASS data','ExpCal'),scatterpoints=1,loc='upper left',ncol=1, fontsize=9)

    for i in range(data['RA_CENT'].size):
        CCDpoints=[[data['RAC2'][i],data['DECC2'][i]],[data['RAC3'][i],data['DECC3'][i]],[data['RAC4'][i],data['DECC4'][i]],[data['RAC1'][i],data['DECC1'][i]]]
        ccdline = plt.Polygon(CCDpoints,  fill=None, edgecolor='k')
        plt.gca().add_patch(ccdline)

    plt.title('D%08d_r%sp%02d %s-Band ZP_Median=%.3f ' %(args.expnum,args.reqnum,args.attnum,BAND,zpmedian))   
    plt.xlabel(r"$RA$", size=18)
    plt.ylabel(r"$DEC$", size=18)
    plt.xlim([minra,maxra])
    plt.ylim([mindec,maxdec])
    plt.savefig(pnglistout0, format="png" )
    plt.clf() 

    ################
    #New plot the RA, DEC vs the expCal Delta Zero-point mag from median 
    ################
    l1=plt.scatter(data0['RA_CENT'], data0['DEC_CENT'], c=data0['ZP'], s=15, marker=(25,0), cmap=mpl.cm.spectral,vmin=zpmin, vmax=zpmax)
    l2=plt.scatter(data1['RA_CENT'], data1['DEC_CENT'], c=1000*(data1['ZP']-zpmedian), s=500, marker=(5,0), cmap=mpl.cm.spectral,vmin=min(1000*(data1['ZP']-zpmedian)), vmax=max(1000*(data1['ZP']-zpmedian)))
    cbar=plt.colorbar(ticks=np.linspace(min(1000*(data1['ZP']-zpmedian)),max(1000*(data1['ZP']-zpmedian)), 4))    
    cbar.set_label('Delta Zero-Point mili-Mag')
    #plt.legend((l1,l2),('No Y2Q1 data','ExpCal'),scatterpoints=1,loc='upper left',ncol=1, fontsize=9)
    plt.legend((l1,l2),('No APASS data','ExpCal'),scatterpoints=1,loc='upper left',ncol=1, fontsize=9)

    for i in range(data['RA_CENT'].size):
        CCDpoints=[[data['RAC2'][i],data['DECC2'][i]],[data['RAC3'][i],data['DECC3'][i]],[data['RAC4'][i],data['DECC4'][i]],[data['RAC1'][i],data['DECC1'][i]]]
        ccdline = plt.Polygon(CCDpoints,  fill=None, edgecolor='k')
        plt.gca().add_patch(ccdline)

    plt.title('D%08d_r%sp%02d %s-Band ZP_Median=%.3f ' %(args.expnum,args.reqnum,args.attnum,BAND,zpmedian))   

    plt.xlabel(r"$RA$", size=18)
    plt.ylabel(r"$DEC$", size=18)
    plt.xlim([minra,maxra])
    plt.ylim([mindec,maxdec])
    plt.savefig(pnglistout1, format="png" )
    plt.clf() 

    ################
    #New plot RA DEC vs Number of stars clipped stars from expCal 
    ################
    l1=plt.scatter(data0['RA_CENT'], data0['DEC_CENT'], c=data0['Nclipped'], s=15, marker=(25,0), cmap=mpl.cm.spectral)
    l2=plt.scatter(data1['RA_CENT'], data1['DEC_CENT'], c=data1['Nclipped'], s=500, marker=(5,0), cmap=mpl.cm.spectral)

    cbar=plt.colorbar()
    cbar.set_label('No. 3 $\sigma$ clipped Stars')
    #plt.legend((l1,l2),('No Y2Q1 data','expCal'),scatterpoints=1,loc='upper left',ncol=1, fontsize=9)
    plt.legend((l1,l2),('No APASS data','expCal'),scatterpoints=1,loc='upper left',ncol=1, fontsize=9)

    for i in range(data['RA_CENT'].size):
        CCDpoints=[[data['RAC2'][i],data['DECC2'][i]],[data['RAC3'][i],data['DECC3'][i]],[data['RAC4'][i],data['DECC4'][i]],[data['RAC1'][i],data['DECC1'][i]]]
        ccdline = plt.Polygon(CCDpoints,  fill=None, edgecolor='k')
        plt.gca().add_patch(ccdline)
   
    plt.title('D%08d_r%sp%02d %s-Band ZP_Median=%.3f ' %(args.expnum,args.reqnum,args.attnum,BAND,zpmedian))
   
    plt.xlabel(r"$RA$", size=18)
    plt.ylabel(r"$DEC$", size=18)
    plt.xlim([minra,maxra])
    plt.ylim([mindec,maxdec])
    plt.savefig(pnglistout2, format="png" )
    plt.clf() 


################    
#New plot CCDs vs ZP from expCal
    #plt.errorbar(data0['CCDNUM'], data0['ZP'], data0['ZPrms'], fmt='o',label='No Y2Q1 data')
    plt.errorbar(data0['CCDNUM'], data0['ZP'], data0['ZPrms'], fmt='o',label='No APASS data')
    plt.errorbar(data1['CCDNUM'], data1['ZP'], data1['ZPrms'], fmt='o',label='expCal')
    legend = plt.legend(loc='upper center', shadow=None, fontsize=12)
    legend.get_frame().set_facecolor('#00FFCC')
    plt.title('D%08d_r%sp%02d %s-Band ZP_Median=%.3f ' %(args.expnum,args.reqnum,args.attnum,BAND,zpmedian))
    plt.xlabel(r"$CCDs$", size=18)
    plt.ylabel(r"$Zero Points$", size=18)
    plt.ylim(min(data1['ZP'])-.01,max(data1['ZP'])+.02)
    plt.xlim(min(data1['CCDNUM'])-1.5,max(data1['CCDNUM'])+1.5)
    plt.savefig(pnglistout4, format="png" )
    plt.clf()


##########################################
    MergedFile="""Merged_D%08d_r%sp%02d.csv""" % (args.expnum,args.reqnum,args.attnum)
    #os.system('rm -rf merged.csv')
    myfile="""D%08d_*_r%sp%02d_sextractor_psf.fits""" % (args.expnum,args.reqnum,args.attnum)
    #rmcmd = """rm -rf %s %s_Obj.csv %s_std.csv %s_match.csv""" % (MergedFile, myfile, myfile, myfile
    #rmcmd = """rm -rf %s_Obj.csv %s_std.csv %s_match.csv""" % (myfile, myfile, myfile)
    #print 'rmcmd = '+rmcmd
    #os.system(rmcmd)
    #os.system('rm -rf *_sextractor_psf.fits_Obj.csv')
    #os.system('rm -rf *_sextractor_psf.fits_std.csv')
    #os.system('rm -rf *_sextractor_psf.fits_match.csv')
    #os.system('rm -rf *_red_catlist.csv')




##################################
# Get 3sigma clipped Zero point and iterater
##################################

def sigmaClipZPallCCDs(args):
    import pandas as pd
    import numpy as np
    import sys,os,glob,math,string
    import astropy 
    from astropy.stats import sigma_clip
    from numpy import mean
    import numpy.ma as ma 

    if args.verbose >0 : print args

    allZPout="""allZP_D%08d_r%sp%02d.csv""" % (args.expnum,args.reqnum,args.attnum)
    stdfile="""STDD%08d_r%sp%02d_red_catlist.csv""" % (args.expnum,args.reqnum,args.attnum)
    objfile="""ObjD%08d_r%sp%02d_red_catlist.csv""" % (args.expnum,args.reqnum,args.attnum)
    outfile="""OUTD%08d_r%sp%02d_red_catlist.csv""" % (args.expnum,args.reqnum,args.attnum)
    stddf = pd.read_csv(stdfile).sort(['RA'], ascending=True)
    #read  file and sort and save 
    stddf.to_csv(stdfile,sep=',',index=False)
    path='./'
    all_files = glob.glob(os.path.join(path, "*Obj.csv"))     
    df = pd.concat((pd.read_csv(f) for f in all_files)).sort(['RA'], ascending=True)

    #read all file and sort and save 
    df.to_csv(objfile,sep=',',index=False)

    stdracol=1; stddeccol=2
    obsracol=1 ; obsdeccol=2 
    matchTolArcsec=1.0 #1.0arcsec 
    verbose=2
    matchSortedStdwithObsCats(stdfile,objfile,outfile,stdracol,stddeccol,obsracol,obsdeccol,matchTolArcsec,verbose)

    if not os.path.isfile(outfile):
	print '%s does not seem to exist... exiting now...' % outfile
	sys.exit(1)
    try:
	data11=np.genfromtxt(outfile,dtype=None,delimiter=',',names=True)
        #New CUTS
	w0=(data11['MAG_2']-data11['WAVG_MAG_PSF_1']-25.0) < -10
	w1=(data11['MAG_2']-data11['WAVG_MAG_PSF_1']-25.0) > -40
	data=data11[ w0 & w1 ]

        # Identify band...      It is now BAND_2!!
	bandList = data['BAND_2'].tolist()
	band = bandList[0].upper()

	WAVG_MAG_PSF_1       =data['WAVG_MAG_PSF_1']
	MAG_2                =data['MAG_2']
	delt_mag_data        =MAG_2 -WAVG_MAG_PSF_1 -25.0
	filtered_data        =sigma_clip(delt_mag_data, 3, 3, np.mean, copy=True)
	NumStarsClipped      =(filtered_data).count()
	NumStarsAll          =len(filtered_data)

	if  NumStarsClipped >2:
		sigclipZP=np.mean(filtered_data)
		stdsigclipzp=np.std(filtered_data)/math.sqrt(NumStarsClipped)
	else:
		sigclipZP=-999
		stdsigclipzp=-999
    except:
	sigclipZP      =-999
	stdsigclipzp   =-999
	NumStarsClipped=0
	NumStarsAll    =0

    hdr="EXPNUM,REQNUM,ATTNUM,NumStarsAll,NumStarsClipped,sigclipZP,stdsigclipzp\n"    
    line = """%d,%s,%d,%d,%d,%f,%f""" % (args.expnum,args.reqnum,args.attnum, NumStarsAll,NumStarsClipped,sigclipZP,stdsigclipzp)
    print line
    fout=open(allZPout,'w')
    fout.write(hdr)
    fout.write(line+'\n')





##################################

if __name__ == "__main__":
    main()

##################################
