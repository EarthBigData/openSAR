#!/usr/bin/env python
'''
Mosaicking and subsetting tool for Global Coherence and Backscatter Data Set

Author: Josef Kellndorfer
(c) 2021, Earth Big Data LLC

'''

import fsspec
import shutil
import os,sys
from math import ceil,floor

from osgeo import gdal

import subprocess as sp
import concurrent.futures as cf
from multiprocessing import cpu_count
from pathlib import Path

import datetime


MAXWORKERS=12

METRICS = [
'fall_vh_AMP',
'fall_vv_AMP',
'fall_vv_COH06',
'fall_vv_COH12',
'fall_vv_COH18',
'fall_vv_COH24',
'fall_vv_COH36',
'fall_vv_COH48',
'fall_vv_rho',
'fall_vv_rmse',
'fall_vv_tau',
'spring_vh_AMP',
'spring_vv_AMP',
'spring_vv_COH06',
'spring_vv_COH12',
'spring_vv_COH18',
'spring_vv_COH24',
'spring_vv_COH36',
'spring_vv_COH48',
'spring_vv_rho',
'spring_vv_rmse',
'spring_vv_tau',
'summer_vh_AMP',
'summer_vv_AMP',
'summer_vv_COH06',
'summer_vv_COH12',
'summer_vv_COH18',
'summer_vv_COH24',
'summer_vv_COH36',
'summer_vv_COH48',
'summer_vv_rho',
'summer_vv_rmse',
'summer_vv_tau',
'winter_vh_AMP',
'winter_vv_AMP',
'winter_vv_COH06',
'winter_vv_COH12',
'winter_vv_COH18',
'winter_vv_COH24',
'winter_vv_COH36',
'winter_vv_COH48',
'winter_vv_rho',
'winter_vv_rmse',
'winter_vv_tau',
'fall_hv_AMP',
'fall_hh_AMP',
'fall_hh_COH06',
'fall_hh_COH12',
'fall_hh_COH18',
'fall_hh_COH24',
'fall_hh_COH36',
'fall_hh_COH48',
'fall_hh_rho',
'fall_hh_rmse',
'fall_hh_tau',
'spring_hv_AMP',
'spring_hh_AMP',
'spring_hh_COH06',
'spring_hh_COH12',
'spring_hh_COH18',
'spring_hh_COH24',
'spring_hh_COH36',
'spring_hh_COH48',
'spring_hh_rho',
'spring_hh_rmse',
'spring_hh_tau',
'summer_hv_AMP',
'summer_hh_AMP',
'summer_hh_COH06',
'summer_hh_COH12',
'summer_hh_COH18',
'summer_hh_COH24',
'summer_hh_COH36',
'summer_hh_COH48',
'summer_hh_rho',
'summer_hh_rmse',
'summer_hh_tau',
'winter_hv_AMP',
'winter_hh_AMP',
'winter_hh_COH06',
'winter_hh_COH12',
'winter_hh_COH18',
'winter_hh_COH24',
'winter_hh_COH36',
'winter_hh_COH48',
'winter_hh_rho',
'winter_hh_rmse',
'winter_hh_tau'
]



def myargsparse(a):
	import argparse

	class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
		pass
	thisprog=os.path.basename(a[0])
	############################################################################
	# define some strings for parsing and help
	############################################################################

	epilog=\
	f'''
	\r**************************************************************
	\r*                                                            *
	\r*  Earth Big Data LLC/Gamma Remote Sensing                   *
	\r*  Global Coherence and Backscatter Products Mosaicking      *
	\r*                                                            *
	\r*                                                            *
	\r*  Version 1.2, 2021-09-20,jmk                               *
	\r*                                                            *
	\r*  (c) 2021 Earth Big Data LLC Creative Commons License 4.0  * 
	\r*  https://creativecommons.org/licenses/by/4.0/              *
	\r*                                                            *
	\r**************************************************************

	\r Requirements: 
	\r 1) AWSCLI Client (aws). Obtain at: https://aws.amazon.com/cli
	\r 2) GDAL Software. Obtain at: https://gdal.org

	\r Note: Geographic tile names refer to a 1x1 degree tile identified by the UPPER LEFT lat/lon coordinate pair
	\r e.g. 'N45W090' covers the tile from longitude W090 to W089 and latitude N44 to N45

	\r***** Extent of subset via tileids or ULLR:
	\r- from geographic coordinates provided as upper left lon/lat and lower right lon/lat coordinates
	\r- List of tile names provided in a in a text file
	\r- list of tile names as input list 


	\nEXAMPLES:
	\r******* Get the list of selectable metrics:
	\r{thisprog} -sm

	\r******* Get http download urls for AWS resource:
	\r{thisprog} -ullr -115 50 -105 40 -http /tmp/coherence/download_urls.txt

	\r******* Make GeoTIFF files of a set of metrics for an extent given by upper left and lower right tile coordinates
	\r{thisprog} -ullr -90 45 -88 43 -o /tmp/global_coherence -v -mg -delete -m winter_vv_COH12 spring_vv_COH12 summer_vv_COH12 fall_vv_COH12
	\r******* Make GeoTIFF files of a set of metrics for an extent given by Tile IDs
	\r{thisprog} -tileids N45W095 N44W095 -o /tmp/global_coherence -v -mg -delete -m winter_vv_COH12 spring_vv_COH12 summer_vv_COH12 fall_vv_COH12

	\r******* Make VRTs of cached files locally with a name of MyRegion for backscatter amplitudes
	\r{thisprog} -n Myregion -o /tmp/global_coherence_vrts -ullr -115 50 -110 45 -m winter_vv_AMP winter_vh_AMP



	\r******* Metrics selection (default all)
	\r- explicit on commandline
	\r- via text file
	\r{thisprog} -m summer_vv_COH12 summer_vv_AMP summer_vh_AMP
	\r{thisprog} -m metrics.txt

	\r******* No caching, e.g., assuming all tiles are available in /home/me/tiles
	\r {thisprog} -n ULLR -ullr -115 50 -100 40 -m winter_hh_AMP -u / -p home/me/tiles -c ""
	'''

	help_url_root="\
	\r  Source of tiles on cloud or locally. Options:\
	\n  1) AWS S3    access: s3://sentinel-1-global-coherence-earthbigdata\
	\n  2) Local     access: /<path>/<to>/<downloaded>/<tile>/<root>\
	"

	p = argparse.ArgumentParser(description=epilog,prog=thisprog,formatter_class=CustomFormatter)
	p.add_argument("-sm","--show_metrics",required=False,help='Show all available metrics',action='store_true',default=False)
	p.add_argument("-n","--name",required=True,help='Name prefix for region of interest (Note: "_" in name will be replaced with "-"). If "ULLR", name will be generated from Lon/Lat ranges extracted from the selected tiles, e.g. UL-N50W090-LR-N48W088' ,action='store')
	p.add_argument("-tileids","--tileids",nargs='*',help="List of tileids OR file with tileids.",action='store',default=None)
	p.add_argument("-m","--metrics",required=False,help='List of metrics OR file with metrics. Defaults to all (see -sm for valid selections)',action='store',default=None,nargs='*')
	p.add_argument("-ullr","--ullr",nargs=4,type=float,required=False,help='Extent of region given by upper left lon/lat and  lower right lon/lat coordinates (can be fractional)', action='store',default=None,metavar=('ULlon','ULlat','LRlon','LRlat'))
	p.add_argument("-u","--url_root",required=False,help=help_url_root,action='store',default='s3://sentinel-1-global-coherence-earthbigdata')
	p.add_argument("-p","--path",required=False,help='Path or key (s3 Bucket) prefix where tiles are stored, e.g. "tiles" and -u /mnt/e would result in a search path of /mnt/e/tiles' ,action='store',default='data/tiles')
	p.add_argument("-c","--cache_path",required=False,help='local directory path to cache tiles. For no caching, this can be set to "", if -url_root <URL_RROT> is a local or nfs mounted file system. If -mg is not set, make this the output dir and do not set -delete!',action='store',default='/tmp/cached_tiles')
	p.add_argument("-delete","--delete_cached",required=False,help='delete cached files after processing (only viable with either -mg or -s3)', action='store_true',default=False)
	# p.add_argument("-s3","--save_to_s3",required=False,help='Writes the .vrt and .vrt.ovr files back to the bucket', action='store_true',default=False)
	p.add_argument("-mo","--make_overviews",required=False,help='Make overviews with gdaladdo (external). Levels can be set with -ol', action='store_true',default=False)
	p.add_argument("-ol","--overview_levels",nargs='*',type=int,required=False,help='Overview levels for gdaladdo', action='store',default=[3,9,27,81])
	p.add_argument("-tr","--target_resolution",nargs=2,type=float,required=False,help='target_resolution for "gdal_translate -tr XRES YRES -r average ..." call. When provided will generate cloud optimized geotiff output at -o OUTDIR', action='store',default=None,metavar=('XRES','YRES'))
	p.add_argument("-mg","--make_geotiff",required=False,help='Make geotiffs at native resolution', action='store_true',default=False)
	p.add_argument("-o","--outdir",required=False,help='URL root to store generated COGs if -tr is provided. Can filesystem path or s3 url. e.g. s3://<my-bucket>/coherence ',action='store',default='/tmp/global_coherence')
	p.add_argument("-t","--threads",type=int,required=False,help='maximum number of threads', action='store',default=4)
	p.add_argument("-http","--http_urls",required=False,help='If set, produces http download URLs as output into a file. No other action performed.', action='store',default=None)
	p.add_argument("-dryrun","--DryRun",required=False,help='DryRun.', action='store_true',default=False)
	p.add_argument("-v","--verbose",required=False,help="Verbose output",action='store_true',default=False)
	args=p.parse_args(a[1:])

	if args.verbose:
		d=vars(args)
		print('Parameter settings:')
		for i in d:
			print(i,'=',d[i])

	args.save_to_s3=False

	if not args.make_geotiff and not args.show_metrics:
		print(f'Not makeing geotiffs, hence setting cachedir to outdir {args.outdir} and not allowing -delete')
		args.cache_path=args.outdir
		args.delete_cached=False

	return args


def subset_tiles(lon1,lat1,lon2,lat2,tiles=None):
	'''
	select from tiles all tiles that fall between the min and max lat lon values
	e.g.
	minlon,maxlon,minlat,maxlat = -84,-82,70,71 
	results in two tiles:
	N71W084,N71W083
	'''
	lonrange=range(int(floor(min(lon1,lon2))),int(ceil(max(lon1,lon2))))
	latrange=range(int(ceil(max(lat1,lat2))),int(floor(min(lat1,lat2))),-1)
	tile_candidates=[]
	for lat in latrange:
		for lon in lonrange:
			NS='N' if lat >=0 else 'S'
			EW='E' if lon >=0 else 'W'
			tile_candidates.append(f'{NS}{abs(lat):02d}{EW}{abs(lon):03d}')
	if tiles:
		selected_tiles =  list(set(tiles).intersection(set(tile_candidates)))
	else:
		selected_tiles =  list(set(tile_candidates))
	selected_tiles.sort()
	return selected_tiles


def make_name_prefix(tiles):
	'''Return a name based on ULLR extent of the tiles in the selection list
	'''
	# find lat ranges
	lat  = [ int(x[1:3]) if x[0]=='N' else -1*int(x[1:3]) for x in tiles]
	lon  = [ int(x[4:7]) if x[3]=='E' else -1*int(x[4:7]) for x in tiles]
	def NS(lat):
		return f'N{abs(lat):02d}' if lat>=0 else f'S{abs(lat):02d}'
	def EW(lon):
		return f'E{abs(lon):03d}' if lon>=0 else f'W{abs(lon):03d}'
	name=f'UL-{NS(max(lat))}{EW(min(lon))}-LR-{NS(min(lat)-1)}{EW(max(lon)+1)}'

	return name


def make_optfile(tiles,metric,dst_tilepath,optfilename=None):
	files=[]
	rootpath=Path(dst_tilepath)
	for t in tiles:
		path=rootpath.joinpath(t)
		files+=[os.path.join(path.name,x.name) for x in path.rglob(f'{t}_*{metric}.tif')]

	files.sort()
	if optfilename:
		optfile=os.path.join(dst_tilepath,optfilename)
		with open(optfile,'w') as f:
			f.write('\n'.join(files))
		return optfile
	else:
		return files


def get_tiles(args):
	if args.url_root.startswith('s3://'):
		fs = fsspec.filesystem('s3',anon=True,client_kwargs={'endpoint_url':'https://s3.us-west-2.amazonaws.com'})
		src_path=args.url_root.rstrip('/')+'/'+args.path.strip('/')
	else:
		fs = fsspec.filesystem('file')
		src_path=os.path.join(args.url_root,args.path)
	available_tiles = set([os.path.basename(x) for x in fs.listdir(src_path,detail=False) if len(os.path.basename(x))==7 and os.path.basename(x)[0] in ['N','S'] and os.path.basename(x)[3] in ['E','W'] ])
	tiles=None
	fs.clear_instance_cache()
	del fs
	if args.tileids:
		if os.path.exists(args.tileids[0]):
			fs = fsspec.filesystem('file')
		elif args.tileids[0].startswith('s3://'):
			fs = fsspec.filesystem('s3')
		else:
			fs = None

		if not fs:
			tiles=args.tileids
		else:
			with fs.open(args.tileids[0],'r') as f:
				tiles=f.read().split()
	elif args.ullr:
		tiles=subset_tiles(*args.ullr)
	else:
		tiles=available_tiles

	if not tiles:
		print('found no tiles. Exit')
		return None
	else:
		# Intersect selected tiles with available_tiles
		selected_tiles = list(available_tiles.intersection(set(tiles)))

		if selected_tiles:
			selected_tiles.sort()
			return selected_tiles
		else:
			print('No tiles found. Exit')
			return None


def get_metrics(args):
	global METRICS
	if not args.metrics:
		return METRICS
	else:
		if os.path.exists(args.metrics[0]):
			with open(args.metrics[0]) as f:
				selected_metrics=f.read().split()
		else:
			selected_metrics=[]
			for metric in args.metrics:
				selected_metrics+=[x for x in METRICS if x.find(metric) >-1]
	metrics=list(set(METRICS).intersection(set(selected_metrics)))
	metrics.sort()
	return metrics

def remove(file2remove):
	if os.path.exists(file2remove):
		os.remove(file2remove)

def rmtree(dir2remove):
	if os.path.isdir(dir2remove):
		import shutil 
		shutil.rmtree(dir2remove)


def make_vrts(tiles,selected_metrics,args):
	'''Make the vrts and overviews
	Example:
	aws s3 sync s3://sentinel-1-global-coherence-earthbigdata/ . --exclude "*" --include "N*W*/*summer_vv_COH12',"
	gdalbuildvrt -srcnodata 0 -vrtnodata 0 NA_summer_vv_COH12.vrt */*tif
	gdaladdo -r average -ro NA_summer_vv_COH12.vrt 3 9 27 81
	aws s3 cp NA_summer_vv_COH12.vrt s3://sentinel-1-global-coherence-earthbigdata/NA_summer_vv_COH12.vrt
	aws s3 cp NA_summer_vv_COH12.vrt.ovr s3://sentinel-1-global-coherence-earthbigdata/NA_summer_vv_COH12.vrt.ovr

	Loop over metrics, find the tifs, cache the tifs locally, build vrt, make overviews, write back to bucket
	'''
	if args.DryRun:
		DRYRUN='DRYRUN:'
	else:
		DRYRUN=''

	print(f'Caching {len(tiles)} tiles')

	CWD=os.getcwd()

	cmd_cache_root='aws s3 sync --region us-west-2 --no-sign-request' if args.url_root.startswith('s3://') else '/bin/cp -R -n'

	vrtnames=[]
	cognames=[]

	for metric in selected_metrics:
		print(f'Processing {metric}')

		# 1. Cache files
		if args.cache_path:
			os.makedirs(args.cache_path,exist_ok=True)
			dst_tilepath=args.cache_path
			os.chdir(dst_tilepath)
			cmds=[]
			optfile=[]
			tilecount=0
			for tile in tiles:
				tilecount+=1
				if args.url_root.startswith('s3://'):

					tilepath='' if not args.path else args.path.strip('/')
					url_root=args.url_root.rstrip('/')+'/'+tilepath+'/'
					tile_url_src=url_root+tile
					tile_url_dst=os.path.join(dst_tilepath,tile)
					cmd=f'{cmd_cache_root} {tile_url_src} {tile_url_dst} --size-only --quiet --exclude * --include *{metric}.tif'
					cmds.append(cmd)
			if args.verbose:
				if tilecount<=10:
					print(f'\n{DRYRUN} '.join(cmds))
				else:
					print(f'\n{DRYRUN} '.join(cmds[:10]))
					print('... (first 10 only shown above)')

			if not args.DryRun:
				execute_parallel(cmds,timeout=7200,maxthreads=args.threads,verbose=args.verbose)
			else:
				workers=min(MAXWORKERS,cpu_count())  
				workers=min(workers,len(cmds))
				print(f'{DRYRUN} {metric}: Executing {len(cmds)} commands with {workers} threads...')

		else:
			dst_tilepath=os.path.join(args.url_root,args.path)
			url_root=None

		# 2. Build gdalbuildvrt and gdaladdo commands
		vrtname=make_name_prefix(tiles) if args.name=='ULLR' else args.name.replace('_','-')
		vrtname=f'{vrtname}_{metric}.vrt'
		vrtnames.append(vrtname) # add the vrtname to the list of vrtnames
		optfile=make_optfile(tiles,metric,dst_tilepath,optfilename=None)
		if not optfile:
			print(f'**** WARNING: No Metric --{metric}-- available for selected tiles ****')
			continue
		#print(optfile)
		if isinstance(optfile,str):
			build_vrt_command=f'gdalbuildvrt -srcnodata 0 -vrtnodata 0 -input_file_list {optfile} {vrtname}'
		else:
			build_vrt_command=f'gdalbuildvrt -srcnodata 0 -vrtnodata 0 -input_file_list optfile_{metric} {vrtname}'

		# build_vrt_commands.append(build_vrt_command)
		if not args.DryRun:
			if args.verbose:
				print(build_vrt_command)
			out=gdal.BuildVRT(vrtname,optfile,srcNodata=0,VRTNodata=0)
			out=None
			if isinstance(optfile,str):
				remove(optfile)
		else:
			print(f'{DRYRUN}',build_vrt_command)

		## Sync back to s3
		if args.save_to_s3:
			cmdvrt   =f'aws s3 cp {vrtname} {url_root}{vrtname}'
			if url_root and not args.DryRun:
				if args.verbose:
					print(cmdvrt)
				sp.check_call(cmdvrt.split())
			elif not url_root:
				print('Replace "None" with appropriate s3 URL and run command from commandline (also check permissions for bucket).')
			else:
				print(f'{DRYRUN} {cmdvrt}')

		# 3. Make COGs if target_resolution is provided
		if args.make_geotiff:
			args.target_resolution=[0.000833333330000,-0.000833333330000]
		if args.target_resolution:
			cogname=make_COG(args,vrtname)
			cognames.append(cognames)

		if args.make_overviews:
			build_overviews_command=f"gdaladdo -ro -r average {vrtname} {' '.join([str(x) for x in args.overview_levels])}"
			if not args.DryRun:
				if args.verbose:
					print(build_overviews_command)
				sp.check_call(build_overviews_command.split())
			else:
				print(f'{DRYRUN}',build_overviews_command)

		## Sync back to s3
		if args.save_to_s3 and args.make_overviews:
			cmdvrtovr=f'aws s3 cp {vrtname}.ovr {url_root}{vrtname}.ovr'
			if url_root and not args.DryRun:
				if args.verbose:
					print(cmdvrtovr)
				sp.check_call(cmdvrtovr.split())

			elif not url_root:
				print('Replace "None" with appropriate s3 URL and run command from commandline (also check permissions for bucket).')
			else:
				print(f'{DRYRUN} {cmdvrtovr}')

		# 5. Check if we need to delete
		if args.delete_cached:
			if not args.DryRun:
				rmtree(args.cache_path)
			else:
				print(f'{DRYRUN} rm -rf {args.cache_path}')

	os.chdir(CWD)
	return vrtnames,cognames


def make_COG(args,vrtname):
	'''make cloud optimized geotiffs'''
	xRes,yRes=args.target_resolution
	now=datetime.datetime.now().isoformat(timespec='seconds')
	creationOptions=['COMPRESS=LZW','TILED=YES','INTERLEAVE=BAND','NUM_THREADS=ALL_CPUS']
	metadataOptions=['TIFFTAG_SOFTWARE="Produced by Earth Big Data LLC and Gamma Remote Sensing Software"',f'TIFFTAG_DATETIME={now}']
	# make a COG name from the target_resolution
	ppd=int(1/xRes)
	cogname=vrtname.replace('.vrt',f'_{ppd}ppd.tif')
	out=gdal.Translate(cogname,vrtname,xRes=xRes,yRes=yRes,creationOptions=creationOptions,metadataOptions=metadataOptions)
	out.BuildOverviews("AVERAGE",args.overview_levels)
	out.FlushCache()
	out=None

	if args.outdir:
		fstype='s3' if args.outdir.startswith('s3://') else 'file'
		if fstype=='file':
			os.makedirs(args.outdir,exist_ok=True)
		fs=fsspec.filesystem(fstype)
		lpath=os.path.join(os.getcwd(),cogname)
		rpath=os.path.join(args.outdir,os.path.basename(cogname))
		if args.verbose:
			print(f'Uploading {lpath} to {rpath}')
			sys.stdout.flush()
		fs.put(lpath,rpath)


	return cogname


def execute_parallel(cmds,timeout=7200,maxthreads=None,verbose=False):
	workers=min(MAXWORKERS,cpu_count())  
	workers=min(workers,len(cmds))
	if maxthreads:
		workers=min(workers,maxthreads)

	pars=cmds
	if verbose:
		print(f'Executing {len(cmds)} jobs with {workers} threads...',end='')
	sys.stdout.flush()
	with cf.ThreadPoolExecutor(max_workers=workers) as executor:
		# Start the wrapper
		future_wrapper = {executor.submit(sp.check_call, par.split()): par for par in pars}
		for future in cf.as_completed(future_wrapper):
			try:
				future.result(timeout=timeout)  # Give it 30 minutes max
			except cf.TimeoutError as e:
				print('Timeout error',e)
	if verbose:
		print('done.')


def make_https_urls(tiles,selected_metrics,outfile):
	try:
		os.makedirs(os.path.basename(outfile),exist_ok=True)
		with open(outfile,"w") as f:
			f.write('')
	except:
		print(f'Cannot generate {outfile}')
		return 0

	urls=[]
	for t in tiles:
		for m in selected_metrics:
			url=f'https://sentinel-1-global-coherence-earthbigdata.s3.us-west-2.amazonaws.com/data/tiles/{t}/{t}_{m}.tif'
			urls.append(url)

	with open(outfile,"w") as f:
		f.write('\n'.join(urls))

	return len(urls)


def processing(args):

	if args.show_metrics:
		sys.stdout.write('\n'.join(METRICS))
		return 
	# Get tiles 
	print(f"\nEarth Big Data's TOOL FOR SUBSETTING GLOBAL COHERENCE DATA SET\n")
	# Get Metrics
	selected_metrics = get_metrics(args)
	print(f'Metric(s) to be produced: {len(selected_metrics)}')
	if args.verbose:
		print('\n'.join(selected_metrics))
	sys.stdout.flush()
	print("Locating tiles...",end='')
	sys.stdout.flush()
	tiles            = get_tiles(args)
	print('done')
	sys.stdout.flush()
	if not tiles:
		return

	if args.http_urls:
			nurls = make_https_urls(tiles,selected_metrics,args.http_urls)
			print(f'Wrote {nurls} URLs to file {args.http_urls}')
			return

	print(f'Making mosaics for {len(tiles)} tile(s).')
	if args.verbose:
		if len(tiles) > 100:
			print(f'Listing 100 of {len(tiles)} tiles:')
			print(' '.join(tiles[:10]),'\n...\n',' '.join(tiles[-10:]))
		else:
			print(' '.join(tiles))


	vrtnames,cognames = make_vrts(tiles,selected_metrics,args)

	print(f'Results in\n{args.outdir}')

def main(a):

	args = myargsparse(a)
	processing(args)


if __name__ == '__main__':
	main(sys.argv)


