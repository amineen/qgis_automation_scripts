from qgis.core import QgsProject, QgsField, QgsExpression, QgsFeatureRequest
from qgis.PyQt.QtCore import QVariant

from math import degrees


layer_name = 'lv_lines_ntatumbila'
angle_field_name = 'line_angle'
layer = QgsProject.instance().mapLayersByName(layer_name)[0]

features = [feature for feature in layer.getFeatures()]
features.sort(key=lambda x: x['span_number'])

angles = {}

unique_branch_ids = set()
for feature in features:
    branch_id = feature['branch_id']
    unique_branch_ids.add(branch_id)

branches_ids = list(unique_branch_ids)
non_deadend_ids = list(filter(lambda b: b != 'deadend', branches_ids))

for branch_id in non_deadend_ids:
    branch_line_features = list(
        filter(lambda feature: feature['branch_id'] == branch_id, features))
    # Order by span_number
    # branch_line_features.sort(key=lambda x: x['span_number'])
    for index, feature in enumerate(branch_line_features):
        span_number = feature['span_number']

        line_start_point = feature.geometry().asPolyline()[0]
        line_end_point = feature.geometry().asPolyline()[1]
        # print(line)
        # # <---edit start here--->
        # line_start_point = line[0]
        # line_end_point = line[1]
        # get line azimuth
        line_azimuth = line_start_point.azimuth(line_end_point)

        # get next line using the span_number variable
        next_line_list = list(
            filter(lambda f: f['span_number'] == span_number + 1, features))

        next_line_start_point = next_line_list[0].geometry().asPolyline()[0]
        next_line_end_point = next_line_list[0].geometry().asPolyline()[1]
        # get next line azimuth
        next_line_azimuth = next_line_start_point.azimuth(next_line_end_point)
        # calculate angle
        diff_azimuth = line_azimuth - next_line_azimuth
        angle = diff_azimuth
        if angle > 180:
            angle -= 360
        elif angle < -180:
            angle += 360
        if (abs(angle)) < 1:
            angle = 0
        angle_txt = ''
        if (angle > 0):
            angle_txt = f'{round(abs(round(angle, 0)))}°L'
        elif (angle == 0):
            angle_txt = f'{round(abs(round(angle, 0)))}°'
        else:
            angle_txt = f'{round(abs(round(angle, 0)))}°R'

        print(f'{span_number} {angle_txt}')

        pole_number = feature['pole_number']
        angles[pole_number] = angle_txt

        # line_azimuth = feature['azimuth_line']
        # next_line_azimuth = feature['azimuth_next_line']
        # diff_azimuth = line_azimuth - next_line_azimuth
        # angle = degrees(diff_azimuth)
        # if angle > 180:
        #     angle -= 360
        # elif angle < -180:
        #     angle += 360
        # if(abs(angle)) <= 2:
        #     angle = 0
        # angle_txt = f'{round(abs(round(angle, 1)))}'
        # angles[back_span_pole] = angle_txt

fields = layer.fields()
if angle_field_name not in fields.names():
    layer.dataProvider().addAttributes(
        [QgsField(angle_field_name, QVariant.String, len=10)])
    layer.updateFields()
angle_field_index = layer.fields().indexFromName(angle_field_name)
attr_map = {}
for feature in features:
    pole_number = feature['pole_number']
    if pole_number in angles:
        attr_map[feature.id()] = {angle_field_index: angles[pole_number]}
    else:
        attr_map[feature.id()] = {angle_field_index: 'deadend'}

# print(attr_map)
layer.dataProvider().changeAttributeValues(attr_map)
