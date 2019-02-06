#!/usr/bin/env python
# coding: utf-8

# In[2]:


import requests, json
import pandas as pd
import numpy as np
import calendar
from datetime import datetime
import time
import sys
import glob


# In[9]:


#input parameters. Read config.txt

try:
    configfile=open('config.txt')
    config=json.loads(configfile.read())

    url = config['url']
    thingcode = config['thingcode']
    feature = config['feature']
    intervalllength = config['intervalllength']
except:
    sys.exit("Config File not properly set!")


#manual coding----------------------
#feature='PM10' #the feature needs to be added in the list of replacements with its corresponding code
#thingcode='DEBY006' #stationID
#url = 'http://smartaqnet-dev.teco.edu:8080/FROST-Server/v1.0' #post where to
#intervalllength = 'PT1H'


# In[50]:


#read data and auxiliary functions

#get the component code for a feature as long as it is listed in the listofreplacements
def componentcode(feat):
    for rep in listofreplacements:
        if rep[0]==feature:
            return(rep[1])


#get the first file matching thingcode and feature e.g. DEBY007_PM10_*.xlsx
filename = glob.glob("data/" + str(thingcode) + "*" + str(feature) + "*.xlsx")[0]
print("Loading file " + str(filename) + "...")
datafile=pd.read_excel(str(filename),0)
datafilemeta=pd.read_excel(str(filename),'id')

#clear all nullresults (False) before the first measurement
nullresults=0
for i in range(len(list(datafile["interval_start_time"]))):
    if datafile[feature][i]==0:
        nullresults+=1
    else:
        break

#read file again but skip the nullresults
datafile=pd.read_excel(str(filename),skiprows=range(1,nullresults+1))
        
#for displaying the elapsed time
starttime=time.time()

#------------------------------------------------------------------------------------
#functions for time conversion
def readtime(sec):
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    return(str(int(h)) + " hours " + str(int(m)) + " minutes " + str(int(s)) + " seconds")

def tounixtime(datetime_input):
    return(calendar.timegm(datetime_input.utctimetuple()))

def todatetimeformat(utctime):
    year=int(utctime[0])*1000 + int(utctime[1])*100 + int(utctime[2])*10 + int(utctime[3])
    month=int(utctime[5])*10 + int(utctime[6])
    day=int(utctime[8])*10 + int(utctime[9])
    hr=int(utctime[11])*10 + int(utctime[12])
    minute=int(utctime[14])*10 + int(utctime[15])
    second=int(utctime[17])*10 + int(utctime[18])
    millisecond=int(utctime[20])*100 + int(utctime[21])*10 + int(utctime[22])   
    return(datetime(year,month,day,hr,minute,second,millisecond))

def toutcformat(datetime_input):
    tstr=str(datetime_input)
    year=tstr[0]+tstr[1]+tstr[2]+tstr[3]
    month=tstr[5]+tstr[6]
    day=tstr[8]+tstr[9]
    
    try:
        if type(int(tstr[11]+tstr[12]))==int:
            hour=str(tstr[11]+tstr[12])
    except:
        hour='00'             #no hours given       
    
    try:
        if type(int(tstr[14]+tstr[15]))==int:
            minute=str(tstr[14]+tstr[15])
    except:
        minute='00'             #no minutes given

    try:
        if type(int(tstr[17]+tstr[18]))==int:
            second=str(tstr[17]+tstr[18])
    except:
        second='00'             #no seconds given
        
    try:
        if type(int(tstr[20]+tstr[21]+tstr[22]))==int:
            millisecond=str(tstr[20]+tstr[21]+tstr[22])
    except:
        millisecond='000'       #no milliseconds given


        
    utctime=year + '-' + month + '-' + day + 'T' + hour + ':' + minute + ':' + second + '.' + millisecond + 'Z'
    return utctime    

currentyear=str(datetime.utcnow())[0:4]


# In[51]:



#get datastream id
#datastreamID="saqn:d:" + str(repnetcodebyurl(file["network_code"][thingnr])) + ":" + str(list(df_stationparameters["measurement_start_date"][thingcode])[sensnr])[0:6] + ":" + thingcode + ":" + feature.replace(" ", "_")
datastreamID=datafilemeta["datastreamID"][0]


print("Uploading Observations for Datastream iot.id: " + datastreamID)

#------------------------------------------------------------------------------------


for i in range(len(list(datafile["interval_start_time"]))): #eleganter ist hier feature zu nehmen aber ist egal
    #phenotime = toutcformat(datetime.utcfromtimestamp(tounixtime(begin)+scopesec*i))
    
    generateobsid="saqn:obs:" + str(datastreamID)[7:] + ":" + str(datafile["interval_start_time"][i]) + "/" + str(intervalllength)
    
    observation = {
    "phenomenonTime" : str(datafile["interval_start_time"][i]) + "/" + str(intervalllength), 
    "result" : float(datafile[str(feature)][i]),
    "Datastream":{"@iot.id": str(datastreamID)},
    "@iot.id": str(generateobsid).lower().replace(" ", "_").replace("/", "_")
    }

    requests.post(url + '/Observations', json.dumps(observation))

    #estimating time remaining for parsing
    timeelapsed=time.time()-starttime
    timeelapsedread=readtime(((len(list(datafile["interval_start_time"]))/(i+1))-1)*int(timeelapsed+1))
    sys.stdout.write('Uploaded ' + str(i) + ' out of ' + str(len(list(datafile["interval_start_time"]))) + ' Observations. Estimating ' + timeelapsedread + ' remaining \r')


endtime=time.time()
timeelapsed=endtime-starttime
    
sys.stdout.write('Finshed! Successfully uploaded ' + str(len(list(datafile["interval_start_time"]))) + ' Observations in ' + str(readtime(int(timeelapsed))) + ' seconds. \r')


# In[12]:


#requests.delete(url + "/Datastreams('saqn:d:lfu.bayern.de:200002:deby006:pm10')")
#requests.delete(url + "/Datastreams('saqn:d:lfu.bayern.de:201412:deby007:particulate_matter_-_pm10,_first_measurement')")
#requests.delete(url + "/Datastreams('saqn:d:lfu.bayern.de:200008:deby099:particulate_matter_-_pm10,_first_measurement')")
#requests.delete(url + "/Datastreams('saqn:d:lfu.bayern.de:200308:deby110:particulate_matter_-_pm10,_first_measurement')")
#requests.delete(url + "/Things")
#requests.delete(url + "/Sensors")
#requests.delete(url + "/Locations")
#requests.delete(url + "/ObservedProperties")
#requests.delete(url + "/FeaturesOfInterest")
#requests.delete(url + "/Datastreams")
#requests.delete(url + "/Observations")


# In[ ]:




