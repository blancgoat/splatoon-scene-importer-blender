bl_info = {
    "name": "Splatoon FBX Importer",
    "author": "blancgoat",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "File > Import > Splatoon FBX (.fbx)",
    "description": "Enhanced FBX importer for Splatoon models with automatic texture linking.",
    "category": "Import-Export",
}

import bpy
from .import_splatoon_fbx import ImportSplatoonFbx

def menu_func_import(self, context):
    self.layout.operator(ImportSplatoonFbx.bl_idname, text="Splatoon FBX (.fbx)")

def register():
    bpy.types.Scene.is_scale_armature_splatoon_fbx_importer = bpy.props.BoolProperty(
        name="Scale Armature",
        default=True
    )
    bpy.types.Scene.scale_value_splatoon_fbx_importer = bpy.props.FloatProperty(
        name="Scale Value",
        default=1.0,
        min=0.01
    )
    bpy.utils.register_class(ImportSplatoonFbx)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    del bpy.types.Scene.is_scale_armature_splatoon_fbx_importer
    del bpy.types.Scene.scale_value_splatoon_fbx_importer
    bpy.utils.unregister_class(ImportSplatoonFbx)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()