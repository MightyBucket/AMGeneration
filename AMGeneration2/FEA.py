import FreeCAD, FreeCADGui, Part
import os.path
import FRDParser
import PySide, operator
import time
import Common


class FEACommand():
    """Perform FEA on generated parts"""

    def GetResources(self):
        return {'Pixmap'  : 'FEA.svg',  # the name of a svg file available in the resources
                'Accel' : "Shift+A",  # a default shortcut (optional)
                'MenuText': "FEA Generations",
                'ToolTip' : "Perform FEA on generated parts"}

    def Activated(self):
        panel = FEAPanel()
        FreeCADGui.Control.showDialog(panel)
        return

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        return True

class FEAPanel:
    def __init__(self):
        # this will create a Qt widget from our ui file

        guiPath = FreeCAD.getUserAppDataDir() + "Mod/AMGeneration2/PerformFEA.ui"
        self.form = FreeCADGui.PySideUic.loadUi(guiPath)
        self.workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
        self.numGenerations = self.checkGenerations()
        (self.stats, self.numAnalysed) = Common.checkAnalyses()

        # Update status labels and table
        self.form.genCountLabel.setText("There are " + str(self.numGenerations) + " generations")
        self.form.analysedCountLabel.setText(str(self.numAnalysed) + " successful analyses")
        self.updateAnalysisTable()

        # Link callback procedures
        self.form.startFEAButton.clicked.connect(self.FEAGenerations)
        self.form.finenessBox.activated.connect(self.finenessChanged)

    def accept(self):
        pass

    def checkGenerations(self):
        numGens = 0
        while os.path.isfile(self.workingDir + "/Gen" + str(numGens) + ".FCStd"):
            numGens += 1

        return numGens

    def checkAnalyses(self):
        numAnalysed = 0
        for i in range(self.numGenerations):
            FRDPath = self.workingDir + "/Gen" + str(i) + "/SolverCcxTools/FEMMeshNetgen.frd"
            if os.path.isfile(FRDPath):
                try:
                    # This returns an exception if analysis failed for this .frd file, because there is no results data
                    FRDParser.FRDParser(FRDPath)
                except:
                    self.stats.append(["Failed"])
                else:
                    self.stats.append(["Analysed"])
                    numAnalysed += 1
            else:
                self.stats.append(["Not analysed"])

        return(numAnalysed)

    def FEAGenerations(self):
        print("Started analysis")

        # Get FEA parameters from controls
        fineness = self.form.finenessBox.currentText()
        growthRate = self.form.growthRateBox.value()
        segsPerEdge = self.form.segsPerEdgeBox.value()
        segsPerRadius = self.form.segsPerRadiusBox.value()

        for i in range(self.numGenerations):
            # Open generated part
            partName = "Gen" + str(i)
            filePath = self.workingDir + "/" + partName + ".FCStd"
            FreeCAD.open(filePath)
            FreeCAD.setActiveDocument(partName)

            # Run FEA solver on generation
            performFEA(fineness, growthRate, segsPerEdge, segsPerRadius)

            # Close generated part
            FreeCAD.closeDocument(partName)

            # Update progress bar
            progress = ((i+1)/self.numGenerations) * 100
            self.form.progressBar.setValue(progress)

        (self.stats, self.numAnalysed) = Common.writeAnalysisStatusToFile()

        self.updateAnalysisTable()

    def finenessChanged(self, value):
        fineness = self.form.finenessBox.currentText()
        if fineness == "UserDefined":
            self.form.growthRateBox.setEnabled(True)
            self.form.segsPerEdgeBox.setEnabled(True)
            self.form.segsPerRadiusBox.setEnabled(True)
        else:
            self.form.growthRateBox.setEnabled(False)
            self.form.segsPerEdgeBox.setEnabled(False)
            self.form.segsPerRadiusBox.setEnabled(False)


    def updateAnalysisTable(self):
        # Make a header and table with one more column, because otherwise the table object will split each character
        # into its own cell
        header = ["Status", ""]
        table = []
        for i in range(len(self.stats)):
            table.append([self.stats[i], ""])

        colours = []
        for status in self.stats:
            white = PySide.QtGui.QColor("white")
            colour = white
            if status == "Analysed":
                # green
                colour = PySide.QtGui.QColor(114, 242, 73, 255)
            elif status == "Not analysed":
                # yellow
                colour = PySide.QtGui.QColor(207, 184, 12, 255)
            elif status == "Failed":
                # red/pink
                colour = PySide.QtGui.QColor(250, 100, 100, 255)
            colours.append([colour, white])

        tableModel = Common.GenTableModel(self.form, table, header, colours=colours)
        self.form.tableView.setModel(tableModel)


def performFEA(fineness, growthRate, segsPerEdge, segsPerRadius):
    # Get document handle to part that was just generated
    doc = FreeCAD.ActiveDocument

    analysis_object = doc.Analysis

    # generate mesh
    mesh = doc.addObject('Fem::FemMeshShapeNetgenObject', 'FEMMeshNetgen')
    mesh.Shape = doc.Body
    mesh.MaxSize = 1000
    mesh.Optimize = True
    mesh.SecondOrder = True
    # set meshing parameters from function inputs
    if fineness == "UserDefined":
        mesh.GrowthRate = growthRate
        mesh.NbSegsPerEdge = segsPerEdge
        mesh.NbSegsPerRadius = segsPerRadius

    mesh.Fineness = fineness
    doc.recompute()

    analysis_object.addObject(mesh)

    # recompute
    doc.recompute()

    # run the analysis step by step
    from femtools import ccxtools
    fea = ccxtools.FemToolsCcx()
    fea.update_objects()
    fea.setup_working_dir()
    fea.setup_ccx()
    message = fea.check_prerequisites()
    if not message:
        fea.purge_results()
        fea.write_inp_file()
        # on error at inp file writing, the inp file path "" was returned (even if the file was written)
        # if we would write the inp file anyway, we need to again set it manually
        # fea.inp_file_name = '/tmp/FEMWB/FEMMeshGmsh.inp'
        fea.ccx_run()
        fea.load_results()
    else:
        FreeCAD.Console.PrintError("Houston, we have a problem! {}\n".format(message))  # in report view
        print("Houston, we have a problem! {}\n".format(message))  # in python console

    # save FEA results
    doc.save()

def hsvToRgb(h, s, v):
    if s == 0.0:
        return v, v, v
    i =int(h * 6.0)  # XXX assume int() truncates!
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = i % 6
    if i == 0:
        return v, t, p
    if i == 1:
        return q, v, p
    if i == 2:
        return p, v, t
    if i == 3:
        return p, q, v
    if i == 4:
        return t, p, v
    if i == 5:
        return v, p, q

FreeCADGui.addCommand('FEA', FEACommand())