# ZOMBI-Manager
This is a python app that allows you to browse ZOMBI(U)'s files. Theres also a WIP importer that allows you to (hopefully) mod the game
If you need help on what .bfz's contain which. There is a text file in the main repository called 'WOR Descriptions' that contains the wor (bfz)'s name, and then what its path was when the game was being compiled (sourced from debug logs in the game off tcrf), this should allow you to make guesses

To get started, you'll need python3 and some dependencies, here are the things my tool needs (I might've missed a few, been awhile)
PySide6 python-lzo

Currently supported formats:
.son (Sound file, allows you to play it back in the Manager, and can export it as .wav)
