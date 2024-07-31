from qgis.core import QgsFeature, QgsGeometry, QgsVectorLayer, QgsProject, QgsField, QgsCoordinateTransform
from qgis.PyQt.QtCore import QVariant

# Replace with the name of your point layer
layer_name = "poles_nimba_county"

# Get the layer
layer = QgsProject.instance().mapLayersByName(layer_name)[0]

# Create a new line layer
line_layer = QgsVectorLayer(
    "LineString?crs=" + layer.crs().authid(), "lines_nimba_county", "memory")
provider = line_layer.dataProvider()
provider.addAttributes([QgsField("distance", QVariant.Double)])
line_layer.updateFields()

# Keep track of pairs for which we have drawn lines
drawn_pairs = set()

# Iterate through points in the layer
features = list(layer.getFeatures())
features2 = list(layer.getFeatures())
# declare a tuple to hold pair_ids
pair_ids = tuple()
for i, feature1 in enumerate(features):
    point1 = feature1.geometry().asPoint()
    min_distance = float('inf')
    nearest_point = None
    nearest_feature_id = None

    destination_crs = QgsProject.instance().crs().fromEpsgId(32629)

    # Get the CRS of the current layer
    source_crs = QgsProject.instance().crs()

    transform = QgsCoordinateTransform(
        source_crs, destination_crs, QgsProject.instance())

    previous_points = []

    # Find the nearest neighbor by calculating the distance to each other point
    f1_id = feature1.id()
    for j, feature2 in enumerate(features2):

        f2_id = feature2.id()
        if f2_id <= f1_id:
            continue
        point2 = feature2.geometry().asPoint()
        point1_transformed = transform.transform(point1)
        point2_transformed = transform.transform(point2)
        # distance = point1.distance(point2)
        distance = point1_transformed.distance(point2_transformed)

        if distance < min_distance:
            min_distance = distance
            nearest_point = point2
            nearest_feature_id = feature2.id()
            # features2.remove(feature2)
            pair_ids = tuple(sorted([feature1.id(), nearest_feature_id]))
            if pair_ids in drawn_pairs:
                # if feature1.id() in previous_points:
                continue

    # Create line between points
    if nearest_point:
        if min_distance > 300:
            continue
        line = QgsGeometry.fromPolylineXY([point1, nearest_point])
        line_feature = QgsFeature()
        line_feature.setGeometry(line)
        line_feature.setAttributes([min_distance])
        provider.addFeature(line_feature)
        drawn_pairs.add(pair_ids)  # Add this pair to the set of drawn pairs
        previous_points.append(feature1.id())

# Add the line layer to the map
QgsProject.instance().addMapLayer(line_layer)
