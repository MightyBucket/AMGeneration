import FreeCAD, FreeCADGui, Part, Mesh
import os.path
import shutil
from random import random
import PySide
import operator
import Common
import csv

class GenerateCommand():
    """Produce part generations"""

    def GetResources(self):
        return {'Pixmap'  : 'Generate.svg', # the name of a svg file available in the resources
                'Accel' : "Shift+G", # a default shortcut (optional)
                'MenuText': "Generate",
                'ToolTip' : "Produce part generations"}

    def Activated(self):
        panel = GeneratePanel()
        FreeCADGui.Control.showDialog(panel)
        """Do something here"""
        return

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        return True

class GeneratePanel():
    def __init__(self):
        # this will create a Qt widget from our ui file
        guiPath = FreeCAD.getUserAppDataDir() + "Mod/AMGeneration2/Generate.ui"
        self.form = FreeCADGui.PySideUic.loadUi(guiPath)
        self.workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])

        # Data variables for parameter table
        self.parameterNames = []
        self.parameterValues = []

        readyText = "Ready"

        # First check if generations have already been made from GeneratedParameters.txt
        (self.parameterNames, self.parameterValues) = Common.checkGenParameters()
        print(self.parameterNames)
        print(self.parameterValues)

        # Check if parameters.txt file has been made
        if os.path.isfile(self.workingDir + "/Parameters.txt"):
            # Read parameter names from Parameters.txt and store them
            f = open(self.workingDir + "/Parameters.txt")
            text = f.read()
            table = [line.split(",") for line in text.split("\n")]
            self.parameterNames = [line[0] for line in table]
            self.parameterNames = self.parameterNames[0:-1] # Remove the last name, it is always blank
        else:
            readyText = "Parameters not defined"

        ## Check if any generations have been made already, and up to what number
        numGens = self.checkGenerations()

        self.form.numGensLabel.setText(str(numGens) + " generations produced")
        self.form.readyLabel.setText(readyText)
        self.selectedGen = -1

        ## Connect the button procedures
        self.form.generateButton.clicked.connect(self.generateParts)
        self.form.viewGenButton.clicked.connect(self.viewGeneration)
        self.form.deleteGensButton.clicked.connect(self.deleteGenerations)

        self.updateParametersTable()

    def generateParts(self):
        numGenerations = self.form.NumGenerations.value()
        docPath = FreeCAD.ActiveDocument.FileName
        docName = FreeCAD.ActiveDocument.Name

        # Close the active document so that it doesn't interfere with the generation process
        FreeCAD.closeDocument(docName)

        for i in range(numGenerations):
            FreeCAD.open(docPath)
            FreeCAD.setActiveDocument(docName)

            # Produce part generation
            self.generate(i)

            FreeCAD.closeDocument(docName)

            # Update progress bar
            progress = ((i+1)/numGenerations) * 100
            self.form.progressBar.setValue(progress)

        # Reopen document again once finished
        FreeCAD.open(docPath)

        self.saveGenParamsToFile()
        self.updateParametersTable()

        # Update number of generations produced in window
        numGens = self.checkGenerations()
        self.form.numGensLabel.setText(str(numGens) + " generations produced")
        self.form.readyLabel.setText("Finished")

        print("Generation done successfully!")

    def deleteGenerations(self):
        numGens = self.checkGenerations()
        for i in range(numGens):
            fileName = self.workingDir + "/Gen" + str(i)
            # Delete FreeCAD part and STL files
            try:
                os.remove(fileName + ".FCStd")
                os.remove(fileName + ".stl")
            except FileNotFoundError:
                print("INFO: Generation " + str(i) + " not found")
            except:
                print("Error while trying to delete files for generation" + str(i))

            # Delete FreeCAD backup part files
            try:
                os.remove(fileName + ".FCStd1")
            except FileNotFoundError:
                pass
            except:
                print("Error while trying to delete backup part files for generation" + str(i))

            # Delete analysis directories
            try:
                shutil.rmtree(fileName + "/")
            except FileNotFoundError:
                #print("INFO: Generation " + str(i) + " analysis data not found")
                pass
            except:
                print("Error while trying to delete analysis folder for generation " + str(i))

        # Delete the GeneratedParameters.txt file
        try:
            os.remove(self.workingDir + "/GeneratedParameters.txt")
        except FileNotFoundError:
            #print("INFO: GeneratedParameters.txt is missing")
            pass
        except:
            print("Error while trying to delete GeneratedParameters.txt")

        # Delete the AnalysisStatus.txt file
        try:
            os.remove(self.workingDir + "/AnalysisStatus.txt")
        except FileNotFoundError:
            #print("INFO: AnalysisStatus.txt is missing")
            pass
        except:
            print("Error while trying to delete AnalysisStatus.txt")

        # Delete the RefinementResults.txt file
        try:
            os.remove(self.workingDir + "/RefinementResults.txt")
        except FileNotFoundError:
            #print("INFO: RefinementResults.txt is missing")
            pass
        except:
            print("Error while trying to delete RefinementResults.txt")

        # Delete the FEAMetrics.npy file
        try:
            os.remove(self.workingDir + "/FEAMetrics.npy")
        except FileNotFoundError:
            #print("INFO: FEAMetrics.npy is missing")
            pass
        except:
            print("Error while trying to delete FEAMetrics.npy")

        # self.updateParametersTable()
        #self.tableModel.updateHeader([])
        #self.tableModel.updateData([None])
        # Refresh the TableView control
        # self.form.parametersTable.clearSelection()
        #self.form.parametersTable.dataChanged.emit(self.index(0, 0), self.index(0, 0))

    def checkGenerations(self):
        numGens = 0
        while os.path.isfile(self.workingDir + "/Gen" + str(numGens) + ".FCStd"):
            numGens += 1

        self.resetViewControls(numGens)

        return numGens

    def saveGenParamsToFile(self):
        filePath = self.workingDir + "/GeneratedParameters.txt"
        with open(filePath, "w", newline='') as my_csv:
            csvWriter = csv.writer(my_csv, delimiter=',')
            csvWriter.writerow(self.parameterNames)
            csvWriter.writerows(self.parameterValues)


    def viewGeneration(self):
        # Close the generation that the user might be viewing previously
        if self.selectedGen >= 0:
            docName = "Gen" +str(self.selectedGen)
            FreeCAD.closeDocument(docName)

        # Find which generation is selected in the combo box
        self.selectedGen = self.form.selectGenBox.currentText()
        self.selectedGen = int(str(self.selectedGen).split()[-1])

        # Open the generation
        docPath = self.workingDir + "/Gen" + str(self.selectedGen) + ".FCStd"
        docName = "Gen" +str(self.selectedGen)
        FreeCAD.open(docPath)
        FreeCAD.setActiveDocument(docName)


    def resetViewControls(self, numGens):
        comboBoxItems = []

        if numGens > 0:
            self.form.viewGenButton.setEnabled(True)
            self.form.selectGenBox.setEnabled(True)

            for i in range(numGens):
                comboBoxItems.append("Generation " + str(i))

            self.form.selectGenBox.clear()
            self.form.selectGenBox.addItems(comboBoxItems)
        else:
            self.form.viewGenButton.setEnabled(False)
            self.form.selectGenBox.setEnabled(False)
            self.form.selectGenBox.clear()

    def updateParametersTable(self):
        self.tableModel = Common.GenTableModel(self.form, self.parameterValues, self.parameterNames)
        self.form.parametersTable.setModel(self.tableModel)
        #self.form.parametersTable.resizeColumnsToContents()

    def getStandardButtons(self, *args):
        #return PySide.QtWidgets.QDialogButtonBox.Ok
        #return QDialogButtonBox.Close | QDialogButtonBox.Ok
        pass

    def generate(self, genNumber):
        ## Read parameters from text file
        workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
        f = open(workingDir + "/Parameters.txt", "r")
        lines = f.read().split("\n")
        f.close()

        ## Save parameters into arrays
        paramNames = []
        mins = []
        maxs = []
        for line in lines:
            if line != "":
                # print(line)
                (name, min, max) = line.split(",")
                paramNames.append(name)
                mins.append(float(min))
                maxs.append(float(max))

        numParams = len(paramNames)
        #print("There are " + str(numParams) + " parameters")

        ## Find the constraint objects where each parameter is located
        objects = []
        indexes = []
        constraints = []
        for paramName in paramNames:
            paramFound = False
            for object in FreeCAD.ActiveDocument.Objects:
                if object.TypeId == "Sketcher::SketchObject":
                    for i, constraint in enumerate(object.Constraints):
                        if constraint.Name == paramName:
                            paramFound = True
                            constraints.append(constraint)
                            indexes.append(i)
                            objects.append(object)
                            break
                if paramFound:
                    break
            if not paramFound:
                print("ERROR: " + paramName + " parameter not found in document")

        self.parameterValues.append([])

        ## Generate new values for each parameter and assign them
        for i in range(numParams):
            # Generate value
            min = mins[i]
            max = maxs[i]
            valueRange = max - min
            newValue = min + random() * valueRange

            try:
                # Assign value to corresponding constraint object
                objects[i].setDatum(indexes[i], FreeCAD.Units.Quantity(newValue))
                self.parameterValues[-1].append(str(round(newValue, 2)))
            except:
                paramName = constraints[i].Name
                self.parameterValues[-1].append("N/A")
                print("ERROR: Modifying parameter '" + paramName + "' failed.")

        ## Regenerate the part and save generation as .stl and FreeCAD doc
        FreeCAD.ActiveDocument.recompute()

        ##  Save CAD part
        filename = "Gen" + str(genNumber)
        extension = ".FCStd"
        filePath = workingDir + "/" + filename + extension
        FreeCAD.ActiveDocument.saveAs(filePath)

        ## Save STL model
        filename = "Gen" + str(genNumber)
        extension = ".stl"
        filePath = workingDir + "/" + filename + extension
        objects = []
        objects.append(FreeCAD.ActiveDocument.getObject("Body"))
        Mesh.export(objects, filePath)


FreeCADGui.addCommand('Generate', GenerateCommand())