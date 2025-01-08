bl_info = {
    "name": "Splatoon FBX Importer",
    "author": "blancgoat",
    "version": (1, 5),
    "blender": (4, 0, 0),
    "location": "File > Import > Splatoon FBX (.fbx)",
    "description": "Enhanced FBX importer for Splatoon models with automatic texture linking.",
    "category": "Import-Export",
}

import bpy
import os

class MaterialProcessor:
    def __init__(self, material):
        self.material = material
        self.principled_node = self._find_principled_node()
        
    def _find_principled_node(self):
        """Find the Principled BSDF node in the material."""
        for node in self.material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                return node
        return None

    def set_metallic_value(self, value):
        """Set the metallic value for the material."""
        if self.principled_node:
            self.principled_node.inputs['Metallic'].default_value = value

    def link_texture(self, texture_dir, base_name, suffix, input_name, non_color=False, is_normal_map=False):
        """Link a texture to a material input."""
        if not self.principled_node:
            return

        texture_path = os.path.join(texture_dir, f"{base_name}{suffix}.png")
        if not os.path.exists(texture_path):
            return

        # Create a new image texture node
        tex_image_node = self.material.node_tree.nodes.new('ShaderNodeTexImage')
        tex_image_node.image = bpy.data.images.load(texture_path)
        if non_color:
            tex_image_node.image.colorspace_settings.name = 'Non-Color'

        if is_normal_map:
            # Create and connect a normal map node
            normal_map_node = self.material.node_tree.nodes.new('ShaderNodeNormalMap')
            self.material.node_tree.links.new(tex_image_node.outputs['Color'], normal_map_node.inputs['Color'])
            self.material.node_tree.links.new(normal_map_node.outputs['Normal'], self.principled_node.inputs[input_name])
        else:
            # Directly connect the texture to the specified input
            self.material.node_tree.links.new(tex_image_node.outputs['Color'], self.principled_node.inputs[input_name])

    def handle_alpha_connection(self, texture_dir, base_name):
        """Handle the alpha connection, removing existing links and connecting _Opa."""
        if not self.principled_node:
            return

        # Remove existing alpha links unconditionally
        for link in self.material.node_tree.links:
            if link.to_node == self.principled_node and link.to_socket.name == "Alpha":
                self.material.node_tree.links.remove(link)

        # Check for _Opa texture and connect if available
        alpha_path = os.path.join(texture_dir, f"{base_name}_Opa.png")
        if os.path.exists(alpha_path):
            tex_image_node = self.material.node_tree.nodes.new('ShaderNodeTexImage')
            tex_image_node.image = bpy.data.images.load(alpha_path)
            tex_image_node.image.colorspace_settings.name = 'Non-Color'
            self.material.node_tree.links.new(tex_image_node.outputs['Color'], self.principled_node.inputs['Alpha'])

class IMPORT_OT_splatoon_fbx(bpy.types.Operator):
    """Custom Splatoon FBX Importer"""
    bl_idname = "import_scene.splatoon_fbx"
    bl_label = "Splatoon FBX (.fbx)"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        # Get the file name without extension
        file_name = os.path.splitext(os.path.basename(self.filepath))[0]
        
        # Call the default FBX importer
        bpy.ops.import_scene.fbx(filepath=self.filepath)

        # Register timer with the file name parameter
        bpy.app.timers.register(lambda: process_imported_fbx_after_delay(file_name))

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
def find_albedo_texture(nodes):
    """Find the albedo texture node specifically"""
    for node in nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            image_path = bpy.path.abspath(node.image.filepath)
            if '_Alb' in image_path:
                return image_path
    return None

def process_imported_fbx_after_delay(file_name):
    """Wait until FBX import finishes before processing meshes."""
    if bpy.context.selected_objects:
        for obj in bpy.context.selected_objects:
            if obj.type == 'ARMATURE':
                obj.scale = (1.0, 1.0, 1.0)
                obj.name = file_name
            elif obj.type == 'MESH':
                for mat_slot in obj.material_slots:
                    if mat_slot.material and mat_slot.material.use_nodes:
                        material_processor = MaterialProcessor(mat_slot.material)
                        
                        # Set initial metallic value to 0
                        material_processor.set_metallic_value(0.0)

                        # Unlink alpha
                        for link in material_processor.material.node_tree.links:
                            if link.to_node == material_processor.principled_node and link.to_socket.name == "Alpha":
                                material_processor.material.node_tree.links.remove(link)

                        image_path = find_albedo_texture(mat_slot.material.node_tree.nodes)
                        if image_path:
                            texture_dir = os.path.dirname(image_path)
                            base_name = os.path.basename(image_path).split('_Alb')[0]
                            material_processor.link_texture(texture_dir, base_name, "_Mtl", "Metallic", non_color=True)
                            material_processor.link_texture(texture_dir, base_name, "_Rgh", "Roughness", non_color=True)
                            material_processor.link_texture(texture_dir, base_name, "_Opa", "Alpha", non_color=True)
                            material_processor.link_texture(texture_dir, base_name, "_Nrm", "Normal", non_color=True, is_normal_map=True)
                        
        return None  # Stop the timer
    return 0.1  # Retry after 0.1 seconds

def menu_func_import(self, context):
    self.layout.operator(IMPORT_OT_splatoon_fbx.bl_idname, text="Splatoon FBX (.fbx)")

def register():
    bpy.utils.register_class(IMPORT_OT_splatoon_fbx)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_class(IMPORT_OT_splatoon_fbx)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()