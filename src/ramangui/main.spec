# -*- mode: python -*-
import sys
sys.setrecursionlimit(7000)


block_cipher = None


a = Analysis(['main.py'],
             pathex=['C:\\Users\\Philipp\\Documents\\HiWi\\interactive-raman-analysis-tool'],
             binaries=[],
             datas=[],
			 hiddenimports=['scipy._lib.messagestream'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='main',
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True )
