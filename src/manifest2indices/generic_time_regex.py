import gzip
import pickle
import re
from datetime import datetime
import os

errorfiles = []
errorcount = 0
icount = 0

def older_parse_filename_for_starttime(filename,pattern=None,prefix=''):
    """ best guess parser of CDAWeb filenames into an ISO time of
    YYYY-MM-DDTHH:MM:SSZ
    """
    if pattern == None:
        pattern = re.compile(r"^(.*?)_+"+prefix+"(\d{4})(\d{2})(\d{2})(\d{2})?(\d{2})?(\d{2})?.*")
    match = pattern.search(filename)
    date = match.groups()[1] + '-' + match.groups()[2] + '-' + match.groups()[3] + 'T'
    hour, minute, sec = '00', '00', '00'
    if match.groups()[4] != None: hour=match.groups()[4]
    if match.groups()[5] != None: minute=match.groups()[5]
    if match.groups()[6] != None: second=match.groups()[6]
    date += hour + ':' + minute + ':' + sec
    #if count > 7: date += '.' + match.groups()[7]
    date += 'Z'
    return date

def parse_filename_for_starttime(filename,pattern=None,prefix=''):
    """ best guess parser of CDAWeb filenames into an ISO time of
    YYYY-MM-DDTHH:MM:SSZ
    """
    if pattern == None:
        pattern = re.compile(r"^(.*?)_+"+prefix+"(\d{4})(\d{2})(\d{2})(\d{2})?(\d{2})?(\d{2})?.*")
    match = pattern.search(filename)
    results = list(match.groups())
    results = [x for x in results if x is not None]
    for i in range(4): results.append('00') # zero pad
    if len(results[2]) == 3:
        doy = True
    else:
        doy = False
    if doy:
        date = '-'.join(results[1:6])
        date = datetime.strptime(date,"%Y-%j-%H-%M-%S").strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        date = '-'.join(results[1:7])
        date = datetime.strptime(date,"%Y-%m-%d-%H-%M-%S").strftime("%Y-%m-%dT%H:%M:%SZ")
    return date

with gzip.open('filelist.gz','rt') as fin:
    """ This pattern set and order is deliberate. We do not want a single regex
    that can match them all, because some patterns are dangerous, for example
    matching YYYYDOY (d{7}) will false-match early for YYYYMMDD, which is also more
    common.
    Fails to match (for CDAWeb) ~4000 pub/data/de/de1/particles_eics files, ~4200 cdaweblib/0MASTERS,
    and ~240 misc files in 35 other categories.
    """
    #pattern1 = re.compile(r"^(.*?)_(\d{4})(\d{2})(\d{2})(\d{2})?(\d{2})?(\d{2})?.*")
    pattern2 = re.compile(r"^(.*?)_[d]?(\d{4})(\d{2})(\d{2})[Tt]?(\d{2})?(\d{2})?(\d{2})?(\d{3})?[_-].*")
    #pattern3 = re.compile(r"^(.*?)/(\d{4})-(\d{2})/(\d{2}).*")
    pattern4 = re.compile(r"^[d]?(\d{4})(\d{2})(\d{2})[Tt]?(\d{2})?(\d{2})?(\d{2})?[_-].*")
    ypattern1 = re.compile(r"^(.*?)[_-](\d{4})[_-](\d{3})_(\d{2})?[_]?(\d{2})?.*")
    ypattern2 = re.compile(r"^(.*?)_(\d{4})(\d{3})[Tt](\d{2})(\d{2})(\d{2}).*")
    #ypattern3 = re.compile(r"^(.*?)[_/](\d{4})(\d{3})[_t\.].*")
    ypattern4 = re.compile(r"^(.*?)_(\d{4})(\d{3})[Tt]?(\d{2})?(\d{2})?(\d{2})?[_-].*")
    ypattern5 = re.compile(r"^(\d{4})(\d{3})[Tt]?(\d{2})?(\d{2})?(\d{2})?[_-].*")
    #pattern4 = re.compile(r"^(.*?)/(\d{4})(\d{2})(\d{2})\..*")
    #patternset = [pattern2, pattern3, ypattern1, ypattern2, ypattern3, ypattern4, pattern4] # fullnames matches all but 5K, filename matches all but 16K
    patternset = [pattern2, pattern4, ypattern1, ypattern2, ypattern4, ypattern5]
    printfirst_warn = True
    for line in fin:
        if line.endswith(".cdf\n") or line.endswith(".nc\n"):
            lineset = line.rstrip().split()
            filename = lineset[-1]
            filename = os.path.basename(filename)
            timestamp = None
            for pattern in patternset:
                try:
                    timestamp = parse_filename_for_starttime(filename, pattern)
                    printfirst_warn = True
                    break
                except:
                    pass
            if timestamp == None:
                if printfirst_warn: print("Error extracting time from: ",filename)
                printfirst_warn = False
                errorcount += 1
                errorfiles.append(filename)
            icount += 1
            if icount % 500000 == 1: print("Up to file",icount)

print(f"There were {errorcount} parsing time problems")
if errorcount > 0:
    with open("errorfiles.pkl","wb") as fout:
        pickle.dump(errorfiles,fout)
    print("Stored filenames in errorfiles.pkl")


