import bpy
from .importers.splatoon.queueing import Queueing

class SplatoonSceneImporter(bpy.types.Operator):
    bl_idname = "import_scene.splatoon_scene_importer"
    bl_label = "Splatoon Scene (.dae .fbx)"
    bl_options = {'REGISTER', 'UNDO'}

    files: bpy.props.CollectionProperty(
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    directory: bpy.props.StringProperty(
        subtype='DIR_PATH',
        options={'HIDDEN'},
    )

    filter_glob: bpy.props.StringProperty(
        default="*.dae;*.fbx",
        options={'HIDDEN'},
        maxlen=255,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, 'is_scale_armature_splatoon_scene_importer')
        layout.prop(context.scene, 'scale_value_splatoon_scene_importer')

    # TODO 텍스처 2번씩 import되는 버그있음
    def execute(self, context):
        quene = Queueing(self.files, self.directory)
        bpy.app.timers.register(quene.process_next_file)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
