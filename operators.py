import math

import bpy
import bmesh
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add

from . import generator


class HOUSE_OT_add_wall_module(bpy.types.Operator, AddObjectHelper):
    bl_idname = "mesh.house_add_wall_module"
    bl_label = "Wall Module"
    bl_description = "Add a low-poly wall plane with an inset and extruded window or door opening"
    bl_options = {'REGISTER', 'UNDO'}

    width: FloatProperty(name="Width", default=3.0, min=0.5, soft_max=10.0, unit='LENGTH')
    height: FloatProperty(name="Height", default=3.0, min=0.5, soft_max=10.0, unit='LENGTH')
    pivot: EnumProperty(
        name="Pivot",
        items=[
            ('CORNER', "Corner", "Origin at the bottom-left corner of the wall plane"),
            ('CENTER', "Bottom Center", "Origin at the bottom center of the wall plane"),
        ],
        default='CENTER',
    )

    opening: EnumProperty(
        name="Opening",
        items=[
            ('WINDOW', "Window", ""),
            ('DOOR', "Door", ""),
            ('BALCONY', "Door + Window", "Balcony door with a window next to it and an optional slab under them"),
            ('LOGGIA', "Loggia", "Recess in the wall with a parapet in front and a door and window on its back wall"),
            ('ENTRANCE', "Entrance", "One to three doors with an optional porch slab and canopy"),
            ('CORNER', "Corner", "Outer corner of two walls with windows; the plinth and cornice wrap around it"),
            ('INNER_CORNER', "Inner Corner", "Inner corner where two walls with windows meet; the plinth and cornice follow it"),
            ('BAY', "Bay Window", "A box or splayed bay sticking out of the wall, with windows only"),
            ('NONE', "None", "Solid wall"),
        ],
        default='WINDOW',
    )
    open_width: FloatProperty(name="Width", default=1.2, min=0.1, soft_max=5.0, unit='LENGTH')
    open_height: FloatProperty(name="Height", default=1.4, min=0.1, soft_max=5.0, unit='LENGTH')
    count: IntProperty(name="Count", description="Number of openings in the wall", default=1, min=1, max=3)
    direction: EnumProperty(
        name="Layout",
        items=[
            ('HORIZONTAL', "Horizontal", "Openings side by side"),
            ('VERTICAL', "Vertical", "Openings stacked on top of each other (windows only)"),
        ],
        default='HORIZONTAL',
    )
    gap: FloatProperty(name="Gap", description="Distance between neighbouring openings", default=0.5, min=0.15, soft_max=3.0, unit='LENGTH')
    door_width: FloatProperty(name="Door Width", default=0.9, min=0.1, soft_max=3.0, unit='LENGTH')
    door_height: FloatProperty(name="Door Height", default=2.1, min=0.2, soft_max=4.0, unit='LENGTH')
    door_step: FloatProperty(name="Door Step", description="Threshold: how far the door sits above the slab", default=0.1, min=0.0, soft_max=0.5, unit='LENGTH')
    flip: BoolProperty(name="Door on Right", default=False)
    bay_width: FloatProperty(name="Bay Width", description="Width of the bay where it meets the wall", default=2.6, min=0.8, soft_max=6.0, unit='LENGTH')
    bay_depth: FloatProperty(name="Bay Depth", description="How far the bay sticks out of the wall", default=0.8, min=0.2, soft_max=3.0, unit='LENGTH')
    bay_splay: FloatProperty(name="Splay", description="How much narrower the front is on each side; 0 gives a box bay (at least 0.25 for a full-height bay)", default=0.5, min=0.0, soft_max=2.0, unit='LENGTH')
    bay_floor: FloatProperty(name="Bay Floor Height", description="Height of the bottom of the bay above the bottom of the module", default=0.6, min=0.1, soft_max=2.0, unit='LENGTH')
    bay_height: FloatProperty(name="Bay Height", default=2.0, min=0.8, soft_max=4.0, unit='LENGTH')
    bay_full: BoolProperty(name="Full Height", description="The bay takes the whole width and height of the module, with no top, bottom or wall around it, so floors can be stacked", default=False)
    bay_side_windows: BoolProperty(name="Windows on the Sides", description="Windows on the two side faces as well as on the front", default=True)
    corner_walls: EnumProperty(
        name="Windows",
        items=[
            ('BOTH', "Both Walls", "A window group on each wall"),
            ('ONE', "One Wall", "Windows on the front wall only, the side wall stays plain"),
        ],
        default='BOTH',
    )
    porch: BoolProperty(name="Porch Slab", description="Slab in front of the doors, standing on the ground", default=True)
    porch_thickness: FloatProperty(name="Thickness", default=0.2, min=0.02, soft_max=0.6, unit='LENGTH')
    porch_depth: FloatProperty(name="Depth", description="How far the porch sticks out of the wall", default=1.5, min=0.05, soft_max=5.0, unit='LENGTH')
    porch_margin: FloatProperty(name="Side Margin", description="Plain wall left and right of the porch and canopy; 0 spans the whole module", default=0.0, min=0.0, soft_max=1.0, unit='LENGTH')
    canopy: BoolProperty(name="Canopy", description="Slab above the doors", default=False)
    canopy_thickness: FloatProperty(name="Thickness", default=0.15, min=0.02, soft_max=0.6, unit='LENGTH')
    canopy_depth: FloatProperty(name="Depth", description="How far the canopy sticks out of the wall", default=1.0, min=0.05, soft_max=4.0, unit='LENGTH')
    canopy_gap: FloatProperty(name="Gap above Door", description="Distance between the top of the door and the canopy", default=0.3, min=0.1, soft_max=1.0, unit='LENGTH')
    loggia_content: EnumProperty(
        name="Back Wall",
        items=[
            ('BOTH', "Door + Window", "A door and a window on the back wall of the loggia"),
            ('DOOR', "Door Only", "A single door in the middle of the back wall"),
        ],
        default='BOTH',
    )
    loggia_width: FloatProperty(name="Loggia Width", default=2.6, min=0.8, soft_max=6.0, unit='LENGTH')
    loggia_height: FloatProperty(name="Opening Height", description="Height of the opening above the parapet", default=1.2, min=0.3, soft_max=3.0, unit='LENGTH')
    loggia_depth: FloatProperty(name="Loggia Depth", description="How deep the loggia is cut into the wall", default=1.2, min=0.4, soft_max=4.0, unit='LENGTH')
    loggia_floor: FloatProperty(name="Floor Height", description="Height of the loggia floor above the bottom of the module", default=0.3, min=0.0, soft_max=2.0, unit='LENGTH')
    parapet_height: FloatProperty(name="Parapet Height", description="Height of the parapet above the loggia floor", default=1.1, min=0.3, soft_max=2.0, unit='LENGTH')
    parapet_thickness: FloatProperty(name="Parapet Thickness", default=0.15, min=0.03, soft_max=0.6, unit='LENGTH')
    depth: FloatProperty(name="Depth", description="How deep the opening is pushed into the wall (towards -Y)", default=0.2, min=0.0, soft_max=1.0, unit='LENGTH')
    offset_x: FloatProperty(name="Offset X", description="Shift from the module center", default=0.0, soft_min=-5.0, soft_max=5.0, unit='LENGTH')
    sill_height: FloatProperty(name="Height from Floor", default=0.9, min=0.0, soft_max=5.0, unit='LENGTH')

    arch: BoolProperty(name="Arched Top", default=False)
    arch_type: EnumProperty(
        name="Arch",
        items=[
            ('ROUND', "Round", "Circular arch, at most a semicircle"),
            ('POINTED', "Pointed", "Gothic arch made of two arcs; a higher rise gives a sharper point"),
        ],
        default='ROUND',
    )
    arch_rise: FloatProperty(name="Arch Rise", description="Height of the arch. Round: half the opening width gives a semicircle. Pointed: higher is sharper", default=0.6, min=0.01, soft_max=3.0, unit='LENGTH')
    arch_segments: IntProperty(name="Segments", default=8, min=2, max=32)

    pediment: BoolProperty(name="Pediment", description="A triangular gable over a straight top instead of the trapezoid lintel", default=False)
    keystone: BoolProperty(name="Keystone", description="A block at the top of the arch band (or of the frame over an arch) that sticks out further than the band", default=False)
    keystone_depth: FloatProperty(name="Keystone Depth", description="How far the keystone sticks out of the band", default=0.04, min=0.01, soft_max=0.2, unit='LENGTH')
    panel: BoolProperty(name="Panel under Window", description="A rectangle of the wall pushed out (or in) under the window", default=False)
    panel_height: FloatProperty(name="Panel Height", default=0.5, min=0.1, soft_max=1.5, unit='LENGTH')
    panel_depth: FloatProperty(name="Panel Depth", description="How far the panel sticks out of the wall; a negative value sinks it into the wall", default=0.03, min=-0.3, max=0.3, unit='LENGTH')
    belt: BoolProperty(name="Belt Course", description="A thin band across the wall above the openings, with a plain strip of wall above it", default=False)
    belt_height: FloatProperty(name="Belt Height", default=0.12, min=0.03, soft_max=0.5, unit='LENGTH')
    belt_depth: FloatProperty(name="Belt Depth", description="How far the belt sticks out of the wall", default=0.06, min=0.02, soft_max=0.5, unit='LENGTH')
    belt_gap: FloatProperty(name="Wall above Belt", description="Plain wall between the belt and the top of the module", default=0.3, min=0.0, soft_max=1.0, unit='LENGTH')
    pilasters: EnumProperty(
        name="Pilasters",
        items=[
            ('NONE', "None", "No pilasters"),
            ('BOTH', "Both", "A pilaster at each end of the module"),
            ('LEFT', "Left", "A pilaster at the left end only"),
            ('RIGHT', "Right", "A pilaster at the right end only"),
        ],
        default='NONE',
    )
    pilaster_width: FloatProperty(name="Pilaster Width", default=0.25, min=0.05, soft_max=0.8, unit='LENGTH')
    pilaster_depth: FloatProperty(name="Pilaster Depth", description="How far the pilasters stick out of the wall", default=0.1, min=0.02, soft_max=0.5, unit='LENGTH')

    frame: BoolProperty(name="Window Frame", description="Two posts and a head round the window, extruded out of the wall; over an arch the head is an arch band. Replaces the trim", default=False)
    frame_width: FloatProperty(name="Frame Width", default=0.12, min=0.03, soft_max=0.5, unit='LENGTH')
    frame_depth: FloatProperty(name="Frame Depth", description="How far the frame sticks out of the wall", default=0.04, min=0.02, soft_max=0.3, unit='LENGTH')
    trim: BoolProperty(name="Window Trim", description="A trapezoid lintel over a straight top, an arch band round an arch, extruded out of the wall", default=False)
    trim_height: FloatProperty(name="Lintel Height", default=0.35, min=0.05, soft_max=1.0, unit='LENGTH')
    trim_flare: FloatProperty(name="Lintel Flare", description="How much wider the lintel is than the window on each side, at its top", default=0.15, min=0.0, soft_max=0.6, unit='LENGTH')
    trim_width: FloatProperty(name="Arch Band Width", default=0.2, min=0.03, soft_max=0.6, unit='LENGTH')
    trim_depth: FloatProperty(name="Trim Depth", description="How far the trim sticks out of the wall", default=0.06, min=0.02, soft_max=0.3, unit='LENGTH')
    sill: BoolProperty(name="Window Sill", default=True)
    sill_thickness: FloatProperty(name="Thickness", default=0.08, min=0.01, soft_max=0.5, unit='LENGTH')
    sill_depth: FloatProperty(name="Depth", description="How far the sill sticks out of the wall", default=0.1, min=0.01, soft_max=0.5, unit='LENGTH')

    slab: BoolProperty(name="Balcony Slab", description="Slab under the door and window; the door stands on it", default=True)
    slab_thickness: FloatProperty(name="Thickness", default=0.2, min=0.02, soft_max=0.6, unit='LENGTH')
    slab_depth: FloatProperty(name="Depth", description="How far the slab sticks out of the wall", default=1.2, min=0.05, soft_max=4.0, unit='LENGTH')
    slab_margin: FloatProperty(name="Side Margin", description="Plain wall left and right of the slab", default=0.15, min=0.0, soft_max=1.0, unit='LENGTH')
    slab_offset: FloatProperty(name="Bottom Offset", description="Wall strip below the slab", default=0.1, min=0.0, soft_max=1.0, unit='LENGTH')

    base: BoolProperty(name="Plinth", description="Rectangular band along the bottom of the module, sticking out of the wall", default=False)
    base_height: FloatProperty(name="Height", default=0.3, min=0.02, soft_max=1.0, unit='LENGTH')
    base_depth: FloatProperty(name="Depth", description="How far the plinth sticks out of the wall", default=0.15, min=0.02, soft_max=1.0, unit='LENGTH')
    cornice: BoolProperty(name="Cornice", description="Rectangular band along the top of the module, sticking out of the wall", default=False)
    cornice_height: FloatProperty(name="Height", default=0.3, min=0.02, soft_max=1.0, unit='LENGTH')
    cornice_depth: FloatProperty(name="Depth", description="How far the cornice sticks out of the wall", default=0.25, min=0.02, soft_max=1.0, unit='LENGTH')

    smooth: BoolProperty(name="Smooth by Angle", description="Smooth shading for edges flatter than the angle; sharper edges stay hard", default=True)
    smooth_angle: FloatProperty(name="Angle", default=math.radians(30), min=0.0, max=math.radians(180), subtype='ANGLE')
    uvs: BoolProperty(name="Auto UV", description="Cube-project and pack the UVs, the same way as Auto UV in TechArt Tools", default=True)
    uv_margin: FloatProperty(name="UV Margin", description="Margin left between packed UV islands", default=0.01, min=0.0, max=0.5, subtype='FACTOR')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column(align=True)
        col.prop(self, "width")
        col.prop(self, "height")
        if self.opening not in {'CORNER', 'INNER_CORNER'}:
            layout.prop(self, "pivot")

        layout.separator()
        layout.prop(self, "opening", expand=True)
        balcony = self.opening in {'BALCONY', 'LOGGIA'}
        loggia = self.opening == 'LOGGIA'
        entrance = self.opening == 'ENTRANCE'
        windowed = self.opening in {'WINDOW', 'CORNER', 'INNER_CORNER', 'BAY'}
        bay = self.opening == 'BAY'
        if self.opening in {'CORNER', 'INNER_CORNER'}:
            layout.prop(self, "corner_walls", expand=True)
        if self.opening != 'NONE':
            col = layout.column(align=True)
            if bay:
                col.prop(self, "bay_full")
                if not self.bay_full:
                    col.prop(self, "bay_width")
                col.prop(self, "bay_depth")
                col.prop(self, "bay_splay")
                if not self.bay_full:
                    col.prop(self, "bay_floor")
                    col.prop(self, "bay_height")
                col.prop(self, "bay_side_windows")
                col = layout.column(align=True)
            if loggia:
                col.prop(self, "loggia_content", expand=True)
                col.prop(self, "loggia_width")
                col.prop(self, "loggia_height")
                col.prop(self, "loggia_depth")
                col.prop(self, "loggia_floor")
                col.prop(self, "parapet_height")
                col.prop(self, "parapet_thickness")
                col = layout.column(align=True)
            if balcony:
                col.prop(self, "door_width")
                col.prop(self, "door_height")
                if not (loggia and self.loggia_content == 'DOOR'):
                    col.prop(self, "open_width", text="Window Width")
                    col.prop(self, "open_height", text="Window Height")
                    col.prop(self, "gap")
                    col.prop(self, "flip")
            elif entrance:
                col.prop(self, "door_width")
                col.prop(self, "door_height")
                col.prop(self, "door_step")
                col.prop(self, "count")
                if self.count > 1:
                    col.prop(self, "gap")
            else:
                col.prop(self, "open_width")
                col.prop(self, "open_height")
                if self.opening == 'DOOR':
                    col.prop(self, "door_step")
            col.prop(self, "depth")
            col.prop(self, "offset_x")
            if not balcony and not entrance and not bay:
                col.prop(self, "count", slider=True)
                if self.count > 1:
                    if windowed:
                        col.prop(self, "direction")
                    col.prop(self, "gap")
                if windowed:
                    col.prop(self, "sill_height")

            layout.prop(self, "arch")
            if self.arch:
                layout.prop(self, "arch_type", expand=True)
                col = layout.column(align=True)
                col.prop(self, "arch_rise", slider=True)
                col.prop(self, "arch_segments", slider=True)

            if entrance:
                layout.prop(self, "porch")
                if self.porch:
                    col = layout.column(align=True)
                    col.prop(self, "porch_thickness", text="Porch Thickness")
                    col.prop(self, "porch_depth", text="Porch Depth")
                layout.prop(self, "canopy")
                if self.canopy:
                    col = layout.column(align=True)
                    col.prop(self, "canopy_thickness", text="Canopy Thickness")
                    col.prop(self, "canopy_depth", text="Canopy Depth")
                    col.prop(self, "canopy_gap")
                layout.prop(self, "porch_margin")

            if self.opening in {'WINDOW', 'DOOR', 'CORNER', 'INNER_CORNER', 'BAY'}:
                layout.prop(self, "frame")
                if self.frame:
                    col = layout.column(align=True)
                    col.prop(self, "frame_width", slider=True)
                    col.prop(self, "frame_depth", slider=True)
                layout.prop(self, "trim")
                if self.trim and not self.frame:
                    col = layout.column(align=True)
                    col.prop(self, "trim_height", slider=True)
                    col.prop(self, "trim_flare", slider=True)
                    col.prop(self, "trim_width", slider=True)
                    col.prop(self, "trim_depth", slider=True)
                    if not self.arch:
                        col.prop(self, "pediment")
                if self.arch and (self.trim or self.frame):
                    layout.prop(self, "keystone")
                    if self.keystone:
                        layout.prop(self, "keystone_depth", slider=True)

            if self.opening in {'WINDOW', 'CORNER', 'INNER_CORNER', 'BAY'}:
                layout.prop(self, "panel")
                if self.panel:
                    col = layout.column(align=True)
                    col.prop(self, "panel_height", slider=True)
                    col.prop(self, "panel_depth", slider=True)

            if self.opening in {'WINDOW', 'BALCONY', 'LOGGIA', 'CORNER', 'INNER_CORNER', 'BAY'}:
                layout.prop(self, "sill")
                if self.sill:
                    col = layout.column(align=True)
                    col.prop(self, "sill_thickness", slider=True)
                    col.prop(self, "sill_depth", slider=True)

            if self.opening == 'BALCONY':
                layout.prop(self, "slab")
                if self.slab:
                    col = layout.column(align=True)
                    col.prop(self, "slab_thickness", text="Slab Thickness")
                    col.prop(self, "slab_depth", text="Slab Depth")
                    col.prop(self, "door_step")
                    col.prop(self, "slab_margin")
                    col.prop(self, "slab_offset")

        if self.opening != 'BAY' or self.bay_full:   # an ordinary bay does not use the plinth and the cornice
            layout.separator()
            layout.prop(self, "base")
            if self.base:
                col = layout.column(align=True)
                col.prop(self, "base_height", text="Plinth Height", slider=True)
                col.prop(self, "base_depth", text="Plinth Depth", slider=True)
            layout.prop(self, "cornice")
            if self.cornice:
                col = layout.column(align=True)
                col.prop(self, "cornice_height", text="Cornice Height", slider=True)
                col.prop(self, "cornice_depth", text="Cornice Depth", slider=True)
        if self.opening != 'BAY':
            layout.prop(self, "belt")
            if self.belt:
                col = layout.column(align=True)
                col.prop(self, "belt_height", slider=True)
                col.prop(self, "belt_depth", slider=True)
                col.prop(self, "belt_gap", slider=True)
        if self.opening in {'WINDOW', 'DOOR', 'NONE', 'CORNER', 'INNER_CORNER'}:
            layout.prop(self, "pilasters", expand=True)
            if self.pilasters != 'NONE':
                col = layout.column(align=True)
                col.prop(self, "pilaster_width", slider=True)
                col.prop(self, "pilaster_depth", slider=True)
                if self.base or self.cornice or self.belt:
                    layout.label(text="Not used with a plinth, cornice or belt", icon='INFO')

        layout.separator()
        layout.prop(self, "smooth")
        if self.smooth:
            layout.prop(self, "smooth_angle")
        layout.prop(self, "uvs")
        if self.uvs:
            layout.prop(self, "uv_margin")
        layout.prop(self, "align")
        layout.prop(self, "location")
        layout.prop(self, "rotation")

    def execute(self, context):
        params = {
            "width": self.width,
            "height": self.height,
            "depth": self.depth,
            "count": self.count,
            "direction": self.direction,
            "gap": self.gap,
            "opening": self.opening,
            "open_width": self.open_width,
            "open_height": self.open_height,
            "offset_x": self.offset_x,
            "sill_height": self.sill_height,
            "arch": self.arch,
            "arch_type": self.arch_type,
            "arch_rise": self.arch_rise,
            "arch_segments": self.arch_segments,
            "sill": self.sill,
            "sill_thickness": self.sill_thickness,
            "sill_depth": self.sill_depth,
            "door_width": self.door_width,
            "door_height": self.door_height,
            "flip": self.flip,
            "loggia_content": self.loggia_content,
            "loggia_width": self.loggia_width,
            "loggia_height": self.loggia_height,
            "loggia_depth": self.loggia_depth,
            "loggia_floor": self.loggia_floor,
            "parapet_height": self.parapet_height,
            "parapet_thickness": self.parapet_thickness,
            "door_step": self.door_step,
            "pediment": self.pediment,
            "keystone": self.keystone,
            "keystone_depth": self.keystone_depth,
            "panel": self.panel,
            "panel_height": self.panel_height,
            "panel_depth": self.panel_depth,
            "belt": self.belt,
            "belt_height": self.belt_height,
            "belt_depth": self.belt_depth,
            "belt_gap": self.belt_gap,
            "pilasters": self.pilasters,
            "pilaster_width": self.pilaster_width,
            "pilaster_depth": self.pilaster_depth,
            "frame": self.frame,
            "frame_width": self.frame_width,
            "frame_depth": self.frame_depth,
            "trim": self.trim,
            "trim_height": self.trim_height,
            "trim_flare": self.trim_flare,
            "trim_width": self.trim_width,
            "trim_depth": self.trim_depth,
            "bay_width": self.bay_width,
            "bay_depth": self.bay_depth,
            "bay_splay": self.bay_splay,
            "bay_full": self.bay_full,
            "bay_floor": self.bay_floor,
            "bay_height": self.bay_height,
            "bay_side_windows": self.bay_side_windows,
            "corner_walls": self.corner_walls,
            "base": self.base,
            "base_height": self.base_height,
            "base_depth": self.base_depth,
            "cornice": self.cornice,
            "cornice_height": self.cornice_height,
            "cornice_depth": self.cornice_depth,
            "porch": self.porch,
            "porch_thickness": self.porch_thickness,
            "porch_depth": self.porch_depth,
            "porch_margin": self.porch_margin,
            "canopy": self.canopy,
            "canopy_thickness": self.canopy_thickness,
            "canopy_depth": self.canopy_depth,
            "canopy_gap": self.canopy_gap,
            "slab": self.slab,
            "slab_thickness": self.slab_thickness,
            "slab_depth": self.slab_depth,
            "slab_margin": self.slab_margin,
            "slab_offset": self.slab_offset,
        }

        bm = bmesh.new()
        generator.build_module(bm, params)
        if self.opening not in {'CORNER', 'INNER_CORNER'}:
            generator.apply_pivot(bm, self.pivot, self.width)

        mesh = bpy.data.meshes.new("WallModule")
        bm.to_mesh(mesh)
        bm.free()

        object_data_add(context, mesh, operator=self)
        context.object.name = "Wall_" + self.opening.title()

        was_editing = context.mode == 'EDIT_MESH'
        if was_editing:
            bpy.ops.object.mode_set(mode='OBJECT')
        if self.smooth:
            bpy.ops.object.shade_smooth_by_angle(angle=self.smooth_angle, keep_sharp_edges=False)
        if self.uvs:
            self.unwrap()
        if was_editing:
            bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}

    def unwrap(self):
        """Same recipe as Auto UV in TechArt Tools: cube projection, then pack without rotation."""
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.cube_project()
        bpy.ops.uv.pack_islands(rotate=False, scale=True, margin=self.uv_margin)
        bpy.ops.object.mode_set(mode='OBJECT')


def menu_func(self, context):
    self.layout.operator(HOUSE_OT_add_wall_module.bl_idname, text="Wall Module", icon='MOD_BUILD')


classes = (HOUSE_OT_add_wall_module,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)


def unregister():
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
