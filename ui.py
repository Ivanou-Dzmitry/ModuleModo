import tomllib
from pathlib import Path

import bpy

from .operators import HOUSE_OT_add_wall_module


def _read_version():
    try:
        with open(Path(__file__).with_name("blender_manifest.toml"), "rb") as f:
            return tomllib.load(f)["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return ""


ADDON_VERSION = _read_version()


# Typical sizes in metres: window 1.2 x 1.4 with the sill at 0.9, interior door 0.9 x 2.1.
_WINDOW = {"opening": 'WINDOW', "arch": False, "arch_type": 'ROUND', "sill": True, "count": 1, "direction": 'HORIZONTAL', "offset_x": 0.0,
           "open_width": 1.2, "open_height": 1.4, "sill_height": 0.9, "gap": 0.5,
           "door_width": 0.9, "door_height": 2.1, "door_step": 0.1, "flip": False, "slab": True,
           "corner_walls": 'BOTH', "base": False, "base_height": 0.3, "base_depth": 0.15,
           "cornice": False, "cornice_height": 0.3, "cornice_depth": 0.25}

# Door + window on a balcony slab: the door stands on a small threshold above the slab and the
# window top is level with the door top.
_BALCONY = {**_WINDOW, "opening": 'BALCONY', "door_width": 0.9, "door_height": 2.1, "door_step": 0.1,
            "open_width": 1.2, "open_height": 1.2, "gap": 0.4, "slab_thickness": 0.2, "slab_depth": 1.2,
            "slab_margin": 0.15, "slab_offset": 0.1}

# Entrance: doors on a threshold, an optional porch slab (stands on the ground) and an optional canopy.
_ENTRANCE = {**_WINDOW, "opening": 'ENTRANCE', "door_width": 1.0, "door_height": 2.1, "door_step": 0.1, "gap": 0.3,
             "porch": True, "porch_thickness": 0.2, "porch_depth": 1.5, "porch_margin": 0.0,
             "canopy": False, "canopy_thickness": 0.15, "canopy_depth": 1.0, "canopy_gap": 0.3}

# Every button sets the full layout, so a button never inherits sizes from the previous one.
PRESETS = (
    ("Window Wall", _WINDOW),
    ("Window Wall (No Sill)", {**_WINDOW, "sill": False}),
    ("2 Windows (Horizontal)", {**_WINDOW, "count": 2, "open_width": 0.8, "gap": 0.6}),
    ("2 Windows (Vertical)", {**_WINDOW, "count": 2, "direction": 'VERTICAL', "open_height": 0.7, "sill_height": 0.7, "gap": 0.4}),
    ("Window Wall + Plinth + Cornice", {**_WINDOW, "base": True, "cornice": True}),
    ("Corner: 2 Windows", {**_WINDOW, "opening": 'CORNER', "corner_walls": 'BOTH', "base": True, "cornice": True}),
    ("Corner: 1 Window", {**_WINDOW, "opening": 'CORNER', "corner_walls": 'ONE', "base": True, "cornice": True}),
    ("Pointed Window", {**_WINDOW, "arch": True, "arch_type": 'POINTED', "open_width": 0.8, "open_height": 2.0,
                        "arch_rise": 0.9, "arch_segments": 6, "sill_height": 0.7}),
    ("Door Wall", {**_WINDOW, "opening": 'DOOR', "open_width": 0.9, "open_height": 2.1, "sill": False}),
    ("Entrance: Door + Porch", _ENTRANCE),
    ("Entrance: Porch + Canopy", {**_ENTRANCE, "canopy": True}),
    ("Entrance: 2 Doors", {**_ENTRANCE, "canopy": True, "count": 2, "door_width": 0.9}),
    ("Balcony: Door + Window", _BALCONY),
    ("Door + Window (No Slab)", {**_BALCONY, "slab": False}),
    ("Loggia", {**_BALCONY, "opening": 'LOGGIA', "door_step": 0.1, "loggia_width": 2.6, "loggia_height": 1.2,
                "loggia_depth": 1.2, "loggia_floor": 0.3, "parapet_height": 1.1, "parapet_thickness": 0.15}),
    ("Solid Wall", {**_WINDOW, "opening": 'NONE'}),
)


class HOUSE_PT_modules(bpy.types.Panel):
    bl_label = "ModuleModo"
    bl_idname = "HOUSE_PT_modules"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ModuleModo"

    def draw(self, context):
        self.bl_label = "ModuleModo v%s" % ADDON_VERSION
        layout = self.layout
        for label, preset in PRESETS:
            op = layout.operator(HOUSE_OT_add_wall_module.bl_idname, text=label, icon='MOD_BUILD')
            for key, value in preset.items():
                setattr(op, key, value)


classes = (HOUSE_PT_modules,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
