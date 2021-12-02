#!/usr/bin/env python
# coding: utf-8
'''
SEPPO RGB Generator from VRT Stacks

Author: Josef Kellndorfer
(c) 2015- Earth Big Data LLC

Generate grayscale or RGBs for tiles based on dates

see http://remotesensing.earth

Choose up to three dates.
Choose blue or red flags for two date images where second date is in the blue or red channel
'''

import os,sys
from osgeo import gdal
import time
import xarray as xr
import pandas as pd
import fsspec
from cryptography.fernet import Fernet

encoded_aws_access_key_id=b'gAAAAABhlYolWvEowUxZQGEoTsTM28ifKgkNeDKfpFE_aQmDOh-MpqsNTvnD4EV7BzfHL64474JZpxFb_EWrQWe9GL2JZoCvWbKOXejJytgkHCEGQjZWlpY='
encoded_aws_secret_access_key=b'gAAAAABhlYolYg3h9yizj1JSbi1N7rGmFAJHS6gdqSKzUYxgVmQuyZA8KttEb9xVnw22zyPmXRMJZOi--LUGJYMG4ia-cF8kT9d1Mr8SuvsriCUkS1wGGS_fEXBkursV6IIl39i1vkZk'


DEVEL=False

if DEVEL:
    outdir='/tmp'
    tiles=['14UPU']
    dates=['20200411','20200329']
    flightdirection='A'
    polarizations=['vv','vh']
    #polarizations=['vv']
    relOrbits=[136]
    blue=False
    red=False
    keyfile=os.path.join(os.environ['HOME'],'.ebd','ebd_key_wasabi_public.txt')


def myargsparse(argv):
    import argparse

    class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
            pass

      
    thisprog=os.path.basename(argv[0])

    ############################################################################
    # define some strings for parsing and help
    ############################################################################

    epilog=\
    f"""*********************************************************************************
    \r *  SEPPO RGB Generator from VRT Stacks
    \r *  
    \r *  Generate grayscale or RGBs for tiles based on dates
    \r *  
    \r *  Choose up to three dates.
    \r *  Choose blue or red flags for two date images where second date 
    \r *     is in the blue or red channel
    \r**********************************************************************************
    \rEXAMPLES:
    \r*** Two Dates RGB
    \r{thisprog} -t 14UPU -fd A -ro 136 -d 20200329 20200411 -pol vh -o /tmp/geotiffs
    \r*** One Date Grayscale with Description
    \r{thisprog} -t 14UPU -d 20200330 -blue -o /tmp/geotiffs -ro 136 -pol vh -v -desc "Sentinel-1 SAR Backscatter"
     """


    
    p = argparse.ArgumentParser(usage=None,description=epilog,prog=thisprog,formatter_class=CustomFormatter)
    p.add_argument("-o","--outdir",required=False,help='Output directory',action='store',default=None)
    p.add_argument("-t","--tiles",required=True,help='List of tile IDs',action='store',nargs='*')
    p.add_argument("-d","--dates",required=True,help='List of dates for RGB (up to three). Format 20200101 or 2020-01-01 supported.',action='store',nargs='*')
    p.add_argument("-fd","--flightdirection",required=False,help='Flightdirection',action='store',default=['A','D'],nargs='*',choices=('A','D'))
    p.add_argument("-ro","--relOrbits",required=False,help='selected relative orbits',action='store',default=None,type=int,nargs='*')
    p.add_argument("-pol","--polarizations",required=False,help='Polarizations',action='store',default=['vv','vh'],nargs='*',choices=('vv','vh'))
    p.add_argument("-red","--red",required=False,help='For two dates, assigns the first date in date list to red, duplicates 2nd date for blue band',action='store_true',default=False)
    p.add_argument("-blue","--blue",required=False,help='For two dates, assigns the first date in date list to blue, duplicates 2nd date for red band. Ignored when -red is set',action='store_true',default=False)
    p.add_argument("-desc","--description",required=False,help='Description of Data Set e.g. "Sentinel-1 SAR Backscatter"',action='store',default=None)
    p.add_argument("-site","--site_name",required=False,help='Name of a site, e.g. "PNWFlood202111"',action='store',default=None)
    p.add_argument("-k","--keyfile",required=False,help='Path to key file to unlock credentials',action='store',default=os.path.join(os.environ['HOME'],'.ebd','ebd_key_wasabi_public.txt'))
    p.add_argument("-mre","--make_realEarth_output",required=False,help='make output in realEarth format',action='store_true',default=False)
    p.add_argument("-no_vrt","--no_vrt",required=False,help='Do not build VRT mosaics of the selected tiles ',action='store_true',default=False)
    p.add_argument("-dryrun","--dryrun",required=False,help='Dryrun Mode. Shows selected Stack VRTs and selectded bands and dates.',action='store_true',default=False)
default=False)
    p.add_argument("-v","--verbose",required=False,help='Verbose output',action='store_true',default=False)

    args=p.parse_args(argv[1:])

    return args


def make_geotiff(vrtfile,dates,outdir=None,red=False,blue=False,description=None,verbose=False,dryrun=False):
    # Open the vrtfile as data array
    if not vrtfile.startswith('/vsis3/'):
        vrtfile='/vsis3/'+vrtfile
    da = xr.open_rasterio(vrtfile)
    acq_dates=pd.DatetimeIndex(da.descriptions)
    da['band']=acq_dates
    da = da.rename({'band':'time'})

    # Make the selection dates and find the nearest ones in the vrtfile as band numbers
    # selection dates
    seldates=pd.DatetimeIndex(dates)
    da_sel = da.sel(time=seldates,method='nearest')

    acq_dates_list=list(acq_dates)
    sel_dates_list=list(da_sel.time)
    found_dates = [str(x.time.values).split('T')[0] for x in sel_dates_list]
    bands = [acq_dates_list.index(x)+1 for x in sel_dates_list ]
    print('Selected dates and bands for',vrtfile)
    print(found_dates,bands)

    if len(bands) in [1,3]:
        pass
    elif red:
        bands.append(bands[-1])
    elif blue:
        bands2=[]
        bands2.append(bands[1])
        bands2.append(bands[1])
        bands2.append(bands[0])
        bands=bands2
    else: 
        bands.append(bands[-1])

    band_dates=[str(da.time[x-1].values).split('T')[0] for x in bands]

    if verbose:
        print('Band/Date order for Grayscale/RGB:', bands,band_dates)

    if dryrun:
        return None
    else:
        # Make a list of vrts for each band first
        input_file_list=[]
        for b in bands:
            name=f'/vsimem/{b}.vrt'
            input_file_list.append(gdal.BuildVRT(name,vrtfile,bandList=[b],srcNodata=0,VRTNodata=0))

        subset_vrt='/vsimem/crap.vrt'

        out=gdal.BuildVRT(subset_vrt,input_file_list,separate=True,srcNodata=0,VRTNodata=0)
        out=None
        for i in input_file_list:
            i=None
        input_file_list=None

        # outname
        basename=vrtfile.split('/')[-1].replace('.vrt','')
        outname='_'.join([basename]+found_dates)+'.tif'
        
        if outdir:
            os.makedirs(outdir,exist_ok=True)
            outpath=os.path.join(outdir,outname)
        else:
            outpath=os.path.join(os.getcwd(),outname)
        out2 = gdal.Translate(outpath,subset_vrt)
        out2 = None
        # Set Metadata
        _ = seppo_SetMetadata(outpath,band_names=band_dates,description=description)
        
        return outpath


def make_filesystem(keyfile):

    with open(keyfile,"r") as f:
        key=f.read()

    # set KEY and secret
    cipher_suite = Fernet(key.encode())
    KEY=cipher_suite.decrypt(encoded_aws_access_key_id).decode()
    SECRET=cipher_suite.decrypt(encoded_aws_secret_access_key).decode()
    os.environ['AWS_DEFAULT_REGION']='us-east-1'
    os.environ['AWS_ACCESS_KEY_ID']=KEY
    os.environ['AWS_SECRET_ACCESS_KEY']=SECRET
    os.environ['AWS_S3_ENDPOINT']='s3.us-east-1.wasabisys.com'
    os.environ.unsetenv('AWS_DEFAULT_PROFILE')

    fs=fsspec.filesystem('s3',anon=False,client_kwargs={'endpoint_url':'https://s3.us-east-1.wasabisys.com'},key=KEY,secret=SECRET)

    return fs


def make_vrtlist(args,filesystem):


    vrtlist=[]
    for tile in args.tiles:
        tilepath=f'sentinel-1-l22/mgrs/{tile}/20m/'

        vrts=[x for x in filesystem.ls(tilepath) if x.endswith('mtfil.vrt')]

        fd_vrts=[]
        for fd in args.flightdirection:
             fds=[x for x in vrts if x.find('20m_'+fd)>-1]
             fd_vrts+=fds
        vrts=fd_vrts

        pol_vrts=[]
        for pol in args.polarizations:
            pols=[x for x in vrts if x.find(pol)>-1]
            pol_vrts+=pols
        vrts=pol_vrts
        
        relOrbits_vrts=[]
        if not args.relOrbits:
            vrtlist+=pol_vrts
        else:
            for ro in args.relOrbits:
                ro_string=f'_{ro:03d}_'
                ros=[x for x in vrts if x.find(ro_string)>-1]
                relOrbits_vrts+=ros
            vrtlist+=relOrbits_vrts

    return vrtlist


def seppo_SetMetadata(src_dataset,band_names=None,description=None):
    '''Writes the seppo metadata to gdal file. If GTiff, sets the TIFFTAGs for DATETIME and SOFTWARE
    src_dataset can be filename or and open gdal.Dataset handle
    '''
    try:    
        if isinstance(src_dataset,str):
            img_handle=gdal.Open(src_dataset,gdal.GA_Update)
        elif isinstance(src_dataset,gdal.Dataset):
            image_name=src_dataset.GetFileList()[0]
            src_dataset=None
            img_handle=gdal.Open(image_name,gdal.GA_Update)
        else:
            print('Cannot set  Metadata. Invalid type: {}'.format(src_dataset))
            return
        gdalformat=img_handle.GetDriver().ShortName
        sw='TIFFTAG_SOFTWARE' if gdalformat.lower()=='gtiff' else 'SOFTWARE'
        now = time.strftime('%Y-%m-%d %H:%M:%S UTC%z',time.localtime())
        timestamp='TIFFTAG_DATETIME' if gdalformat.lower()=='gtiff' else 'DATETIME'
        md = img_handle.GetMetadata()
        md[sw]='SEPPO version 3.0.0'
        md[timestamp]=now
        if gdalformat.lower()=='gtiff':
            md['TIFFTAG_ARTIST']='info@earthbigdata.com'
            md['TIFFTAG_COPYRIGHT']='Earth Big Data LLC'
            if description:
                md['TIFFTAG_IMAGEDESCRIPTION']=description
        else:
            md['ARTIST']='Josef Kellndorfer, josef@earthbigdata.com'
            md['COPYRIGHT']='Earth Big Data LLC'
            if description:
                md['IMAGEDESCRIPTION']=description

        img_handle.SetMetadata(md)
        if description:
            img_handle.SetDescription(description)

        # Write the band metadata
        if band_names:
            if len(band_names) != img_handle.RasterCount:
                raise 'Mismatch in band nubmers and band labels'
            else:
                for idx in range(img_handle.RasterCount):
                    band=img_handle.GetRasterBand(idx+1)
                    bname=band_names[idx]
                    md={'Date':bname}
                    #print('Metadata',md)
                    band.SetDescription(bname)
                    band.SetMetadata(md)
                    band=None
        # Close or return handle
        if isinstance(src_dataset,str):
            img_handle=None
        else:
            src_dataset=img_handle
    except Exception as e:
        print('Exception in seppo_SetMetadata:',e)

def make_vrts(geotiffs,site_name='NoName'):
    # Lets group the geotiffs into paths and polarizations
    vrt_dict={}
    for geotiff in geotiffs:
        g_basename=os.path.basename(geotiff)
        tokens=geotiff.split('_')
        key=tokens[2:5]
        if not key in vrt_dict:
            vrt_dict[key]=[]
        vrt_dict[key].append(geotiff)

    for key in vrt_dict:
        vrtname=site_name.replace('_','')





def processing(args):

    filesystem = make_filesystem(args.keyfile)
    vrtlist    = make_vrtlist(args,filesystem)

    if not vrtlist:
        print('No Data found. Please check your parameters.')

    if args.verbose:
        print('VRTLIST:')
        for v in vrtlist:
            print(v)
        print()

    # Make geotiffs
    geotiffs=[]
    for vrtfile in vrtlist:
        print('\n***** Working on',vrtfile)
        geotiff = make_geotiff(vrtfile,args.dates,outdir=args.outdir,red=args.red,blue=args.blue,description=args.description,verbose=args.verbose,dryrun=args.dryrun)
        if geotiff:
            print('Produced',geotiff)
            geotiffs.append(geotiff)

    # Make vrts
    if not args.no_vrt:
        vrts = make_vrts(geotiffs,site=args.site_name)
    else:
        vrts= None 

    # Make RealEarth compatible products
    if args.make_realEarth and vrts:
        re_tiffs = make_realEarth(vrts)



def main(a):
    args = myargsparse(a)
    processing(args)


if __name__ == '__main__':
    main(sys.argv)


