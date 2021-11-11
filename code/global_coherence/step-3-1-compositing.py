#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import glob,os,sys,warnings,time
import multiprocessing as mp
import concurrent.futures as cf
import zipfile
import subprocess as sp
from functools import partial
from osgeo import gdal
import atexit
#import fsspec
import shutil
import numpy as np
import datetime as dt
import scipy.optimize
from numba import jit
warnings.filterwarnings("ignore")

def myargsparse(a):
    import argparse
    class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
        pass

    thisprog=os.path.basename(a[0])

    epilog=\
    """**************************************************************************************
    \n*            Calculate: 1) seaonsal mean of Amplitudes at co- and cross-polarization  *
    \n*                       2) seasonal median of coherences per repeat interval          *
    \n*                       3) fit rho-tau coherence model per season                     *
    \n*                                  v2.0, 2021-03-05, oc,jk                            *
    \n**************************************************************************************
    \nEXAMPLES:
    \n{thisprog} -i indir -o outdir  N50E010
    """.format(thisprog=thisprog)

    help_indir=\
    '''Directory where input files live'''
    help_outname=\
    '''Output directory root. Tileid will be added'''
    help_tileid=\
    '''Tileid'''   
    help_parallel=\
    '''Multithreaded processing with numpy or multiprocessing'''  
    help_no_rhotau=\
    '''Do not perform rho-tau-rmse modeling'''   

    p = argparse.ArgumentParser(usage=None,description=epilog,prog=thisprog,formatter_class=CustomFormatter)
    p.add_argument("-i","--indir",required=False,help=help_indir,action='store',default='s3://ebd-proc-21')
    p.add_argument("-o","--outdir",required=False,help=help_outname,action='store',default='s3://ebd-sentinel-1-l3-coherence')
    p.add_argument("-m","--parallel",required=False,help=help_parallel,action='store',choices=['numpy','multiprocessing'],default='multiprocessing')
    p.add_argument("-nrt","--no_rhotau",required=False,help=help_no_rhotau,action='store_true',default=False)
    p.add_argument("-v","--verbose",required=False,help='Verbose output',action='store_true',default=False)    
    p.add_argument("tileid",help=help_tileid,action='store')
    
    args=p.parse_args(a[1:])
    return args

# Rho-tau model - np.apply functions
@jit(parallel=True)
def fun0(p, x, y):
    return (1-p[0]) * np.exp(-x/p[1])+p[0]-y

@jit(parallel=True)
def fun1(x, p1, p2):
    return (1-p1) * np.exp(-x/p2)+p1

@jit(parallel=True)
def ts(y1,x,x0):
    res_lsq = scipy.optimize.least_squares(fun0, x0, args=(x, y1), method='lm')  
    if res_lsq.x[0] < 0:
        res_lsq = scipy.optimize.curve_fit(fun1, x, y1, p0=x0, method='trf', bounds=([0, 0], [1, np.inf]))
        return res_lsq[0]
    else:
        return res_lsq.x
             
# Funtion to calculate multi-temporal median
@jit(parallel=True)
def mtmedian(x):
    y=np.median(x)
    return y

# Funtion to calculate multi-temporal mean
@jit(parallel=True)
def mtmean(x):
    y=np.mean(x)
    return y

# Rho-tau model - Multiprocessing functions
def fun2(p, x, y):
    return (1-p[0]) * np.exp(-x/p[1])+p[0]-y

def fun3(x, p1, p2):
    return (1-p1) * np.exp(-x/p2)+p1

def ts2(y1,x,x0):
    res_lsq = scipy.optimize.least_squares(fun2, x0, args=(x, y1), method='lm')  
    if res_lsq.x[0] < 0:
        res_lsq = scipy.optimize.curve_fit(fun3, x, y1, p0=x0, method='trf', bounds=([0, 0], [1, np.inf]))
        return res_lsq[0]
    else:
        return res_lsq.x
    
def tsfit(stack,tb,id):       
    y1=stack[:,id].reshape(len(tb),)
    mdl = np.array([0, 0], dtype=float)
 
    x=tb[y1>0]
    y1=y1[y1>0] 

    x0 = np.array([0.5,4])
    if len(y1) >= 4:
        # Fit model     
        res_lsq = ts2 (y1,x,x0)
        mdl[0]=res_lsq[0] # When using scipy.optimize.least_squares
        mdl[1]=res_lsq[1]               
         
    return mdl

def rmtree(dirname):
    if os.path.exists(dirname):
        shutil.rmtree(dirname)

def remove(filename):
    if os.path.exists(filename):
        os.remove(filename)

def unzip(zipfilename,targetdir):
    z = zipfile.ZipFile(zipfilename,mode='r')
    z.extractall(path=targetdir)
    remove(zipfilename)


def make_inc_lsmap(indir,outdir):
    for ftype in ['inc','lsmap']:
        filelist=glob.glob(os.path.join(indir,f'*_{ftype}.tif'))
        if filelist:
            s1paths=set([os.path.basename(x).split('_')[1] for x in filelist])
            tileid=os.path.basename(filelist[0]).split('_')[0]
            for s1path in s1paths:
                optfile=[x for x in filelist if os.path.basename(x).split('_')[1]==s1path]
                if optfile:
                    outpath=os.path.dirname(optfile[0])
                    vrtname=os.path.join(outpath,f'{tileid}_{s1path}_{ftype}.vrt')
                    out=gdal.BuildVRT(vrtname,optfile,srcNodata=0,VRTNodata=0)
                    out=None
                    outname = os.path.join(outdir,f'{tileid}_{s1path}_{ftype}.tif')
                    out=gdal.Translate(outname,vrtname,noData=0,creationOptions=['COMPRESS=LZW'])
                    out=None
                    remove(vrtname)
                    for i in optfile:
                        remove(i)


def make_vrt(date,allfiles):
    optfile=[x for x in allfiles if x.find(date) > -1]
    tokens=os.path.basename(optfile[0]).split('_')
    tileid=tokens[0]
    s1path=tokens[1]
    pol = tokens[-2]
    ftype=tokens[-1].split('.')[0]
    outpath=os.path.dirname(optfile[0])
    vrtname=os.path.join(outpath,f'{tileid}_{s1path}_{date}_{pol}_{ftype}.vrt')
    out=gdal.BuildVRT(vrtname,optfile,srcNodata=0,VRTNodata=0)
    out=None
    return vrtname


def cache_data(args,outdir='/dev/shm'):
    # Cache from s3
    if args.indir.startswith('s3://'):
        indir=args.indir.rstrip('/')
        outpath=os.path.join(outdir,args.tileid)
        os.makedirs(outpath,exist_ok=True)
        cmd=f'aws s3 sync {indir}/{args.tileid} {outpath}'
        sp.check_call(cmd.split())
        atexit.register(rmtree,outpath)
    else:
        outpath=args.indir

    # Get the zipfiles 
    zipfiles=glob.glob(os.path.join(outpath,'*.zip'))
    # Unzip 
    # JOSEF TO FINISH
    workers=None  # Leave default

    pars=[(x,outpath) for x in zipfiles] 
    with cf.ThreadPoolExecutor(max_workers=workers) as executor:
        # Start the wrapper
        future_wrapper = {executor.submit(unzip, *par): par for par in pars}
        for future in cf.as_completed(future_wrapper):
            try:
                future.result(timeout=1800)  # Give it 30 minutes max
            except cf.TimeoutError as e:
                print('Timeout error',e)

    polarizations=list(set([x.split('_')[-2] for x in glob.glob(os.path.join(outpath,'*_AMP.tif'))]))


    workers=None  # Leave default
    for pol in polarizations:
        for ftype in ['AMP','COH']:
            if ftype=='COH' and pol[0]!=pol[1]:
                continue

            allfiles = glob.glob(os.path.join(outpath,f'*_{pol}_{ftype}.tif'))

            if ftype=='COH':
                dates = list(set(['_'.join(x.split('_')[-6:-4]) for x in allfiles]))
            else:
                dates = list(set([x.split('_')[-5] for x in allfiles]))

            dates.sort()

            pars=[(x,allfiles) for x in dates] 
            vrtnames=[]
            with cf.ThreadPoolExecutor(max_workers=workers) as executor:
                # Start the wrapper
                future_wrapper = {executor.submit(make_vrt, *par): par for par in pars}
                for future in cf.as_completed(future_wrapper):
                    try:
                        res = future.result(timeout=1800)  # Give it 30 minutes max
                        vrtnames.append(res)
                    except cf.TimeoutError as e:
                        print('Timeout error',e)


    return polarizations,outpath

def multi_stat(args,indir,polarization,ftype):

    print('********************************************************************')
    print('*       Calculate seasonal median/mean of coherence/backscatter    *')
    print('*                and fit rho/tau coherence model                   *')
    print('********************************************************************')
    print(' ')

    start = time.time()

    ##########################################################
    # Input files/parameters                                 #
    ##########################################################

    outdir     = args.outdir
    tileid     = args.tileid
    pol        = polarization
    parallel   = args.parallel

    indir=indir.rstrip('/')
    
    if args.outdir.startswith('s3://'):
        outdir=f'/dev/shm/s3/{tileid}'
        os.makedirs(outdir,exist_ok=True)
        s3outdir=os.path.join(args.outdir,tileid)
        atexit.register(rmtree,outdir)
    else:
        outdir=os.path.join(args.outdir,tileid)
        os.makedirs(outdir,exist_ok=True)
        s3outdir=None


    if args.verbose:
        print(f'local dir: {outdir}\ns3    dir: {s3outdir}\n{args}')

    ##########################################################
    # Generate Inc/Lsmap tifs                                #
    ##########################################################
    if ftype == "COH":
        make_inc_lsmap(indir,outdir)


    pattern = os.path.join(indir,f'*_{pol}_{ftype}.vrt')
    optfile=glob.glob(pattern)

    # In case no vrts are found for that ftype, do nothing
    if not optfile:
        return
    
    # Save Geotransform and Projection for writing geotiffs later
    ds = gdal.Open(optfile[0])
    geotrans = ds.GetGeoTransform()
    proj     = ds.GetProjection()
    ds = None

    ##########################################################
    # Calculate metrics                                      #
    ##########################################################
    if ftype == "COH":         
        seasonname=['winter','spring','summer','fall']
        season=np.zeros(len(optfile))
        repeat=np.zeros(len(optfile))
        for n,f in enumerate(optfile):
            a1=f.split('/')[-1].split('_')[2]  # assume tileid_153D_20191201_20200106
            a2=f.split('/')[-1].split('_')[3]
            acqdate1=dt.date(int(a1[0:4]),int(a1[4:6]),int(a1[6:8])).toordinal()
            acqdate2=dt.date(int(a2[0:4]),int(a2[4:6]),int(a2[6:8])).toordinal()
            repeat[n]=np.abs(acqdate2-acqdate1)
            cdate=dt.date.fromordinal(int(np.floor((acqdate1+acqdate2)/2)))   
            if cdate.month in [1,2,12]:
                season[n]=0
            elif cdate.month in [3,4,5]:
                season[n]=1
            elif cdate.month in [6,7,8]:
                season[n]=2  
            elif cdate.month in [9,10,11]:
                season[n]=3    
        seasons=np.unique(season)
        repeats=np.unique(repeat)
        for s in seasons:
            stack_med_exist=False
            for rc,r in enumerate(repeats):
                stack_all_exist=False
                mask=(season==s)*(repeat==r)
                tb_all=repeat[mask]
                if mask.sum()>0:
                    selectlist=[]
                    for n,f in enumerate(optfile):   
                        if mask[n]==True:
                            selectlist.append(f)                    
                    for n,f in enumerate(selectlist):            
                        ds = gdal.Open(f)
                        im = np.float32(ds.ReadAsArray())
                        ds = None
                        [rows, cols] = im.shape
                        if not stack_all_exist:
                            stack_all = np.zeros((len(selectlist),rows*cols), dtype=np.float32)
                            stack_all_exist=True
                        stack_all[n,:]=im.reshape((rows*cols))
                        
                    # Crate masked array  and estimate median
                    stack_all_masked = np.ma.array(stack_all,mask=stack_all==0)
                    stack_all=None
                    #med= np.ma.apply_along_axis(mtmedian,0,stack_all_masked)
                    med=np.ma.median(stack_all_masked,0)
                    stack_all_masked=None

                    if not stack_med_exist:
                        stack_med=np.zeros((len(repeats),rows*cols), dtype=np.float32)
                        tb_med=np.zeros(len(repeats))
                        stack_med_exist=True
                    stack_med[rc,:]=med/100
                    tb_med[rc]=r
                    
                    # Save
                    of = outdir + '/' + tileid  + '_' + seasonname[int(s)] + '_' + pol +'_COH' + f'{int(r):02d}' + '.tif'
                    driver = gdal.GetDriverByName("GTiff")
                    outdata = driver.Create(of, cols, rows, 1, gdal.GDT_Byte,  options = [ 'COMPRESS=LZW' ])
                    outdata.SetGeoTransform(geotrans)         
                    outdata.SetProjection(proj)             
                    outdata.GetRasterBand(1).WriteArray(np.uint8(med.reshape((rows,cols))))
                    outdata.GetRasterBand(1).SetNoDataValue(0)
                    outdata.FlushCache()
                    outdata = None
            
            # Rho/tau modeling
            if not args.no_rhotau:
                if parallel=='numpy':
                    stack_med_masked = np.ma.array(stack_med,mask=stack_med==0)
                    x0=np.array([0.1, 4])
                    rhotau = np.ma.apply_along_axis(ts,0,stack_med_masked,tb_med,x0)
                elif parallel=='multiprocessing':
                    id=np.arange(cols*rows)
                    a_pool = mp.Pool()
                    func = partial(tsfit, stack_med, tb_med)
                    mdl = a_pool.map(func, id)
                    a_pool.close()
        
                    rhotau=np.zeros((2,rows*cols), dtype=np.float32)
                    for vc in range(len(id)):
                        rhotau[0,vc]=mdl[vc][0]
                        rhotau[1,vc]=mdl[vc][1]
                    
                # clear stacks
                stack_med=None
                stack_med_masked=None
                stack_all_exist=False
                stack_med_exist=False
                        
                # Model RMSE estimation -  Load all coherences per season
                stack_all_exist=False
                mask=(season==s)
                tb_all=repeat[mask]


                if mask.sum()>0:
                    selectlist=[]
                    for n,f in enumerate(optfile):   
                        if mask[n]==True:
                            selectlist.append(f)                    
                    for n,f in enumerate(selectlist):            
                        ds = gdal.Open(f)
                        im = np.float32(ds.ReadAsArray())
                        ds = None
                        remove(f)
                        [rows, cols] = im.shape
                        if not stack_all_exist:
                            stack_all = np.zeros((len(selectlist),rows*cols), dtype=np.float32)
                            stack_all_exist=True
                        stack_all[n,:]=im.reshape((rows*cols))/100
                

                rho=np.repeat(rhotau[0,:].reshape(1,cols*rows),len(tb_all),axis=0)
                tau=np.repeat(rhotau[1,:].reshape(1,cols*rows),len(tb_all),axis=0)
                tb=np.repeat(tb_all.reshape(len(tb_all),1),cols*rows,axis=1)
                residuals=((1-rho) * np.exp(-tb/tau)+rho)-stack_all
                residuals_masked = np.ma.array(residuals,mask=stack_all==0)
                model_rmse=np.ma.std(residuals_masked,0)
                residuals_masked=None
                stack_all=None
                stack_all_exist=False
                rho=None
                tau=None
                tb=None
                # Output array
                outarr=np.zeros((3,rows*cols),dtype=np.float32)
                outarr[0:2,:]=rhotau
                outarr[2,:]=model_rmse

                outarr=outarr*1000.
                outarr[outarr>65535.]=65535

                outarr=np.uint16(np.ceil(outarr))

                # Save maps
                for b,modelout in enumerate(['rho','tau','rmse']):
                    outfile = os.path.join(outdir,f'{tileid}_{seasonname[int(s)]}_{pol}_{modelout}.tif')
                    driver = gdal.GetDriverByName('GTiff')
                    outdata = driver.Create(outfile, cols, rows, 1, gdal.GDT_UInt16,  options = ['COMPRESS=LZW'])
                    outdata.SetGeoTransform(geotrans)
                    outdata.SetProjection(proj)
                    outdata.GetRasterBand(1).WriteArray(outarr[b,:].reshape((rows,cols)))
                    outdata.GetRasterBand(1).SetNoDataValue(0)
                    outdata.FlushCache()
                    outdata = None
                outarr=None
                rhotau=None


    elif ftype == "AMP":
        seasonname=['winter','spring','summer','fall']
        season=np.zeros(len(optfile))
        for n,f in enumerate(optfile):
            a=f.split('/')[-1].split('_')[2]  # assume tileid_153D_20191201
            acqdate=dt.date(int(a[0:4]),int(a[4:6]),int(a[6:8])).toordinal()
            cdate=dt.date.fromordinal(int(acqdate))   
            if cdate.month in [1,2,12]:
                season[n]=0
            elif cdate.month in [3,4,5]:
                season[n]=1
            elif cdate.month in [6,7,8]:
                season[n]=2  
            elif cdate.month in [9,10,11]:
                season[n]=3    
        seasons=np.unique(season)
        
        for s in seasons:
            mask=(season==s)
            if mask.sum()>0:
                selectlist=[]
                for n,f in enumerate(optfile):   
                    if mask[n]==True:
                        selectlist.append(f)                    
                for n,f in enumerate(selectlist):            
                    ds = gdal.Open(f)
                    band = ds.GetRasterBand(1)
                    ot=ds.GetRasterBand(1).DataType
                    im = np.float32(band.ReadAsArray())
                    band=None
                    ds=None
                    remove(f)
                    [rows, cols] = im.shape
                    if n == 0:
                        arr = np.zeros((len(selectlist),rows*cols))
                    arr[n,:]=im.reshape((rows*cols))

                # Crate masked array  and estimate mean
                arr_masked = np.ma.array(arr,mask=arr==0)
                arr=None
                #med= np.ma.apply_along_axis(mtmean,0,arr_masked)
                med=np.ma.mean(arr_masked,0)
                arr_masked=None
                
                #Save result       
                outfile = os.path.join(outdir,f'{tileid}_{seasonname[int(s)]}_{pol}_AMP.tif')
                driver = gdal.GetDriverByName("GTiff")
                outdata = driver.Create(outfile, cols, rows, 1, ot,  options = [ 'COMPRESS=LZW' ])
                outdata.SetGeoTransform(geotrans)         
                outdata.SetProjection(proj)             
                outdata.GetRasterBand(1).WriteArray(np.uint16(med.reshape((rows,cols))))
                outdata.GetRasterBand(1).SetNoDataValue(0)
                outdata.FlushCache()
                outdata = None

    #########################################################################################
    # output to s3 and cleanup                                                              #
    #########################################################################################
    if s3outdir:
        cmd=f'aws s3 sync {outdir} {s3outdir}'
        print(f'***** Output to s3:\n{cmd}')
        sp.check_call(cmd.split())
        rmtree(outdir)
    
    #########################################################################################
    # Compute and display execution time                                                    #
    #########################################################################################
    end = time.time()
    diff=end-start
    print(('Processed in ' + str(diff) + ' s'))


def processing(args):
    polarizations,cachedir = cache_data(args)
    # Coherence:
    for polarization in polarizations:
        # only for likepol case:
        if polarization[0]==polarization[1]:
            multi_stat(args,cachedir,polarization,'COH')
    # AMPLITUDES
    for polarization in polarizations:
        multi_stat(args,cachedir,polarization,'AMP')

    # Cleanup cachedir
    rmtree(cachedir)

#########################################################################
def main(a):
    args= myargsparse(a)   
    res = processing(args)


if __name__ == '__main__':
    main(sys.argv)
