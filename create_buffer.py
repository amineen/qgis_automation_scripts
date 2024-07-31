from qgis.core import QgsProject
from qgis.analysis import QgsNativeAlgorithms
import processing
from processing.core.Processing import Processing

Processing.initialize()
QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

# Load the point layer
pointLayer = QgsProject.instance().mapLayersByName('lv_poles_nalusanga')[0]

# Generate a buffer around each point
buffer_parameters = {"INPUT": pointLayer,
                     "DISTANCE": 30,
                     "OUTPUT": 'memory:'}
buffered = processing.run("native:buffer", buffer_parameters)['OUTPUT']

# Generate Voronoi Polygons based on original point layer
voronoi_parameters = {"INPUT": pointLayer,
                      "BUFFER": 0.1,
                      "OUTPUT": 'memory:'}
voronoi_layer = processing.run(
    "qgis:voronoipolygons", voronoi_parameters)['OUTPUT']

# Clip the Voronoi polygons with the buffer layer
clip_parameters = {"INPUT": voronoi_layer,
                   "OVERLAY": buffered,
                   "OUTPUT": 'memory:'}
clipped_voronoi = processing.run("qgis:clip", clip_parameters)['OUTPUT']

# Add the clipped voronoi layer to the map
QgsProject.instance().addMapLayer(clipped_voronoi)
