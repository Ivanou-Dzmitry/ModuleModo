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
_WINDOW = {"width": 3.0, "height": 3.0, "below_ground": False, "opening": 'WINDOW', "arch": False, "arch_type": 'ROUND', "sill": True, "count": 1, "direction": 'HORIZONTAL', "offset_x": 0.0,
           "open_width": 1.2, "open_height": 1.4, "sill_height": 0.9, "gap": 0.5,
           "door_width": 0.9, "door_height": 2.1, "door_step": 0.1, "flip": False, "slab": True,
           "frame": False, "trim": False, "pediment": False, "shutters": False, "keystone": False, "panel": False, "belt": False,
           "pilasters": 'NONE', "corner_walls": 'BOTH', "bay_width": 2.6, "bay_depth": 0.8, "bay_splay": 0.5, "bay_floor": 0.6, "bay_height": 2.0,
           "bay_side_windows": True, "bay_full": False, "loggia_content": 'BOTH', "base": False, "base_height": 0.3, "base_depth": 0.15,
           "cornice": False, "cornice_height": 0.3, "cornice_depth": 0.25}

# Door + window on a balcony slab: the door stands on a small threshold above the slab and the
# window top is level with the door top.
_BALCONY = {**_WINDOW, "opening": 'BALCONY', "door_width": 0.9, "door_height": 2.1, "door_step": 0.1,
            "open_width": 1.2, "open_height": 1.2, "gap": 0.4, "slab_thickness": 0.2, "slab_depth": 1.2,
            "slab_margin": 0.15, "slab_offset": 0.1}

# Entrance: doors on a threshold, an optional porch slab (stands on the ground) and an optional canopy.
_ENTRANCE = {**_WINDOW, "opening": 'ENTRANCE', "door_width": 1.0, "door_height": 2.1, "door_step": 0.1, "gap": 0.3,
             "porch": True, "porch_thickness": 0.2, "porch_depth": 1.5, "porch_margin": 0.1,
             "stairs": False, "stairs_height": 1.0, "stairs_steps": 6, "stairs_tread": 0.3, "stairs_landing": 1.0,
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
    ("Inner Corner: 2 Windows", {**_WINDOW, "opening": 'INNER_CORNER', "corner_walls": 'BOTH', "base": True, "cornice": True}),
    ("Inner Corner: 1 Window", {**_WINDOW, "opening": 'INNER_CORNER', "corner_walls": 'ONE', "base": True, "cornice": True}),
    ("Bay Window", {**_WINDOW, "opening": 'BAY', "open_width": 1.0, "open_height": 1.2, "sill_height": 0.4}),
    ("Bay Window (Box)", {**_WINDOW, "opening": 'BAY', "open_width": 1.0, "open_height": 1.2, "sill_height": 0.4,
                          "bay_width": 2.0, "bay_depth": 0.7, "bay_splay": 0.0}),
    ("Bay Window (Full Height)", {**_WINDOW, "opening": 'BAY', "bay_full": True, "bay_depth": 0.8, "bay_splay": 0.5,
                                  "open_width": 1.2, "open_height": 1.4, "sill_height": 0.9}),
    ("Bay (Full Height) + Plinth", {**_WINDOW, "opening": 'BAY', "bay_full": True, "bay_depth": 0.8, "bay_splay": 0.5,
                                    "open_width": 1.2, "open_height": 1.4, "sill_height": 0.9, "base": True}),
    ("Bay (Full Height) + Cornice", {**_WINDOW, "opening": 'BAY', "bay_full": True, "bay_depth": 0.8, "bay_splay": 0.5,
                                     "open_width": 1.2, "open_height": 1.4, "sill_height": 0.9, "cornice": True}),
    ("Window + Lintel", {**_WINDOW, "trim": True}),
    ("Arched Window + Archivolt", {**_WINDOW, "trim": True, "arch": True, "arch_rise": 0.6, "arch_segments": 8,
                                   "open_height": 1.6}),
    ("Window + Frame", {**_WINDOW, "frame": True}),
    ("Arched Window + Frame", {**_WINDOW, "frame": True, "arch": True, "arch_rise": 0.6, "arch_segments": 8,
                               "open_height": 1.6}),
    ("Window + Pediment", {**_WINDOW, "trim": True, "pediment": True}),
    ("Arched Window + Keystone", {**_WINDOW, "trim": True, "keystone": True, "arch": True, "arch_rise": 0.6,
                                  "arch_segments": 9, "open_height": 1.6}),    # odd: a segment, not a vertex, at the crown
    ("Window + Panel", {**_WINDOW, "panel": True}),
    ("Window Wall + Belt Course", {**_WINDOW, "belt": True}),
    ("Window Wall + Pilasters", {**_WINDOW, "pilasters": 'BOTH'}),
    ("Window + Shutters", {**_WINDOW, "shutters": True}),
    ("Arched Window + Shutters", {**_WINDOW, "shutters": True, "arch": True, "arch_rise": 0.6, "arch_segments": 8,
                                  "open_height": 1.6}),
    ("Pointed Window + Shutters", {**_WINDOW, "shutters": True, "arch": True, "arch_type": 'POINTED', "open_width": 0.8,
                                   "open_height": 2.0, "arch_rise": 0.9, "arch_segments": 8, "sill_height": 0.7}),
    ("Pointed Window", {**_WINDOW, "arch": True, "arch_type": 'POINTED', "open_width": 0.8, "open_height": 2.0,
                        "arch_rise": 0.9, "arch_segments": 8, "sill_height": 0.7}),
    ("Door Wall", {**_WINDOW, "opening": 'DOOR', "open_width": 0.9, "open_height": 2.1, "sill": False}),
    ("Entrance: Door + Porch", _ENTRANCE),
    ("Entrance: Porch + Canopy", {**_ENTRANCE, "canopy": True}),
    ("Entrance: 2 Doors", {**_ENTRANCE, "canopy": True, "count": 2, "door_width": 0.9}),
    # A raised entrance: steps up from the ground to a landing 1 m high. The module is 4 m high, so that its
    # edges match the neighbouring 4 m modules (1 m of base and 3 m of storey).
    ("Entrance: Stairs", {**_ENTRANCE, "stairs": True, "height": 4.0}),
    ("Entrance: Stairs + Canopy", {**_ENTRANCE, "stairs": True, "height": 4.0, "canopy": True}),
    ("Entrance: Stairs, 2 Doors", {**_ENTRANCE, "stairs": True, "height": 4.0, "canopy": True, "count": 2, "door_width": 0.9}),
    ("Balcony: Door + Window", _BALCONY),
    ("Door + Window (No Slab)", {**_BALCONY, "slab": False}),
    ("Loggia", {**_BALCONY, "opening": 'LOGGIA', "door_step": 0.1, "loggia_width": 2.6, "loggia_height": 1.2,
                "loggia_depth": 1.2, "loggia_floor": 0.3, "parapet_height": 1.1, "parapet_thickness": 0.15}),
    ("Loggia (Door Only)", {**_BALCONY, "opening": 'LOGGIA', "loggia_content": 'DOOR', "door_step": 0.1, "loggia_width": 2.0,
                            "loggia_height": 1.2, "loggia_depth": 1.2, "loggia_floor": 0.3, "parapet_height": 1.1,
                            "parapet_thickness": 0.15}),
    ("Solid Wall", {**_WINDOW, "opening": 'NONE'}),
    # The underground band: a plain wall below level 0, its top edge at Z=0.
    ("Underground", {**_WINDOW, "opening": 'NONE', "height": 0.5, "below_ground": True}),
    # The technical floor over the last storey: a low module, 1 m by default.
    ("Attic: Plain", {**_WINDOW, "opening": 'NONE', "height": 1.0}),
    ("Attic: Window", {**_WINDOW, "height": 1.0, "open_width": 0.5, "open_height": 0.5, "sill_height": 0.25,
                       "sill": False}),
    ("Attic + Cornice: Plain", {**_WINDOW, "opening": 'NONE', "height": 1.0, "cornice": True, "cornice_height": 0.25}),
    ("Attic + Cornice: Window", {**_WINDOW, "height": 1.0, "open_width": 0.4, "open_height": 0.4, "sill_height": 0.15,
                                 "sill": False, "cornice": True, "cornice_height": 0.25}),
)


# The panel is grouped into collapsible sections. A row is either a single wide button (label None) or a
# caption followed by a few linked buttons: (caption, ((button text, preset name), ...)).
SECTIONS = (
    ("windows", "Windows", 'WINDOW', (
        ("Window", (("With Sill", "Window Wall"), ("No Sill", "Window Wall (No Sill)"))),
        ("2 Windows", (("Horizontal", "2 Windows (Horizontal)"), ("Vertical", "2 Windows (Vertical)"))),
        ("Trim", (("Lintel", "Window + Lintel"), ("Pediment", "Window + Pediment"),
                  ("Arch Band", "Arched Window + Archivolt"))),
        (None, (("Arch Band + Keystone", "Arched Window + Keystone"),)),
        ("Frame", (("Straight", "Window + Frame"), ("Arched", "Arched Window + Frame"))),
        ("Shutters", (("Straight", "Window + Shutters"), ("Round", "Arched Window + Shutters"),
                      ("Pointed", "Pointed Window + Shutters"))),
        (None, (("Window + Panel under It", "Window + Panel"),)),
        (None, (("Pointed Window", "Pointed Window"),)),
        (None, (("Window + Plinth + Cornice", "Window Wall + Plinth + Cornice"),)),
        ("Wall", (("Belt Course", "Window Wall + Belt Course"), ("Pilasters", "Window Wall + Pilasters"))),
    )),
    ("doors", "Doors and Entrance", 'HOME', (
        (None, (("Door", "Door Wall"),)),
        ("Entrance", (("Porch", "Entrance: Door + Porch"), ("Canopy", "Entrance: Porch + Canopy"),
                      ("2 Doors", "Entrance: 2 Doors"))),
        ("Entrance + Stairs", (("Stairs", "Entrance: Stairs"), ("Canopy", "Entrance: Stairs + Canopy"),
                               ("2 Doors", "Entrance: Stairs, 2 Doors"))),
    )),
    ("corners", "Corners", 'AXIS_TOP', (
        ("Outer Corner", (("2 Windows", "Corner: 2 Windows"), ("1 Window", "Corner: 1 Window"))),
        ("Inner Corner", (("2 Windows", "Inner Corner: 2 Windows"), ("1 Window", "Inner Corner: 1 Window"))),
    )),
    ("bays", "Bay Windows", 'MESH_CUBE', (
        ("Bay", (("Splayed", "Bay Window"), ("Box", "Bay Window (Box)"))),
        ("Full Height", (("Plain", "Bay Window (Full Height)"), ("Plinth", "Bay (Full Height) + Plinth"),
                         ("Cornice", "Bay (Full Height) + Cornice"))),
    )),
    ("balcony", "Balcony and Loggia", 'MOD_BUILD', (
        ("Balcony", (("With Slab", "Balcony: Door + Window"), ("No Slab", "Door + Window (No Slab)"))),
        ("Loggia", (("Door + Window", "Loggia"), ("Door Only", "Loggia (Door Only)"))),
    )),
    ("levels", "Underground and Attic", 'TRIA_DOWN', (
        (None, (("Underground (below Z=0)", "Underground"),)),
        ("Attic", (("Plain", "Attic: Plain"), ("Window", "Attic: Window"))),
        ("Attic + Cornice", (("Plain", "Attic + Cornice: Plain"), ("Window", "Attic + Cornice: Window"))),
    )),
    ("other", "Other", 'MESH_PLANE', (
        (None, (("Solid Wall", "Solid Wall"),)),
    )),
)

CAPTION_WIDTH = 0.34


def _add_button(layout, text, preset_name):
    op = layout.operator(HOUSE_OT_add_wall_module.bl_idname, text=text)
    for key, value in dict(PRESETS)[preset_name].items():
        setattr(op, key, value)


def draw_sections(layout):
    """Draw every section as a collapsible sub-panel; each stays open or closed by itself."""
    for key, title, icon, rows in SECTIONS:
        header, body = layout.panel("HOUSE_SECTION_" + key, default_closed=False)
        header.label(text=title, icon=icon)
        if body is None:
            continue
        col = body.column(align=True)
        for caption, buttons in rows:
            if caption is None:
                for text, preset_name in buttons:
                    _add_button(col, text, preset_name)
                continue
            split = col.split(factor=CAPTION_WIDTH, align=True)
            split.label(text=caption)
            row = split.row(align=True)
            for text, preset_name in buttons:
                _add_button(row, text, preset_name)


class HOUSE_PT_modules(bpy.types.Panel):
    bl_label = "ModuleModo"
    bl_idname = "HOUSE_PT_modules"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ModuleModo"

    def draw(self, context):
        self.bl_label = "ModuleModo v%s" % ADDON_VERSION
        draw_sections(self.layout)


classes = (HOUSE_PT_modules,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
