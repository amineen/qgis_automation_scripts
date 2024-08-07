from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsSpatialIndex,
    QgsField, QgsVectorFileWriter, QgsCoordinateReferenceSystem, QgsFields, QgsWkbTypes
)
from PyQt5.QtCore import QVariant
import os

# Load the layers
poles_layer_name = 'lv_poles_ntatumbila'
structures_layer_name = 'recorded_structures'

# Check if layers exist
poles_layers = QgsProject.instance().mapLayersByName(poles_layer_name)
structures_layers = QgsProject.instance().mapLayersByName(structures_layer_name)

if not poles_layers or not structures_layers:
    raise ValueError(
        "One or both layers not found. Please check the layer names.")

poles_layer = poles_layers[0]
structures_layer = structures_layers[0]

# Create a temporary copy of the poles layer
temp_poles_layer_path = os.path.join(
    QgsProject.instance().homePath(), 'temp_poles_layer.shp')
QgsVectorFileWriter.writeAsVectorFormat(
    poles_layer, temp_poles_layer_path, "utf-8", poles_layer.crs(), "ESRI Shapefile")
temp_poles_layer = QgsVectorLayer(
    temp_poles_layer_path, "temp_poles_layer", "ogr")

# Ensure the CRS is WGS 84 (EPSG:4326)
crs_4326 = QgsCoordinateReferenceSystem("EPSG:4326")
if temp_poles_layer.crs() != crs_4326:
    temp_poles_layer.setCrs(crs_4326)

# Create a temporary layer for the buffers
buffer_layer_path = os.path.join(
    QgsProject.instance().homePath(), 'buffer_layer.shp')
buffer_fields = QgsFields()
buffer_fields.append(QgsField('id', QVariant.Int))
buffer_writer = QgsVectorFileWriter(
    buffer_layer_path, 'UTF-8', buffer_fields, QgsWkbTypes.Polygon, crs_4326, 'ESRI Shapefile')
buffer_layer = QgsVectorLayer(buffer_layer_path, 'buffer_layer', 'ogr')

# Create a spatial index for the structures layer
spatial_index = QgsSpatialIndex()
for structure in structures_layer.getFeatures():
    spatial_index.insertFeature(structure)

# Add a new field to the temporary poles layer for storing the count
if 'structure_count' not in [field.name() for field in temp_poles_layer.fields()]:
    temp_poles_layer.startEditing()
    temp_poles_layer.dataProvider().addAttributes(
        [QgsField('structure_count', QVariant.Int)])
    temp_poles_layer.updateFields()
    temp_poles_layer.commitChanges()

# Calculate the count of structures within a 30m radius for each pole
temp_poles_layer.startEditing()

for pole in temp_poles_layer.getFeatures():
    pole_geom = pole.geometry()
    buffer_geom = pole_geom.buffer(30, 5)  # Create a buffer of 30 meters

    # Add the buffer to the buffer layer
    buffer_feature = QgsFeature(buffer_fields)
    buffer_feature.setGeometry(buffer_geom)
    buffer_feature.setAttribute('id', pole.id())
    buffer_writer.addFeature(buffer_feature)

    ids_within_buffer = spatial_index.intersects(buffer_geom.boundingBox())

    count = 0
    for id in ids_within_buffer:
        structure = structures_layer.getFeature(id)
        if buffer_geom.contains(structure.geometry()):
            count += 1

    # Debug print statements to verify
    print(f"Pole ID: {pole.id()}")
    print(f"Buffer: {buffer_geom.asWkt()}")
    print(
        f"Structures within buffer: {len(ids_within_buffer)}, Count: {count}")
    for id in ids_within_buffer:
        structure = structures_layer.getFeature(id)
        print(
            f"  Structure ID: {id}, Geometry: {structure.geometry().asWkt()}")

    # Update the count field
    temp_poles_layer.changeAttributeValue(
        pole.id(), temp_poles_layer.fields().indexFromName('structure_count'), count)

# Commit the changes
temp_poles_layer.commitChanges()
del buffer_writer  # Close the writer to flush features to disk

# Add the temporary layers to the QGIS project
QgsProject.instance().addMapLayer(temp_poles_layer)
QgsProject.instance().addMapLayer(buffer_layer)

print("Counts updated successfully and buffers created.")
