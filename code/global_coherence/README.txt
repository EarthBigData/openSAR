# Global Seasonal Sentinel-1 Interferometric Coherence and Backscatter Data Set
# Software tools to generate and visualize coherence and backscatter data

1. Scripts for generating the data set

Note that these scripts only run on Linux OS.

These scripts are source code based on Gamma Remote Sensing AG Software to generate 
- seasonal backscatter and coherence metrics
- coherence decay model parameters
- incidence angle and layover shadow files

step-1-1-slc2bursts.py
step-1-2-bursts2burstGroups.py
step-2-1-insar_processor.py
step-3-1-compositing.py
step-4.1-mosaics.py


2. Subsetting/Mosaicking tool to access the data located on AWS in the bucket s3://sentinel-1-global-coherence-earthbigdata

Execute check_modules.py to verify that required python modules are available.
Note that this tool only runs on Linux and MAC OSX operating systems.

External software requirements: 
1) AWSCLI Client (aws). Obtain at: https://aws.amazon.com/cli
2) GDAL Software. Obtain at: https://gdal.org


usage: global_coherence_mosaic_tool.py [-h] [-sm] [-n NAME]
                                       [-tileids [TILEIDS [TILEIDS ...]]]
                                       [-m [METRICS [METRICS ...]]]
                                       [-ullr ULlon ULlat LRlon LRlat]
                                       [-u URL_ROOT] [-p PATH] [-c CACHE_PATH]
                                       [-delete] [-mo]
                                       [-ol [OVERVIEW_LEVELS [OVERVIEW_LEVELS ...]]]
                                       [-tr XRES YRES] [-mg] [-o OUTDIR]
                                       [-t THREADS] [-dryrun] [-v]

	
**************************************************************
*                                                            *	
*  Earth Big Data LLC/Gamma Remote Sensing                   *
*  Global Cohernce Products Mosaicking                       *
*                                                            *	
*                                                            *
*  Version 1.2, 2021-09-20,jmk                               *
*                                                            *
*  (c) 2021 Earth Big Data LLC Creative Commons License 4.0  * 
*  https://creativecommons.org/licenses/by/4.0/              *
*                                                            *
**************************************************************

	
 Requirements: 
	
 1) AWSCLI Client (aws). Obtain at: https://aws.amazon.com/cli
 2) GDAL Software. Obtain at: https://gdal.org

	
 Note: Geographic tile names refer to a 1x1 degree tile identified by the UPPER LEFT lat/lon coordinate pair
 e.g. 'N45W090' covers the tile from longitude W090 to W089 and latitude N44 to N45

		
***** Extent of subset via tileids or ULLR:
	
- from geographic coordinates provided as upper left lon/lat and lower right lon/lat coordinates
- List of tile names provided in a in a text file
- list of tile names as input list 

	
EXAMPLES:

******* Get http download urls for AWS resource:
global_coherence_mosaic_tool.py -ullr -115 50 -105 40 -http /tmp/coherence/download_urls.txt

******* Make GeoTIFF files of a set of metrics for an extent given by upper left and lower right tile coordinates
global_coherence_mosaic_tool.py -ullr -90 45 -88 43 -o /tmp/global_coherence -v -mg -delete -m winter_vv_COH12 spring_vv_COH12 summer_vv_COH12 fall_vv_COH12
******* Make GeoTIFF files of a set of metrics for an extent given by Tile IDs
global_coherence_mosaic_tool.py -tileids N45W095 N44W095 -o /tmp/global_coherence -v -mg -delete -m winter_vv_COH12 spring_vv_COH12 summer_vv_COH12 fall_vv_COH12

******* Make VRTs of cached files locally with a name of MyRegion for backscatter amplitudes
global_coherence_mosaic_tool.py -n Myregion -o /tmp/global_coherence_vrts -ullr -115 50 -100 40 -m winter_vv_AMP winter_vh_AMP

******* Metrics selection (default all)
- explicit on commandline
- via text file
	
global_coherence_mosaic_tool.py -m summer_vv_COH12 summer_vv_AMP summer_vh_AMP
global_coherence_mosaic_tool.py -m metrics.txt

******* No caching, e.g., assuming all tiles are available in /home/me/tiles
global_coherence_mosaic_tool.py -n ULLR -ullr -115 50 -100 40 -m winter_hh_AMP -u / -p home/me/tiles -c ""
	

optional arguments:
  -h, --help            show this help message and exit
  -sm, --show_metrics   Show all available metrics (default: False)
  -n NAME, --name NAME  Name prefix for region of interest (Note: "_" in name
                        will be replaced with "-"). If "ULLR", name will be
                        generated from Lon/Lat ranges extracted from the
                        selected tiles, e.g. UL-N50W090-LR-N48W088 (default:
                        ULLR)
  -tileids [TILEIDS [TILEIDS ...]], --tileids [TILEIDS [TILEIDS ...]]
                        List of tileids OR file with tileids. (default: None)
  -m [METRICS [METRICS ...]], --metrics [METRICS [METRICS ...]]
                        Selection of metrics. Defaults to all (see -sm for
                        valid selections) (default: None)
  -ullr ULlon ULlat LRlon LRlat, --ullr ULlon ULlat LRlon LRlat
                        Extent of region given by upper left lon/lat and lower
                        right lon/lat coordinates (can be fractional)
                        (default: None)
  -u URL_ROOT, --url_root URL_ROOT
                        Source of tiles on cloud or locally. Options: 1) AWS
                        S3 access: s3://sentinel-1-global-coherence-
                        earthbigdata 2) Local access:
                        /<path>/<to>/<downloaded>/<tile>/<root> (default:
                        s3://sentinel-1-global-coherence-earthbigdata)
  -p PATH, --path PATH  Path or key (s3 Bucket) prefix where tiles are stored,
                        e.g. "tiles" and -u /mnt/e would result in a search
                        path of /mnt/e/tiles (default: data/tiles)
  -c CACHE_PATH, --cache_path CACHE_PATH
                        local directory path to cache tiles. For no caching,
                        this can be set to "", if -url_root <URL_RROT> is a
                        local or nfs mounted file system. If -mg is not set,
                        make this the output dir and do not set -delete!
                        (default: /tmp/cached_tiles)
  -delete, --delete_cached
                        delete cached files after processing (only viable with
                        either -mg or -s3) (default: False)
  -mo, --make_overviews
                        Make overviews with gdaladdo (external). Levels can be
                        set with -ol (default: False)
  -ol [OVERVIEW_LEVELS [OVERVIEW_LEVELS ...]], --overview_levels [OVERVIEW_LEVELS [OVERVIEW_LEVELS ...]]
                        Overview levels for gdaladdo (default: [3, 9, 27, 81])
  -tr XRES YRES, --target_resolution XRES YRES
                        target_resolution for "gdal_translate -tr XRES YRES -r
                        average ..." call. When provided will generate cloud
                        optimized geotiff output at -o OUTDIR (default: None)
  -mg, --make_geotiff   Make geotiffs at native resolution (default: False)
  -o OUTDIR, --outdir OUTDIR
                        URL root to store generated COGs if -tr is provided.
                        Can filesystem path or s3 url. e.g. s3://<my-
                        bucket>/coherence (default: /tmp/global_coherence)
  -t THREADS, --threads THREADS
                        maximum number of threads (default: 4)
  -http HTTP_URLS, --http_urls HTTP_URLS
                        If set, produces http download URLs as output into a file. 
                        No other action performed. (default: None)
  -dryrun, --DryRun     DryRun. (default: False)
  -v, --verbose         Verbose output (default: False)
