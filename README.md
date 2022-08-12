### TableTop Simulator Downloader

This is a (very) simple downloader for board games defined for TableTop Simulator.



## Running:
1- Open TTS and make sure it updates all your subscriptions

2- copy the .json files of the games you want to download to the same forlder as where the script is. For instance, to download the game 2827229184, you need to have downloades the 2827229184.json file and put it into your project folder.

3- Just run it as any other Python project:

python TTS_dumper.py "./2827229184.json"

Wait! If you see, at the end of the excecution, that there have been errors, excecute the code one or two more times. It is still fails, probably you will need to manually check the problem, usually consisting of a mising file on the server itself (it has happened).