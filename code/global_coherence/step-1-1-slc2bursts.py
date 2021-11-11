#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import time
import numpy as np
import py_gamma as pg
import atexit
import glob
import zipfile
import json

def myargsparse():
    import argparse

    thisprog=os.path.basename(sys.argv[0])

    ############################################################################
    # define some strings for parsing and help
    ############################################################################

    epilog=\
    """**********************************************************************************************************
    \n*                                GAMMA S1 InSAR processor, v1.0, 2020-12-14, oc                           *
    \n*         Import a list of S1 SLCs from the same datatake and store as individual bursts                  *
    \n*                                                                                                         *
    \n* Input and options:                                                                                      *
    \n* 1)  SLC zipfile                                                                                         *
    \n* 2)  Output directory                                                                                    *
    \n* 3)  Directory containing S1 precision orbits AUX_POEORB (optional)                                      *
    \n*                                                                                                         *
    \n* Output:                                                                                                 *
    \n* Burst SLCs and associated par and tops_par files                                                        *
    \n*                                                                                                         *
    \n***********************************************************************************************************
    \nEXAMPLES:
    \n{thisprog} -l $PATH/slclist* -o /home/user/ -p /nas/qc.sentinel1.eo.esa.int/aux_poeorb/
     """.format(thisprog=thisprog)

    help_slclist=\
    '''List of S1 SLC zipfiles'''
    help_outdir=\
    '''Output directory '''
    help_porb=\
    '''Directory containing S1 precision orbits AUX_POEORB'''
    help_q=\
    '''Verbose Mode'''
    help_r=\
    '''Create temporary directory in ramdisk Mode'''    
    
    p = argparse.ArgumentParser(usage=None,description=epilog,prog=thisprog,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-o",required=False,help=help_outdir,action='store',dest='outdir',default=os.getcwd())
    p.add_argument("-z",required=True,help=help_slclist,action='store',dest='ziplist',default=None,nargs='*')
    p.add_argument("-p",required=False,help=help_porb,action='store',dest='porb',default=False)
    p.add_argument("-v","--verbose",required=False,help=help_q,action='store_true',default=False)  
    p.add_argument("-r","--ramdisk",required=False,help=help_r,action='store_true',default=False)

    args=p.parse_args()
    args.outdir = args.outdir.rstrip('/') + '/'
    return args

#########################################################################
# Function to be called by atexit when script stops
def delfun(dirname):
    shutil.rmtree(dirname)
                        
#########################################################################
def S1_import(args):
    
    # Start time
    start = time.time()

    ##########################################################
    # Define Input/Output filenames/processing parameters    #
    ##########################################################

    ziplist    = args.ziplist            # List of S1 zipfiles
    outdir     = args.outdir             # Output directory
    porb       = args.porb               # Precision orbits
    q          = args.verbose            # Verbose mode
    ramdisk    = args.ramdisk            # Use ramdisk
    
    outdir=outdir.rstrip('/') 
    
    ziplist=list(ziplist)
    imno=len(ziplist)
    ints=10
    intv=10
    if imno<11:
        ints=int(100/(imno))
        intv=int(100/(imno))       
    print('Import SLCs [%]: 0..', end='', flush=True) 
    for i,f in enumerate(ziplist): 
        f=f.rstrip()

        # Obtain information from filename
        filename=f.rpartition('/')[-1]
        sat=filename.split('_')[0]
        mode=filename.split('_')[4][-2:]
        acqtime=filename.split('_')[5]
        acqdate=filename.split('_')[5].split('T')[0]
        orbit=filename.split('_')[7]
        datatake=filename.split('_')[8]
                
        # Define second polarization
        if mode == 'DV':
            pols=['vv','vh']
        elif mode == 'DH':
            pols=['hh','hv']
        elif mode == 'SH':
            pols='hh'
        elif mode == 'SV':
            pols='vv'
        elif mode == 'HH':
            pols='hh'
        elif mode == 'VV':
            pols='vv'
        elif mode == 'HV':
            pols='hv'
        elif mode == 'VH':
            pols='vh'
        
        # Output directory
        outdir = outdir.rstrip('/') + '/'
        if os.path.isdir(outdir) == False:
            os.mkdir(outdir)            
        
        # Define temporary working directory and filenames
        tfile = orbit + '_' + datatake + '_' + acqtime 
        if i==0:
            if ramdisk:
                tpath = '/dev/shm/gamma_' + tfile + '_' + str(abs(np.random.randn())).replace('.','') + '/'
            else:
                tpath = outdir + '/gamma_' + tfile + '_' + str(abs(np.random.randn())).replace('.','') + '/'
            os.mkdir(tpath)
            os.chdir(tpath)
            # Delete temporary working directory when script stops
            atexit.register(delfun, tpath)
           
        # Define name of log files
        logout= outdir + tfile + '.log'
        errout= outdir + tfile + '.err'
        
        # Determine relative orbit 
        if sat=='S1B':
            relpath=(int(int(orbit)-26-175*(np.floor((int(orbit)-27)/175))))
        elif sat=='S1A':
            relpath=(int(int(orbit)-72-175*(np.floor((int(orbit)-73)/175))))
        relpath=f'{relpath:03d}'
        
        # Unzip
        z=zipfile.ZipFile(f)
       
        product_path=tpath + filename.rstrip('zip') + 'SAFE'
        
        refburst_resource='/cluster/raid/home/oliver/Scripts/JPL/sentinel1_reference_burst_offsets.json'
        with open(refburst_resource,'r') as f:
            refbursts=json.load(f)        
            
        # Import GRD
        for p in pols:
            for iw in ['iw1','iw2','iw3']:
                flist=[x.filename for x in z.filelist if not x.is_dir() and x.filename.find(p) > -1 and x.filename.find(iw) > -1]
                for u in flist:
                    z.extract(u)
                
                # Input
                tiff   = glob.glob( product_path + '/measurement/*' + iw + '*' + p + '*tiff' )[0]
                lead1  = glob.glob( product_path + '/annotation/*' + iw + '*' + p + '*xml' )[0]
                lead2  = glob.glob( product_path + '/annotation/calibration/calibration-*' + iw + '*' + p + '*xml' )[0]
                lead3  = glob.glob( product_path + '/annotation/calibration/noise-*' + iw + '*' + p + '*xml' )[0]

                # Output
                slc       = tpath + tfile + '_' + p + '_' + iw + '.slc'
                slcpar    = tpath + tfile + '_' + p + '_' + iw + '.slc.par'
                slctpar   = tpath + tfile + '_' + p + '_' + iw + '.slc.tops_par'
                
                # Import SLC
                pg.par_S1_SLC(tiff,lead1,lead2,lead3,slcpar,slc,slctpar,1,'-', logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
                
                # Update orbit state vectors
                if porb:
                    if os.path.isdir(porb):
                        pg.OPOD_vec(slcpar,porb, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
                        
                # Create tabfile
                full_tabf=tpath + tfile + '_' + iw + '_' + p + '_fulltab'
                full_tab=[slc, slcpar, slctpar]
                pg.write_tab(full_tab, full_tabf)
                
                # Copy individual bursts
                pardict=pg.ParFile(slctpar)
                nobursts=int(pardict.get_value('number_of_bursts'))
                
                for b in range(1,nobursts+1):
                    burstid = pardict.get_value('burst_asc_node_' + str(b))[0]
                    burstid = str(np.floor(100*np.float32(burstid))/100)
                    
                    s1path=relpath.lstrip('0')
                    refburst=float(refbursts[str(s1path)][iw[-1]])
                    burstid_integer=np.floor(float(burstid))
                    burstid_decimal=float(burstid)-burstid_integer
                    # Three cases
                    # 1. burstid just below integer
                    if burstid_decimal > 0.9 and refburst< 0.1:
                        burstid_integer+=1
                        burstid=str(int((burstid_integer+refburst)*100))
                    # 2. burstid just above integer
                    elif burstid_decimal < 0.1 and refburst >  0.9:
                        burstid_integer-=1
                        burstid=str(int((burstid_integer+refburst)*100))
                    # 3. burstid and refburst in same integer range
                    else:
                        burstid=str(int((burstid_integer+refburst)*100))                    
                    
                    slcb     = outdir + '/' + relpath + '_' + iw + '_' + p + '_' + burstid + '_' + acqdate + '.slc'
                    slcbpar  = outdir + '/' + relpath + '_' + iw + '_' + p + '_' + burstid + '_' + acqdate + '.slc.par' 
                    slcbtpar = outdir + '/' + relpath + '_' + iw + '_' + p + '_' + burstid + '_' + acqdate + '.slc.tops_par'
                    out_tab=[slcb, slcbpar, slcbtpar]
                    out_tabf=tpath + tfile + '_' + iw + '_' + p + '_' + burstid + '_tab'
                    pg.write_tab(out_tab, out_tabf)
                    
                    # Create burst tab
                    bursttabf=tpath + tfile + '_' + iw + '_' + p + '_bursttab'
                    bursttab=[b,b]
                    pg.write_tab(bursttab, bursttabf)
                    
                    pg.SLC_copy_ScanSAR(full_tabf,out_tabf, bursttabf,1, logf = logout, errf = errout, stdout_flag = q, stderr_flag = q)
                    os.remove(out_tabf)
                    os.remove(bursttabf)
                    
                os.remove(full_tabf)
                os.remove(slc)
                os.remove(slcpar)
                os.remove(slctpar)
                    
                shutil.rmtree(product_path)
        
        prct_coreg=np.floor(100*i/imno)
        if prct_coreg>=ints:
            print(str(ints), end='..', flush=True)
            ints=ints+intv
    print(('100 Done'))      
               
    #########################################################################################
    # Compute and display execution time                                                    #
    #########################################################################################
    end = time.time()
    diff=end-start
    print(('Processed in ' + str(diff) + ' s'))       

#########################################################################
def main():
    args=myargsparse()
    S1_import(args)
    
if __name__ == '__main__':
    main()