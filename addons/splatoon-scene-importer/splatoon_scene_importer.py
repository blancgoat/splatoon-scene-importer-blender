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
        layout.prop(context.scene, 'is_apply_second_shader')

        col = layout.column()
        col.enabled = context.scene.is_apply_second_shader
        col.label(text="Shader Mix Style:")
        col.prop(context.scene, "shader_mix_style", expand=True)

        layout.prop(context.scene, 'is_scale_armature_splatoon_scene_importer')
        sub_col = layout.column()
        sub_col.enabled = context.scene.is_scale_armature_splatoon_scene_importer
        sub_col.prop(context.scene, 'scale_value_splatoon_scene_importer')

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

class SplatoonSceneImporterDragDrop(bpy.types.Operator):
    bl_idname = "import_scene.splatoon_scene_importer_dragdrop"
    bl_label = "Splatoon Scene Drag & Drop (.dae .fbx)"
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
        layout.prop(context.scene, 'is_apply_second_shader')

        col = layout.column()
        col.enabled = context.scene.is_apply_second_shader
        col.label(text="Shader Mix Style:")
        col.prop(context.scene, "shader_mix_style", expand=True)

        layout.prop(context.scene, 'is_scale_armature_splatoon_scene_importer')
        sub_col = layout.column()
        sub_col.enabled = context.scene.is_scale_armature_splatoon_scene_importer
        sub_col.prop(context.scene, 'scale_value_splatoon_scene_importer')

    def invoke(self, context, event):
        # 드래그 앤드롭으로 파일을 가져온 후, 레이아웃을 표시
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        self.queue = Queueing(self.files, self.directory)

        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            try:
                if not self.queue or not self.queue.processing_queue:
                    self.cancel(context)
                    return {'FINISHED'}

                result = self.queue.process_next_file()
                if not result:
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

    def cancel(self, context):
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

class IO_FH_splatoon(bpy.types.FileHandler):
    bl_idname = "IO_FH_splatoon"
    bl_label = "import Splatoon scene"
    bl_import_operator = "import_scene.splatoon_scene_importer_dragdrop"
    bl_file_extensions = ".dae;.fbx"

    @classmethod
    def poll_drop(cls, context):
        return poll_file_object_drop(context)
