# Splatoon scene importer for Blender

### Before You Start

1. This addon is supported from Blender 4.2 and above.
2. You must have a .dae file extracted from Nintendo Switch.
   - Use the **[Toolbox](https://github.com/KillzXGaming/Switch-Toolbox)**!

**Optional**: If you want to directly import .dae into Blender, install Autodesk's FBX Converter (just the installation is required).  
[Autodesk FBX Converter](https://aps.autodesk.com/developer/overview/fbx-converter-archives).  
Once the installer installation is completed, this addon will utilize it.

### Usage
1. Go to **Files -> Import -> Splatoon Scene** and select it.
   - ![image](https://github.com/user-attachments/assets/939d5ab8-db66-48c6-8443-fbd7214e97bb)
   - Or you can drag and drop. Whatever is comfortable for you!
     - .dae ![image](https://github.com/user-attachments/assets/d0c724dc-8a62-4c2e-b89c-ce66182e6894)
     - .fbx ![image](https://github.com/user-attachments/assets/93ab50c9-cdc2-48a6-bf44-c01c0154f238)

2. Select the .dae or .fbx file, then import it.
   - ![image](https://github.com/user-attachments/assets/ca6ca062-9841-4495-ae76-5fce7cb003b3)
   - ![image](https://github.com/user-attachments/assets/6bcc49bc-96bf-409a-9888-1e4c3ae6c4f7)

3. That's it. Check the shader section to see if the desired shader is linked.
    ![image](https://github.com/user-attachments/assets/8496e3f4-bded-475c-9765-f7688d1745d7)


### Additional Usage

1. Batch importing is supported. Try importing multiple files at the same time.
   - This is suitable when importing maps.
   - https://github.com/user-attachments/assets/5ed615bc-cfc4-4ac7-9b47-542d12d0f6d2
2. You can set the scale of the armature during import. Normally it would be defined as 0.001 or 0.025.
   - The default value for this addon is 1.0.
3. This add-on provides two methods for importing the second shader:
   - Mix Color Style: All color textures are mixed first → Converted to a single BSDF → Output
   - Mix Shader Style: Each color texture is converted to BSDF separately → Mix Shader → Output  
   Import using your preferred style!  
   If you don't want to import the second shader, you can uncheck "Apply Second Shader"
   - If you have your own shading method, feel free to share it through an issue submission!  
     I will review it and consider integrating it into the add-on if appropriate.


