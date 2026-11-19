import json
import re
from pathlib import Path

import bpy
from bpy.props import BoolProperty, StringProperty

from . import operators
from .operators import STAMP, snapshot

_presets = None     # name -> settings of the saved presets, read from the disk when first needed


def safe_name(name):
    """A name that is fine as a file name; letters of any language stay."""
    return re.sub(r"[^\w.\- ]+", "_", name).strip(" .") or "module"


def get_prefs(context):
    addon = context.preferences.addons.get(__package__)
    return addon.preferences if addon else None


def export_folder(context, override=""):
    prefs = get_prefs(context)
    raw = override or (prefs.export_dir if prefs else "")
    return Path(bpy.path.abspath(raw)) if raw else Path.home() / "ModuleModo"


def presets_dir(create=False):
    """The folder of the saved presets: in the extension's user folder, or in the config folder when the
    add-on is not installed as an extension."""
    try:
        return Path(bpy.utils.extension_path_user(__package__, path="presets", create=create))
    except (ValueError, RuntimeError, AttributeError):
        return Path(bpy.utils.user_resource('CONFIG', path="ModuleModo_presets", create=create))


def load_presets(refresh=False):
    global _presets
    if _presets is None or refresh:
        _presets = {}
        folder = presets_dir()
        for path in sorted(folder.glob("*.json")) if folder.is_dir() else ():
            try:
                data = json.loads(path.read_text("utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(data, dict) and isinstance(data.get("settings"), dict):
                _presets[str(data.get("name", path.stem))] = data["settings"]
    return _presets


def current_settings(context):
    """The settings of the active module, or the last used ones when it is not a module."""
    obj = context.object
    raw = obj.get(STAMP) if obj else None
    if raw:
        try:
            return json.loads(raw)
        except ValueError:
            pass
    last = context.window_manager.operator_properties_last(operators.HOUSE_OT_add_wall_module.bl_idname)
    return snapshot(last) if last else None


class HOUSE_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    export_dir: StringProperty(
        name="Export Folder",
        description="Where Export FBX puts the files",
        subtype='DIR_PATH',
        default=str(Path.home() / "ModuleModo"),
    )

    def draw(self, context):
        self.layout.prop(self, "export_dir")


class HOUSE_OT_export_fbx(bpy.types.Operator):
    bl_idname = "house.export_fbx"
    bl_label = "Export FBX"
    bl_description = "Save the selected modules, with their shutters, as FBX files in the export folder: one file per module"
    bl_options = {'REGISTER'}

    directory: StringProperty(name="Folder", description="Export folder; empty uses the one from the add-on preferences",
                              subtype='DIR_PATH', default="")
    at_origin: BoolProperty(name="At Origin", description="Export every module at the world origin with no rotation, whatever its place in the scene",
                            default=True)

    @classmethod
    def poll(cls, context):
        return any(o.type == 'MESH' for o in context.selected_objects)

    def execute(self, context):
        selected = [o for o in context.selected_objects if o.type == 'MESH']
        roots = [o for o in selected if o.parent not in selected]
        folder = export_folder(context, self.directory)
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            self.report({'ERROR'}, "Cannot create %s: %s" % (folder, error))
            return {'CANCELLED'}

        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        active = context.view_layer.objects.active
        selection = list(context.selected_objects)
        written = []
        try:
            for root in roots:
                group = [root] + [c for c in root.children_recursive if c.type == 'MESH']
                bpy.ops.object.select_all(action='DESELECT')
                for obj in group:
                    obj.select_set(True)
                context.view_layer.objects.active = root
                location, rotation = root.location.copy(), root.rotation_euler.copy()
                if self.at_origin and root.parent is None:
                    root.location = (0.0, 0.0, 0.0)
                    root.rotation_euler = (0.0, 0.0, 0.0)
                    context.view_layer.update()
                path = folder / (safe_name(root.name) + ".fbx")
                try:
                    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'MESH'},
                                             add_leaf_bones=False)
                finally:
                    root.location, root.rotation_euler = location, rotation
                written.append(path)
        finally:
            bpy.ops.object.select_all(action='DESELECT')
            for obj in selection:
                obj.select_set(True)
            context.view_layer.objects.active = active
            context.view_layer.update()
        self.report({'INFO'}, "Exported %d file(s) to %s" % (len(written), folder))
        return {'FINISHED'}


class HOUSE_OT_open_export_folder(bpy.types.Operator):
    bl_idname = "house.open_export_folder"
    bl_label = "Open Folder"
    bl_description = "Open the export folder in the file manager"

    def execute(self, context):
        folder = export_folder(context)
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            self.report({'ERROR'}, "Cannot create %s: %s" % (folder, error))
            return {'CANCELLED'}
        bpy.ops.wm.path_open(filepath=str(folder))
        return {'FINISHED'}


class HOUSE_OT_save_preset(bpy.types.Operator):
    bl_idname = "house.save_preset"
    bl_label = "Save Preset"
    bl_description = "Save the settings of the active module (or the last used ones) as a button of your own under My Presets"

    name: StringProperty(name="Name", default="My Module")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        name = self.name.strip()
        if not name:
            self.report({'ERROR'}, "Give the preset a name")
            return {'CANCELLED'}
        settings = current_settings(context)
        if not settings:
            self.report({'ERROR'}, "Add a module first: there are no settings to save")
            return {'CANCELLED'}
        path = presets_dir(create=True) / (safe_name(name) + ".json")
        try:
            path.write_text(json.dumps({"name": name, "settings": settings}, indent=2, ensure_ascii=False), "utf-8")
        except OSError as error:
            self.report({'ERROR'}, "Cannot save %s: %s" % (path, error))
            return {'CANCELLED'}
        load_presets(refresh=True)
        self.report({'INFO'}, "Saved preset %s" % name)
        return {'FINISHED'}


class HOUSE_OT_delete_preset(bpy.types.Operator):
    bl_idname = "house.delete_preset"
    bl_label = "Delete Preset"
    bl_description = "Delete this saved preset"

    name: StringProperty(name="Name")

    def execute(self, context):
        path = presets_dir() / (safe_name(self.name) + ".json")
        try:
            path.unlink()
        except OSError as error:
            self.report({'ERROR'}, "Cannot delete %s: %s" % (path, error))
            return {'CANCELLED'}
        load_presets(refresh=True)
        return {'FINISHED'}


def _add_preset_button(layout, name, settings):
    op = layout.operator(operators.HOUSE_OT_add_wall_module.bl_idname, text=name)
    for key, value in settings.items():
        try:
            setattr(op, key, value)
        except (AttributeError, TypeError, ValueError):
            pass     # a setting that this version does not have


def draw_export(layout, context):
    header, body = layout.panel("HOUSE_SECTION_export", default_closed=False)
    header.label(text="Export", icon='EXPORT')
    if body is None:
        return
    col = body.column(align=True)
    prefs = get_prefs(context)
    if prefs:
        col.prop(prefs, "export_dir", text="")
    row = col.row(align=True)
    row.operator(HOUSE_OT_export_fbx.bl_idname, text="Export FBX", icon='EXPORT')
    row.operator(HOUSE_OT_open_export_folder.bl_idname, text="Open Folder", icon='FILE_FOLDER')


def draw_presets(layout, context):
    header, body = layout.panel("HOUSE_SECTION_presets", default_closed=False)
    header.label(text="My Presets", icon='PRESET')
    if body is None:
        return
    col = body.column(align=True)
    col.operator(HOUSE_OT_save_preset.bl_idname, text="Save Settings as Preset...", icon='ADD')
    for name, settings in load_presets().items():
        row = col.row(align=True)
        _add_preset_button(row, name, settings)
        row.operator(HOUSE_OT_delete_preset.bl_idname, text="", icon='X').name = name


classes = (HOUSE_Preferences, HOUSE_OT_export_fbx, HOUSE_OT_open_export_folder, HOUSE_OT_save_preset,
           HOUSE_OT_delete_preset)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
