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
    arch_segments: IntProperty(name="Segments", default=4, min=2, max=32)

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
        if self.opening != 'CORNER':
            layout.prop(self, "pivot")

        layout.separator()
        layout.prop(self, "opening", expand=True)
        balcony = self.opening in {'BALCONY', 'LOGGIA'}
        loggia = self.opening == 'LOGGIA'
        entrance = self.opening == 'ENTRANCE'
        windowed = self.opening in {'WINDOW', 'CORNER'}
        if self.opening == 'CORNER':
            layout.prop(self, "corner_walls", expand=True)
        if self.opening != 'NONE':
            col = layout.column(align=True)
            if loggia:
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
            if not balcony and not entrance:
                col.prop(self, "count")
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
                col.prop(self, "arch_rise")
                col.prop(self, "arch_segments")

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

            if self.opening in {'WINDOW', 'BALCONY', 'LOGGIA', 'CORNER'}:
                layout.prop(self, "sill")
                if self.sill:
                    col = layout.column(align=True)
                    col.prop(self, "sill_thickness")
                    col.prop(self, "sill_depth")

            if self.opening == 'BALCONY':
                layout.prop(self, "slab")
                if self.slab:
                    col = layout.column(align=True)
                    col.prop(self, "slab_thickness", text="Slab Thickness")
                    col.prop(self, "slab_depth", text="Slab Depth")
                    col.prop(self, "door_step")
                    col.prop(self, "slab_margin")
                    col.prop(self, "slab_offset")

        layout.separator()
        layout.prop(self, "base")
        if self.base:
            col = layout.column(align=True)
            col.prop(self, "base_height", text="Plinth Height")
            col.prop(self, "base_depth", text="Plinth Depth")
        layout.prop(self, "cornice")
        if self.cornice:
            col = layout.column(align=True)
            col.prop(self, "cornice_height", text="Cornice Height")
            col.prop(self, "cornice_depth", text="Cornice Depth")

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
            "loggia_width": self.loggia_width,
            "loggia_height": self.loggia_height,
            "loggia_depth": self.loggia_depth,
            "loggia_floor": self.loggia_floor,
            "parapet_height": self.parapet_height,
            "parapet_thickness": self.parapet_thickness,
            "door_step": self.door_step,
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
        if self.opening != 'CORNER':
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
