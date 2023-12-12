# TODO: IF A USER UPLOADS A FILE THAT HAS ALREADY BEEN UPLOADED BEFORE (AKA, FILE NAME ALREADY EXISTS IN MONGO UNDER ONE OF THE ACTIONS), MAYBE AVOID ADDING IT AGAIN AND DELETING THE EXISTING ENTRY AND ADDING IT BACK TO THE END OF THE LIST (AKA, PUT IT TO THE END OF THE LIST/MOST RECENT ENTRY (INDEXING AT [-1]))

import datetime
import io
import os
import ssl
import xml.etree.ElementTree as et
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, Dict, Union

from bson.objectid import ObjectId
from fastapi import FastAPI, File, Form, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# from fastkml import kml
from geopy.geocoders import Nominatim
from pydantic import BaseModel
from utils.fixKml import fix
from utils.jsonToKml import createKML
from utils.kmlToCsv import dfToCSV, kmlToDF
from utils.mongoUtils import handleDupeFileName
from utils.pymongo_get_database import connectMongoClient, disconnectMongoClient
from utils.transformKml import handledirs, output, transform

db = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db
    db = connectMongoClient()
    yield
    disconnectMongoClient()


app = FastAPI(lifespan=lifespan)

origins = ["http://localhost:3000", "http://localhost"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["File-Timestamp"],  # headers that are accessible from client-side
)


class KmlError(BaseModel):
    name: str
    error: str


# in fastapi, async functions will block the main thread if there are no calls to I/O-bound operations (e.g., file.read()) or if there is an I/O-bound operation (e.g., time.sleep(5))
# async def endpoints run in the event loop—on the main (single) thread — that is, the server will also process requests to such endpoints concurrently/asynchronously, as long as there is an await call to non-blocking I/O-bound operations inside such async def endpoints/routes, such as waiting for (1) data from the client to be sent through the network, (2) contents of a file in the disk to be read, (3) a database operation to finish, etc.
# normal functions will run in an external threadpool that is then awaited, instead of being called directly (as it would block the server)


# perhaps running async is the right choice, as the server could crash if handling too many requests at the same time (request files are bigger than the server RAM)
@app.post("/upload")  # response_class=Union[FileResponse, Response]
def root(
    action: Annotated[str, Form()],
    file: Annotated[UploadFile, File(...)],
    userId: Annotated[str, Form()],
    # fileResponse: FileResponse,
    response: Response,
):  # The File(...) annotation ensures that the file parameter is required, and you must include a file in the request body.
    # perform action & saving file to server
    fileName = file.filename
    cwd = os.getcwd()
    content = file.file.read()  # returns bytes
    baseName = Path(fileName).stem
    absPath = os.path.abspath(os.path.join(cwd, userId, action))
    if action != "json-to-kml":
        contentAsString = content.decode()
        root = et.fromstring(contentAsString)
        tree = et.ElementTree(root)

    ts = str(
        datetime.datetime.now().timestamp()
        * 1000  # multiply by 1000 because python stores timestamps in seconds and javascript stores in milliseconds
    )  # store timestamp as string to store into db
    newName = f"{ts}_{baseName}.kml"

    # return file/errors
    match action:
        case "configure":
            print("action is configure")

        case "transform":
            root, unpassableErrors, errors, errorObjectList = transform(root)
            handledirs(
                userId, action, newName
            )  # create directories if needed and delete file if it already exists to save with newer contents
            fileOutput = os.path.join(absPath, newName)
            output(tree, fileOutput)

            # update db with new file
            collection = db["User"]
            handleDupeFileName(
                collection, userId, action, newName
            )  # if this filename already exists then it will add it to the end of the array to make it the most recent
            if errors:
                response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
                response.headers["File-Timestamp"] = ts
                return errorObjectList
            else:
                # f = f"C:\\Users\\royc3\\Desktop\\krumbl\\server\\{outFileName}"
                # fileResponse.status_code = status.HTTP_201_CREATED
                # return f
                headers = {"File-Timestamp": ts}
                return FileResponse(fileOutput, headers=headers, status_code=201)

        case "kml-to-csv":
            handledirs(userId, action, f"{baseName}.csv")
            df = kmlToDF(root)
            fileOutput = os.path.join(absPath, f"{baseName}.csv")
            dfToCSV(df, fileOutput)
            # update db with new file
            collection = db["User"]

            filter_ = {"_id": ObjectId(f"{userId}")}
            newValue = {"$push": {f"files.{action}": f"{baseName}.csv"}}
            collection.update_one(
                filter_,
                newValue,
            )
            return FileResponse(fileOutput, status_code=201)

        case "kml-to-shp":
            print("action is kmltoshp")

        case "json-to-kml":
            inst = createKML(content)
            root = inst.getJSONFieldsAndFeatures()
            tree = et.ElementTree(root)
            fileOutput = os.path.join(absPath, f"{baseName}.kml")
            inst.output(tree, fileOutput)
            return FileResponse(fileOutput, status_code=201)

    return {"action": action}
    # fileObject = io.BytesIO(content)   # convert bytes to file-like object
    # tree = et.parse(fileObject) # parse needs a file or a file-like object
    # root = tree.getroot()
    # ns = r'{http://www.opengis.net/kml/2.2}'
    # for child in root.find(f'.//{ns}Placemark'):


@app.post("/upload/fix")
def root(data: Dict[str, str], response: Response):
    fileName = data["fileName"]
    baseName = Path(fileName).stem
    userId = data["userId"]
    action = data["action"]
    ts = data["ts"]
    # timestamp = str({"ts": ts})
    cwd = os.getcwd()
    absPath = os.path.abspath(os.path.join(cwd, userId, action, f"{ts}_{baseName}.kml"))
    print(absPath)
    del data["fileName"], data["userId"], data["ts"], data["action"]
    root, tree = fix(data, absPath)
    root, unpassableErrors, errors, errorObjectList = transform(root, revision=True)
    output(tree, absPath)
    if errors:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return errorObjectList
    else:
        # f = f"C:\\Users\\royc3\\Desktop\\krumbl\\server\\{outFileName}"
        # fileResponse.status_code = status.HTTP_201_CREATED
        # return f
        return FileResponse(absPath, status_code=201)


@app.get("/result")
def root(userId: str, action: str):
    cwd = os.getcwd()
    print("the userId", userId, action)
    collection = db["User"]

    filter_ = {"_id": ObjectId(f"{userId}")}
    query = {"_id": 0, "files": {action: 1}}
    files = collection.find_one(
        filter_,
        query,
    )
    # ex: files = {'files': {'transform': []}}
    print("files", files)
    latestFile = files["files"][action][-1]

    absPath = os.path.join(cwd, userId, action, latestFile)
    match action:
        case "transform":
            return FileResponse(absPath, status_code=201)
        case "configure":
            pass
        case "kml-to-csv":
            return FileResponse(absPath, status_code=201)


@app.get("/retrieve")
def retrieveFile(userId: str, action: str, file: str):
    cwd = os.getcwd()

    absPath = os.path.join(cwd, userId, action, file)
    return FileResponse(absPath, status_code=201)
    # match action:
    #     case "transform":
    #         return FileResponse(absPath, status_code=201)
    #     case "configure":
    #         pass
    #     case "kml-to-csv":
    #         return FileResponse(absPath, status_code=201)
