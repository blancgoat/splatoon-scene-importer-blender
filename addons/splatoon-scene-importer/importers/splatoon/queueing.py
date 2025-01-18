import bpy
import os
from collections import deque
from .material_processor import MaterialProcessor
from ...utilities.DAE_OT_import_via_fbx import DAE_OT_import_via_fbx, NotFoundConvertModule, FailConvert

class Queueing:
    def __init__(self, files, directory):
        self.processing_queue = deque()
        self.imported_objects = []
        self.processing_queue.clear()
        self.imported_objects.clear()

        for file_elem in files:
            file_path = os.path.join(directory, file_elem.name)
            dir_path = os.path.dirname(file_path)
            file_splitext = os.path.splitext(file_elem.name)
            file_name = file_splitext[0]
            file_ext = file_splitext[1].lower()
            self.processing_queue.append((file_path, dir_path, file_name, file_ext))

    def process_next_file(self):
        """Process the next file in queue, including import and post-processing"""

        # If we have current objects to process
        if self.imported_objects:
            objects, file_name, file_path = self.imported_objects[0]

            # Process current objects
            for obj in objects:
                if obj.type == 'ARMATURE':
                    if bpy.context.scene.is_scale_armature_splatoon_scene_importer:
                        scale = bpy.context.scene.scale_value_splatoon_scene_importer
                        obj.scale = (scale, scale, scale)
                    obj.name = file_name
                elif obj.type == 'MESH':
                    for mat_slot in obj.material_slots:
                        if mat_slot.material and mat_slot.material.use_nodes:
                            material_processor = MaterialProcessor(mat_slot.material, file_path)

                            # metallic to 0
                            material_processor.principled_node.inputs['Metallic'].default_value = 0

                            # Alpha unlink
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

            # Clear current processed objects
            self.imported_objects.pop(0)
            bpy.ops.object.select_all(action='DESELECT')

        # If we have more files to process
        if self.processing_queue:
            file_path, dir_path, file_name, file_ext = self.processing_queue.popleft()

            # Store currently selected objects
            prev_selected = set(obj.name for obj in bpy.context.selected_objects)

            # Import file
            if file_ext == '.fbx':
                bpy.ops.import_scene.fbx(filepath=file_path)
            elif file_ext == '.dae':
                try:
                    file_path = DAE_OT_import_via_fbx.convert(file_path)
                    bpy.ops.import_scene.fbx(filepath=file_path)
                    try:
                        os.unlink(file_path)
                    except:
                        pass
                except (NotFoundConvertModule, FailConvert) as e:
                    pass

            # Find newly imported objects
            new_objects = [obj for obj in bpy.context.selected_objects if obj.name not in prev_selected]
            self.imported_objects.append((new_objects, file_name, dir_path))

            return 0.1  # Continue timer for next file

        return None  # Stop timer when all files are processed