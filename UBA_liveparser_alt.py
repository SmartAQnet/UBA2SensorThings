#!/usr/bin/env python
from datetime import datetime, timezone
import hashlib
import logging as log
import requests
import isodate 

log.basicConfig(level=log.INFO)

ST_URL = "http://smartaqnet-dev.dmz.teco.edu/v1.0"  # saqn frost server
UBA_URL = 'https://www.umweltbundesamt.de/api/air_data/v2/measures/json'

SCOPE = '2'  # umweltbundesamt website code: 1 hour averages
SCOPE_SEC = 60 * 60  # scope in seconds


FEATURE = '1'  # umweltbundesamt observedProperty code 'component'
OBSPROPERTY_CODE = "mcpm10"  # frost server observedProperty code



def getdate(unixtime):
    """returns unix timestamp in format YYYY-MM-DD so uba does understand it"""
    return pd.to_datetime(unixtime,unit='s').strftime("%Y-%m-%d")
    

def gettime(unixtime):
    """returns unix timestamp in format HH:mm:ss so uba does understand it"""
    return pd.to_datetime(unixtime,unit='s').strftime("%H:%M:%S")

def getisostamp(unixtime):
    """returns unix timestamp in format YYYY-MM-DDTHH:mm:ss.000Z for the database to accept"""
    return pd.to_datetime(unixtime,unit='s').strftime("%Y-%m-%d" + "T" + "%H:%M:%S" + ".000Z")


def idstr(idinput):
    """returns strings in the conventional format for iot.ids"""
    return (str(idinput).lower().replace(" ", "_").replace("/", "_").replace(
        "ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss"))


def hashfunc(inputstring):
    """returns the first 7 digits of the sha1 hash of the input string"""
    returnhash = hashlib.sha1(bytes(str(inputstring),
                                    'utf-8')).hexdigest()[0:7]
    log.debug("Converting '" + str(inputstring) + "' to hash '" +
              str(returnhash) + "'")
    return returnhash


def hashfuncfull(inputstring):
    """returns the full 40 digits of the sha1 hash of the input string"""
    returnhash = hashlib.sha1(bytes(str(inputstring), 'utf-8')).hexdigest()
    log.debug("Converting '" + str(inputstring) + "' to hash '" +
              str(returnhash) + "'")
    return returnhash


def get(*r):
    """Sensorthing request"""
    paginate = len([x for x in r if x.startswith("$top")]) > 0
    url = ST_URL + "/" + r[0] + "?" + "&".join(r[1:]) if len(r) > 1 else ""
    json = {"value": []}
    while True:
        response = requests.get(url)
        response.raise_for_status()
        value = json["value"]
        json = response.json()
        json["value"] += value
        if paginate and "@iot.nextLink" in response.json():
            url = response.json()["@iot.nextLink"]
        else:
            break
    return json


def getuba(current_component, current_scope, current_station, start_date, start_result_time, end_date, end_result_time):
    """Umweltbundesamt request"""
    getdatafrom = UBA_URL + '?date_from=' + start_date + "&time_from=" + start_result_time + "&date_to=" + end_date + "&time_to=" + end_result_time + "&station=" + current_station["station id"] + "&component=" + current_component + "&scope=" + current_scope
    response = requests.get(getdatafrom)
    response.raise_for_status()
    return response.json()



# - get all existing UBA stations from frost server
# - get the latest observation date
# - get the next observation from UBA server
# - post to frost

# all things von lfu.bayern.de


class LatestObservations:  # pylint: disable=too-few-public-methods
    """iterate the latest observation"""

    def __init__(self, iot_id):
        self.iot_id = iot_id
        self.last = None

    def __iter__(self):
        return self

    def __next__(self):
        latest_pheno_time = get(
            "Datastreams('" + datastream["@iot.id"] + "')/Observations",
            "$orderby=phenomenontime%20desc&$top=1"
        )["value"][0]["phenomenonTime"]
        end_latest_pheno_datetime = isodate.parse_datetime(
            latest_pheno_time.split('/')[-1])
        if (datetime.now(timezone.utc) -
                end_latest_pheno_datetime).total_seconds() < SCOPE_SEC + 10:
            raise StopIteration()
        self.last = end_latest_pheno_datetime
        return self.last


# for each thing...
for thing in get(
        "Things",
        "$filter=properties/operator.domain eq 'umweltbundesamt.de'")["value"]:
    log.info(thing["name"])

    # ...identify the datastream iot.id corresponding to the observedproperty
    try:
        datastream = get(
            "Things('" + thing["@iot.id"] + "')/Datastreams",
            "$filter=ObservedProperty/@iot.id eq 'saqn:op:" +
            OBSPROPERTY_CODE + "'")["value"][0]
    except IndexError:
        log.warning("no datastream existing for thing " + thing["name"] +
                    " with observedProperty " + OBSPROPERTY_CODE)
        continue

    for current in LatestObservations(datastream["@iot.id"]):
        begintimeunix = current.timestamp()
        endtimeunix = begintimeunix + SCOPE_SEC

        # get data from uba
        datavalue = getuba(FEATURE, SCOPE, thing["properties"]["hardware.id"],
                           getdate(begintimeunix), gettime(begintimeunix), getdate(endtimeunix), gettime(endtimeunix))

        # get the unhashed datastream id
        # thing id
        thing_tohash = idstr(str(thing["properties"]["operator.domain"]) + ":" + str(thing["properties"]["shortname"]) + ":" + str(thing["properties"]["hardware.id"]))

        # Sensor id
        sensor = json.loads(requests.get(datastream["Sensor@iot.navigationLink"]).text)
        sensor_tohash =  idstr(str(sensor["properties"]["manufacturer.domain"]) + ":" + str(sensor["properties"]["shortname"])
        
        
        # Datastream ID
        stream_id_serialnumber = str(datastream["properties"]["hardware.serial_number"])

        fullstream_tohash = idstr(thing_tohash + ":" + sensor_tohash + ":" + stream_id_serialnumber + ":" + OBSPROPERTY_CODE)

        # generate observation and push to frost
        observation_id_prefix = "saqn:o:"
        observation_interval = current.isoformat() + "/" + "PT1H"
        observation_tohash = idstr(fullstream_tohash + ":" +
                                   observation_interval)
        generateobsid = observation_id_prefix + hashfuncfull(
            observation_tohash)

        observation = {
            "phenomenonTime": observation_interval,
            "resultTime": getisostamp(endtimeunix),
            "result": datavalue,
            "Datastream": {
                "@iot.id": datastream["@iot.id"]
            },
            "@iot.id": generateobsid
        }
        requests.post(ST_URL + "/Datastreams('" + datastream["@iot.id"] +
                      "')/Observations",
                      json=observation).raise_for_status()
        log.info("Successfully posted an Observation for " +
                 str(observation_interval))
