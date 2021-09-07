# AMGeneration
A FreeCAD module that uses Generative Design to design optimally for Additive Manufacturing.

This project was done as part of my Master's thesis. For more information, click [here](https://mightybucket.github.io/projects/2021/05/31/masters-dissertation.html).

## Installation instructions
This folder contains the code for a workbench plug-in for FreeCAD. Therefore you must have FreeCAD installed to use it.

FreeCAD 0.19 can be downloaded for free from https://www.freecadweb.org/

Once installed, you must manually copy the 'AMGeneration2' folder to the user 'Mod' directory for FreeCAD. On Windows, this is normally found in the following directory:

`C:\Users\*UserName*\AppData\Roaming\FreeCAD\Mod\`

Where `UserName` is replaced with the name of your user profile.

Once copied, start up FreeCAD. From the workbench selection drop down menu in the top middle of the window, you should see the option for "AM Generation v2". Selecting this will activate the workbench.

Not all of the functions will work out of the box. Some dependencies need to be installed first, which is detailed in the section below.

Have fun!

## Dependencies
The following Python packages need to be installed via `pip` for this module to work:
 - `simple-3dviz`
 - `wxPython`

FreeCAD has its own built in Python interpreter where these packages must be installed.

To do this, do the following:
1. Open up cmd
2. Go to Program Files/FreeCAD 0.19/bin/
3. Enter command `python -m pip install simple-3dviz`
4. Enter command `python -m pip install wxPython`

(C) Rahul Jhuree, 2021
