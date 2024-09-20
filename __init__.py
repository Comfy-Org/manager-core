import os
import sys

cli_mode_flag = os.path.join(os.path.dirname(__file__), '.enable-cli-only-mode')
is_pytest_running = 'pytest' in sys.modules

if os.path.exists(cli_mode_flag):
    print("\n[ComfyUI-Manager] !! cli-only-mode is enabled !!\n")
elif is_pytest_running:
    print("\n[ComfyUI-Manager] !! Running in pytest environment !!\n")
else:
    from .glob import manager_server
    WEB_DIRECTORY = "js"

NODE_CLASS_MAPPINGS = {}
__all__ = ['NODE_CLASS_MAPPINGS']



