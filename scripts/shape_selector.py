import panel as pn
import pyvista as pv

# Initialize Panel extension for VTK
pn.extension('vtk')

# --- Widgets ---
shape_selector = pn.widgets.Select(
    name='Shape', options=['Sphere', 'Cube', 'Cylinder'], value='Sphere'
)

# --- PyVista Plot ---
# Create a plotter and a VTK pane ONCE
plotter = pv.Plotter()
# Add a mesh that will be updated. The initial shape doesn't matter much.
plotter.add_mesh(pv.Sphere(), name='shape')
vtk_pane = pn.pane.VTK(plotter.ren_win, height=400, width=600)

# --- Callbacks ---
def update_shape(event):
    """Updates the mesh based on the dropdown selection."""
    shape = event.new
    if shape == 'Sphere':
        new_mesh = pv.Sphere()
    elif shape == 'Cube':
        new_mesh = pv.Cube()
    elif shape == 'Cylinder':
        new_mesh = pv.Cylinder()
    else:
        return

    # Get the mesh from the plotter and update its data
    # This is more efficient and stable than clearing and re-adding.
    plotter.meshes[0].copy_from(new_mesh)
    
    # Reset the camera to fit the new shape
    plotter.reset_camera()
    
    # Trigger an update on the pane
    vtk_pane.object = plotter.ren_win

# Link widget to callback
shape_selector.param.watch(update_shape, 'value')

# --- Layout ---
app = pn.Column(
    '# 3D Shape Selector',
    shape_selector,
    vtk_pane
)

app.servable()
