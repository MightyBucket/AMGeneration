import FreeCADGui

class AMWorkbenchv2(Workbench):
    MenuText = "AM Generation v2"
    ToolTip = "Use generative design to optimise your part for Additive Manufacturing"
    Icon = FreeCAD.getUserAppDataDir() + "Mod/AMGeneration2/icon.svg"

    def Initialize(self):
        """This function is executed when FreeCAD starts"""
        #import MyModuleA, MyModuleB  # import here all the needed files that create your FreeCAD commands
        import Initiate, Generate, FEA, Results, Refine
        FreeCADGui.addIconPath(FreeCAD.getUserAppDataDir() + "Mod/AMGeneration2/")
        self.list = ["Initiate", "Generate", "FEA", "Refine", "Results"]  # A list of command names created in the line above
        self.appendToolbar("Commands", self.list)  # creates a new toolbar with your commands
        self.appendMenu("AM Generation v2", self.list)  # creates a new menu


    def Activated(self):
        """This function is executed when the workbench is activated"""
        return

    def Deactivated(self):
        """This function is executed when the workbench is deactivated"""
        return

    def ContextMenu(self, recipient):
        """This is executed whenever the user right-clicks on screen"""
        # "recipient" will be either "view" or "tree"
        self.appendContextMenu("My commands", self.list)  # add commands to the context menu

    def GetClassName(self):
        # This function is mandatory if this is a full python workbench
        # This is not a template, the returned string should be exactly "Gui::PythonWorkbench"
        return "Gui::PythonWorkbench"


Gui.addWorkbench(AMWorkbenchv2())