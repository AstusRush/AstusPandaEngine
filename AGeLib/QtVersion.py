
global sUsePyQt5
sUsePyQt5 = True
try:
    import AGeLibQtVersion
    sUsePyQt5 = AGeLibQtVersion.sUsePyQt5
except:
    pass
def UsePyQt5():
    #print(sUsePyQt5)
    return sUsePyQt5