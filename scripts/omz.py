import pyvista as pv
import xarray as xr
import matplotlib.pyplot as plt
from dask.diagnostics import ProgressBar
from scipy.ndimage import gaussian_filter


def shift_lon(ds:xr.Dataset, shift:int) -> xr.Dataset:
    lon = ds.lon + shift
    ds = ds.assign_coords(lon = lon.where(lon>0, 360+lon).data)
    return ds.sortby('lon')

# subsample
factor = 20

# local dev version (still need to push to source coop, see `gebco_2025_sourcecoop`)
ds_elevation = xr.open_dataset("../gebco_2025_sourcecoop/data/GEBCO_2025.zarr", chunks={}, engine='zarr', consolidated=False)


# smooth the elevation data
with ProgressBar():
    z = ds_elevation.elevation.coarsen(lon=factor, lat=factor).mean()

# print("Downloading GEBCO 2025 data (1.7GB), this may take a while...")
# import fsspec
# with fsspec.open("https://dap.ceda.ac.uk/bodc/gebco/global/gebco_2025/ice_surface_elevation/netcdf/GEBCO_2025.nc", mode='rb') as f:
#     ds_elevation = xr.open_dataset(f, chunks={'lon':3000, 'lat':3000})

#     # smooth the elevation data
#     with ProgressBar():
#         z = ds_elevation.elevation.coarsen(lon=factor, lat=factor).mean().load()

# convert to 0-360 convention (doesnt cut the pacific)
z = shift_lon(z, shift=-30)

# smooth only the ocean
smoothed_z = z.copy(deep=True)
smoothed_z.data = gaussian_filter(smoothed_z.data, sigma=3)

# scale land elevation to focus on the ocean
scaled_z = (z/z.max())*750

# combine scaled land and smoothed ocean
z_combo = smoothed_z.where(smoothed_z<0, scaled_z)

mesh = z_combo.squeeze().pyvista.mesh(x="lon", y="lat")
surface = mesh.warp_by_scalar()

surface = surface.extract_surface()
smoothed_surface = surface.smooth_taubin(n_iter=5)

import xarray as xr
store = 'https://ncsa.osn.xsede.org/Pangeo/pangeo-forge/WOA_1degree_monthly-feedstock/woa18-1deg-monthly.zarr'
ds = xr.open_dataset(store, engine='zarr', chunks={})

with ProgressBar():
    obs = ds.o_an.load()

obs = shift_lon(obs, shift=-30)

obs.coords['depth'] = -obs['depth']


# Plot in 3D
p = pv.Plotter(
    lighting='three lights',
    window_size=([2048, 1536]),
)

p.add_mesh(
    smoothed_surface,
    cmap='Greys_r',
    # scalars='z',
    smooth_shading=True,
    show_scalar_bar=False,
    # opacity=0.8
) 

def get_o2_isosurface(da:xr.DataArray):
    o2_mesh = da.pyvista.mesh(x="lon", y="lat", z='depth')
    return o2_mesh.contour(isosurfaces=[10, 40, 80])
    # return o2_mesh.contour(isosurfaces=range(0, 100, 10))

iso = p.add_mesh(
    get_o2_isosurface(obs.isel(time=0)),
    opacity=[1.0, 0.6, 0.4],
    smooth_shading=False,
    cmap='plasma',
    clim=[0, 100],
    scalar_bar_args={'title':'o2'},
)

p.camera_position = 'xy'
p.set_scale(zscale=0.005)
p.camera.zoom(1.5)

# set up animation
state = {'time':0}

# --- Update function ---
def update_scene(obj, event):
    if state["time"]==len(ds.time)-1:
        state['time'] = 0
    else:
        state["time"] += 1
    
    new_iso = get_o2_isosurface(obs.isel(time=state['time']))
    iso.mapper.SetInputData(new_iso)  # update the mesh
    p.render()

# Create a repeating timer (interval in ms)
timer_id = p.iren.create_timer(500)  # 50 ms interval
p.iren.add_observer("TimerEvent", update_scene)

p.show()