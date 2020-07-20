"""
Astus' General Library  \n
This library provides a prebuild QApplication (with standard options window (alt+O) and basic global shortcuts)
and custom windows (including custom frames and a space efficient notification display) for PyQt5 applications. \n
Use Main_App instead of QtWidgets.QApplication and AWWF instead of QtWidgets.QMainWindow. \n
For communication with the user and exception output use NC.
NC is AGeLib's standard notification class and is especially useful for exception handling as it can create a full bug report. \n
Import the exc submodule to access all exception handling functions. \n \n
In addition to this AGeLib also provides several advanced widgets to provide a sophisticated alterernative to the barebone Qt base widgets. \n
AGeMain.py includes a basic example with a main function and a test window. \n
For a more advanced example please visit https://github.com/AstusRush/AMaDiA .\n
AMaDiA was not only build to fully utilise most to all features of AGeLib but was also the origin of AGeLib: \n
As AMaDiA's basic application grew it became apparent that it should be turned into a separate Library: AGeLib
"""
import importlib
try: #CRITICAL: Make it easier to find import errors by printing the exceptions
    from AGeLib.AGeMain import *
except ModuleNotFoundError:
    from AGeMain import *
try: #CRITICAL: Make it easier to find import errors by printing the exceptions
    from AGeLib import exc
except ModuleNotFoundError:
    import exc
__version__ = Version
__all__ = ["Main_App",
           "AWWF",
           "App",
           "NC",
           "common_exceptions",
           "ExceptionOutput",
           "UsePyQt5",
           "MplWidget",
           "MplWidget_2D_Plot",
           "MplWidget_LaTeX",
           "ListWidget",
           "NotificationInfoWidget",
           "TextEdit",
           "LineEdit",
           "TableWidget",
           "TableWidget_Delegate",
           "TopBar_Widget",
           "MenuAction",
           "advancedMode",
           "AButton",
           "QuickSetup",
           "QuickWindow"
           ]

#def reloadAll():
#    importlib.reload(AGeMain)
#    importlib.reload(exc)
#    #import sys
#    ##if globals(  ).has_key('init_modules'):
#    ##    # second or subsequent run: remove all but initially loaded modules
#    ##    for m in sys.modules.keys(  ):
#    ##        if m not in init_modules:
#    ##            del(sys.modules[m])
#    ##else:
#    ##    # first run: find out which modules were initially loaded
#    ##    init_modules = sys.modules.keys(  )
#    #for module in sys.modules.values():
#    #    importlib.reload(module)

#V3: Things that need to be done in update 3.0.0
# Put the Mpl Widgets in their own submodule so that mpl is no longer a forced import for all programs
# Try to eliminate some imports to speed up start time
# Evaluate the names of all widgets
# Remove dead variables
# Change import to make reloadAll work
# Make compatible with PySide2
# Make Everything easier to find with autocomplete (for example by making everything begin with A) OR remove some A's in the beginning (like the one from AButton)!!!
#       The current state (especially AButton's A in the beginning) is a bit confusing
#