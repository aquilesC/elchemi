from pathlib import Path

home_folder = Path.home()

param_folder = home_folder/'.LPL.Code.Elchemi.elchemi.OneDrives' #FIXME: This path is not elegant
buffer_folder = home_folder/'.LPL.Code.Elchemi.elchemi.Buffers'

param_folder.mkdir(exist_ok=True)
#FIXME: Why is teh buffer_folder not created as well?