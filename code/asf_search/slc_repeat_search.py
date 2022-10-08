'''Find repeat coverage of frames with asf_search

Author: Josef Kellndorfer, 2022-10-07

Usage:

Modify the search parameters, WKT polygon and output path and name as desired

then run:

python  <this-script>


BACKGROUND:
 - ASF SEARCH PARAMETERS:
Performs a generic search using the ASF SearchAPI. Accepts a number of search parameters, and/or an ASFSearchOptions object. If an ASFSearchOptions object is provided as well as other specific parameters, the two sets of options will be merged, preferring the specific keyword arguments.

absoluteOrbit: For ALOS, ERS-1, ERS-2, JERS-1, and RADARSAT-1, Sentinel-1A, Sentinel-1B this value corresponds to the orbit count within the orbit cycle. For UAVSAR it is the Flight ID.
asfFrame: This is primarily an ASF / JAXA frame reference. However, some platforms use other conventions. See ‘frame’ for ESA-centric frame searches.
beamMode: The beam mode used to acquire the data.
campaign: For UAVSAR and AIRSAR data collections only. Search by general location, site description, or data grouping as supplied by flight agency or project.
maxDoppler: Doppler provides an indication of how much the look direction deviates from the ideal perpendicular flight direction acquisition.
minDoppler: Doppler provides an indication of how much the look direction deviates from the ideal perpendicular flight direction acquisition.
end: End date of data acquisition. Supports timestamps as well as natural language such as "3 weeks ago"
maxFaradayRotation: Rotation of the polarization plane of the radar signal impacts imagery, as HH and HV signals become mixed.
minFaradayRotation: Rotation of the polarization plane of the radar signal impacts imagery, as HH and HV signals become mixed.
flightDirection: Satellite orbit direction during data acquisition
flightLine: Specify a flightline for UAVSAR or AIRSAR.
frame: ESA-referenced frames are offered to give users a universal framing convention. Each ESA frame has a corresponding ASF frame assigned. See also: asfframe
granule_list: List of specific granules. Search results may include several products per granule name.
groupID: Identifier used to find products considered to be of the same scene but having different granule names
insarStackId: Identifier used to find products of the same InSAR stack
instrument: The instrument used to acquire the data. See also: platform
intersectsWith: Search by polygon, linestring, or point defined in 2D Well-Known Text (WKT)
lookDirection: Left or right look direction during data acquisition
offNadirAngle: Off-nadir angles for ALOS PALSAR
platform: Remote sensing platform that acquired the data. Platforms that work together, such as Sentinel-1A/1B and ERS-1/2 have multi-platform aliases available. See also: instrument
polarization: A property of SAR electromagnetic waves that can be used to extract meaningful information about surface properties of the earth.
processingDate: Used to find data that has been processed at ASF since a given time and date. Supports timestamps as well as natural language such as "3 weeks ago"
processingLevel: Level to which the data has been processed
product_list: List of specific products. Guaranteed to be at most one product per product name.
relativeOrbit: Path or track of satellite during data acquisition. For UAVSAR it is the Line ID.
season: Start and end day of year for desired seasonal range. This option is used in conjunction with start/end to specify a seasonal range within an overall date range.
start: Start date of data acquisition. Supports timestamps as well as natural language such as "3 weeks ago"
maxResults: The maximum number of results to be returned by the search
provider: Custom provider name to constrain CMR results to, for more info on how this is used, see https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html#c-provider
session: A Session to be used when performing the search. For most uses, can be ignored. Used when searching for a dataset, provider, etc. that requires authentication. See also: asf_search.ASFSession
host: SearchAPI host, defaults to Production SearchAPI. This option is intended for dev/test purposes and can generally be ignored.
opts: An ASFSearchOptions object describing the search parameters to be used. Search parameters specified outside this object will override in event of a conflict.

- RESULT PROPERTIES OF EACH granule as a dictionary example:
{'beamModeType': 'IW',
 'browse': [],
 'bytes': '4429891902',
 'centerLat': '49.5285',
 'centerLon': '-71.7832',
 'faradayRotation': None,
 'fileID': 'S1A_IW_SLC__1SDV_20211231T223712_20211231T223739_041259_04E754_F10D-SLC',
 'fileName': 'S1A_IW_SLC__1SDV_20211231T223712_20211231T223739_041259_04E754_F10D.zip',
 'flightDirection': 'ASCENDING',
 'frameNumber': '158',
 'granuleType': 'SENTINEL_1A_FRAME',
 'groupID': 'S1A_IWDV_0158_0164_041259_062',
 'insarStackId': None,
 'md5sum': '7821270379dfdf9cd7c132af21344c20',
 'offNadirAngle': None,
 'orbit': '41259',
 'pathNumber': '62',
 'perpendicularBaseline': None,
 'platform': 'Sentinel-1A',
 'pointingAngle': None,
 'polarization': 'VV+VH',
 'processingDate': '2021-12-31T22:37:12.000000',
 'processingLevel': 'SLC',
 'sceneName': 'S1A_IW_SLC__1SDV_20211231T223712_20211231T223739_041259_04E754_F10D',
 'sensor': 'C-SAR',
 'startTime': '2021-12-31T22:37:12.000000',
 'stopTime': '2021-12-31T22:37:39.000000',
 'temporalBaseline': None,
 'url': 'https://datapool.asf.alaska.edu/SLC/SA/S1A_IW_SLC__1SDV_20211231T223712_20211231T223739_041259_04E754_F10D.zip'}
'''


import os 
import asf_search as asf
import datetime as dt
import json 


#########################################################################################
# OUTPUT FILENAME
#########################################################################################
# Where to store the result as a geojson
outname='asf_search.json'
outpath=os.path.join(os.environ['HOME'],'junk','asf_search')
os.makedirs(outpath,exist_ok=True)
outfile=os.path.join(outpath,outname)
#########################################################################################
#########################################################################################

#########################################################################################
# SEARCH PARAMETERS
#########################################################################################
## PLATFORMAND MODES
platform='Sentinel-1'
processingLevel='SLC'
beamMode='IW'
maxResults=None 

## DATERANGE
start = dt.datetime(2021,1,1,0,0,0)
end   = dt.datetime(2022,1,1,0,0,0)

## AREA as WKT Polygon 
# #Lower 48
# wkt='POLYGON((-126 48, -68 48, -75 23, -126 23, -126 48))'
# maxResults=None

# California
wkt='POLYGON((-125 42, -120 42, -111 32, -121 32, -125 40, -125 42))'
#########################################################################################
#########################################################################################

# Perform the search
print('Searching ASF database (this can take a while)...',end='',flush=True)
intersectsWith=wkt
res = asf.search (platform=platform,start=start,end=end,intersectsWith=intersectsWith,beamMode=beamMode,processingLevel=processingLevel,maxResults=maxResults)
print('done',flush=True)
print('Number of granules found:',len(res),flush=True)
# Group result by relativeOrbit and frame
frame_dict={}
for frame in res:
	key=(frame.properties['pathNumber'],frame.properties['frameNumber'])
	if not key in frame_dict:
		frame_dict[key]={}
		frame_dict[key]['geometry']=frame.geometry
		frame_dict[key]['scenedate']=[]
		frame_dict[key]['flightDirection']=	frame.properties['flightDirection']
	scenedate=dt.datetime.fromisoformat(frame.properties['startTime']).date()
	frame_dict[key]['scenedate'].append(scenedate)
print('Number of unique path/frame combinations found:',len(frame_dict),flush=True)

# Determine how many 6-day, 12-day, 24-day etc  repeats we have
repeat_dict={}
for key in frame_dict:
	frame_dict[key]['scenedate'].sort()
	if not key in repeat_dict:
		repeat_dict[key]={}
	for i in range(1,len(frame_dict[key]['scenedate'])):
		daysdiff=frame_dict[key]['scenedate'][i]-frame_dict[key]['scenedate'][i-1]
		daysdiff=daysdiff.days
		if not daysdiff in repeat_dict[key]:
			repeat_dict[key][daysdiff]=0
		repeat_dict[key][daysdiff]+=1

# let's build a geojson that shows the repeat coverage
## First the feature list
features=[]
for key in frame_dict:
	feature={}
	feature['type']='Feature'
	feature['geometry']=frame_dict[key]['geometry']
	feature['properties']={}
	feature['properties']['pathNumber']=key[0]
	feature['properties']['frameNumber']=key[1]
	feature['properties']['flightDirection']=frame_dict[key]['flightDirection']
	for days in repeat_dict[key]:
		feature['properties'][str(days)]=repeat_dict[key][days]
	features.append(feature)

## Now the FeatureCollection geojson
out_geojson={}
out_geojson['type']='FeatureCollection'
out_geojson['features']=features

print(f'Writing geojson file {outfile}')
with open(outfile,'w') as f:
	json.dump(out_geojson,f)


# 6-day repeat path frame list as csv
six_day_list=[x for x in features  if "6" in x['properties']]

## For sorting the list we want path and frame as integers
def key_func(line):
	p,f,_,_=line.split(',')
	return (int(p),int(f))

outfile_six_days = os.path.splitext(outfile)[0]+'.csv'
print(f'Writing csv     file {outfile_six_days}')
with open(outfile_six_days,'w') as f:
	f.writelines(f'pathNumber,frameNumber,flightDirection,6-day-repeats\n')
	lines=[]
	for feature in six_day_list:
		prop=feature['properties']
		line=f"{prop['pathNumber']},{prop['frameNumber']},{prop['flightDirection']},{prop['6']}\n"
		lines.append(line)
	lines.sort(key=key_func)
	f.writelines(lines)


