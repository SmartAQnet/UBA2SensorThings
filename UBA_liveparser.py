#!/usr/bin/env python
# coding: utf-8

import requests, json
from datetime import datetime
import pandas as pd
import hashlib


# function that takes two lists of same length and makes a dict of them, identifying element i with element i
def stitch_to_dict(a,b):
    r={}
    for i in range(len(a)):
        r[a[i]]=b[i]
    return r

# everything lowercase, replaces slashes and spaces with underscores, ...
def idstr(idinput):
    """returns strings in the conventional format for iot.ids"""
    return (str(idinput).lower().replace(" ", "_").replace("/", "_").replace(
        "ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss"))

# returns the first 7 digits of the sha1 hash of the input string
def hashfunc(inputstring):
    return hashlib.sha1(bytes(str(inputstring), 'utf-8')).hexdigest()[0:7]

# returns the full 40 digits of the sha1 hash of the input string
def hashfuncfull(inputstring):
    return hashlib.sha1(bytes(str(inputstring), 'utf-8')).hexdigest()

# UBA has phenomenonTimes end with hour 24 instead of 0 the next day. datetime cant deal with that, have to replace
def todatetimeUTCstring(string):
    if(string[-8:-6] == '24'):
        res=pd.to_datetime(string.replace(" 24:"," 23:"))+pd.Timedelta('1 hour')
    else: 
        res=pd.to_datetime(string)
    return (res - pd.Timedelta('1 hour')).strftime("%Y-%m-%d" + "T" + "%H" + ":00:00.000Z")





url = "https://api.smartaq.net/v1.0"

uba_stations = json.loads(requests.get(url + "/Things?$filter=properties/operator.domain%20eq%20%27umweltbundesamt.de%27&$expand=datastreams($expand=sensor,observedProperty)").text)["value"]

current_component = "1" #PM10
current_scope = "2" #hourly averages

for thing in uba_stations:
    station_no = thing["properties"]["station_no"]
    current_thing_idparts = thing["properties"]["operator.domain"] + ":" + thing["properties"]["shortname"] + ":" + thing["properties"]["hardware.id"]
    
    for stream in thing["Datastreams"]:
        current_sensor_idparts = stream["Sensor"]["properties"]["manufacturer.domain"] + ":" + stream["Sensor"]["properties"]["shortname"]
        current_datastream_idparts = current_thing_idparts + ":" + current_sensor_idparts + ":" + stream["properties"]["hardware.serial_number"] + ":" + stream["ObservedProperty"]["properties"]["shortname"]
        
        timestamp_from = stream["phenomenonTime"].split("/")[1]
        
        start_date=timestamp_from.split("T")[0]
        start_result_time=str(int(timestamp_from.split("T")[1].split(":")[0]) + 1)
        end_date=datetime.strftime(datetime.now(),"%Y-%m-%d")
        end_result_time=datetime.strftime(datetime.now(),"%H")

        data=json.loads(requests.get("https://www.umweltbundesamt.de/api/air_data/v2/measures/json?date_from=" + start_date + "&time_from=" + start_result_time + "&date_to=" + end_date + "&time_to=" + end_result_time + "&station=" + str(station_no) + "&component=" + current_component + "&scope=" + current_scope).text)

        val_index=data["indices"]["data"]["station id"]["date start"].index("value")
        end_index=data["indices"]["data"]["station id"]["date start"].index("date end")

        #function todatetimeUTCstring converts to pandas datetime, converts CET to UTC, then outputs ISO string
        list_of_results=list(map(lambda x: {"result":data['data'][str(station_no)][x][val_index],"resultTime":todatetimeUTCstring(data['data'][str(station_no)][x][end_index]) ,"phenomenonTime": todatetimeUTCstring(x) + "/" + todatetimeUTCstring(data['data'][str(station_no)][x][end_index])},data['data'][str(station_no)].keys()))
        
        totalobs = len(list_of_results)

        for thisresult in list_of_results:
            thisobs = thisresult
            thisobs["@iot.id"] = "saqn:o:" + hashfuncfull(current_datastream_idparts + ":" + idstr(thisresult["phenomenonTime"]))
            p = requests.post(url + "/Datastreams('" + stream["@iot.id"]  + "')/Observations",json.dumps(thisobs))        

