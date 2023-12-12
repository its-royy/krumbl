import datetime
import re
import json

ts = datetime.datetime.now().timestamp()
# date = datetime.datetime.fromtimestamp(ts)
# now = date.strftime('%m/%d/%Y %H:%M:%S')
# s = r'something.kml_{"ts": 1701885854.292673}'
# nameWithoutTime = re.search(r'.*(?=_{"ts":.*})', s).group(0)
# time = json.loads(re.sub(nameWithoutTime + '_', '', s))
# print(time['ts'])
filename = 'something.kml'
d = str({"ts": ts})
newName = filename + f'_{d}'
print(newName)