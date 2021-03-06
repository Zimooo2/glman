#!/usr/bin/env python

import sys
import math
import os

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

# the following should not be happening and is some kind of scoping issue
# TODO: only import the shapes library once
# this is so we can call the functions
from shapes import *
# this is so we can scan the functions
import shapes

# an inspecting function that will allow us to get all functions in a file
# as a list
import inspect

import OpenGL.GL as gl

# generate and show a popup error message box
def generateErrorMessage(label, text, moreDetails=""):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setText("Error: " + text)
    msg.setStyleSheet("QLabel { }")
    msg.setWindowTitle(label)
    # if we have more details to show
    if moreDetails != "":
        msg.setDetailedText(moreDetails)
    msg.exec_()

def makeSliderLabel(text):
    slider = QLabel()
    # set our name
    slider.setText(text)
    # make the text white and center it on the menu
    slider.setStyleSheet("QLabel { qproperty-alignment: AlignCenter; }")
    return slider

def denormalizeSliderRange(min, value, max):
    range = max - min
    step = range / 100.0
    return value * step

def normalizeSliderRange(min, value, max):
    range = max - min
    step = range / 100.0
    mult = 1 / step
    normalMin = int(math.floor(min * mult))
    normalMax = int(math.floor(max * mult))
    normalValue = int(math.floor(value * mult))
    return (normalMin, normalValue, normalMax)

# returns a list of lines, each line split by white space into a list
def parseGLIB(glibFile):
    # read our glib file
    with open(glibFile) as f:
        glibContents = f.readlines()
    # trim whitespace off the ends of strings
    glibContents = [x.strip() for x in glibContents]
    # split each argument by whitespace
    glibContents = [x.split() for x in glibContents]
    # remove all empty lines
    glibContents = [x for x in glibContents if x != []]
    return glibContents

def parseUniformVariables(glibContents):
    # a list of all our programs
    programs = []
    # the current program number we are on
    programNumber = 0
    # a flag to let us know if we are currently in a program scope (aka. between brackets)
    inProgram = False

    for line in glibContents:
        # if we find an open bracket at the begining of a line, throw an error
        if line[0] == "{":
            print("""
                Error: Unexpected open bracket.
                Please place your opening brackets at the end of your program line""")
            exit(1)

        # if we got to a program
        if line[0].lower() == "program":
            programs.append({})
            # get our program name
            programs[programNumber]["name"] = line[1]
            programs[programNumber]["variables"] = []
            # if the user opened up a scope, that means they are going to have
            # uniform variables that we are going to use in our program
            if line[2] == "{":
                inProgram = True
                # move on to the next line
                continue

        if line[0] == "}":
            inProgram = False
            programNumber += 1

        if inProgram:
            # store the name, min default and max values
            programs[programNumber]["variables"].append({
                "name": line[0],
                # remove the opening <
                "min": float(line[1][1:]),
                "value": float(line[2]),
                # remove the closing >
                "max": float(line[3][:-1])
            })
    return programs


class Window(QWidget):

    def __init__(self):
        super(Window, self).__init__()

        self.glWidget = MakeGLWidget()

        # create our horizontal main layout
        self.mainLayout = QHBoxLayout()
        self.mainLayout.addWidget(self.glWidget)

        # expand the glWidget to fill all available space
        self.glWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # this is a container that will hold all our uniform variable sliders
        self.uniformVariableSliders = QVBoxLayout()

        # this is where we will hold all our control systems
        self.controlBar = self.makeControlBar()

        # add the vertical layout
        self.mainLayout.addLayout(self.controlBar)

        # set our main layout for the window
        self.setLayout(self.mainLayout)

        self.setWindowTitle("glman")

    def makeControlBar(self):
        # create each slider
        self.xSlider = self.createSlider(0, 360 * 16)
        self.ySlider = self.createSlider(0, 360 * 16)
        self.zSlider = self.createSlider(0, 360 * 16)
        self.zoomSlider= self.createSlider(1, 500)

        self.xLabel = makeSliderLabel('x')
        self.yLabel = makeSliderLabel('y')
        self.zLabel = makeSliderLabel('z')
        self.zoomLabel = makeSliderLabel('zoom')

        # the connect function takes in a single value, which is the new value
        # of the slider when it is changed.
        # use a lambda function to connect set the rotation on the axis and
        # send in the new value to be used for that element
        self.xSlider.valueChanged.connect( lambda newValue: self.glWidget.setRotation('x', newValue))
        self.glWidget.xRotationChanged.connect(self.xSlider.setValue)
        self.ySlider.valueChanged.connect( lambda newValue: self.glWidget.setRotation('y', newValue))
        self.glWidget.yRotationChanged.connect(self.ySlider.setValue)
        self.zSlider.valueChanged.connect( lambda newValue: self.glWidget.setRotation('z', newValue))
        self.glWidget.zRotationChanged.connect(self.zSlider.setValue)

        # connect the zoom slider to the variable that goes into the glScale function
        self.zoomSlider.valueChanged.connect(self.glWidget.changeZoom)
        self.glWidget.zoomChanged.connect(self.zoomSlider.setValue)

        # set the value of the slider now that they are linked
        self.xSlider.setValue(23  * 16)
        self.ySlider.setValue(315 * 16)
        self.zSlider.setValue(1   * 16)

        # add in a vertical layout for all our controls
        controlBar = QVBoxLayout()

        # a horizontal layout for some check boxes
        checkBoxes = QHBoxLayout()

        # create an axis box and connect a state changed listener to the glWidget
        self.axisCheckbox = self.makeCheckBox("Axes")
        self.axisCheckbox.setCheckState(Qt.Checked)
        self.axisCheckbox.stateChanged.connect(self.glWidget.toggleAxes)

        checkBoxes.addWidget(self.axisCheckbox)
        # checkBoxes.addWidget(self.makeCheckBox("Orthographic"))
        controlBar.addLayout(checkBoxes)

        loadGlibButton = QPushButton("Load GLIB File")
        loadGlibButton.clicked.connect(self.getGLIB)

        reloadGlibButton = QPushButton("Reload GLIB File")
        reloadGlibButton.clicked.connect(self.glWidget.loadGLIB)

        controlBar.addWidget(loadGlibButton)
        controlBar.addWidget(reloadGlibButton)
        controlBar.addWidget(self.xLabel)
        controlBar.addWidget(self.xSlider)
        controlBar.addWidget(self.yLabel)
        controlBar.addWidget(self.ySlider)
        controlBar.addWidget(self.zLabel)
        controlBar.addWidget(self.zSlider)
        controlBar.addWidget(self.zoomLabel)
        controlBar.addWidget(self.zoomSlider)
        return controlBar

    # remove all child elements from the layout
    def clearLayout(self, layout):
        # remove them in reverse order so that it does not shift the contents
        # around while they are being removed
        for i in reversed(range(layout.count())):
            # when you set the parent to None, the cleaner automatically removes
            # the widget
            layout.itemAt(i).widget().setParent(None)

        return layout

    def addSliders(self, programs):
        variableSliders = []
        sliderLabels = []

        programNumber = 0

        self.uniformVariableSliders = self.clearLayout(self.uniformVariableSliders)

        # for every program we have
        for program in programs:
            for key, value in program.items():
                # if we see variables
                if key == "variables":
                    for variable in value:
                        # convert the floats to an integer range
                        sliderRange = normalizeSliderRange(variable["min"], variable["value"], variable["max"])
                        # make a slider with a min and max value
                        slider = self.createSlider(sliderRange[0], sliderRange[2])
                        # set the slider to the default variable
                        slider.setValue(sliderRange[1])
                        # make a label for our slider
                        label = makeSliderLabel(variable["name"])

                        # define the program and variable names as variables
                        variableName = variable["name"]
                        # this is a tricky line, so it is in the readme
                        slider.valueChanged.connect( lambda newValue, programNumber=programNumber, variableName=variableName: self.glWidget.setUniformVariable(programNumber, variableName, newValue) )
                        # add the label and slider to their respective arrays
                        sliderLabels.append(label)
                        variableSliders.append(slider)
            programNumber += 1

        # just in case we have an uneven number of sliders and labels
        if len(variableSliders) != len(sliderLabels):
            print("Error: the number of sliders and labels do not match")
            exit(1)

        # only add in our uniform variable sliders if a program exists
        if programNumber > 0:
            self.controlBar.addLayout(self.uniformVariableSliders)

        # for every slider and label
        for x in range(0,len(variableSliders)):
            self.uniformVariableSliders.addWidget(sliderLabels[x])
            self.uniformVariableSliders.addWidget(variableSliders[x])

    def makeCheckBox(self, label):
        checkBox = QCheckBox(label)
        # make the text white
        checkBox.setStyleSheet("""
            QCheckBox {
               border: none;
            }""")
        return checkBox

    def createSlider(self, start, end):
        slider = QSlider(Qt.Horizontal)
        slider.setRange(start, end)
        return slider

    def getGLIB(self):
        # prompt the user for the file location
        dialog = QFileDialog()
        # it returns a tuple with the path and the filter type
        self.glibFile = dialog.getOpenFileName()[0]
        # if the user did not cancel the file selection
        if (self.glibFile != ''):
            self.glibContents = parseGLIB(self.glibFile)
            self.addSliders(parseUniformVariables(self.glibContents))

            # now that we have the glib location, load it in
            self.glWidget.setGLIB(self.glibFile)
            self.glWidget.loadGLIB()

class MakeGLWidget(QOpenGLWidget):
    # these are signals that are emitted to make connections
    xRotationChanged = pyqtSignal(int)
    yRotationChanged = pyqtSignal(int)
    zRotationChanged = pyqtSignal(int)
    zoomChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super(MakeGLWidget, self).__init__(parent)

        self.axis = 0

        self.rotation = {
            "x": 0,
            "y": 0,
            "z": 0
        }
        self.uniformVariables = {}

        self.axisOn = 2

        self.programOn = False

        self.lastPos = QPoint()

        self.workingDirectory = ""
        self.glibFile = ""
        self.glibContents = ""

        self.scale = 1

        # get all functions in the shapes module
        self.availableShapes = inspect.getmembers(shapes, inspect.isfunction)
        self.availableShapes = [i[0] for i in self.availableShapes]

        self.backgroundColor = QColor.fromCmykF(0.0, 0.0, 0.0, 1.0)

    def getOpenglInfo(self):
        info = """
            Vendor: {0}
            Renderer: {1}
            OpenGL Version: {2}
            Shader Version: {3}
        """.format(
            gl.glGetString(gl.GL_VENDOR),
            gl.glGetString(gl.GL_RENDERER),
            gl.glGetString(gl.GL_VERSION),
            gl.glGetString(gl.GL_SHADING_LANGUAGE_VERSION)
        )

        return info

    def minimumSizeHint(self):
        return QSize(150, 150)

    def sizeHint(self):
        return QSize(4000, 4000)

    def toggleAxes(self, value):
        self.axisOn = value
        self.update()

    def glibCommandToFunction(self, command):
        # get the function name
        function = command[0].lower() + "("
        # start at the first argument and add in all the arguments that
        # have a comma after them
        for x in range(1,len(command) - 1):
            function += command[x]
            function += ","
        # add in the last argument with a closing parenthisis
        function += command[-1] + ")"
        return function

    def setGLIB(self, glibFile):
        self.glibFile = glibFile
        # get the directory that the glib file comes from so we can look for shaders
        self.workingDirectory = os.path.dirname(self.glibFile)
        self.glibContents = parseGLIB(glibFile)

    def loadGLIB(self):
        # to keep track of whether we have a missing file
        missingShader = False

        # for every line in our glib file
        for line in self.glibContents:
            # if the line starts with the keyword Vertex, we will be loading a
            # vertex file
            if line[0].lower() == 'vertex':
                # add the absolute path, and the file name
                self.vertexFile = self.workingDirectory + '/' + line[1] + '.vert'
                print("Looking for", self.vertexFile)

                # if the file exists
                if os.path.isfile(self.vertexFile):
                    print("Found", self.vertexFile)
                    self.vertOn = True
                else:
                    missingShader = True
                    generateErrorMessage("Missing Shader", "Could not find your vertex shader file. Aborting loading the files")

            if line[0].lower() == 'fragment':
                self.fragmentFile = self.workingDirectory + '/' + line[1] + '.frag'
                print("Looking for", self.fragmentFile)
                if os.path.isfile(self.fragmentFile):
                    print("Found", self.fragmentFile)
                    self.fragOn = True
                else:
                    missingShader = True
                    generateErrorMessage("Missing Shader", "Could not find your fragment shader file. Aborting loading the files")

        self.uniformVariables = parseUniformVariables(self.glibContents)

        # if we are not missing a shader, turn on the shader program
        if not missingShader:
            self.programOn = True

        self.update()

    def setUniformVariable(self, program, variableName, value):
        for variable in self.uniformVariables[program]["variables"]:
            if variable["name"] == variableName:
                variable["value"] = value;
        self.update()

    def changeZoom(self, value):
        self.scale = value / 100.0
        self.zoomChanged.emit(value)
        self.update()

    def setRotation(self, axis, angle):
        angle = self.normalizeAngle(angle)
        if angle != self.rotation[axis]:
            self.rotation[axis] = angle
            if axis == 'x':
                self.xRotationChanged.emit(angle)
            elif axis == 'y':
                self.yRotationChanged.emit(angle)
            elif axis == 'z':
                self.zRotationChanged.emit(angle)
            self.update()

    # initialize the GL context. This is only called once on setup
    def initializeGL(self):
        # print the information that the operating system can support
        print(self.getOpenglInfo())

        # set the background to a dark grey
        self.setClearColor(self.backgroundColor.darker())

        # create an arrows object (call list)
        self.axis = self.Arrow()

        gl.glShadeModel(gl.GL_SMOOTH)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_CULL_FACE)

    # evaluate a shape written in the glib file
    def evaluateShape(self, command):
        # get the name of the shape (function) from the glib file
        function = self.glibCommandToFunction(command)
        # call the function associated with the name
        gl.glCallList(eval(function))

    def evaluateCommand(self, command):
        # if the shape we got is in the list of available shapes
        if command[0] in self.availableShapes:
            # call the command associated with that shape
            self.evaluateShape(command)

    def createProgram(self, shaderList):
        program = gl.glCreateProgram()

        for shader in shaderList:
            gl.glAttachShader(program, shader)

        gl.glLinkProgram(program)

        status = gl.glGetProgramiv(program, gl.GL_LINK_STATUS)
        if status == gl.GL_FALSE:
            # Note that getting the error log is much simpler in Python than in C/C++
            # and does not require explicit handling of the string buffer
            strInfoLog = gl.glGetProgramInfoLog(program)
            print("Linker failure: \n" + strInfoLog)

        for shader in shaderList:
            gl.glDetachShader(program, shader)

        return program

    def loadShader(self, shaderType, shaderFile):
        if os.path.isfile(shaderFile):
            with open(shaderFile, 'r') as f:
                shaderData = f.read()
        else:
            # this should have been taken care of already, but this is here just
            # incase
            raise IOError("Could not find shader file")

        shader = gl.glCreateShader(shaderType)
        gl.glShaderSource(shader, shaderData) # note that this is a simpler function call than in C

        # This shader compilation is more explicit than the one used in
        # framework.cpp, which relies on a glutil wrapper function.
        # This is made explicit here mainly to decrease dependence on pyOpenGL
        # utilities and wrappers, which docs caution may change in future versions.
        gl.glCompileShader(shader)

        status = gl.glGetShaderiv(shader, gl.GL_COMPILE_STATUS)
        if status == gl.GL_FALSE:
            # Note that getting the error log is much simpler in Python than in C/C++
            # and does not require explicit handling of the string buffer
            strShaderType = ""
            if shaderType is gl.GL_VERTEX_SHADER:
                strShaderType = "vertex"
            elif shaderType is gl.GL_GEOMETRY_SHADER:
                strShaderType = "geometry"
            elif shaderType is gl.GL_FRAGMENT_SHADER:
                strShaderType = "fragment"

            print("Compilation failure for " + strShaderType + " shader:\n")

        return shader

    # this function runs every time something on the GL window changes
    def paintGL(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glLoadIdentity()

        # if we never loaded in a glib file
        if not self.programOn:
            gl.glTranslated(0.0, 0.0, -10.0)
            # set the rotations
            gl.glRotated(self.rotation['x'] / 16.0, 1.0, 0.0, 0.0)
            gl.glRotated(self.rotation['y'] / 16.0, 0.0, 1.0, 0.0)
            gl.glRotated(self.rotation['z'] / 16.0, 0.0, 0.0, 1.0)
            gl.glScalef(self.scale, self.scale, self.scale)

            # if the box is checked
            if (self.axisOn == 2):
                # add in our axis
                gl.glCallList(self.axis)
        else:
            # don't use a shader program while we draw the axes
            gl.glUseProgram(0)

            shaderList = []
            shaderList.append(self.loadShader(gl.GL_VERTEX_SHADER, self.vertexFile))
            shaderList.append(self.loadShader(gl.GL_FRAGMENT_SHADER, self.fragmentFile))
            program = self.createProgram(shaderList)
            for shader in shaderList:
                gl.glDeleteShader(shader)

            gl.glTranslated(0.0, 0.0, -10.0)
            gl.glRotated(self.rotation['x'] / 16.0, 1.0, 0.0, 0.0)
            gl.glRotated(self.rotation['y'] / 16.0, 0.0, 1.0, 0.0)
            gl.glRotated(self.rotation['z'] / 16.0, 0.0, 0.0, 1.0)
            gl.glScalef(self.scale, self.scale, self.scale)

            # if the box is checked for axis on
            if (self.axisOn == 2):
                gl.glCallList(self.axis)

            # bind the shader program
            gl.glUseProgram(program)

            # for every program
            for x in range(0, len(self.uniformVariables)):
                # for every variable in that program
                for y in range(0, len(self.uniformVariables[x]["variables"])):
                    # get the name of that variable
                    uniformVariable = gl.glGetUniformLocation(program, self.uniformVariables[x]["variables"][y]["name"])

                    value = denormalizeSliderRange(self.uniformVariables[x]["variables"][y]["min"], self.uniformVariables[x]["variables"][y]["value"], self.uniformVariables[x]["variables"][y]["max"])

                    # set the uniform value
                    gl.glUniform1f(uniformVariable, value)

            # for every command in the glib file
            for command in self.glibContents:
                # evaluate and run the command
                self.evaluateCommand(command)

    # whenever the screen is resized
    def resizeGL(self, width, height):
        # get the smallest edge
        minSide = min(width, height)
        # the default x and y spans -.5 to .5
        xRange = yRange = 0.5

        # distort the Orthographic view so that it maintains the same aspect
        # ratio for the elements in the screen
        if width > height:
            xRange = (width / height) * yRange
        else:
            yRange = (height / width) * xRange

        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(-xRange, xRange, -yRange, yRange, 0.01, 1000.)
        gl.glMatrixMode(gl.GL_MODELVIEW)

    def mousePressEvent(self, event):
        self.lastPos = event.pos()

    def mouseMoveEvent(self, event):
        dx = event.x() - self.lastPos.x()
        dy = event.y() - self.lastPos.y()

        if event.buttons() & Qt.LeftButton:
            self.setRotation('x', self.rotation['x'] + 8 * dy)
            self.setRotation('y', self.rotation['y'] + 8 * dx)
        elif event.buttons() & Qt.RightButton:
            self.setRotation('x', self.rotation['x'] + 8 * dy)
            self.setRotation('z', self.rotation['z'] + 8 * dx)

        self.lastPos = event.pos()

    def Arrow(self):
        genList = gl.glGenLists(1)
        gl.glNewList(genList, gl.GL_COMPILE)

        dx = .5
        dy = .5
        dz = .5

        gl.glBegin(gl.GL_LINES)

        # red +x
        gl.glColor(1, 0, 0)
        gl.glVertex3f(0, 0, 0)
        gl.glVertex3f(dx, 0, 0)

        # dark red -x
        gl.glColor(.2, 0, 0)
        gl.glVertex3f(0, 0, 0)
        gl.glVertex3f(-dx, 0, 0)

        # green +y
        gl.glColor(0, 1, 0)
        gl.glVertex3f(0, 0, 0)
        gl.glVertex3f(0, dy, 0)

        # dark red -y
        gl.glColor(0, .2, 0)
        gl.glVertex3f(0, 0, 0)
        gl.glVertex3f(0, -dy, 0)

        # blue z
        gl.glColor(0, 0, 1)
        gl.glVertex3f(0, 0, 0)
        gl.glVertex3f(0, 0, dz)

        # dark blue -z
        gl.glColor(0, 0, .2)
        gl.glVertex3f(0, 0, 0)
        gl.glVertex3f(0, 0, -dz)

        gl.glEnd()
        gl.glEndList()

        return genList

    def normalizeAngle(self, angle):
        while angle < 0:
            angle += 360 * 16
        while angle > 360 * 16:
            angle -= 360 * 16
        return angle

    def setClearColor(self, c):
        gl.glClearColor(c.redF(), c.greenF(), c.blueF(), c.alphaF())

    def setColor(self, c):
        gl.glColor4f(c.redF(), c.greenF(), c.blueF(), c.alphaF())


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())
