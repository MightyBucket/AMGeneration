import os.path
import os
import time

import Common
import FRDParser
import FreeCAD
import FreeCADGui
import Part
import PySide
import Voxelise
import numpy as np
import operator


class RefineCommand():
    """Refine generations for Additive Manufacturing"""

    def GetResources(self):
        return {'Pixmap'  : 'Refine.svg',  # the name of a svg file available in the resources
                'Accel' : "Shift+R",  # a default shortcut (optional)
                'MenuText': "Refine",
                'ToolTip' : "Refine generations for Additive Manufacturing"}

    def Activated(self):
        panel = RefinePanel()
        FreeCADGui.Control.showDialog(panel)
        return

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        return True

class RefinePanel:
    def __init__(self):
        # this will create a Qt widget from our ui file

        guiPath = FreeCAD.getUserAppDataDir() + "Mod/AMGeneration2/Refine.ui"
        self.form = FreeCADGui.PySideUic.loadUi(guiPath)
        self.workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
        self.selectedGen = -1
        self.numGenerations = Common.checkGenerations()
        (self.analysedStatuses, self.numAnalysed) = Common.checkAnalyses()

        self.voxelResolution = 1.00
        self.results = []
        self.voxels = []

        # Update the status labels
        self.form.genCountLabel.setText("There are " + str(self.numGenerations) + " generations")
        self.form.analysedCountLabel.setText(str(self.numAnalysed) + " generations analysed")

        # Link the callback functions
        self.form.resolutionSlider.sliderMoved.connect(self.sliderMoved)
        self.form.resolutionSpinBox.valueChanged.connect(self.spinBoxChanged)

        self.form.refineButton.clicked.connect(self.refineAllGens)
        self.form.deleteButton.clicked.connect(self.deleteAllRefinements)
        self.form.viewGenButton.clicked.connect(self.viewGeneration)

        # Load refinement results if they exist already
        self.updateResultsTable()
        (resolution, header, results) = Common.checkRefinements()
        numGens = len(results)
        self.resetViewControls(numGens)


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
                    self.statuses.append(["Failed"])
                else:
                    self.statuses.append(["Analysed"])
                    numAnalysed += 1
            else:
                self.statuses.append(["Not analysed"])

        return numAnalysed


    def updateResultsTable(self):
        (resolution, header, results) = Common.checkRefinements()
        colours = None

        # Chop off the voxel count columns as they are less relevant
        for i, title in enumerate(header):
            if title == "Part Voxel Count":
                header.pop(i)
                [line.pop(i) for line in results]
        for i, title in enumerate(header):
            if title == "Support Voxel Count":
                header.pop(i)
                [line.pop(i) for line in results]

        # Generate colour scales for table values
        if not len(header) == 0:
            colours = Common.generateColourScale(results, hue=0.5)

        tableModel = Common.GenTableModel(self.form, results, header, colours)
        self.form.tableView.setModel(tableModel)


    def refineAllGens(self):
        checkBuildVolume = self.form.buildVolumeCheck.isChecked()
        checkSupportStructure = self.form.supportStructureCheck.isChecked()

        for i in range(self.numGenerations):
            result = {}

            # Create /Gen# folder if it doesn't exist
            try:
                os.mkdir(self.workingDir + "/Gen" + str(i) + "/")
            except FileExistsError:
                # Folder already exists, so ignore
                pass
            except:
                print("Error while creating /Gen" + str(i) + "/ folder")

            # Voxelise .stl file for this generation
            stlPath = self.workingDir + "/Gen" + str(i) + ".stl"
            voxels = Voxelise.voxelisePart(stlPath, self.voxelResolution)

            # Save numpy array to file
            savePath = self.workingDir + "/Gen" + str(i) + "/voxelModel.npy"
            np.save(savePath, voxels)

            if checkBuildVolume:
                voxelCount = Voxelise.countPartVolume(voxels)
                volume = voxelCount / (self.voxelResolution ** 3)
                result['partVoxelCount'] = voxelCount
                result['partVolume'] = volume

            if checkSupportStructure:
                (supportVoxels, noOfPartVoxels, noOfSupportVoxels) = Voxelise.generateSupportMaterial(voxels)
                savePath = self.workingDir + "/Gen" + str(i) + "/supportModel.npy"
                np.save(savePath, supportVoxels)
                volume = noOfSupportVoxels / (self.voxelResolution ** 3)
                result['supportVoxelCount'] = noOfSupportVoxels
                result['supportVolume'] = volume
                result['supportRatio'] = noOfSupportVoxels/(noOfPartVoxels+noOfSupportVoxels)

            # Update progress bar
            progress = ((i + 1) / self.numGenerations) * 100
            self.form.progressBar.setValue(progress)

            self.results.append(result)

        ## Save results to file
        filePath = self.workingDir + "/RefinementResults.txt"
        f = open(filePath, 'w')
        f.write("resolution=" + str(self.voxelResolution) + "\n")

        # Write column headings
        header = ""
        if checkBuildVolume:
            header += "Part Voxel Count,"
            header += "Part Volume,"
        if checkSupportStructure:
            header += "Support Voxel Count,"
            header += "Support Volume,"
            header += "Support Ratio,"
        header = header[0:-1]       # Chop off the last comma at the end

        f.write(header + "\n")

        # Write rows of data
        for result in self.results:
            line = ""
            if checkBuildVolume:
                line += str(result['partVoxelCount']) + ","
                line += str(result['partVolume']) + ","
            if checkSupportStructure:
                line += str(result['supportVoxelCount']) + ","
                line += str(result['supportVolume']) + ","
                line += str(result['supportRatio']) + ","
            line = line[0:-1]
            f.write(line+"\n")

        f.close()

        self.updateResultsTable()
        self.resetViewControls(self.numGenerations)

    def saveRefinementStatsToFile(self):
        filePath = self.workingDir + "/RefinementResults.txt"
        pass

    def deleteAllRefinements(self):
        for i in range(self.numGenerations):
            try:
                # Delete part voxel model
                os.remove(self.workingDir + "/Gen" + str(i) + "/voxelModel.npy")
                # Delete support voxel model
                os.remove(self.workingDir + "/Gen" + str(i) + "/supportModel.npy")
            except FileNotFoundError:
                # Models were not generated in the first place, so ignore
                pass
            except:
                print("Error occured while deleting refinements")

        try:
            # Delete RefinementResults.txt
            os.remove(self.workingDir + "/RefinementResults.txt")
        except FileNotFoundError:
            pass
        except:
            print("Error while deleting RefinementResults.txt")

        self.updateResultsTable()

    def resetViewControls(self, numGens):
        comboBoxItems = []

        if numGens > 0:
            self.form.viewGenButton.setEnabled(True)
            self.form.selectGenBox.setEnabled(True)
            self.form.previousGen.setEnabled(True)
            self.form.nextGen.setEnabled(True)

            for i in range(numGens):
                comboBoxItems.append("Generation " + str(i))

            self.form.selectGenBox.clear()
            self.form.selectGenBox.addItems(comboBoxItems)
        else:
            self.form.viewGenButton.setEnabled(False)
            self.form.selectGenBox.setEnabled(False)
            self.form.previousGen.setEnabled(False)
            self.form.nextGen.setEnabled(False)
            self.form.selectGenBox.clear()

    # Callback signal function for viewing generation
    def viewGeneration(self):
        # Close the generation that the user might be viewing previously
        if self.selectedGen >= 0:
            # docName = "Gen" +str(self.selectedGen)
            # FreeCAD.closeDocument(docName)
            pass

        # Find which generation is selected in the combo box
        self.selectedGen = self.form.selectGenBox.currentText()
        self.selectedGen = int(str(self.selectedGen).split()[-1])

        # Open the part and support model for this generation
        filePath = self.workingDir + "/Gen" + str(self.selectedGen) + "/voxelModel.npy"
        partVoxels = np.load(filePath)
        filePath = self.workingDir + "/Gen" + str(self.selectedGen) + "/supportModel.npy"
        supportVoxels = np.load(filePath)
        self.voxels = partVoxels | supportVoxels

        # Colour in the part voxels orange, and the support voxels red
        orange = (0.95, 0.55, 0.0)
        red = (0.95, 0.05, 0.05)
        colours = np.empty(partVoxels.shape + (3,), dtype=np.float32)
        colours[partVoxels] = orange
        colours[supportVoxels] = red

        #voxels = np.ones((50,50,50), dtype=bool)
        #print(voxels)

        # Show the model
        Voxelise.viewVoxelModel(self.voxels, colours)

    # Callback signal function for resolution slider
    def sliderMoved(self, position):
        value = position / 100
        self.form.resolutionSpinBox.setValue(value)
        self.voxelResolution = value

    # Callback signal function for double spin box
    def spinBoxChanged(self, value):
        position = int(value*100)
        self.form.resolutionSlider.setValue(position)
        self.voxelResolution = value


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

FreeCADGui.addCommand('Refine', RefineCommand())