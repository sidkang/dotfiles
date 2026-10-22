c = get_config()

c.InteractiveShellApp.exec_lines = [
    """
try:
    from icecream import ic
except ImportError:
    print("Icecream not installed. Skipping.")
"""
]
c.InteractiveShellApp.extensions = []

c.TerminalInteractiveShell.shortcuts = [
    {"command": "IPython:auto_suggest.accept", "new_keys": ["c-y"], "create": True},
    {"command": "IPython:auto_suggest.accept_token", "new_keys": ["c-l"]},
    {"command": "IPython:auto_suggest.swap_autosuggestion_up", "new_keys": ["c-p"]},
    {"command": "IPython:auto_suggest.swap_autosuggestion_down", "new_keys": ["c-n"]},
]
