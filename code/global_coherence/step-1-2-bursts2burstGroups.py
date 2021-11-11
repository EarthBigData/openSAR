#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import numpy as np
import datetime
import shutil
import py_gamma as pg
import glob

DEVEL=False

def myargsparse():
    import argparse


    class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
        pass
    thisprog=os.path.basename(sys.argv[0])
    ############################################################################
    # define some strings for parsing and help
    ############################################################################

    epilog=\
    """**********************************************************************************************************
    \r*                                GAMMA S1 InSAR processor, v1.0, 2020-12-14, oc                           *
    \r*                        Earth Big Data LLC AWS Cloud integration, 2020-01-13,jmk                         *
    \r*                         Create json file summraizing files to create burst segments                     *
    \r*                                                                                                         *
    \r* Input and options:                                                                                      *
    \r* 1) List of single burst SLCs (associated .par and .tops_par files assumed to exist)                     *
    \r* 2) Output directory                                                                                     *
    \r*                                                                                                         *
    \r* Output:                                                                                                 *
    \r* JSON file                                                                                               *
    \r* Tabfiles                                                                                                *
    \r*                                                                                                         *    
    \r***********************************************************************************************************
    \nEXAMPLES:
    \n{thisprog} -z $PATH/slclist* -o /home/user/ -s 849.17 851.86
    \n{thisprog} -p 54 -o s3://ebd-scratch/jpl_coherence/step2
    """.format(thisprog=thisprog)

    help_slclist=\
    '''List of S1 burst SLCs (locally available)'''
    help_outdir=\
    '''Output directory '''
    help_path='Sentinel-1 acquisition path'
    help_indir='Root path to where Sentinel-1 relative orbits (paths) are stored.'
    
    p = argparse.ArgumentParser(description=epilog,prog=thisprog,formatter_class=CustomFormatter)
    p.add_argument("-i","--indir",required=False,help=help_indir,action='store',default='s3://ebd-scratch/jpl_coherence/step11')
    p.add_argument("-o","--outdir",required=False,help=help_outdir,action='store',default='s3://ebd-scratch/jpl_coherence/step12')
    p.add_argument("-p","--path",required=True,help=help_path,action='store',default=None)
    p.add_argument("-z","--slclist",required=False,help=help_slclist,action='store',default=None,nargs='*')
    p.add_argument("-profile","--profile",required=False,help="AWS profile with s3 access",action='store',default='default')
    p.add_argument("-v","--verbose",required=False,help="Verbose output",action='store_true',default=False)    

    args=p.parse_args()

    if not args.slclist and not args.path:
        p.print_usage()
        print('Need one of --path or --slclist')
        sys.exit(1)

    return args

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
        for ri in range(r):
            l1=tab1[ri]
            l2=tab2[ri]
            shutil.copy(l1,l2)
            


def get_slclist(args):
    indir = args.indir.rstrip(os.sep)+os.sep+str(args.path)
    files = glob.glob(indir+'/*slc')
    files = [x['name'] for x in files if x['name'].endswith('.slc')]

    return files



#########################################################################
def S1_segment(args):
    
    # Start time
    start = time.time()

    tmpdir='/dev/shm'
    ##########################################################
    # Define Input/Output filenames/processing parameters    #
    ##########################################################

    if args.slclist:
        slclist    = args.slclist            # List of S1 zipfiles
    else:
        slclist = get_slclist(args)
    outdir     = args.outdir             # Output directory
    
    outdir=outdir.rstrip('/') 
    outdir=os.path.join(outdir,args.path)  # Include path in outdir

    if os.path.isdir(outdir) == False and not args.outdir.startswith('s3://'):
        os.mkdir(outdir)    
        
    relorb=np.zeros(len(slclist), dtype=np.int64)
    swath=np.zeros(len(slclist), dtype=np.int8)
    pol=np.zeros(len(slclist), dtype=np.int8)
    burstid=np.zeros(len(slclist))
    acqdate=np.zeros(len(slclist), dtype=list)
    polvec=['vv','vh','hv','hh']
    
    # Obtain information from filename, e.g., 144_iw2_vh_2362.3802030_20191031.slc
    for i,f in enumerate(slclist): 
        f=f.rstrip()
        filename=f.rpartition('/')[-1]
        relorb[i]  = np.int32(filename.split('_')[0])
        swath[i]   = np.int(filename.split('_')[1][2])
        if filename.split('_')[2] == 'vv':
            pol[i]     = 0
        elif filename.split('_')[2] == 'vh':
            pol[i]     = 1
        elif filename.split('_')[2] == 'hv':
            pol[i]     = 2
        elif filename.split('_')[2] == 'hh':
            pol[i]     = 3            
        burstid[i] = np.float(filename.split('_')[3])/100.
        acqdate[i] = filename.split('_')[4].split('.')[0]
        
    # Unique values
    relorbs=np.unique(relorb)
    try:
        relorbs=int(relorbs)
    except Exception as e:
        raise RuntimeError(e)
    swaths=np.unique(swath)
    pols=np.unique(pol)
   
    # Per swath burstid offsets 
    boffset=np.zeros(len(swaths))
    for sw in swaths:
        burstid_swath=burstid[swath==sw]
        boffset[sw-1]=np.median(burstid_swath-np.floor(burstid_swath))
    
    for i in range(1,3):
        if boffset[i]<boffset[i-1]: boffset[i]+=1

    # max burstid per swath
    burstidmax=np.floor(np.max(burstid))
    
    # Define burst segments
    burstgroups=[]
    repeat=[]
    polarization=[]
    for bid in range(0,int(burstidmax)):
        burst_start=bid+boffset[0]
        burst_end=bid+boffset[2]
        mask=(burstid>=burst_start-0.1) * (burstid<=burst_end+0.1) * (pol==pols[0])
        if mask.sum()>0:
            burst_ids_group=np.unique(burstid[mask])
            acqdates=np.unique(acqdate[mask])
            burst_ids_acq=np.zeros(len(acqdates))
            for i,a in enumerate(acqdates):
                maska=(burstid>=burst_start-0.1) * (burstid<=burst_end+0.1) * (pol==pols[0]) * (acqdate==a)
                burst_ids_acq[i]=len(np.unique(swath[maska]))
            if np.min(burst_ids_acq[burst_ids_acq!=0])==3:
                mask_pol=(burstid>=burst_start-0.1) * (burstid<=burst_end+0.1)
                acqdates=np.unique(acqdate[mask])

                polarization.append([polvec[x] for x in np.unique(pol[mask_pol])])
                burstgroups.append(np.sort(np.unique(burstid[mask])))  
                acqs=[]
                
                # Decide wether to process 6- or 12-day repeat intervals
                for i,a in enumerate(acqdates):
                    a2=datetime.date(int(a[0:4]),int(a[4:6]),int(a[6:8]))
                    acqs.append(a2.toordinal())
                                     
                image_pairs=[]
                for im1 in acqs:
                    for im2 in acqs:
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
                
                if np.min(no06)<8:
                    repeat.append(12)
                else:
                    repeat.append(6)
            else:
                for i,n in enumerate(burst_ids_group):
                    masks=(burstid>=n-0.1) * (burstid<=n+0.1) * (pol==pols[0])
                    burstgroups.append(np.sort(np.unique(burstid[masks]))) 
                    masks_pol=(burstid>=n-0.1) * (burstid<=n+0.1)
                    polarization.append([polvec[x] for x in np.unique(pol[masks_pol])])
                    acqdates=np.unique(acqdate[masks])
                    acqs=[]
                    
                    # Decide wether to process 6- or 12-day repeat intervals
                    for i,a in enumerate(acqdates):
                        a2=datetime.date(int(a[0:4]),int(a[4:6]),int(a[6:8]))
                        acqs.append(a2.toordinal())                    
                
                    image_pairs=[]
                    for im1 in acqs:
                        for im2 in acqs:
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
                    
                    if np.min(no06)<8:
                        repeat.append(12)
                    else:
                        repeat.append(6)                                    
                                
    ##############################################################
    # Create JSON File 
    ##############################################################
    burstgroups_100=[(x*100).astype(np.int) for x in burstgroups]    
    bucket=args.indir.replace('s3://','').split('/')[0]  
    prefix='/'.join(args.indir.replace('s3://','').split('/')[1:]) 

    burst_dict={}
    burst_dict['bucket']=bucket
    burst_dict['prefix']=prefix
    burst_dict['relorbs']=relorbs
    burst_dict['reference_burst_ids']={}
    for i in range(len(burstgroups_100)):
        burst_dict['reference_burst_ids'][i]={}
        burst_dict['reference_burst_ids'][i]['repeat']=repeat[i]
        burst_dict['reference_burst_ids'][i]['polarization']=polarization[i]
        burst_dict['reference_burst_ids'][i]['burstgroup']=[int(x) for x in burstgroups_100[i]]

    jsondir=outdir.rstrip(str(args.path))
    dstname=f'{jsondir}{relorbs}.json'

    with open(dstname,"w") as f:
        json.dump(burst_dict,f)
    
    ###########################################################################
    # Create tab files           
    for bgrp in burstgroups:
        bgrpmin=np.min(bgrp)
        bgrpmax=np.max(bgrp)
        mask=(burstid>bgrpmin-0.1)*(burstid<bgrpmax+0.1)
        acqdates_segment=acqdate[mask]
        pols_segment=pol[mask]
        
        slclist_segment=[]
        for i,s in enumerate(slclist):
            if mask[i]:
                slclist_segment.append(slclist[i])
                
        for a in np.unique(acqdates_segment):
            for p in np.unique(pols_segment):
                mask_segment=(acqdates_segment==a)*(pols_segment==p)
                slclist_segment_acq_pol=[]
                for i,s in enumerate(slclist_segment):
                    if mask_segment[i]:
                        slclist_segment_acq_pol.append(slclist_segment[i])                    
                slclist_segment_acq_pol.sort()
                
                tab_arr=[]
                for slc in slclist_segment_acq_pol:
                    slcpar  = slc + '.par'
                    slctpar = slc + '.tops_par'
                    tab_arr.append([slc, slcpar, slctpar])             
                
                # assume tab filename: ${relpath}_${acqdate}_${pol}_${minburstid}_${maxburstid} 
                bgrpmin_100 = int(bgrpmin*100)
                bgrpmax_100 = int(bgrpmax*100)
                out_tabfile=f'{outdir}/{relorbs}_{a}_{polvec[p]}_{bgrpmin_100}_{bgrpmax_100}_segment_tab_s3'

                # Call the gamma write_tab srcipt:
                print(len(tab_arr))
                pg.write_tab(tab_arr, out_tabfile)
    
    #########################################################################################
    # Compute and display execution time                                                    #
    #########################################################################################
    end = time.time()
    diff=end-start
    print(('Processed in ' + str(diff) + ' s'))       

#########################################################################
def main():
    args=myargsparse()
    S1_segment(args)
    
if __name__ == '__main__':
    main()
