import xml.etree.ElementTree as et
import json
import re
from itertools import repeat
import requests
import math 
import os

class createKML():
    def __init__(self, jsonFile):
        self.ns = {'prefix': 'http://www.opengis.net/kml/2.2'}
        self.raw_ns = r'{http://www.opengis.net/kml/2.2}'
        et.register_namespace('', 'http://www.opengis.net/kml/2.2')
        self.root = et.Element(f'{self.raw_ns}kml')
        # self.root.set('xmlns', 'http://www.opengis.net/kml/2.2')
        self.doc = et.SubElement(self.root, f'{self.raw_ns}Document')
        self.idKeywords = ['id', 'number', 'name']
        self.placemarkNameKeyword = None
        self.count = 0
        self.sr = None
        self.geometryType = None
        self.json = jsonFile
    
    def convertToLatLong(self, geometryType, x, y):    # input => spatial reference of JSON
        url = 'https://sampleserver6.arcgisonline.com/arcgis/rest/services/Utilities/Geometry/GeometryServer/project'
        data = {
            'inSR': self.sr, 
            'outSR': 4326,
            'geometries': str({
                'geometryType': geometryType,
                'geometries':[{'x': x, 'y': y}]
            }),
            'f': 'json'
        }
        
        req = requests.post(url, data=data)
        res = req.json()
        x = res['geometries'][0]['y']
        y = res['geometries'][0]['x']
        return x, y

    def metersToLatLong(self, x, y):
        originShift = 2 * math.pi * 6378137 / 2.0
        long = (x / originShift) * 180
        lat = (y / originShift) * 180
        
        lat = 180 / math.pi * (2 * math.atan( math.exp( lat * math.pi / 180.0)) - math.pi / 2.0)
        return lat, long

    
    def _makePlacemark(self, feature, fileName):
        placemark = et.SubElement(self.folder, f'{self.raw_ns}Placemark')
        name = et.SubElement(placemark, f'{self.raw_ns}name')
        if self.placemarkNameKeyword:
            name.text = feature['attributes'][self.placemarkNameKeyword]
        else:
            name.text = f'Placemark {self.count}'
        extendedData = et.SubElement(placemark, f'{self.raw_ns}ExtendedData')
        schemaData = et.SubElement(extendedData, f'{self.raw_ns}SchemaData', attrib={'schemaUrl': fileName})
        for key, value in feature['attributes'].items():
            # simpleDatas = map(self._makeSimpleData, feature, repeat(schemaData))
            simpleData = et.SubElement(schemaData, f'{self.raw_ns}SimpleData', attrib={'name': key})
            if not isinstance(value, str):
                value = str(value)
            simpleData.text = value
            
        point = et.SubElement(placemark, f'{self.raw_ns}Point')
        x = feature['geometry']['x']    
        y = feature['geometry']['y']
        if self.sr == 102100:
            x, y = self.metersToLatLong(x, y)
        else:
            x, y = self.convertToLatLong(self.sr, self.geometryType, x, y)
        coordinates = et.SubElement(point, f'{self.raw_ns}coordinates')
        coordinates.text = str(y)+','+str(x)
        self.count += 1
        
        
    # def write(self, name:str):
    #     tree = et.ElementTree(self.root)
    #     # tree = et.parse('output.kml')
    #     # root = tree.getroot()
    #     # print(root.find(r'.//{http://www.opengis.net/kml/2.2}Schema'))
    #     et.indent(tree, space='\t', level=0)
    #     tree.write(name + '.kml', encoding="utf-8", short_empty_elements=False, xml_declaration=True)
    
    def createSchema(f):
        def inner(self, *args, **kwargs):
            fields, features, fileName = f(self, *args, **kwargs)
            self.schema = et.SubElement(self.doc, f'{self.raw_ns}Schema', attrib={'name': fileName}, id=fileName)
            for field in fields:
                et.SubElement(self.schema, f'{self.raw_ns}SimpleField', attrib={
                                                                    'name': f'{field}'}, type='string')
            return fields, features, fileName
        return inner
    
    def addPlacemarks(f):
        def inner(self, *args, **kwargs):
            fields, features, fileName = f(self, *args, **kwargs)
            self.folder = et.SubElement(self.doc, f'{self.raw_ns}Folder')
            folderName = et.SubElement(self.folder, f'{self.raw_ns}name') 
            folderName.text = 'Placemarks'
            list(map(self._makePlacemark, features, repeat(fileName))) # must do list() or consume the returned iterator becuse Python 3's map() function is lazy
            return self.root
        return inner
            
    
    @addPlacemarks    
    @createSchema
    def getJSONFieldsAndFeatures(self):
        with open(self.json, 'rb') as jsonFile:
            data = json.load(jsonFile)
            
            fields = [k for k in data['fieldAliases'].keys()]
            features = data['features']

            self.sr = data['spatialReference']['wkid']
            self.latestSr = data['spatialReference']['latestWkid']
            self.geometryType = data['geometryType']
        for field in fields:
            for id in self.idKeywords:
                if id in field.lower() and not self.placemarkNameKeyword:
                    self.placemarkNameKeyword = field
                    break
            if self.placemarkNameKeyword:
                break
        
            
        fileName = re.search(r'.*(?=.json)', self.json).group(0)
        return fields, features, fileName
    
    def output(self, tree, name):
        et.indent(tree, space="\t", level=0)
        et.register_namespace("", "http://www.opengis.net/kml/2.2")
        et.register_namespace("gx", "http://www.google.com/kml/ext/2.2")
        tree.write(
            name,
            encoding="utf-8",
            short_empty_elements=False,
            xml_declaration=True,
    )
    
if __name__ == '__main__':
    cwd = os.getcwd()
    jsonFile = os.path.join(cwd, 'test.json')
    base = createKML(jsonFile)
    root = base.getJSONFieldsAndFeatures()
    tree = et.ElementTree(root)
    base.output(tree, 'testing123.kml')