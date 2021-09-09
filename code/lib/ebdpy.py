# Functions to support notebooks with ebd kernel
# (c) 2020 Earth Big Data LLC All Rights Reservered
# Author: Josef Kellndorfer
# Date June 2020

import os,sys
import configparser

from osgeo import gdal
import numpy as np
import pandas as pd
import xarray as xr
import holoviews as hv
from holoviews import opts
from math import floor,ceil


from bokeh.models import HoverTool

from dask_gateway import Gateway
from dask.distributed import Client,WorkerPlugin
import uuid
import asyncio
from time import sleep


Numpy2gdalGDTCode={
  "uint8": 1,
  "int8": 1,
  "uint16": 2,
  "int16": 3,
  "uint32": 4,
  "int32": 5,
  "float32": 6,
  "float64": 7,
  "complex64": 10,
  "complex128": 11,
}

def aws_add_shared_to_my_credentials(
    s_cfile=os.path.join(os.environ['HOME'],'shared','.aws','credentials'),
    m_cfile=os.path.join(os.environ['HOME'],'.aws','credentials')):
    s_cp = configparser.ConfigParser()
    m_cp = configparser.ConfigParser()
    s_cp.read(s_cfile)
    if not os.path.exists(m_cfile):
        os.makedirs(os.path.dirname(m_cfile),exist_ok=True)
        with open(m_cfile, "w") as f:
            f.write('')
    m_cp.read(m_cfile)
    # Missing shared profiles in my profiles:
    missing=set(s_cp) - set(m_cp)
    # print(missing)
    #print(missing,set(s_cp),set(m_cp))
    # Add missing to my credentials
    for m in missing:
        print(f'adding section [{m}] to {m_cfile}')
        m_cp.add_section(m)
        for k in s_cp[m]:
            # print(m,k,s_cp[m][k])
            m_cp.set(m,k,s_cp[m][k])
    m_cp.update()   
    # Write the updated file
    with open(m_cfile,"w") as f:
        m_cp.write(f)
    return m_cfile

def aws_add_shared_to_my_config(
    s_cfile=os.path.join(os.environ['HOME'],'shared','.aws','config'),
    m_cfile=os.path.join(os.environ['HOME'],'.aws','config')):
    aws_add_shared_to_my_credentials(s_cfile,m_cfile)

def set_credentials(profile='w-ebd-public',region='us-east-1',endpoint='s3.wasabisys.com'):
    '''Sets the aws credentials if not set already and profilename is default'''
    # Update user credentials and config with missing credentials from shared credentials
    m_cfile=aws_add_shared_to_my_credentials()
    aws_add_shared_to_my_config()
    # Set the credentials from the user credentials file
    cp = configparser.ConfigParser()
    cp.read(m_cfile)
    os.environ['aws_access_key_id'.upper()]=cp[profile]['aws_access_key_id']	
    os.environ['aws_secret_access_key'.upper()]=cp[profile]['aws_secret_access_key']	
    os.environ['aws_profile'.upper()]=profile
    os.environ['aws_default_profile'.upper()]=profile
    os.environ['aws_s3_region'.upper()]=region
    os.environ['aws_s3_endpoint'.upper()]=endpoint
    os.environ['aws_default_region'.upper()]=region
        
def set_credentials2(profile='default',region='us-west-2',endpoint=None,cfile=None):
    # Set the credentials from the user credentials file
    cp = configparser.ConfigParser()
    if not cfile:
        cfile=os.path.join(os.environ['HOME'],'.aws','credentials')
    if not endpoint:
        endpoint=f's3.{region}.amazonaws.com'
    cp.read(cfile)
    os.environ['aws_access_key_id'.upper()]=cp[profile]['aws_access_key_id']    
    os.environ['aws_secret_access_key'.upper()]=cp[profile]['aws_secret_access_key']    
    os.environ['aws_profile'.upper()]=profile
    os.environ['aws_default_profile'.upper()]=profile
    os.environ['aws_s3_region'.upper()]=region
    os.environ['aws_s3_endpoint'.upper()]=endpoint
    os.environ['aws_default_region'.upper()]=region

def list_profiles(cfile=os.path.join(os.environ['HOME'],'.aws','credentials')):
    cp = configparser.ConfigParser()
    cp.read(cfile)
    profiles=list(cp)
    print(f'Your available profiles:\n({cfile})')
    print('\n'.join(profiles))
    
    
    
def da_subset_xy(da,subset=None):
    '''Subset a xarray data array by x and y
    da  data array
    
    subset  [x1,y1,x2,y2] # coordinate for two points describing subset extent
    
    Uses da.transform to compute indices used for subsetting
    
    e.g. 
    da.transform 
       (20.0, 0.0, 241980.0, 0.0, -20.0, 748040.0)
       
    Raises ValueError if subset bounds are outside the data array boundaries
    '''
    if not subset:
        return da
    else:
        xmin=min(subset[0],subset[2])
        ymin=min(subset[1],subset[3])
        xmax=max(subset[0],subset[2])
        ymax=max(subset[1],subset[3])
    
        xres,_,xoff,_,yres,yoff=da.transform
        x0=int(floor((xmin-xoff)/xres))
        x1= int(ceil((xmax-xoff)/xres))
        y0=int(floor((ymax-yoff)/yres))
        y1= int(ceil((ymin-yoff)/yres))

        # Check for validity of subset
        if x0<0 or x1>len(da.x) or y0<0 or y1 > len(da.y):
            raise ValueError(f'Invalid subset {subset} resulting in xmin,ymin,xmax,ymax indices {x0} {y0} {x1} {y1} on data array with dimensions {da.shape}')
        else:
            print (f'Subset {subset} resulting in xmin,ymin,xmax,ymax indices {x0} {y0} {x1} {y1}')
            da_sub=da[:,y0:y1,x0:x1]
            # Update the transform attribute
            tr=list(da_sub.transform)
            xorig=tr[2]+tr[0]*x0
            yorig=tr[5]+tr[4]*y0
            tr[2]=xorig
            tr[5]=yorig
            da_sub = da_sub.assign_attrs({'transform':tuple(tr)})
            return da_sub
    


def CreateGeoTiff(Name, Array, DataType=None, NDV=0,bandnames=None,ref_image=None, 
                  GeoT=None, Projection=None,overwrite=False,colors=None):
    '''Creates a GeoTIFF image from a numpy array
    Name       name of output image
    Array      Numpy 2D (y,x) or 3D (z,y,x) array
    DataType   gdal datatype corresponding with the Array. See ?gdal.GDT...
                    Will be deternind from Array.dtype if not provided.
    NDV        No data value (default 0)
    bandnames  Optional list ['...','...'] of bandnames (can be one element for 2D)
    ref_image  reference image to get GeoT(ransformation) and Projection info
    GeoT       provide GeoT(ransformation) (overwrites ref_image)
    Projection provide Projection (overwrites ref_image)
    overwrite  set to True if file with Name exists
    '''
    if ref_image==None and (GeoT==None or Projection==None):
        raise ValueError('Need ref_image OR GeoT and Projection.')

    if not overwrite and os.path.exists(Name):
        print(f'{Name} exists. Use "overwrite=True" to replace.')
        return None
    else:
        # If it's a 2D image we fake a third dimension:
        if len(Array.shape)==2:
            Array=np.array([Array])
        if bandnames != None:
            if len(bandnames) != Array.shape[0]:
                raise RuntimeError('Need {} bandnames. {} given'
                                   .format(Array.shape[0],len(bandnames)))
        else:
            bandnames=['Band {}'.format(i+1) for i in range(Array.shape[0])]
        GeoT_ref=None
        Projection_ref=None
        if ref_image!= None:
            refimg=gdal.Open(ref_image)
            GeoT_ref=refimg.GetGeoTransform()
            Projection_ref=refimg.GetProjection()
            refimg=None
        # if GeoT or Projection are supplied, it trumps the ref_image
        GeoT = GeoT if GeoT else GeoT_ref
        Projection= Projection if Projection else Projection_ref
        if not GeoT:
            raise ValueError('Need GeoT or ref_image.')
        if not Projection:
            raise ValueError('Need Projection or ref_image.')
        driver= gdal.GetDriverByName('GTIFF')
        Array[np.isnan(Array)] = NDV
        if Array.dtype=='bool':
            Array=Array.astype(np.uint8)
        if not DataType:
            DataType = Numpy2gdalGDTCode[str(Array.dtype)]
        DataSet = driver.Create(Name, 
                Array.shape[2], Array.shape[1], Array.shape[0], DataType,options=['PHOTOMETRIC=RGB','COMPRESS=LZW'])
        DataSet.SetGeoTransform(GeoT)
        DataSet.SetProjection( Projection)
        for i, image in enumerate(Array, 1):
            band=DataSet.GetRasterBand(i)
            band.SetNoDataValue(NDV)
            band.SetDescription(bandnames[i-1])
            band.WriteArray( image )
            if colors:
                band.SetRasterColorTable(colors)
                band.SetRasterColorInterpretation(gdal.GCI_PaletteIndex)
        DataSet.FlushCache()
        DataSet=None
        return Name

def transform2geotras(t):
    '''Converts a xarray transform info (from rasterio) to gdal geotrans tuple
    Transform : (20.0, 0.0, 241980.0, 0.0, -20.0, 748040.0)
    Geotrans  : (241980.0, 20.0, 0.0, 748040.0, 0.0, -20.0)
    '''
    return (t[2],t[0],t[1],t[5],t[3],t[4])
    

def timeseries_metrics(raster,ndv=0): 
    # Make use of numpy nan functions
    # Check if type is a float array
    if not raster.dtype.name.find('float')>-1:
        raster=raster.astype(np.float32)
    # Set ndv to nan
    if ndv != np.nan:
        raster[np.equal(raster,ndv)]=np.nan
    # Build dictionary of the metrics
    tsmetrics={}
    rperc = np.nanpercentile(raster,[5,50,95],axis=0)
    tsmetrics['mean']=np.nanmean(raster,axis=0)
    tsmetrics['max']=np.nanmax(raster,axis=0)
    tsmetrics['min']=np.nanmin(raster,axis=0)
    tsmetrics['range']=tsmetrics['max']-tsmetrics['min']
    tsmetrics['median']=rperc[1]
    tsmetrics['p5']=rperc[0]
    tsmetrics['p95']=rperc[2]
    tsmetrics['prange']=rperc[2]-rperc[0]
    tsmetrics['std']=np.nanvar(raster,axis=0)
    tsmetrics['cov']=tsmetrics['std']/tsmetrics['mean']
    return tsmetrics


def rgb_stretch(rgb,stretch='histogram'):
    '''For display, we want a histogram equalized version'''
    from skimage import exposure # to enhance image display

    rgb_stretched=rgb.copy()
    # For each band we apply the strech
    for i in range(rgb_stretched.shape[2]):
        if np.isnan(rgb).any():
            mask=~np.isnan(rgb_stretched[:,:,i])
        else:
            mask=~np.equal(rgb_stretched[:,:,i],0)     
        rgb_stretched[:,:,i] = exposure.\
        equalize_hist(rgb_stretched[:,:,i],
        mask=mask)
    return rgb_stretched

def rgb_stretch_ds(RGB,stretch='histogram',dim=0):
    '''For display, we want a histogram equalized version
    '''
    from skimage import exposure # to enhance image display

    rgb=RGB.copy()
    rgb=rgb.where(rgb>0,0)
    rgb=rgb.where(rgb<1,1)
    elist=[]
    dims=list(rgb.dims.keys())
    dimsel=dims[dim]
    datavar=list(rgb.data_vars)[0]
    for i in range(3):
        band = rgb.isel({dimsel:i}).to_array()
        mask=~np.isnan(rgb.isel({dimsel:i})).to_array()
        e = exposure.equalize_hist(band.values,mask=mask.values)
        elist.append(e)
    estack = np.vstack(elist)   
    rgb[datavar]=(('time','y','x'),estack)    # Hardcode alert
    return rgb

def rgb_plot(rgb,da,label='RGB Plot',width=800,height=800):
    '''Use Holoviews for an RGB plot of a rgb data array'''
    TOOLTIPS = [("(x,y)", "($x{0,0.0}, $y{0,0.0})"),]
    hover = HoverTool(tooltips=TOOLTIPS)
    xmin,ymax=da.transform[2],da.transform[5]
    xmax=xmin+da.transform[0]*da.shape[2]
    ymin=ymax+da.transform[4]*da.shape[1]
    bounds=(xmin,ymin,xmax,ymax)
    epsg=da.crs.split(':')[1]
    kdims=[f'Easting [m] (EPSG:{epsg})','Northing [m]']
    hv_rgb=hv.RGB(rgb,bounds=bounds,kdims=kdims,label=label)
    hv_rgb=hv_rgb.options(opts.RGB(width=width,height=height,tools=[hover],xformatter='%.0f',yformatter='%.0f'))
    return hv_rgb


def read_sar(src,dsname=None,chunks=(20,500,500),keep_DN=False):
    '''Returns a SAR power data array time series stack from the Amplitude scale data stack'''
    try:
        da=xr.open_rasterio(src,chunks=chunks)
        if not dsname:
            da.name=os.path.splitext(os.path.basename(src))[0]
        da.name=dsname

        da['band']=pd.DatetimeIndex(da.descriptions)
        da=da.rename({'band':'time'})

        #da.set_index(time="time")
        if not keep_DN:
            # Convert to power
            attrs=da.attrs.copy()
            CAL=np.power(10,-8.3)
            da=(np.power(da.astype(np.float32),2)*CAL)
            da = da.where(da>0)  # Sets values <= 0 to nan
            da.attrs=attrs
        return da
    except Exception as e:
        raise ValueError(e)

# def stretch(arr,stretch='equalize'):
#     arr_stretched=arr.copy()
    
#     # For each band we apply the strech
#     for i in range(rgb_stretched.shape[2]):
#         rgb_stretched[:,:,i] = exposure.\
#         equalize_hist(rgb_stretched[:,:,i])
#     #     mask=~np.equal(rgb_stretched[:,:,i].data,0.))

# Subset tiles from tilelist for region of interest
def subset_tiles(tiles,minlon,maxlon,minlat,maxlat):
    '''
    select from tiles all tiles that fall between the min and max lat lon values
    e.g.
    minlon,maxlon,minlat,maxlat = -84,-82,70,71 
    results in two tiles:
    N71W084,N71W083
    '''
    lonrange=range(minlon,maxlon)
    latrange=range(maxlat,minlat,-1)
    tile_candidates=[]
    for lat in latrange:
        for lon in lonrange:
            NS='N' if lat >=0 else 'S'
            EW='E' if lon >=0 else 'W'
            tile_candidates.append(f'{NS}{abs(lat):02d}{EW}{abs(lon):03d}')
    selected_tiles =  list(set(tiles) & set(tile_candidates))
    selected_tiles.sort()
    return selected_tiles

# DASK Stuff 2021-03-12
def start_dask_cluster(environment=os.path.basename(os.environ['CONDA_PREFIX']),worker_profile='Medium Worker',profile='default',region='us-west-2',endpoint=None,worker_min=2,worker_max=20,adaptive_scaling=True,wait_for_cluster=True,
cfile=None,use_existing_cluster=True,propagate_env=False):
    '''
    environment      - should match the kernel running, and will be set autmatically
    worker profile   - 'Small Worker', 'Medium Worker', or 'Pangeo Worker' (determines available memory in a worker)
    profile          - 'default' is good, but others can be used 
    region           - AWS region
    endpoint         - None by default matches region. Set correct endpoint to s3 buckets
    worker_min       - minumum number of workers (for adaptive scaling)
    worker_max       - maximum number of workers
    adaptive_scaling - Default True. If False, launches worker_max workers
    wait_for_cluster - Default True. 
    cfile            - None. Finds aws credentials in this file
    use_existing_cluster - Default True.
    propagate_env    - Default False. Set to True when working with Cloud VRTs
    '''
    if not endpoint:
        endpoint=f's3.{region}.amazonaws.com'
    
    set_credentials2(profile=profile,region=region,endpoint=endpoint,cfile=cfile)

    try:
        gateway.list_clusters()
    except:
        gateway = Gateway()


    if gateway.list_clusters():
        print('Existing Dask clusters:')
        j=0
        for c in gateway.list_clusters():
            print(f'Cluster Index c_idx: {j} / Name:',c.name,c.status)
            j+=1        
    else:
        print('No Cluster running.')


    # TODO Check if worker_profile is the same, otherwise start new cluster
    if gateway.list_clusters() and use_existing_cluster:
        print('Using existing cluster [0].')
        cluster=gateway.connect(gateway.list_clusters()[0].name)  
    else:
        print('Starting new cluster.')
        cluster = gateway.new_cluster(environment=environment, profile=worker_profile)    
    

    if adaptive_scaling:
        print(f'Setting Adaptive Scaling min={worker_min}, max={worker_max}')
        cluster.adapt(minimum=worker_min, maximum=worker_max)
    else:
        print(f'Setting Fixed Scaling workers={worker_max}')
        cluster.scale(worker_max)




    try:
        client = Client(cluster)
        client.close()
        print('Reconnect client to clear cache')
    except:
        pass
    client = Client(cluster)


    print(f'client.dashboard_link (for new browser tab/window or dashboard searchbar in Jupyterhub):\n{client.dashboard_link}')


    if wait_for_cluster:
        target_workers=worker_min if adaptive_scaling else worker_max
        live_workers=len(list(cluster.scheduler_info['workers']))
        t=0
        interval=2
        print(f'Elapsed time to wait for {target_workers} live workers:\n{live_workers}/{target_workers} workers - {t} seconds',end='')
        while not live_workers>=target_workers:
            sleep(interval)
            t+=interval
            print(f'\r{live_workers}/{target_workers} workers - {t} seconds',end='')
            live_workers=len(client.scheduler_info()['workers'])
        print(f'\r{live_workers}/{target_workers} workers - {t} seconds')


    # We need to propagate credentials to the workers
    #set_credentials(profile=profile,region=region,endpoint=endpoint)


    if propagate_env:
        print('Propagating environment variables to workers')
        class InitWorker(WorkerPlugin):
            name = "init_worker"

            def __init__(self, filepath=None, script=None):
                self.data = {}
                if filepath:
                    if isinstance(filepath, str):
                        filepath = [filepath]
                    for file_ in filepath:
                        with open(file_, "rb") as f:
                            filename = os.path.basename(file_)
                            self.data[filename] = f.read()
                if script:
                    filename = f"{uuid.uuid1()}.py"
                    self.data[filename] = script

            async def setup(self, worker):
                responses = await asyncio.gather(
                    *[
                        worker.upload_file(
                            comm=None, filename=filename, data=data, load=True
                        )
                        for filename, data in self.data.items()
                    ]
                )
                assert all(
                    len(data) == r["nbytes"]
                    for r, data in zip(responses, self.data.values())
                )


        script = f"""
        \rimport os
        \ros.environ["AWS_ACCESS_KEY_ID"] = "{os.getenv("AWS_ACCESS_KEY_ID")}"
        \ros.environ["AWS_SECRET_ACCESS_KEY"] = "{os.getenv("AWS_SECRET_ACCESS_KEY")}"
        \ros.environ["AWS_DEFAULT_REGION"] = "{os.getenv("AWS_DEFAULT_REGION")}"
        \ros.environ["GDAL_DISABLE_READDIR_ON_OPEN"] ="EMPTY_DIR"
        """


        plugin = InitWorker(script=script)
        client.register_worker_plugin(plugin)

    return client,cluster


def stop_dask_cluster(client,cluster):
    # Set done=True and run cell to shutdown the cluster
    client.close()
    cluster.shutdown()
    client=None
    cluster=None
