# UBA2SensorThings

Um zumindest rudimentäre Informationen über die benutzten Sensortypen bekommen zu können, braucht das Skript die Metadaten aus den beiden Files (Things und Datastreams) vom UBA, zu finden unter
https://www.env-it.de/stationen/public/downloadRequest.do;jsessionid=E8AFCC07034FB720B76496AD24465D5B.2

Die Messdaten kommen von
https://www.umweltbundesamt.de/daten/luft/luftdaten/doc

Python Notebook "new_uba_parser" modelliert die Datenbank (falls noch nicht vorhanden) und schreibt Werte für den angegeben Zeitraum für die gewünschte Station in die Datenbank. 

Python Notebook / Python Skript "UBA_liveparser" fragt die api.smartaq.net Datenbank an nach allen Things mit /properties/operator.domain = umweltbundesamt.de und füllt diese mit Daten auf soweit verfügbar. 