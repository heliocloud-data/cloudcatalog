import csv

def getrealyear(id,year):
    fname = f"s3/spdf/cdaweb/data/mms/indices/{id}_{year}.csv"
    with open(fname) as fin:
        l1 = fin.readline()
        l2 = fin.readline()
        start = l2.split(',')[0]
        return start

fname = "mms_indices.txt"
cname = "catalog_updates.csv"
cnew = "catalog_updates2.csv"

window = {}
with open(fname) as fin:
    for line in fin:
        stems = line.split("_")
        year = stems[-1].split(".csv")[0]
        tag = "_".join(stems[0:-1])
        if tag in window:
            window[tag].append(year)
        else:
            window[tag] = [year]

tally = 0
goodtally = 0
csvout = ["id,start,stop,index,modification\n"]
with open(cname) as cin:
    reader = csv.DictReader(cin)
    for row in reader:
        tally += 1
        tag = row.get("id")
        start = row.get("start")
        stop = row.get("stop")
        startyear = start[0:4]
        stopyear = stop[0:4]
        if tag in window and startyear in window[tag] and stopyear in window[tag]:
            pass
        else:
            print(tag,startyear,stopyear)
            print(window[tag])

        realstartyear = window[tag][0]
        realstopyear = window[tag][-1]
        if realstartyear == startyear and realstopyear == stopyear:
            start = row.get('start')
        else:
            print(f"{tag}, says {startyear}-{stopyear} but indices exist for {realstartyear}-{realstopyear}")
            start = getrealyear(tag,realstartyear)
            
        line = f"{row.get('id')},{start},{row.get('stop')},{row.get('index')},{row.get('modification')}\n"
        csvout.append(line)

with open(cnew,"w") as fout:
    fout.writelines(csvout)
        
print(f"{goodtally} good out of {tally}")

