def read(filename, headline, startline, delim=' '):
    linenum = 0
    go = 0
    column_list = []
    return_cols = {}
    inf = open(filename)
    for line in inf:
        print line
        line = line.replace('#', '')
        line = line.strip()
        cols = line.split(delim)
        cols[:] = (value for value in cols if value != '')
        if linenum == headline - 1:
            for col in cols:
                return_cols[col.strip()] = []
                column_list.append(col.strip())
                go += 1
        if linenum >= startline - 1:
            index = 0
            for col in cols:
                try:
                    return_cols[column_list[index]].append(float(col.strip()))
                except:
                    return_cols[column_list[index]].append(col.strip())
                index += 1
        linenum += 1
    inf.close()
    return return_cols