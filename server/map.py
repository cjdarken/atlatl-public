import math
import json

class MapData:
    def __init__(self):
        self.edgeIndex = {}  # Values are indexes into map.edges
        self.hexIndex = {} # Values are Hex objects
        self.pathIndex = {} # Values are Path objects
    def hexes(self):
        return self.hexIndex.values()
    def edges(self):
        return self.edgeIndex.values()
    def getCityHexes(self):
        result = []
        for hexId in self.hexIndex:
            hex = self.hexIndex[hexId]
            if hex.terrain == "urban":
                result.append(hex)
        return result           
    def getDimensions(self):
        if not hasattr(self,'width'):
            width = 0
            height = 0
            for id in self.hexIndex:
                hex = self.hexIndex[id]
                if hex.x_offset + 1 > width:
                    width = hex.x_offset + 1
                if hex.y_offset + 1 > height:
                    height = hex.y_offset + 1
            self.width, self.height = width, height
        return {"width":self.width, "height":self.height} 
    def hasSetupHexes(self):
        for hex in self.hexes():
            if hex.setup:
                return True
        return False
    def getSetupHexes(self,faction):
        value = "setup-type-"+faction
        return [hex for hex in self.hexes() if hex.setup==value]
    def createHexGrid(self,rows,cols):
            self.edgeIndex = {} # Point pairs to edges
            terrain = "clear"
            for r in range(rows):
                for c in range(cols):
                    Hex(c,r,terrain,self)
    def toString(self):
        return json.dumps( self.toPortable() )
    def toPortable(self):
        portable_hexes = []
        for hex in self.hexes():
            portable_hexes.append( hex.portableCopy() )
        portable_paths = []
        for path_id in self.pathIndex:
            path = self.pathIndex[path_id]
            portable_paths.append( path.portableCopy() )
        portable_edges = []
        for edge in self.edges():
            portable_edges.append( edge.toPortable() )
        return {"hexes":portable_hexes, "edges":portable_edges, "paths":portable_paths}

vertexOffsets = ( (-1,-1), (1,-1), (2,0), (1,1), (-1,1), (-2,0) ) # grid
    
class Edge:
    def __init__(self, xa_grid, ya_grid, xb_grid, yb_grid, type, mapData):
        edgeIndex = mapData.edgeIndex
        self.id = f'edge-{xa_grid}-{ya_grid}-{xb_grid}-{yb_grid}'
        self.xa_grid = xa_grid
        self.xb_grid = xb_grid
        self.ya_grid = ya_grid
        self.yb_grid = yb_grid
        self.type = type
        edgeIndex[self.id] = self
    def toPortable(self):
        copy = {}
        copy["id"] = self.id
        copy["xa_grid"] = self.xa_grid
        copy["xb_grid"] = self.xb_grid
        copy["ya_grid"] = self.ya_grid
        copy["yb_grid"] = self.yb_grid
        copy["type"] = self.type
        return copy

def edgeFromGenericObject(obj, mapData):
    edgeIndex = mapData.edgeIndex
    edge = Edge(obj['xa_grid'], obj['ya_grid'], obj['xb_grid'], obj['yb_grid'], obj['type'], mapData)
    edgeIndex[edge.id] = edge
    return edge
    
def offsetToGridCenters(x_off, y_off):
    # Vertical spacing sqrt(3)u and horizontal spacing u
    x_grid = 2 + x_off * 3
    y_grid = 2 + y_off * 2 + (x_off%2)
    return (x_grid, y_grid)
    
def getEdgeFromEndpoints(a,b,mapData):
    edgeIndex = mapData.edgeIndex
    keyAB = f"edge-{a['x']}-{a['y']}-{b['x']}-{b['y']}"
    keyBA = f"edge-${a['x']}-{a['y']}-{b['x']}-{b['y']}"
    edgeAB = edgeIndex.get(keyAB,None)
    edgeBA = edgeIndex.get(keyBA,None)
    if edgeAB != None:
        return edgeAB
    if edgeBA != None:
        return edgeBA
    return None

class Hex:
    def __init__(self,x_offset,y_offset,terrain,mapData):
        hexIndex = mapData.hexIndex
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.setup = None
        self.terrain = terrain
        self.x_grid, self.y_grid = offsetToGridCenters(x_offset,y_offset)
        self.edges = []
        self.addEdges(mapData) # Sets this.edges
        self.paths = [None,None,None,None,None,None]
        self.id = f'hex-{self.x_offset}-{self.y_offset}'
        hexIndex[self.id] = self 
    def getPoints(self, mapData):
        points = []
        for i in range(6):
            x = self.x_grid + vertexOffsets[i][0]
            y = self.y_grid + vertexOffsets[i][1]
            points.append( {'x':x, 'y':y} )
        return points
    def addEdges(self, mapData):
        points = self.getPoints(mapData)
        for i in range(6):
            j = (i+1)%6
            a = points[i]
            b = points[j]
            edge = getEdgeFromEndpoints(a,b,mapData)
            if edge==None:
                edge = Edge(a['x'],a['y'],b['x'],b['y'],"normal",mapData)
            self.edges.append( edge ) 
    def portableCopy(self):
        copy = {}
        copy["x_offset"] = self.x_offset
        copy["y_offset"] = self.y_offset
        copy["terrain"] = self.terrain
        copy["x_grid"] = self.x_grid
        copy["y_grid"] = self.y_grid
        copy["setup"] = self.setup
        # Replace edge objects by their unique IDs and omit paths
        copy["edges"] = []
        for edge in self.edges:
            copy["edges"].append( edge.id )
        return copy

    
def hexFromGenericObject(obj, mapData):
    hex = Hex(obj['x_offset'], obj['y_offset'], obj['terrain'], mapData)
    hex.setup = obj['setup']
    return hex
    
class Path:
    def __init__(self, hexA, hexB, type, mapData):
        pathIndex = mapData.pathIndex
        self.id = f'path-{hexA.id}-{hexB.id}'
        self.hexA = hexA
        self.hexB = hexB
        self.type = type
        pathIndex[self.id] = self
    def portableCopy(self):
        copy = {}
        copy.id = self.id
        copy.hexA = self.hexA.id
        copy.hexB = self.hexB.id
        copy.type = self.type
        return copy
        
# Neighbor locations in offset coordinates
oddXOffsets = ( (0,-1), (1,0), (1,1), (0,1), (-1,1), (-1,0) )
evenXOffsets = ( (0,-1), (1,-1), (1,0), (0,1), (-1,0), (-1,-1) )

def getNeighborHex(hex, mapData, direction):
    if hex.x_offset%2:
        offsets = oddXOffsets
    else:
        offsets = evenXOffsets
    offset = offsets[direction]
    x = hex.x_offset + offset[0]
    y = hex.y_offset + offset[1]
    id = f'hex-{x}-{y}'
    neigh = mapData.hexIndex.get(id,None)
    return neigh

def getNeighborHexes(hex, mapData):
    neighbors = []
    for dir in range(6):
        neigh = getNeighborHex(hex, mapData, dir)
        if neigh:
            neighbors.append(neigh)
    return neighbors
        
def directionFrom(hexA, hexB):
    global oddXOffsets, evenXOffsets
    xa = hexA.x_offset
    xb = hexB.x_offset
    ya = hexA.y_offset
    yb = hexB.y_offset
    offsets = evenXOffsets
    if hexA.x_offset%2:
        offsets = oddXOffsets
    for i in range(6):
        if xa + offsets[i][0] == xb and ya + offsets[i][1] == yb:
            return i
    return None
    
# def pathFromGenericObject(obj, mapData):
#     pathIndex = mapData.pathIndex
#     hexA = hexIndex[obj['hexA']]
#     hexB = hexIndex[obj['hexB']]
#     path = Path(hexA, hexB, obj['type'], mapData)
#     dir = directionFrom(hexA, hexB)
#     hexA.paths[dir] = path
#     hexB.paths[(dir+3)%6] = path
#     pathIndex[path.id] = path

def fromPortable(obj, mapData):
    mapData.edgeIndex = {}
    mapData.hexIndex = {}
    for edge_obj in obj['edges']:
        edgeFromGenericObject(edge_obj, mapData)
    for hex_obj in obj['hexes']:
        hexFromGenericObject(hex_obj, mapData)
    # for path_obj in obj['paths']:
    #     pathFromGenericObject(path_obj, mapData) # Sets paths

SQRT3 = math.sqrt(3)
        
def gridDistance(xA,yA,xB,yB):
    # Inputs are coordinates from a inhomogeneous rectangular grid, hex.x_grid and hex.y_grid
    # Returns Euclidean distance in units of hex width
    dx = (xB-xA)/6*SQRT3
    dy = (yB-yA)/2
    return math.sqrt( dx*dx + dy*dy )

def offsetToCube(col,row):
    q = col
    r = -(col//2)+row
    s = -(q+r)
    return q,r,s

def cubeToOffset(q,r,s):
    col = q
    row = r + col//2
    return col,row

def hexDistance(xA,yA,xB,yB):
    # Inputs are offset coordinates, i.e. hex column (x_offset) and row (y_offset)
    q1,r1,s1 = offsetToCube(xA,yA)
    q2,r2,s2 = offsetToCube(xB,yB)
    return max(abs(q2-q1),abs(r2-r1),abs(s2-s1))