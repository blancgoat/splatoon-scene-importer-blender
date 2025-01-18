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

        # Add all files to queue
        for file_elem in self.files:
            filepath = os.path.join(self.directory, file_elem.name)
            file_path = os.path.dirname(filepath)
            file_name = os.path.splitext(file_elem.name)[0]
            processing_queue.append((filepath, file_path, file_name))

        # Start processing timer
        bpy.app.timers.register(process_next_file)

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

def process_next_file():
    """Process the next file in queue, including import and post-processing"""
    global processing_queue, imported_objects

    # If we have current objects to process
    if imported_objects:
        current_file_name, current_objects, current_file_path = imported_objects[0]

        # Process current objects
        for obj in current_objects:
            if obj.type == 'ARMATURE':
                if bpy.context.scene.is_scale_armature_splatoon_scene_importer:
                    scale = bpy.context.scene.scale_value_splatoon_scene_importer
                    obj.scale = (scale, scale, scale)
                obj.name = current_file_name
            elif obj.type == 'MESH':
                for mat_slot in obj.material_slots:
                    if mat_slot.material and mat_slot.material.use_nodes:
                        material_processor = MaterialProcessor(mat_slot.material, current_file_path)

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
        imported_objects.pop(0)
        bpy.ops.object.select_all(action='DESELECT')

    # If we have more files to process
    if processing_queue:
        filepath, file_path, file_name = processing_queue.popleft()

        # Store currently selected objects
        prev_selected = set(obj.name for obj in bpy.context.selected_objects)

        # Import file
        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.fbx':
            bpy.ops.import_scene.fbx(filepath=filepath)
        elif ext == '.dae':
            try:
                filepath = DAE_OT_import_via_fbx.convert(filepath)
                bpy.ops.import_scene.fbx(filepath=filepath)
                try:
                    os.unlink(filepath)
                except:
                    pass
            except (NotFoundConvertModule, FailConvert) as e:
                pass

        # Find newly imported objects
        new_objects = [obj for obj in bpy.context.selected_objects if obj.name not in prev_selected]
        imported_objects.append((file_name, new_objects, file_path))

        return 0.1  # Continue timer for next file

    return None  # Stop timer when all files are processed
