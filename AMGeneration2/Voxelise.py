import argparse
import os.path
import io
import xml.etree.cElementTree as ET
from zipfile import ZipFile
import zipfile

from PIL import Image
import numpy as np

import stltovoxel.slice as slice
import stltovoxel.stl_reader as stl_reader
import stltovoxel.perimeter as perimeter
from stltovoxel.util import arrayToWhiteGreyscalePixel, padVoxelArray

#from simple_3dviz import Mesh
#from simple_3dviz.window import show
#from simple_3dviz.utils import render


def meshToVoxel(inputFilePath, scaleFactor):
    mesh = list(stl_reader.read_stl_verticies(inputFilePath))
    (scale, shift, bounding_box) = slice.calculateScaleAndShift(mesh, scaleFactor)
    mesh = list(slice.scaleAndShiftMesh(mesh, scale, shift))
    #Note: vol should be addressed with vol[z][x][y]
    vol = np.zeros((bounding_box[2],bounding_box[0],bounding_box[1]), dtype=bool)
    for height in range(bounding_box[2]):
        #print('Processing layer %d/%d'%(height+1,bounding_box[2]))
        lines = slice.toIntersectingLines(mesh, height)
        prepixel = np.zeros((bounding_box[0], bounding_box[1]), dtype=bool)
        perimeter.linesToVoxels(lines, prepixel)
        vol[height] = prepixel
    vol, bounding_box = padVoxelArray(vol)
    return(vol)

def voxelisePart(fileName, resolution):
    voxels = meshToVoxel(fileName, resolution)
    voxels = np.swapaxes(voxels, 0, 2)
    voxels = np.flip(voxels, 1)

    return voxels

def countPartVolume(voxels):
    noOfPartVoxels = np.sum(voxels)
    return(noOfPartVoxels)

def generateSupportMaterial(voxels):
    # voxels: 3 dimensional boolean numpy array of part voxels
    (x_length, y_length, z_length) = voxels.shape
    supportVoxels = np.zeros(voxels.shape, dtype=bool)
    noOfPartVoxels = 0
    noOfSupportVoxels = 0
    for z in range(1, z_length):
        for y in range(y_length):
            for x in range(x_length):
                voxel = voxels[x, y, z]
                if voxel == True:  # If there is material at this voxel...
                    noOfPartVoxels += 1
                    support = False
                    # Check if there is support material at the voxels below and adjacent
                    if voxels[x, y, z - 1]:  # Just underneath?
                        support = True
                    if not y == 0:
                        if not x == 0:
                            if voxels[x - 1, y - 1, z - 1]:  # (-1, -1)
                                support = True
                        if not x == (y_length - 1):
                            if voxels[x + 1, y - 1, z - 1]:  # (-1, +1)
                                support = True
                        if voxels[x, y - 1, z - 1]:  # (-1, 0)
                            support = True

                    if not y == (x_length - 1):
                        if not x == 0:
                            if voxels[x - 1, y + 1, z - 1]:  # (+1, -1)
                                support = True
                        if not x == (y_length - 1):
                            if voxels[x + 1, y + 1, z - 1]:  # (+1, +1)
                                support = True
                        if voxels[x, y + 1, z - 1]:  # (+1, 0)
                            support = True

                    if not x == 0:
                        if voxels[x - 1, y, z - 1]:  # (0, -1)
                            support = True
                    if not x == (y_length - 1):
                        if voxels[x + 1, y, z - 1]:  # (0, +1)
                            support = True

                    # If support material wasn't found, build material underneath til the next material voxel is hit
                    if not support and z > 2:
                        zi = z
                        while (voxels[x, y, zi - 1] == False and zi > 1):
                            noOfSupportVoxels += 1
                            supportVoxels[x, y, zi - 1] = True
                            zi = zi - 1
                            pass
                        pass

    return((supportVoxels, noOfPartVoxels, noOfSupportVoxels))


def viewVoxelModel(voxels, colours=(0.95, 0.55, 0.0, 1.0)):
    (x_length, y_length, z_length) = voxels.shape
    boundingbox = [[-x_length / 200, -y_length / 200, -z_length / 200],
                   [x_length / 200, y_length / 200, z_length / 200]]
    #show(Mesh.from_voxel_grid(voxels=voxels, colors=colours, bbox=boundingbox), light=(-1, -1, 1))
    print("Viewing voxel models has been disabled due to an unsolved bug")