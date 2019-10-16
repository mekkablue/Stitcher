# encoding: utf-8

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
import math

def deleteAllComponents( thisLayer ):
	try:
		# print "-- Deleting %i existing components." % ( len(thisLayer.components) ) #DEBUG
		while len(thisLayer.components) > 0:
			# print "  Deleting component", thisLayer.components[0].componentName
			del thisLayer.components[0]
		
		return True
		
	except Exception as e:
		print traceback.format_exc()
		return False

def bezier( A, B, C, D, t ):
	x1, y1 = A.x, A.y
	x2, y2 = B.x, B.y
	x3, y3 = C.x, C.y
	x4, y4 = D.x, D.y
	
	x = x1*(1-t)**3 + x2*3*t*(1-t)**2 + x3*3*t**2*(1-t) + x4*t**3
	y = y1*(1-t)**3 + y2*3*t*(1-t)**2 + y3*3*t**2*(1-t) + y4*t**3

	return x, y

def distance( node1, node2 ):
	return math.hypot( node1.x - node2.x, node1.y - node2.y )

def segmentsForPath( p ):
	segments=[]
	currentSegment=[]
	pathlength = len(p.nodes)
	for i,n in enumerate(p.nodes):
		currentSegment.append(n.position)
		if i>0 and n.type != GSOFFCURVE:
			offset = len(currentSegment)
			if not offset in (2,4):
				firstPoint = p.nodes[(i-offset)%pathlength].position
				currentSegment.insert(0, firstPoint)
			segments.append( tuple(currentSegment) )
			currentSegment=[]
	return segments
	

def getFineGrainPointsForPath( thisPath, distanceBetweenDots ):
	try:
		layerCoords = [ ]
		pathSegments = segmentsForPath( thisPath )
	
		for thisSegment in pathSegments:
		
			if len( thisSegment ) == 2:
				# straight line:
				beginPoint = thisSegment[0]
				endPoint   = thisSegment[1]
			
				dotsPerSegment = int( ( distance( beginPoint, endPoint ) / distanceBetweenDots ) * 11 )
			
				for i in range( dotsPerSegment ):
					x = float( endPoint.x * i ) / dotsPerSegment + float( beginPoint.x * ( dotsPerSegment-i ) ) / dotsPerSegment
					y = float( endPoint.y * i ) / dotsPerSegment + float( beginPoint.y * ( dotsPerSegment-i ) ) / dotsPerSegment
					layerCoords += [ NSPoint( x, y ) ]
				
			elif len( thisSegment ) == 4:
				# curved segment:
				bezierPointA = thisSegment[0]
				bezierPointB = thisSegment[1]
				bezierPointC = thisSegment[2]
				bezierPointD = thisSegment[3]
			
				bezierLength = distance( bezierPointA, bezierPointB ) + distance( bezierPointB, bezierPointC ) + distance( bezierPointC, bezierPointD ) # very rough approximation, up to 11% too long
				dotsPerSegment = int( ( bezierLength / distanceBetweenDots ) * 10 )
			
				for i in range( 1, dotsPerSegment ):
					t = float( i ) / float( dotsPerSegment )
					x, y = bezier( bezierPointA, bezierPointB, bezierPointC, bezierPointD, t )
					layerCoords += [ NSPoint( x, y ) ]
			
				layerCoords += [ NSPoint( bezierPointD.x, bezierPointD.y ) ]
	
		return layerCoords
	except Exception as e:
		print "Stitcher Error:\n%s"%e
		import traceback
		print traceback.format_exc()

def interpolatePointPos( p1, p2, factor ):
	factor = factor % 1.0
	x = p1.x * factor + p2.x * (1.0-factor)
	y = p1.y * factor + p2.y * (1.0-factor)
	return NSPoint(x,y)

def dotCoordsOnPath( thisPath, distanceBetweenDots, balanceOverCompletePath=False ):
	try:
		dotPoints = [ thisPath.nodes[0] ]
		fineGrainPoints = getFineGrainPointsForPath( thisPath, distanceBetweenDots )
	
		myLastPoint = dotPoints[-1]
	
		for thisPoint in fineGrainPoints:
			if distance( myLastPoint, thisPoint ) >= distanceBetweenDots:
				dotPoints += [thisPoint]
				myLastPoint = thisPoint
			else:
				pass
		
		if balanceOverCompletePath:
			reversePath = thisPath.copy()
			reversePath.reverse()
			reverseDotPoints = dotCoordsOnPath( reversePath, distanceBetweenDots )
			numberOfPoints = min( len(reverseDotPoints), len(dotPoints)-1 )
			for i in range(numberOfPoints):
				factor = 1.0/numberOfPoints*i
				j = -1-i
				newPos = interpolatePointPos( dotPoints[j], reverseDotPoints[i], factor )
				dotPoints[j] = newPos
	
		return dotPoints
	except Exception as e:
		print traceback.format_exc()

def placeDots( thisLayer, useBackground, componentName, distanceBetweenDots, balanceOverCompletePath=False ):
	try:
		# find out component offset:
		xOffset = 0.0
		yOffset = 0.0
		Font = thisLayer.parent.parent
		FontMasterID = thisLayer.associatedMasterId
		sourceComponent = Font.glyphs[ componentName ]
		
		if sourceComponent:
			try:
				sourceAnchor = sourceComponent.layers[thisLayer.associatedMasterId].anchors["origin"]
				xOffset, yOffset = -sourceAnchor.position.x, -sourceAnchor.position.y
			except:
				pass
				#print "-- Note: no origin anchor in '%s'." % ( componentName )
		
			# use background if specified:
			if useBackground:
				sourceLayer = thisLayer.background
			else:
				sourceLayer = thisLayer
		
			for thisPath in sourceLayer.paths:
				for thisPoint in dotCoordsOnPath( thisPath, distanceBetweenDots, balanceOverCompletePath ):
					newComp = GSComponent( componentName, NSPoint( thisPoint.x + xOffset, thisPoint.y + yOffset ) )
					newComp.alignment = -1
					thisLayer.addComponent_( newComp )
				
			return True
		else:
			return False
		
	except Exception as e:
		print "Stitcher Error:\n%s"%e
		import traceback
		print traceback.format_exc()
		return False

def minimumOfOne( value ):
	try:
		returnValue = float( value )
		if returnValue < 1.0:
			returnValue = 1.0
	except:
		returnValue = 1.0
		
	return returnValue

def process( thisLayer, deleteComponents, componentName, distanceBetweenDots, useBackground=True, balanceOverCompletePath=False ):
	try:
		if deleteComponents:
			if not deleteAllComponents( thisLayer ):
				print "-- Error deleting previously placed components."
	
		if useBackground and len( thisLayer.paths ) > 0:
			if thisLayer.className() == "GSBackgroundLayer":
				thisLayer = thisLayer.foreground()
			thisLayer.background.clear()
			for thisPath in thisLayer.paths:
				thisLayer.background.paths.append( thisPath.copy() )
		
			thisLayer.paths = []
	
		if not placeDots( thisLayer, useBackground, componentName, distanceBetweenDots, balanceOverCompletePath ):
			print "-- Could not place components at intervals of %.1f units." % distanceBetweenDots
	except Exception as e:
		print "Stitcher Error:\n%s"%e
		import traceback
		print traceback.format_exc()

class Stitcher(FilterWithDialog):
	
	# Definitions of IBOutlets
	
	# The NSView object from the User Interface. Keep this here!
	dialog = objc.IBOutlet()
	
	# Text field in dialog
	intervalField = objc.IBOutlet()
	componentField = objc.IBOutlet()
	balanceCheckbox = objc.IBOutlet()
	useBackgroundCheckbox = objc.IBOutlet()
	
	def settings(self):
		self.menuName = "Stitcher"
		
		# Word on Run Button (default: Apply)
		self.actionButtonLabel = "Stitch"
		
		# Load dialog from .nib (without .extension)
		self.loadNib('IBdialog', __file__)
	
	# On dialog show
	def start(self):
		
		# Set default value
		Glyphs.registerDefault( 'com.mekkablue.Stitcher.interval', 100.0 )
		Glyphs.registerDefault( 'com.mekkablue.Stitcher.component', "_circle" )
		
		# Set value of text field
		self.intervalField.setStringValue_( Glyphs.defaults['com.mekkablue.Stitcher.interval'] )
		self.componentField.setStringValue_( Glyphs.defaults['com.mekkablue.Stitcher.component'].strip() )
		self.balanceCheckbox.setIntValue_( int(Glyphs.defaults['com.mekkablue.Stitcher.balance']) )
		
		# Set focus to text field
		self.intervalField.becomeFirstResponder()
		
	# Action triggered by UI
	@objc.IBAction
	def setInterval_( self, sender ):
		# Store value coming in from dialog
		Glyphs.defaults['com.mekkablue.Stitcher.interval'] = sender.floatValue()
		self.update()

	# Action triggered by UI
	@objc.IBAction
	def setComponent_( self, sender ):
		# Store value coming in from dialog
		Glyphs.defaults['com.mekkablue.Stitcher.component'] = sender.stringValue().strip()
		self.update()

	# Action triggered by UI
	@objc.IBAction
	def setBalance_( self, sender ):
		# Store value coming in from dialog
		Glyphs.defaults['com.mekkablue.Stitcher.balance'] = sender.intValue()
		self.update()
	
	# Action triggered by UI
	@objc.IBAction
	def setUseBackground_( self, sender ):
		# Store value coming in from dialog
		Glyphs.defaults['com.mekkablue.Stitcher.useBackground'] = sender.intValue()
		self.update()
	
	# Actual filter
	def filter(self, layer, inEditView, customParameters):
		# Defaults:
		interval, component, balance, useBackground = 100.0, "_circle", False, True
		
		# Overwrite defaults:
		if customParameters.has_key('interval'):
			interval = customParameters['interval']
		else:
			interval = float(Glyphs.defaults['com.mekkablue.Stitcher.interval'])
		
		if customParameters.has_key('component'):
			component = customParameters['component'].strip()
		else:
			component = Glyphs.defaults['com.mekkablue.Stitcher.component'].strip()
			
		if customParameters.has_key('balance'):
			balance = customParameters['balance']
		else:
			balance = Glyphs.defaults['com.mekkablue.Stitcher.balance']
		
		try:
			# determine Font:
			if not customParameters:
				Font = Glyphs.font
			else:
				Font = layer.parent.parent
			
			if not Font:
				print "Stitcher Filter Error: could not determine font."
			else:
				if component:
					componentGlyph = Font.glyphs[component]
					if not componentGlyph:
						print "Stitcher Filter Error: required component '%s' not in font." % component
					else:
						if interval and component:
							# settings:
							componentName = component
							distanceBetweenDots = minimumOfOne( interval )
							balanceOverCompletePath = bool( Glyphs.defaults["com.mekkablue.Stitcher.balance"] )
							if customParameters:
								useBackground = False
								deleteComponents = False
								selectedLayers = (layer,)
							else:
								useBackground = bool( Glyphs.defaults["com.mekkablue.Stitcher.useBackground"] )
								deleteComponents = True
								selectedLayers = Font.selectedLayers
		
							for thisLayer in selectedLayers:
								thisGlyph = thisLayer.parent
								if thisGlyph.name != componentName:
									process( thisLayer, deleteComponents, componentName, distanceBetweenDots, useBackground, balanceOverCompletePath )
						else:
							print "Stitcher Filter Input Error: need a valid (non-zero) interval, and a valid component name."
							print "  interval: %f" % interval
							print "  component name: %s" % component
		except Exception as e:
			print "Stitcher Process Error:\n%s"%e
			import traceback
			print traceback.format_exc()
		
	
	def generateCustomParameter( self ):
		return "%s; component:%s; interval:%s; balance:%s" % ( self.__class__.__name__, 
			Glyphs.defaults['com.mekkablue.Stitcher.component'],
			Glyphs.defaults['com.mekkablue.Stitcher.interval'],
			Glyphs.defaults['com.mekkablue.Stitcher.balance'],
		)
	
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__