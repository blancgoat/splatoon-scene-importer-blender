
import os
import tempfile
import subprocess

class DAE_OT_import_via_fbx:
    
    @staticmethod
    def _find_fbx_converter():
        # FBX Converter의 일반적인 설치 경로들
        possible_paths = [
            "C:\\Program Files\\Autodesk\\FBX\\FBX Converter\\2013.3\\bin\\fbxconverter.exe",
            "C:\\Program Files (x86)\\Autodesk\\FBX\\FBX Converter\\2013.3\\bin\\fbxconverter.exe",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
                
        return None
    
    @staticmethod
    def convert(file_path):
        # FBX Converter 경로 찾기
        converter_path = DAE_OT_import_via_fbx._find_fbx_converter()
        if not converter_path:
            raise NotFoundConvertModule("FBX Converter not found. Please install Autodesk FBX Converter.")
            
        # 임시 FBX 파일을 위한 경로 생성
        with tempfile.NamedTemporaryFile(suffix='.fbx', delete=False) as temp_file:
            temp_fbx_path = temp_file.name
            
        
        # DAE를 FBX로 변환
        conversion_command = [
            converter_path,
            file_path,  # 입력 DAE 파일
            temp_fbx_path,  # 출력 FBX 파일
            "/v"            # verbose 출력
        ]
        
        process = subprocess.Popen(
            conversion_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise FailConvert(f'Conversion failed: {stderr.decode()}')
            
        return temp_fbx_path

class NotFoundConvertModule(Exception):
    pass

class FailConvert(Exception):
    pass