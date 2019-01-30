# UBA2SensorThings

Braucht die Metadaten aus den beiden Files (Things und Datastreams) vom UBA, zu finden unter
https://www.env-it.de/stationen/public/downloadRequest.do;jsessionid=E8AFCC07034FB720B76496AD24465D5B.2

Die Messdaten kommen von
https://www.umweltbundesamt.de/js/uaq/data/stations/measuring?pollutant[]=PM10&scope[]=1SMW&station[]=DEBY007&group[]=pollutant&range[]=1546398762,1546598762

Die eine File Modelliert die Datenbank (falls noch nicht vorhanden) und generiert ein Excel File mit den Werten aus dem angegebenen Zeitraum für die gewünschte Station. 
Die andere File parsed das Excel File und schreibt die Daten auf den Server. 
