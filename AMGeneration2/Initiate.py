import FreeCAD, FreeCADGui, Part, Mesh
import PySide

class InitiateCommand():
    """Analyse the generated parts"""

    def GetResources(self):
        return {'Pixmap'  : 'Initiate.svg',  # the name of a svg file available in the resources
                'Accel' : "Shift+N",  # a default shortcut (optional)
                'MenuText': "Initiate",
                'ToolTip' : "Initialise the generation process"}

    def Activated(self):
        panel = InitiatePanel()
        FreeCADGui.Control.showDialog(panel)
        """Do something here"""
        return

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        return True

class InitiatePanel:
    def __init__(self):
        # this will create a Qt widget from our ui file
        guiPath = FreeCAD.getUserAppDataDir() + "Mod/AMGeneration2/Initiate.ui"
        self.form = FreeCADGui.PySideUic.loadUi(guiPath)

        self.extraParameterControls = []

        ## Attach functions to pushbuttons
        self.form.addParam.clicked.connect(self.addParameter)
        self.form.delParam.clicked.connect(self.delParameter)

        ## Search through all constraints in all objects for custom parameters
        self.paramNames = []
        self.values = []
        self.minVals = []
        self.maxVals = []

        for object in FreeCAD.ActiveDocument.Objects:
            if object.TypeId == "Sketcher::SketchObject":
                for constraint in object.Constraints:
                    if constraint.Name != "":
                        self.paramNames.append(constraint.Name)
                        self.values.append(constraint.Value)
                        self.minVals.append(constraint.Value)
                        self.maxVals.append(constraint.Value + 1)

        self.numParams = len(self.paramNames)
        self.form.paramsDetected.setText(str(self.numParams) + " parameters detected")

        ## Assign these values to the appropriate labels and boxes
        numberOfBoxes = 4 if self.numParams > 4 else self.numParams
        for i in range(numberOfBoxes):
            nameBox = getattr(self.form, "paramName"+str(i+1))
            valueLabel = getattr(self.form, "value"+str(i+1))
            minBox = getattr(self.form, "min"+str(i+1))
            maxBox = getattr(self.form, "max" + str(i + 1))

            nameBox.setText(self.paramNames[i])
            valueLabel.setText(str(round(self.values[i], 2)))
            minBox.setValue(self.minVals[i])
            maxBox.setValue(self.maxVals[i])

        # Add more parameter rows if more than 4 parameters were detected in the document
        numExtraParams = self.numParams - 4
        if numExtraParams > 0:
            for i in range(numExtraParams):
                self.addParameter()
                controls = self.extraParameterControls[-1]
                controls[0].setText(self.paramNames[i+4])
                controls[1].setText(str(round(self.values[i+4], 2)))
                controls[2].setValue(self.minVals[i+4])
                controls[3].setValue(self.maxVals[i+4])




    def accept(self):
        workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])

        parameters = []

        # Read parameters in first four rows
        for i in range(4):
            paramName = getattr(self.form, "paramName"+str(i+1)).text()
            min = getattr(self.form, "min"+str(i+1)).value()
            max = getattr(self.form, "max" + str(i+1)).value()

            if paramName == "":     # Parameter is blank, so don't add to list
                continue

            parameters.append([paramName, str(min), str(max)])

        # Read parameters in subsequent rows that may have been added
        numExtraParams = len(self.extraParameterControls)
        for controls in self.extraParameterControls:
            paramName = controls[0].text()
            min = controls[2].value()
            max = controls[3].value()

            if paramName == "":     # Parameter is blank, so don't add to list
                continue

            parameters.append([paramName, str(min), str(max)])

        # Write parameters to file
        f = open(workingDir + "/Parameters.txt", "w")
        f.writelines([line[0]+","+str(line[1])+","+str(line[2])+"\n" for line in parameters])
        f.close()

        numParams = len(parameters)
        print(str(numParams) + " written parameters to file")
        FreeCADGui.Control.closeDialog()

    def addParameter(self):

        # Instantiate widgets for new parameter row
        nameBox = PySide.QtGui.QLineEdit(self.form)
        valueLabel = PySide.QtGui.QLabel(self.form)
        valueLabel.setText("N/A")
        minBox = PySide.QtGui.QDoubleSpinBox(self.form)
        maxBox = PySide.QtGui.QDoubleSpinBox(self.form)
        minBox.setMinimum(-9999.99)
        minBox.setMinimum(-9999.99)
        minBox.setMaximum(9999.99)
        minBox.setMaximum(9999.99)

        controls = [nameBox, valueLabel, minBox, maxBox]
        self.extraParameterControls.append(controls)

        # Add widgets to form
        parameterGrid = self.form.parameterGrid
        numRows = parameterGrid.rowCount()
        parameterGrid.addWidget(nameBox, numRows, 0)
        parameterGrid.addWidget(valueLabel, numRows, 1)
        parameterGrid.addWidget(minBox, numRows, 2)
        parameterGrid.addWidget(maxBox, numRows, 3)

        pass

    def delParameter(self):
        controls = self.extraParameterControls[-1]
        parameterGrid = self.form.parameterGrid
        numRows = parameterGrid.rowCount()

        # Take out the widgets from the parameter grid
        parameterGrid.removeWidget(controls[0])
        parameterGrid.removeWidget(controls[1])
        parameterGrid.removeWidget(controls[2])
        parameterGrid.removeWidget(controls[3])

        # Delete the widgets
        controls[0].deleteLater()
        controls[1].deleteLater()
        controls[2].deleteLater()
        controls[3].deleteLater()

        # Remove their references from the list of extra controls
        self.extraParameterControls.pop()
        pass

FreeCADGui.addCommand('Initiate', InitiateCommand())