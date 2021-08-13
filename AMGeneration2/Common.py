import FreeCAD, FreeCADGui, Part, Mesh
import PySide, os.path
import FRDParser
import numpy as np
import copy


def checkGenerations():
    numGens = 0
    workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
    while os.path.isfile(workingDir + "/Gen" + str(numGens) + ".FCStd"):
        numGens += 1

    return numGens

def searchAnalysed():
    numAnalysed = 0
    statuses = []
    numGenerations = checkGenerations()
    workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
    for i in range(numGenerations):
        FRDPath = workingDir + "/Gen" + str(i) + "/SolverCcxTools/FEMMeshNetgen.frd"
        if os.path.isfile(FRDPath):
            try:
                # This returns an exception if analysis failed for this .frd file, because there is no results data
                FRDParser.FRDParser(FRDPath)
            except:
                status = "Failed"
            else:
                status = "Analysed"
                numAnalysed += 1
        else:
            status = "Not analysed"

        statuses.append(status)


    return (statuses, numAnalysed)

def writeAnalysisStatusToFile():
    workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])

    (statuses, numAnalysed) = searchAnalysed()
    filePath = workingDir + "/AnalysisStatus.txt"
    f = open(filePath, "w")
    f.write(str(numAnalysed) + "\n")
    [f.write(status+"\n") for status in statuses]
    print(statuses)
    f.close()

    return (statuses, numAnalysed)


def checkAnalyses():    # Reads AnalysisStatus.txt for results of analysis
    workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
    filePath = workingDir + "/AnalysisStatus.txt"
    try:
        f = open(filePath)
        text = f.read().split("\n")
        numAnalysed = int(text[0])
        statuses = text[1:]
    except FileNotFoundError:
        print("ERROR: AnalysisStatus.txt does not exist")
        statuses = []
        numAnalysed = 0
    except:
        print("An error occured while trying to read analysis results")
        statuses = []
        numAnalysed = 0

    return (statuses, numAnalysed)


def checkRefinements():     # Reads RefinementResults.txt for results of analysis
    workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
    filePath = workingDir + "/RefinementResults.txt"

    resolution = 0
    header = []
    results = []

    try:
        f = open(filePath)
        text = f.read().split("\n")
        resolution = float(text[0].split("=")[-1])
        header = text[1].split(",")
        for line in text[2:-1]:
            result = line.split(",")
            result = [float(cell) for cell in result]
            results.append(result)
    except FileNotFoundError:
        print("ERROR: RefinementResults.txt does not exist")
    except:
        print("An error occured while trying to read refinement results")

    return (resolution, header, results)


def checkGenParameters():
    workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
    filePath = workingDir + "/GeneratedParameters.txt"

    header = []
    parameters = []

    try:
        f = open(filePath)
        text = f.read().split("\n")
        header = text[0].split(",")
        for line in text[1:-1]:
            result = line.split(",")
            parameters.append(result)
    except FileNotFoundError:
        print("ERROR: GeneratedParameters.txt does not exist")
        header = [""]
        parameters = []
    except:
        print("An error occured while trying to read generation parameters")
        header = [""]
        parameters = []

    return (header, parameters)


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
            print("INFO: Generation " + str(i) + " analysis data not found")
        except:
            print("Error while trying to delete analysis folder for generation " + str(i))

    # Delete the GeneratedParameters.txt file
    try:
        os.remove(self.workingDir + "/GeneratedParameters.txt")
    except FileNotFoundError:
        print("INFO: GeneratedParameters.txt is missing")
    except:
        print("Error while trying to delete GeneratedParameters.txt")

    # Delete the AnalysisStatus.txt file
    try:
        os.remove(self.workingDir + "/AnalysisStatus.txt")
    except FileNotFoundError:
        print("INFO: AnalysisStatus.txt is missing")
    except:
        print("Error while trying to delete AnalysisStatus.txt")

    # Delete the RefinementResults.txt file
    try:
        os.remove(self.workingDir + "/RefinementResults.txt")
    except FileNotFoundError:
        print("INFO: RefinementResults.txt is missing")
    except:
        print("Error while trying to delete RefinementResults.txt")

    # Delete the FEAMetrics.npy file
    try:
        os.remove(self.workingDir + "/FEAMetrics.npy")
    except FileNotFoundError:
        print("INFO: FEAMetrics.npy is missing")
    except:
        print("Error while trying to delete FEAMetrics.npy")

def calcAndSaveFEAMetrics():
    workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
    numGenerations = checkGenerations()

    if numGenerations > 0:
        #table = [["Node Count", "Elem Count", "Max Stress", "Mean Stress", "Max Disp", "Mean Disp"]]
        table = [["Max Stress", "Mean Stress", "Max Disp", "Mean Disp"]]
        for i in range(numGenerations):
            filePath = workingDir + "/Gen" + str(i) + "/SolverCcxTools/FEMMeshNetgen.frd"

            r = calculateFEAMetric(filePath)
            #result = [r["NodeCount"], r["ElemCount"], r["MaxStress"], r["MeanStress"], r["MaxDisp"], r["MeanDisp"]]
            result = [r["MaxStress"], r["MeanStress"], r["MaxDisp"], r["MeanDisp"]]
            result = [str(r) for r in result]
            table.append(result)

        print("Table of results: ")
        print(table)

        # Save FEA metrics to .npy file
        np.save(workingDir + "/FEAMetrics.npy", np.array(table))



def calculateFEAMetric(FRDFilePath):
    result = None
    try:
        parser = FRDParser.FRDParser(FRDFilePath)

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
        return result


def generateColourScale(table, hue=0.5):
    width = len(table[0])
    height = len(table)
    colours = [[PySide.QtGui.QColor("white") for x in range(width)] for y in range(height)]

    for i in range(width):
        # Gather all the values in a column
        values = [table[y][i] for y in range(height)]

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

        # Calculate value range to calibrate colour scale
        valRange = maxVal - minVal

        for j, value in enumerate(values):
            try:
                # Normalise the value between 0-1 for the value range of that column
                normVal = (float(value) - minVal) / valRange

                col = hsvToRgb(hue, normVal, 1.0)
                col = [int(col[0]*255), int(col[1]*255), int(col[2]*255)]
                colours[j][i] = PySide.QtGui.QColor(col[0], col[1], col[2], 255)
            except ValueError:
                # Item was not a number. Likely a string because an error occured for analysis in this row
                # so colour it pink
                colours[j][i] = PySide.QtGui.QColor(230, 184, 184, 255)
                pass

    return colours


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


class GenTableModel(PySide.QtCore.QAbstractTableModel):
    def __init__(self, parent, itemList, header, colours=None, *args):
        PySide.QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.itemList = copy.deepcopy(itemList)
        self.header = header[:]
        height = len(itemList)
        width = len(header)
        defaultColour = PySide.QtGui.QColor("white")

        if colours == None:
            self.colours = [[defaultColour for x in range(width)] for y in range(height)]
        else:
            self.colours = colours[:]

        # Insert generation number column into table
        self.header.insert(0, "Gen")
        for i in range(height):
            self.itemList[i].insert(0, i)
            self.colours[i].insert(0, defaultColour)

        #print(self.itemList)
        #print(self.header)

    def updateColours(self, colours):
        for i, row in enumerate(colours):
            self.colours[i][1:] = row
        # self.dataChanged.emit()

    def updateData(self, table):
        for i, row in enumerate(table):
            self.itemList[i][1:] = row

    def updateHeader(self, header):
        self.header[1:] = header

    def rowCount(self, parent):
        return len(self.itemList)

    def columnCount(self, parent):
        return len(self.header)

    def data(self, index, role):
        if not index.isValid():
            return None
        elif role == PySide.QtCore.Qt.BackgroundRole:
            # Return colour
            return self.colours[index.row()][index.column()]
        elif role == PySide.QtCore.Qt.DisplayRole:
            return self.itemList[index.row()][index.column()]

    def headerData(self, col, orientation, role):
        if orientation == PySide.QtCore.Qt.Horizontal and role == PySide.QtCore.Qt.DisplayRole:
            return self.header[col]
        return None

    def sort(self, col, order):
        """sort table by given column number col"""
        self.emit(PySide.QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.itemList = sorted(self.itemList, key=operator.itemgetter(col))
        if order == PySide.QtCore.Qt.DescendingOrder:
            self.itemList.reverse()
        self.emit(PySide.QtCore.Qt.SIGNAL("layoutChanged()"))
        pass

