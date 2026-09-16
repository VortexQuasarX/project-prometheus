import os
import zipfile

def create_lambda_zip(source_dir, output_filename):
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                arcname = os.path.relpath(dir_path, source_dir).replace('\\', '/') + '/'
                zinfo = zipfile.ZipInfo(arcname)
                zinfo.external_attr = 0o040755 << 16  # drwxr-xr-x
                zf.writestr(zinfo, b'')
                
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir).replace('\\', '/')
                zinfo = zipfile.ZipInfo.from_file(file_path, arcname)
                
                if file == 'run.sh':
                    zinfo.external_attr = 0o100755 << 16  # -rwxr-xr-x
                else:
                    zinfo.external_attr = 0o100644 << 16  # -rw-r--r--
                    
                with open(file_path, 'rb') as f:
                    zf.writestr(zinfo, f.read())

if __name__ == '__main__':
    create_lambda_zip('.next/standalone', 'prometheus-web.zip')
