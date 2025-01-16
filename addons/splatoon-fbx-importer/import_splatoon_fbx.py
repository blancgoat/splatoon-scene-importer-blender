import os
import bpy
from collections import deque
from .material_processor import MaterialProcessor

processing_queue = deque()
imported_objects = []

class ImportSplatoonFbx(bpy.types.Operator):
    """Custom Splatoon FBX Importer with batch support"""
    bl_idname = "import_scene.splatoon_fbx"
    bl_label = "Splatoon FBX (.fbx)"
    bl_options = {'REGISTER', 'UNDO'}
    
    files: bpy.props.CollectionProperty(
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    directory: bpy.props.StringProperty(
        subtype='DIR_PATH',
        options={'HIDDEN'},
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, 'is_scale_armature_splatoon_fbx_importer')
        layout.prop(context.scene, 'scale_value_splatoon_fbx_importer')

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
            filepath, file_path, file_name = processing_queue.popleft()
            
            # 현재 선택된 오브젝트 저장
            prev_selected = set(obj.name for obj in bpy.context.selected_objects)
            
            # FBX 임포트
            bpy.ops.import_scene.fbx(filepath=filepath)
            
            # 새로 임포트된 오브젝트 찾기
            new_objects = [obj for obj in bpy.context.selected_objects if obj.name not in prev_selected]
            imported_objects.append((file_name, new_objects))
            
            # 후처리를 위한 타이머 등록
            bpy.app.timers.register(
                lambda: process_imported_fbx_after_delay(file_path, file_name)
            )
        
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
def process_imported_fbx_after_delay(file_path, file_name):
    """Wait until FBX import finishes before processing meshes."""
    global imported_objects
    
    if not imported_objects:
        return 0.1  # 임포트된 오브젝트가 없으면 재시도
    
    current_file_name, current_objects = imported_objects[0]
    
    # 현재 파일의 오브젝트만 처리
    for obj in current_objects:
        if obj.type == 'ARMATURE':
            if bpy.context.scene.is_scale_armature_splatoon_fbx_importer:
                scale = bpy.context.scene.scale_value_splatoon_fbx_importer
                obj.scale = (scale, scale, scale)
            obj.name = current_file_name  # 현재 파일 이름으로 설정
        elif obj.type == 'MESH':
            for mat_slot in obj.material_slots:
                if mat_slot.material and mat_slot.material.use_nodes:
                    material_processor = MaterialProcessor(mat_slot.material)
                    
                    # metallic to 0
                    material_processor.principled_node.inputs['Metallic'].default_value = 0
                    
                    # Alpha unlink (made by blender) (지우진 않음 가끔쓸때가있어서)
                    for link in material_processor.material.node_tree.links:
                        if (link.to_node == material_processor.principled_node and 
                            link.to_socket.name == 'Alpha'):
                            material_processor.material.node_tree.links.remove(link)
                    
                    base_name = MaterialProcessor.find_base_texture(mat_slot.material.node_tree.nodes) or MaterialProcessor.find_base_from_material(mat_slot.material)
                    
                    material_processor.link_texture_principled_node(
                        material_processor.import_texture(file_path, base_name, '_mtl', non_color=True),
                        'Metallic'
                    )
                    material_processor.link_texture_principled_node(
                        material_processor.import_texture(file_path, base_name, '_rgh', non_color=True),
                        'Roughness'
                    )
                    material_processor.link_texture_principled_node(
                        material_processor.import_texture(file_path, base_name, '_opa', non_color=True),
                        'Alpha'
                    )
                    material_processor.link_texture_normal(
                        material_processor.import_texture(file_path, base_name, '_nrm', non_color=True),
                        'Normal'
                    )

                    material_processor.handle_emission()
    
    # 현재 파일 처리 완료
    imported_objects.pop(0)
    
    # 모든 객체 선택 해제
    bpy.ops.object.select_all(action='DESELECT')
    
    # 대기열에 다음 파일이 있으면 처리 시작
    if processing_queue:
        filepath, file_path, file_name = processing_queue.popleft()
        
        # 현재 선택된 오브젝트 저장
        prev_selected = set(obj.name for obj in bpy.context.selected_objects)
        
        # 다음 FBX 임포트
        bpy.ops.import_scene.fbx(filepath=filepath)
        
        # 새로 임포트된 오브젝트 찾기
        new_objects = [obj for obj in bpy.context.selected_objects if obj.name not in prev_selected]
        imported_objects.append((file_name, new_objects))
        
        return 0.1  # 다음 파일의 후처리를 위해 타이머 유지
    
    return None  # 모든 처리 완료