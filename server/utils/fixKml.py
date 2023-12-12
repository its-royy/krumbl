import xml.etree.ElementTree as et
import pandas as pd
from typing import Dict
import re

ns = {"kml": "http://www.opengis.net/kml/2.2"}

def fix(data: Dict[str, str], fileName: str):
    count = int(len(data.keys()) / 2)
    # fipsDF = pd.read_csv(
    #     "./utils/fips2county.txt",
    #     sep="\t",
    #     header="infer",
    #     dtype=str,
    #     encoding="latin-1",
    # )
    # stateCountyDF = fipsDF[["CountyFIPS", "CountyName", "StateName"]]
    with open(fileName, 'rb') as f:
        tree = et.parse(f)
        root = tree.getroot()
    for i in range(count):
        for placemark in root.findall(".//kml:Folder//kml:Placemark", ns):
            name = placemark.find('.//kml:name', ns)
            if name.text == data[f'O{i}']:
                name.text = data[f'N{i}']
    return root, tree
    
# def checkForErrors(data: Dict[str, str], fileName):
#     l = []
#     with open(fileName, 'rb') as f:
#         tree = et.parse(f)
#         root = tree.getroot()
#     count = int(len(data.keys()) / 2)
#     for i in range(count):
#         newName = data[f'N{i}']
#         oldName = data[f'O{i}']
#         placemark: et.Element = root.find(f".//*[kml:name='{oldName}']", ns)
#         placemarkType: str = root.find(f".//*[kml:name='{oldName}']/../kml:name", ns).text
        
#         simpleDataList = (re.search(r"(?<=\()(.*)(?=\))", newName).group(0).split(","))  # gets the data within the parentheses
#                          # parse through substation placemarks that already have ExtendedData
#         if 'line' in placemarkType.lower(): # perform tests for correct line name
#             if len(simpleDataList) < 7:
#                 newMessage = f"\n{newName} is missing a field(s). Please revise."
#                 errorStatements.append(newMessage)
#                 errorObjectList.append(
#                     {
#                         "name": placemark.find(".//kml:name", ns).text,
#                         "error": "Missing Field(s)",
#                         # "mf",
#                     }
#                 )
#         else:
            
        # if :# check to see if the placemark is a line or a substation
if __name__ == '__main__':
    fileName = r'C:\Users\royc3\Desktop\krumbl\server\64e680742d5d3c5853e2e4f9cambria.kml - Copy.kml'
    data = {'O0': 'CAMBRIA SLOPE (Ebensburg,D, PRISTINE RESOURCES, -1, N, -1, N)', 'N0': 'd', 'O1': 'PA-CAMBRIA-L0001 (PENELEC, S, PENELEC, 34.5, REVLOC, EBENSBURG)', 'N1': 'd', 'O2': 'PA-CAMBRIA-L0002 (PENELEC, S, PENELEC, 34.5, REVLOC, EBENSBURG)', 'N2': 'd'}
    fix(data, fileName)
    # checkForErrors(data, fileName)