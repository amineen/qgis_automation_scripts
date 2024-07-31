import math
from qgis.core import (QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsFeatureRequest, QgsFields, QgsField,
                       QgsFeature, QgsGeometry, QgsPointXY, QgsPoint, QgsProject, QgsDistanceArea, QgsWkbTypes, QgsVectorLayer)

from PyQt5.QtCore import QVariant


def calculate_points_distance(totalDistance: float, min_distance=35, max_distance=55):

    if totalDistance < max_distance:
        # If totalDistance is less than min_distance,
        # you cannot place any point between
        return 1, totalDistance

    # Calculate the maximum number of intervals (of 55m) that fit in the total distance
    number_of_points: int = totalDistance // max_distance

    # Calculate the remaining distance after using number_of_points
    remaining_distance = totalDistance % max_distance

    if remaining_distance > 0:
        number_of_points += 1

    distance_between_points = totalDistance / number_of_points

    return number_of_points, distance_between_points


pointLayer = QgsProject.instance().mapLayersByName('lv_poles_nalusanga')[0]

newPointLayer = QgsVectorLayer(
    'Point?crs=EPSG:4326', 'new_pole_points', 'memory')

# create a memory layer to store lines
line_layer = QgsVectorLayer("LineString?crs=epsg:4326", "line_layer", "memory")
line_layer_dp = line_layer.dataProvider()
point_layer_dp = newPointLayer.dataProvider()
fields = QgsFields()
fields = QgsFields()
fields.append(QgsField('pole_number', QVariant.String))
fields.append(QgsField('number_of_connections', QVariant.Int))
fields.append(QgsField('back_span', QVariant.Double))
point_layer_dp.addAttributes(fields)
newPointLayer.updateFields()

line_layer_dp.addAttributes(fields)
line_layer.updateFields()


# Ensure the layer is a point layer
if pointLayer.geometryType() != QgsWkbTypes.PointGeometry:
    raise ValueError('The selected layer is not a point layer')

sourceCrs = pointLayer.sourceCrs()

# Get all features from the point layer
features = pointLayer.getFeatures()

numFeatures = pointLayer.featureCount()

pointFeatures = []
poleCoordinates = []
poleNumbers: list[int] = []

for index, feature in enumerate(features):

    if index == 0:
        # create a new point feature from feature
        new_feature = QgsFeature(fields)
        new_feature.setGeometry(feature.geometry())
        new_feature.setAttribute('pole_number', 'LV01')
        pointFeatures.append(new_feature)
        poleNumbers.append(1)
        continue

    field_name = 'connecting_cp'
    expression = f'"control_pole" = \'{feature[field_name]}\''
    request = QgsFeatureRequest().setFilterExpression(expression)
    all_connecting_cps = pointLayer.getFeatures(request)
    connecting_cp = next(all_connecting_cps, None)

    if connecting_cp is None:
        print(
            f'WARNING: No connecting point found for {feature["control_pole"]}!')
        continue

    # print(f'{feature["control_pole"]} -> {connecting_cp["control_pole"]}')

    # Coordinate transformation
    utm_zone = math.floor((feature.geometry().asPoint().x() + 180) / 6) + 1
    utmCrs = QgsCoordinateReferenceSystem(f'EPSG:326{utm_zone:02d}')
    transformToUtm = QgsCoordinateTransform(
        sourceCrs, utmCrs, QgsProject.instance())
    transformToSrc = QgsCoordinateTransform(
        utmCrs, sourceCrs, QgsProject.instance())

    featureUtm = transformToUtm.transform(feature.geometry().asPoint())
    connectingCpUtm = transformToUtm.transform(
        connecting_cp.geometry().asPoint())

    # Calculate the slope

    x1, y1 = connectingCpUtm.x(), connectingCpUtm.y()
    x2, y2 = featureUtm.x(), featureUtm.y()
    slope = (y2 - y1) / (x2 - x1)

    # Create a QgsDistanceArea object
    distanceArea = QgsDistanceArea()
    # Set the ellipsoid and source CRS (coordinate reference system)
    distanceArea.setEllipsoid('WGS84')
    distanceArea.setSourceCrs(QgsCoordinateReferenceSystem(
        4326), QgsProject.instance().transformContext())

    # Distance between points
    totalDistance = distanceArea.measureLine(
        feature.geometry().asPoint(), connecting_cp.geometry().asPoint())

    number_of_poles, distance = calculate_points_distance(
        totalDistance, 35, 56)

    d = distance

    # Calculate Δx
    delta_xx = (d / math.sqrt(1 + slope**2))
    delta_x = delta_xx if x2 > x1 else -delta_xx

    branch_points = []
    for i in range(int(number_of_poles) + 1):
        # Calculate the x coordinate of the new point
        x = x1 + delta_x * (i)
        # Calculate the y coordinate of the new point
        y = y1 + slope * delta_x * (i)
        # Create a new QgsPointXY object
        point = QgsPointXY(x, y)
        # Transform the point back to the source CRS
        point = transformToSrc.transform(point)
        # Create a new QgsFeature object
        pointFeature = QgsFeature(fields)

        pointFeature.setGeometry(QgsGeometry.fromPointXY(point))
        # Get the last pole number in pole_numbers and increment it by 1
        pole_number = poleNumbers[-1] + 1
        # Add the pole number to the pole_numbers list
        poleNumbers.append(pole_number)
        # Set the pole number attribute
        pointFeature.setAttribute('pole_number', f'LV{pole_number:02d}')
        # Add the point feature to the list of point features
        pointFeatures.append(pointFeature)
        branch_points.append(QgsPoint(point.x(), point.y()))
    line_feature = QgsFeature()
    line_feature.setGeometry(QgsGeometry.fromPolyline(branch_points))
    success = line_layer_dp.addFeature(line_feature)

    # create a new point layer and add the point features to it

newPointLayer.dataProvider().addFeatures(pointFeatures)
# Add the new point layer to the map
QgsProject.instance().addMapLayer(newPointLayer)


# Add the new line layer to the map
QgsProject.instance().addMapLayer(line_layer)
