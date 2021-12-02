#!/usr/bin/env python
# coding: utf-8

# # GLOBAL SEASONAL SENTINEL-1 INTERFEROMETRIC COHERENCE AND BACKSCATTER DATA SET
# 
# See http://sentinel-1-global-coherence-earthbigdata.s3-website-us-west-2.amazonaws.com/ for a description of the data description, format and layout. It is made of millions of geoTIFF files.
# 
# This notebook uses **fsspec/kerchunk** to treat this global data set of geoTIFFs as a **zarr** store with metadata to visualize all variables dynamically as a globally cohesive data set.  
# 
# Authors/Contributors: [Martin Durant](https://github.com/martindurant), [Christoph Gohlke](https://github.com/cgohlke), [Richard Signell](https://github.com/rsignell-usgs), [Josef Kellndorfer](https://github.com/jkellndorfer)
# 
# Original source code in examples at fsspec/kerchunk: [https://github.com/fsspec/kerchunk](https://github.com/fsspec/kerchunk)
# 
# ## Load required modules

# In[ ]:


import os,sys
import fsspec
import geoviews as gv
from geoviews import tile_sources as gvts
import imagecodecs.numcodecs
import hvplot.xarray
import holoviews as hv
import numpy as np
import panel as pn
import param
import intake
from tqdm import tqdm
import xarray as xr

import itertools
import math

imagecodecs.numcodecs.register_codecs()  # register the TIFF codec
pn.extension()  # viz


# In[ ]:


# TURN WARNINGS OFF
import warnings
warnings.filterwarnings("ignore")


# ## Set Local or Server Mode
# 
# Via two variables we can adjust how we want to run this notebook. In server_mode we generate a **servable** which can be accessed via a web server. Otherwise we **show** the application in our local browser. Typically we want to cache data masks.

# In[ ]:


cache_s3=False # Read the cached mask data from s3 s3://sentinel-1-global-coherence-earthbigdata/data/wrappers/mask_ds.zarr
cache_local = True # Set to false if mask data should not be cached as local zarr stores
server_mode = True # Set to false if you want to run the notebook locally and visualize in a browser tab, True for display inside notebook or via webserver


# ## Load JSON File containing zarr store Simulation of the Global Data Set
# 
# We are loading from s3 via fsspec a json file that contains the descriptions of how we tie the global geo tiffs in tiles into a single xarray compatible zarr store. That work has been performed by Christoph Gohlke and can be seen in detail [here](https://github.com/cgohlke/tifffile/blob/v2021.10.10/examples/earthbigdata.py).
# 
# The entire power of this global visualization starts with two simple steps:
# 
# - generate a mapper to the jsom file
# - open a xarray dataset based on this mapper with the zarr engine

# In[ ]:


zarr_all_url='https://sentinel-1-global-coherence-earthbigdata.s3.us-west-2.amazonaws.com/data/wrappers/zarr-all.json'

mapper = fsspec.get_mapper(
    'reference://',
    fo=zarr_all_url,
    target_protocol='http',
)
dataset = xr.open_dataset(
    mapper, engine='zarr', backend_kwargs={'consolidated': False}
)


# In[ ]:


if not server_mode:
    print(dataset)


# In[ ]:


print('unmasked effective in-memory size of data set (TBytes):',dataset.nbytes / 2**40) 


# ## Prepare a Data Set Browser masking No Data regions
# 
# As much of the dimension space is empty, and contains no data, these areas would return a bunch of NaNs if we tried to extract the data. To be able to explore more efficiently, we create a view of the whole dataset, showing areas where data files do exist and thus can focus on exploring only these regions.
# We do this very much downsampled, because the process is quite slow.

# In[ ]:


STEP = 5


# In[ ]:


das = {}
new_coords = {}
for var in dataset.data_vars:
    newc = {k:v.values for k,v in dataset[var].coords.items()}
    newc['latitude'] = np.arange(89.5, -90.5, -STEP)
    newc['longitude'] = np.arange(-179.5, 180.5, STEP)
    empty_da = xr.DataArray(data=np.nan, dims=list(newc), coords=newc)
    das[var] = empty_da
    new_coords[var] = newc


# In[ ]:


mask_ds = xr.Dataset(das)


# In[ ]:


zkeys = set(mapper)


# In[ ]:


def find_nearest_idx(array, value):
    if array[1] > array[0]:
        idx = np.searchsorted(array, value, side="left")
        if idx > 0 and (idx == len(array) or math.fabs(value - array[idx-1]) < math.fabs(value - array[idx])):
            idx = idx-1
    else:
        idx = array.size - np.searchsorted(array[::-1], value, side="right")
        # idx = np.searchsorted(array, value, side="left", sorter=np.argsort(array))
        if idx > 0 and (idx == len(array) or math.fabs(value - array[idx]) < math.fabs(value - array[idx+1])):
            idx = idx-1
    return idx


# In[ ]:


def zarr_key(variable: xr.DataArray, coords: dict, chunks: dict, indexes: dict) -> str:
    chunk = []
    for i, dim in enumerate(variable.dims):
        vals = indexes[dim]
        if vals.dtype == "O":
            chunk.append(list(vals).index(coords[dim]) // chunks[dim])
        else:
            chunk.append(find_nearest_idx(vals.values, coords[dim]) // chunks[dim])
    return variable.name + "/" + ".".join(str(ch) for ch in chunk)


# In[ ]:


# Generate the masks
# After generation we are caching to disk if so desired.

chunks = {"latitude": 1200, "longitude": 1200}

if not cache_s3:
    mask_path=os.path.join(os.environ['HOME'],'mask_ds')
    mask_ds_zarr=os.path.join(mask_path,'mask_ds.zarr')
    if not os.path.exists(mask_ds_zarr):
        for var in mask_ds.data_vars:
            print(f'Processing {var}...')
            chunks = {dim: chunks.get(dim, 1) for i, dim in enumerate(dataset[var].dims)}
            # chunks = {dim:dataset[var].chunks[i][0] for i, dim in enumerate(dataset[var].dims)}
            indexes = {dim: dataset[var].indexes[dim] for dim in dataset[var].dims}
            total = mask_ds[var].size
            mask = np.full(total, np.nan, dtype=np.float16)
            for i, coords in enumerate(itertools.product(*(new_coords[var].values()))):
                coords = dict(zip(new_coords[var].keys(), coords))
                zkey = zarr_key(dataset[var], coords, chunks, indexes)
                mask[i] = zkey in zkeys
            mask = mask.reshape(mask_ds[var].shape)
            mask = np.where(mask == 0, np.nan, 1)
            mask_ds[var].values = mask
        print("done")
        if cache_local:
            # Now cache to disk
            print('Caching mask_ds to local',mask_ds_zarr)
            os.makedirs(mask_path,exist_ok=True)
            mask_ds.to_zarr(store=mask_ds_zarr,mode='w',consolidated=True,compute=True)
    else:
        # Load the cached data set
        print('Loading mask_ds from local cache', mask_ds_zarr)
        mask_ds=xr.open_zarr(mask_ds_zarr,consolidated=True)
        mask_ds = mask_ds.load()
else:
    mask_ds_s3='s3://sentinel-1-global-coherence-earthbigdata/data/wrappers/mask_ds.zarr'
    print('Loading mask_ds from s3 cache', mask_ds_s3)
    # Get a mapper for the mask data cached on s3 and open the data set
    fsz=fsspec.get_mapper(mask_ds_s3)
    mask_ds=xr.open_zarr(fsz,consolidated=True)
    mask_ds.load()



# ## Setup and Deploy the Visualization Tool 
# 
# We use a custom viz tool to be able to navigate the data space. As coded here, this will open in a separate browser tab (server_mode=False) or generate a servable (server_mode=True) that can be deployed with a call to `panel serve` via commandline on a webserver.
# 
# We are selecting Open Street Map as base map tiles for the region select portion of the tool.

# In[ ]:


hv.config.image_rtol = 0.01

class ZarrExplorer(param.Parameterized):
    base_map_select = param.Selector(doc='Basemap:', default=gvts.OSM,objects=gvts.tile_sources)
    local_map_extent = param.Number(default=1.5)
    variable = param.Selector(doc='Dataset Variable', default='COH', objects=list(mask_ds.data_vars))
    stream_tap_global = param.ClassSelector(hv.streams.SingleTap, hv.streams.SingleTap(x=-70.6, y=41.9), precedence=-1)
    update_localmap = param.Action(lambda x: x.param.trigger('update_localmap'), label='Click to load data after panning / zooming / parameter change')

    def __init__(self, **params):
        super().__init__(**params)
        self.global_map()
        self.lm = pn.pane.HoloViews(None, linked_axes=False)
        self.stream_rng = hv.streams.RangeXY()
        self.x_range, self.y_range = None, None
        self.update_local_map_after_map_click()

    @param.depends('variable','base_map_select')
    def global_map(self):
        base_map=self.base_map_select
        ds = hv.Dataset(mask_ds[self.variable])
        self.img_dm = ds.to(gv.QuadMesh, kdims=['longitude', 'latitude'], dynamic=True).opts(alpha=0.3)
        self.img_dm.cache_size = 1  # No cache so that last_key returns the current widgets state
        #overlay = base_map * self.img_dm * gv.feature.coastline.opts(scale='50m')
        overlay = base_map * self.img_dm 
        self.stream_tap_global.source = self.img_dm  # Attache the tap stream to this map
        overlay = overlay * self.withregion()
        pn_out = pn.panel(overlay.opts(width=600, height=500), widget_location='left')
        if self.variable=='COH':
            pn_out[0][1][0].value=12.0
            pn_out[0][1][1].value='vv'
            pn_out[0][1][2].value='winter'  
        elif self.variable in ('AMP','rho','tau','rmse'):
            pn_out[0][1][0].value='vv'
            pn_out[0][1][1].value='winter'
        else:
            pass
        return pn_out

    def withregion(self):
        def make_point(x, y):
            return gv.Points([(x, y)]).opts(color='red', marker='+', size=20)
        return hv.DynamicMap(make_point, streams=dict(x=self.stream_tap_global.param.x, y=self.stream_tap_global.param.y))

    @param.depends('stream_tap_global.x', 'stream_tap_global.y', watch=True)
    def update_local_map_after_map_click(self):
        x, y = self.stream_tap_global.x, self.stream_tap_global.y
        half_lme = self.local_map_extent / 2
        self.x_range = (x-half_lme, x+half_lme)
        self.y_range = (y+half_lme, y-half_lme)  # The dataset has reversed longitude

    @param.depends('update_localmap', watch=True)
    def update_local_map_after_refresh(self):
        y0, y1 = self.stream_rng.y_range
        self.x_range = self.stream_rng.x_range
        self.y_range = (y1, y0)  # The dataset has reversed longitude
    
    @param.depends('update_local_map_after_map_click', 'update_local_map_after_refresh')
    def local_map(self):
        if self.img_dm.last_key:
            state = {kdim.name: val for kdim, val in zip(self.img_dm.kdims, self.img_dm.last_key)}
        else:
            if self.variable=='COH':
                state = {'season': 'winter','polarization':'vv','coherence':12.0}
            elif self.variable in ('AMP','rho','tau','rmse'):
                state = {'season': 'winter','polarization':'vv'}
            else:
                state = {kdim.name: kdim.values[0] for kdim in self.img_dm.kdims}

        dssub = dataset[self.variable].sel(latitude=slice(*self.y_range), longitude=slice(*self.x_range), **state)
        title = f'{self.variable} @' + ', '.join(f'{dim}: {val}' for dim, val in state.items())
        img = dssub.hvplot.image(
            x="longitude", y="latitude",
            cmap='spectral_r', frame_width=400, geo=True, 
            rasterize=True,
            title=title,
            shared_axes=False,
        )
        self.stream_rng.source = img
        return img


# In[ ]:


ze = ZarrExplorer()


# In[ ]:


html_header='''
<a href="http://earthbigdata.com" target="_blank" rel="noopener noreferrer">
<img src="http://earthbigdata.com/wp-content/uploads/2017/06/logo-with-name-v3.png" width=200>
</a><a href="https://www.gamma-rs.ch" target="_blank" rel="noopener noreferrer">
<img src="https://www.gamma-rs.ch/images/gamma-img/gamma_logo.jpg" width=200>
</a><a href="https://jpl.nasa.gov" target="_blank" rel="noopener noreferrer">
<img src="https://upload.wikimedia.org/wikipedia/commons/c/c6/Jet_Propulsion_Laboratory_logo.svg" width=75>
</a>
<br><font size="+3">Global Sentinel-1 Coherence and Backscatter Data Set</font_size>
<font size="+0"><br>Contains modified Copernicus Sentinel-1 Data acquired from 1.Dec.2019 to 30.Nov.2020
<p><font size="+0">Choose from variables, polarizations, and time steps to see global coverage and select regions to visualize the data.
<br>Scaling for coherence such that  coherence   = COH / 100.
<br>Scaling for amplitudes such that backscatter [dB] = 20  * log10(AMP) -83.</font size>
<br>For a detailed data set descriction <a href="http://sentinel-1-global-coherence-earthbigdata.s3-website-us-west-2.amazonaws.com/" target="_blank" rel="noopener noreferrer">click here</a>.
</p>
'''


# In[ ]:


html_footer='''
<br><font size="+0">Dataset Repository</font_size></br>
<a href="https://registry.opendata.aws/ebd-sentinel-1-global-coherence-backscatter/" target="_blank" rel="noopener noreferrer">AWS Registry of Open Data Global Sentinel-1 Coherence and Backscatter Dataset</a>
<br><font size="+0">Visualization Credits</font_size></br>
<a href="https://github.com/fsspec/kerchunk" target="_blank" rel="noopener noreferrer">Martin Durant's fsspec/kerchunk</a>
<br><a href="https://github.com/cgohlke/tifffile" target="_blank" rel="noopener noreferrer">Christoph Gohlke's tifffile and json implementation of the zarr meta structure</a>
<br><a href="https://github.com/fsspec/kerchunk/issues/78" target="_blank" rel="noopener noreferrer">Richard Signell for kicking us off on the implementation and finetuning the notebook</a>
'''


# In[ ]:


app = pn.Column(
    html_header,
    pn.Param(ze.param.variable, width=150),
    pn.Row(
        ze.global_map,
        pn.Column(
            pn.panel(ze.local_map, loading_indicator=True),
            ze.param.update_localmap
        ),
    ),
    html_footer
)


# In[ ]:


if not server_mode:
    app.show(title='Global Interferometric Coherence and Backscatter from Sentinel-1',open=True)
else:
    app.servable(title='Global Interferometric Coherence and Backscatter from Sentinel-1')



