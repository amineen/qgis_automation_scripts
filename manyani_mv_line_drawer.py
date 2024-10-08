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


pointLayer = QgsProject.instance().mapLayersByName(
    'mv_control_poles')[0]

newPointLayer = QgsVectorLayer(
    'Point?crs=EPSG:4326', 'new_manyani_mv_pole_points', 'memory')

# create a memory layer to store lines
line_layer = QgsVectorLayer(
    "LineString?crs=epsg:4326", "manyani_mv_line_layer", "memory")
line_layer_dp = line_layer.dataProvider()
point_layer_dp = newPointLayer.dataProvider()
fields = QgsFields()
fields = QgsFields()
fields.append(QgsField('pole_number', QVariant.String))
fields.append(QgsField('number_of_connections', QVariant.Int))
fields.append(QgsField('back_span', QVariant.Double))
fields.append(QgsField('branch_id', QVariant.String))
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

# declare a dictionaries of QgsPoint objects
branch_points = {}

for index, feature in enumerate(features):

    if index == 0:
        # create a new point feature from feature
        new_feature = QgsFeature(fields)
        new_feature.setGeometry(feature.geometry())
        new_feature.setAttribute('pole_number', 'MV01')
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

    # print(f'x1: {x1}, y1: {y1}, x2: {x2}, y2: {y2}')

    if x2 == x1:
        slope = float('inf')
    else:
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
        totalDistance, 60, 115)

    if slope == float('inf'):
        d = distance
        delta_x = 0
    else:
        d = distance
        delta_xx = (d / math.sqrt(1 + slope**2))
        delta_x = delta_xx if x2 > x1 else -delta_xx

    # create a new point feature from connecting_cp and initialize a list of branch_points
    new_point = QgsPointXY(x1, y1)
    new_point = transformToSrc.transform(new_point)
    control_pole = feature['control_pole']
    cp_number = feature['connecting_cp']
    # create branch_points as list of dictionaries
    branch_id = f'{control_pole} - {cp_number}'
    branch_points[branch_id] = []
    branch_points[branch_id].append(
        {'pole_number': 'MV01', 'point': QgsPoint(new_point.x(), new_point.y())})
    for i in range(int(number_of_poles)):
        # Calculate the x coordinate of the new point
        x = x1 + delta_x * (i+1)
        # Calculate the y coordinate of the new point
        y = y1 + slope * delta_x * (i+1)
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
        pointFeature.setAttribute('pole_number', f'MV{pole_number:02d}')
        # Add the point feature to the list of point features
        pointFeatures.append(pointFeature)
        branch_points[branch_id].append(
            {'pole_number': f'MV{pole_number:02d}', 'point': QgsPoint(point.x(), point.y())})


# loop through the branch_points dictionary and loop through the list of points in each branch and create line between each pair of points
numbers: list[int] = []
for branch_id, points in branch_points.items():

    for i in range(len(points) - 1):
        # is this first dict item?
        if len(numbers) == 0:
            numbers.append(2)
        else:
            numbers.append(numbers[-1] + 1)

        current_number = numbers[-1]
        # Create a new QgsFeature object
        lineFeature = QgsFeature(fields)
        # Create a new QgsGeometry object
        point1 = points[i]['point']
        point2 = points[i+1]['point']
        # startPoint = QgsPointXY(point1.x(), point1.y())
        # endPoint = QgsPointXY(point2.x(), point2.y())
        pole_number = points[i+1]['pole_number']
        lineGeometry = QgsGeometry.fromPolyline([point1, point2])
        # Set the geometry of the feature
        lineFeature.setGeometry(lineGeometry)
        # Set the pole number attribute
        lineFeature.setAttribute('branch_id', branch_id)
        lineFeature.setAttribute('pole_number', f'MV{current_number:02d}')
        success = line_layer_dp.addFeature(lineFeature)
        # update pole_number in pointLayer with current_number base on the lineFeature end point
        # get point feature from pointFeatures list where pole_number == current_number and update the pole_number attribute
        point_feature = next(
            (feature for feature in pointFeatures if feature['pole_number'] == pole_number), None)
        if point_feature is not None:
            point_feature.setAttribute(
                'pole_number', f'MV{current_number:02d}')


newPointLayer.dataProvider().addFeatures(pointFeatures)
# Add the new point layer to the map
QgsProject.instance().addMapLayer(newPointLayer)

# Add the new line layer to the map
QgsProject.instance().addMapLayer(line_layer)
