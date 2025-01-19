# Splatoon scene importer for Blender

### Before You Start

1. This addon is supported from Blender 4.0 and above.
2. You must have a .dae file extracted from Nintendo. You can easily find pre-parsed files at [models-resource.com](https://www.models-resource.com/nintendo_switch/splatoon3/).

**Optional**: If you want to directly import .dae into Blender, install Autodesk's FBX Converter (just the installation is required).  
[Autodesk FBX Converter](https://aps.autodesk.com/developer/overview/fbx-converter-archives).  
Once the installer installation is completed, this addon will utilize it.

### Usage

![Untitled-1](https://github.com/user-attachments/assets/4cfa49a6-12aa-40f4-b99f-b1299afea867)

1. Go to **Files -> Import -> Splatoon Scene** and select it.
    - You can use either the typical method shown in the picture or drag & drop.
  
![image](https://github.com/user-attachments/assets/27ae4414-c785-4eb2-90e5-bb7e029c0d2c)
2. Select the .dae or .fbx file, then import it.
   
![image](https://github.com/user-attachments/assets/83040060-85ab-47a9-baa9-6c208e7dce33)
That's it. Check the shader section to see if the desired shader is linked.  

The image above shows the result of importing with "Apply Second Shader" disabled, and subsequently organizing the nodes for a cleaner view.  
Please note that this addon doesn't specifically organize shaders other than the color menu selection!


### Additional Usage

1. Multiple imports are possible. Import multiple .dae or .fbx files at once.
2. You can set the scale of the armature during import. Normally it would be defined as 0.001 or 0.025.  
   The default value for this addon is 1.0.
3. You can add a second shader. Select "Apply Second Shader" during import.  
   It will try to import .trm, .thc as shader formats.  
   Unfortunately, we do not know a universal import method.  
   We are linking in a generally trouble-free manner based on body.  
   If you happen to know any universal shader application methods applicable in Blender 4, please let us know via issue!
