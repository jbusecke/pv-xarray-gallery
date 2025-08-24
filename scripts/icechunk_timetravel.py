# Set up an in-memory icechunk repo and use the xarray example dataset
import xarray as xr
import icechunk as ic
import pyvista as pv

import panel as pn

# Initialize Panel extension for VTK
pn.extension('vtk')


def mesh_from_roms_ds(ds:xr.Dataset) -> pv.core.pointset.StructuredGrid:
    if ds.Vtransform == 1:
        Zo_rho = ds.hc * (ds.s_rho - ds.Cs_r) + ds.Cs_r * ds.h
        z_rho = Zo_rho + ds.zeta * (1 + Zo_rho / ds.h)
    elif ds.Vtransform == 2:
        Zo_rho = (ds.hc * ds.s_rho + ds.Cs_r * ds.h) / (ds.hc + ds.h)
        z_rho = ds.zeta + (ds.zeta + ds.h) * Zo_rho

    ds.coords["z_rho"] = z_rho.transpose()  # needing transpose seems to be an xarray bug

    da = ds.salt[dict(ocean_time=0)]

    # Make array ordering consistent
    da = da.transpose("s_rho", "xi_rho", "eta_rho", transpose_coords=False)

    # Grab StructuredGrid mesh
    return da.pyvista.mesh(x="lon_rho", y="lat_rho", z="z_rho")

## set up snapshots
storage = ic.in_memory_storage()
config = ic.RepositoryConfig.default()
repo = ic.Repository.open_or_create(storage=storage, config=config)

ds = xr.tutorial.open_dataset("ROMS_example.nc", chunks={"ocean_time": 1})

# Create commits (your existing code)
w_session = repo.writable_session('main')
ds.to_zarr(w_session.store, consolidated=False, zarr_format=3)
snap1 = w_session.commit('Initial commit of ROMS_example dataset')

ds['salt'] = ds['salt'] * 0.9
w_session = repo.writable_session('main')
ds.to_zarr(w_session.store, consolidated=False, zarr_format=3, mode='w')
snap2 = w_session.commit('Modified commit of ROMS_example dataset')

ds['salt'] = ds['salt'] * 5
w_session = repo.writable_session('main')
ds.to_zarr(w_session.store, consolidated=False, zarr_format=3, mode='w')
snap3 = w_session.commit('Drastic commit of ROMS_example dataset')

ancestry = list(repo.ancestry(branch='main'))
# we need to remove the last one as it is the initial commit without data!!!
ancestry.pop(-1)

selector_options = {a.id: a for a in ancestry}

def get_mesh(snapshot):
    session = repo.readonly_session(snapshot_id=snapshot)
    ds = xr.open_zarr(session.store, consolidated=False)
    return mesh_from_roms_ds(ds)


clim = [20, 35]

selector = pn.widgets.Select(
    name='IceChunk Snapshot',
    options=selector_options,
    value=ancestry[0]
)

def adjust_plotter(plotter): 
    plotter.view_vector([1, -1, 1])
    plotter.set_scale(zscale=0.001)

# --- Single Callback for both selectors ---
def update_plot(event):
    """Reads the state of both selectors and updates the plots accordingly."""
    text_actor.set_text('ul', f"Message: {selector.value.message} | Committed: {selector.value.written_at}")
    plotter.add_mesh(get_mesh(selector.value.id), name='shape1', clim=clim)
    adjust_plotter(plotter)
    vtk_pane.param.trigger('object')
        

# --- Initialize Plots ---
plotter = pv.Plotter(window_size=[1400, 1400])
text_actor = plotter.add_text(f"Message: {selector.value.message} | Committed: {selector.value.written_at}",font_size=24, position='ul')
plotter.add_mesh(get_mesh(selector.value.id), name='shape1', clim=clim)
adjust_plotter(plotter)
vtk_pane = pn.pane.VTK(plotter.ren_win, sizing_mode='stretch_both', min_height=500)


# Link the single callback to both selectors
selector.param.watch(update_plot, 'value')

# --- Layout ---
app = pn.Column(
    pn.pane.Markdown('# Icechunk Time Travel'),
    selector,
    vtk_pane
)

app.servable()