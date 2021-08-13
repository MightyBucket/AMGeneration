import FreeCAD, FreeCADGui, Part, PySide
import os.path
import FRDParser, operator
import numpy as np
import random
import Common

class ResultsCommand():
    """Show results of analysed generations"""

    def GetResources(self):
        return {'Pixmap'  : 'Results.svg',  # the name of a svg file available in the resources
                'Accel' : "Shift+R",  # a default shortcut (optional)
                'MenuText': "Show Results",
                'ToolTip' : "Show results of analysed generations"}

    def Activated(self):
        panel = ResultsPanel()
        FreeCADGui.Control.showDialog(panel)
        """Do something here"""
        return

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        return True

class ResultsPanel:
    def __init__(self):
        # this will create a Qt widget from our ui file
        guiPath = FreeCAD.getUserAppDataDir() + "Mod/AMGeneration2/Results.ui"
        self.form = FreeCADGui.PySideUic.loadUi(guiPath)
        self.workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
        self.numGenerations = self.checkGenerations()

        # If FEAMetrics.npy doesn't exist, try to generate it from scratch
        filePath = self.workingDir + "/FEAMetrics.npy"
        if not os.path.isfile(filePath):
            print("Calculating metrics...")
            Common.calcAndSaveFEAMetrics()

        # Load metrics from file
        metrics = np.load(filePath)
        table = metrics.tolist()

        # Split into header and table data, then update table
        self.metricNames = table[0]
        self.metrics = table[1:]

        # Add configuration controls
        self.addConfigControls()

        self.updateResultsTable()


    def accept(self):
        FreeCADGui.Control.closeDialog()

    def checkGenerations(self):
        numGens = 0
        while os.path.isfile(self.workingDir + "/Gen" + str(numGens) + ".FCStd"):
            numGens += 1

        return numGens

    def updateResultsTable(self):
        header = self.metricNames
        items = self.metrics

        colours = self.generateColourScalesFromMetrics()
        self.tableModel = Common.GenTableModel(self.form, items, header, colours)
        self.form.resultsTable.setModel(self.tableModel)
        self.form.resultsTable.resizeColumnsToContents()

    def addConfigControls(self):
        self.configControls = []

        for name in self.metricNames:
            # Create instances of controls
            paramCheck = PySide.QtGui.QCheckBox(name, self.form)
            redGreenRadio = PySide.QtGui.QRadioButton(self.form)
            gradientRadio = PySide.QtGui.QRadioButton(self.form)
            radioGroup = PySide.QtGui.QButtonGroup()
            minBox = PySide.QtGui.QDoubleSpinBox(self.form)
            maxBox = PySide.QtGui.QDoubleSpinBox(self.form)

            # Configure control parameters
            paramCheck.setChecked(True)
            minBox.setMaximum(999999.99)
            maxBox.setMaximum(999999.99)
            gradientRadio.setChecked(True)
            radioGroup.addButton(redGreenRadio)
            radioGroup.addButton(gradientRadio)

            (minVal, maxVal) = self.getMetricValueRange(name)
            minBox.setValue(minVal)
            maxBox.setValue(maxVal)

            # Create and link callback functions
            def valueChanged(value):
                colours = self.generateColourScalesFromMetrics()
                self.updateResultsTableColours(colours)
                pass

            minBox.valueChanged.connect(valueChanged)
            maxBox.valueChanged.connect(valueChanged)

            controls = [paramCheck, redGreenRadio, gradientRadio, radioGroup, minBox, maxBox]
            self.configControls.append(controls)

            # Add widgets to form
            configGrid = self.form.configGrid
            numRows = configGrid.rowCount()
            configGrid.addWidget(paramCheck, numRows, 0)
            configGrid.addWidget(redGreenRadio, numRows, 1)
            configGrid.addWidget(gradientRadio, numRows, 2)
            configGrid.addWidget(minBox, numRows, 3)
            configGrid.addWidget(maxBox, numRows, 4)

    def updateResultsTableColours(self, colours):
        self.tableModel.updateColours(colours)
        #self.form.resultsTable.update()
        self.form.resultsTable.activated.emit(1)

    def getMetricValueRange(self, metricName):
        i = self.metricNames.index(metricName)
        height = len(self.metrics)
        # Gather all the values in a column
        values = [self.metrics[y][i] for y in range(height)]

        # Make new column of values that doesn't include numbers
        vals = []
        for item in values:
            try:
                vals.append(float(item))
            except ValueError:
                pass

        # Calculate value range
        minVal = min(vals)
        maxVal = max(vals)
        return (minVal, maxVal)

    def generateColourScalesFromMetrics(self):
        width = len(self.metricNames)
        height = len(self.metrics)
        colours = [[PySide.QtGui.QColor("white") for x in range(width)] for y in range(height)]

        items = self.metrics

        for i in range(width):
            # Gather all the values in a column
            values = [items[y][i] for y in range(height)]

            # Make new column of values that doesn't include numbers
            vals = []
            for item in values:
                try:
                    vals.append(float(item))
                except ValueError:
                    pass

            # Calculate value range
            minVal = self.configControls[i][4].value()
            maxVal = self.configControls[i][5].value()

            # Calculate value range to calibrate colour scale
            valRange = maxVal - minVal

            for j, value in enumerate(values):
                try:
                    value = float(value)
                    if value > maxVal:
                        # If value is greater than maximum, set it to full intensity
                        normVal = 1.0
                    else:
                        # Normalise the value between 0-1 for the value range of that column
                        normVal = (value - minVal) / valRange

                    hue = 0.4
                    col = hsvToRgb(hue, normVal, 1.0)
                    col = [int(col[0]*255), int(col[1]*255), int(col[2]*255)]
                    colours[j][i] = PySide.QtGui.QColor(col[0], col[1], col[2], 255)
                except ValueError:
                    # Item was not a number. Likely a string because an error occured for analysis in this row
                    # so colour it pink
                    colours[j][i] = PySide.QtGui.QColor(230, 184, 184, 255)
                    pass

        return colours


def readFRD(filepath):
    result = None
    try:
        parser = FRDParser.FRDParser(filepath)

        nodeCount = parser.frd.node_block.numnod
        elemCount = parser.frd.elem_block.numelem

        stresses = np.zeros((nodeCount, 4), dtype=np.float32)
        disp = np.zeros((nodeCount, 4), dtype=np.float32)
        error = np.zeros((nodeCount, 1), dtype=np.float32)
        for i in range(nodeCount):
            stresses[i, 0:3] = parser.get_results_node(i + 1, names="STRESS")[0][0:3]
            disp[i, 0:3] = parser.get_results_node(i + 1, names="DISP")[0][0:3]
            error[i] = parser.get_results_node(i + 1, names="ERROR")[0]

        # Calculate resultant stresses and displacements
        stresses[:, 3] = np.sqrt(np.square(stresses[:, 0]) + np.square(stresses[:, 1]) + np.square(stresses[:, 2]))
        disp[:, 3] = np.sqrt(np.square(disp[:, 0]) + np.square(disp[:, 1]) + np.square(disp[:, 2]))

        # Find max and mean for stress, displacement, and error
        resultantStress = stresses[:, 3]
        maxStress = round(max(resultantStress), 3)
        meanStress = round(np.mean(resultantStress), 3)

        resultantDisp = disp[:, 3]
        maxDisp = round(max(resultantDisp), 3)
        meanDisp = round(np.mean(resultantDisp), 3)

        maxError = round(max(error)[0], 1)
        meanError = round((np.mean(error)), 1)

        # Store results in dictionary to be returned by function
        result = {
            "NodeCount": nodeCount,
            "ElemCount": elemCount,
            "MaxStress": maxStress,
            "MeanStress": meanStress,
            "MaxDisp": maxDisp,
            "MeanDisp": meanDisp,
            "MaxError": maxError,
            "MeanError": meanError
        }
    except:
        print("Analysis failed on generation")
        result = {
            "NodeCount": None,
            "ElemCount": None,
            "MaxStress": None,
            "MeanStress": None,
            "MaxDisp":    None,
            "MeanDisp":   None,
            "MaxError":   None,
            "MeanError":  None
        }
    finally:
        return(result)

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


FreeCADGui.addCommand('Results', ResultsCommand())