import bpy
import os
from collections import deque
from .material_processor import MaterialProcessor
from ...utilities.DAE_OT_import_via_fbx import DAE_OT_import_via_fbx, NotFoundConvertModule, FailConvert

class Queueing:
    def __init__(self, files, directory):
        self.processing_queue = deque()
        self.processing_queue.clear()

        for file_elem in files:
            file_path = os.path.join(directory, file_elem.name)
            dir_path = os.path.dirname(file_path)
            file_splitext = os.path.splitext(file_elem.name)
            file_name = file_splitext[0]
            file_ext = file_splitext[1].lower()
            self.processing_queue.append((file_path, dir_path, file_name, file_ext))

    def process_material(self, matarial, file_path):
        """머티리얼 처리 함수"""
        material_processor = MaterialProcessor(matarial, file_path)

        # metallic to 0
        material_processor.principled_node.inputs['Metallic'].default_value = 0

        # link textures
        material_processor.link_texture_principled_node(
            'Metallic',
            '_mtl',
            non_color = True,
            location_y = material_processor.principled_node.location.y - 85
        )
        material_processor.link_texture_principled_node(
            'Roughness',
            '_rgh',
            non_color = True,
            location_y = material_processor.principled_node.location.y - 99
        )

        material_processor.import_alpha()
        material_processor.import_normal()
        material_processor.import_emission()
        if bpy.context.scene.is_apply_second_shader:
            if bpy.context.scene.shader_mix_style == 'COLOR':
                material_processor.import_second_color()
            elif bpy.context.scene.shader_mix_style == 'SHADE':
                material_processor.import_second_shader()

    def process_armature(self, obj, file_name):
        """아마추어 처리 함수"""
        if bpy.context.scene.is_scale_armature_splatoon_scene_importer:
            scale = bpy.context.scene.scale_value_splatoon_scene_importer
            obj.scale = (scale, scale, scale)
        obj.name = file_name

    def import_file(self, file_path, file_ext):
        """파일 임포트 함수"""
        if file_ext == '.fbx':
            bpy.ops.import_scene.fbx(filepath=file_path)
        elif file_ext == '.dae':
            converted_path = DAE_OT_import_via_fbx.convert(file_path)
            bpy.ops.import_scene.fbx(filepath=converted_path)
            try:
                os.unlink(converted_path)
            except:
                pass

        return [obj for obj in bpy.context.selected_objects]

    def process_imported_objects(self, objects, file_name, file_path):
        """임포트된 객체들 처리 함수"""
        materials = set()
        for obj in objects:
            if obj.type == 'ARMATURE':
                self.process_armature(obj, file_name)
            elif obj.type == 'MESH':
                for slot in obj.material_slots:
                    if slot.material and slot.material.use_nodes:
                        materials.add(slot.material)

        for material in materials:
            self.process_material(material, file_path)

    def process_next_file(self):
        """큐의 다음 파일 처리 함수"""
        if not self.processing_queue:
            return None

        file_path, dir_path, file_name, file_ext = self.processing_queue.popleft()

        prev_selected = set(obj.name for obj in bpy.context.selected_objects)
        new_objects = self.import_file(file_path, file_ext)
        self.process_imported_objects(new_objects, file_name, dir_path)
        bpy.ops.object.select_all(action='DESELECT')

        return True
