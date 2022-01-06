import os
import fsspec
import geoviews as gv
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

zarr_all_url='https://sentinel-1-global-coherence-earthbigdata.s3.us-west-2.amazonaws.com/data/wrappers/zarr-all.json'

mapper = fsspec.get_mapper(
    'reference://',
    fo=zarr_all_url,
    target_protocol='http',
)
dataset = xr.open_dataset(
    mapper, engine='zarr', backend_kwargs={'consolidated': False}
)

STEP = 5
das = {}
new_coords = {}
for var in dataset.data_vars:
    newc = {k:v.values for k,v in dataset[var].coords.items()}
    newc['latitude'] = np.arange(89.5, -90.5, -STEP)
    newc['longitude'] = np.arange(-179.5, 180.5, STEP)
    empty_da = xr.DataArray(data=np.nan, dims=list(newc), coords=newc)
    das[var] = empty_da
    new_coords[var] = newc
mask_ds = xr.Dataset(das)
zkeys = set(mapper)
zkeys

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
def zarr_key(variable: xr.DataArray, coords: dict, chunks: dict, indexes: dict) -> str:
    chunk = []
    for i, dim in enumerate(variable.dims):
        vals = indexes[dim]
        if vals.dtype == "O":
            chunk.append(list(vals).index(coords[dim]) // chunks[dim])
        else:
            chunk.append(find_nearest_idx(vals.values, coords[dim]) // chunks[dim])
    return variable.name + "/" + ".".join(str(ch) for ch in chunk)
chunks = {"latitude": 1200, "longitude": 1200}

# Generate the masks
# After generation we are caching to disk
mask_path=os.path.join(os.environ['HOME'],'mask_ds')
mask_ds_zarr=os.path.join(mask_path,'mask_ds.zarr')
os.makedirs(mask_path,exist_ok=True)
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
    # Now cache to disk
    mask_ds.to_zarr(store=mask_ds_zarr,mode='w',consolidated=True,compute=True)
else:
    # Load the cached data set
    print('Loading mask_ds from cache', mask_ds_zarr)
    mask_ds=xr.open_zarr(mask_ds_zarr,consolidated=True)
    mask_ds = mask_ds.load()


hv.config.image_rtol = 0.01

class ZarrExplorer(param.Parameterized):
    local_map_extent = param.Number(default=0.2)
    variable = param.Selector(doc='Dataset Variable', default='COH', objects=list(mask_ds.data_vars))
    stream_tap_global = param.ClassSelector(hv.streams.SingleTap, hv.streams.SingleTap(x=-43.7, y=59.9), precedence=-1)
    update_localmap = param.Action(lambda x: x.param.trigger('update_localmap'), label='Click to load data after panning/zooming')

    def __init__(self, **params):
        super().__init__(**params)
        self.global_map()
        self.lm = pn.pane.HoloViews(None, linked_axes=False)
        self.stream_rng = hv.streams.RangeXY()
        self.x_range, self.y_range = None, None
        self.update_local_map_after_map_click()

    @param.depends('variable')
    def global_map(self):
        ds = hv.Dataset(mask_ds[self.variable])
        self.img_dm = ds.to(gv.QuadMesh, kdims=['longitude', 'latitude'], dynamic=True).opts()
        self.img_dm.cache_size = 1  # No cache so that last_key returns the current widgets state
        overlay = self.img_dm * gv.feature.coastline.opts(scale='50m')
        self.stream_tap_global.source = self.img_dm  # Attache the tap stream to this map
        overlay = overlay * self.withregion()
        return pn.panel(overlay.opts(width=600, height=500), widget_location='left')

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

    # replaced aspect='equal' with geo=True
    @param.depends('update_local_map_after_map_click', 'update_local_map_after_refresh')
    def local_map(self):
        if self.img_dm.last_key:
            state = {kdim.name: val for kdim, val in zip(self.img_dm.kdims, self.img_dm.last_key)}
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
ze = ZarrExplorer()
app = pn.Column(
    pn.Param(ze.param.variable, width=150),
    pn.Row(
        ze.global_map,
        pn.Column(
            pn.panel(ze.local_map, loading_indicator=True),
            ze.param.update_localmap
        ),
    ),
)
# app.show(title='Global Interferometric Coherence and Backscatter from Sentinel-1',open=False,port=8080)
# ?app.servable
app.servable(title='Global Interferometric Coherence and Backscatter from Sentinel-1')