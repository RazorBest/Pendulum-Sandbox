from distutils.core import setup
import py2exe

setup(windows=['main.py'],
        options={
            'py2exe': {
                "dll_excludes": 
                ['api-ms-win-core-string-l1-1-0.dll',
                 'api-ms-win-core-psapi-l1-1-0.dll',
                 'api-ms-win-core-registry-l1-1-0.dll',
                 'api-ms-win-core-localization-l1-2-0.dll'
                 'libopenblas.TXA6YQSD3GCQQC22GEQ54J2UDCXDXHWN.gfortran-win_amd64.dll']
            }
        })