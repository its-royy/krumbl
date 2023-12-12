import json
import re
import xml.etree.ElementTree as et
from collections import defaultdict
from datetime import date, datetime

import geopy.geocoders
import pandas as pd
import requests
from geopy.geocoders import Nominatim

import os

ns = {"kml": "http://www.opengis.net/kml/2.2"}
substationAcceptedInputs = [
    "NAME",
    "OBJECTID",
    "ID",
    "CITY",
    "STATE",
    "ZIP",
    "TYPE",
    "OWNER",
    "STATUS",
    "COUNTY",
    "COUNTYFIPS",
    "COUNTRY",
    "LATITUDE",
    "LONGITUDE",
    "NAICS_CODE",
    "NAICS_DESC",
    "SOURCE",
    "SOURCEDATE",
    "VAL_METHOD",
    "VAL_DATE",
    "LINES",
    "MAX_VOLT",
    "MIN_VOLT",
    "CAPACITY",
    "MAX_INFER",
    "MIN_INFER",
    "GlobalID",
]
lineAcceptedInputs = [
    "ID",
    "IOU",
    "TYPE",
    "OWNER",
    "VOLTAGE",
    "VOLT_SOURCE",
    "INFERRED",
    "SUB",
    "SUB_2",
    "ANALYST",
    "VAL_DATE",
    "COUNTY",
]
stateToAbbrev = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
    "district of columbia": "DC",
    "american samoa": "AS",
    "guam": "GU",
    "northern mariana islands": "MP",
    "puerto rico": "PR",
    "united states minor outlying islands": "UM",
    "u.s. virgin islands": "VI",
}
today = datetime.strftime(date.today(), r"%Y/%m/%d")

"""
error types:
mf = missing field
tmf = too many fields
ma = mislabeled attribute(s)
lt = line type
ln = line name
mn = mislabeled name
ep = empty point
"""

def handledirs(userId, action, fileName):
    cwd = os.getcwd()
    if os.path.exists(os.path.join(cwd, userId)):
        if os.path.exists(os.path.join(cwd, userId, action)):
            if os.path.exists(os.path.join(cwd, userId, action, fileName)):
                os.remove(os.path.join(cwd, userId, action, fileName))
        else:
            os.makedirs(os.path.join(cwd, userId, action))
    else:
        os.makedirs(os.path.join(cwd, userId, action))


def transform(root, revision=False):
    '''revision refers to if the client already submitted their kml and is now revising their errors'''
    unpassableErrors = 0
    errorStatements = []
    errorObjectList = []
    errors = 0
    fipsDF = pd.read_csv(
        "./utils/fips2county.txt",
        sep="\t",
        header="infer",
        dtype=str,
        encoding="latin-1",
    )
    stateCountyDF = fipsDF[["CountyFIPS", "CountyName", "StateName"]]
    # first parent county folder
    # root.findall() returns a list of all 'Folder' types
    for folder in root.findall(".//kml:Folder", ns):
        for folder_names in folder:  # subfolders (Substations, Lines)
            # generate substations - access substations folder
            if (
                folder_names.text.lower() == "substation"
                or folder_names.text.lower() == "substations"
            ):
                # all placemarks
                for placemark in folder.findall(".//kml:Placemark", ns):
                    objExc = placemark
                    styleUrl = placemark.find(".//kml:styleUrl", ns)
                    if styleUrl != None:
                        placemark.remove(styleUrl)
                    lookAt = placemark.find(".//kml:LookAt", ns)
                    if lookAt != None:
                        placemark.remove(lookAt)
                    if "(" in placemark.find(".//kml:name", ns).text:
                        for name in placemark.findall(".//kml:name", ns):
                            print(name.text)
                            substationName = re.search(
                                r"(^[A-Za-z0-9].*(?=\s\())|(^[A-Za-z0-9].*(?=\())",
                                name.text,
                            ).group(
                                0
                            )  # gets the name of line

                            try:
                                subInputs = re.search(r"\((.*)\)", name.text).group(0)
                            except AttributeError:
                                subInputs = re.search(r"\((.*)", name.text).group(0)
                                newMessage = f"{substationName} has an incorrect name. Please revise."
                                errorObjectList.append(
                                    {
                                        "name": placemark.find(".//kml:name", ns).text,
                                        "error": "Mislabeled Name",
                                        # "mn",
									}
                                )
                                errors += 1
                                continue
                            simpleDataList = (
                                re.search(r"(?<=\()(.*)(?=\))", name.text)
                                .group(0)
                                .split(",")
                            )  # gets the data within the parentheses
                            # parse through substation placemarks that already have ExtendedData
                            if placemark.find(".//kml:ExtendedData", ns) != None:
                                schemaDataAttrib = placemark.find(
                                    ".//kml:SchemaData", ns
                                )

                                # if user has names such as GIRARD (MAX_VOLT:13)
                                if ":" in name.text:
                                    # list of attributes that the existing placemark has in the kml
                                    attribList = [
                                        x.attrib["name"]
                                        for x in schemaDataAttrib.findall(
                                            ".//kml:SimpleData", ns
                                        )
                                    ]

                                    # check to see if all the inputs are valid inputs (all() in this case essentially checks for spelling errors)
                                    if all(
                                        fields.split(":")[0].strip().upper()
                                        in substationAcceptedInputs
                                        for fields in simpleDataList
                                    ):
                                        for field in simpleDataList:
                                            attribToChange = (
                                                field.split(":")[0].strip().upper()
                                            )
                                            newValue = field.split(":")[1].strip()

                                            # if the new attribute you're trying to add is in the list of accepted inputs and does not currently exist as an attribute in the placemark
                                            if (
                                                attribToChange
                                                in substationAcceptedInputs
                                                and schemaDataAttrib.find(
                                                    f".//kml:SimpleData[@name='{attribToChange}']",
                                                    ns,
                                                )
                                                == None
                                            ):
                                                attribToChangeElement = et.Element(
                                                    r"{http://www.opengis.net/kml/2.2}SimpleData",
                                                    attrib={
                                                        "name": f"{attribToChange}"
                                                    },
                                                )  # creates a new element for the attribute you're trying to add
                                                attribToChangeElement.text = newValue
                                                index = substationAcceptedInputs.index(
                                                    attribToChange
                                                )

                                                # goal of for loop below - check to see which previous attribute from the list of accepted inputs is existent in the placemark
                                                # EXAMPLE: GIRARD (CAPACITY:45, MAX_VOLT:69) -> CAPACITY AND MAX_VOLT ARE NOT CURRENTLY ATTRIBUTES IN THE PLACEMARK
                                                for i in range(index - 1, -1, -1):
                                                    # checks to see which previous attribute from the list of accepted inputs is existent in the placemark -> FOR CAPACITY, IT'S MIN_VOLT; FOR MAX_VOLT, IT'S LINES
                                                    if (
                                                        schemaDataAttrib.find(
                                                            f".//kml:SimpleData[@name='{substationAcceptedInputs[i]}']",
                                                            ns,
                                                        )
                                                        != None
                                                    ):
                                                        # gets the closest neighboring previous attribute that exists (I.E., MIN_VOLT, LINES)
                                                        neighboringAttrib = (
                                                            substationAcceptedInputs[i]
                                                        )
                                                        # gets the index of the closest neighboring previous attribute in the placemark
                                                        neighboringAttribIndex = (
                                                            attribList.index(
                                                                neighboringAttrib
                                                            )
                                                        )

                                                        # adds the new attribute ahead of the closest previous neighboring attribute in the placemark; it is +2 because you add a 'NAME' attribute in the beginning
                                                        schemaDataAttrib.insert(
                                                            neighboringAttribIndex + 1,
                                                            attribToChangeElement,
                                                        )

                                                        # adds the new attribute ahead of the closest previous neighboring attribute in the list of attributes for the existing placemark
                                                        attribList.insert(
                                                            neighboringAttribIndex + 1,
                                                            attribToChange,
                                                        )
                                                        break
                                                    else:
                                                        continue

                                            elif (
                                                schemaDataAttrib.find(
                                                    f".//kml:SimpleData[@name='{attribToChange}']",
                                                    ns,
                                                )
                                                != None
                                            ):
                                                schemaDataAttrib.find(
                                                    f".//kml:SimpleData[@name='{attribToChange}']",
                                                    ns,
                                                ).text = newValue
                                        name.text = substationName
                                    else:
                                        passable = False
                                        incorrectInputList = []
                                        for field in simpleDataList:
                                            attribToChange = (
                                                field.split(":")[0].strip().upper()
                                            )
                                            newValue = field.split(":")[1].strip()
                                            if (
                                                attribToChange
                                                not in substationAcceptedInputs
                                            ):
                                                incorrectInputList.append(
                                                    attribToChange
                                                )

                                        errorObjectList.append(
                                            {
                                                "name": placemark.find(".//kml:name", ns).text,
                                                "error": "Mislabeled Attribute(s)",
                                                # "ma",
                                            }
                                        )  # [placemark object, placemark name, errorType, parent name]
                                        errors += 1
                                # if user had all normal fields (e.g., GIRARD ((SOME CITY, D, AMEREN, 34.5, y, 12, y))
                                else:
                                    if len(simpleDataList) == 8:
                                        placemark.remove(
                                            placemark.find(".//kml:ExtendedData", ns)
                                        )

                                        coordinates = placemark.find(
                                            ".//kml:coordinates", ns
                                        ).text
                                        coordinatesList = coordinates.split(",")
                                        try:
                                            latitude = coordinatesList[1]
                                            longitude = coordinatesList[0]
                                        except IndexError:
                                            unpassableErrors += 1
                                            unpassableMessage = f"\n{name.text} is an empty substation point. Please add a point or delete the placemark from the KML."
                                            # unpassableStatements.append(
                                            #     unpassableMessage
                                            # )
                                            continue

                                        try:
                                            geolocator = Nominatim(user_agent="kmlHub")
                                            location = geolocator.reverse(
                                                latitude + "," + longitude,
                                                language="en",
                                            )
                                            address = location.raw["address"]
                                        except (
                                            geopy.exc.GeocoderServiceError
                                            or geopy.exc.GeocoderUnavailable
                                            or geopy.exc.GeocoderInsufficientPrivileges
                                        ):  # when the geopy servers are down, or whenever geopy runs into an error for some reason, directly use Nominatim API with requests
                                            url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json&accept-language=en&addressdetails=1"
                                            res = requests.get(url)
                                            j = res.json()
                                            address = j["address"]
                                        county = address.get("county", "")
                                        county = re.search(
                                            r".*(?=\sCounty)", county
                                        ).group(0)
                                        state = address.get("state", "")
                                        stateAbbrev = stateToAbbrev[state.lower()]
                                        zipCode = address.get("postcode", "")
                                        countyFIPS = stateCountyDF.loc[
                                            (stateCountyDF["CountyName"] == county)
                                            & (stateCountyDF["StateName"] == state),
                                            "CountyFIPS",
                                        ].values[0]

                                        objectID = schemaDataAttrib.find(
                                            f".//kml:SimpleData[@name='OBJECTID']",
                                            ns,
                                        ).text
                                        id = schemaDataAttrib.find(
                                            f".//kml:SimpleData[@name='ID']", ns
                                        ).text

                                        # creates new element 'ExtendedData'
                                        extendedData = et.Element(
                                            r"{http://www.opengis.net/kml/2.2}ExtendedData"
                                        )

                                        # inserts 'ExtendedData' element at index 3
                                        placemark.insert(3, extendedData)

                                        # creates subelement 'SchemaData' under 'ExtendedData'
                                        schemaData = et.SubElement(
                                            extendedData,
                                            r"{http://www.opengis.net/kml/2.2}SchemaData",
                                        )
                                        # create tag 'schemaUrl' with value '#Substations'
                                        schemaData.set("schemaUrl", '"#Substations"')
                                        # 'name' tag within placemark
                                        for name in placemark.findall(
                                            ".//kml:name", ns
                                        ):
                                            # creation of all attributes
                                            nameAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            nameAttrib.text = substationName
                                            nameAttrib.set("name", "NAME")

                                            objectIDAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            objectIDAttrib.text = objectID
                                            objectIDAttrib.set("name", "OBJECTID")

                                            idAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            idAttrib.text = id
                                            idAttrib.set("name", "ID")

                                            simpleDataCity = simpleDataList[0].strip()
                                            if simpleDataCity:
                                                # creates 'IOU' simpleData subelement
                                                cityAttrib = et.SubElement(
                                                    schemaData,
                                                    r"{http://www.opengis.net/kml/2.2}SimpleData",
                                                )
                                                cityAttrib.text = simpleDataCity
                                                cityAttrib.set("name", "CITY")
                                            else:
                                                cityAttrib = et.SubElement(
                                                    schemaData,
                                                    r"{http://www.opengis.net/kml/2.2}SimpleData",
                                                )
                                                cityAttrib.text = ""
                                                cityAttrib.set("name", "CITY")

                                            stateAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            stateAttrib.text = stateAbbrev
                                            stateAttrib.set("name", "STATE")

                                            zipAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            zipAttrib.text = zipCode
                                            zipAttrib.set("name", "ZIP")

                                            simpleDataSubstationType = (
                                                simpleDataList[1].strip().upper()
                                            )
                                            if simpleDataSubstationType:
                                                substationTypeAttrib = et.SubElement(
                                                    schemaData,
                                                    r"{http://www.opengis.net/kml/2.2}SimpleData",
                                                )
                                                if re.search(
                                                    r"^D", simpleDataSubstationType
                                                ):
                                                    substationTypeAttrib.text = (
                                                        "DISTRIBUTION SUBSTATION"
                                                    )
                                                elif re.search(
                                                    r"^S", simpleDataSubstationType
                                                ):
                                                    substationTypeAttrib.text = (
                                                        "SWITCHING STATION"
                                                    )
                                                else:
                                                    substationTypeAttrib.text = (
                                                        "TRANSMISSION SUBSTATION"
                                                    )
                                                substationTypeAttrib.set("name", "TYPE")

                                            simpleDataSubstationOwner = (
                                                simpleDataList[2].strip().upper()
                                            )
                                            if simpleDataSubstationOwner:
                                                # creates 'IOU' simpleData subelement
                                                substationOwner = et.SubElement(
                                                    schemaData,
                                                    r"{http://www.opengis.net/kml/2.2}SimpleData",
                                                )
                                                substationOwner.text = (
                                                    simpleDataSubstationOwner
                                                )
                                                substationOwner.set("name", "OWNER")
                                            else:
                                                iou = et.SubElement(
                                                    schemaData,
                                                    r"{http://www.opengis.net/kml/2.2}SimpleData",
                                                )
                                                iou.text = ""
                                                iou.set("name", "IOU")

                                            status = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            status.text = "IN SERVICE"
                                            status.set("name", "STATUS")

                                            countyAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            countyAttrib.text = county.upper()
                                            countyAttrib.set("name", "COUNTY")

                                            countyFIPSAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            countyFIPSAttrib.text = countyFIPS
                                            countyFIPSAttrib.set("name", "COUNTYFIPS")

                                            countryAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            countryAttrib.text = "USA"
                                            countryAttrib.set("name", "COUNTRY")

                                            latitideAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            latitideAttrib.text = latitude
                                            latitideAttrib.set("name", "LATITUDE")

                                            longitudeAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            longitudeAttrib.text = longitude
                                            longitudeAttrib.set("name", "LONGITUDE")

                                            naicsCodeAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            naicsCodeAttrib.text = "221121"
                                            naicsCodeAttrib.set("name", "NAICS_CODE")

                                            naicsDescAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            naicsDescAttrib.text = "ELECTRIC BULK POWER TRANSMISSION AND CONTROL"
                                            naicsDescAttrib.set("name", "NAICS_DESC")

                                            sourceAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            sourceAttrib.text = "IMAGERY"
                                            sourceAttrib.set("name", "SOURCE")

                                            sourceDateAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            sourceDateAttrib.text = str(today)
                                            sourceDateAttrib.set("name", "SOURCEDATE")

                                            valMethodAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            valMethodAttrib.text = "IMAGERY"
                                            valMethodAttrib.set("name", "VAL_METHOD")

                                            valDateAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            valDateAttrib.text = str(today)
                                            valDateAttrib.set("name", "VAL_DATE")

                                            linesAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            linesAttrib.text = ""
                                            linesAttrib.set("name", "LINES")

                                            simpleDataMaxVolt = simpleDataList[
                                                3
                                            ].strip()
                                            if simpleDataMaxVolt:
                                                maxVoltAttrib = et.SubElement(
                                                    schemaData,
                                                    r"{http://www.opengis.net/kml/2.2}SimpleData",
                                                )
                                                maxVoltAttrib.text = simpleDataMaxVolt
                                                maxVoltAttrib.set("name", "MAX_VOLT")

                                            simpleDataMinVolt = simpleDataList[
                                                5
                                            ].strip()
                                            if simpleDataMinVolt:
                                                minVoltAttrib = et.SubElement(
                                                    schemaData,
                                                    r"{http://www.opengis.net/kml/2.2}SimpleData",
                                                )
                                                minVoltAttrib.text = simpleDataMinVolt
                                                minVoltAttrib.set("name", "MIN_VOLT")

                                            simpleDataCapacity = simpleDataList[
                                                7
                                            ].strip()
                                            if simpleDataCapacity:
                                                capacityAttrib = et.SubElement(
                                                    schemaData,
                                                    r"{http://www.opengis.net/kml/2.2}SimpleData",
                                                )
                                                capacityAttrib.text = simpleDataCapacity
                                                capacityAttrib.set("name", "CAPACITY")

                                            simpleDataMaxInfer = (
                                                simpleDataList[4].strip().upper()
                                            )
                                            if simpleDataMinVolt:
                                                maxInferAttrib = et.SubElement(
                                                    schemaData,
                                                    r"{http://www.opengis.net/kml/2.2}SimpleData",
                                                )
                                                maxInferAttrib.text = simpleDataMaxInfer
                                                maxInferAttrib.set("name", "MAX_INFER")

                                            simpleDataMinInfer = (
                                                simpleDataList[6].strip().upper()
                                            )
                                            if simpleDataMinVolt:
                                                minInferAttrib = et.SubElement(
                                                    schemaData,
                                                    r"{http://www.opengis.net/kml/2.2}SimpleData",
                                                )
                                                minInferAttrib.text = simpleDataMinInfer
                                                minInferAttrib.set("name", "MIN_INFER")

                                            globalIDAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            globalIDAttrib.text = ""
                                            globalIDAttrib.set("name", "GlobalID")

                                        name.text = substationName

                                    elif len(simpleDataList) < 8:
                                        passable = False
                                        newMessage = f"\n{substationName} is missing a field(s). Please revise."
                                        errorStatements.append(newMessage)

                                        errorObjectList.append(
                                            {
                                                "name": placemark.find(".//kml:name", ns).text,
                                                "error": "Missing Field(s)",
                                                # "mf",
											}
                                        )  # [placemark object, placemark name, errorType, parent object]
                                        errors += 1
                                    else:
                                        passable = False
                                        newMessage = f"\n{substationName} has too many fields. Please revise."
                                        errorStatements.append(newMessage)

                                        errorObjectList.append(
                                            {
                                                "name": placemark.find(".//kml:name", ns).text,
                                                "error": "Too Many Field(s)",
                                                # "tmf",
											}
                                        )  # [placemark object, placemark name, errorType, parent object]
                                        errors += 1
                            # parse through substation placemarks that do not have any ExtendedData
                            else:
                                if len(simpleDataList) == 8:
                                    coordinates = placemark.find(
                                        ".//kml:coordinates", ns
                                    ).text
                                    coordinatesList = coordinates.split(",")
                                    try:
                                        latitude = coordinatesList[1]
                                        longitude = coordinatesList[0]
                                    except IndexError:
                                        unpassableErrors += 1
                                        unpassableMessage = f"\n{name.text} is an empty substation point. Please add a point or delete the placemark from the KML."
                                        errorObjectList.append(
                                            {
                                                "name": placemark.find(".//kml:name", ns).text,
                                                "error": "Missing Field(s)",
                                                # "mf",
											}
                                        )
                                        continue
                                    # geolocator = Nominatim(
                                    #     user_agent='kmlHub')
                                    # location = geolocator.reverse(
                                    #     latitude+','+longitude, language='en')
                                    # print(location)
                                    # address = location.raw['address']
                                    try:
                                        # raise geopy.exc.GeocoderServiceError
                                        geolocator = Nominatim(user_agent="kmlHub")
                                        location = geolocator.reverse(
                                            latitude + "," + longitude, language="en"
                                        )
                                        address = location.raw["address"]
                                    except (
                                        geopy.exc.GeocoderServiceError
                                        or geopy.exc.GeocoderUnavailable
                                        or geopy.exc.GeocoderInsufficientPrivileges
                                    ):  # when the geopy servers are down, or whenever geopy runs into an error for some reason, directly use Nominatim API with requests
                                        url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json&accept-language=en&addressdetails=1"
                                        res = requests.get(url)
                                        j = res.json()
                                        address = j["address"]
                                    # returns a value like 'Monroe Country'
                                    county = address.get("county", "")
                                    county = re.search(r".*(?=\sCounty)", county).group(
                                        0
                                    )
                                    state = address.get("state", "")
                                    stateAbbrev = stateToAbbrev[state.lower()]
                                    zipCode = address.get("postcode", "")
                                    countyFIPS = stateCountyDF.loc[
                                        (stateCountyDF["CountyName"] == county)
                                        & (stateCountyDF["StateName"] == state),
                                        "CountyFIPS",
                                    ].values[0]

                                    # creates new element 'ExtendedData'
                                    extendedData = et.Element(
                                        r"{http://www.opengis.net/kml/2.2}ExtendedData"
                                    )
                                    # inserts 'ExtendedData' element at index 3
                                    placemark.insert(3, extendedData)
                                    # creates subelement 'SchemaData' under 'ExtendedData'
                                    schemaData = et.SubElement(
                                        extendedData,
                                        r"{http://www.opengis.net/kml/2.2}SchemaData",
                                    )
                                    # create tag 'schemaUrl' with value '#Substations'
                                    schemaData.set("schemaUrl", '"#Substations"')
                                    # 'name' tag within placemark
                                    for name in placemark.findall(".//kml:name", ns):
                                        substationName = re.search(
                                            r"(^[A-Za-z0-9].*(?=\s\())|(^[A-Za-z0-9].*(?=\())",
                                            name.text,
                                        ).group(
                                            0
                                        )  # gets the name of line
                                        simpleDataList = (
                                            re.search(r"(?<=\()(.*)(?=\))", name.text)
                                            .group(0)
                                            .split(",")
                                        )  # gets the data within the parentheses

                                        # creation of all attributes
                                        nameAttrib = et.SubElement(
                                            schemaData,
                                            r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        )
                                        nameAttrib.text = substationName
                                        nameAttrib.set("name", "NAME")

                                        objectIDAttrib = et.SubElement(
                                            schemaData,
                                            r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        )
                                        objectIDAttrib.text = ""
                                        objectIDAttrib.set("name", "OBJECTID")

                                        idAttrib = et.SubElement(
                                            schemaData,
                                            r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        )
                                        idAttrib.text = ""
                                        idAttrib.set("name", "ID")

                                        simpleDataCity = simpleDataList[0].strip()
                                        if simpleDataCity:
                                            # creates 'IOU' simpleData subelement
                                            cityAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            cityAttrib.text = simpleDataCity
                                            cityAttrib.set("name", "CITY")
                                        else:
                                            cityAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            cityAttrib.text = ""
                                            cityAttrib.set("name", "CITY")

                                        stateAttrib = et.SubElement(
                                            schemaData,
                                            r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        )
                                        stateAttrib.text = stateAbbrev
                                        stateAttrib.set("name", "STATE")

                                        zipAttrib = et.SubElement(
                                            schemaData,
                                            r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        )
                                        zipAttrib.text = zipCode
                                        zipAttrib.set("name", "ZIP")

                                        simpleDataSubstationType = (
                                            simpleDataList[1].strip().upper()
                                        )
                                        if simpleDataSubstationType:
                                            substationTypeAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            if re.search(
                                                r"^D", simpleDataSubstationType
                                            ):
                                                substationTypeAttrib.text = (
                                                    "DISTRIBUTION SUBSTATION"
                                                )
                                            elif re.search(
                                                r"^S", simpleDataSubstationType
                                            ):
                                                substationTypeAttrib.text = (
                                                    "SWITCHING STATION"
                                                )
                                            else:
                                                substationTypeAttrib.text = (
                                                    "TRANSMISSION SUBSTATION"
                                                )
                                            substationTypeAttrib.set("name", "TYPE")

                                        simpleDataSubstationOwner = (
                                            simpleDataList[2].strip().upper()
                                        )
                                        if simpleDataSubstationOwner:
                                            substationOwner = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            substationOwner.text = (
                                                simpleDataSubstationOwner
                                            )
                                            substationOwner.set("name", "OWNER")
                                        else:
                                            iou = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            iou.text = ""
                                            iou.set("name", "IOU")

                                        status = et.SubElement(
                                            schemaData,
                                            r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        )
                                        status.text = "IN SERVICE"
                                        status.set("name", "STATUS")

                                        countyAttrib = et.SubElement(
                                            schemaData,
                                            r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        )
                                        countyAttrib.text = county.upper()
                                        countyAttrib.set("name", "COUNTY")

                                        countyFIPSAttrib = et.SubElement(
                                            schemaData,
                                            r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        )
                                        countyFIPSAttrib.text = countyFIPS
                                        countyFIPSAttrib.set("name", "COUNTYFIPS")

                                        countryAttrib = et.SubElement(
                                            schemaData,
                                            r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        )
                                        countryAttrib.text = "USA"
                                        countryAttrib.set("name", "COUNTRY")

                                        latitideAttrib = et.SubElement(
                                            schemaData,
                                            r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        )
                                        latitideAttrib.text = latitude
                                        latitideAttrib.set("name", "LATITUDE")

                                        longitudeAttrib = et.SubElement(
                                            schemaData,
                                            r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        )
                                        longitudeAttrib.text = longitude
                                        longitudeAttrib.set("name", "LONGITUDE")

                                        naicsCodeAttrib = et.SubElement(
                                            schemaData,
                                            r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        )
                                        naicsCodeAttrib.text = "221121"
                                        naicsCodeAttrib.set("name", "NAICS_CODE")

                                        naicsDescAttrib = et.SubElement(
                                            schemaData,
                                            r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        )
                                        naicsDescAttrib.text = "ELECTRIC BULK POWER TRANSMISSION AND CONTROL"
                                        naicsDescAttrib.set("name", "NAICS_DESC")

                                        sourceAttrib = et.SubElement(
                                            schemaData,
                                            r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        )
                                        sourceAttrib.text = "IMAGERY"
                                        sourceAttrib.set("name", "SOURCE")

                                        sourceDateAttrib = et.SubElement(
                                            schemaData,
                                            r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        )
                                        sourceDateAttrib.text = str(today)
                                        sourceDateAttrib.set("name", "SOURCEDATE")

                                        valMethodAttrib = et.SubElement(
                                            schemaData,
                                            r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        )
                                        valMethodAttrib.text = "IMAGERY"
                                        valMethodAttrib.set("name", "VAL_METHOD")

                                        valDateAttrib = et.SubElement(
                                            schemaData,
                                            r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        )
                                        valDateAttrib.text = str(today)
                                        valDateAttrib.set("name", "VAL_DATE")

                                        linesAttrib = et.SubElement(
                                            schemaData,
                                            r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        )
                                        linesAttrib.text = ""
                                        linesAttrib.set("name", "LINES")

                                        simpleDataMaxVolt = simpleDataList[3].strip()
                                        if simpleDataMaxVolt:
                                            maxVoltAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            maxVoltAttrib.text = simpleDataMaxVolt
                                            maxVoltAttrib.set("name", "MAX_VOLT")

                                        simpleDataMinVolt = simpleDataList[5].strip()
                                        if simpleDataMinVolt:
                                            minVoltAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            minVoltAttrib.text = simpleDataMinVolt
                                            minVoltAttrib.set("name", "MIN_VOLT")

                                        simpleDataCapacity = simpleDataList[7].strip()
                                        if simpleDataCapacity:
                                            capacityAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            capacityAttrib.text = simpleDataCapacity
                                            capacityAttrib.set("name", "CAPACITY")

                                        simpleDataMaxInfer = (
                                            simpleDataList[4].strip().upper()
                                        )
                                        if simpleDataMinVolt:
                                            maxInferAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            maxInferAttrib.text = simpleDataMaxInfer
                                            maxInferAttrib.set("name", "MAX_INFER")

                                        simpleDataMinInfer = (
                                            simpleDataList[6].strip().upper()
                                        )
                                        if simpleDataMinVolt:
                                            minInferAttrib = et.SubElement(
                                                schemaData,
                                                r"{http://www.opengis.net/kml/2.2}SimpleData",
                                            )
                                            minInferAttrib.text = simpleDataMinInfer
                                            minInferAttrib.set("name", "MIN_INFER")

                                        globalIDAttrib = et.SubElement(
                                            schemaData,
                                            r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        )
                                        globalIDAttrib.text = ""
                                        globalIDAttrib.set("name", "GlobalID")
                                    name.text = substationName
                                elif len(simpleDataList) < 8:
                                    passable = False
                                    newMessage = f"\n{substationName} is missing a field(s). Please revise."
                                    errorStatements.append(newMessage)
                                    errorObjectList.append(
                                        {
                                            "name": placemark.find(".//kml:name", ns).text,
                                            "error": "Missing Field(s)",
                                            # "mf",
                                        }
                                    )
                                    errors += 1
                                else:
                                    passable = False
                                    newMessage = f"\n{substationName} has too many fields. Please revise."
                                    errorStatements.append(newMessage)
                                    errorObjectList.append(
                                        {
                                            "name": placemark.find(".//kml:name", ns).text,
                                            "error": "Too Many Field(s)",
                                            # "tmf",
										}
                                    )
                                    errors += 1
                    else:
                        if not revision:    
                            for schemaData in placemark.findall(".//kml:SchemaData", ns):
                                # create tag 'schemaUrl' with value '#Substations'
                                schemaData.set("schemaUrl", '"#Substations"')
            # generate lines - access lines folder
            if "line" in folder_names.text.lower():
                # all placemarks
                for placemark in folder.findall(".//kml:Placemark", ns):
                    objExc = placemark
                    if "(" in placemark.find(".//kml:name", ns).text:
                        name = placemark.find(".//kml:name", ns)
                        print(name.text)
                        lineName = re.search(
                            r"(^[A-Za-z0-9-]*(?=\s\())|(^[A-Za-z0-9-]*(?=\())",
                            name.text,
                        ).group(
                            0
                        )  # gets the name of line

                        try:
                            lineInputs = re.search(r"\((.*)\)", name.text).group(0)
                        except AttributeError:
                            lineInputs = re.search(r"\((.*)", name.text).group(0)
                            newMessage = (
                                f"{lineName} has an incorrect name. Please revise."
                            )
                            errorObjectList.append(
                                {
                                    "name": placemark.find(".//kml:name", ns).text,
                                    "error": "Mislabeled Name",
                                    # "mn",
                                }
                            )
                            errors += 1
                            continue

                        if placemark.find(".//kml:ExtendedData", ns) != None:
                            schemaData = placemark.find(r".//kml:SchemaData", ns)

                            simpleDataList = (
                                re.search(r"(?<=\()(.*)(?=\))", name.text)
                                .group(0)
                                .split(",")
                            )  # gets the data within the parentheses
                            if len(simpleDataList) == 7:
                                simpleDataIOU = simpleDataList[0].strip()
                                if simpleDataIOU:
                                    # creates 'IOU' simpleData subelement
                                    iou = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    iou.text = simpleDataIOU
                                    iou.set("name", "IOU")
                                else:
                                    iou = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    iou.text = simpleDataIOU
                                    iou.set("name", "IOU")

                                simpleDataLineType = simpleDataList[1].strip().lower()
                                if simpleDataLineType:
                                    lineType = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )  # creates 'IOU' simpleData subelement
                                    lineType.set("name", "TYPE")
                                    distribution = re.search(r"^d", simpleDataLineType)
                                    sub_transmission = re.search(
                                        r"^(s|m)", simpleDataLineType
                                    )
                                    transmission = re.search(r"^t", simpleDataLineType)
                                    # changes styleUrl text (aka, line color) based on the 'TYPE' value
                                    if distribution:
                                        placemark.find(
                                            ".//kml:styleUrl", ns
                                        ).text = "#distribution"
                                        lineType.text = "DISTRIBUTION"
                                    elif sub_transmission:
                                        placemark.find(
                                            ".//kml:styleUrl", ns
                                        ).text = "#sub_transmission"
                                        lineType.text = "SUB_TRANSMISSION"
                                    elif transmission:
                                        placemark.find(
                                            ".//kml:styleUrl", ns
                                        ).text = "#transmission"
                                        lineType.text = "TRANSMISSION"
                                    else:
                                        placemark.find(
                                            ".//kml:styleUrl", ns
                                        ).text = "#unknown"
                                        lineType.text = "UNKNOWN"
                                        newMessage = f"{lineName} has an incorrect line type. Please revise."
                                        errorStatements.append(newMessage)
                                        errorObjectList.append(
                                            {
                                                "name": placemark.find(".//kml:name", ns).text,
                                                "error": "Line Type",
                                                # "lt",
											}
                                        )
                                        errors += 1
                                simpleDataOwner = simpleDataList[2].strip()
                                if simpleDataOwner:
                                    # creates 'OWNER' simpleData subelement
                                    owner = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    owner.text = simpleDataOwner
                                    owner.set("name", "OWNER")
                                else:
                                    owner = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    owner.text = ""
                                    owner.set("name", "OWNER")

                                simpleDataVoltage = simpleDataList[3].strip()
                                # creates 'VOLTAGE' simpleData subelement
                                if (
                                    simpleDataVoltage != "-1"
                                    and simpleDataVoltage != ""
                                    and simpleDataVoltage != " "
                                ):
                                    voltage = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    voltage.text = simpleDataVoltage
                                    voltage.set("name", "VOLTAGE")
                                    # creates 'VOLT_SOURCE' simpleData subelement
                                    voltageSource = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    # if "VOLTAGE" has some value other than -1 or empty string, make VOLT_SOURCE text 'HIFLD'
                                    voltageSource.text = "FERC"
                                    voltageSource.set("name", "VOLT_SOURCE")
                                    # creates 'INFERRED' simpleData subelement
                                    infer = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    infer.text = "N"
                                    infer.set("name", "INFERRED")
                                else:
                                    voltage = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    voltage.text = "-1"
                                    voltage.set("name", "VOLTAGE")
                                    voltageSource = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    # if "VOLTAGE" is -1, make VOLT_SOURCE text 'IMAGERY'
                                    voltageSource.text = "IMAGERY"
                                    voltageSource.set("name", "VOLT_SOURCE")
                                    infer = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    infer.text = "Y"
                                    infer.set("name", "INFERRED")

                                simpleDataSub1 = simpleDataList[4].strip()
                                if simpleDataSub1:
                                    # creates 'SUB' simpleData subelement
                                    sub1 = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    sub1.text = simpleDataSub1
                                    sub1.set("name", "SUB")
                                else:
                                    # creates 'SUB' simpleData subelement
                                    sub1 = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    sub1.text = ""
                                    sub1.set("name", "SUB")

                                simpleDataSub2 = simpleDataList[5].strip()
                                if simpleDataSub2:
                                    # creates 'SUB_2' simpleData subelement
                                    sub2 = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    sub2.text = simpleDataSub2
                                    sub2.set("name", "SUB_2")
                                else:
                                    sub2 = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    sub2.text = ""  # need to manually set the text to an empty string, else the attribute completely disappears in kml
                                    sub2.set("name", "SUB_2")

                                simpleDataAnalyst = simpleDataList[6].strip()
                                if simpleDataAnalyst:
                                    # creates 'ANALYST' simpleData subelement
                                    analyst = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    analyst.text = simpleDataAnalyst
                                    analyst.set("name", "ANALYST")
                                else:
                                    analyst = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    analyst.text = ""
                                    analyst.set("name", "ANALYST")

                                # creates 'VAL_DATE' simpleData subelement
                                val_date = et.SubElement(
                                    schemaData,
                                    r"{http://www.opengis.net/kml/2.2}SimpleData",
                                )
                                val_date.text = str(today)
                                val_date.set("name", "VAL_DATE")

                                # creates 'COUNTY' simpleData subelement
                                lineCounty = et.SubElement(
                                    schemaData,
                                    r"{http://www.opengis.net/kml/2.2}SimpleData",
                                )
                                lineCounty.set("name", "COUNTY")
                                coordinates = placemark.find(
                                    ".//kml:coordinates", ns
                                ).text
                                coordinatesList = coordinates.split(",")
                                try:
                                    latitude = coordinatesList[1]
                                    longitude = coordinatesList[0]
                                except IndexError:
                                    unpassableErrors += 1
                                    unpassableMessage = f"\n{name.text} is an empty line with no points. Please draw a line or delete the line from the KML."
                                    errorObjectList.append(
                                        {
                                            "name": placemark.find(".//kml:name", ns).text,
                                            "error": "Missing Field(s)",
                                            # "mf",
										}
                                    )
                                    continue
                                # geolocator = Nominatim(
                                #     user_agent='kmlHub')
                                # location = geolocator.reverse(
                                #     latitude+','+longitude, language='en')
                                # print(location)
                                # address = location.raw['address']
                                try:
                                    # raise geopy.exc.GeocoderServiceError
                                    geolocator = Nominatim(user_agent="kmlHub")
                                    location = geolocator.reverse(
                                        latitude + "," + longitude, language="en"
                                    )
                                    address = location.raw["address"]
                                except (
                                    geopy.exc.GeocoderServiceError
                                    or geopy.exc.GeocoderUnavailable
                                    or geopy.exc.GeocoderInsufficientPrivileges
                                ):  # when the geopy servers are down, or whenever geopy runs into an error for some reason, directly use Nominatim API with requests
                                    url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json&accept-language=en&addressdetails=1"
                                    res = requests.get(url)
                                    j = res.json()
                                    address = j["address"]
                                county = address.get("county", "").upper()
                                county = re.search(r".*(?=\sCOUNTY)", county).group(0)
                                lineCounty.text = county.upper()

                                placemark.find(".//kml:name", ns).text = lineName
                            elif len(simpleDataList) < 7:
                                newMessage = f"\n{lineName} is missing a field(s). Please revise."
                                errorStatements.append(newMessage)
                                errorObjectList.append(
                                    {
                                        "name": placemark.find(".//kml:name", ns).text,
                                        "error": "Missing Field(s)",
                                        # "mf",
                                    }
                                )
                                errors += 1
                            else:
                                newMessage = (
                                    f"\n{lineName} has too many fields. Please revise."
                                )
                                errorStatements.append(newMessage)
                                errorObjectList.append(
                                    {
                                        "name": placemark.find(".//kml:name", ns).text,
                                        "error": "Too Many Field(s)",
                                        # "tmf",
                                    }
                                )
                                errors += 1
                        else:
                            # creates new element 'ExtendedData'
                            extendedData = et.Element(
                                r"{http://www.opengis.net/kml/2.2}ExtendedData"
                            )
                            # inserts 'ExtendedData' element at index 3
                            placemark.insert(3, extendedData)
                            # creates subelement 'SchemaData' under 'ExtendedData'
                            schemaData = et.SubElement(
                                extendedData,
                                r"{http://www.opengis.net/kml/2.2}SchemaData",
                            )
                            # create tag 'schemaUrl' with value '#Distribution_Lines'
                            schemaData.set("schemaUrl", '"#Distribution_Lines"')
                            # 'name' tag within placemark

                            if (
                                lineName
                                and placemark.find('.//kml:SimpleData[@name="ID"]', ns)
                                == None
                            ):
                                # creates 'ID' simpleData subelement
                                id = et.SubElement(
                                    schemaData,
                                    r"{http://www.opengis.net/kml/2.2}SimpleData",
                                )
                                id.text = lineName
                                id.set("name", "ID")

                            simpleDataList = (
                                re.search(r"(?<=\()(.*)(?=\))", name.text)
                                .group(0)
                                .split(",")
                            )  # gets the data within the parentheses

                            if len(simpleDataList) == 7:
                                simpleDataIOU = simpleDataList[0].strip()
                                if simpleDataIOU:
                                    # creates 'IOU' simpleData subelement
                                    iou = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    iou.text = simpleDataIOU
                                    iou.set("name", "IOU")
                                else:
                                    iou = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    iou.text = simpleDataIOU
                                    iou.set("name", "IOU")

                                simpleDataLineType = simpleDataList[1].strip().lower()
                                if simpleDataLineType:
                                    lineType = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )  # creates 'IOU' simpleData subelement
                                    lineType.set("name", "TYPE")
                                    distribution = re.search(r"^d", simpleDataLineType)
                                    sub_transmission = re.search(
                                        r"^(s|m)", simpleDataLineType
                                    )
                                    transmission = re.search(r"^t", simpleDataLineType)
                                    # changes styleUrl text (aka, line color) based on the 'TYPE' value
                                    if distribution:
                                        placemark.find(
                                            ".//kml:styleUrl", ns
                                        ).text = "#distribution"
                                        lineType.text = "DISTRIBUTION"
                                    elif sub_transmission:
                                        placemark.find(
                                            ".//kml:styleUrl", ns
                                        ).text = "#sub_transmission"
                                        lineType.text = "SUB_TRANSMISSION"
                                    elif transmission:
                                        placemark.find(
                                            ".//kml:styleUrl", ns
                                        ).text = "#transmission"
                                        lineType.text = "TRANSMISSION"
                                    else:
                                        placemark.find(
                                            ".//kml:styleUrl", ns
                                        ).text = "#unknown"
                                        lineType.text = "UNKNOWN"
                                        newMessage = f"{lineName} has an incorrect line type. Please revise."
                                        errorStatements.append(newMessage)
                                        errorObjectList.append(
                                            {
                                                "name": placemark.find(".//kml:name", ns).text,
                                                "error": "Line Type",
                                                # "lt",
											}
                                        )
                                        errors += 1
                                simpleDataOwner = simpleDataList[2].strip()
                                if simpleDataOwner:
                                    # creates 'OWNER' simpleData subelement
                                    owner = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    owner.text = simpleDataOwner
                                    owner.set("name", "OWNER")
                                else:
                                    owner = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    owner.text = ""
                                    owner.set("name", "OWNER")

                                simpleDataVoltage = simpleDataList[3].strip()
                                # creates 'VOLTAGE' simpleData subelement
                                if (
                                    simpleDataVoltage != "-1"
                                    and simpleDataVoltage != ""
                                    and simpleDataVoltage != " "
                                ):
                                    voltage = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    voltage.text = simpleDataVoltage
                                    voltage.set("name", "VOLTAGE")
                                    # creates 'VOLT_SOURCE' simpleData subelement
                                    voltageSource = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    # if "VOLTAGE" has some value other than -1 or empty string, make VOLT_SOURCE text 'HIFLD'
                                    voltageSource.text = "FERC"
                                    voltageSource.set("name", "VOLT_SOURCE")
                                    # creates 'INFERRED' simpleData subelement
                                    infer = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    infer.text = "N"
                                    infer.set("name", "INFERRED")
                                else:
                                    voltage = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    voltage.text = "-1"
                                    voltage.set("name", "VOLTAGE")
                                    voltageSource = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    # if "VOLTAGE" is -1, make VOLT_SOURCE text 'IMAGERY'
                                    voltageSource.text = "IMAGERY"
                                    voltageSource.set("name", "VOLT_SOURCE")
                                    infer = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    infer.text = "Y"
                                    infer.set("name", "INFERRED")

                                simpleDataSub1 = simpleDataList[4].strip()
                                if simpleDataSub1:
                                    # creates 'SUB' simpleData subelement
                                    sub1 = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    sub1.text = simpleDataSub1
                                    sub1.set("name", "SUB")
                                else:
                                    # creates 'SUB' simpleData subelement
                                    sub1 = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    sub1.text = ""
                                    sub1.set("name", "SUB")

                                simpleDataSub2 = simpleDataList[5].strip()
                                if simpleDataSub2:
                                    # creates 'SUB_2' simpleData subelement
                                    sub2 = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    sub2.text = simpleDataSub2
                                    sub2.set("name", "SUB_2")
                                else:
                                    sub2 = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    sub2.text = ""  # need to manually set the text to an empty string, else the attribute completely disappears in kml
                                    sub2.set("name", "SUB_2")

                                simpleDataAnalyst = simpleDataList[6].strip()
                                if simpleDataAnalyst:
                                    # creates 'ANALYST' simpleData subelement
                                    analyst = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    analyst.text = simpleDataAnalyst
                                    analyst.set("name", "ANALYST")
                                else:
                                    analyst = et.SubElement(
                                        schemaData,
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                    )
                                    analyst.text = ""
                                    analyst.set("name", "ANALYST")

                                # creates 'VAL_DATE' simpleData subelement
                                val_date = et.SubElement(
                                    schemaData,
                                    r"{http://www.opengis.net/kml/2.2}SimpleData",
                                )
                                val_date.text = str(today)
                                val_date.set("name", "VAL_DATE")

                                # creates 'COUNTY' simpleData subelement
                                lineCounty = et.SubElement(
                                    schemaData,
                                    r"{http://www.opengis.net/kml/2.2}SimpleData",
                                )
                                lineCounty.set("name", "COUNTY")
                                coordinates = placemark.find(
                                    ".//kml:coordinates", ns
                                ).text
                                coordinatesList = coordinates.split(",")
                                try:
                                    latitude = coordinatesList[1]
                                    longitude = coordinatesList[0]
                                except IndexError:
                                    unpassableErrors += 1
                                    unpassableMessage = f"\n{name.text} is an empty line with no points. Please draw a line or delete the line from the KML."
                                    # unpassableStatements.append(unpassableMessage)
                                    continue
                                try:
                                    # raise geopy.exc.GeocoderServiceError
                                    geolocator = Nominatim(user_agent="kmlHub")
                                    location = geolocator.reverse(
                                        latitude + "," + longitude, language="en"
                                    )
                                    address = location.raw["address"]
                                except (
                                    geopy.exc.GeocoderServiceError
                                    or geopy.exc.GeocoderUnavailable
                                    or geopy.exc.GeocoderInsufficientPrivileges
                                ):  # when the geopy servers are down, or whenever geopy runs into an error for some reason, directly use Nominatim API with requests
                                    url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json&accept-language=en&addressdetails=1"
                                    res = requests.get(url)
                                    j = res.json()
                                    address = j["address"]
                                county = address.get("county", "").upper()
                                county = re.search(r".*(?=\sCOUNTY)", county).group(0)
                                lineCounty.text = county.upper()
                                name.text = lineName
                            elif len(simpleDataList) < 7:
                                newMessage = f"\n{lineName} is missing a field(s). Please revise."
                                errorStatements.append(newMessage)
                                errorObjectList.append(
                                    {
                                        "name": placemark.find(".//kml:name", ns).text,
                                        "error": "Missing Field(s)",
                                        # "mf",
                                    }
                                )
                                errors += 1
                            else:
                                newMessage = (
                                    f"\n{lineName} has too many fields. Please revise."
                                )
                                errorStatements.append(newMessage)
                                errorObjectList.append(
                                    {
                                        "name": placemark.find(".//kml:name", ns).text,
                                        "error": "Too Many Field(s)",
                                        # "tmf",
									}
                                )
                                errors += 1
                    else:
                        if not revision:
                            for styleUrl in placemark.findall(".//kml:styleUrl", ns):
                                styleUrlText = styleUrl.text
                                styleUrl.text = re.sub(r"\d+", "", styleUrlText)
                            for schemaData in placemark.findall(".//kml:SchemaData", ns):
                                # create tag 'schemaUrl' with value '#Distribution_Lines'
                                schemaData.set("schemaUrl", '"#Distribution_Lines"')
    return root, unpassableErrors, errors, errorObjectList


def kmlToDF(root):
    if root == None:
        pass
    else:
        try:
            root = root
            dfMajorMessages = []
            dfMinorMessages = []
            linesData = defaultdict(list)
            # first folder (Trumbull)
            for folder in root.findall(".//kml:Folder", ns):
                for (
                    folder_names
                ) in folder:  # all children including name, open, and any subfolders
                    if "line" in folder_names.text.lower():
                        # accessing SimpleData layer within each placemark
                        for line in folder.findall(".//kml:Placemark", ns):
                            name = line.find(".//kml:name", ns).text
                            __currentState = name.split("-")[
                                0
                            ].lower()  # WILL NEED TO CHANGE THIS IN THE FUTURE, THIS ITERATES OVER ALL PLACEMARKS AND CONSTANTLY CHANGES, WHICH IS UNNECESSARY
                            for child in line.findall(".//kml:SimpleData", ns):
                                if (
                                    child.text == None
                                ):  # if SimpleData has a null or None value, replace it with an empty string
                                    child.text = ""
                                for (
                                    _,
                                    value,
                                ) in (
                                    child.attrib.items()
                                ):  # values = ID, IOU, TYPE, STATUS, VAL_METHOD, ETC
                                    # appends based on SimpleData name => linesData['ID'], linesData['IOU']; child.text  is the text of each value => OH-TRUM-L0001
                                    linesData[value].append(child.text)
                            attribList = [
                                x.attrib["name"]
                                for x in line.findall(".//kml:SimpleData", ns)
                            ]
                            current = set(attribList)
                            original = set(lineAcceptedInputs)
                            missing = list(original - current)
                            if len(attribList) < 12:
                                if "COUNTY" in missing:
                                    schemaDataAttrib = line.find(
                                        ".//kml:SchemaData", ns
                                    )
                                    coordinates = line.find(
                                        ".//kml:coordinates", ns
                                    ).text
                                    coordinatesList = coordinates.split(" ")
                                    coordinates = coordinatesList[0].split(",")
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
                                        geolocator = Nominatim(user_agent="kmlHub")
                                        location = geolocator.reverse(
                                            latitude + "," + longitude,
                                            language="en",
                                        )
                                        address = location.raw["address"]
                                    except (
                                        geopy.exc.GeocoderServiceError
                                        or geopy.exc.GeocoderUnavailable
                                        or geopy.exc.GeocoderInsufficientPrivileges
                                    ):  # when the geopy servers are down, or whenever geopy runs into an error for some reason, directly use Nominatim API with requests
                                        url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json&accept-language=en&addressdetails=1"
                                        res = requests.get(url)
                                        j = res.json()
                                        address = j["address"]
                                    county = address.get("county", "").upper()
                                    county = re.search(r".*(?=\sCOUNTY)", county).group(
                                        0
                                    )
                                    countyAttrib = et.Element(
                                        r"{http://www.opengis.net/kml/2.2}SimpleData",
                                        attrib={"name": "COUNTY"},
                                    )
                                    countyAttrib.text = county.upper()
                                    schemaDataAttrib.insert(
                                        len(attribList) + 1, countyAttrib
                                    )
                                    linesData["COUNTY"].append(county.upper())
                                    minorErrors += 1
                                if len(missing) == 1 and "".join(missing) == "COUNTY":
                                    dfMinorMessages.append(
                                        f'"{name}" is missing {12 - len(attribList)} attribute(s): {", ".join(missing)}. The "COUNTY" attribute has been automatically filled in for you.\n'
                                    )
                                elif len(missing) != 1 and "COUNTY" in missing:
                                    errors += 1
                                    dfMajorMessages.append(
                                        f'"{name}" is missing {12 - len(attribList)} attribute(s): {", ".join(missing)}. The "COUNTY" attribute has been filled in for you. Please revise the rest of the attributes.\n'
                                    )
                                else:
                                    errors += 1
                                    dfMajorMessages.append(
                                        f'"{name}" is missing {12 - len(attribList)} attribute(s): {", ".join(missing)}. Please revise your KML.\n'
                                    )
                            elif len(attribList) > 12:
                                dfMajorMessages.append(
                                    f'"{name}" has too many attribute(s).'
                                )
                                errors += 1

            if errors == 0:
                dfMinorMessages.append(
                    f"Your KML had {minorErrors} minor errors!\n" + "-" * 23 + "\n"
                )
                dfMajorMessages.append(
                    f"Nice! Your KML had {errors} major errors!\n" + "-" * 23 + "\n\n"
                )
                # save as df to easily convert to csv
                df = pd.DataFrame(linesData)
                return (
                    df,
                    minorErrors,
                    root,
                    errors,
                    dfMajorMessages,
                    dfMinorMessages,
                    __currentState,
                )
            else:
                dfMajorMessages.append(
                    f"Oh, no! Your KML has {errors} major error(s)!\n" + "-" * 23 + "\n"
                )
                df = None
                return (
                    df,
                    minorErrors,
                    root,
                    errors,
                    dfMajorMessages,
                    dfMinorMessages,
                    __currentState,
                )
        except:
            return (
                None,
                0,
                root,
                1,
                [
                    "Your KML is invalid. Make sure you have a properly formatted KML before running! To easily properly format your KML, please transform it, and then try converting.",
                    "Oh, no! Your KML has 1 major error!\n" + "-" * 23 + "\n",
                ],
                None,
            )


# def kmlToSHP(func):
# 	def kmlToSHPInner(self, *args, **kwargs):
# 		lineFields = []
# 		subFields = []
# 		polyFields = []
# 		root, passable, convertibles, fileName, folders = func(
# 			self, *args, **kwargs
# 		)
# 		if root == None or not passable:
# 			return subFields, lineFields, fileName, root, passable, folders
# 		else:
# 			for folder in convertibles:
# 				for folder_names in folder:  # subfolders (Substations, Lines)
# 					if "substation" in folder_names.text.lower():
# 						index = 0
# 						for placemark in folder.findall(".//kml:Placemark", ns):
# 							for coord in placemark.findall(
# 								".//kml:coordinates", ns
# 							):
# 								cPair = (
# 									re.sub(r"[\n\t]", "", coord.text)
# 									.strip()
# 									.split(" ")
# 								)
# 								for pair in cPair:
# 									latitude = float(pair.split(",")[1])
# 									longitude = float(pair.split(",")[0])
# 									z = float(pair.split(",")[2])
# 									subCoords.append([longitude, latitude, z])

# 							placemarkData = {}
# 							for simpleData in placemark.findall(
# 								".//kml:SimpleData", ns
# 							):
# 								for _, value in simpleData.attrib.items():
# 									placemarkData[value] = simpleData.text
# 							subFields.append(placemarkData)

# 					if "lines" in folder_names.text.lower():
# 						index = 0
# 						for placemark in folder.findall(".//kml:Placemark", ns):
# 							for coord in placemark.findall(
# 								".//kml:coordinates", ns
# 							):
# 								lineCoords.append([])
# 								cPair = (
# 									re.sub(r"[\n\t]", "", coord.text)
# 									.strip()
# 									.split(" ")
# 								)
# 								for pair in cPair:
# 									lat = float(pair.split(",")[1])
# 									long = float(pair.split(",")[0])
# 									z = float(pair.split(",")[2])
# 									lineCoords[index].append([long, lat, z])
# 								index += 1

# 							placemarkData = {}
# 							for simpleData in placemark.findall(
# 								".//kml:SimpleData", ns
# 							):
# 								for _, value in simpleData.attrib.items():
# 									placemarkData[value] = simpleData.text
# 							lineFields.append(placemarkData)

# 					if "poly" in folder_names.text.lower():
# 						index = 0
# 						for placemark in folder.findall(".//kml:Placemark", ns):
# 							for coord in placemark.findall(
# 								".//kml:coordinates", ns
# 							):
# 								polyCoords.append([])
# 								cPair = (
# 									re.sub(r"[\n\t]", "", coord.text)
# 									.strip()
# 									.split(" ")
# 								)
# 								for pair in cPair:
# 									lat = float(pair.split(",")[1])
# 									long = float(pair.split(",")[0])
# 									z = float(pair.split(",")[2])
# 									polyCoords[index].append([long, lat, z])
# 								index += 1

# 							placemarkData = {}
# 							for simpleData in placemark.findall(
# 								".//kml:SimpleData", ns
# 							):
# 								for _, value in simpleData.attrib.items():
# 									placemarkData[value] = simpleData.text
# 							polyFields.append(placemarkData)
# 			return subFields, lineFields, fileName, root, passable, folders

# 	return kmlToSHPInner

# def createSHP(func):
# 	def createSHPInner(self, *args, **kwargs):
# 		subFields, lineFields, fileName, root, passable, folders = func(
# 			self, *args, **kwargs
# 		)
# 		if root == None or not passable:
# 			return (
# 				folders,
# 				majorMessages,
# 				minorMessages,
# 				passable,
# 				errors,
# 				minorErrors,
# 			)
# 		else:
# 			index = 0
# 			print("linefields", lineFields)
# 			if len(polyFields) > 0:
# 				with shapefile.Writer(os.getcwd() + f"\\{fileName}_Polygons") as w:
# 					for key in polyFields[0]:
# 						w.field(key, "C")
# 					for i in polyFields:
# 						w.record(**i)
# 						w.poly([polyCoords[index]])
# 						index += 1
# 					index = 0
# 				with open(os.getcwd() + f"\\{fileName}_Polygons.prj", "w") as txt:
# 					epsg = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]'
# 					print(epsg, file=txt)
# 			if len(lineFields) > 0:
# 				with shapefile.Writer(os.getcwd() + f"\\{fileName}_Lines") as w:
# 					for key in lineFields[0]:
# 						w.field(key, "C")
# 					for i in lineFields:
# 						w.record(**i)
# 						w.linez([lineCoords[index]])
# 						index += 1
# 					index = 0
# 				with open(os.getcwd() + f"\\{fileName}_Lines.prj", "w") as txt:
# 					epsg = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]'
# 					print(epsg, file=txt)
# 			if len(subFields) > 0:
# 				with shapefile.Writer(
# 					os.getcwd() + f"\\{fileName}_Substations"
# 				) as w:
# 					for key in subFields[0]:
# 						w.field(key, "C")
# 					for i in subFields:
# 						w.record(**i)
# 						w.pointz(*subCoords[index])
# 						index += 1
# 					index = 0
# 				with open(
# 					os.getcwd() + f"\\{fileName}_Substations.prj", "w"
# 				) as txt:
# 					epsg = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]'
# 					print(epsg, file=txt)
# 			return (
# 				folders,
# 				majorMessages,
# 				minorMessages,
# 				passable,
# 				errors,
# 				minorErrors,
# 			)

# 	return createSHPInner

# @createSHP
# @kmlToSHP
# def checkForInconvertibles(self, root):
# 	if root == None:
# 		pass
# 	else:
# 		root = root
# 		notInKML = []
# 		inconvertibles = []
# 		simpleDataList = []
# 		convertibles = []
# 		passable = False
# 		for folder in folders[:]:
# 			counts = []
# 			index = 0
# 			simpleDataList = []
# 			if folder.lower() in [
# 				kmlFolder.text.lower()
# 				for kmlFolder in root.findall(f".//kml:Folder/prefix:name", ns)
# 			]:
# 				try:
# 					for kmlFolder in root.findall(f".//kml:Folder", ns):
# 						for folder_names in kmlFolder:
# 							if folder.lower() in folder_names.text.lower():
# 								if (
# 									(
# 										kmlFolder.findall(".//kml:LineString", ns)
# 										and kmlFolder.findall(".//kml:Point", ns)
# 									)
# 									or (
# 										kmlFolder.findall(".//kml:LineString", ns)
# 										and kmlFolder.findall(".//kml:Polygon", ns)
# 									)
# 									or (
# 										kmlFolder.findall(".//kml:Polygon", ns)
# 										and kmlFolder.findall(".//kml:Point", ns)
# 									)
# 								):
# 									majorMessages.append(
# 										f'Your "{folder}" folder has more than one type of shape in it. Please make sure there is only one type of shape in it.\n'
# 									)
# 									inconvertibles.append(folder)
# 									errors += 1
# 								else:
# 									if (
# 										kmlFolder.findall(
# 											".//kml:LineString/..", ns
# 										)
# 										or kmlFolder.findall(".//kml:Point/..", ns)
# 										or kmlFolder.findall(
# 											".//kml:Polygon/..", ns
# 										)
# 									):
# 										for placemark in kmlFolder.findall(
# 											".//kml:Placemark", ns
# 										):
# 											if (
# 												placemark.find(
# 													"./prefix:ExtendedData//kml:SimpleData",
# 													ns,
# 												)
# 												== None
# 											):
# 												minorMessages.append(
# 													f"Your object \"{placemark.find('.//kml:name', ns).text}\" has no SimpleData and was not converted.\n\n"
# 												)
# 												minorErrors += 1
# 												kmlFolder.remove(placemark)
# 												continue
# 											else:
# 												simpleDataList.append(
# 													[
# 														simpleData.attrib["name"]
# 														for simpleData in placemark.findall(
# 															".//kml:SimpleData",
# 															ns,
# 														)
# 													]
# 												)
# 												counts.append(
# 													len(simpleDataList[index])
# 												)
# 												index += 1
# 												if (
# 													len(counts) > 1
# 													and counts[0] != counts[1]
# 												) or (
# 													len(simpleDataList) > 1
# 													and len(simpleDataList[0])
# 													!= len(simpleDataList[1])
# 												):
# 													errors += 1
# 													inconvertibles.append(folder)
# 													majorMessages.append(
# 														f'Your "{folder}" folder is not convertible. The folder has objects that have different attributes or varying numbers of tags. Please make sure all objects have identical tags/attributes.\nTip: A quick, easy solution is to run your KML file through the "Transform KML" process; however, this will default missing values to -1!\n\n'
# 													)
# 													folders.remove(folder)
# 													raise StopIteration
# 												else:
# 													if index == 1:
# 														index = 0
# 													counts = [counts[0]]
# 													simpleDataList = [
# 														simpleDataList[0]
# 													]
# 													continue
# 										convertibles.append(kmlFolder)
# 				except Exception as e:
# 					continue

# 			else:
# 				majorMessages.append(
# 					f'A "{folder}" folder does not exist in your KML!\n'
# 				)
# 				notInKML.append(folder)
# 				errors += 1
# 				continue
# 	if errors > 0 and minorErrors > 0:
# 		majorMessages.append(
# 			f"Oh, no! Your KML has {errors} major error(s) and {minorErrors} minor error(s)!\n"
# 			+ "-" * 23
# 			+ "\n\n"
# 		)
# 	elif minorErrors > 0:
# 		minorMessages.append(
# 			f"Your KML has {minorErrors} minor error(s)!\n" + "-" * 23 + "\n\n"
# 		)
# 	elif errors > 0:
# 		majorMessages.append(
# 			f"Oh, no! Your KML has {errors} major error(s)!\n" + "-" * 23 + "\n\n"
# 		)
# 	else:
# 		majorMessages.append(
# 			f"Nice! Your KML had {errors} major errors and {minorErrors} minor error(s)!\n"
# 			+ "-" * 23
# 			+ "\n\n"
# 		)

# 	if len(inconvertibles) + len(notInKML) < len(folders) and len(convertibles) > 0:
# 		passable = True
# 	return root, passable, convertibles, fileName, folders

# def jsonToKML(self, jsonFile):
# 	res = createKML(jsonFile).getJSONFieldsAndFeatures()
# 	return res


# def run(self):
# 	try:
# 		if option == "g":
# 			result = generateSubsAndLines(root)
# 			if result == None:
# 				pass
# 			else:
# 				queue.put(result)
# 		elif option == "c":
# 			result = kmlToDF(
# 				root
# 			)  # result = df, minorErrors, root, errors, dfMajorMessages, dfMinorMessages, __currentState
# 			queue.put(result)
# 		elif option == "s":
# 			result = checkForInconvertibles(root)
# 			queue.put(
# 				result
# 			)  # result = (folders, majorMessages, minorMessages, passable, errors, minorErrors)
# 		elif option == "j":
# 			result = [(jsonToKML(jsonFile))]  # result = root
# 			queue.put(result)
# 	except Exception:
# 		tb = traceback.format_exc()
# 		queue.put(["error", tb, objExc])
def output(tree, name):
    et.indent(tree, space="\t", level=0)
    et.register_namespace("", "http://www.opengis.net/kml/2.2")
    et.register_namespace("gx", "http://www.google.com/kml/ext/2.2")
    tree.write(
        name,
        encoding="utf-8",
        short_empty_elements=False,
        xml_declaration=True,
    )


if __name__ == "__main__":
    doc = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2" xmlns:kml="http://www.opengis.net/kml/2.2" xmlns:atom="http://www.w3.org/2005/Atom">
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
			<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"/>
		</IconStyle>
	</Style>
	<Style id="sh_placemark_square_highlight">
		<IconStyle>
			<scale>1.2</scale>
			<Icon>
				<href>http://maps.google.com/mapfiles/kml/pushpin/grn-pushpin.png</href>
			</Icon>
			<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"/>
		</IconStyle>
	</Style>
	<Style id="sh_ylw-pushpin">
		<IconStyle>
			<scale>1.3</scale>
			<Icon>
				<href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href>
			</Icon>
			<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"/>
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
			<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"/>
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
			<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"/>
		</IconStyle>
	</Style>
	<Style id="sn_placemark_square">
		<IconStyle>
			<scale>1.2</scale>
			<Icon>
				<href>http://maps.google.com/mapfiles/kml/pushpin/grn-pushpin.png</href>
			</Icon>
			<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"/>
		</IconStyle>
	</Style>
	<Style id="sn_ylw-pushpin">
		<IconStyle>
			<scale>1.1</scale>
			<Icon>
				<href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href>
			</Icon>
			<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"/>
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
			<hotSpot x="20" y="2" xunits="pixels" yunits="pixels"/>
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
				<name>GREEN HILL (JOHNSTOWN, D, PENELEC, -1, N, -1, N, -1)</name>
				<LookAt>
					<longitude>-78.91240502125055</longitude>
					<latitude>40.3234677723234</latitude>
					<altitude>0</altitude>
					<heading>-0.003512015146407333</heading>
					<tilt>0</tilt>
					<range>67.75120800421665</range>
					<gx:altitudeMode>relativeToSeaFloor</gx:altitudeMode>
				</LookAt>
				<styleUrl>#msn_ylw-pushpin</styleUrl>
				<Point>
					<gx:drawOrder>1</gx:drawOrder>
					<coordinates>-78.912476,40.323442,0</coordinates>
				</Point>
			</Placemark>
			<Placemark>
				<name>WESLEY CHAPEL</name>
				<ExtendedData>
					<SchemaData schemaUrl="#Substations102">
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
				<name>CAMBRIA SLOPE (Ebensburg,D, PRISTINE RESOURCES, -1, N, -1, N, -1)</name>
				<LookAt>
					<longitude>-78.69799220569264</longitude>
					<latitude>40.46337728193316</latitude>
					<altitude>0</altitude>
					<heading>-6.074468370054971e-05</heading>
					<tilt>0</tilt>
					<range>381.8925026148954</range>
					<gx:altitudeMode>relativeToSeaFloor</gx:altitudeMode>
				</LookAt>
				<styleUrl>#msn_ylw-pushpin0</styleUrl>
				<Point>
					<gx:drawOrder>1</gx:drawOrder>
					<coordinates>-78.697425,40.463151,0</coordinates>
				</Point>
			</Placemark>
		</Folder>
		<Folder>
			<name>Lines</name>
			<Placemark>
				<name>PA-CAMBRIA-L0001 (PENELEC, S, PENELEC, 34.5, REVLOC, EBENSBURG)</name>
				<styleUrl>#sub_transmission400010</styleUrl>
				<LineString>
					<tessellate>1</tessellate>
					<coordinates>
						-78.76943638057332,40.49593595991323,0 -78.769713557893,40.49516517326612,0 -78.76984167411086,40.49441427002112,0 -78.77028633423393,40.49210741687307,0 -78.77073727608581,40.48987280390774,0 -78.76824557576954,40.48867325509222,0 -78.76570256517876,40.4875802697419,0 -78.76386696242115,40.48673137404788,0 -78.76264740614093,40.48626996675452,0 -78.76139339970467,40.48588330377842,0 -78.75989505684885,40.48530375959117,0 -78.75809065117382,40.48466019836901,0 -78.75586027883523,40.48385446215635,0 -78.75442393319999,40.48333844137476,0 -78.75313505619259,40.48288238882031,0 -78.74938378697281,40.48155781594809,0 -78.74682408883987,40.48162652950908,0 -78.74498402275982,40.48163312218308,0 -78.74215085549066,40.48165820795284,0 -78.73943903395669,40.48167134798436,0 -78.73763265694409,40.48170572065429,0 -78.73647777341831,40.48112578509861,0 -78.73582067263474,40.48081407374421,0 -78.73133420939004,40.48068364437479,0 -78.72827016238237,40.4808083356708,0 -78.72685012354187,40.48189693303355,0 
					</coordinates>
				</LineString>
			</Placemark>
			<Placemark>
				<name>PA-CAMBRIA-L0002 (PENELEC, S, PENELEC, 34.5, REVLOC, EBENSBURG)</name>
				<styleUrl>#sub_transmission400010</styleUrl>
				<LineString>
					<tessellate>1</tessellate>
					<coordinates>
						-78.76943638057332,40.49593595991323,0 -78.769713557893,40.49516517326612,0 -78.76984167411086,40.49441427002112,0 -78.77028633423393,40.49210741687307,0 -78.77073727608581,40.48987280390774,0 -78.76824557576954,40.48867325509222,0 -78.76570256517876,40.4875802697419,0 -78.76386696242115,40.48673137404788,0 -78.76264740614093,40.48626996675452,0 -78.76139339970467,40.48588330377842,0 -78.75989505684885,40.48530375959117,0 -78.75809065117382,40.48466019836901,0 -78.75586027883523,40.48385446215635,0 -78.75442393319999,40.48333844137476,0 -78.75313505619259,40.48288238882031,0 -78.74938378697281,40.48155781594809,0 -78.74682408883987,40.48162652950908,0 -78.74498402275982,40.48163312218308,0 -78.74215085549066,40.48165820795284,0 -78.73943903395669,40.48167134798436,0 -78.73763265694409,40.48170572065429,0 -78.73647777341831,40.48112578509861,0 -78.73582067263474,40.48081407374421,0 -78.73133420939004,40.48068364437479,0 -78.72827016238237,40.4808083356708,0 -78.72685012354187,40.48189693303355,0 
					</coordinates>
				</LineString>
			</Placemark>
			<Placemark>
				<name>PA-CAMBRIA-L0003 (PENELEC, S, PENELEC, 34.5, REVLOC, EBENSBURG, NU)</name>
				<styleUrl>#sub_transmission400010</styleUrl>
				<LineString>
					<tessellate>1</tessellate>
					<coordinates>
						-78.76943638057332,40.49593595991323,0 -78.769713557893,40.49516517326612,0 -78.76984167411086,40.49441427002112,0 -78.77028633423393,40.49210741687307,0 -78.77073727608581,40.48987280390774,0 -78.76824557576954,40.48867325509222,0 -78.76570256517876,40.4875802697419,0 -78.76386696242115,40.48673137404788,0 -78.76264740614093,40.48626996675452,0 -78.76139339970467,40.48588330377842,0 -78.75989505684885,40.48530375959117,0 -78.75809065117382,40.48466019836901,0 -78.75586027883523,40.48385446215635,0 -78.75442393319999,40.48333844137476,0 -78.75313505619259,40.48288238882031,0 -78.74938378697281,40.48155781594809,0 -78.74682408883987,40.48162652950908,0 -78.74498402275982,40.48163312218308,0 -78.74215085549066,40.48165820795284,0 -78.73943903395669,40.48167134798436,0 -78.73763265694409,40.48170572065429,0 -78.73647777341831,40.48112578509861,0 -78.73582067263474,40.48081407374421,0 -78.73133420939004,40.48068364437479,0 -78.72827016238237,40.4808083356708,0 -78.72685012354187,40.48189693303355,0 
					</coordinates>
				</LineString>
			</Placemark>
		</Folder>
	</Folder>
</Document>
</kml>
"""
    # k = kml.KML()
    # k.from_string(doc)
    root = et.fromstring(doc)
    tree = et.ElementTree(root)
    root, unpassableErrors, errors, errorObjectList = transform(root)
    print(root)
    print("1", unpassableErrors)
    print("2", errors)
    print("4", errorObjectList)
    print(json.dumps(errorObjectList))
    output(tree, 'output')