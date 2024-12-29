# encoding: utf-8
from __future__ import division, print_function, unicode_literals

###########################################################################################################
#
#
#	Filter with dialog Plugin
#
#	Read the docs:
#	https://github.com/schriftgestalt/GlyphsSDK/tree/master/Python%20Templates/Filter%20with%20Dialog
#
#	For help on the use of Interface Builder:
#	https://github.com/schriftgestalt/GlyphsSDK/tree/master/Python%20Templates
#
#
###########################################################################################################

import objc
from GlyphsApp import *
from GlyphsApp.plugins import *
from math import hypot, atan2, cos, sin, pi
from AppKit import NSAffineTransform, NSPoint

@objc.python_method
def deleteAllComponents(thisLayer):
	try:
		for i in reversed(range(len(thisLayer.shapes))):
			if isinstance(thisLayer.shapes[i], GSComponent):
				del thisLayer.shapes[i]
		return True
		
	except Exception as e:
		import traceback
		print(traceback.format_exc())
		return False


@objc.python_method
def bezier(A, B, C, D, t):
	x1, y1 = A.x, A.y
	x2, y2 = B.x, B.y
	x3, y3 = C.x, C.y
	x4, y4 = D.x, D.y
	
	x = x1*(1-t)**3 + x2*3*t*(1-t)**2 + x3*3*t**2*(1-t) + x4*t**3
	y = y1*(1-t)**3 + y2*3*t*(1-t)**2 + y3*3*t**2*(1-t) + y4*t**3

	return x, y


@objc.python_method
def distance(node1, node2):
	return hypot(node1.x - node2.x, node1.y - node2.y)


@objc.python_method
def segmentsForPath(p):
	segments=[]
	currentSegment=[]
	pathlength = len(p.nodes)
	for i,n in enumerate(p.nodes):
		currentSegment.append(n.position)
		if i>0 and n.type != OFFCURVE:
			offset = len(currentSegment)
			if not offset in (2,4):
				firstPoint = p.nodes[(i-offset)%pathlength].position
				currentSegment.insert(0, firstPoint)
			segments.append(tuple(currentSegment))
			currentSegment=[]
	return segments


@objc.python_method
def getOrientationAngle(originPoint, orientationPoint):
	dx = orientationPoint.x - originPoint.x
	dy = orientationPoint.y - originPoint.y
	return atan2(dy, dx)


@objc.python_method
def createTransformMatrix(origin, angle):
	transform = NSAffineTransform.transform()
	transform.translateXBy_yBy_(origin.x, origin.y)
	transform.rotateByRadians_(angle)
	transform.translateXBy_yBy_(-origin.x, -origin.y)
	return transform.transformStruct()


@objc.python_method
def weightedAverageAngles(angle1Rad, angle2Rad, factor=0.5):
	x =  (1 + factor) * cos(angle1Rad) + -factor * cos(angle2Rad)
	y =  (1 + factor) * sin(angle1Rad) + -factor * sin(angle2Rad)
	avgAngleRad = atan2(y, x) % (2 * pi)
	return avgAngleRad


@objc.python_method
def getTangentAngle(p1, p2, p3=None, p4=None, t=0):
	# Line segment case
	if p3 is None and p4 is None:
		dx = p2[0] - p1[0]
		dy = p2[1] - p1[1]
		return atan2(dy, dx)
	
	# Cubic Bezier case
	# First derivative of cubic Bezier gives tangent direction
	t = max(0, min(1, t))  # Clamp t between 0 and 1
	
	# Derivative coefficients
	mt = 1 - t
	dx = 3 * mt**2 * (p2[0] - p1[0]) + \
		 6 * mt * t * (p3[0] - p2[0]) + \
		 3 * t**2 * (p4[0] - p3[0])
		 
	dy = 3 * mt**2 * (p2[1] - p1[1]) + \
		 6 * mt * t * (p3[1] - p2[1]) + \
		 3 * t**2 * (p4[1] - p3[1])
	
	return atan2(dy, dx)


@objc.python_method
def getFineGrainPointsForPath(thisPath, distanceBetweenDots, precision=10):
	try:
		layerCoords = []
		tangentAngles = []
		# pathSegments = segmentsForPath(thisPath)
		pathSegments = thisPath.segments
		
		for thisSegment in pathSegments:
			# gsPathSegment = GSPathSegment(*thisSegment) # convert to GSPathSegment for convenience methods
			segmentLength = thisSegment.length()
			
			if len(thisSegment) == 2:
				# straight line:
				beginPoint = thisSegment[0]
				endPoint   = thisSegment[1]
				tangentAngle = getTangentAngle(beginPoint, endPoint)
				dotsPerSegment = int(segmentLength/distanceBetweenDots*11)
				for i in range(dotsPerSegment):
					x = float(endPoint.x * i) / dotsPerSegment + float(beginPoint.x * (dotsPerSegment-i)) / dotsPerSegment
					y = float(endPoint.y * i) / dotsPerSegment + float(beginPoint.y * (dotsPerSegment-i)) / dotsPerSegment
					layerCoords.append(NSPoint(x, y))
					tangentAngles.append(tangentAngle)
				
			elif len(thisSegment) == 4:
				# curved segment:
				bezierPointA = thisSegment[0]
				bezierPointB = thisSegment[1]
				bezierPointC = thisSegment[2]
				bezierPointD = thisSegment[3]
				dotsPerSegment = int((segmentLength / distanceBetweenDots) * 10)
			
				for i in range(1, dotsPerSegment):
					t = float(i) / float(dotsPerSegment)
					x, y = bezier(bezierPointA, bezierPointB, bezierPointC, bezierPointD, t)
					layerCoords.append(NSPoint(x, y))
					tangentAngles.append(getTangentAngle(bezierPointA, bezierPointB, bezierPointC, bezierPointD, t))
			
				layerCoords.append(NSPoint(bezierPointD.x, bezierPointD.y))
				tangentAngles.append(getTangentAngle(bezierPointA, bezierPointB, bezierPointC, bezierPointD, 1))
				
		return layerCoords, tangentAngles
	except Exception as e:
		print("Stitcher Error in getFineGrainPointsForPath():\n%s"%e)
		import traceback
		print(traceback.format_exc())


@objc.python_method
def interpolatePointPos(p1, p2, factor):
	factor = factor % 1.0
	x = p1.x * factor + p2.x * (1.0-factor)
	y = p1.y * factor + p2.y * (1.0-factor)
	return NSPoint(x,y)


@objc.python_method
def dotCoordsOnPath(thisPath, distanceBetweenDots, balanceOverCompletePath=False):
	try:
		firstPoint = thisPath.nodes[0]
		if firstPoint.type == OFFCURVE:
			firstPoint = thisPath.nodes[-1] # closed path that starts with a curve
		dotPoints = [firstPoint]
		fineGrainPoints, fineGrainTangentAngles = getFineGrainPointsForPath(thisPath, distanceBetweenDots)
		tangentAngles = [fineGrainTangentAngles[0]]
	
		myLastPoint = dotPoints[-1]
		for i, thisPoint in enumerate(fineGrainPoints):
			if distance(myLastPoint, thisPoint) >= distanceBetweenDots:
				dotPoints.append(thisPoint)
				tangentAngles.append(fineGrainTangentAngles[i])
				myLastPoint = thisPoint
			else:
				pass
		
		if balanceOverCompletePath:
			reversePath = thisPath.copy()
			reversePath.reverse()
			reverseDotPoints, reverseTangentAngles = dotCoordsOnPath(reversePath, distanceBetweenDots)
			numberOfPoints = min(len(reverseDotPoints), len(dotPoints)-1)
			for i in range(numberOfPoints):
				factor = 1.0/numberOfPoints*i
				j = -1-i
				dotPoints[j] = interpolatePointPos(dotPoints[j], reverseDotPoints[i], factor)
				tangentAngles[j] = weightedAverageAngles(tangentAngles[j], reverseTangentAngles[i], factor)
			print("UPDATE")
		
		if distance(dotPoints[0], dotPoints[-1]) < 0.8: #closed path
			dotPoints.pop(-1)
			tangentAngles.pop(-1)
			
		return dotPoints, tangentAngles
	except Exception as e:
		import traceback
		print(traceback.format_exc())


@objc.python_method
def isSelected(thisPath):
	if thisPath:
		thisLayer = thisPath.parent
		if thisLayer:
			for thisNode in thisPath.nodes:
				if thisNode in thisLayer.selection:
					return True
	return False


@objc.python_method
def placeDots(thisLayer, useBackground, componentNameString, distanceBetweenDots, balanceOverCompletePath=False, selectionMatters=False, deleteComponents=False):
	try:
		# find out component offset:
		xOffsets, yOffsets = [], []
		componentAngles = []
		thisFont = thisLayer.parent.parent
		componentNames = [name.strip(" *") for name in componentNameString.split(",") if thisFont.glyphs[name.strip(" *")]]
		shouldUseMask = ["*" in name for name in componentNameString.split(",")]
		sourceComponents = [thisFont.glyphs[name] for name in componentNames]
		
		if sourceComponents:
			for sourceComponent in sourceComponents:
				sourceLayer = sourceComponent.layers[thisLayer.associatedMasterId]
				
				# if component has an origin anchor, record the offset:
				sourceAnchor = sourceLayer.anchors["origin"]
				if sourceAnchor:
					originPosition = sourceAnchor.position
				else:
					originPosition = NSPoint(0, 0)
				xOffsets.append(-originPosition.x)
				yOffsets.append(-originPosition.y)
				
				# if component has an orientation anchor, make note of it:
				orientationAnchor = sourceLayer.anchors["orientation"]
				if orientationAnchor:
					angle = getOrientationAngle(originPosition, orientationAnchor.position)
					componentAngles.append(angle)
				else:
					componentAngles.append(None)
		
			# use background if specified:
			if useBackground:
				sourceLayer = thisLayer.background
			else:
				sourceLayer = thisLayer
			
			# selection only matters if source layer actually has a selection:
			if not sourceLayer.selection:
				selectionMatters = False
			
			# delete existing components first
			selectedPathHashes = []
			if deleteComponents:
				if not selectionMatters:
					if not deleteAllComponents(thisLayer):
						print("-- Error deleting previously placed components.")
				else:
					for thisPath in sourceLayer.paths:
						if isSelected(thisPath) or not selectionMatters:
							selectedPathHashes.append(thisPath.__hash__())
					if selectedPathHashes:
						for i in reversed(range(len(thisLayer.shapes))):
							if not isinstance(thisLayer.shapes[i], GSComponent):
								continue
							currComp = thisLayer.components[i]
							pathHash = currComp.userDataForKey_("originPath")
							if pathHash and pathHash in selectedPathHashes:
								del thisLayer.shapes[i]
			
			for thisPath in sourceLayer.paths:
				pathHash = thisPath.__hash__()
				pathIsSelected = pathHash in selectedPathHashes
				if not selectionMatters or pathIsSelected:
					dotsOnPath, anglesOnPath = dotCoordsOnPath(thisPath, distanceBetweenDots, balanceOverCompletePath)
					for i, thisPoint in enumerate(dotsOnPath):
						j = i % len(sourceComponents)
						newComp = GSComponent(
							componentNames[j],
							NSPoint(
								thisPoint.x + xOffsets[j],
								thisPoint.y + yOffsets[j],
							),
							)
						newComp.alignment = -1
						if shouldUseMask[j]:
							newComp.attributes["mask"] = 1
						
						if componentAngles[j] is not None:
							rotateAngle = anglesOnPath[i] - componentAngles[j]
							newComp.applyTransform(createTransformMatrix(thisPoint, rotateAngle))
						
						thisLayer.addShape_(newComp)
						newComp.setUserData_forKey_(pathHash, "originPath")
			return True
		else:
			return False
		
	except Exception as e:
		print("Stitcher Error:\n%s"%e)
		import traceback
		print(traceback.format_exc())
		return False


@objc.python_method
def minimumOfOne(value):
	try:
		returnValue = float(value)
		if returnValue < 1.0:
			returnValue = 1.0
	except:
		returnValue = 1.0
		
	return returnValue


@objc.python_method
def process(thisLayer, deleteComponents, componentName, distanceBetweenDots, useBackground=True, balanceOverCompletePath=False, selectionMatters=False):
	try:
		if useBackground and len(thisLayer.paths) > 0:
			if thisLayer.className() == "GSBackgroundLayer":
				thisLayer = thisLayer.foreground()
			thisLayer.background.clear()
			for thisPath in thisLayer.paths:
				try:
					thisLayer.background.shapes.append(thisPath.copy())
				except:
					thisLayer.background.paths.append(thisPath.copy())
			
			try:
				for i in reversed(range(len(thisLayer.shapes))):
					shape = thisLayer.shapes[i]
					if type(shape) is GSPath:
						del thisLayer.shapes[i]
			except:
				thisLayer.paths = None
	
		if not placeDots(thisLayer, useBackground, componentName, distanceBetweenDots, balanceOverCompletePath, selectionMatters, deleteComponents):
			print("-- Could not place components at intervals of %.1f units." % distanceBetweenDots)
	except Exception as e:
		print("Stitcher Error:\n%s"%e)
		import traceback
		print(traceback.format_exc())


class Stitcher(FilterWithDialog):
	# Definitions of IBOutlets
	# The NSView object from the User Interface. Keep this here!
	dialog = objc.IBOutlet()
	
	# Text field in dialog
	intervalField = objc.IBOutlet()
	componentField = objc.IBOutlet()
	balanceCheckbox = objc.IBOutlet()
	useBackgroundCheckbox = objc.IBOutlet()
	
	prefID = "com.mekkablue.Stitcher"

	@objc.python_method
	def domain(self, prefName):
		prefName = prefName.strip().strip(".")
		return self.prefID + "." + prefName.strip()
	
	@objc.python_method
	def pref(self, prefName):
		prefDomain = self.domain(prefName)
		return Glyphs.defaults[prefDomain]
	
	@objc.python_method
	def setPref(self, prefName, prefValue):
		Glyphs.defaults[self.domain(prefName)] = prefValue

	@objc.python_method
	def settings(self):
		self.menuName = "Stitcher"
		
		# Word on Run Button (default: Apply)
		self.actionButtonLabel = "Stitch"
		
		# Load dialog from .nib (without .extension)
		self.loadNib('IBdialog', __file__)
	
	# On dialog show
	@objc.python_method
	def start(self):
		
		# Set default value
		Glyphs.registerDefault(self.domain('interval'), 100.0)
		Glyphs.registerDefault(self.domain('component'), "_circle")
		Glyphs.registerDefault(self.domain('balance'), 0)
		
		# Set value of text field
		self.intervalField.setStringValue_(self.pref('interval'))
		self.componentField.setStringValue_(self.pref('component').strip())
		self.balanceCheckbox.setIntValue_(bool(self.pref('balance')))
		
		# Set focus to text field
		self.intervalField.becomeFirstResponder()
		
	# Action triggered by UI
	@objc.IBAction
	def setInterval_(self, sender):
		# Store value coming in from dialog
		self.setPref('interval', sender.floatValue())
		self.update()

	# Action triggered by UI
	@objc.IBAction
	def setComponent_(self, sender):
		# Store value coming in from dialog
		self.setPref('component', sender.stringValue().strip())
		self.update()

	# Action triggered by UI
	@objc.IBAction
	def setBalance_(self, sender):
		# Store value coming in from dialog
		self.setPref('balance', sender.intValue())
		self.update()
	
	# Action triggered by UI
	@objc.IBAction
	def setUseBackground_(self, sender):
		# Store value coming in from dialog
		self.setPref('useBackground', sender.intValue())
		self.update()
	
	# Actual filter
	@objc.python_method
	def filter(self, layer, inEditView, customParameters):
		# Defaults:
		interval, component, balance, useBackground = 100.0, "_circle", False, True
		selectionMatters = False
		
		# Overwrite defaults:
		if 'interval' in customParameters:
			interval = customParameters['interval']
		else:
			interval = float(self.pref('interval'))
		
		if 'component' in customParameters:
			component = customParameters['component'].strip()
		else:
			component = self.pref('component').strip()
			
		if 'balance' in customParameters:
			balance = customParameters['balance']
		else:
			balance = self.pref('balance')
		
		try:
			# determine Font:
			if not customParameters:
				Font = Glyphs.font
			else:
				Font = layer.parent.parent
			
			if not Font:
				print("Stitcher Filter Error: could not determine font.")
			else:
				if component:
					componentNames = [name.strip(" *") for name in component.split(",") if Font.glyphs[name.strip(" *")]]
					componentGlyphs = [Font.glyphs[name] for name in componentNames]
					if not componentGlyphs:
						print("Stitcher Filter Error: required components not in font:", component)
					else:
						if interval and component:
							# settings:
							distanceBetweenDots = minimumOfOne(interval)
							balanceOverCompletePath = bool(balance)
							if customParameters:
								useBackground = False
								deleteComponents = False
								selectedLayers = (layer,)
							else:
								useBackground = bool(self.pref("useBackground"))
								deleteComponents = True
								selectedLayers = Font.selectedLayers
								if len(selectedLayers) == 1 and inEditView:
									selectionMatters = True
							
							# selection can only matter if only one glyph is open for editing:
							if len(selectedLayers) != 1:
								selectionMatters = False
								
							for thisLayer in selectedLayers:
								thisGlyph = thisLayer.parent
								if not thisGlyph.name in componentNames:
									process(
										thisLayer,
										deleteComponents,
										component,
										distanceBetweenDots,
										useBackground,
										balanceOverCompletePath,
										selectionMatters,
										)
						else:
							print("Stitcher Filter Input Error: need a valid (non-zero) interval, and a valid component name.")
							print("  interval: %f" % interval)
							print("  component name: %s" % component)
		except Exception as e:
			print("Stitcher Process Error:\n%s"%e)
			import traceback
			print(traceback.format_exc())
		
	@objc.python_method
	def generateCustomParameter(self):
		return "%s; component:%s; interval:%s; balance:%s" % (self.__class__.__name__, 
			self.pref('component'),
			self.pref('interval'),
			self.pref('balance'),
		)
	
	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
