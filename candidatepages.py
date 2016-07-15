import os
import numpy as np

import datetime
import pytz
from copy import copy

'''
Usage:

import candidatepages
candidatepages.makeNewPage( candidate_paramfile = 'cpf.npz' )

candidate_paramfile must have the following
    #TABLE 1
    band = cand_params['band'] #this is a numpy array
    x = cand_params['x']#this is a numpy array
    y = cand_params['y']#this is a numpy array
    mag = cand_params['mag']#this is a numpy array
    nite = cand_params['nite']#this is a numpy array
    mjd = cand_params['mjd']#this is a numpy array
    season = cand_params['season']#this is a numpy array
    expnum = cand_params['expnum']#this is a numpy array
    ccdnum = cand_params['ccdnum']#this is a numpy array

    #TABLE 2
    search = cand_params['search']#this is a numpy array
    template = cand_params['template']#this is a numpy array
    diff = cand_params['diff']#this is a numpy array
    mlscore = cand_params['mlscore']#this is a numpy array
    diffmjd = cand_params['diffmjd']#this is a numpy array
    diffband = cand_params['diffband']#this is a numpy array

    candidate_id = cand_params['candid']
    trigger_id = cand_params['trigger_id']
    field = cand_params['field']
    ra = cand_params['ra']
    dec = cand_params['dec']
    lcplot = cand_params['lcplot']
    peakmlscore = cand_params['peakmlscore']#i may be calculating this


'''
def makeNewPage(candidate_paramfile):

    try:
        cand_params = np.load(candidate_paramfile)
    except:
        print 'could not find candidate param file'
        return

    print cand_params
    print cand_params.keys()
    band = cand_params['band'] #this is a numpy array
    xs = cand_params['x']#this is a numpy array
    ys = cand_params['y']#this is a numpy array
    #mag = cand_params['mag']#this is a numpy array
    mag = cand_params['x']*0-9
    nite = cand_params['nite']#this is a numpy array
    mjd = cand_params['mjd']#this is a numpy array
    season = cand_params['season']#this is a numpy array
    expnum = cand_params['expnum']#this is a numpy array
    ccdnum = cand_params['ccdnum']#this is a numpy array

    #TABLE 2
    search = cand_params['search']#this is a numpy array
    template = cand_params['template']#this is a numpy array
    diff = cand_params['diff']#this is a numpy array


    mlscore = cand_params['photprob']#this is a numpy array
    obsid = cand_params['thisobs_ID']
    diffmjd = cand_params['diffmjd']#this is a numpy array
    diffband = cand_params['diffband']#this is a numpy array

    candidate_id = cand_params['candid']
    trigger_id = cand_params['trigger_id']
    field = cand_params['field']
    ra = cand_params['ra']
    dec = cand_params['dec']
    lcplot = cand_params['lcplot']
    peakmlscore = np.max(mlscore)

    #MAKE A DIRECTORY FOR THE CANDIDATE PAGE AND FILES
    outdir = 'DES_GW_Website/Candidates/'
    outfile = outdir+'DES'+str(candidate_id)+'.html'
    outimages = 'DES_GW_Website/Candidates/'+str(candidate_id)+'/images/'

    trigger_cand_dir = 'DES_GW_Website/Triggers/'+str(trigger_id)+'/candidate_param_files/'
    trigger_cand_file = 'DES_GW_Website/Triggers/'+str(trigger_id)+'/candidate_param_files/'+str(candidate_id)+'.npz'
    if not os.path.exists(trigger_cand_dir):
        os.mkdir(trigger_cand_dir)

    print outfile
    print outimages
    print trigger_cand_file

    np.savez(trigger_cand_file,
             id=str(candidate_id),
             ra=str(round(float(ra),3)),
             dec=str(round(float(dec),3)),
             mlscore=str(round(float(peakmlscore),2)),
             peakmag=str(round(np.max(np.float(mag)),2)),
             peakmjd=str(round(float(mjd[np.argmax(np.float(mag))]),2))
             )


    if not os.path.exists(outdir):
        os.mkdir(outdir)

    if not os.path.exists(outimages):
        os.mkdir(outimages)

    os.system('cp '+lcplot+' '+outimages+'lightcurve.png')
    searchs = copy(search)
    templates = copy(template)
    diffs = copy(diff)


    for i,s,t,d in zip(range(len(search)),search,template,diff):

        sout = s.split('/')[-1]
        searchs[i] = sout
        if s is None:
            s = 'DES_GW_Website/image_placeholder.png'
        os.system('cp '+s+' '+outimages+sout)
        tout = t.split('/')[-1]
        templates[i] = tout
        if t is None:
            t = 'DES_GW_Website/image_placeholder.png'
        os.system('cp '+t+' '+outimages+tout)
        dout = d.split('/')[-1]
        diffs[i] = dout
        if d is None:
            d = 'DES_GW_Website/image_placeholder.png'
        os.system('cp '+d+' '+outimages+dout)

    search = searchs
    template = template
    diff = diffs

    print search
    raw_input()
    html = '\<!DOCTYPE html> \
        <html lang="en" style="height:100%;">\
        <head> \
        <meta charset="utf-8"> \
        <title>DES Candidate '+str(candidate_id)+'</title>\
        <meta name="viewport" content="width=device-width, initial-scale=1.0"> \
        <meta name="keywords" content="pinegrow, blocks, bootstrap" />\
        <meta name="description" content="My new website" />\
        <link rel="shortcut icon" href="ico/favicon.png"> \
        <!-- Core CSS -->\
        <link href="bootstrap/css/bootstrap.min.css" rel="stylesheet"> \
        <link href="css/font-awesome.min.css" rel="stylesheet">\
        <link href="http://fonts.googleapis.com/css?family=Open+Sans:300italic,400italic,600italic,700italic,400,300,600,700" rel="stylesheet">\
        <link href="http://fonts.googleapis.com/css?family=Lato:300,400,700,300italic,400italic,700italic" rel="stylesheet">\
        <!-- Style Library -->\
        <link href="css/style-library-1.css" rel="stylesheet">\
        <link href="css/plugins.css" rel="stylesheet">\
        <link href="css/blocks.css" rel="stylesheet">\
        <link href="css/custom.css" rel="stylesheet">\
        <!-- HTML5 shim, for IE6-8 support of HTML5 elements. All other JS at the end of file. -->\
           <!--[if lt IE 9]>\
      <script src="js/html5shiv.js"></script>\
      <script src="js/respond.min.js"></script>\
    <![endif]-->\
        <script type="text/javascript">\
    function ChangeColor(tableRow, highLight)\
    {\
    if (highLight)\
    {\
      tableRow.style.backgroundColor = "#7FFFD4";\
    }\
    else\
    {\
      tableRow.style.backgroundColor = "white";\
    }\
  }\
  function DoNav(theUrl)\
  {\
  document.location.href = theUrl;\
  }\
  </script>\
    </head>\
    <body data-spy="scroll" data-target="nav" style="PADDING-TOP: 80px">\
        <header id="header-2" class="soft-scroll header-2">\
            <script type="text/javascript" src="http://ajax.googleapis.com/ajax/libs/jquery/1.7.1/jquery.min.js"></script>\
            <script type="text/javascript" src="js/smoothscroll.js"></script>\
            <nav class="main-nav navbar navbar-default navbar-fixed-top">\
                <div class="container">\
                    <!-- Brand and toggle get grouped for better mobile display -->\
                    <div class="navbar-header">\
                        <a href="http://des-ops.fnal.gov:8080/desgw/index.html">\
                            <button type="button" class="btn btn-default">Home</button>\
                        </a>\
                        <button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target="#navbar-collapse">\
                            <span class="sr-only">Toggle navigation</span>\
                            <span class="icon-bar"></span>\
                            <span class="icon-bar"></span>\
                            <span class="icon-bar"></span>\
                        </button>\
                        <a href="#"></a>\
                    </div>\
                    <!-- Collect the nav links, forms, and other content for toggling -->\
                    <div class="collapse navbar-collapse" id="navbar-collapse">\
                        <ul class="nav navbar-nav navbar-right">\
                            <li class="nav-item active">\
                                <a href="#DES" class="smoothScroll">DES '+str(candidate_id)+'</a>\
                            </li>\
                            <li class="nav-item">\
                                <a href="#Data" class="smoothScroll">Info</a>\
                            </li>\
                            <li class="nav-item">\
                                <a href="#Lightcurve" class="smoothScroll">Lightcurve</a>\
                            </li>\
                            <li class="nav-item">\
                                <a href="#Stamps" class="smoothScroll">Stamps</a>\
                            </li>\
                            <li class="nav-item">\
                                <a href="http://des-ops.fnal.gov:8080/desgw/Triggers/'+str(trigger_id)+'/'+str(trigger_id)+'_trigger.html">Trigger '+str(trigger_id)+'</a>\
                            </li>\
                        </ul>\
                    </div>\
                    <!-- /.navbar-collapse -->\
                </div>\
                <!-- /.container-fluid -->\
            </nav>\
        </header>\
        <section id="promo-3" class="content-block promo-3 min-height-600px bg-deepocean">\
            <div class="container text-center">\
                <h1><a name="DES" style="padding-top: 105px;">DES CANDIDATE '+str(candidate_id)+'</a></h1>\
                <h2><a href="#" style="color: white">LIGO Trigger '+str(round(trigger_id))+'</a></h2>\
                <a href="#" class="btn btn-outline btn-outline-xl outline-light">Prev</a>\
                <a href="#" class="btn btn-outline btn-outline-xl outline-light">Next</a>\
            </div>\
            <!-- /.container -->\
        </section>\
        <section class="content-block gallery-1 gallery-1-1">\
            <h1><a name="Data" style="padding-top: 105px;">Candidate Info</a></h1>\
            <table class="table">\
                <thead>\
                    <tr> \
                        <th></th> \
                        <th></th> \
                        <th></th> \
                        <th></th>\
                    </tr>\
                </thead><tbody><tr onmouseover="ChangeColor(this, true);" onmouseout="ChangeColor(this, false);">\
                        <th></th>\
                        <td></td>\
                        <td>Candidate ID</td>\
                        <td>'+str(candidate_id)+'</td>\
                    </tr>\
                    <tr onmouseover="ChangeColor(this, true);" onmouseout="ChangeColor(this, false);">\
                        <th></th>\
                        <td></td>\
                        <td>RA</td>\
                        <td>'+str(ra)+'</td>\
                    </tr>\
                    <tr onmouseover="ChangeColor(this, true);" onmouseout="ChangeColor(this, false);">\
                        <th></th>\
                        <td></td>\
                        <td>DEC</td>\
                        <td>'+str(dec)+'</td> \
                    </tr>\
                    <tr onmouseover="ChangeColor(this, true);" onmouseout="ChangeColor(this, false);">\
                        <th></th>\
                        <td></td>\
                        <td>Field</td>\
                        <td>'+str(field)+'</td> \
                    </tr>\
                </tbody>\
            </table>\
            <div class="content-block contact-3">\
                <h1><a name="Lightcurve" style="padding-top: 105px;">Lightcurve</a></h1>\
                <div class="container">\
                    <div class="row">\
                        <div class="col-md-6">\
                            <div id="contact" class="form-container">\
                                <table class="table"> \
                                    <thead> \
                                        <tr> \
                                            <th>Band</th>\
                                            <th>x</th> \
                                            <th>y</th> \
                                            <th>Mag</th>\
                                            <th>Nite</th> \
                                            <th>MJD</th>\
                                            <th>Season</th>\
                                            <th>ExpNum</th>\
                                            <th>CCDNum</th>\
                                        </tr>\
                                    </thead>\
                                    <tbody>'
    lightcurvedata = ''
    for b,x,y,m,n,mj,s,e,c in zip(band,xs,ys,mag,nite,mjd,season,expnum,ccdnum):
        lightcurvedata += '<tr onmouseover="ChangeColor(this, true);" onmouseout="ChangeColor(this, false);"> \
                                            <td>'+str(b)+'</td> \
                                            <td>'+str(x)+'</td> \
                                            <td>'+str(y)+'</td> \
                                            <td>'+str(m)+'</td> \
                                            <td>'+str(n)+'</td> \
                                            <td>.'+str(mj)+'</td>\
                                            <td>'+str(s)+'</td> \
                                            <td>'+str(e)+'</td> \
                                            <td>.'+str(c)+'</td> \
                                        </tr>'
    html += lightcurvedata
    html += '</tbody>\
                                </table>\
                                <div id="message"></div>\
                                <form method="post" action="js/contact-form.php" name="contactform" id="contactform">\
                                    <div class="form-group">\
                                    </div>\
                                    <div class="form-group">\
                                    </div>\
                                    <div class="form-group">\
                                    </div>\
                                    <div class="form-group">\
                                        <div class="editContent">\
                                    </div>\
                                    </div>\
                                    <div class="form-group">\
                                    </div>\
                                </form>\
                            </div>\
                            <!-- /.form-container -->\
                        </div>\
                        <div class="col-md-6">\
                            <div class="container">\
                                <!-- /.gallery-filter -->\
                                <div class="row">\
                                    <div class="isotope-gallery-container">\
                                        <div class="col-md-6 gallery-item-wrapper artwork creative">\
                                            <div class="gallery-item">\
                                                <div class="gallery-thumb">\
                                                    <img src="http://des-ops.fnal.gov:8080/desgw/Candidates/'+str(candidate_id)+'/images/lightcurve.png" class="img-responsive" alt="1st gallery Thumb">\
                                                    <div class="image-overlay"></div>\
                                                    <a href="http://des-ops.fnal.gov:8080/desgw/Candidates/'+str(candidate_id)+'/images/lightcurve.png" class="gallery-zoom"><i class="fa fa-eye" alt="This is the title"></i></a>\
                                                    <a href="http://des-ops.fnal.gov:8080/desgw/Candidates/'+str(candidate_id)+'/images/lightcurve.png" download class="gallery-link" target="_blank"><i class="fa fa-link"></i></a>\
                                                </div>\
                                                <div class="gallery-details">\
                                            </div>\
                                            </div>\
                                        </div>\
                                    </div>\
                                </div>\
                            </div>\
                        </div>\
                    </div>\
                    <!-- /.row -->\
                </div>\
                <!-- /.container -->\
            </div>\
            <h1><a name="Stamps" style="padding-top: 105px;">Stamps</a></h1>\
            <div class="container">\
                <!-- /.gallery-filter -->\
                <div class="row">\
                    <div class="isotope-gallery-container">'

    stampgallery = ''
    for s,t,d,ml,mjd,b,o in zip(search,template,diff,mlscore,diffmjd,diffband,obsid):
        stampgallery += '<div class="col-md-4 col-sm-4 col-xs-4 gallery-item-wrapper artwork creative">\
                            <div class="gallery-item">\
                                <div class="gallery-thumb">\
                                    <img src="http://des-ops.fnal.gov:8080/desgw/Candidates/'+str(candidate_id)+'/images/'+s+'" class="img-responsive" alt="1st gallery Thumb">\
                                    <div class="image-overlay"></div>\
                                    <a href="http://des-ops.fnal.gov:8080/desgw/Candidates/'+str(candidate_id)+'/images/'+s+'" class="gallery-zoom"><i class="fa fa-eye" alt="This is the title"></i></a>\
                                    <a href="http://des-ops.fnal.gov:8080/desgw/Candidates/'+str(candidate_id)+'/images/'+s+'" download class="gallery-link" target="_blank"><i class="fa fa-link"></i></a>\
                                </div>\
                                <h4>MJD '+str(mjd)+', OBSID '+str(o)+'</h4>\
                                <h5>'+b+' - SEARCH</h5>\
                            </div>\
                        </div>\
                        <div class="col-md-4 col-sm-4 col-xs-4 gallery-item-wrapper artwork creative">\
                            <div class="gallery-item">\
                                <div class="gallery-thumb">\
                                    <img src="http://des-ops.fnal.gov:8080/desgw/Candidates/'+str(candidate_id)+'/images/'+t+'" class="img-responsive" alt="1st gallery Thumb">\
                                    <div class="image-overlay"></div>\
                                    <a href="http://des-ops.fnal.gov:8080/desgw/Candidates/'+str(candidate_id)+'/images/'+t+'" class="gallery-zoom"><i class="fa fa-eye" alt="This is the title"></i></a>\
                                    <a href="http://des-ops.fnal.gov:8080/desgw/Candidates/'+str(candidate_id)+'/images/'+t+'" download class="gallery-link" target="_blank"><i class="fa fa-link"></i></a>\
                                </div>\
                                <h4>MJD '+str(mjd)+', OBSID '+str(o)+'</h4>\
                                <h5>'+b+' - TEMPLATE</h5>\
                            </div>\
                        </div>\
                        <div class="col-md-4 col-sm-4 col-xs-4 gallery-item-wrapper artwork creative">\
                            <div class="gallery-item">\
                                <div class="gallery-thumb">\
                                    <img src="http://des-ops.fnal.gov:8080/desgw/Candidates/'+str(candidate_id)+'/images/'+d+'" class="img-responsive" alt="1st gallery Thumb">\
                                    <div class="image-overlay"></div>\
                                    <a href="http://des-ops.fnal.gov:8080/desgw/Candidates/'+str(candidate_id)+'/images/'+d+'" class="gallery-zoom"><i class="fa fa-eye" alt="This is the title"></i></a>\
                                    <a href="http://des-ops.fnal.gov:8080/desgw/Candidates/'+str(candidate_id)+'/images/'+d+'" download class="gallery-link" target="_blank"><i class="fa fa-link"></i></a>\
                                </div>\
                                <h4>MJD '+str(mjd)+', OBSID '+str(o)+'</h4>\
                                <h5>'+b+' - DIFF MLScore '+str(round(ml,2))+'</h5>\
                            </div>\
                        </div>'
    html += stampgallery
    html += '<!-- /.gallery-item-wrapper -->\
                        <!-- /.gallery-item-wrapper -->\
                        <!-- /.gallery-item-wrapper -->\
                        <!-- /.gallery-item-wrapper -->\
                        <!-- /.gallery-item-wrapper -->\
                        <!-- /.gallery-item-wrapper -->\
                        <!-- /.gallery-item-wrapper -->\
                    </div>\
                    <!-- /.isotope-gallery-container -->\
                </div>\
                <!-- /.row -->\
            </div>\
            <!-- /.container -->\
        </section>\
        <h1></h1>\
        <script type="text/javascript" src="js/jquery-1.11.1.min.js"></script>\
        <script type="text/javascript" src="js/bootstrap.min.js"></script>\
        <script type="text/javascript" src="js/plugins.js"></script>\
        <script src="https://maps.google.com/maps/api/js?sensor=true"></script>\
        <script type="text/javascript" src="js/bskit-scripts.js"></script>\
    </body>\
</html>'



    a = open(outfile, 'w')
    a.write(html)
    a.close()

    print outfile,'CREATED SUCCESSFULLY'

def updateWebpage(self):
    os.system('kinit -k -t /var/keytab/desgw.keytab desgw/des/des41.fnal.gov@FNAL.GOV')
    os.system('scp -r DES_GW_Website/* codemanager@desweb.fnal.gov:/des_web/www/html/desgw/')
    return


def mjd_to_datetime(mjd):
    mjd_epoch = datetime.datetime(1858, 11, 17, tzinfo=pytz.utc)
    d = mjd_epoch + datetime.timedelta(mjd)
    return d



if __name__ == '__main__':
    makeNewPage('/data/des41.a/data/desgw/gw_mi/test-triggers/M189424/candidates/101902.0.npz')
    pass