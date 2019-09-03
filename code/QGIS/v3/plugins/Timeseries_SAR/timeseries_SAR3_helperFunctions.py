
#Time series helper functions
# (c) Josef Kellndorfer, Earth Big Data LLC
def lsf (srcmin,srcmax,dstmin,dstmax):
    '''Linear Scale Factors: Generate the scaling factors from in and out ranges'''
    delta=(np.float32(srcmax)-srcmin)/(dstmax-dstmin+1)
    offset=np.float32(srcmin)
    return [delta,offset]

def dB2pwr (dB,ndv=None):
    '''Convert dB to pwr data. Writes nan as NoDataValue'''
    # Make mask
    if ndv and not np.isnan(ndv):
        dB = np.ma.masked_values(dB,ndv)
    else:
        dB = np.ma.masked_invalid(dB)
    out=np.power(10.,dB/10.)
    return 'pwr', out.filled(np.nan)

def pwr2dB (pwr,ndv=None):
    '''Convert pwr to dB. Writes nan as NoDataValue.'''
    if ndv and not np.isnan(ndv):
        pwr = np.ma.masked_values(pwr,ndv)
    else:
        pwr = np.ma.masked_invalid(pwr)
    out=10.* np.log10(pwr)
    return 'dB', out.filled(np.nan)

def DN2dB (DN,lsf,ndv=None):
    '''Converts a DN to dB according to dB = DN * delta_dB + offset. Writes nan as NoDataValue'''
    if not ndv: 
        ndv=0
    DN = np.ma.masked_values(DN,ndv)
    # The casting function takes care of data outside the 8bit range
    out= np.float32(DN * lsf[0] + lsf[1])
    # set no data to nan
    return 'dB', out.filled(np.nan)

def DN2pwr ( DN, lsf, ndv=None):
    '''Converts DN data to pwr according to pwr = dB2pwr ( DN2dB (DN,delta_dB,offset) ) '''
    _, dB = DN2dB(DN,lsf,ndv)
    itype, pwr = dB2pwr( dB )
    return itype, pwr

def amp2pwr (amp,ndv=None):
    '''Convert amp to pwr data. Writes nan as NoDataValue. Assumes scaling as dB=20*log10(AMP)-83. Cal factor = 10^8.3 = 199526231'''
    CF=199526231  
    ndv = 0 if ndv==None else ndv
    # ndv = 0.0 if not ndv==None else ndv
    # Make mask
    if ndv != None and not np.isnan(ndv):
        amp = np.ma.masked_values(amp,ndv)
    else:
        amp = np.ma.masked_invalid(amp)
    pwr=np.ma.power(amp,2.)/CF
    out = np.array(pwr.data,dtype=np.float32)
    mask=~pwr.mask & (out==0.)     
    out[ mask ] = 0.000001 # HARDCODE ALERT
    out[pwr.mask] = 0.   
    return 'pwr', out


def ReadInfo(img):
    ds = gdal.Open(img, gdal.GA_ReadOnly)
    datatype=ds.GetRasterBand(1).DataType
    geo = ds.GetGeoTransform()
    proj = ds.GetProjection()
    srs=osr.SpatialReference(wkt=proj)
    unit=srs.GetAttrValue('unit')
    return ds, geo, proj, unit, datatype


def dates_from_meta(src_dataset):
    img_handle=gdal.Open(src_dataset)
    meta={}
    dates=[]
    for i in range(1,img_handle.RasterCount+1,1):
        meta[i]=img_handle.GetRasterBand(i).GetMetadata_Dict()
        if 'Date' in meta[i].keys():
            dates.append(meta[i]['Date'].replace('-',''))
    img_handle=None
    if dates:
        return dates
    else:
        return []


def max_date_range(img):
    '''Checks for other datefiles at the same directory level, parses them and returns the min/max data range as a tuple to use as x axis scaling'''
    dfile=os.path.splitext(img)[0]+'.dates'
    dirname=os.path.dirname(dfile)
    dfiles=glob.glob('{}/*.dates'.format(dirname))
    alldates=[]
    for i in dfiles:
        idates=[ s.strip('\n') for s in open(i).readlines()]
        alldates+=idates
    alldates = [int(x) for x in list(set(alldates))]
    alldates.sort()
    alldates  = [datetime.datetime.strptime(str(x),'%Y%m%d') for x in alldates]
    return alldates, (min(alldates),max(alldates))


