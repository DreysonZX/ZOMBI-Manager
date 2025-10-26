# ZOMBI-Manager
This is a python app that allows you to browse ZOMBI(U)'s files. Theres also a WIP importer that allows you to (hopefully) mod the game

If you need help on what .bfz's contain which. There is a text file in the main repository called 'WOR Descriptions' that contains the wor (bfz)'s name, and then what its path was when the game was being compiled (sourced from debug logs in the game off tcrf), this should allow you to make guesses

# Get started
To get started, you'll need python3 and some dependencies, here are the things my tool needs (I might've missed a few, been awhile)
PySide6 python-lzo

Next, simply just download the repo, go to the ZOMBIManager folder, and run the "zombiManager.py". It should open up a nice menu

# How to use
Go to file -> and import and select a .bfz file (they are located in your ZOMBI folder's Data folder)
It should load and you can sort through all the files
Selecting a file will show it on the right panel, currently it just shows the name, the HEX view + the string view
If its a .son (audio), it should allow you to play it back

Right clicking on the file on the left-side panel will allow you to export the file, exporting it raw will export the file as it is in the archive (if you want the raw .son files)
You can also export all the files of the .bfz to a folder

# Currently supported formats:
.son (Sound file, allows you to play it back in the Manager, and can export it as .wav)
