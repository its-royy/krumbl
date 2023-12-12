import re
import xml.etree.ElementTree as et
from collections import defaultdict
from itertools import repeat

import geopy.geocoders
import pandas as pd
import requests
from geopy.geocoders import Nominatim

ns = {"kml": "http://www.opengis.net/kml/2.2"}
lineAcceptedInputs = ["ID", 'IOU', 'TYPE', 'OWNER', 'VOLTAGE', 'VOLT_SOURCE', 'INFERRED', 'SUB', 'SUB_2', 'ANALYST', 'VAL_DATE', 'COUNTY']
def kmlToDF(root):
    if root == None:
        pass
    else:
        linesData = defaultdict(list)
        # first folder (Trumbull)
        for folder in root.findall('.//kml:Folder', ns):
            for folder_names in folder:  # all children including name, open, and any subfolders
                if 'line' in folder_names.text.lower():
                    # accessing SimpleData layer within each placemark
                    for ind, line in enumerate(folder.findall('.//kml:Placemark', ns)):
                        # name = line.find('.//kml:name', ns).text
                        # __currentState = name.split('-')[0].lower() # WILL NEED TO CHANGE THIS IN THE FUTURE, THIS ITERATES OVER ALL PLACEMARKS AND CONSTANTLY CHANGES, WHICH IS UNNECESSARY
                        attribList = [x.attrib['name'] for x in line.findall(
                            './/kml:SimpleData', ns)]
                        current = set(attribList)
                        original = set(lineAcceptedInputs)
                        if len(attribList) < 12:
                            missing = list(original - current)
                            if 'COUNTY' in missing:
                                schemaDataAttrib = line.find(
                                    './/kml:SchemaData', ns)
                                coordinates = line.find(
                                    './/kml:coordinates', ns).text
                                coordinatesList = coordinates.split(
                                    ' ')
                                coordinates = coordinatesList[0].split(',')
                                latitude = coordinates[1].strip()
                                longitude = coordinates[0].strip()
                                # geolocator = Nominatim(
                                #     user_agent='kmlHub')
                                # location = geolocator.reverse(
                                #     latitude+','+longitude, language='en')
                                # print(location)
                                # address = location.raw['address']
                                try:
                                    # raise geopy.exc.GeocoderServiceError
                                    geolocator = Nominatim(
                                        user_agent='kmlHub')
                                    location = geolocator.reverse(
                                        latitude+','+longitude, language='en')
                                    address = location.raw['address']
                                except geopy.exc.GeocoderServiceError or geopy.exc.GeocoderUnavailable or geopy.exc.GeocoderInsufficientPrivileges:   # when the geopy servers are down, or whenever geopy runs into an error for some reason, directly use Nominatim API with requests
                                    url = f'https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json&accept-language=en&addressdetails=1'
                                    res = requests.get(url)
                                    j = res.json()
                                    address = j['address']
                                county = address.get(
                                    'county', '').upper()
                                county = re.search(
                                    r'.*(?=\sCOUNTY)', county).group(0)
                                countyAttrib = et.Element(
                                    r'{http://www.opengis.net/kml/2.2}SimpleData', attrib={'name': 'COUNTY'})
                                countyAttrib.text = county.upper()
                                schemaDataAttrib.insert(
                                    len(attribList) + 1, countyAttrib)
                                linesData['COUNTY'].append(county.upper())
                                # self.minorErrors += 1
                            else:
                                for attribute in missing:
                                    linesData[attribute].append('')
                        elif len(attribList) > 12:
                            extraAttribs = (current - original)
                            for attrib in extraAttribs:
                                if len(linesData[attrib]) < ind + 1: # for every extra attribute added, need to add empty values for other placemarks that do not have this attribute so that the df can be made from equal length arrays. 
                                    diff = (ind+1) - (len(linesData[attrib]))
                                    linesData[attrib].extend(repeat('', diff - 1)) #Here, doing that but also making sure to add empty values before so that the value of the extra attribute is lined up with the correct line in the df
                        for child in line.findall('.//kml:SimpleData', ns):
                            if child.text == None:  # if SimpleData has a null or None value, replace it with an empty string
                                child.text = ''
                            for _, value in child.attrib.items():  # values = ID, IOU, TYPE, STATUS, VAL_METHOD, ETC
                                # appends based on SimpleData name => linesData['ID'], linesData['IOU']; child.text  is the text of each value => OH-TRUM-L0001
                                linesData[value].append(child.text)
                                

        # save as df to easily convert to csv
        df = pd.DataFrame(linesData)
        return df
    
def dfToCSV(df, outputName):
    if not df.empty:
        df.to_csv(outputName, index=False)
    else:
        pass
    
if __name__ == '__main__':
    doc = """<?xml version='1.0' encoding='utf-8'?>
    <kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
	<Document>
		<name>CAMBRIA.kml</name>
		<Schema name="Substations" id="Substations102">
			<SimpleField type="int" name="OBJECTID"></SimpleField>
			<SimpleField type="string" name="ID"></SimpleField>
			<SimpleField type="string" name="CITY"></SimpleField>
			<SimpleField type="string" name="STATE"></SimpleField>
			<SimpleField type="string" name="ZIP"></SimpleField>
			<SimpleField type="string" name="TYPE"></SimpleField>
			<SimpleField type="string" name="STATUS"></SimpleField>
			<SimpleField type="string" name="COUNTY"></SimpleField>
			<SimpleField type="string" name="COUNTYFIPS"></SimpleField>
			<SimpleField type="string" name="COUNTRY"></SimpleField>
			<SimpleField type="float" name="LATITUDE"></SimpleField>
			<SimpleField type="float" name="LONGITUDE"></SimpleField>
			<SimpleField type="string" name="NAICS_CODE"></SimpleField>
			<SimpleField type="string" name="NAICS_DESC"></SimpleField>
			<SimpleField type="string" name="SOURCE"></SimpleField>
			<SimpleField type="string" name="SOURCEDATE"></SimpleField>
			<SimpleField type="string" name="VAL_METHOD"></SimpleField>
			<SimpleField type="string" name="VAL_DATE"></SimpleField>
			<SimpleField type="int" name="LINES"></SimpleField>
			<SimpleField type="int" name="MAX_VOLT"></SimpleField>
			<SimpleField type="int" name="MIN_VOLT"></SimpleField>
			<SimpleField type="int" name="CAPACITY"></SimpleField>
			<SimpleField type="string" name="MAX_INFER"></SimpleField>
			<SimpleField type="string" name="MIN_INFER"></SimpleField>
		</Schema>
		<Style id="inline">
			<LineStyle>
				<color>ffffff00</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="inline0">
			<Pair>
				<key>normal</key>
				<styleUrl>#inline12</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#inline3</styleUrl>
			</Pair>
		</StyleMap>
		<StyleMap id="inline00">
			<Pair>
				<key>normal</key>
				<styleUrl>#inline100</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#inline300</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="inline01">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="inline010">
			<Pair>
				<key>normal</key>
				<styleUrl>#inline6</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#inline11</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="inline02">
			<LineStyle>
				<color>ffffff00</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="inline03">
			<Pair>
				<key>normal</key>
				<styleUrl>#inline16</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#inline1</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="inline1">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="inline10">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="inline100">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="inline11">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="inline12">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="inline13">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="inline14">
			<LineStyle>
				<color>ffffff00</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="inline140">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="inline15">
			<Pair>
				<key>normal</key>
				<styleUrl>#inline24</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#inline13</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="inline16">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="inline17">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="inline18">
			<Pair>
				<key>normal</key>
				<styleUrl>#inline22</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#inline17</styleUrl>
			</Pair>
		</StyleMap>
		<StyleMap id="inline2">
			<Pair>
				<key>normal</key>
				<styleUrl>#inline23</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#inline21</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="inline20">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="inline21">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="inline22">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="inline23">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="inline24">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="inline3">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="inline30">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="inline300">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="inline301">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="inline302">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="inline4">
			<LineStyle>
				<color>ffffff00</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="inline40">
			<Pair>
				<key>normal</key>
				<styleUrl>#inline50</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#inline20</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="inline41">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="inline410">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="inline4100">
			<Pair>
				<key>normal</key>
				<styleUrl>#inline140</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#inline01</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="inline411">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="inline5">
			<Pair>
				<key>normal</key>
				<styleUrl>#inline30</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#inline411</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="inline50">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="inline51">
			<Pair>
				<key>normal</key>
				<styleUrl>#inline301</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#inline41</styleUrl>
			</Pair>
		</StyleMap>
		<StyleMap id="inline52">
			<Pair>
				<key>normal</key>
				<styleUrl>#inline302</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#inline410</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="inline6">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="inline7">
			<Pair>
				<key>normal</key>
				<styleUrl>#inline</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#inline14</styleUrl>
			</Pair>
		</StyleMap>
		<StyleMap id="inline70">
			<Pair>
				<key>normal</key>
				<styleUrl>#inline4</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#inline02</styleUrl>
			</Pair>
		</StyleMap>
		<StyleMap id="inline8">
			<Pair>
				<key>normal</key>
				<styleUrl>#inline10</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#inline9</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="inline9">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="msn_grn-pushpin">
			<Pair>
				<key>normal</key>
				<styleUrl>#sn_grn-pushpin</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sh_grn-pushpin</styleUrl>
			</Pair>
		</StyleMap>
		<StyleMap id="msn_placemark_square">
			<Pair>
				<key>normal</key>
				<styleUrl>#sn_placemark_square</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sh_placemark_square_highlight</styleUrl>
			</Pair>
		</StyleMap>
		<StyleMap id="msn_ylw-pushpin0">
			<Pair>
				<key>normal</key>
				<styleUrl>#sn_ylw-pushpin0</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sh_ylw-pushpin</styleUrl>
			</Pair>
		</StyleMap>
		<StyleMap id="msn_ylw-pushpin">
			<Pair>
				<key>normal</key>
				<styleUrl>#sn_ylw-pushpin</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sh_ylw-pushpin0</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="sh_grn-pushpin">
			<IconStyle>
				<scale>1.44</scale>
				<Icon>
					<href>http://maps.google.com/mapfiles/kml/pushpin/grn-pushpin.png</href>
				</Icon>
				<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"></hotSpot>
			</IconStyle>
		</Style>
		<Style id="sh_placemark_square_highlight">
			<IconStyle>
				<scale>1.2</scale>
				<Icon>
					<href>http://maps.google.com/mapfiles/kml/pushpin/grn-pushpin.png</href>
				</Icon>
				<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"></hotSpot>
			</IconStyle>
		</Style>
		<Style id="sh_ylw-pushpin">
			<IconStyle>
				<scale>1.3</scale>
				<Icon>
					<href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href>
				</Icon>
				<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"></hotSpot>
			</IconStyle>
			<BalloonStyle>
		</BalloonStyle>
		</Style>
		<Style id="sh_ylw-pushpin0">
			<IconStyle>
				<scale>1.3</scale>
				<Icon>
					<href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href>
				</Icon>
				<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"></hotSpot>
			</IconStyle>
			<BalloonStyle>
		</BalloonStyle>
		</Style>
		<Style id="sn_grn-pushpin">
			<IconStyle>
				<scale>1.2</scale>
				<Icon>
					<href>http://maps.google.com/mapfiles/kml/pushpin/grn-pushpin.png</href>
				</Icon>
				<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"></hotSpot>
			</IconStyle>
		</Style>
		<Style id="sn_placemark_square">
			<IconStyle>
				<scale>1.2</scale>
				<Icon>
					<href>http://maps.google.com/mapfiles/kml/pushpin/grn-pushpin.png</href>
				</Icon>
				<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"></hotSpot>
			</IconStyle>
		</Style>
		<Style id="sn_ylw-pushpin">
			<IconStyle>
				<scale>1.1</scale>
				<Icon>
					<href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href>
				</Icon>
				<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"></hotSpot>
			</IconStyle>
			<BalloonStyle>
		</BalloonStyle>
		</Style>
		<Style id="sn_ylw-pushpin0">
			<IconStyle>
				<scale>1.1</scale>
				<Icon>
					<href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href>
				</Icon>
				<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"></hotSpot>
			</IconStyle>
			<BalloonStyle>
		</BalloonStyle>
		</Style>
		<Style id="sub_transmission4000">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission40000">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission40001">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="sub_transmission400010">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400070</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400050</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="sub_transmission400011">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="sub_transmission400012">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400035</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400039</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="sub_transmission400013">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400014">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400015">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="sub_transmission400016">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400067</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400056</styleUrl>
			</Pair>
		</StyleMap>
		<StyleMap id="sub_transmission400017">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400028</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400025</styleUrl>
			</Pair>
		</StyleMap>
		<StyleMap id="sub_transmission400018">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400043</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400037</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="sub_transmission400019">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission40002">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="sub_transmission400020">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400015</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400013</styleUrl>
			</Pair>
		</StyleMap>
		<StyleMap id="sub_transmission400021">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission40003</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission4000</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="sub_transmission400022">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400023">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400024">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400025">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400026">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="sub_transmission400027">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400049</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400053</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="sub_transmission400028">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400029">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission40003">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400030">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="sub_transmission400031">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400034</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400033</styleUrl>
			</Pair>
		</StyleMap>
		<StyleMap id="sub_transmission400032">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400068</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400065</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="sub_transmission400033">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400034">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400035">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="sub_transmission400036">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400024</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400029</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="sub_transmission400037">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400038">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400039">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission40004">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="sub_transmission400040">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission40004</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission40000</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="sub_transmission400041">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="sub_transmission400042">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400057</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400060</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="sub_transmission400043">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400044">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400045">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400046">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400047">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="sub_transmission400048">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400019</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission40005</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="sub_transmission400049">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission40005">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400050">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="sub_transmission400051">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400011</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400014</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="sub_transmission400052">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400053">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="sub_transmission400054">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission40002</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission40001</styleUrl>
			</Pair>
		</StyleMap>
		<StyleMap id="sub_transmission400055">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400064</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400045</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="sub_transmission400056">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400057">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400058">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400059">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="sub_transmission40006">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400041</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400026</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="sub_transmission400060">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400061">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400062">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="sub_transmission400063">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400058</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400052</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="sub_transmission400064">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400065">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400066">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400067">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400068">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="sub_transmission400069">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400044</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400059</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="sub_transmission40007">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400070">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="sub_transmission400071">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400066</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400079</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="sub_transmission400072">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400073">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<Style id="sub_transmission400074">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="sub_transmission400075">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400030</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400022</styleUrl>
			</Pair>
		</StyleMap>
		<StyleMap id="sub_transmission400076">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400061</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400062</styleUrl>
			</Pair>
		</StyleMap>
		<StyleMap id="sub_transmission400077">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400038</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400023</styleUrl>
			</Pair>
		</StyleMap>
		<StyleMap id="sub_transmission400078">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400046</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400047</styleUrl>
			</Pair>
		</StyleMap>
		<Style id="sub_transmission400079">
			<LineStyle>
				<color>ffff00aa</color>
				<width>3</width>
			</LineStyle>
			<PolyStyle>
				<fill>0</fill>
			</PolyStyle>
		</Style>
		<StyleMap id="sub_transmission40008">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400074</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission40007</styleUrl>
			</Pair>
		</StyleMap>
		<StyleMap id="sub_transmission40009">
			<Pair>
				<key>normal</key>
				<styleUrl>#sub_transmission400073</styleUrl>
			</Pair>
			<Pair>
				<key>highlight</key>
				<styleUrl>#sub_transmission400072</styleUrl>
			</Pair>
		</StyleMap>
		<Folder>
			<name>CAMBRIA</name>
			<open>1</open>
			<Folder>
				<name>Substations</name>
				<Placemark>
					<name>GREEN HILL</name>
					<Point>
						<gx:drawOrder>1</gx:drawOrder>
						<coordinates>-78.912476,40.323442,0</coordinates>
					</Point>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="NAME">GREEN HILL</SimpleData>
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">JOHNSTOWN</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15902</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="OWNER">PENELEC</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.323442</SimpleData>
							<SimpleData name="LONGITUDE">-78.912476</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">IMAGERY</SimpleData>
							<SimpleData name="SOURCEDATE">2023/10/25</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2023/10/25</SimpleData>
							<SimpleData name="LINES"></SimpleData>
							<SimpleData name="MAX_VOLT">-1</SimpleData>
							<SimpleData name="MIN_VOLT">-1</SimpleData>
							<SimpleData name="CAPACITY">-1</SimpleData>
							<SimpleData name="MAX_INFER">N</SimpleData>
							<SimpleData name="MIN_INFER">N</SimpleData>
							<SimpleData name="GlobalID"></SimpleData>
						</SchemaData>
					</ExtendedData>
				</Placemark>
				<Placemark>
					<name>MINE 40</name>
					<Point>
						<gx:drawOrder>1</gx:drawOrder>
						<coordinates>-78.844757,40.253643,0</coordinates>
					</Point>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="NAME">MINE 40</SimpleData>
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">Windber</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15963</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="OWNER">PENELEC</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.253643</SimpleData>
							<SimpleData name="LONGITUDE">-78.844757</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">IMAGERY</SimpleData>
							<SimpleData name="SOURCEDATE">2023/10/25</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2023/10/25</SimpleData>
							<SimpleData name="LINES"></SimpleData>
							<SimpleData name="MAX_VOLT">-1</SimpleData>
							<SimpleData name="MIN_VOLT">-1</SimpleData>
							<SimpleData name="CAPACITY">-1</SimpleData>
							<SimpleData name="MAX_INFER">N</SimpleData>
							<SimpleData name="MIN_INFER">N</SimpleData>
							<SimpleData name="GlobalID"></SimpleData>
						</SchemaData>
					</ExtendedData>
				</Placemark>
				<Placemark>
					<name>ASHVILLE</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">ASHVILLE</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">16613</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.552017</SimpleData>
							<SimpleData name="LONGITUDE">-78.557620</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">1</SimpleData>
							<SimpleData name="MAX_VOLT">46</SimpleData>
							<SimpleData name="MIN_VOLT">46</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.55762,40.552017,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>BEAR ROCK</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">26232</SimpleData>
							<SimpleData name="ID">123838</SimpleData>
							<SimpleData name="CITY">ALTOONA</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">16602</SimpleData>
							<SimpleData name="TYPE">SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.402228591</SimpleData>
							<SimpleData name="LONGITUDE">-78.566267438</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-05-27T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">4</SimpleData>
							<SimpleData name="MAX_VOLT">230</SimpleData>
							<SimpleData name="MIN_VOLT">230</SimpleData>
							<SimpleData name="MAX_INFER">Y</SimpleData>
							<SimpleData name="MIN_INFER">Y</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.56626743799995,40.40222859100003,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>BELMONT</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">STONYCREEK TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15904</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.288469</SimpleData>
							<SimpleData name="LONGITUDE">-78.898654</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.89865399999999,40.288469,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>BETHLEHEM GILLEN</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">VINCO</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15942</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.416661</SimpleData>
							<SimpleData name="LONGITUDE">-78.878741</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">IMAGERY</SimpleData>
							<SimpleData name="SOURCEDATE">2020-10-26T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2020-10-26T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">2</SimpleData>
							<SimpleData name="MAX_VOLT">46</SimpleData>
							<SimpleData name="MIN_VOLT">23</SimpleData>
							<SimpleData name="CAPACITY">14</SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.83305665392628,40.42217320814103,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>BETHLEHEM NO 31</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">JACKSON TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15943</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.453489</SimpleData>
							<SimpleData name="LONGITUDE">-78.825949</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.82594899999999,40.453489,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>BON AIR</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">26238</SimpleData>
							<SimpleData name="ID">124185</SimpleData>
							<SimpleData name="CITY">CONEMAUGH TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15902</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.340787984</SimpleData>
							<SimpleData name="LONGITUDE">-78.8718796269999</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">IMAGERY</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-14T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-05-14T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">3</SimpleData>
							<SimpleData name="MAX_VOLT">115</SimpleData>
							<SimpleData name="MIN_VOLT">115</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">Y</SimpleData>
							<SimpleData name="MIN_INFER">Y</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.87187962699994,40.34078798400002,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>BOULEVARD</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">36354</SimpleData>
							<SimpleData name="ID">157417</SimpleData>
							<SimpleData name="CITY">JOHNSTOWN</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15906</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.3339202760001</SimpleData>
							<SimpleData name="LONGITUDE">-78.925874576</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2017-10-09T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2017-10-10T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NOT AVAILABLE</SimpleData>
							<SimpleData name="MIN_INFER">NOT AVAILABLE</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.92587457599994,40.33392027600007,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>CAMBRIA CO-GEN COMPANY</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">26229</SimpleData>
							<SimpleData name="ID">123835</SimpleData>
							<SimpleData name="CITY">EBENSBURG</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15931</SimpleData>
							<SimpleData name="TYPE">POWER PLANT</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.4743658940001</SimpleData>
							<SimpleData name="LONGITUDE">-78.7018464449999</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-06-16T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">2</SimpleData>
							<SimpleData name="MAX_VOLT">115</SimpleData>
							<SimpleData name="MIN_VOLT">115</SimpleData>
							<SimpleData name="MAX_INFER">Y</SimpleData>
							<SimpleData name="MIN_INFER">Y</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.70184644499994,40.47436589400007,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>CAMBRIA COUNTY PRISON</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">EBENSBURG</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15931</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.486454</SimpleData>
							<SimpleData name="LONGITUDE">-78.697133</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2020-10-22T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2020-10-22T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">1</SimpleData>
							<SimpleData name="MAX_VOLT">46</SimpleData>
							<SimpleData name="MIN_VOLT">23</SimpleData>
							<SimpleData name="CAPACITY">11</SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.69713299999999,40.486454,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>CAMBRIA SLOPE</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">26230</SimpleData>
							<SimpleData name="ID">123836</SimpleData>
							<SimpleData name="CITY">CRESSON TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">16630</SimpleData>
							<SimpleData name="TYPE">TRANSMISSION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.459592695</SimpleData>
							<SimpleData name="LONGITUDE">-78.693959799</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-05-27T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">5</SimpleData>
							<SimpleData name="MAX_VOLT">115</SimpleData>
							<SimpleData name="MIN_VOLT">115</SimpleData>
							<SimpleData name="MAX_INFER">Y</SimpleData>
							<SimpleData name="MIN_INFER">Y</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.69395979899997,40.45959269500003,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>CARROLTOWN</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">CARROLTOWN</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15773</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.619899</SimpleData>
							<SimpleData name="LONGITUDE">-78.705230</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2020-10-30T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2020-10-30T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">1</SimpleData>
							<SimpleData name="MAX_VOLT">46</SimpleData>
							<SimpleData name="MIN_VOLT">46</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.70523,40.619899,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>COLVER POWER PROJECT</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">26228</SimpleData>
							<SimpleData name="ID">123834</SimpleData>
							<SimpleData name="CITY">CAMBRIA TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15927</SimpleData>
							<SimpleData name="TYPE">POWER PLANT</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.551301499</SimpleData>
							<SimpleData name="LONGITUDE">-78.798196848</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-05-15T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">2</SimpleData>
							<SimpleData name="MAX_VOLT">115</SimpleData>
							<SimpleData name="MIN_VOLT">115</SimpleData>
							<SimpleData name="MAX_INFER">Y</SimpleData>
							<SimpleData name="MIN_INFER">Y</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.79819684799998,40.55130149900003,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>CONEMAUGH</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">JOHNSTOWN</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15906</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.351552</SimpleData>
							<SimpleData name="LONGITUDE">-78.887691</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.887691,40.351552,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>COOPER</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">26235</SimpleData>
							<SimpleData name="ID">124181</SimpleData>
							<SimpleData name="CITY">MIDDLE TAYLOR TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15906</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.3522997420001</SimpleData>
							<SimpleData name="LONGITUDE">-78.9291682739999</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">IMAGERY</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-14T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-05-14T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">2</SimpleData>
							<SimpleData name="MAX_VOLT">115</SimpleData>
							<SimpleData name="MIN_VOLT">23</SimpleData>
							<SimpleData name="CAPACITY">75</SimpleData>
							<SimpleData name="MAX_INFER">Y</SimpleData>
							<SimpleData name="MIN_INFER">Y</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.92916827399995,40.35229974200007,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>EBENSBURG</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">34366</SimpleData>
							<SimpleData name="ID">147378</SimpleData>
							<SimpleData name="CITY">EBENSBURG</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15931</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.4819402970001</SimpleData>
							<SimpleData name="LONGITUDE">-78.7265892349999</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2016-08-04T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2017-04-03T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">1</SimpleData>
							<SimpleData name="MAX_VOLT">46</SimpleData>
							<SimpleData name="MIN_VOLT">12.47</SimpleData>
							<SimpleData name="CAPACITY">18</SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.72658923499993,40.48194029700005,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>EBENSBURG POWER COMPANY</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">26239</SimpleData>
							<SimpleData name="ID">124186</SimpleData>
							<SimpleData name="CITY">EBENSBURG</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15931</SimpleData>
							<SimpleData name="TYPE">POWER PLANT</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.4554994200001</SimpleData>
							<SimpleData name="LONGITUDE">-78.747694367</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">IMAGERY</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-14T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-06-18T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">2</SimpleData>
							<SimpleData name="MAX_VOLT">115</SimpleData>
							<SimpleData name="MIN_VOLT">115</SimpleData>
							<SimpleData name="MAX_INFER">Y</SimpleData>
							<SimpleData name="MIN_INFER">Y</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.74769436699995,40.45549942000007,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>DORIS</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">JOHNSTOWN</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15906</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.366613</SimpleData>
							<SimpleData name="LONGITUDE">-78.939569</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.93956900000001,40.366613,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>EHRENFELD JACKSON</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">CROYLE TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15958</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.383386</SimpleData>
							<SimpleData name="LONGITUDE">-78.776191</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.776191,40.383386,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>FALLENTIMBER</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">READE TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">16639</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.688265</SimpleData>
							<SimpleData name="LONGITUDE">-78.494007</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">1</SimpleData>
							<SimpleData name="MAX_VOLT">46</SimpleData>
							<SimpleData name="MIN_VOLT">46</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.494007,40.688265,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>FRANKLIN BORO</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">JOHNSTOWN</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15909</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.346724</SimpleData>
							<SimpleData name="LONGITUDE">-78.879624</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY">6</SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.87962400000001,40.346724,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>GARMAN</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">26233</SimpleData>
							<SimpleData name="ID">124177</SimpleData>
							<SimpleData name="CITY">SUSQUEHANNA TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15714</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.695483117</SimpleData>
							<SimpleData name="LONGITUDE">-78.818995462</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">IMAGERY</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-13T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-05-13T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">3</SimpleData>
							<SimpleData name="MAX_VOLT">115</SimpleData>
							<SimpleData name="MIN_VOLT">34.5</SimpleData>
							<SimpleData name="CAPACITY">50</SimpleData>
							<SimpleData name="MAX_INFER">Y</SimpleData>
							<SimpleData name="MIN_INFER">Y</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.81899546199998,40.69548311700004,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>GEISTOWN</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">RICHLAND TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15904</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.300196</SimpleData>
							<SimpleData name="LONGITUDE">-78.869016</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.869016,40.300196,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>HILLTOP</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">26236</SimpleData>
							<SimpleData name="ID">124182</SimpleData>
							<SimpleData name="CITY">DAISYTOWN</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15902</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.3212239810001</SimpleData>
							<SimpleData name="LONGITUDE">-78.903723508</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">IMAGERY</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-14T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-05-14T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">3</SimpleData>
							<SimpleData name="MAX_VOLT">115</SimpleData>
							<SimpleData name="MIN_VOLT">23</SimpleData>
							<SimpleData name="CAPACITY">60</SimpleData>
							<SimpleData name="MAX_INFER">Y</SimpleData>
							<SimpleData name="MIN_INFER">Y</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.90372350799998,40.32122398100006,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>HOLLOW RD?</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">PA0021</SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">SUMMERHILL</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15958</SimpleData>
							<SimpleData name="TYPE">SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.40782200935131</SimpleData>
							<SimpleData name="LONGITUDE">-78.8105884969281</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap, http://www.pjm.com/markets-and-operations/transmission-service/transmission-facilities.aspx</SimpleData>
							<SimpleData name="SOURCEDATE">2015/05/05 00:00:00+00</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015/10/02 00:00:00+00</SimpleData>
							<SimpleData name="LINES"></SimpleData>
							<SimpleData name="MAX_VOLT"></SimpleData>
							<SimpleData name="MIN_VOLT"></SimpleData>
							<SimpleData name="MAX_INFER">N</SimpleData>
							<SimpleData name="MIN_INFER">N</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.8105884969281,40.40782200935131,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>IRON BRIDGE?</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">PA0019</SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">NICKTOWN</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15762</SimpleData>
							<SimpleData name="TYPE">SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.56162756669899</SimpleData>
							<SimpleData name="LONGITUDE">-78.86026426932422</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap, http://www.pjm.com/markets-and-operations/transmission-service/transmission-facilities.aspx</SimpleData>
							<SimpleData name="SOURCEDATE">2015/05/05 00:00:00+00</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015/10/02 00:00:00+00</SimpleData>
							<SimpleData name="LINES"></SimpleData>
							<SimpleData name="MAX_VOLT"></SimpleData>
							<SimpleData name="MIN_VOLT"></SimpleData>
							<SimpleData name="MAX_INFER">N</SimpleData>
							<SimpleData name="MIN_INFER">N</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.86026426932422,40.56162756669899,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>JACKSON ROAD</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">26240</SimpleData>
							<SimpleData name="ID">124188</SimpleData>
							<SimpleData name="CITY">MINERAL POINT</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15942</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.429409918</SimpleData>
							<SimpleData name="LONGITUDE">-78.817383228</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">IMAGERY</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-14T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-05-14T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">2</SimpleData>
							<SimpleData name="MAX_VOLT">115</SimpleData>
							<SimpleData name="MIN_VOLT">115</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">Y</SimpleData>
							<SimpleData name="MIN_INFER">Y</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.81738322799998,40.42940991800003,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>JOHNSTOWN</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">26244</SimpleData>
							<SimpleData name="ID">146944</SimpleData>
							<SimpleData name="CITY">JACKSON TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15906</SimpleData>
							<SimpleData name="TYPE">SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.403750562</SimpleData>
							<SimpleData name="LONGITUDE">-78.916081478</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-05-27T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">5</SimpleData>
							<SimpleData name="MAX_VOLT">230</SimpleData>
							<SimpleData name="MIN_VOLT">115</SimpleData>
							<SimpleData name="MAX_INFER">Y</SimpleData>
							<SimpleData name="MIN_INFER">Y</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.91608147799995,40.40375056200001,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>KRAYNE</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">26243</SimpleData>
							<SimpleData name="ID">124192</SimpleData>
							<SimpleData name="CITY">ADAMS TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15955</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.302963026</SimpleData>
							<SimpleData name="LONGITUDE">-78.6904957639999</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">IMAGERY</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-14T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-05-14T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">4</SimpleData>
							<SimpleData name="MAX_VOLT">115</SimpleData>
							<SimpleData name="MIN_VOLT">115</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">Y</SimpleData>
							<SimpleData name="MIN_INFER">Y</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.69049576399993,40.30296302600005,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>LILY</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">SOUTH FORK BORO</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15938</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.432266</SimpleData>
							<SimpleData name="LONGITUDE">-78.624385</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.624385,40.432266,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>LORETTO</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">ALLEGANY TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15940</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.497270</SimpleData>
							<SimpleData name="LONGITUDE">-78.625587</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.625587,40.49727,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>NANTY GLO</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">39350</SimpleData>
							<SimpleData name="ID">123833</SimpleData>
							<SimpleData name="CITY">NANTY GLO</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15943</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.4722648220001</SimpleData>
							<SimpleData name="LONGITUDE">-78.831550756</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-06-16T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">46</SimpleData>
							<SimpleData name="MIN_VOLT">12.47</SimpleData>
							<SimpleData name="CAPACITY">8</SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.83155075599994,40.47226482200006,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>NICKTOWN</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">NICKTOWN</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15762</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.629258</SimpleData>
							<SimpleData name="LONGITUDE">-78.828311</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">1</SimpleData>
							<SimpleData name="MAX_VOLT">46</SimpleData>
							<SimpleData name="MIN_VOLT">46</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.828311,40.629258,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>Oregon</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">36355</SimpleData>
							<SimpleData name="ID">157603</SimpleData>
							<SimpleData name="CITY">JOHNSTOWN</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15906</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.3418558450001</SimpleData>
							<SimpleData name="LONGITUDE">-78.936159114</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2017-10-09T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2017-10-10T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NOT AVAILABLE</SimpleData>
							<SimpleData name="MIN_INFER">NOT AVAILABLE</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.93615911399995,40.34185584500005,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>PATTON</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">PATTON</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">16668</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.614450</SimpleData>
							<SimpleData name="LONGITUDE">-78.662571</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2020-10-30T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2020-10-30T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">1</SimpleData>
							<SimpleData name="MAX_VOLT">46</SimpleData>
							<SimpleData name="MIN_VOLT">46</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.662571,40.61445,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>PORTAGE</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">31774</SimpleData>
							<SimpleData name="ID">147379</SimpleData>
							<SimpleData name="CITY">PORTAGE TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15946</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.3966431850001</SimpleData>
							<SimpleData name="LONGITUDE">-78.6620170309999</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2016-08-04T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2017-04-03T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">46</SimpleData>
							<SimpleData name="MIN_VOLT">12.47</SimpleData>
							<SimpleData name="CAPACITY">19</SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.66201703099996,40.39664318500006,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>PROSPECT</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">JOHNSTOWN</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15901</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.336861</SimpleData>
							<SimpleData name="LONGITUDE">-78.918324</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.918324,40.336861,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>RACHEL HILL</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">26241</SimpleData>
							<SimpleData name="ID">124190</SimpleData>
							<SimpleData name="CITY">RICHLAND TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15904</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.267047045</SimpleData>
							<SimpleData name="LONGITUDE">-78.847842778</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">IMAGERY</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-14T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-05-14T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">2</SimpleData>
							<SimpleData name="MAX_VOLT">115</SimpleData>
							<SimpleData name="MIN_VOLT">23</SimpleData>
							<SimpleData name="CAPACITY">58</SimpleData>
							<SimpleData name="MAX_INFER">Y</SimpleData>
							<SimpleData name="MIN_INFER">Y</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.84784277799997,40.26704704500003,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>REA WILMORE</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">READE TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">16639</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.409143</SimpleData>
							<SimpleData name="LONGITUDE">-78.689546</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">2</SimpleData>
							<SimpleData name="MAX_VOLT">46</SimpleData>
							<SimpleData name="MIN_VOLT">46</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.68954600000001,40.409143,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>REEDER STREET</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">JOHNSTOWN</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15906</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.299203</SimpleData>
							<SimpleData name="LONGITUDE">-78.918675</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2020-10-23T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2020-10-23T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">115</SimpleData>
							<SimpleData name="MIN_VOLT">23</SimpleData>
							<SimpleData name="CAPACITY">75</SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.91867499999999,40.299203,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>REVLOC</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">CAMBRIA</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15948</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.495964</SimpleData>
							<SimpleData name="LONGITUDE">-78.769378</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2020-10-22T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2020-10-22T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">1</SimpleData>
							<SimpleData name="MAX_VOLT">46</SimpleData>
							<SimpleData name="MIN_VOLT">12.47</SimpleData>
							<SimpleData name="CAPACITY">18</SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.769378,40.495964,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>ROD MILL</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">JOHNSTOWN</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15906</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.349378</SimpleData>
							<SimpleData name="LONGITUDE">-78.941513</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.941513,40.349378,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>SALIX</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">26242</SimpleData>
							<SimpleData name="ID">124191</SimpleData>
							<SimpleData name="CITY">ADAMS TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15955</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.307115185</SimpleData>
							<SimpleData name="LONGITUDE">-78.756294999</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">IMAGERY</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-14T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-05-14T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">2</SimpleData>
							<SimpleData name="MAX_VOLT">115</SimpleData>
							<SimpleData name="MIN_VOLT">23</SimpleData>
							<SimpleData name="CAPACITY">30</SimpleData>
							<SimpleData name="MAX_INFER">Y</SimpleData>
							<SimpleData name="MIN_INFER">Y</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.75629499899998,40.30711518500004,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>SOUTH FORK</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">SOUTH FORK BORO</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15956</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.363797</SimpleData>
							<SimpleData name="LONGITUDE">-78.796347</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.796347,40.363797,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>SPANGLER</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">26234</SimpleData>
							<SimpleData name="ID">124178</SimpleData>
							<SimpleData name="CITY">NORTHERN CAMBRIA</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15714</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.6354695410001</SimpleData>
							<SimpleData name="LONGITUDE">-78.76929685</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">IMAGERY</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-13T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-05-13T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">1</SimpleData>
							<SimpleData name="MAX_VOLT">115</SimpleData>
							<SimpleData name="MIN_VOLT">12.47</SimpleData>
							<SimpleData name="CAPACITY">65</SimpleData>
							<SimpleData name="MAX_INFER">Y</SimpleData>
							<SimpleData name="MIN_INFER">Y</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.76929684999999,40.63546954100007,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>SPRUCE STREET</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">26237</SimpleData>
							<SimpleData name="ID">124183</SimpleData>
							<SimpleData name="CITY">FRANKLIN</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15909</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.3380813470001</SimpleData>
							<SimpleData name="LONGITUDE">-78.883039299</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">IMAGERY</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-14T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-05-14T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">1</SimpleData>
							<SimpleData name="MAX_VOLT">115</SimpleData>
							<SimpleData name="MIN_VOLT">115</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">Y</SimpleData>
							<SimpleData name="MIN_INFER">Y</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.88303929899998,40.33808134700006,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>ST AUGUSTINE</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">CLEARFIELD TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">16668</SimpleData>
							<SimpleData name="TYPE">REA REC SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.609033</SimpleData>
							<SimpleData name="LONGITUDE">-78.573763</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">1</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.573763,40.609033,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>ST BENEDICT</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">CARROLTOWN</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15773</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.628949</SimpleData>
							<SimpleData name="LONGITUDE">-78.736417</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2020-10-30T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2020-10-30T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">1</SimpleData>
							<SimpleData name="MAX_VOLT">46</SimpleData>
							<SimpleData name="MIN_VOLT">12.47</SimpleData>
							<SimpleData name="CAPACITY">17</SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.736417,40.628949,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>SUMMIT</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">26231</SimpleData>
							<SimpleData name="ID">123837</SimpleData>
							<SimpleData name="CITY">CRESSON TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">16630</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.4597073670001</SimpleData>
							<SimpleData name="LONGITUDE">-78.569900224</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-05-15T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">3</SimpleData>
							<SimpleData name="MAX_VOLT">115</SimpleData>
							<SimpleData name="MIN_VOLT">115</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">Y</SimpleData>
							<SimpleData name="MIN_INFER">Y</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.56990022399998,40.45970736700009,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>TEAKETTLE</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">BARR TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15762</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.598571</SimpleData>
							<SimpleData name="LONGITUDE">-78.847909</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.847909,40.598571,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>TOWER HILL</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">26227</SimpleData>
							<SimpleData name="ID">123831</SimpleData>
							<SimpleData name="CITY">UPPER YODER TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15905</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.296477753</SimpleData>
							<SimpleData name="LONGITUDE">-78.979231746</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-05-27T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">3</SimpleData>
							<SimpleData name="MAX_VOLT">115</SimpleData>
							<SimpleData name="MIN_VOLT">115</SimpleData>
							<SimpleData name="CAPACITY">42</SimpleData>
							<SimpleData name="MAX_INFER">Y</SimpleData>
							<SimpleData name="MIN_INFER">Y</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.979231746,40.29647775300003,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>TWIN ROCKS?</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">PA0020</SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">TWIN ROCKS</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15960</SimpleData>
							<SimpleData name="TYPE">SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.49369396264719</SimpleData>
							<SimpleData name="LONGITUDE">-78.86207529817082</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap, http://www.pjm.com/markets-and-operations/transmission-service/transmission-facilities.aspx</SimpleData>
							<SimpleData name="SOURCEDATE">2015/05/05 00:00:00+00</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015/10/02 00:00:00+00</SimpleData>
							<SimpleData name="LINES"></SimpleData>
							<SimpleData name="MAX_VOLT"></SimpleData>
							<SimpleData name="MIN_VOLT"></SimpleData>
							<SimpleData name="MAX_INFER">N</SimpleData>
							<SimpleData name="MIN_INFER">N</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.86207529817082,40.49369396264719,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>UNKNOWN124184</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID">39351</SimpleData>
							<SimpleData name="ID">124184</SimpleData>
							<SimpleData name="CITY">FRANKLIN</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15909</SimpleData>
							<SimpleData name="TYPE">SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.3373496630001</SimpleData>
							<SimpleData name="LONGITUDE">-78.888315754</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">IMAGERY</SimpleData>
							<SimpleData name="SOURCEDATE">2015-05-14T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2015-05-14T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="MAX_INFER">NOT AVAILABLE</SimpleData>
							<SimpleData name="MIN_INFER">NOT AVAILABLE</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.88831575399996,40.33734966300005,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>WESLEY CHAPEL</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">EAST TAYLOR TWP</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15909</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.390860</SimpleData>
							<SimpleData name="LONGITUDE">-78.862485</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.86248500000001,40.39086,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>WESTWOOD</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">JOHNSTOWN</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15905</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.324891</SimpleData>
							<SimpleData name="LONGITUDE">-78.961384</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.961384,40.324891,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>WOODMONT</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">JOHNSTOWN</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15905</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.319306</SimpleData>
							<SimpleData name="LONGITUDE">-78.979843</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.979843,40.319306,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>WOODVALE</name>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">JOHNSTOWN</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15906</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.334958</SimpleData>
							<SimpleData name="LONGITUDE">-78.898633</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">OpenStreetMap</SimpleData>
							<SimpleData name="SOURCEDATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2021-01-05T00:00:00.000Z</SimpleData>
							<SimpleData name="LINES">0</SimpleData>
							<SimpleData name="MAX_VOLT">-999999</SimpleData>
							<SimpleData name="MIN_VOLT">-999999</SimpleData>
							<SimpleData name="CAPACITY"></SimpleData>
							<SimpleData name="MAX_INFER">NU</SimpleData>
							<SimpleData name="MIN_INFER">NU</SimpleData>
						</SchemaData>
					</ExtendedData>
					<Point>
						<coordinates>-78.898633,40.334958,0</coordinates>
					</Point>
				</Placemark>
				<Placemark>
					<name>CAMBRIA SLOPE</name>
					<Point>
						<gx:drawOrder>1</gx:drawOrder>
						<coordinates>-78.697425,40.463151,0</coordinates>
					</Point>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="NAME">CAMBRIA SLOPE</SimpleData>
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">Ebensburg</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">15931</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="OWNER">PRISTINE RESOURCES</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="COUNTYFIPS">42021</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.463151</SimpleData>
							<SimpleData name="LONGITUDE">-78.697425</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">IMAGERY</SimpleData>
							<SimpleData name="SOURCEDATE">2023/10/25</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2023/10/25</SimpleData>
							<SimpleData name="LINES"></SimpleData>
							<SimpleData name="MAX_VOLT">-1</SimpleData>
							<SimpleData name="MIN_VOLT">-1</SimpleData>
							<SimpleData name="CAPACITY">RC</SimpleData>
							<SimpleData name="MAX_INFER">N</SimpleData>
							<SimpleData name="MIN_INFER">N</SimpleData>
							<SimpleData name="GlobalID"></SimpleData>
						</SchemaData>
					</ExtendedData>
				</Placemark>
				<Placemark>
					<name>Private Hideaway</name>
					<Point>
						<gx:drawOrder>1</gx:drawOrder>
						<coordinates>-78.53953799999999,40.759938,0</coordinates>
					</Point>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Substations&quot;">
							<SimpleData name="NAME">Private Hideaway</SimpleData>
							<SimpleData name="OBJECTID"></SimpleData>
							<SimpleData name="ID"></SimpleData>
							<SimpleData name="CITY">COALPORT</SimpleData>
							<SimpleData name="STATE">PA</SimpleData>
							<SimpleData name="ZIP">16627</SimpleData>
							<SimpleData name="TYPE">DISTRIBUTION SUBSTATION</SimpleData>
							<SimpleData name="OWNER">UNKNOWN PRIVATE</SimpleData>
							<SimpleData name="STATUS">IN SERVICE</SimpleData>
							<SimpleData name="COUNTY">CLEARFIELD</SimpleData>
							<SimpleData name="COUNTYFIPS">42033</SimpleData>
							<SimpleData name="COUNTRY">USA</SimpleData>
							<SimpleData name="LATITUDE">40.759938</SimpleData>
							<SimpleData name="LONGITUDE">-78.53953799999999</SimpleData>
							<SimpleData name="NAICS_CODE">221121</SimpleData>
							<SimpleData name="NAICS_DESC">ELECTRIC BULK POWER TRANSMISSION AND CONTROL</SimpleData>
							<SimpleData name="SOURCE">IMAGERY</SimpleData>
							<SimpleData name="SOURCEDATE">2023/10/25</SimpleData>
							<SimpleData name="VAL_METHOD">IMAGERY</SimpleData>
							<SimpleData name="VAL_DATE">2023/10/25</SimpleData>
							<SimpleData name="LINES"></SimpleData>
							<SimpleData name="MAX_VOLT">-1</SimpleData>
							<SimpleData name="MIN_VOLT">-1</SimpleData>
							<SimpleData name="CAPACITY">-1</SimpleData>
							<SimpleData name="MAX_INFER">N</SimpleData>
							<SimpleData name="MIN_INFER">N</SimpleData>
							<SimpleData name="GlobalID"></SimpleData>
						</SchemaData>
					</ExtendedData>
				</Placemark>
			</Folder>
			<Folder>
				<name>Lines</name>
				<Placemark>
					<name>PA-CAMBRIA-L0001</name>
					<styleUrl>#sub_transmission</styleUrl>
					<LineString>
						<tessellate>1</tessellate>
						<coordinates>
						-78.76943638057332,40.49593595991323,0 -78.769713557893,40.49516517326612,0 -78.76984167411086,40.49441427002112,0 -78.77028633423393,40.49210741687307,0 -78.77073727608581,40.48987280390774,0 -78.76824557576954,40.48867325509222,0 -78.76570256517876,40.4875802697419,0 -78.76386696242115,40.48673137404788,0 -78.76264740614093,40.48626996675452,0 -78.76139339970467,40.48588330377842,0 -78.75989505684885,40.48530375959117,0 -78.75809065117382,40.48466019836901,0 -78.75586027883523,40.48385446215635,0 -78.75442393319999,40.48333844137476,0 -78.75313505619259,40.48288238882031,0 -78.74938378697281,40.48155781594809,0 -78.74682408883987,40.48162652950908,0 -78.74498402275982,40.48163312218308,0 -78.74215085549066,40.48165820795284,0 -78.73943903395669,40.48167134798436,0 -78.73763265694409,40.48170572065429,0 -78.73647777341831,40.48112578509861,0 -78.73582067263474,40.48081407374421,0 -78.73133420939004,40.48068364437479,0 -78.72827016238237,40.4808083356708,0 -78.72685012354187,40.48189693303355,0 
					</coordinates>
					</LineString>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Distribution_Lines&quot;">
							<SimpleData name="ID">PA-CAMBRIA-L0001</SimpleData>
							<SimpleData name="IOU">PENELEC</SimpleData>
							<SimpleData name="TYPE">SUB_TRANSMISSION</SimpleData>
							<SimpleData name="OWNER">PENELEC</SimpleData>
							<SimpleData name="VOLTAGE">34.5</SimpleData>
							<SimpleData name="VOLT_SOURCE">FERC</SimpleData>
							<SimpleData name="INFERRED">N</SimpleData>
							<SimpleData name="SUB">REVLOC</SimpleData>
							<SimpleData name="SUB_2">EBENSBURG</SimpleData>
							<SimpleData name="ANALYST">RC</SimpleData>
							<SimpleData name="VAL_DATE">2023/10/25</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
						</SchemaData>
					</ExtendedData>
				</Placemark>
				<Placemark>
					<name>PA-CAMBRIA-L0002</name>
					<styleUrl>#sub_transmission</styleUrl>
					<LineString>
						<tessellate>1</tessellate>
						<coordinates>
						-78.76943638057332,40.49593595991323,0 -78.769713557893,40.49516517326612,0 -78.76984167411086,40.49441427002112,0 -78.77028633423393,40.49210741687307,0 -78.77073727608581,40.48987280390774,0 -78.76824557576954,40.48867325509222,0 -78.76570256517876,40.4875802697419,0 -78.76386696242115,40.48673137404788,0 -78.76264740614093,40.48626996675452,0 -78.76139339970467,40.48588330377842,0 -78.75989505684885,40.48530375959117,0 -78.75809065117382,40.48466019836901,0 -78.75586027883523,40.48385446215635,0 -78.75442393319999,40.48333844137476,0 -78.75313505619259,40.48288238882031,0 -78.74938378697281,40.48155781594809,0 -78.74682408883987,40.48162652950908,0 -78.74498402275982,40.48163312218308,0 -78.74215085549066,40.48165820795284,0 -78.73943903395669,40.48167134798436,0 -78.73763265694409,40.48170572065429,0 -78.73647777341831,40.48112578509861,0 -78.73582067263474,40.48081407374421,0 -78.73133420939004,40.48068364437479,0 -78.72827016238237,40.4808083356708,0 -78.72685012354187,40.48189693303355,0 
					</coordinates>
					</LineString>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Distribution_Lines&quot;">
							<SimpleData name="ID">PA-CAMBRIA-L0002</SimpleData>
							<SimpleData name="IOU">PENELEC</SimpleData>
							<SimpleData name="TYPE">SUB_TRANSMISSION</SimpleData>
							<SimpleData name="OWNER">PENELEC</SimpleData>
							<SimpleData name="VOLTAGE">34.5</SimpleData>
							<SimpleData name="VOLT_SOURCE">FERC</SimpleData>
							<SimpleData name="INFERRED">N</SimpleData>
							<SimpleData name="SUB">REVLOC</SimpleData>
							<SimpleData name="SUB_2">EBENSBURG</SimpleData>
							<SimpleData name="ANALYST">RC</SimpleData>
							<SimpleData name="VAL_DATE">2023/10/25</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
						</SchemaData>
					</ExtendedData>
				</Placemark>
				<Placemark>
					<name>PA-CAMBRIA-L0003</name>
					<styleUrl>#sub_transmission</styleUrl>
					<LineString>
						<tessellate>1</tessellate>
						<coordinates>
						-78.76943638057332,40.49593595991323,0 -78.769713557893,40.49516517326612,0 -78.76984167411086,40.49441427002112,0 -78.77028633423393,40.49210741687307,0 -78.77073727608581,40.48987280390774,0 -78.76824557576954,40.48867325509222,0 -78.76570256517876,40.4875802697419,0 -78.76386696242115,40.48673137404788,0 -78.76264740614093,40.48626996675452,0 -78.76139339970467,40.48588330377842,0 -78.75989505684885,40.48530375959117,0 -78.75809065117382,40.48466019836901,0 -78.75586027883523,40.48385446215635,0 -78.75442393319999,40.48333844137476,0 -78.75313505619259,40.48288238882031,0 -78.74938378697281,40.48155781594809,0 -78.74682408883987,40.48162652950908,0 -78.74498402275982,40.48163312218308,0 -78.74215085549066,40.48165820795284,0 -78.73943903395669,40.48167134798436,0 -78.73763265694409,40.48170572065429,0 -78.73647777341831,40.48112578509861,0 -78.73582067263474,40.48081407374421,0 -78.73133420939004,40.48068364437479,0 -78.72827016238237,40.4808083356708,0 -78.72685012354187,40.48189693303355,0 
					</coordinates>
					</LineString>
					<ExtendedData>
						<SchemaData schemaUrl="&quot;#Distribution_Lines&quot;">
							<SimpleData name="ID">PA-CAMBRIA-L0003</SimpleData>
							<SimpleData name="IOU">PENELEC</SimpleData>
							<SimpleData name="TYPE">SUB_TRANSMISSION</SimpleData>
							<SimpleData name="OWNER">PENELEC</SimpleData>
							<SimpleData name="VOLTAGE">34.5</SimpleData>
							<SimpleData name="VOLT_SOURCE">FERC</SimpleData>
							<SimpleData name="INFERRED">N</SimpleData>
							<SimpleData name="SUB">REVLOC</SimpleData>
							<SimpleData name="SUB_2"></SimpleData>
							<SimpleData name="ANALYST">NU</SimpleData>
							<SimpleData name="VAL_DATE">2023/10/25</SimpleData>
							<SimpleData name="COUNTY">CAMBRIA</SimpleData>
							<SimpleData name="something random">random</SimpleData>
						</SchemaData>
					</ExtendedData>
				</Placemark>
			</Folder>
		</Folder>
	</Document>
</kml>"""
    root = et.fromstring(doc)
    tree = et.ElementTree(root)
    df = kmlToDF(root)
    dfToCSV(df, 'something')