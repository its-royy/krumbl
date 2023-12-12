import certifi
from bson.objectid import ObjectId
from dotenv import dotenv_values
from pymongo.mongo_client import MongoClient

config = dotenv_values(".env")

client = None


def connectMongoClient():
    global client
    client = MongoClient(config["ATLAS_URI"], tlsCAFile=certifi.where())
    db = client[config["DB_NAME"]]
    print('database has been connected')
    return db


def disconnectMongoClient():
    global client
    client.close()


# if __name__ == "__main__":
#     db = connectMongoClient()
#     filter_ = {"_id": ObjectId("653801cc05140854eb24889a")}
#     newValue = {"$push": {"_id": 0, "files": {"transform": file.filename}}}
#     files = db["User"].find_one(
#         {"_id": ObjectId("653801cc05140854eb24889a")},
#         {"_id": 0, "files": {"transform": 1}},
#     )
#     print(files)
    # user = db["User"].update_one({'_id': ObjectId('64e6731f4f4f856048d72e6e')}, {'$set': {'files': {'transform': ''}}})
