
# coding: utf-8

# # 1. Initialisations
# ## 1.1. Import Libraries

# In[2]:


import requests, json
import pandas as pd
from pandas import ExcelWriter
from pandas import ExcelFile
import sys
import time
import requests, json
import numpy as np
import calendar
from datetime import datetime
import random
import glob
import hashlib
#import easygui
import os
import shutil


# ## 1.2. Read Metadata Files

# In[3]:


destinationurl = "http://smartaqnet-dev.teco.edu/v1.0"

file = pd.read_excel('metadata/Bericht_EU_Meta_Stationen.xlsx')
filemeta=pd.read_excel('metadata/Bericht_EU_Meta_Stationsparameter.xlsx')
df_stationparameters = filemeta.set_index("station_code")

#list of features with their component codes as appears in 'metadata/Bericht_EU_Meta_Stationsparameter.xlsx'
listofreplacements=[
    ('PM10','5.0','mcpm10'),
    ('PM2,5','6001.0','mcpm2p5'),
    ('PM1','6002.0','mcpm1'),
]

#federal state, network code (as appears in 'metadata/Bericht_EU_Meta_Stationen.xlsx'), operator-url
ccodesetreadable=[('Hessen', 'DE009A','hlnug.de'),
 ('Saarland', 'DE001A','saarland.de'),
 ('Berlin', 'DE008A','berlin.de'),
 ('Bayern', 'DE007A','lfu.bayern.de'),
 ('Rheinland-Pfalz', 'DE011A','luft.rlp.de'),
 ('Sachsen', 'DE016A','umwelt.sachsen.de'),
 ('Umweltbundesamt', 'DE006A','umweltbundesamt.de'),
 ('Baden-Wuerttemberg', 'DE005A','lubw.baden-wuerttemberg.de'),
 ('Nordrhein-Westfalen', 'DE004A','lanuv.nrw.de'),
 ('Brandenburg', 'DE014A','lfu.brandenburg.de'),
 ('Bremen', 'DE013A','bauumwelt.bremen.de'),
 ('Mecklenburg-Vorpommern', 'DE018A','lung.mv-regierung.de'),
 ('Hamburg', 'DE012A','luft.hamburg.de'),
 ('Thueringen', 'DE017A','tlug-jena.de'),
 ('Schleswig-Holstein', 'DE002A','schleswig-holstein.de'),
 ('Sachsen-Anhalt', 'DE015A','luesa.sachsen-anhalt.de'),
 ('Niedersachsen', 'DE010A','umwelt.niedersachsen.de')]


#returns the url for the network code
def repnetcodebyurl(netcode):
    for item in ccodesetreadable:
        if item[1]==netcode:
            return(item[2])

#returns the name of the state for the network code
def repnetcodebystate(netcode):
    for item in ccodesetreadable:
        if item[1]==netcode:
            return(item[0])


# ## 1.3. General Function Definitions

# In[4]:


#converts numpy types to python types, otherwise json conversion produces an error. call json.dumps(***, cls=MyEncoder)
class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(MyEncoder, self).default(obj)

        

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


def addminutesutc(utctime,mins):
    return(toutcformat(datetime.utcfromtimestamp(tounixtime(todatetimeformat(utctime))+(mins*60))))


# # 2. Function generatemetadata() 
# ## - models the Database from the Metadata Files
# ## - gets the Observations from UBA url and saves them into an excel file
# ## - If upload set to true will execute parseexcel() to upload the Observations

# In[5]:




#------------------------------------------------------------------------------------
#function that builds the metadata


def generatemetadata():

    #input values. Read config.txt

    try:
        with open('config.txt') as configfile:
            config=json.loads(configfile.read())

            url = config['url']
            thingcode = config['thingcode']
            feature = config['feature']
        #    intervalllength = config['intervalllength']
            if config["runparseaftermodelling"] == True:
                upload == True #set to True/False to enable/disable upload of metadata to FROST
    except:
        sys.exit("Config File not properly set!")

    baseurl = 'https://www.umweltbundesamt.de/js/uaq/data/stations' #get data where from
    scope='1SMW' #umweltbundesamt website code: 1 hour means
    scopesec= 60*60 #scope in seconds, needed for interval to tag the next observation

    print("Upload is set to " + str(upload))
    print("Extracting Observations for ObservedProperty " + str(feature))

    #fetches the code for the 'feature' defined in listofreplacements
    for eachelement in listofreplacements:
        if eachelement[0] == feature:
            code = eachelement[1]
            op_id_variable = eachelement[2]

    
    
    
    #print for human crosscheck
    print('Check: Going to uploading data for station ' + str(thingcode) + ' at ' + str(file.set_index("station_code")["station_name"][thingcode]))

    #metadata
    totalstarttime = time.time() #to check how long the upload took
    
    #observed property --> should already be "officially" created!
    op_tohash = idstr(op_id_variable)
#    generatepropertyid = "saqn:op:" + hashfunc(op_tohash, True)
    generatepropertyid = "saqn:op:" + op_tohash

    if requests.head(url +  "/ObservedProperties" + "('" + generatepropertyid + "')").status_code == 200:
        print(generatepropertyid + " exists.")
    else:
#        print(generatepropertyid + " does NOT exist. Will generate dummy that needs to be patched. Upload is " + str(upload))
#        obsproperty = {
#            "name": str(feature),
#            "description": str(feature),
#            "definition": "",
#            "@iot.id": generatepropertyid
#            }
#        if upload==True:
#            requests.post(url + '/ObservedProperties', json.dumps(obsproperty))
#        else:
#            pass
        sys.exit("Observed Property " + str(feature) + " with id " + generatepropertyid + " does not exist! Abort.")

    #-----------------------------------------------------------------------------
    thingnr=list(file["station_code"]).index(thingcode) #the number of the row in the excel file

    generatedescr="" #generates the description for the thing
    if  df_stationparameters["type_of_parameter"].index.contains(thingcode): #checks whether the station actually exists
        if thingcode in df_stationparameters["type_of_parameter"][thingcode]: #if the stations measures only one type of parameter, the index is not returned somehow and the loop produces an error, therefore check if the index is returned and if not handle case separately
            for element in list(set(df_stationparameters["type_of_parameter"][thingcode])):
                generatedescr+= " -" + element + "-"
        else: #if the station only measures one type of parameter (loop produces an error in that case, thus handled separately)
            generatedescr+= " -" + df_stationparameters["type_of_parameter"][thingcode] + "-"

    #------------------------------------------------------------------------------------------------
    #building things

    #Location ID
    loc_id_prefix = "geo:" 
    loc_id_lat = str(float(file["station_latitude_d"][thingnr]))
    loc_id_lon = str(float(file["station_longitude_d"][thingnr]))
    loc_id_alt = str(float(file["station_altitude"][thingnr]))
    
    loc_tohash = idstr(loc_id_lat + "," + loc_id_lon + "," + loc_id_alt)
    
    generatelocid = loc_id_prefix + loc_tohash #hashfunc(loc_tohash, True)

    #Thing ID
    thing_id_prefix = "saqn:t:"
    thing_id_url = str(repnetcodebyurl(file["network_code"][thingnr]))
    thing_id_thingname = "Station " + str(file["station_name"][thingnr])
    thing_id_date = str(file["station_start_date"][thingnr])[0:4] + "-" + str(file["station_start_date"][thingnr])[4:6]
    thing_id_thingnumber = str(file["station_code"][thingnr])
    
    thing_tohash = idstr(thing_id_url + ":" + thing_id_thingname + ":" + thing_id_date + ":" + thing_id_thingnumber)
    
    generatethingid = thing_id_prefix + hashfunc(thing_tohash, True)

    #generates a dictionary of all raw properties of the thing
    rawproperties = {}
    for eachproperty in list(file):
        if str(file[eachproperty][thingnr])=='nan':
            rawproperties[eachproperty]='nan'
        else:
            rawproperties[eachproperty] = file[eachproperty][thingnr]
    rawproperties["operator_url"] = thing_id_url

    #generate the thing JSON
    thingdata = {"name": thing_id_thingname,
        "description": "A station measuring" + str(generatedescr),
        "properties": rawproperties,
        "@iot.id": idstr(generatethingid),
         "Locations": [{
            "name": "Location at latitude " + loc_id_lat + " and longitude " + loc_id_lon,
            "description": "located at " + str(file["station_name"][thingnr]),
            "encodingType": "application/vnd.geo+json",
            "@iot.id": idstr(generatelocid),
            "location": {
                  "type": "Point",
                  "coordinates": [float(file["station_longitude_d"][thingnr]), float(file["station_latitude_d"][thingnr]), float(file["station_altitude"][thingnr])]
            }

          }]
    }
    if upload==True:
        requests.post(url + '/Things', json.dumps(thingdata, cls=MyEncoder))
    else:
        pass



    #loop over all sensors and check which contains the requested observedproperty
    try:
        if float(code) not in list(df_stationparameters["component_code"][thingcode]):
            print("Station " + str(thingcode) + " does not measure " + str(feature))
        else:
            for sensnr in range(len(list(df_stationparameters["component_code"][thingcode]))):
                if list(df_stationparameters["component_code"][thingcode])[sensnr] == float(code):
                    thissensor=list(df_stationparameters["parameter"][thingcode])[sensnr] #the parameter to parse, e.g. "Particulate Matter - PM10, first measurement"
                    mestech=list(df_stationparameters["measurement_technique_principle"][thingcode])[sensnr]
                    #warning: if only one sensor exists, this will blow up because one item is not returned as dataframe but as string

                    #------------------------------------------------------------------------------------------------
                    #building the sensors


                    #Sensor ID
                    sensor_id_prefix = "saqn:s:"
                    sensor_id_url = str(repnetcodebyurl(file["network_code"][thingnr]))
                    sensor_id_name = "generic " + str(list(df_stationparameters["measurement_technique_principle"][thingcode])[sensnr]) + " sensor"
                    
                    sensor_tohash = idstr(sensor_id_url + ":" + sensor_id_name)
                    
                    generatesensorid = sensor_id_prefix + hashfunc(sensor_tohash, True)


                    #generate sensor JSON
                    sensor = {"name": sensor_id_name,
                            "description": "A sensor measuring " + str(feature) + " using " + str(mestech),
                            "properties": {"operator_url": sensor_id_url},
                            "encodingType": "",
                            "metadata": "",
                            "@iot.id": idstr(generatesensorid)
                            }
                    if upload==True:
                        requests.post(url + '/Sensors', json.dumps(sensor, cls=MyEncoder))
                    else:
                        pass

                    #------------------------------------------------------------------------------------------------
                    #building the datastreams
                    
                    #Datastream ID
                    stream_id_prefix = "saqn:ds:"
                    stream_id_url = str(repnetcodebyurl(file["network_code"][thingnr]))
                    stream_id_sensorname = sensor_id_name
                    stream_id_sensornumber = ""
                    
                    stream_tohash = idstr(stream_id_url + ":" + stream_id_sensorname + ":" + stream_id_sensornumber)
                    fullstream_tohash = thing_tohash + ":" + stream_tohash + ":" + op_tohash
                    
                    generatestreamid = stream_id_prefix + hashfunc(fullstream_tohash, True)
     
                    #generates a dictionary of all raw properties of the thing to dump into metadata property
                    uploadmetadata = {}
#                    uploadmetadata["script version number"]="1.0"
#                    uploadmetadata["uploaded data from"]=configuration["starttime"]
#                    uploadmetadata["uploaded data until"]=configuration["endtime"]
                    
                    rawmetadata = {}
#                    rawmetadata["station_code"]=thingcode
                    rawmetadata["operator_url"]=stream_id_url
                    rawmetadata["upload properties"]=uploadmetadata
                    
                    
                    for eachdata in list(df_stationparameters): #option 1: all metadata
                    #for eachdata in ["type_of_parameter","parameter","component_code","measurement_technique_principle"]: #option 2: pick
                        if str(list(df_stationparameters[eachdata][thingcode])[sensnr]) == 'nan':
                            rawmetadata[eachdata]='nan'
                        else:
                            rawmetadata[eachdata] = list(df_stationparameters[eachdata][thingcode])[sensnr]

                    
                    
                    
                   
                    
                    
                    print("Building Datastream " + idstr(generatestreamid))

                    datastream = {"name": str(thissensor) + " Datastream of station " + str(thingcode),
                                "description": "A Datastream measuring " + str(thissensor) + " using " + str(mestech),
                                "observationType": "http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_Measurement",
                                "unitOfMeasurement": {
                                    "name": "microgram per cubic meter",
                                    "symbol": "ug/m^3",
                                    "definition": "http://www.qudt.org/qudt/owl/1.0.0/unit/Instances.html#KilogramPerCubicMeter"
                                    },
                                "properties": rawmetadata,
                                "@iot.id": idstr(generatestreamid),
                                "Thing":{"@iot.id":idstr(generatethingid)},
                                "Sensor":{"@iot.id":idstr(generatesensorid)},
                                "ObservedProperty":{"@iot.id":idstr(generatepropertyid)}
                                }

                    if upload==True:
                        requests.post(url + '/Datastreams', json.dumps(datastream))
                    else:
                        pass

                    #END OF METADATA - - - BEGIN OF DATA UPLOAD
                    #------------------------------------------------------------

                    def graburl(start,end): #start and end in datetime
                        return(baseurl + '/measuring?pollutant[]=' + feature + '&scope[]=' + scope + '&station[]=' + thingcode + '&group[]=pollutant&range[]=' + str(tounixtime(start)) + ',' + str(tounixtime(end)))

                    #begin time
                    try:
                        begintime=todatetimeformat(config['starttime'])
                    except:

                        #get the start month of the respective datastream

                        def getstarttime():
                            sys.stdout.write("Searching Datastream Start Time")
                            for i in range(1970,2018+1): #ranges to 2018, the +1 is because how range counts
                                try:
                                    theurl=graburl(datetime(i,1,1,0,0,0),datetime(i,12,31,23,59,0))
                                    datafromurl=json.loads(requests.get(theurl).content)["data"][0]
                                    if datafromurl[0][0]!='bananas': #anything but an error
                                        for j in range(1,12+1):
                                            try:
                                                theurl2=graburl(datetime(i,j,1,0,0,0),datetime(i,j,calendar.monthrange(i,j)[1],23,59,0))
                                                datafromurl2=json.loads(requests.get(theurl2).content)["data"][0]
                                                if datafromurl2[0][0]!='bananas':
                                                    for k in range(1,calendar.monthrange(i,j)[1]+1):
                                                        try:
                                                            theurl3=graburl(datetime(i,j,k,0,0,0),datetime(i,j,k,23,59,0))
                                                            datafromurl3=json.loads(requests.get(theurl3).content)["data"][0]
                                                            if datafromurl3[0][0]!='bananas':
                                                                return(datetime(i,j,k,0,0,0))
                                                                break
                                                        except:
                                                            pass
                                            except:
                                                pass
                                except:
                                    sys.stdout.write(".")
                                    pass

                        begintime=getstarttime()

                        print("")
                        print("Parsing start time not properly set. Taking earliest date measurements appear: " + str(begintime))

                    #end time
                    try:
                        endtime=todatetimeformat(config['endtime'])
                    except:
                        print("Parsing end time not properly set. Taking " + str(datetime.utcnow()))
                        endtime = datetime.utcnow() 


                    #------------------------------------------------------------

                    try:
                        begintimeunix=tounixtime(begintime)
                        endtimeunix=tounixtime(endtime)
                    except:
                        print("Error! Datatstream empty! Cannot find any data!")
                        return()

                    print('Measurements of ' + str(thingcode) + ' ' +  str(thissensor) + ' are being parsed from ' + str(begintime))


                    getdatafrom=baseurl + '/measuring?pollutant[]=' + feature + '&scope[]=' + scope + '&station[]=' + thingcode + '&group[]=pollutant&range[]=' + str(begintimeunix + (scopesec/2)) + ',' + str(endtimeunix  + (scopesec/2))
                    datavalue=json.loads(requests.get(getdatafrom).content)["data"][0]


                    #convert list into a dataframe
                    datalist=[]
                    labels=['interval_start_time','interval_end_time',str(feature)]

                    for i in range(len(datavalue)):
                            datalist.append([toutcformat(datetime.utcfromtimestamp(begintimeunix + (scopesec*i))),toutcformat(datetime.utcfromtimestamp(begintimeunix + ((scopesec*i) + (scopesec-60)) )),datavalue[i][0]])

                    dataframe = pd.DataFrame.from_records(datalist, columns=labels)
                    dataframemeta = pd.DataFrame.from_records([[idstr(generatestreamid)],[fullstream_tohash]], columns=['datastreamID'])

                    
                    #if already a file exists for that datastream and feature move it into archive before creating new
                    try: #get the first file matching thingcode and feature e.g. DEBY007_PM10_*.xlsx
                        data_dir=str(os.getcwd()) + "/data/"
                                                
                        existing_file = glob.glob(data_dir + str(thingcode) + "*" + str(feature) + "*.xlsx")[0]
                        print("File for that datastream and observedProperty already exists. ")
                        existing_file_new = str(existing_file)[:-5] + "---" + str(toutcformat(datetime.utcnow()))[:-5].replace(":","-") + ".xlsx"
                        print("Renaming file " + existing_file + " to " + existing_file_new)
                        os.rename(existing_file, data_dir +'/archive/' + str(existing_file_new)[len(data_dir):])
                        print("Moving file into archive folder")
                    except:
                        pass
                    
                    #save dataframe to excel sheet
                    filename= str(thingcode) + "_" + str(thissensor) + "_" + str(toutcformat(begintime)[0:10]) + "_" + str(toutcformat(endtime)[0:10]) + ".xlsx"
                    writer = ExcelWriter('data/' +  str(filename))
                    dataframe.to_excel(writer,'Sheet1',index=False)
                    dataframemeta.to_excel(writer,'id',index=False)
                    writer.save()

                    #crosschecking: checks a number of random points between the dataframe and the url

                    #the UBA database gives the result for the hour that has PASSED, e.g. the value at 5 o'clock is the mean between 4 and 5 o'clock
                    #the code writes a value for the interval between e.g. 3:00 and 3:59. for this interval, the UBA value at 3:30 is taken. 
                    #therefore the check also needs to add 30m to the url to check with the corresponding start time

                    numberoftests=10
                    testistrue=False


                    for i in range(0,10):
                        r = random.randint(1,len(list(dataframe["interval_start_time"])))
                        getdatapoint=graburl(todatetimeformat(addminutesutc(dataframe["interval_start_time"][r],30)),todatetimeformat(addminutesutc(dataframe["interval_end_time"][r],30)))
                        checkdatavalue=json.loads(requests.get(getdatapoint).content)["data"][0][0][0]
                        if dataframe[feature][r] == checkdatavalue:
                            testistrue=True
                        else:
                            print(str(dataframe[feature][r]) + "!=" + str(checkdatavalue))
                            testistrue=False

                    print("Crosscheck for " + str(thingcode) + " " + str(thissensor) + " with " + str(numberoftests) + " random datapoints gave result " + str(testistrue))


        endtime=time.time()
        timeelapsed=endtime-totalstarttime

        print("Time elapsed: " + str(readtime(timeelapsed)))

        if upload==True:
            parseexcel()

    except:
        print("Could not retrieve any data for station " + str(thingcode))
    return()

    


# # 3. Function parseexcel() parses the Observation File

# In[6]:


#------------------------------------------------------------------------------------
#function parses the data file



def parseexcel():
    #input parameters. Read config.txt

    try:
        with open('config.txt') as configfile:
            config=json.loads(configfile.read())

            url = config['url']
            thingcode = config['thingcode']
            feature = config['feature']
            intervalllength = config['intervalllength']
    except:
        sys.exit("Config File not properly set!")


    #read data and auxiliary functions

    #get the component code for a feature as long as it is listed in the listofreplacements
    def componentcode(feat):
        for rep in listofreplacements:
            if rep[0]==feature:
                return(rep[1])


     


     
            
            
    try: #get the first file matching thingcode and feature e.g. DEBY007_PM10_*.xlsx
        filename = glob.glob("data/" + str(thingcode) + "*" + str(feature) + "*.xlsx")[0]
    except:
        print("No file to parse found that matches the requirements")
        pass
    
#    filename_path = easygui.fileopenbox(msg=None, title=None, default='Data/' + str(thingcode) + '*' + str(feature) + '*.xlsx', filetypes=None, multiple=False)
#    filename= filename_path.split("\\")[-1]
    
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


    #get datastream id
    datastreamID=datafilemeta["datastreamID"][0]
    fullstream_tohash=datafilemeta["datastreamID"][1]

    print("Uploading Observations for Datastream iot.id: " + datastreamID)

    #------------------------------------------------------------------------------------

    for i in range(len(list(datafile["interval_start_time"]))): #eleganter ist hier feature zu nehmen aber ist egal

        observation_id_prefix = "saqn:o:"
        observation_interval = str(datafile["interval_start_time"][i]) + "/" + str(intervalllength)

        observation_tohash = idstr(fullstream_tohash + ":" + observation_interval)

        generateobsid = observation_id_prefix + hashfuncfull(observation_tohash, False)

        observation = {
        "phenomenonTime" : observation_interval, 
        "result" : float(datafile[str(feature)][i]),
        "Datastream":{"@iot.id": str(datastreamID)},
        "@iot.id": generateobsid
        }

        requests.post(url + '/Observations', json.dumps(observation))

        #estimating time remaining for parsing
        timeelapsed=time.time()-starttime
        timeelapsedread=readtime(((len(list(datafile["interval_start_time"]))/(i+1))-1)*int(timeelapsed+1))
        sys.stdout.write('Uploaded ' + str(i) + ' out of ' + str(len(list(datafile["interval_start_time"]))) + ' Observations. Estimating ' + timeelapsedread + ' remaining \r') 


    endtime=time.time()
    timeelapsed=endtime-starttime
    
    sys.stdout.write('\n' + '__________________________________________________________________________' + '\n')
    sys.stdout.write('Finshed! Successfully uploaded ' + str(len(list(datafile["interval_start_time"]))) + ' Observations in ' + str(readtime(int(timeelapsed))) + ' seconds. \r')


# # 4. User Input determines which stations to parse

# In[ ]:


#file = pd.read_excel('metadata/Bericht_EU_Meta_Stationen.xlsx')
listofstations=list(file["station_code"])
userinput = input("Please enter UBA Station to parse: ")

parselist=[]
#for station in listofstations:
#    if userinput in station:
#        parselist.append(station)
                         
if isinstance(userinput,list) is True: #if the user gives an array of station codes, take that
    parselist=userinput
else: 
    for nr in range(len(file)): #else perform a substring search in all informations on the stations
        the_dict=file.iloc[[str(nr)]].to_dict(orient="index")[nr]
        for key in the_dict:
            if userinput in str(the_dict[key]):
                parselist.append(the_dict["station_code"])

print("Will parse the following stations: ")
print(parselist)


print("If you do not input a start time, the earliest date a measurement appears will be taken. ")
starttimeyesno = input("Input start time (yes/no) : ")

if starttimeyesno == "yes":
    yr = input("Enter start time year : ")
    mth = input("Enter start time month : ")
    day = input("Enter start time day : ")
    hr = input("Enter start time hour : ")
    mts = input("Enter start time minutes : ")
    starttime = yr + "-" + mth + "-" + day + "T" + hr + ":" + mts + ":00.000Z"
    starttimestring = starttime
else:
    starttime = False
    starttimestring = "the first measurement"


print("If you do not input an end time, 'right now' will be taken. ")
endtimeyesno = input("Input end time (yes/no) : ")

if endtimeyesno == "yes":
    yr = input("Enter end time year : ")
    mth = input("Enter end time month : ")
    day = input("Enter end time day : ")
    hr = input("Enter end time hour : ")
    mts = input("Enter end time minutes : ")
    endtime = yr + "-" + mth + "-" + day + "T" + hr + ":" + mts + ":00.000Z"
    endtimestring = endtime
else:
    endtime = False
    endtimestring = "now"

uploadyesno = input("Upload data to server after writing to file (yes/no): ")
if uploadyesno == "yes":
    upload=True
    uploadstring = "Data will be uploaded"
else:
    upload=False
    uploadstring = "Data will not be uploaded"
    
    
print("Parsing " + str(len(parselist)) + " Stations: " + str(parselist) + " in the time between " + str(starttimestring) + " and " + str(endtimestring))
print(str(uploadstring))
yesno = input("To abort type 'no': ")
if yesno == 'no':
    sys.exit("Aborting.")





# # 5. Main Parsing Function: Writes config.txt and runs the script generatemetadata() including parseexcel() if upload is set to True

# In[ ]:


for station in parselist:
    
    print("__________________________________________________________________________")
    print("Parsing Station " + str(parselist.index(station) + 1) + " of " + str(len(parselist)))
    with open('config.txt','w') as configtxt:
        configuration={}

        configuration["url"] = destinationurl
        configuration["thingcode"] = station
        configuration["feature"] = "PM10"
        configuration["intervalllength"] = "PT1H"
        configuration["runparseaftermodelling"] = upload
        configuration["starttime"] = starttime #in case of false will try to find the earliest date of a measurement
        configuration["endtime"] = endtime #in case of false will take utctime.now()
        #time format is ISO8601 time standard UTC, e.g.: '2018-12-31T23:59:00.000Z'

        configtxt.write(json.dumps(configuration))
    
    generatemetadata()
#    with open('UBA_generate_excel_with_metadata.py') as generatedata:
#        exec(generatedata.read())

sys.stdout.write('\n' + '__________________________________________________________________________' + '\n')
print("Done")


# In[ ]:


#requests.delete("http://smartaqnet-dev.teco.edu:8080/FROST-Server/v1.0/Things")
#requests.delete("http://smartaqnet-dev.teco.edu:8080/FROST-Server/v1.0/Sensors")
#requests.delete("http://smartaqnet-dev.teco.edu:8080/FROST-Server/v1.0/Locations")
#requests.delete("http://smartaqnet-dev.teco.edu:8080/FROST-Server/v1.0/ObservedProperties")
#requests.delete("http://smartaqnet-dev.teco.edu:8080/FROST-Server/v1.0/FeaturesOfInterest")
#requests.delete("http://smartaqnet-dev.teco.edu:8080/FROST-Server/v1.0/Datastreams")
#requests.delete("http://smartaqnet-dev.teco.edu:8080/FROST-Server/v1.0/Observations")

