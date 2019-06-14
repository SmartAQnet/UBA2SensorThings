#!/usr/bin/env python
# coding: utf-8

# # 1. Initialisations

# In[1]:


import requests, json
import pandas as pd
import requests, json
import calendar
from datetime import datetime
import hashlib


# In[2]:


#from datetime to unixtime
def tounixtime(datetime_input):
    return(calendar.timegm(datetime_input.utctimetuple()))

# returns strings in the conventional format for iot.ids
def idstr(idinput):
    return(str(idinput).lower().replace(" ", "_").replace("/", "_").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss"))

# returns the first 7 digits of the sha1 hash of the input string
def hashfunc(inputstring, printme):
    returnhash= hashlib.sha1(bytes(str(inputstring), 'utf-8')).hexdigest()[0:7]
    if printme == True:
        print("Converting '" + str(inputstring) + "' to hash '" + str(returnhash) +"'")
    return(returnhash)

# returns the full 40 digits of the sha1 hash of the input string
def hashfuncfull(inputstring, printme):
    returnhash= hashlib.sha1(bytes(str(inputstring), 'utf-8')).hexdigest()
    if printme == True:
        print("Converting '" + str(inputstring) + "' to hash '" + str(returnhash) +"'")
    return(returnhash)


# In[3]:


baseurl = 'https://www.umweltbundesamt.de/js/uaq/data/stations' #get data where from: umweltbundesamt
url = "http://api.smartaq.net/v1.0" #post data where to: saqn frost server

scope='1SMW' #umweltbundesamt website code: 1 hour means
scopesec= 60*60 #scope in seconds, needed for interval to tag the next observation

feature='PM10' #umweltbundesamt observedProperty code
obsproperty_code = "mcpm10" #frost server observedProperty code


# # 2. Program

# - get all existing UBA stations from frost server 
# - get the latest observation date
# - get the next observation from UBA server
# - post to frost

# In[ ]:


#alle things von lfu.bayern.de
number_of_things=json.loads(requests.get(url + "/Things?$filter=properties/operator_url%20eq%20%27lfu.bayern.de%27&$select=@iot.id&$count=True").text)["@iot.count"]
listofthings=json.loads(requests.get(url + "/Things?$filter=properties/operator_url%20eq%20%27lfu.bayern.de%27&$top=" + str(number_of_things)).text)["value"]

#for each thing...
for thing in listofthings:
    print(thing["name"])
    
    #...identify the datastream iot.id corresponding to the observedproperty (pm10)...
    try:
        pm10streamid=json.loads(requests.get(url + "/Things('" + thing["@iot.id"] + "')/Datastreams?$filter=ObservedProperty/@iot.id%20eq%20%27saqn:op:" + obsproperty_code + "%27&$select=@iot.id").text)["value"][0]["@iot.id"]
        print("Datastream found: " + str(pm10streamid))
    except:
        print("no datastream existing for thing " + thing["name"] + " with observedProperty " + obsproperty_code)
        print("____________________________________________________")
        continue
    
    #... and get the datastream url
    datastream=json.loads(requests.get("https://api.smartaq.net/v1.0/Datastreams('" + pm10streamid + "')").text)

    
    #then find the latest observation
    try:
        end_latest_pheno_time = json.loads(requests.get("https://api.smartaq.net/v1.0/Datastreams('" + pm10streamid + "')/Observations?$orderby=phenomenontime%20desc&$top=1").text)["value"][0]["phenomenonTime"][-24:]
        print("latest phenomenon time found: " + str(end_latest_pheno_time))
    except: 
        print("no data available on datastream " + pm10streamid)
        print("____________________________________________________")
        continue
    print(end_latest_pheno_time)
    #if a new observation is due, get it
    try:
        while (pd.datetime.now() - pd.to_datetime(end_latest_pheno_time)).total_seconds() > scopesec + 10:
            
            begintimeunix=tounixtime(pd.to_datetime(end_latest_pheno_time))
            endtimeunix=tounixtime(pd.to_datetime(end_latest_pheno_time)) + scopesec

            #get data from uba
            getdatafrom=baseurl + '/measuring?pollutant[]=' + feature + '&scope[]=' + scope + '&station[]=' + thing["properties"]["station_code"] + '&group[]=pollutant&range[]=' + str(begintimeunix+10) + ',' + str(endtimeunix+10)
            datavalue=json.loads(requests.get(getdatafrom).text)["data"][0][0][0]





            #get the unhashed datastream id
            #thing id           
            thing_id_url = thing["properties"]["operator_url"]
            thing_id_thingname = str(thing["name"])
            thing_id_date = str(thing["properties"]["station_start_date"])[0:4] + "-" + str(thing["properties"]["station_start_date"])[4:6]
            thing_id_thingnumber = str(thing["properties"]["station_code"])
            thing_tohash = idstr(thing_id_url + ":" + thing_id_thingname + ":" + thing_id_date + ":" + thing_id_thingnumber)

            #Datastream ID
            stream_id_url = datastream["properties"]["operator_url"] #sollte eigentlich auch in den properties des datastreams stehen
            stream_id_sensorname = datastream["properties"]["sensor_name"]
            stream_id_sensornumber = datastream["properties"]["sensor_serial_number"]
            stream_tohash = idstr(stream_id_url + ":" + stream_id_sensorname + ":" + stream_id_sensornumber)

            fullstream_tohash = thing_tohash + ":" + stream_tohash + ":" + obsproperty_code

#             #check function if idgeneration was correct
#             if "saqn:ds:" + hashfunc(fullstream_tohash,False) == pm10streamid:
#                 print("hash checksum true")
#             else:
#                 print("stream id not correct: ")
#                 print("    " + pm10streamid + " != " + "saqn:ds:" + hashfunc(fullstream_tohash,False))
#                 print("    " + "tried to hash " + fullstream_tohash)



            #generate observation and push to frost
            observation_id_prefix = "saqn:o:"
            observation_interval = end_latest_pheno_time + "/" + "PT1H"
            observation_tohash = idstr(fullstream_tohash + ":" + observation_interval)
            generateobsid = observation_id_prefix + hashfuncfull(observation_tohash, False)

            observation = {
            "phenomenonTime" : observation_interval, 
            "result" : datavalue,
            "Datastream":{"@iot.id": str(pm10streamid)},
            "@iot.id": generateobsid
            }
            requests.post(url +  "/Datastreams('" + pm10streamid + "')/Observations", json.dumps(observation))
            print("Successfully posted an Observation")
            print("____________________________________________________")
            
                #then find the latest observation
            try:
                end_latest_pheno_time = json.loads(requests.get("https://api.smartaq.net/v1.0/Datastreams('" + pm10streamid + "')/Observations?$orderby=phenomenontime%20desc&$top=1").text)["value"][0]["phenomenonTime"][-24:]
                print("latest phenomenon time found: " + str(end_latest_pheno_time))
            except: 
                print("no data available on datastream " + pm10streamid)
                print("____________________________________________________")
                continue

    except:
        print("some error")
        print("____________________________________________________")
        continue

