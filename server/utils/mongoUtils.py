from bson.objectid import ObjectId
import re


def handleDupeFileName(collection, userId, action, newName):
    fileFilter = {"_id": ObjectId(f"{userId}"), f"files.{action}": {"$exists": True}}
    userFilter = {"_id": ObjectId(f"{userId}")}
    projection = {"_id": 0, f"files.{action}": 1}
    res = collection.find_one(
        fileFilter,
        projection,
    )  # returns object with file names under specific 'action'
    # example: {'files': {'transform': ['cambria.kml', 'cambria.kml', 'cambria.kml', 'cambria.kml', 'cambria.kml', 'cambria.kml', 'cambria.kml']}}
    
    files: list = res["files"][action]
    # if len(files) > 0:
    #     filesWithoutTime = [re.search(r'.*(?=_{"ts":.*})', f).group(0) for f in files]
    #     if fileName in filesWithoutTime:
    #         ind = filesWithoutTime.index(fileName)
    #         files.pop(ind)
    #         files.append(newName)
    #         newValue = {"$set": {f"files.{action}": files}}
    #         collection.update_one(userFilter, newValue)
    #         return
    if len(files) > 4:
        pass
    newValue = {"$push": {f"files.{action}": newName}}
    collection.update_one(
        userFilter,
        newValue,
    )
