from PySide2.QtWidgets import (QWidget, QGraphicsScene, QGraphicsView, QGraphicsItem, QPushButton,
                               QGraphicsPolygonItem, QGraphicsPixmapItem, QSizePolicy, QVBoxLayout, QHBoxLayout, 
                               QAction, QCheckBox, QTabWidget, QMenu, QScrollArea)
from PySide2.QtGui import (QPixmap, QPen, QBrush, QPolygonF, QPainter, QImage, QColor,
                           QIntValidator, QDoubleValidator, QKeySequence)
from PySide2.QtCore import Qt, QSize, QPointF, Slot

import hou, numpy, os, math
from math import pi, sin, cos, degrees, radians, sqrt, asin, acos, atan2
from husdui import widgets
from functools import partial
from pprint import pprint as pp

"""
Houdini Lighter UI
Pyhon 3.9.10
Houdini 18.5.569
PySide2 5.15.2

Author: Anton Grabovskiy
This tool is a part of my USD pipeline. It can fast and interactive edit HDR maps, 
delete or change lights shapes, bake textures and preview results.
2023
"""

class Colors :
    shapeDef = (0, 0, 255) # deault state shape color
    shapeSep = (0, 255, 0) # separated state shape color
    shapeDefSel = (255, 0, 0) # selected default state shape color
    shapeSepSel = (255, 255, 0) # selected separated state shape color
    shapefill = (100, 150, 200, 200) # filled shape color
    tabDef = (100, 100, 255) # default state tab color
    tabSep = (100, 255, 0) # separated state tab color
    needBake = (255, 50, 0) # need bake button color
    baked = (100, 200, 50) # baked button color

"""
Collapsable box for extended parameters which are
not needed allways on the screen
"""
class CollapsableBox(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.toggle_button = QPushButton(title)
        self.toggle_button.setStyleSheet("text-align:left")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.toggled.connect(self.on_pressed)

        self.content_area = QWidget()
        self.content_area.setHidden(True)
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.layout_main = QVBoxLayout(self)
        self.layout_main.setSpacing(2)
        self.layout_main.setContentsMargins(0, 10, 0, 0)
        self.layout_main.addWidget(self.toggle_button, 1)
        self.layout_main.addWidget(self.content_area, 7)

    def setContentLayout(self, layout):
        self.content_area.setLayout(layout)

    def on_pressed(self, checked):
        self.content_area.setHidden(not checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton and event.modifiers() == Qt.ControlModifier:
            wtypes = (CheckBox, ColorField, SliderParm, TextField, ComboBoxField)
            for wtype in wtypes :
                for widget in self.content_area.findChildren(wtype):
                    widget.reset()
                        
        super().mousePressEvent(event)

"""
File parameter widget (have some issues with hou.qt.FileLineEdit)
Linked to houdini node parameter
"""
class FileParm(QWidget) :
    def __init__(self, name="Label", parent=None) :
        super().__init__(parent)
        self.parm = None
        label = hou.qt.FieldLabel(name)
        self.field = hou.qt.FileLineEdit()
        self.field.setShortcutAutoRepeat(QKeySequence.Cancel, False)

        lay = hou.qt.GridLayout()
        lay.addWidget(label, 0, 1)
        lay.addWidget(self.field, 0, 2)
        lay.setContentsMargins(2, 2, 2, 2)

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setLayout(lay)

        self.field.editingFinished.connect(self.updateParm)

    def setParm(self, parm) :
        self.parm = parm
        self.setValue(self.parm.rawValue())

    def updateParm(self) :
        current_val = self.parm.rawValue()
        new_val = self.getValue()
        self.parm.set(new_val)
        if current_val != new_val :
            self.parm.pressButton()

    def setValue(self, value) :
        self.field.setText(value)

    def getValue(self) :
        return self.field.text()

    def mousePressEvent(self, event):
        if (event.buttons() == Qt.MidButton and 
            event.modifiers() == Qt.ControlModifier):
            self.reset()

    def reset(self):
        current_val = self.parm.rawValue()
        self.parm.revertToDefaults()
        new_val = self.parm.rawValue()
        self.setValue(new_val)
        if current_val != new_val :
            self.parm.pressButton()

"""
Simple text parameter widget
Linked to houdini node parameter
"""
class TextField(QWidget):
    def __init__(self, name="Label", parent=None):
        super().__init__(parent)
        self.parm = None
        self.field = hou.qt.InputField(hou.qt.InputField.StringType, 1, name)

        lay = QHBoxLayout()
        lay.addWidget(self.field)
        lay.setContentsMargins(2, 2, 2, 2)

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setLayout(lay)

        self.field.editingFinished.connect(self.updateParm)

    def setParm(self, parm) :
        self.parm = parm
        self.setValue(self.parm.eval())

    def updateParm(self) :
        current_val = self.parm.rawValue()
        new_val = self.getValue()
        self.parm.set(new_val)
        if current_val != new_val :
            self.parm.pressButton()

    def setValue(self, value) :
        self.field.setValue(value)

    def getValue(self) :
        return self.field.value()

    def mousePressEvent(self, event):
        if (event.buttons() == Qt.MidButton and 
            event.modifiers() == Qt.ControlModifier):
            self.reset()

    def reset(self):
        current_val = self.parm.rawValue()
        self.parm.revertToDefaults()
        new_val = self.parm.rawValue()
        self.setValue(new_val)
        if current_val != new_val :
            self.parm.pressButton()

"""
Vector parameter widget
Linked to houdini node parameter
"""
class VectorField(QWidget):
    def __init__(self, name="Label", parent=None):
        super().__init__(parent)
        self.parm = None
        self.field = hou.qt.InputField(hou.qt.InputField.FloatType, 3, name)

        lay = QHBoxLayout()
        lay.addWidget(self.field)
        lay.setContentsMargins(2, 2, 2, 2)

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setLayout(lay)

        self.field.editingFinished.connect(self.updateParm)

    def updateValue(self) :
        value = self.parm.eval()
        self.setValue(value[0], 0)
        self.setValue(value[1], 1)
        self.setValue(value[2], 2)

    def setParm(self, parm) :
        self.parm = parm
        self.updateValue()

    def updateParm(self) :
        current_val = self.parm.eval()
        new_val = (self.value(0), self.value(1), self.value(2))
        self.parm.set(new_val)
        if current_val != new_val :
            self.parm.node().parm(self.parm.name()+"x").pressButton()

    def setValue(self, value, component) :
        self.field.setValue(value, component)

    def value(self, component) :
        return self.field.value(component)

    def mousePressEvent(self, event):
        if (event.buttons() == Qt.MidButton and 
            event.modifiers() == Qt.ControlModifier):
            self.reset()

    def reset(self):
        current_val = self.parm.eval()
        self.parm.revertToDefaults()
        new_val = self.parm.eval()
        self.updateValue()
        if current_val != new_val :
            self.parm.node().parm(self.parm.name()+"x").pressButton()

"""
Color parameter widget
Linked to houdini node parameter
"""    
class ColorField(QWidget):
    def __init__(self, name="Label", parent=None):
        super().__init__(parent)
        self.parm = None
        self.field = hou.qt.ColorField(name)
        self.colorField = self.field.findChild(hou.qt.InputField)

        lay = QHBoxLayout()
        lay.addWidget(self.field)
        lay.setContentsMargins(2, 2, 2, 2)

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setLayout(lay)

        self.colorField.valueChanged.connect(self.updateParm)

    def updateValue(self) :
        self.field.setColor(QColor.fromRgbF(*self.parm.eval()))

    def setParm(self, parm) :
        self.parm = parm
        self.updateValue()

    def updateParm(self) :
        current_val = self.parm.eval()
        color = self.getColor().getRgbF()
        new_val = (color[0], color[1], color[2])
        self.parm.set(new_val)
        if current_val != new_val :
            self.parm.node().parm(self.parm.name()+"r").pressButton()

    def setColor(self, color) :
        self.field.setColor(color)

    def getColor(self) :
        return self.field.color()

    def mousePressEvent(self, event):
        if (event.buttons() == Qt.MidButton and 
            event.modifiers() == Qt.ControlModifier):
            self.reset()

    def reset(self):
        self.parm.revertToDefaults()
        self.updateValue()

"""
Button parameter widget
Linked to houdini node parameter
"""
class Button(QWidget) :
    def __init__(self, name="Label", parent=None) :
        super().__init__(parent)
        self.parm = None
        self.button = QPushButton(name)
        self.button.clicked.connect(self.pressButton)

        lay = hou.qt.GridLayout()
        lay.addWidget(self.button, 0, 1)
        lay.setContentsMargins(2, 2, 2, 2)

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setLayout(lay)

    def setParm(self, parm) :
        self.parm = parm

    def pressButton(self) :
        self.parm.pressButton()

    def setColor(self, color) :
        self.button.setStyleSheet(f"QPushButton {{ color: rgb({color[0]},{color[1]},{color[2]}); }}")

    def reset(self):
        self.parm.revertToDefaults()

"""
Houdini like slider parameter widget. Have two modes: float and integer
Linked to houdini node parameter
"""
class SliderParm(QWidget) :
    def __init__(self, valType=hou.qt.InputField.FloatType, name="Label", range=(0,10), parent=None) :
        super().__init__(parent)
        self.parm = None
        self._field = self._createField(valType, name)
        self._slider = self._createSlider(valType, range)

        lay = hou.qt.GridLayout()
        lay.addWidget(self._field, 0, 1)
        lay.addWidget(self._slider, 0, 2)
        lay.setContentsMargins(2, 2, 2, 2)

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setLayout(lay)

        self._field.editingFinished.connect(self.updateParm)
        self._slider.valueChanged.connect(self.updateParm)
    
    def setParm(self, parm) :
        self.parm = parm
        self.setValue(self.parm.eval())

    def updateParm(self) :
        current_val = self.parm.eval()
        self.parm.set(self.getValue())
        new_val = self.parm.eval()
        if current_val != new_val :
            self.parm.pressButton()
        
    def _createSlider(self, valType, range) :
        slider = None
        if valType == hou.qt.InputField.IntegerType :
            slider = widgets.HSlider(Qt.Horizontal)
        elif valType == hou.qt.InputField.FloatType :
            slider = widgets.LinearSlider(Qt.Horizontal)
        slider.setRange(*range)
        slider.valueChanged.connect(self._updateField)
        return slider
        
    def _createField(self, valType, name) :
        field = hou.qt.InputField(valType,1,name)
        field.setValue(1.0)
        
        if valType == hou.qt.InputField.IntegerType :
            field.setValidator(QIntValidator())
        elif valType == hou.qt.InputField.FloatType :
            field.setValidator(QDoubleValidator())
            
        field.editingFinished.connect(self._updateSlider)
        return field
        
    def _updateField(self) :
        self._field.setValue(float(int(self._slider.actualValue()*1000)/1000))
        
    def _updateSlider(self) :
        self._slider.setActualValue(self._field.value())

    def setValue(self, value) :
        self._field.setValue(value)
        self._slider.setActualValue(value)

    def getValue(self) :
        return self._field.value()

    def mousePressEvent(self, event):
        if (event.buttons() == Qt.MidButton and 
            event.modifiers() == Qt.ControlModifier):
            self.reset()

    def reset(self):
        self.parm.revertToDefaults()
        self.parm.pressButton()
        self.setValue(self.parm.eval())

"""
Simple checkbox parameter widget
Linked to houdini node parameter
"""
class CheckBox(QWidget) :
    def __init__(self, name="Label", parent=None) :
        super().__init__(parent)
        self.parm = None
        label = hou.qt.FieldLabel(name)
        self.toggle = QCheckBox()
        lay = hou.qt.GridLayout()
        lay.addWidget(label, 0, 1)
        lay.addWidget(self.toggle, 0, 2)
        
        lay.setContentsMargins(2, 2, 2, 2)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        self.setLayout(lay)
        self.toggle.toggled.connect(self.updateParm)

    def setParm(self, parm) :
        self.parm = parm
        self.setValue(self.parm.eval())

    def updateParm(self) :
        current_val = self.parm.eval()
        new_val = self.getValue()
        self.parm.set(new_val)
        if current_val != new_val :
            self.parm.pressButton()
    
    def setValue(self, value) :
        self.toggle.setChecked(value)

    def getValue(self) :
        return self.toggle.isChecked()

    def mousePressEvent(self, event):
        if (event.buttons() == Qt.MidButton and event.modifiers() == Qt.ControlModifier):
            self.reset()

    def reset(self):
        current_val = self.parm.eval()
        self.parm.revertToDefaults()
        new_val = self.parm.eval()
        self.setValue(new_val)
        if current_val != new_val :
            self.parm.pressButton()

"""
Ordered menu parameter widget
Linked to houdini node parameter
"""
class ComboBoxField(QWidget):
    def __init__(self, name="Label", parent=None):
        super().__init__(parent)
        self.parm = None
        self.label = hou.qt.FieldLabel(name)
        self.field = hou.qt.ComboBox()

        lay = QHBoxLayout()
        lay.addWidget(self.label,1)
        lay.addWidget(self.field,3)
        lay.setContentsMargins(2, 2, 2, 2)

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setLayout(lay)

    def setParm(self, parm):
        self.parm = parm
        self.setValue(self.parm.rawValue())
        self.field.currentIndexChanged.connect(self.updateParm)

    def updateParm(self):
        current_val = self.parm.eval()
        new_val = self.getValue()
        self.parm.set(new_val)
        if current_val != new_val:
            self.parm.pressButton()

    def setValue(self, value):
        index = self.field.findData(value)
        if index != -1:
            self.field.setCurrentIndex(index)

    def getValue(self):
        return self.field.currentData()

    def addValue(self, label, value):
        self.field.addItem(label, value)
    
    def addValues(self, labels, values):
        for label, value in zip(labels, values):
            self.addValue(label, value)

    def mousePressEvent(self, event):
        if event.buttons() == Qt.MidButton and event.modifiers() == Qt.ControlModifier:
            self.reset()

    def reset(self):
        current_val = self.parm.eval()
        self.parm.revertToDefaults()
        new_val = self.parm.eval()
        self.setValue(new_val)
        if current_val != new_val :
            self.parm.pressButton()

"""
Interactive pligon item for light shape
"""
class LightShapeItem(QGraphicsPolygonItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.name = None
        self.idx = None
        self.LightsView = None
        self.separeted = False
        self.filled = False

        self.selectedPen = QPen(QColor.fromRgb(*Colors.shapeDefSel), 2, Qt.SolidLine)
        self.defaultPen = QPen(QColor.fromRgb(*Colors.shapeDef), 2, Qt.SolidLine)
        self.separetedPen = QPen(QColor.fromRgb(*Colors.shapeSep), 2, Qt.SolidLine)
        self.selectedSeparetedPen = QPen(QColor.fromRgb(*Colors.shapeSepSel), 2, Qt.SolidLine)
        self.filledShape = QBrush(QColor(*Colors.shapefill))
        self.setPen(self.defaultPen)

    def updateColor(self):
        if self.isSelected() and self.separeted :
            self.setPen(self.selectedSeparetedPen)
        elif self.isSelected():
            self.setPen(self.selectedPen)
        elif self.separeted:
            self.setPen(self.separetedPen)
        else:
            self.setPen(self.defaultPen)

        if self.filled :
            self.setBrush(self.filledShape)
        else :
            self.setBrush(Qt.NoBrush)
        self.update()

    def mousePressEvent(self, event) :
        self.LightsView.setCurrentIndex(self.idx+1)
        self.update()
        self.scene().update()

    def contextMenuEvent(self, event):
        menu = QMenu()
        option1 = "Merge Light" if self.separeted else "Separate Light"
        option2 = "Unfill Light" if self.filled else "Fill Light"
        separateLightAction = QAction(option1, self.scene().views()[0])
        fillLightAction = QAction(option2, self.scene().views()[0])
        if self.separeted :
            separateLightAction.triggered.connect(self.mergeLight)
        else :
            separateLightAction.triggered.connect(self.separateLight)
        if self.filled :
            fillLightAction.triggered.connect(self.unfillLight)
        else :
            fillLightAction.triggered.connect(self.fillLight)
        menu.addAction(separateLightAction)
        menu.addAction(fillLightAction)
        menu.exec_(event.screenPos())

    def separateLight(self):
        self.LightsView.seps[self.idx].toggle.setChecked(True)

    def mergeLight(self):
        self.LightsView.seps[self.idx].toggle.setChecked(False)

    def fillLight(self):
        self.LightsView.fills[self.idx].toggle.setChecked(True)

    def unfillLight(self):
        self.LightsView.fills[self.idx].toggle.setChecked(False)

    def setLightsView(self, lightsView):
        self.LightsView = lightsView

    def setName(self, name):
        self.name = name

    def setIdx(self, idx):
        self.idx = idx

    @Slot(bool)
    def setSeparated(self, value):
        self.separeted = value
        self.updateColor()

    @Slot(bool)
    def setFilled(self, value):
        self.filled = value
        self.updateColor()

"""
Resizable graphics view for HDR map
"""
class ResizableGraphicsView(QGraphicsView):
    def __init__(self, lightsView, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.lightsView = lightsView

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def setEnvTab(self) :
        self.lightsView.setCurrentIndex(0)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        event.accept()

"""
Clicable pixmap item for HDR map
"""
class ClickablePixmapItem(QGraphicsPixmapItem):
    def __init__(self, pixmap=None, parent=None):
        super().__init__(pixmap, parent)
        self.lightsView = None
        self.node = None

    def setLightsView(self, lightsView):
        self.lightsView = lightsView

    def setNode(self, node):
        self.node = node

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.lightsView.setCurrentIndex(0)
            event.accept()
        else :
            event.ignore()

    def contextMenuEvent(self, event):
        menu = QMenu()
        option1 = "Align to center"
        option2 = "Reset rotation"
        alignAction = QAction(option1, self.scene().views()[0])
        alignAction.triggered.connect(lambda : self.alignToCenter(event.pos()))
        resetAction = QAction(option2, self.scene().views()[0])
        resetAction.triggered.connect(self.resetRotations)
        menu.addAction(alignAction)
        menu.addAction(resetAction)
        menu.exec_(event.screenPos())

    def upadate(self):
        self.lightsView.updateParmsView()

    def cartesian_to_spherical(self, x, y):
        latitude = math.pi * (y - 0.5)
        longitude = 2 * math.pi * (x - 0.5)
        return (latitude, longitude)
    
    def spherical_to_cartesian(self, lat, lon):
        X = math.cos(lat) * math.cos(lon)
        Y = math.cos(lat) * math.sin(lon)
        Z = math.sin(lat)
        return (X, Y, Z)
    
    def cartesian_to_euler(self, X, Y, Z):
        # rotation order: x, y, z
        r = math.sqrt(X*X + Y*Y + Z*Z)
        elevation = math.degrees(math.asin(Z / r))
        azimuth = math.degrees(math.atan2(Y, X))
        return (azimuth, elevation, 0)

    def alignToCenter(self, pos) :
        pixmap_size = self.pixmap().size()
        pos = self.mapToScene(pos)
        x = pos.x() / pixmap_size.width()
        y = 0.5 # pos.y() / pixmap_size.height()

        lat, lon = self.cartesian_to_spherical(x, y)
        X, Y, Z = self.spherical_to_cartesian(lat, lon)
        azimuth, elevation, _ = self.cartesian_to_euler(X, Y, Z)
        
        current_angle = self.node.parm("roty").eval()
        self.node.parm("roty").set(current_angle - azimuth)
        self.upadate()

    def resetRotations(self) :
        self.node.parm("rotx").set(0)
        self.node.parm("roty").set(0)
        self.node.parm("rotz").set(0)
        self.upadate()

"""
Graphics view for lights shapes and Hdr map preview
"""
class HdrView(QWidget) :
    def __init__(self, lightsView, parent=None) :
        super().__init__(parent)
        self.asset = None
        self.cop = None
        self.parms = None
        self.lightsView = lightsView
        self.pixmap_item = None
        self.background = None
        self.shapes = []

    def initView(self) :
        self.scene = QGraphicsScene()
        self.view = ResizableGraphicsView(self.lightsView)
        self.view.setScene(self.scene)

        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

        self.sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.sizePolicy.setHeightForWidth(True)
        self.setSizePolicy(self.sizePolicy)

        self.adjustSize()
        self.setLayout(layout)

    def sizeHint(self):
        return QSize(512, 256)

    def heightForWidth(self, width):
        return width / 2

    def setWidthForHeight(self, height):
        return height * 2

    def setHDR(self, copNode) :
        self.cop = copNode
        width = self.cop.xRes()
        height = self.cop.yRes()
        imgArr = numpy.frombuffer(self.cop.allPixelsAsString("C", depth=hou.imageDepth.Int8), dtype=numpy.int8)
        img = QImage(imgArr.data, width, height, QImage.Format_RGB888)
        self.background = QPixmap(img)
        if self.pixmap_item is None :
            pixmap_item = ClickablePixmapItem(self.background)
            pixmap_item.setLightsView(self.lightsView)
            pixmap_item.setNode(self.asset)
            pixmap_item.setZValue(0)
            self.scene.addItem(pixmap_item)
        else :
            self.pixmap_item.setPixmap(self.background)

    def setAsset(self, node) :
        self.asset = node
        self.cop = self.asset.node("VIEW/OUT")
        self.setHDR(self.cop)

    def setLightsView(self, lightsView) :
        self.lightsView = lightsView

    # build shapes from geo
    def updateShapes(self) :
        poly = self.asset.node("geo/POLYGONS")
        geo = poly.geometry()

        # cleanup old shapes
        current_names = set(prim.attribValue("name") for prim in geo.prims())
        for i in range(len(self.shapes)) :
            if i >= len(current_names) :
                item = self.shapes.pop(-1)
                self.scene.removeItem(item)
                del item

        # create new shapes
        for i, prim in enumerate(geo.prims()) :
            name = prim.attribValue("name")
            points = prim.points()
            coords = []
            for point in points :
                pos = point.position()
                coords.append(QPointF(int(pos[0]), int(pos[1])))
            polygon = QPolygonF(coords)

            if i >= len(self.shapes) :
                self.shapes.append(LightShapeItem(polygon))
                self.shapes[i].setName(name)
                self.shapes[i].setIdx(i)
                self.shapes[i].setLightsView(self.lightsView)
                self.shapes[i].setFlag(QGraphicsItem.ItemIsSelectable, True)
                self.shapes[i].setFlag(QGraphicsItem.ItemIsMovable, False)
                self.shapes[i].setZValue(1)
                self.scene.addItem(self.shapes[i])
            else :
                self.shapes[i].setPolygon(polygon)

    def selectShape(self, index) :
        for shape in self.shapes :
            shape.setSelected(False)
            shape.updateColor()
        if index < len(self.shapes) and index >= 0 :
            self.shapes[index].setSelected(True)
            self.shapes[index].updateColor()

"""
General parameters widget
Store parameters for loading and saving 
and for highlights detection
"""
class ParmsView(QWidget) :
    def __init__(self, hdrView, parent=None) :
        super().__init__(parent)
        self.node = None
        self.hdrView = hdrView
        self.lightsView = None
        
        self.primpath = TextField("Prim Path")
        self.extract = Button("Extract Lights")
        self.file = FileParm("Input HDR Map")
        self.output = FileParm("Output HDR Map")
        self.mapRes = ComboBoxField("Output HDR Res")
        self.mapRes.addValues(["Same as Input", "1024 x 512", "2048 x 1024", "4096 x 2048"], [0,1,2,3])
        self.texRes = ComboBoxField("    Light Bake Res")
        self.texRes.addValues(["64 x 64", "128 x 128", "256 x 256", "512 x 512"], [64, 128, 256, 512])
        self.blur_tex = SliderParm(hou.qt.InputField.FloatType, "Light Bake Blur", (0.0,10000.0))
        self.bakeall = Button("Bake All Textures")
        self.hdrRes = ComboBoxField("Detect Map Res")
        self.hdrRes.addValues(["512 x 256", "1024 x 512", "2048 x 1024"], [512, 1024, 2048])
        self.clip = SliderParm(hou.qt.InputField.FloatType, "Clip Lights", (10.0,5000.0))
        self.blur = SliderParm(hou.qt.InputField.FloatType, "Blur", (0.0,10000.0))
        self.reshape = SliderParm(hou.qt.InputField.IntegerType, "Dilate/Erode", (-10,10))
        self.threshold = SliderParm(hou.qt.InputField.FloatType, "Threshold", (0.1, 1000.0))
        self.rot = VectorField("Rotate Map")
        self.intensity = SliderParm(hou.qt.InputField.FloatType, "Master Intensity", (0.0, 1000.0))

        self.primpath.setToolTip("primpath\nPath to the prim with lights")
        self.extract.setToolTip("extract\nCreate network with native houdini nodes for each light")
        self.file.setToolTip("texpath\nPath to the HDR map")
        self.output.setToolTip("savepath\nPath to the HDR map, used for detection")
        self.mapRes.setToolTip("envres\nResolution of the output HDR map") 
        self.texRes.setToolTip("lightres\nResolution of the baked individual light texture")
        self.blur_tex.setToolTip("blurtex\nBlur size of the baked individual light texture")
        self.bakeall.setToolTip("bake\nBake all light textures\nIt will go through all tabs and bake textures for each light\nIf button color is green - all textures are baked\nIf button color is red - some textures can need to bake")
        self.hdrRes.setToolTip("lightres\nResolution of the HDR map used for detection")
        self.clip.setToolTip("clip\nClip higlights threshold")
        self.blur.setToolTip("blursize\nBlur size of the higlights for shape smoothing")
        self.reshape.setToolTip("size\nDilate/Erode size of the higlights for glueing nearest shapes")
        self.threshold.setToolTip("threshold\nThreshold of the higlights for result mask creation.\nLower value - bigger shapes of higlights")
        self.rot.setToolTip("rotx, roty, rotz\nRotate HDR map. Needed if you have splitted lights on the sides of hdr map\n Change orientation of the map and all lights")
        self.intensity.setToolTip("intensity\nGlobal intensity of all lights and HDR map")

        self.file.field.textChanged.connect(self.FileLineEditCrutch)
        self.output.field.textChanged.connect(self.FileLineEditCrutch)

        self.file.field.textChanged.connect(self.update_hdr)
        self.texRes.field.currentIndexChanged.connect(self.drawView)
        self.hdrRes.field.currentIndexChanged.connect(self.drawView)
        self.clip._field.editingFinished.connect(self.drawView)
        self.clip._slider.valueChanged.connect(self.drawView)
        self.blur._field.editingFinished.connect(self.drawView)
        self.blur._slider.valueChanged.connect(self.drawView)
        self.reshape._field.editingFinished.connect(self.drawView)
        self.reshape._slider.valueChanged.connect(self.drawView)
        self.threshold._field.editingFinished.connect(self.drawView)
        self.threshold._slider.valueChanged.connect(self.drawView)
        self.rot.field.editingFinished.connect(self.drawView)

        self.mapRes.field.currentIndexChanged.connect(self.checkBakedFlag)
        self.output.field.textChanged.connect(self.checkBakedFlag)
        self.blur_tex._field.editingFinished.connect(self.checkBakedFlag)
        self.blur_tex._slider.valueChanged.connect(self.checkBakedFlag)
        self.bakeall.button.clicked.connect(self.updateParms)
        self.bakeall.button.clicked.connect(self.checkBakedFlag)

        prim_layout = QHBoxLayout()
        prim_layout.setSpacing(0)
        prim_layout.setContentsMargins(2, 2, 2, 2)
        prim_layout.addWidget(self.primpath,3)
        prim_layout.addWidget(self.extract,1)

        out_layout = QHBoxLayout()
        out_layout.setSpacing(0)
        out_layout.setContentsMargins(2, 2, 2, 2)
        out_layout.addWidget(self.output,3)
        out_layout.addWidget(self.bakeall,1)

        res_layout = QHBoxLayout()
        res_layout.setSpacing(0)
        res_layout.setContentsMargins(2, 2, 2, 2)
        res_layout.addWidget(self.mapRes)
        res_layout.addWidget(self.texRes)

        group_box = CollapsableBox("Hightlights Detection")

        box_layout = QVBoxLayout()
        box_layout.setSpacing(0)
        box_layout.addWidget(self.hdrRes)
        box_layout.addWidget(self.clip)
        box_layout.addWidget(self.blur)
        box_layout.addWidget(self.reshape)
        box_layout.addWidget(self.threshold)
        box_layout.addWidget(self.rot)
        group_box.setContentLayout(box_layout)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.addLayout(prim_layout)
        layout.addWidget(self.file)
        layout.addLayout(out_layout)
        layout.addLayout(res_layout)
        layout.addWidget(self.blur_tex)
        layout.addWidget(group_box)
        layout.addSpacing(10)
        layout.addWidget(self.intensity)
        
        self.setLayout(layout)

    def setNode(self, node) :
        self.node = node

    def setLightsView(self, lightsView) :
        self.lightsView = lightsView

    def updateParms(self) :
        self.primpath.setParm(self.node.parm("primpath"))
        self.extract.setParm(self.node.parm("extract"))
        self.file.setParm(self.node.parm("texpath"))
        self.output.setParm(self.node.parm("savepath"))
        self.mapRes.setParm(self.node.parm("envres"))
        self.blur_tex.setParm(self.node.parm("blurtex"))
        self.bakeall.setParm(self.node.parm("bake"))
        self.texRes.setParm(self.node.parm("lightres"))
        self.hdrRes.setParm(self.node.parm("detectres"))
        self.clip.setParm(self.node.parm("clip"))
        self.blur.setParm(self.node.parm("blursize"))
        self.reshape.setParm(self.node.parm("size"))
        self.threshold.setParm(self.node.parm("threshold"))
        self.rot.setParm(self.node.parmTuple("rot"))
        self.intensity.setParm(self.node.parm("intensity"))

    # Crutch for solving problem when Cancel button in FileParm widget pressed
    def FileLineEditCrutch(self) :
        file = self.file.getValue()
        output = self.output.getValue()
        if file == "" or output == "" :
            self.updateParms()
    
    def drawView(self) :
        self.hdrView.setHDR(self.hdrView.cop)
        self.hdrView.updateShapes()
        self.lightsView.buildTabs()
        self.checkBakedFlag()

    def update_hdr(self) :
        current_path = self.node.parm("texpath").eval()
        new_path = self.file.getValue()
        if current_path != new_path and os.path.exists(hou.text.expandString(new_path)) :
            self.node.parm("texpath").set(self.file.getValue())
            self.hdrView.setHDR(self.hdrView.cop)
            self.checkBakedFlag()
        self.hdrView.updateShapes()
        self.lightsView.buildTabs()
    
    # Check for all baked flags on node and switch buttons color
    def checkBakedFlag(self) :
        check = self.node.parm("baked_env").eval()
        env_color = Colors.baked if check else Colors.needBake
        self.lightsView.envBake.setColor(env_color)
        for i, button in enumerate(self.lightsView.buttons) :
            baked = self.node.parm(f"baked{i+1}").eval()
            check = check and baked
            color = Colors.baked if baked else Colors.needBake
            button.setColor(color)
        all_color = Colors.baked if check else Colors.needBake
        self.bakeall.setColor(all_color)

"""
Light parameters widget
First tab is for environment light
Other tabs are for light shapes
"""
class LightParms(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.node = None
        self.hdrView = None
        self.parmsView = None
        self.tabs = []
        self.seps = []
        self.fills = []
        self.envBake = None
        self.buttons = []
        self.envTab = None

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.currentChanged.connect(self.onTabChange)

    # reset full content of current tab
    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton and event.modifiers() == Qt.ControlModifier:
            current_index = self.currentIndex()
            if current_index != -1:
                tab_widget = self.widget(current_index)
                if isinstance(tab_widget, QWidget):
                    wtypes = (CheckBox, ColorField, SliderParm, TextField, ComboBoxField)
                    for wtype in wtypes :
                        for widget in tab_widget.findChildren(wtype):
                            widget.reset()
                        
        super().mousePressEvent(event)

    def setHdrView(self, hdrView) :
        self.hdrView = hdrView

    def setNode(self, node) :
        self.node = node

    def setParmsView(self, parmsView) :
        self.parmsView = parmsView

    def updateParmsView(self) :
        self.parmsView.updateParms()
        self.parmsView.drawView()
    
    # environment map tab is always first
    def buildEnvTab(self) :
        use_env = CheckBox("Use EnvLight")
        env_color = ColorField("Color Tint")
        env_exposure = SliderParm(hou.qt.InputField.FloatType, "Exposure", (-1500.0,1500.0))
        env_light_name = TextField("Name")
        env_lpe = TextField("                LPE Tag")
        self.envBake = Button(f"Bake EnvLight Texture")

        use_env.setParm(self.node.parm("use_env"))
        env_color.setParm(self.node.parmTuple("env_clr"))
        env_exposure.setParm(self.node.parm("env_exposure"))
        env_light_name.setParm(self.node.parm("env_name"))
        env_lpe.setParm(self.node.parm("env_lpe"))
        self.envBake.setParm(self.node.parm("bake_env"))

        use_env.setToolTip("use_env\nUse Environment Light")
        env_color.setToolTip("env_clrr, env_clrg, env_clrb\nEnvironment Light Color multiplier")
        env_exposure.setToolTip("env_exposure\nEnvironment Light Exposure")
        env_light_name.setToolTip("env_name\nEnvironment Light Name")
        env_lpe.setToolTip("env_lpe\nEnvironment Light LPE Tag")
        self.envBake.setToolTip("bake_env\nBake Environment Light Texture\nIf button color is green - texture is baked\nIf button color is red - texture need to bake")

        self.envBake.button.clicked.connect(self.parmsView.checkBakedFlag)

        def toggle_widgets(checked, widgets):
            for widget in widgets:
                widget.setEnabled(checked)

        toggle_func = partial(toggle_widgets, widgets=[env_color, env_exposure, env_light_name, env_lpe])
        use_env.toggle.toggled.connect(toggle_func)
        toggle_func(use_env.toggle.isChecked())

        env_name_layout = QHBoxLayout()
        env_name_layout.setSpacing(2)
        env_name_layout.setContentsMargins(0, 0, 0, 0)
        env_name_layout.addWidget(env_light_name)
        env_name_layout.addWidget(env_lpe)

        env_bake_layout = QHBoxLayout()
        env_bake_layout.setSpacing(2)
        env_bake_layout.setContentsMargins(0, 0, 0, 0)
        env_bake_layout.addStretch(2)
        env_bake_layout.addWidget(self.envBake,3)

        env_layout = QVBoxLayout()
        env_layout.setSpacing(2)
        env_layout.setContentsMargins(2, 10, 2, 2)
        env_layout.addWidget(use_env)
        env_layout.addWidget(env_color)
        env_layout.addWidget(env_exposure)
        env_layout.addLayout(env_name_layout)
        env_layout.addStretch()
        env_layout.addLayout(env_bake_layout)
        
        self.envTab = QWidget()
        self.envTab.setLayout(env_layout)
        self.envTab.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.addTab(self.envTab, "Env")     

    # dinamicaly build tabs for all light shapes
    def buildTabs(self) :
        # Create widgets
        self.node.parm("lights").set(len(self.hdrView.shapes))
        
        self.envTab = None
        for i in range(len(self.tabs)) :
            tab = self.tabs.pop(0)
            sep = self.seps.pop(0)
            fil = self.fills.pop(0)
            buttons = self.buttons.pop(0)
            del tab
            del sep
            del fil
            del buttons

        for i in range(self.count()) :
            self.removeTab(0)

        self.buildEnvTab()
        # iterate over shapes and create tabs
        for i in range(len(self.hdrView.shapes)) :
            shape = self.hdrView.shapes[i]
            separate_toggle = CheckBox("Separate Light")
            renderable_toggle = CheckBox("Renderable")
            fill_toggle = CheckBox("Fill Background")
            color = ColorField("Color Tint")
            exposure = SliderParm(hou.qt.InputField.FloatType, "Exposure", (-2000.0,2000.0))
            light_name = TextField("Name")
            lpe = TextField("                LPE Tag")
            light_type = ComboBoxField("Light Type")
            light_type.addValues(["Distant", "Point", "Sphere", "Disc", "Rectangle"], [0,1,2,3,4])
            distant_angle = SliderParm(hou.qt.InputField.FloatType, "    Distant Angle", (0.0,6000.0))
            distance = SliderParm(hou.qt.InputField.FloatType, "Distance", (0.0,10000.0))
            use_texture = CheckBox("Use Texture")
            bake_texture = Button(f"Bake Light Texture")

            # link widgets to parameters
            separate_toggle.setParm(self.node.parm(f"separate{i+1}"))
            renderable_toggle.setParm(self.node.parm(f"renderable{i+1}"))
            fill_toggle.setParm(self.node.parm(f"fill{i+1}"))
            color.setParm(self.node.parmTuple(f"clr{i+1}"))
            exposure.setParm(self.node.parm(f"exposure{i+1}"))
            light_name.setParm(self.node.parm(f"name{i+1}"))
            lpe.setParm(self.node.parm(f"lpe{i+1}"))
            light_type.setParm(self.node.parm(f"lighttype{i+1}"))
            distant_angle.setParm(self.node.parm(f"dist_angle{i+1}"))
            distance.setParm(self.node.parm(f"dist{i+1}"))
            use_texture.setParm(self.node.parm(f"use_tex{i+1}"))
            bake_texture.setParm(self.node.parm(f"bake{i+1}"))

            separate_toggle.setToolTip(f"separate{i+1}\nSeparate Light from the HDR map")
            renderable_toggle.setToolTip(f"renderable{i+1}\nMake Light renderable")
            fill_toggle.setToolTip(f"fill{i+1}\nDelete highlight from the HDR map (Fill with nearest colors)")
            color.setToolTip(f"clr{i+1}r, clr{i+1}g, clr{i+1}b\nLight Color multiplier")
            exposure.setToolTip(f"exposure{i+1}\nLight Exposure")
            light_name.setToolTip(f"name{i+1}\nLight Name")
            lpe.setToolTip(f"lpe{i+1}\nLight LPE Tag")
            light_type.setToolTip(f"lighttype{i+1}\nLight Type Definition\nTexture can be used only for Rectangle Light")
            distant_angle.setToolTip(f"dist_angle{i+1}\nDistant Light Angle\n (size of shape meashured in degrees from the center of imaginary sphere)")
            distance.setToolTip(f"dist{i+1}\nLight Distance from center. Usable for all instead distant light.\n When Light in distant mode it just move icon in 3d space but not change lighting")
            use_texture.setToolTip(f"use_tex{i+1}\nUse Texture for Rectangle Light")
            bake_texture.setToolTip(f"bale{i+1}\nBake current light Texture\nIf button color is green - texture is baked\nIf button color is red - texture need to bake")

            # connect widgets to each other
            separate_toggle.toggle.toggled.connect(self.hdrView.shapes[i].setSeparated)
            separate_toggle.toggle.toggled.connect(self.parmsView.checkBakedFlag)
            fill_toggle.toggle.toggled.connect(self.hdrView.shapes[i].setFilled)
            fill_toggle.toggle.toggled.connect(self.parmsView.checkBakedFlag)
            color.colorField.valueChanged.connect(self.parmsView.checkBakedFlag)
            exposure._field.editingFinished.connect(self.parmsView.checkBakedFlag)
            exposure._slider.valueChanged.connect(self.parmsView.checkBakedFlag)
            bake_texture.button.clicked.connect(self.parmsView.checkBakedFlag)
            shape.setSeparated(separate_toggle.getValue())

            # set rules for widgets activation
            #                         Sep   Type   UseTex
            renderable_toggle.rule = [True, None,  None]
            fill_toggle.rule =       [None, None,  None]
            light_name.rule =        [True, None,  None]
            lpe.rule =               [True, None,  None]
            light_type.rule =        [True, None,  None]
            distant_angle.rule =     [True, True,  None]
            distance.rule =          [True, None,  None]
            use_texture.rule =       [True, False, None]
            bake_texture.rule =      [None, None,  None]

            # activate widgets by rules. Not beautiful but works ))
            def activateParms(checked, widgets, checks) :
                for widget in widgets :
                    tests = []
                    for i, check in enumerate(checks) :
                        if i == 1 :
                            tests.append(check.currentIndex()==0 if check is not None else None)
                        else :
                            tests.append(check.isChecked() if check is not None else None)
                    state = all([tests[i]==widget.rule[i] for i in range(len(tests)) if widget.rule[i] is not None])
                    widget.setEnabled(state)
            toggles = [ separate_toggle.toggle, light_type.field, use_texture.toggle ]
            separate_toggle.toggle.toggled.connect(lambda checked, w=[renderable_toggle, light_name, lpe, light_type, distant_angle, distance, use_texture, bake_texture], check=toggles : activateParms(checked,w,check))
            light_type.field.currentIndexChanged.connect(lambda checked, w=[distant_angle, distance, use_texture, bake_texture], check=toggles : activateParms(checked,w,check))
            use_texture.toggle.toggled.connect(lambda checked, w=[bake_texture], check=toggles: activateParms(checked,w,check))
            activateParms(separate_toggle.toggle.isChecked(), [renderable_toggle, light_name, lpe, light_type, distant_angle, distance, use_texture, bake_texture],toggles)

            toggles_layout = QHBoxLayout()
            toggles_layout.setSpacing(2)
            toggles_layout.setContentsMargins(0, 0, 0, 0)
            toggles_layout.addWidget(separate_toggle)
            toggles_layout.addWidget(fill_toggle)
            toggles_layout.addWidget(renderable_toggle)

            name_layout = QHBoxLayout()
            name_layout.setSpacing(2)
            name_layout.setContentsMargins(0, 0, 0, 0)
            name_layout.addWidget(light_name)
            name_layout.addWidget(lpe)

            type_layout = QHBoxLayout()
            type_layout.setSpacing(2)
            type_layout.setContentsMargins(0, 0, 0, 0)
            type_layout.addWidget(light_type,2)
            type_layout.addWidget(distant_angle,3)

            tex_layout = QHBoxLayout()
            tex_layout.setSpacing(2)
            tex_layout.setContentsMargins(0, 0, 0, 0)
            tex_layout.addWidget(use_texture,2)
            tex_layout.addWidget(bake_texture,3)

            layout = QVBoxLayout()
            layout.setSpacing(2)
            layout.setContentsMargins(2, 10, 2, 2)
            layout.addLayout(toggles_layout)
            layout.addWidget(color)
            layout.addWidget(exposure)
            layout.addLayout(name_layout)
            layout.addLayout(type_layout)
            layout.addWidget(distance)
            layout.addLayout(tex_layout)
            
            self.tabs.append(QWidget())
            self.seps.append(separate_toggle)
            self.fills.append(fill_toggle)
            self.buttons.append(bake_texture)
            self.tabs[i].setLayout(layout)
            self.tabs[i].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            self.addTab(self.tabs[i], f"L {i+1}")
            
            # set color for tabs of separated lights
            def sep_color(idx, checked) :
                if checked :
                    self.tabBar().setTabTextColor(idx+1, QColor.fromRgb(*Colors.tabSep))
                else :
                    self.tabBar().setTabTextColor(idx+1, QColor.fromRgb(*Colors.tabDef))
            # connect color to toggle
            self.seps[i].toggle.toggled.connect(lambda checked, index=i: sep_color(index, checked))
            sep_color(i, self.seps[i].toggle.isChecked())
        # check all baked flags
        self.parmsView.checkBakedFlag()

    def activateTab(self, index):
        self.setCurrentIndex(index)

    def onTabChange(self, index):
        if len(self.tabs) != 0:
            self.hdrView.selectShape(index-1)

"""
Main panel widget
Have methods used in houdini lighter python pannel
"""
class LighterPanel(QWidget) :
    def __init__(self, parent=None) :
        super().__init__(parent)

        self._asset = None
        self._panel = None
        self._LightsView = LightParms()
        self._HdrView = HdrView(self._LightsView)
        self._HdrView.setMinimumHeight(256)
        self._HdrView.initView()
        self._LightsView.setHdrView(self._HdrView)
        self._ParmsView = ParmsView(self._HdrView)
        self._HdrView.setLightsView(self._LightsView)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        scroll_area = QScrollArea()
        layout.addWidget(scroll_area)
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_area.setWidget(scroll_widget)
        scroll_layout = QVBoxLayout()
        scroll_layout.addWidget(self._HdrView,1)
        scroll_layout.addWidget(self._ParmsView)
        scroll_layout.addWidget(self._LightsView)
        scroll_widget.setLayout(scroll_layout)
        self.setLayout(layout)

    def onActivate(self, kwargs) :
        self._panel = kwargs["paneTab"]

    def onDeactivate(self) :
        self._panel = None

    def onDestroy(self) :
        del self._panel
        del self._asset
        del self._LightsView
        del self._HdrView
        del self._ParmsView

    def onNodePathChanged(self, node) :
        if "lighter" in node.type().name() :
            self._asset = node
            self._ParmsView.setNode(self._asset)
            self._ParmsView.setLightsView(self._LightsView)
            self._LightsView.setNode(self._asset)
            self._LightsView.setParmsView(self._ParmsView)
            self._HdrView.setAsset(self._asset)
            self._HdrView.setLightsView(self._LightsView)
            self._HdrView.updateShapes()
            self._LightsView.buildTabs()
            self._ParmsView.updateParms()

