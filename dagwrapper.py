import os
import subprocess
import time
import easyaccess as ea
#propid = "'2012B-0001'" # des
propid = "'2015B-0187'" # desgw

DATABASE = 'desoper' #read only
#DATABASE = 'destest' #We can write here

class jobmanajer:
    def __init__(self,trigger_id):
        self.connection = ea.connect(DATABASE)
        self.cursor = connection.cursor()

        dire = './processing/'+trigger_id+'/'
        if not os.path.exists(dire):
            os.makedirs(dire)

file_firedlist = open('firedlist.txt','w')
file_firedlist.close()

file_firedlist = open('firedlist.txt','r')
firedlist = file_firedlist.readlines()
file_firedlist.close()
firedlist = map(str.strip, firedlist)
#print firedlist

q1 = "select expnum,nite,mjd_obs,telra,teldec,band,exptime,propid,obstype,object from exposure where nite>20130828 and nite<20150101 and expnum<300000 and obstype='object' order by expnum" # y1 images
connection.query_and_save(q1,'exposuresY1.tab') 

q2 = "select expnum,nite,mjd_obs,radeg,decdeg,band,exptime,propid,obstype,object from prod.exposure where nite>20150901 and obstype='object' order by expnum" # y2 and later 
connection.query_and_save(q2,'exposuresCurrent.tab') 

os.system('cat exposuresY1.tab exposuresCurrent.tab > exposures.list')

starttime = time.time()
keepgoing = True
index = -1
submission_counter = 0
maxsub = 1
while keepgoing:
    index += 1
    newfireds = []
    if time.time() - starttime > 50000:
        keepgoing = False
        continue

    ofile = open(dire+'latestquery.txt','w')
    
    ofile.write("--------------------------------------------------------------------------------------------------\n")
    ofile.write("EXPNUM\tNITE\tBAND\tEXPTIME\tTELRA\t TELDEC\tPROPID\tOBJECT\n")
    ofile.write("--------------------------------------------------------------------------------------------------\n")
    
    print "--------------------------------------------------------------------------------------------------"
    print "EXPNUM\tNITE\tBAND\tEXPTIME\tTELRA\t TELDEC\tPROPID\tOBJECT"
    print "--------------------------------------------------------------------------------------------------"
    
    query = "SELECT expnum,nite,band,exptime,telra,teldec,propid,object FROM prod.exposure@desoper WHERE expnum > 475900 and propid="+propid+"and obstype='object'" # latest
    
    cursor.execute(query)

    
    for s in cursor:
        ofile.write(str(s[0])+"\t"+str(s[1])+"\t"+str(s[2])+"\t"+str(s[3])+"\t"+str(s[4])+"\t"+str(s[5])+"\t"+str(s[6])+"\t"+str(s[7])+'\n')
        print str(s[0])+"\t"+str(s[1])+"\t"+str(s[2])+"\t"+str(s[3])+"\t"+str(s[4])+"\t"+str(s[5])+"\t"+str(s[6])+"\t"+str(s[7]) 

        expnum = str(s[0])
        nite = str(s[1])
        band = str(s[2])
        if not expnum in firedlist:
            #print expnum
            try:
                if submission_counter < maxsub:
                    subprocess.call(["sh", "DAGMaker.sh", '00'+expnum]) #create dag
                    print 'created dag for '+str(expnum)
                    subprocess.call(["sh", "jobsub_submit_dag -G des --role=DESGW file:./desgw_pipeline_00"+expnum+".dag"]) #submit to the grid
                    print 'submitting to grid'
                    subprocess.call(["./RUN_DIFFIMG_PIPELINE_LOCAL.sh","-E "+nite+" -b "+band+" -n "+nite]) #submit local
                    print 'SUBMITTED JOB FOR EXPOSURE: 00'+expnum
                    newfireds.append(expnum)
                    submission_counter += 1
            except:
                'SUBMISSION FAILED'
            
    #write newfireds to file
    ofile.close()
    file_firedlist = open('firedlist.txt','a')
    for f in newfireds:
        print 'New Fired: '+str(f)
        file_firedlist.write(str(f)+'\n')
    file_firedlist.close()
    sys.exit()
    time.sleep(120)
    
