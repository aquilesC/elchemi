from pathlib import Path

home_folder = Path.home()
param_folder = home_folder/'.elchemi'

param_folder.mkdir(exist_ok=True)