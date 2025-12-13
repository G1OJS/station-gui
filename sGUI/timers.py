import time

def tnow():
    return time.time()

def tnow_str(offset_secs = 0):
    return time.strftime("%H%M%S", time.gmtime(tnow()+offset_secs))

def QSO_dnow_tnow():
    t = time.gmtime(tnow())
    return time.strftime("%Y%m%d",t), time.strftime("%H%M%S", t)

def strftime(fmt,t):
    return time.strftime(fmt, time.gmtime(t))
    
def sleep(secs):
    if(secs>0):
        time.sleep(secs)

def timestamp_bundle():
    """Return all forms of time once so all logs stay consistent."""
    t = time.time()
    return {
        "t": t,                        
        "t_fmt": time.strftime("%H%M%S")     
    }

def timedLog(msg, silent=False, logfile=None):
    ts = timestamp_bundle()
    if not silent:
        print(f"{ts['t_fmt']} {msg}")
    if logfile:
        with open(logfile, 'a') as f:
            f.write(f"{ts['t']} {ts['t_fmt']} {msg}\n")

logs_opened=[]
def timedLogCSV(stats_dict, filename):
    global logs_opened
    ts = timestamp_bundle()
    row_dict = {
        "cycle_str": ts["cycle_str"],
        "t_elapsed": round(ts["t_elapsed"], 3),
        "unix_ts":   round(ts["t"], 3),
        **stats_dict
    }
    
    if(not filename in logs_opened):
        with open(filename, 'w') as f:
            f.write(','.join(row_dict.keys()) + "\n")
        logs_opened.append(filename)
        
    with open(filename, 'a') as f:
        f.write(','.join(str(v) for v in row_dict.values()) + "\n")

