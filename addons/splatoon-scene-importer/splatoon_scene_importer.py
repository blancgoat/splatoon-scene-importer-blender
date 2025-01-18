import bpy
from .importers.splatoon.queueing import Queueing
from .utilities.DAE_OT_import_via_fbx import NotFoundConvertModule, FailConvert
from bpy_extras.io_utils import (
    poll_file_object_drop,
)

class SplatoonSceneImporter(bpy.types.Operator):
    bl_idname = "import_scene.splatoon_scene_importer"
    bl_label = "Splatoon Scene (.dae .fbx)"
    bl_options = {'REGISTER', 'UNDO'}
    _timer = None
    queue = None

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

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            try:
                if not self.queue or not self.queue.processing_queue:
                    # 모든 처리가 완료됨
                    self.cancel(context)
                    return {'FINISHED'}

                result = self.queue.process_next_file()
                if not result:
                    # 큐가 비었음
                    self.cancel(context)
                    return {'FINISHED'}

            except (NotFoundConvertModule, FailConvert) as e:
                self.report({'ERROR'}, f"Failed to convert file: {str(e)}")
                self.cancel(context)
                return {'CANCELLED'}
            except Exception as e:
                self.report({'ERROR'}, f"Unexpected error: {str(e)}")
                self.cancel(context)
                return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def execute(self, context):
        self.queue = Queueing(self.files, self.directory)

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

class SplatoonSceneImporterDragDrop(SplatoonSceneImporter):
    bl_idname = "import_scene.splatoon_scene_importer_dragdrop"
    bl_label = "Import Splatoon scene"

    def invoke(self, context, event):
        return self.execute(context)

class IO_FH_splatoon(bpy.types.FileHandler):
    bl_idname = "IO_FH_splatoon"
    bl_label = "import Splatoon scene"
    bl_import_operator = "import_scene.splatoon_scene_importer_dragdrop"
    bl_file_extensions = ".dae;.fbx"

    @classmethod
    def poll_drop(cls, context):
        return poll_file_object_drop(context)
