bl_info = {
    "name": "Splatoon Scene Importer",
    "author": "blancgoat",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "File > Import > Splatoon Scene (.dae .fbx)",
    "description": "Importer for Splatoon models with automatic texture linking.",
    "category": "Import-Export",
}

import bpy
from .splatoon_scene_importer import SplatoonSceneImporter, SplatoonSceneImporterDragDrop, IO_FH_splatoon

def menu_func_import(self, context):
    self.layout.operator(SplatoonSceneImporter.bl_idname, text="Splatoon Scene (.dae .fbx)")

def register():
    bpy.types.Scene.is_scale_armature_splatoon_scene_importer = bpy.props.BoolProperty(
        name="Scale Armature",
        default=True
    )
    bpy.types.Scene.scale_value_splatoon_scene_importer = bpy.props.FloatProperty(
        name="Scale Value",
        default=1.0,
        min=0.01
    )
    bpy.utils.register_class(SplatoonSceneImporter)
    bpy.utils.register_class(SplatoonSceneImporterDragDrop)
    bpy.utils.register_class(IO_FH_splatoon)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    del bpy.types.Scene.is_scale_armature_splatoon_scene_importer
    del bpy.types.Scene.scale_value_splatoon_scene_importer
    bpy.utils.unregister_class(SplatoonSceneImporter)
    bpy.utils.unregister_class(SplatoonSceneImporterDragDrop)
    bpy.utils.unregister_class(IO_FH_splatoon)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()