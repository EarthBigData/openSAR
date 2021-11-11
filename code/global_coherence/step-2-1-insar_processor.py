#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import time
import numpy as np
import py_gamma as pg
import gdal
import datetime
import atexit
import glob

def myargsparse():
    import argparse

    thisprog=os.path.basename(sys.argv[0])

    ############################################################################
    # define some strings for parsing and help
    ############################################################################

    epilog=\
    """**********************************************************************************************************
    \n*                                GAMMA S1 InSAR processor, v1.0, 2020-12-14, oc                           *
    \n* InSAR Processing of multi-temporal stack of S1 SLCs with equal number of bursts in all three sub-swaths *
    \n*                                                                                                         *
    \n*                                                                                                         *
    \n* Input and options:                                                                                      *
    \n* 1)  List of tabfiles for a burst segment (copol SLCs)                                                   *
    \n* 2)  List of tabfiles for a burst segment (crosspol SLCs)                                                *
    \n* 3)  Output directory                                                                                    *
    \n* 4)  Data directory                                                                                      *    
    \n* 5)  Input DEM incl. absolute path                                                                       *
    \n* 6)  Multi-looking factors in range and azimuth, e.g. 10x2                                               *
    \n*                                                                                                         *
    \n* Output:                                                                                                 *
    \n* 1) Geocoded, topographically corrected backscatter and coherence images in one or two polarizations     *
    \n* 2) Local incidence angle map in degrees                                                                 *
    \n* 3) Layover / shadow mask                                                                                *
    \n*                                                                                                         *
    \n* Backscatter images are scaled to 16-bit Amplitudes (AMP) where dB=20*log10(AMP)-83                      *    
    \n* Coherence images are scaled to 8-bit format with CC*100                                                 *
    \n*                                                                                                         *
    \n* All image files are tiled to a 1x 1 degree grid                                                         *    
    \n*                                                                                                         *    
    \n***********************************************************************************************************
    \nEXAMPLES:
    \n{thisprog} -t1 $PATH/tabsvv* -t2 $PATH/tabsvh* -o /home/user/ -m 10 2 -d /home/user/dem.tif -i  /home/user/data/
     """.format(thisprog=thisprog)

    help_tabfile1=\
    '''List of tabfiles for each burst segment in copol'''
    help_tabfile2=\
    '''List of tabfiles for each burst segment in crosspol'''    
    help_outdir=\
    '''Output directory '''
    help_datadir=\
    '''Data directory '''    
    help_deminp=\
    '''DEM filenames. DEMs needs to be in a gdal readable format, e.g. VRT, GTIFF, HGT, ..., or in GAMMA format with associated dem_par file '''
    help_ml=\
    '''Multilooking factors in range and azimuth'''
    help_q=\
    '''Verbose Mode'''
    
    p = argparse.ArgumentParser(usage=None,description=epilog,prog=thisprog,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-o",required=False,help=help_outdir,action='store',dest='outdir',default=os.getcwd())
    p.add_argument("-i",required=True,help=help_datadir,action='store',dest='datadir',default=None)    
    p.add_argument("-t1",required=True,help=help_tabfile1,action='store',dest='tablist1',default=None,nargs='*')
    p.add_argument("-t2",required=False,help=help_tabfile2,action='store',dest='tablist2',default=False,nargs='*')    
    p.add_argument("-d",required=True,help=help_deminp,action='store',dest='dems',default=None,nargs='*')
    p.add_argument("-m",required=True,help=help_ml,action='store',dest='ml',default=None,type=int,nargs=2)
    p.add_argument("-v",required=False,help=help_q,action='store_true',dest='verbose',default=False)    

    args=p.parse_args()
    args.outdir = args.outdir.rstrip('/') + '/'
    return args

#########################################################################
# Function to be called by atexit when script stops
def delfun(dirname):
    shutil.rmtree(dirname)
    
#########################################################################
# Function to rename filenames in tabfiles
def tabfile_rename(tabfilein,tabfileout,regexp_before,regexp_after):
    tab = pg.read_tab(tabfilein, as_list = True, dtype = str, transpose = False)  
    tabout=tab.copy()
    r=len(tab)
    c=sum(1 for x in tab if isinstance(x, list))
    if c>0:
        for ri in range(r):
            for ci in range(c):
                l=tab[ri][ci]
                tabout[ri][ci]=l.replace(regexp_before,regexp_after)
    else:
        for ri in range(r):
                l=tab[ri]
                tabout[ri]=l.replace(regexp_before,regexp_after)        
    pg.write_tab(tabout, tabfileout)  
    
#########################################################################
# Function to remove paths in tabfiles
def tabfile_remove_path(tabfilein,tabfileout):
    tab = pg.read_tab(tabfilein, as_list = True, dtype = str, transpose = False)  
    tabout=tab.copy()    
    r=len(tab)
    c=sum(1 for x in tab if isinstance(x, list))
    if c>0:
        for ri in range(r):
            for ci in range(c):
                l=tab[ri][ci]
                tabout[ri][ci]=l.rsplit('/')[-1]
    else:
        for ri in range(r):
            l=tab[ri]
            tabout[ri]=l.rsplit('/')[-1]        
    pg.write_tab(tabout, tabfileout)      

#########################################################################
# Function to add paths in tabfiles
def tabfile_add_path(tabfilein,tabfileout,fpath):
    tab = pg.read_tab(tabfilein, as_list = True, dtype = str, transpose = False)      
    tabout=tab.copy()
    fpath=fpath.rstrip('/')
    r=len(tab)
    c=sum(1 for x in tab if isinstance(x, list))
    if c>0:
        for ri in range(r):
            for ci in range(c):
                l=tab[ri][ci]
                tabout[ri][ci]=fpath + '/' + l
    else:
        for ri in range(r):
            l=tab[ri]
            tabout[ri]=fpath + '/' + l        
    pg.write_tab(tabout, tabfileout)  

#########################################################################
# Function to copy files listed in first tabfile with output filenames 
# according to the second tabfile 
def copytab(tabfilein,tabfileout):
    tab1 = pg.read_tab(tabfilein, as_list = True, dtype = str, transpose = False)  
    tab2 = pg.read_tab(tabfileout, as_list = True, dtype = str, transpose = False)
    r=len(tab1)
    c=sum(1 for x in tab1 if isinstance(x, list))
    if c>0:
        for ri in range(r):
            for ci in range(1,c):
                l1=tab1[ri][ci]
                l2=tab2[ri][ci]
                shutil.copy(l1,l2)
    else:
        for ri in range(1,r):
            l1=tab1[ri]
            l2=tab2[ri]
            shutil.copy(l1,l2)
                
#########################################################################
# Count number of bursts
def burstcount(tabfilein):
    tab1 = pg.read_tab(tabfilein, as_list = True, dtype = str, transpose = False)  
    r=len(tab1)
    c=sum(1 for x in tab1 if isinstance(x, list))
    bc=0
    if c>0:
        for ri in range(r):
            topspar=tab1[ri][2]
            tpardict=pg.ParFile(topspar)
            bc=bc+int(tpardict.get_value('number_of_bursts'))
    else:
        topspar=tab1[2]
        tpardict=pg.ParFile(topspar)
        bc=bc+int(tpardict.get_value('number_of_bursts'))        
    return bc

#########################################################################
# Function to delete files listed in tabfiles
def deltab(tabfile):
    tab=pg.read_tab(tabfile, as_list = True, dtype = str, transpose = False)
    c=sum(1 for x in tab if isinstance(x, list))
    if c>0:
        for l1 in tab:
            for l2 in l1:
                os.remove(l2)     
    else:                 
        for l in tab:
            os.remove(l)
             
#########################################################################
# Function to check if files listed in tabfile exist
def tabexist(tabfile):
    tab=pg.read_tab(tabfile, as_list = True, dtype = str, transpose = False)
    out=True
    c=sum(1 for x in tab if isinstance(x, list))
    if c>0:
        for l1 in tab:
            for l2 in l1:
                out=os.path.isfile(l2)
    else:
        for l1 in tab:
            out=os.path.isfile(l1)        
    return out

#########################################################################
# Function to convert from PWR to AMP (JAXA scaling)
def pwr2amp(mli,amp): 
    pwr = np.fromfile(mli, dtype='>f', count=-1)
    mask=(pwr>0) * (pwr<0.0001)
    pwr[mask]=0.0001
    m = pwr>0
    dn=np.zeros(pwr.shape)
    dn[m]=10.0**((10.0*np.log10(pwr[m])+83.0)/20.0)
    dn[dn<1]=1
    dn[dn>32766]=32766
    dn[ pwr == 0 ] = 0
    dn.astype('int16').byteswap().tofile(amp)
    
#########################################################################
# Function to scale coherence to Byte
def ccbyte(cc,ccb): 
    img = np.fromfile(cc, dtype='>f', count=-1)
    img=img*100
    mask=(img>0) * (img<1)
    img[mask]=1
    img[img>100]=100
    img.astype('uint8').tofile(ccb)   

#########################################################################
# Function to scale coherence to Byte
def rad2deg(radin,degout):
    img = np.fromfile(radin, dtype='>f', count=-1)
    img=img*np.pi/180
    mask=(img>0) * (img<1)
    img[mask]=1
    img[img>100]=100
    img.astype('uint8').tofile(degout)
        
#########################################################################
def insar(args):
    
    # Start time
    start = time.time()

    ##########################################################
    # Define Input/Output filenames/processing parameters    #
    ##########################################################

    tablist_co = args.tablist1           # List of tab files
    tablist_cr = args.tablist2           # List of tab files
    outdir     = args.outdir             # Output directory
    datadir    = args.datadir            # Data directory
    demfile    = args.dems               # DEMs
    ml         = args.ml                 # Multilooking factors
    q          = args.verbose            # Verbose mode
   
    DEVEL=False
    if DEVEL:
        datadir='/cluster/raid/home/oliver/S1_coherence_new/SLC/bursts/'
        outdir='/cluster/raid/home/oliver/S1_coherence_new/SLC/testout/'
        tablist_co=glob.glob('/cluster/raid/home/oliver/S1_coherence_new/SLC/segments/144/*vv*85315_85386*s3')
        tablist_cr=glob.glob('/cluster/raid/home/oliver/S1_coherence_new/SLC/segments/144/*vh*85315_85386*s3')
        ml=[12,3]
        q=True
        demfile=['/cluster/raid/data/DEM/Copernicus_DEM/copdem.vrt']
    
    # Process crosspol coherence
    crosspolcoh=False

    # Process one or two polarizations
    if tablist_cr == False:
        dp=False
    else:
        dp=True
            
    demfile=demfile[0]
    outdir=outdir.rstrip('/') 
    
    # Multilooking factors in range and azimuth
    ml_rg = int(ml[0])
    ml_az = int(ml[1])
    
    # Size of COHERENCE estimation window
    CC_WIN_MIN=3
    CC_WIN_MAX=7
        
    # Number of tabfiles
    imno=len(tablist_co)
    acqid=np.arange(imno, dtype=np.int32)
    
    # Target resolution (HARDCODE --> maybe add option in argparse)
    tr_x=0.000833333330000
    tr_y=-0.000833333330000
    
    # Add correct directory in tabfiles
    for i,f in enumerate(tablist_co): 
        tabfile_remove_path(f,f)
        tabfile_add_path(f,f,datadir)
    if dp:
        for i,f in enumerate(tablist_cr): 
            tabfile_remove_path(f,f)
            tabfile_add_path(f,f,datadir)            
    
    # Extract IW polarization mode and acquisition date from tab filename
    # assume tab filename: ${relpath}_${acqdate}_${pol}_${minburstid}_${maxburstid} paus
    acqdate= np.zeros(imno, dtype='int32') 
    yr = np.zeros(imno, dtype='int32')
    acqdate_cal= []
    for i,f in enumerate(tablist_co): 
        a=f.rpartition('/')[-1].split('_')[1]
        acqdate_cal.append(a)
        yr[i]=int(a[0:4])
        a=datetime.date(int(a[0:4]),int(a[4:6]),int(a[6:8]))
        acqdate[i]=a.toordinal()
        relpath=f.rpartition('/')[-1].split('_')[0]        
        refpol=f.rpartition('/')[-1].split('_')[2]
        minburstid=f.rpartition('/')[-1].split('_')[3]
        maxburstid=f.rpartition('/')[-1].split('_')[4]
    
    # Define second polarization
    if dp:
        if refpol=='vv':
            secpol='vh'
        elif refpol=='hh':
            secpol='hv' 
        pols=[refpol,secpol]
    else:
        pols=refpol
    
    # Output directory
    outdir = outdir.rstrip('/') + '/'
    if os.path.isdir(outdir) == False:
        os.mkdir(outdir)    
    
    # Define temporary working directory and filenames
    tfile = relpath + '_' + minburstid + '_' + maxburstid
    tpath = outdir + 'gamma_' + tfile + '_' + str(abs(np.random.randn())).replace('.','') + '/'
    #tpath = '/scratch/gamma_' + tfile + '_' + str(abs(np.random.randn())).replace('.','') + '/'   # --> we will need scratch space on AWS
    os.mkdir(tpath)
    os.chdir(tpath)
    
    # Delete temporary working directory when script stops
    atexit.register(delfun, tpath)

    # Define name of log files
    logout= outdir + tfile + '.log'
    errout= outdir + tfile + '.err'
       
    ###########################################################################
    # Select reference SLC segment
    # Criteria: 1 - Maximum number of bursts, 2 - a central date in the time series
    bno=np.arange(imno, dtype=np.int32)
    for i,ff in enumerate(tablist_co):
        bno[i]=burstcount(ff)
        
    potential_scenes=acqid[bno==np.max(bno)]
    acqdate_potential=acqdate[potential_scenes]
    
    ac=datetime.date(int(np.median(yr)),int(7),int(1))
    ac=ac.toordinal()
    diffacq=np.abs(ac-acqdate_potential)
    acq_selected=acqdate_potential[diffacq==np.min(diffacq)][0]
    ref_selected=int(acqid[acqdate==acq_selected])
    
    refdate=acqdate[ref_selected]
    refdate_cal=acqdate_cal[ref_selected]
    
    refslc_co_tab = tpath + tfile + '_' + str(refdate_cal) + '_' + refpol + '_slctab'
    shutil.copy(tablist_co[ref_selected],refslc_co_tab)
    if dp:
        refslc_cr_tab = tpath + tfile + '_' + str(refdate_cal) + '_' + secpol + '_slctab' 
        shutil.copy(tablist_cr[ref_selected],refslc_cr_tab)
    
    ###########################################################################
    # Print Summary   
    print(' ')
    print('Number of SLCs:                       ' + str(imno))
    print('Reference scene:                      ' + refdate_cal)
    print('Multi-looking factors:                ' + str(ml_rg) + 'x' + str(ml_az))
    print('Target Resolution:                    ' + str(tr_x))
    print('Adaptive coherence estimation window: ' + str(CC_WIN_MIN) + '-' + str(CC_WIN_MAX))
    print('Polarizations:                        ' + str(pols))
   
    #########################################################################################
    # Select image combinations to compute 6-, 12-, ... repeat intervals     
    print(' ')                            
    image_pairs=[]
    for im1 in acqdate:
        for im2 in acqdate:
            if im2>im1:
                if (im2-im1) in [6,12,18,24,36,48]:
                    image_pairs.append([im1,im2,im2-im1])
             
    # Count number of 6-day image pairs per season to decide wether multiple of 6- or 12-day repeat intervals are to be processed
    no06=np.zeros(4, dtype=np.int16)
    for p in image_pairs:
        cdate=datetime.date.fromordinal(int(np.floor((p[1]+p[0])/2)))   
        if cdate.month in [1,2,12]:
            season=0
        elif cdate.month in [3,4,5]:
            season=1
        elif cdate.month in [6,7,8]:
            season=2  
        elif cdate.month in [9,10,11]:
            season=3                   
        if p[2]==6:
            no06[int(season)]=no06[int(season)]+1    
            
    # Select image pairs        
    image_pairs_select=[]
    if np.min(no06)<8:       
        # if only few/no image pairs with 6-day repeat orbits have been acquired,
        # calculate only 12,24,36,48 repeat interval coherences
        print('Calculate 12,24,36,48-day repeat-pass coherence') 
        for p in image_pairs:
            if (np.int32(p[2])!=6) * (np.int32(p[2])!=18):
                image_pairs_select.append(p) 
                date1=p[0]
                date2=p[1]
                id1    = int(acqid[np.int32(acqdate)==np.int32(date1)])
                id2    = int(acqid[np.int32(acqdate)==np.int32(date2)])
                date1f = acqdate_cal[id1]
                date2f = acqdate_cal[id2]
    else:
        # If 6-day repeat-pass images were acquired consistently, compute 6,12,18,24
        # repeat intervals     
        print('Calculate 6,12,18,24-day repeat-pass coherence')   
        for p in image_pairs:
            if (np.int32(p[2])!=36) * (np.int32(p[2])!=48):
                image_pairs_select.append(p)
                date1=p[0]
                date2=p[1]
                id1    = int(acqid[acqdate==date1])
                id2    = int(acqid[acqdate==date2])
                date1f = acqdate_cal[id1]
                date2f = acqdate_cal[id2]
    print('Number of image pairs for which coherence will be calculated: ' + str(len(image_pairs_select)))
    print(' ')
    print('Start Processing')
                
    ###########################################################################
    # Mosaic and multilook reference SLC segment        --> section nneds to be updated in AWS scripts  
    print('Multilook and mosaic reference SLC')  
    
    # SLC mosaic par only required for phase_sim_orb  
    refslc_co_img = tpath + tfile + '_' + str(refdate_cal) + '_' + refpol + '_mos_slc'
    refslc_co_par = tpath + tfile + '_' + str(refdate_cal) + '_' + refpol + '_mos_slc.par'       
    pg.SLC_mosaic_S1_TOPS(refslc_co_tab,refslc_co_img,refslc_co_par,ml_rg,ml_az, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)    
    os.remove(refslc_co_img)
    
    # Create burst MLIs and then mosaic
    refmli_co_tab = tpath + tfile + '_' + str(refdate_cal) + '_' + refpol + '_mlitab'
    tabfile_rename(refslc_co_tab,refmli_co_tab,'slc','mli')  
    tabfile_remove_path(refmli_co_tab, refmli_co_tab)
    tabfile_add_path(refmli_co_tab,refmli_co_tab,tpath)  
    pg.ScanSAR_burst_MLI(refslc_co_tab,refmli_co_tab,ml_rg,ml_az,0, '-', logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)        
    refmli_co_img = tpath + tfile + '_' + str(refdate_cal) + '_' + refpol + '_mos_mli' 
    refmli_co_par = tpath + tfile + '_' + str(refdate_cal) + '_' + refpol + '_mos_mli.par'     
    pg.ScanSAR_burst_to_mosaic(refmli_co_tab,refmli_co_img,refmli_co_par,1,'-',1,1, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
    if dp:
        refmli_cr_tab = tpath + tfile + '_' + str(refdate_cal) + '_' + secpol + '_mlitab'
        tabfile_rename(refslc_cr_tab,refmli_cr_tab,'slc','mli')  
        tabfile_remove_path(refmli_cr_tab, refmli_cr_tab)
        tabfile_add_path(refmli_cr_tab,refmli_cr_tab,tpath)       
        pg.ScanSAR_burst_MLI(refslc_cr_tab,refmli_cr_tab,ml_rg,ml_az,0, '-', logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)        
        refmli_cr_img = tpath + tfile + '_' + str(refdate_cal) + '_' + secpol + '_mos_mli' 
        refmli_cr_par = tpath + tfile + '_' + str(refdate_cal) + '_' + secpol + '_mos_mli.par'     
        pg.ScanSAR_burst_to_mosaic(refmli_cr_tab,refmli_cr_img,refmli_cr_par,1,'-',1,1, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
            
    # Read width of reference MLIs from parfile
    mlidict=pg.ParFile(refmli_co_par)
    mli1_width=int(mlidict.get_value('range_samples'))
    mli1_lines=int(mlidict.get_value('azimuth_lines'))

    ###########################################################################
    # Prepare DEM
    print('Prepare DEM')
    dem_handle = gdal.Open(demfile,gdal.GA_ReadOnly)

    # Determine extent of input DEM
    demresx=dem_handle.GetGeoTransform()[1]
    demresy=dem_handle.GetGeoTransform()[-1]
    dem_ulx=dem_handle.GetGeoTransform()[0]
    dem_uly=dem_handle.GetGeoTransform()[-3]
   
    # Create dem.par for required DEM subset
    dem    = tpath + tfile + '_dem'
    dempar = tpath + tfile + '_dem.par'
    pg.create_dem_par(dempar,refmli_co_par,0.0,tr_y,tr_x,4326,0, logf = logout, errf = logout, stdout_flag = q, stderr_flag = q)
    
    # Match corner coordinate of subset to be imported with pixel grid defined by global DEM 
    demdict=pg.ParFile(dempar)
    cl=demdict.get_dict(key='corner_lat')
    corner_north=np.float32(cl['corner_lat'][0])
    cl=demdict.get_dict(key='corner_lon')
    corner_east=np.float32(cl['corner_lon'][0])

    corner_east=dem_ulx-(np.floor((dem_ulx-(corner_east-demresx))/demresx)*demresx)+demresx/2
    corner_north=dem_uly-(np.floor((dem_uly-(corner_north-demresy))/demresy)*demresy)+demresy/2

    demdict.set_value('corner_lat', corner_north, index=0)
    demdict.set_value('corner_lon', corner_east, index=0)
    demdict.write_par(dempar)
    
    # Import DEM
    pg.dem_import(demfile,dem,dempar,0,0, pg.which('egm2008-5.dem'), pg.which('egm2008-5.dem_par'),0,'-','-',1, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)

    ###########################################################################
    # Create geocoding look-up table
    print('Create geocoding look-up table')
    geo2rdc = tpath + tfile + '_lt'
    inc     = tpath + tfile + '_inc'
    lsmap   = tpath + tfile + '_lsmap' 
    gcmapsuccess=pg.gc_map2(refmli_co_par, dempar, dem, '-', '-', geo2rdc, 1, 1, lsmap, '-', inc, '-', '-', '-', '-', '-', '-', '-', 0.25, 3, '-', '-', '-', '-', '-', logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
    if gcmapsuccess!=0:
        cmd='Creation of geocoding lookup table failed'
        text_file = open(errout, "a")
        text_file.write(cmd + '\n')
        text_file.close()
        raise RuntimeError ('Creation of geocoding lookup table failed')
        quit
    
    gcdemdict=pg.ParFile(dempar)
    dem_width=int(gcdemdict.get_value('width'))
    
    # Calculate pixel area normalization factor
    sig2gamratio = tpath + tfile + '_sig2gam'
    pix_sigma    = tpath + tfile + '_pixsigma'
    pix          = tpath + tfile + '_pix'
    # Use new option in pixel_area to compute gamma0 directly --> update "10" on AWS
    pg.pixel_area(refmli_co_par, dempar, dem, geo2rdc, lsmap, inc, pix_sigma,'-',10,'-','-','-', sig2gamratio, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
    pg.fill_gaps(sig2gamratio,mli1_width,pix,0,4,0,1, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
    os.remove(sig2gamratio)

    # Check accuracy of geocoding lookup table
    try:
        fineregout = outdir + '/' + relpath + '_' + str(refdate_cal) + '_' + minburstid + '_' + maxburstid + '_geo2rdc.log'
        diffpar=tpath + tfile + '_diff.par'
        pg.create_diff_par(refmli_co_par, '-', diffpar, 1, 0, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)

        offs     = tpath + tfile + '_offs'
        ccp      = tpath + tfile + '_ccp'
        offsets  = tpath + tfile + '_offsets'
        pg.offset_pwrm(pix_sigma, refmli_co_img, diffpar, offs, ccp, 64, 64, offsets, '-', 32, 32, 0.15, logf = fineregout, errf = errout, stdout_flag = q, stderr_flag = q)

        coffs    = tpath + tfile + '_coffs'
        coffsets = tpath + tfile + '_coffsets'
        pg.offset_fitm(offs, ccp, diffpar, coffs, coffsets, 0.15, 1, 0, logf = fineregout, errf = errout, stdout_flag = q, stderr_flag = q)
        
        # Delete temporary files
        os.remove(diffpar)
        os.remove(offs)
        os.remove(ccp)
        os.remove(offsets)
        os.remove(coffs)
        os.remove(coffsets)
    except:
        cmd='Check of accuracy of geocoding lookup table not possible'
        text_file = open(errout, "a")
        text_file.write(cmd + '\n')
        text_file.close()
     
    # Delete temporary files       
    os.remove(pix_sigma)
    
    # resample DEM to RDC geometry
    hgt = tpath + tfile + '_rdc.hgt'
    pg.geocode(geo2rdc,dem,dem_width,hgt,mli1_width,mli1_lines,'-' ,0, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)

    ###########################################################################
    # Co-registration     
    ints=10
    intv=10
    if imno<11:
        ints=int(100/imno)
        intv=int(100/imno)       
    print('Co-registration [%]: 0..', end='', flush=True)  
    for i,ff in enumerate(tablist_co):
        depslc_co_tab=tablist_co[i]
        if dp:
            depslc_cr_tab=tablist_cr[i]
        depdate=acqdate[i]
        depdate_cal=acqdate_cal[i]
        
        if depdate!=refdate:            
            # Create additional tab files
            depslc_rco_tab = tpath + tfile + '_' + str(depdate_cal) + '_' + refpol + '_slctab'
            tabfile_rename(depslc_co_tab,depslc_rco_tab,'.slc','.rslc')
            tabfile_remove_path(depslc_rco_tab,depslc_rco_tab)
            tabfile_add_path(depslc_rco_tab,depslc_rco_tab,tpath)             
            
            if dp:
                depslc_rcr_tab = tpath + tfile + '_' + str(depdate_cal) + '_' + secpol + '_slctab'
                tabfile_rename(depslc_cr_tab,depslc_rcr_tab,'.slc','.rslc')  
                tabfile_remove_path(depslc_rcr_tab,depslc_rcr_tab)
                tabfile_add_path(depslc_rcr_tab,depslc_rcr_tab,tpath)                  
                
                # List of tabfiles for reference burst segment    
                SLC1_tab_list_v=[[refslc_co_tab], [refslc_cr_tab]]                
                SLC1_ID_list_v=[[str(refdate_cal) + '_' + refpol],[str(refdate_cal) + '_' + secpol]]
                # List of tabfiles for dependent burst segment    
                SLC2_tab_list_v=[[depslc_co_tab], [depslc_cr_tab]]
                SLC2_ID_list_v=[[str(depdate_cal) + '_' + refpol],[str(depdate_cal) + '_' + secpol]]
                # List of tabfiles for co-registered burst segment       
                RSLC2_tab_list_v=[[depslc_rco_tab], [depslc_rcr_tab]]
                
                pg.write_tab(SLC1_tab_list_v, tpath + 'SLC1_tab_list')
                pg.write_tab(SLC1_ID_list_v, tpath + 'SLC1_ID_list')
                pg.write_tab(SLC2_tab_list_v, tpath + 'SLC2_tab_list')
                pg.write_tab(SLC2_ID_list_v, tpath + 'SLC2_ID_list')
                pg.write_tab(RSLC2_tab_list_v, tpath + 'RSLC2_tab_list')  
                
                # Start co-registration 
                pg.ScanSAR_coreg_pol(tpath + 'SLC1_tab_list',tpath + 'SLC1_ID_list',tpath + 'SLC2_tab_list',tpath + 'SLC2_ID_list',tpath + 'RSLC2_tab_list',hgt,ml_rg,ml_az,'--it1 1','--it2 0','--nr 32','--naz 16','--rwin 256','--azwin 256','--no_int','--no_check', logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)            
            else:                                     
                # Start co-registration 
                pg.ScanSAR_coreg(refslc_co_tab,str(refdate_cal) + '_' + refpol,depslc_co_tab,str(depdate_cal) + '_' + refpol,depslc_rco_tab,hgt,ml_rg,ml_az,'--it1 1','--it2 0','--nr 32','--naz 16','--rwin 256','--azwin 256','--no_int','--no_check', logf = logout, errf = errout, stdout_flag = q, stderr_flag = q) 
            
            for doff in glob.glob(tpath + '*coreg_quality'):
                shutil.copy(doff,outdir + '/' + relpath + '_' + str(depdate_cal) + '_' + minburstid + '_' + maxburstid + '_coreg.log')                              
            
            # Multilook and mosaic co-registered SLCs--> Section needs to be updated on AWS
            depslc_rco_img = tpath + tfile + '_' + str(depdate_cal) + '_' + refpol + '_mos_slc'
            depslc_rco_par = tpath + tfile + '_' + str(depdate_cal) + '_' + refpol + '_mos_slc.par'
            pg.SLC_mosaic_S1_TOPS(depslc_rco_tab,depslc_rco_img,depslc_rco_par,ml_rg,ml_az, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
            os.remove(depslc_rco_img)
            depmli_rco_img = tpath + tfile + '_' + str(depdate_cal) + '_' + refpol + '_mos_mli'
            depmli_rco_par = tpath + tfile + '_' + str(depdate_cal) + '_' + refpol + '_mos_mli.par' 
            depmli_rco_tab = tpath + tfile + '_' + str(depdate_cal) + '_' + refpol + '_mlitab'
            tabfile_rename(depslc_rco_tab,depmli_rco_tab,'rslc','mli')  
            tabfile_remove_path(depmli_rco_tab, depmli_rco_tab)
            tabfile_add_path(depmli_rco_tab,depmli_rco_tab,tpath)            
            pg.ScanSAR_burst_MLI(depslc_rco_tab,depmli_rco_tab,ml_rg,ml_az,0, refslc_co_tab, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)        
            pg.ScanSAR_burst_to_mosaic(depmli_rco_tab,depmli_rco_img,depmli_rco_par,1,refmli_co_tab,1,1, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
            if dp:
                depmli_rcr_img = tpath + tfile + '_' + str(depdate_cal) + '_' + secpol + '_mos_mli'
                depmli_rcr_par = tpath + tfile + '_' + str(depdate_cal) + '_' + secpol + '_mos_mli.par' 
                depmli_rcr_tab = tpath + tfile + '_' + str(depdate_cal) + '_' + secpol + '_mlitab'
                tabfile_rename(depslc_rcr_tab,depmli_rcr_tab,'rslc','mli')  
                tabfile_remove_path(depmli_rcr_tab, depmli_rcr_tab)
                tabfile_add_path(depmli_rcr_tab,depmli_rcr_tab,tpath)            
                pg.ScanSAR_burst_MLI(depslc_rcr_tab,depmli_rcr_tab,ml_rg,ml_az,0, refslc_co_tab, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)        
                pg.ScanSAR_burst_to_mosaic(depmli_rcr_tab,depmli_rcr_img,depmli_rcr_par,1,refmli_co_tab,1,1, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)

            # Delete temporary files
            for df in glob.glob(tpath + str(depdate_cal) + '*_*'):
                    os.remove(df)
            for df in glob.glob(tpath + str(refdate_cal) + '*_*'):
                    os.remove(df)  
                
            prct_coreg=np.floor(100*i/imno)
            if prct_coreg>=ints:
                print(str(ints), end='..', flush=True)
                ints=ints+intv
    print(('100 Done')) 
                
    #########################################################################################
    # Start interometric processing
    ccno=len(image_pairs_select)
    if ccno<2:
        ccno=2
    ints=10
    intv=10
    if ccno<11:
        ints=int(100/(ccno-1))
        intv=int(100/(ccno-1))  
    print('Coherence calculation [%]: 0..', end='', flush=True) 
    for i,p in enumerate(image_pairs_select):
        date1=p[0]
        date2=p[1]

        id1    = int(acqid[acqdate==date1])
        id2    = int(acqid[acqdate==date2])
        date1f = acqdate_cal[id1]
        date2f = acqdate_cal[id2]
        
        # Input files       
        im1mli_co_tab = tpath + tfile + '_' + str(date1f) + '_' + refpol + '_mlitab'
        im1slc_co_tab = tpath + tfile + '_' + str(date1f) + '_' + refpol + '_slctab'
        
        im2slc_co_tab = tpath + tfile + '_' + str(date2f) + '_' + refpol + '_slctab'
        im2mli_co_tab = tpath + tfile + '_' + str(date2f) + '_' + refpol + '_mlitab'    
        
        if dp and crosspolcoh:
            im1mli_cr_tab = tpath + tfile + '_' + str(date1f) + '_' + secpol + '_mlitab'
            im1slc_cr_tab = tpath + tfile + '_' + str(date1f) + '_' + secpol + '_slctab'
        
            im2slc_cr_tab = tpath + tfile + '_' + str(date2f) + '_' + secpol + '_slctab'
            im2mli_cr_tab = tpath + tfile + '_' + str(date2f) + '_' + secpol + '_mlitab'

        # Simulate phase    --> Needs to be updated on AWS
        slcpar1   = tpath + tfile + '_' + str(date1f) + '_' + refpol + '_mos_slc.par'
        slcpar2   = tpath + tfile + '_' + str(date2f) + '_' + refpol + '_mos_slc.par'
        off       = tpath + tfile + '_' + str(date2f) + '_' + refpol + '.off'
        sim_unw   = tpath + tfile + '.simunw' 
        pg.create_offset(slcpar1,slcpar2,off,1,ml_rg,ml_az,0, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
        pg.phase_sim_orb(slcpar1,slcpar2,off,hgt,sim_unw,refslc_co_par, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
        os.remove(off)

        # Resample simulated phase to burst geometry
        sim_tab = tpath + tfile + '_simtab' 
        tabfile_rename(refmli_co_tab,sim_tab,'mli','sim')
        tabfile_remove_path(sim_tab, sim_tab)
        tabfile_add_path(sim_tab,sim_tab,tpath)   
        copytab(refmli_co_tab,sim_tab)
        pg.ScanSAR_mosaic_to_burst(sim_unw,refmli_co_par,sim_tab, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
        os.remove(sim_unw)
        
        # Calculate differential interferogram
        diff_co_tab = tpath + tfile + '_diff_co_tab' 
        tabfile_rename(im1mli_co_tab,diff_co_tab,'mli','diff')
        tabfile_remove_path(diff_co_tab, diff_co_tab)
        tabfile_add_path(diff_co_tab,diff_co_tab,tpath)          
        pg.ScanSAR_burst_diff_intf(im1slc_co_tab,im2slc_co_tab,sim_tab,diff_co_tab, refslc_co_tab, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
        if dp and crosspolcoh:
            diff_cr_tab = tpath + tfile + '_diff_cr_tab'
            tabfile_rename(im1mli_cr_tab,diff_cr_tab,'mli','diff')            
            pg.ScanSAR_burst_diff_intf(im1slc_cr_tab,im2slc_cr_tab,sim_tab,diff_cr_tab, refslc_cr_tab, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
        deltab(sim_tab)
        os.remove(sim_tab)
        
        # Estimate baseline    
        base = tpath +  tfile + '_base'
        baseout = outdir + '/' + relpath + '_' + str(date1f) + '_' + str(date2f) + '_' + minburstid + '_' + maxburstid + '_base.txt'
        pg.base_orbit(slcpar1,slcpar2,base, logf = baseout, errf = errout, stdout_flag = q, stderr_flag = q)

        # Estimate coherence                              
        cc_co_tab = tpath + tfile + '_cc_co_tab' 
        cclog = tpath + tfile + '_cclog' 
        cc_co_img = tpath + tfile + '_' + str(date1f) + '_' + str(date2f)  + '_' + refpol + '_cc_ad' 
        cc_co_par = tpath + tfile + '_' + str(date1f) + '_' + str(date2f)  + '_' + refpol + '_cc_ad.par'
        tabfile_rename(diff_co_tab,cc_co_tab,'diff','cc')
        copytab(im1mli_co_tab,cc_co_tab)
        pg.ScanSAR_burst_cc_ad(diff_co_tab, im1mli_co_tab,im2mli_co_tab,'-','-',cc_co_tab, cclog,CC_WIN_MIN,CC_WIN_MAX, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
        pg.ScanSAR_burst_to_mosaic(cc_co_tab,cc_co_img,cc_co_par,1,refmli_co_tab,1,1, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
        cc_co_imgf = tpath + tfile + '_' + str(date1f) + '_' + str(date2f)  + '_' + refpol + '_cc_adf'
        pg.frame(cc_co_img,cc_co_imgf,mli1_width,0,1,1,1,1,1, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
        deltab(diff_co_tab)
        deltab(cc_co_tab)
        if dp and crosspolcoh:
            cc_cr_tab = tpath + tfile + '_cc_cr_tab' 
            cclog = tpath + tfile + '_cclog' 
            cc_cr_img = tpath + tfile + '_' + str(date1f) + '_' + str(date2f)  + '_' + secpol + '_cc_ad' 
            cc_cr_par = tpath + tfile + '_' + str(date1f) + '_' + str(date2f)  + '_' + secpol + '_cc_ad.par'
            tabfile_rename(diff_cr_tab,cc_cr_tab,'diff','cc')
            copytab(im1mli_cr_tab,cc_cr_tab)
            pg.ScanSAR_burst_cc_ad(diff_cr_tab, im1mli_cr_tab,im2mli_cr_tab,'-','-',cc_cr_tab, cclog,CC_WIN_MIN,CC_WIN_MAX, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
            pg.ScanSAR_burst_to_mosaic(cc_cr_tab,cc_cr_img,cc_cr_par,1,refmli_co_tab,1,1, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
            cc_cr_imgf = tpath + tfile + '_' + str(date1f) + '_' + str(date2f)  + '_' + secpol + '_cc_adf' 
            pg.frame(cc_cr_img,cc_cr_imgf,mli1_width,0,1,1,1,1,1, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
            deltab(diff_cr_tab)
            deltab(cc_cr_tab)
            
        # geocode coherence images and store as GTiffs in 8bit format
        cc_co_geo = tpath + tfile + '_' + str(date1f) + '_' + str(date2f)  + '_' + refpol + '_geo_cc_ad'
        cc_co_geo_byte = tpath + tfile + '_' + str(date1f) + '_' + str(date2f)  + '_' + refpol + '_geo_cc_ad_bite'
        cc_co_out_byte = outdir + '/' + relpath + '_' + str(date1f) + '_' + str(date2f) + '_' + minburstid + '_' + maxburstid + '_' + refpol + '_cc_ad.tif'
        pg.geocode_back(cc_co_imgf,mli1_width,geo2rdc,cc_co_geo,dem_width,'-',3,0,'-','-','-',1,logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
        ccbyte(cc_co_geo,cc_co_geo_byte)
        pg.data2geotiff(dempar,cc_co_geo_byte,5,cc_co_out_byte, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q) 
        os.remove(cc_co_geo_byte)
        os.remove(cc_co_geo)
        os.remove(cc_co_img)     
        os.remove(cc_co_imgf)
        if dp and crosspolcoh:
            cc_cr_geo = tpath + tfile + '_' + str(date1f) + '_' + str(date2f)  + '_' + secpol + '_geo_cc_ad'
            cc_cr_geo_byte = tpath + tfile + '_' + str(date1f) + '_' + str(date2f)  + '_' + secpol + '_geo_cc_ad_bite'
            cc_cr_out_byte = outdir + '/' + relpath + '_' + str(date1f) + '_' + str(date2f) + '_' + minburstid + '_' + maxburstid + '_' + secpol + '_cc_ad.tif'
            pg.geocode_back(cc_cr_imgf,mli1_width,geo2rdc,cc_cr_geo,dem_width,'-',3,0,'-','-','-',1,logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
            ccbyte(cc_cr_geo,cc_cr_geo_byte)
            pg.data2geotiff(dempar,cc_cr_geo_byte,5,cc_cr_out_byte, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q) 
            os.remove(cc_cr_geo_byte)
            os.remove(cc_cr_geo)
            os.remove(cc_cr_img)        
            os.remove(cc_cr_imgf)

        prct_coreg=np.floor(100*(i-1)/(ccno-1))
        if prct_coreg>=ints:
            print(str(ints), end='..', flush=True)
            ints=ints+intv
    print(('100 Done'))
    
    ###########################################################################
    # delete temporary files
    for df in glob.glob(tpath + '*rslc*'):
        os.remove(df)
    for df in glob.glob(tpath + '*diff*'):
        os.remove(df)    
                
    ###########################################################################
    # Convert inc to GTiff    --> Section needs to be updated on AWS
    incDN = tpath + relpath + '_' + minburstid + '_' + maxburstid  + '_incDN'
    inc_out_byte = outdir + '/' + relpath + '_' + minburstid + '_' + maxburstid  + '_inc.tif'
    pg.float2uchar(inc,incDN,57.29578, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
    os.remove(inc)
    pg.data2geotiff(dempar,incDN,5,inc_out_byte, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
    os.remove(incDN)

    # Convert lsmap to GTiff
    lsmap_out_byte = outdir + '/'  + relpath + '_' + minburstid + '_' + maxburstid  + '_lsmap.tif'
    pg.data2geotiff(dempar,lsmap,5,lsmap_out_byte, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q) 
    os.remove(lsmap)
    
    print('Geocode Backscatter images')
    for a in acqdate_cal:
        mli_co_img = tpath + tfile + '_' + str(np.int32(a)) + '_' + refpol + '_mos_mli'
        g0_co_img  = tpath + tfile + '_' + str(np.int32(a)) + '_' + refpol + '_mos_g0'
        g0f_co_img  = tpath + tfile + '_' + str(np.int32(a)) + '_' + refpol + '_mos_g0f'
        g0_co_geo = tpath + tfile + '_' + str(np.int32(a)) + '_' + refpol + '_geo_g0'
        amp_co_geo = tpath + tfile + '_' + str(np.int32(a)) + '_' + refpol + '_geo_amp'
        amp_co_out = outdir + '/' + relpath + '_' +  str(np.int32(a)) + '_' + minburstid + '_' + maxburstid + '_' + refpol + '_AMP.tif'
        pg.product(mli_co_img,pix,g0_co_img,mli1_width,1,1,0, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)   
        pg.average_filter(g0_co_img,g0f_co_img,mli1_width,3,3,1,logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
        pg.geocode_back(g0f_co_img,mli1_width,geo2rdc,g0_co_geo,dem_width,'-',3,0,'-','-','-',1, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q) 
        pwr2amp(g0_co_geo,amp_co_geo)   
        pg.data2geotiff(dempar,amp_co_geo,1,amp_co_out,0, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q) 
        os.remove(mli_co_img)
        os.remove(g0_co_img)   
        os.remove(g0f_co_img)               
        os.remove(g0_co_geo)        
        os.remove(amp_co_geo)
    if dp:
        for a in acqdate_cal:
            mli_cr_img = tpath + tfile + '_' + str(np.int32(a)) + '_' + secpol + '_mos_mli'
            g0_cr_img  = tpath + tfile + '_' + str(np.int32(a)) + '_' + secpol + '_mos_g0'
            g0f_cr_img  = tpath + tfile + '_' + str(np.int32(a)) + '_' + secpol + '_mos_g0f'
            g0_cr_geo = tpath + tfile + '_' + str(np.int32(a)) + '_' + secpol + '_geo_g0'
            amp_cr_geo = tpath + tfile + '_' + str(np.int32(a)) + '_' + secpol + '_geo_amp'
            amp_cr_out = outdir + '/' + relpath + '_' +  str(np.int32(a)) + '_' + minburstid + '_' + maxburstid + '_' + secpol + '_AMP.tif'
            pg.product(mli_cr_img,pix,g0_cr_img,mli1_width,1,1,0, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)   
            pg.average_filter(g0_cr_img,g0f_cr_img,mli1_width,3,3,1,logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
            pg.geocode_back(g0f_cr_img,mli1_width,geo2rdc,g0_cr_geo,dem_width,'-',3,0,'-','-','-',1, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q) 
            pwr2amp(g0_cr_geo,amp_cr_geo)   
            pg.data2geotiff(dempar,amp_cr_geo,1,amp_cr_out,0, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q) 
            os.remove(mli_cr_img)
            os.remove(g0_cr_img)   
            os.remove(g0f_cr_img)               
            os.remove(g0_cr_geo)        
            os.remove(amp_cr_geo)              
            
    #########################################################################################
    # Compute and display execution time                                                    #
    #########################################################################################
    end = time.time()
    diff=end-start
    print(('Processed in ' + str(diff) + ' s'))

#########################################################################
def main():
    args=myargsparse()
    insar(args)
    
if __name__ == '__main__':
    main()
