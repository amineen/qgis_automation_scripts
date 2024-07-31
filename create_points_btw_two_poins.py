

import math
from qgis.core import (QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsDistanceArea, QgsWkbTypes)


point_layer = QgsProject.instance().mapLayersByName('mv_poles')[0]

# Ensure the layer is a point layer
if point_layer.geometryType() != QgsWkbTypes.PointGeometry:
    raise ValueError("The selected layer is not a point layer")

source_crs = point_layer.sourceCrs()
# Get all features from the point layer
features = point_layer.getFeatures()

num_features = point_layer.featureCount()

point_features = []
pole_coordinates = []
p1 = None
p2 = None
# Iterate over all features
for index, feature in enumerate(features):
    # End the loop if feature is the last item in the list by comparing the current index to the length of the list
    if index == num_features - 1:
        break
    p1 = feature
    # Get the next feature by using the fid of the current feature
    p2 = point_layer.getFeature(p1.id() + 1)

    if p1 is None or p2 is None:
        raise ValueError("One or more points not found in the layer")

    # Coordinate transformation
    utm_zone = math.floor((p1.geometry().asPoint().x() + 180) / 6) + 1
    utm_crs = QgsCoordinateReferenceSystem(f"EPSG:326{utm_zone:02d}")
    transform_to_utm = QgsCoordinateTransform(
        source_crs, utm_crs, QgsProject.instance())
    transform_to_src = QgsCoordinateTransform(
        utm_crs, source_crs, QgsProject.instance())

    p1_utm = transform_to_utm.transform(p1.geometry().asPoint())
    p2_utm = transform_to_utm.transform(p2.geometry().asPoint())

    # Calculate the slope
    x1, y1 = p1_utm.x(), p1_utm.y()
    x2, y2 = p2_utm.x(), p2_utm.y()
    slope = (y2 - y1) / (x2 - x1)

    # Create a QgsDistanceArea object
    distance_area = QgsDistanceArea()
    # Set the ellipsoid and source CRS (coordinate reference system)
    distance_area.setEllipsoid('WGS84')
    distance_area.setSourceCrs(QgsCoordinateReferenceSystem(
        4326), QgsProject.instance().transformContext())

    # Distance between points
    total_distance = distance_area.measureLine(
        p1.geometry().asPoint(), p2.geometry().asPoint())
    pole_number1 = p1['pole_number']
    pole_number2 = p2['pole_number']

    # remove first character from pole number and convert to integer
    pole_number1 = int(pole_number1[1:])
    pole_number2 = int(pole_number2[1:])

    # create the next pole number with the following format: P002, P003, P004, etc.
    pole_number = pole_number1 + 1

    # Calculate the number of points to be created between the two points
    number_of_points = pole_number2 - pole_number1-1

    # Calculate the distance between the two points
    d = total_distance / (number_of_points + 1)

    # Calculate Δx
    delta_xx = (d / math.sqrt(1 + slope**2))
    delta_x = delta_xx if x2 > x1 else -delta_xx

    # generate the new points for each number_of_points
    for i in range(number_of_points):
        # Calculate the x coordinate of the new point
        x = x1 + delta_x * (i + 1)
        # Calculate the y coordinate of the new point
        y = y1 + slope * delta_x * (i + 1)
        # Create a new QgsPointXY object
        point = QgsPointXY(x, y)
        # Transform the point back to the source CRS
        point = transform_to_src.transform(point)

        pole_number_txt = f"M{pole_number:03d}"

        # Create a new point feature
        point_feature = QgsFeature(point_layer.fields())
        point_feature.setGeometry(QgsGeometry.fromPointXY(point))

        # #set the pole number attribute
        point_feature.setAttribute('pole_number', pole_number_txt)
        point_feature.setAttribute('minigrid_id', 'Ntatumbila')
        point_feature.setAttribute('back_span', d)

        # get point x, y coordinates
        point_x = point.x()
        point_y = point.y()

        pole_coordinates.append(
            {'pole_number': pole_number_txt, 'x': point_x, 'y': point_y, 'span': d})

        # Add the new point to the list
        point_features.append(point_feature)
        pole_number += 1


# loop over list of pole_coordinates and print the pole number and coordinates
# for i in range(len(pole_coordinates)):
#     print(f"pole number: {pole_coordinates[i]['pole_number']}, x: {pole_coordinates[i]['x']}, y: {pole_coordinates[i]['y']}, span: {pole_coordinates[i]['span']}")

# loop through the new points and create a new feature for each one
for point_feature in point_features:
    # Add the new point feature to the point layer
    point_layer.dataProvider().addFeatures([point_feature])
    point_layer.updateExtents()
    point_layer.triggerRepaint()
