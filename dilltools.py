def read(filename, headline, startline, delim=' '):
    linenum = 0
    go = 0
    column_list = []
    return_cols = {}
    inf = open(filename)
    for line in inf:
        #print line
        line = line.replace('#', '')
        line = line.strip()
        cols = line.split(delim)
        cols[:] = (value for value in cols if value != '')
        if linenum == headline - 1:
            colnums = len(cols)
            for col in cols:
                return_cols[col.strip()] = []
                column_list.append(col.strip())
                go += 1
        if linenum >= startline - 1:
            index = 0
            for col in cols:
                if index < colnums:
                    try:
                        return_cols[column_list[index]].append(float(col.strip()))
                    except:
                        return_cols[column_list[index]].append(col.strip())
                index += 1
        linenum += 1
    inf.close()
    return return_cols

def mjd_to_datetime(mjd):
    mjd_epoch = datetime.datetime(1858, 11, 17, tzinfo=pytz.utc)
    d = mjd_epoch + datetime.timedelta(mjd)
    return d

def sendEmailSubject(trigger_id,subject):
    import smtplib
    from email.mime.text import MIMEText

    text = subject
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