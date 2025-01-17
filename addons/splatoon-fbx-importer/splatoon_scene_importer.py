import os
import bpy
from collections import deque
from .material_processor import MaterialProcessor
from .DAE_OT_import_via_fbx import DAE_OT_import_via_fbx, NotFoundConvertModule, FailConvert

processing_queue = deque()
imported_objects = []

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

    def execute(self, context):
        global processing_queue, imported_objects
        processing_queue.clear()
        imported_objects.clear()
        
        # 먼저 모든 파일 정보를 대기열에 추가
        for file_elem in self.files:
            filepath = os.path.join(self.directory, file_elem.name)
            file_path = os.path.dirname(filepath)
            file_name = os.path.splitext(file_elem.name)[0]
            processing_queue.append((filepath, file_path, file_name))
        
        # 첫 번째 파일 처리 시작
        if processing_queue:
            import_scene()
            
            # 후처리를 위한 타이머 등록
            bpy.app.timers.register(
                lambda: process_imported_fbx_after_delay(file_path)
            )
        
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
def process_imported_fbx_after_delay(file_path):
    """Wait until FBX import finishes before processing meshes."""
    global imported_objects
    
    if not imported_objects:
        return 0.1  # 임포트된 오브젝트가 없으면 재시도
    
    current_file_name, current_objects = imported_objects[0]
    
    # 현재 파일의 오브젝트만 처리
    for obj in current_objects:
        if obj.type == 'ARMATURE':
            if bpy.context.scene.is_scale_armature_splatoon_scene_importer:
                scale = bpy.context.scene.scale_value_splatoon_scene_importer
                obj.scale = (scale, scale, scale)
            obj.name = current_file_name  # 현재 파일 이름으로 설정
        elif obj.type == 'MESH':
            for mat_slot in obj.material_slots:
                if mat_slot.material and mat_slot.material.use_nodes:
                    material_processor = MaterialProcessor(mat_slot.material, file_path)
                    
                    # metallic to 0
                    material_processor.principled_node.inputs['Metallic'].default_value = 0
                    
                    # Alpha unlink (made by blender) (지우진 않음 가끔쓸때가있어서)
                    for link in material_processor.material.node_tree.links:
                        if (link.to_node == material_processor.principled_node and 
                            link.to_socket.name == 'Alpha'):
                            material_processor.material.node_tree.links.remove(link)
                    
                    # link textures
                    material_processor.link_texture_principled_node(
                        material_processor.import_texture('_mtl', non_color=True),
                        'Metallic'
                    )
                    material_processor.link_texture_principled_node(
                        material_processor.import_texture('_rgh', non_color=True),
                        'Roughness'
                    )
                    material_processor.link_texture_principled_node(
                        material_processor.import_texture('_opa', non_color=True),
                        'Alpha'
                    )
                    material_processor.import_normal()
                    material_processor.handle_emission()
    
    # 현재 파일 처리 완료
    imported_objects.pop(0)
    
    # 모든 객체 선택 해제
    bpy.ops.object.select_all(action='DESELECT')
    
    # 대기열에 다음 파일이 있으면 처리 시작
    if processing_queue:
        import_scene()
        return 0.1  # 다음 파일의 후처리를 위해 타이머 유지
    
    return None  # 모든 처리 완료


# TODO 기존로직이 시동거는로직이라 scene importer가 복잡해지니 답이없음. 새로운 아이디어 구상해야함
# importer 관련은 클래스로 밖으로빼고 얘는 블랜더 importer그리는역할만 담당하게 해야할듯?
def import_scene():
    filepath, file_path, file_name = processing_queue.popleft()
            
    # 현재 선택된 오브젝트 저장
    prev_selected = set(obj.name for obj in bpy.context.selected_objects)
    
    # import dae or fbx
    ext = os.path.splitext(filepath)[1].lower()

    if ext == '.fbx':
        bpy.ops.import_scene.fbx(filepath=filepath)
    elif ext == '.dae': # dae는 임시로 fbx로만든뒤 import후 삭제함, 블랜더 dae importer는 bone 데이터가 유실되기때문
        try:
            filepath = DAE_OT_import_via_fbx.convert(filepath)
        except NotFoundConvertModule as e:
            pass
            # self.report({'ERROR'}, str(e))
        except FailConvert as e:
            pass
            # self.report({'ERROR'}, str(e))
        else:
            bpy.ops.import_scene.fbx(filepath=filepath)
            try:
                os.unlink(filepath)
            except:
                pass
    # else:
    #     self.report({'ERROR'}, f"Unsupported file type: {ext}")            
    
    # 새로 임포트된 오브젝트 찾기
    new_objects = [obj for obj in bpy.context.selected_objects if obj.name not in prev_selected]
    imported_objects.append((file_name, new_objects))