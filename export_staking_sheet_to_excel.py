import pandas as pd
from qgis.core import QgsProject, QgsFeatureRequest
from datetime import datetime
import os

def string_to_float(s):
    try:
        return float(s)
    except ValueError:
        return s

layer_name = 'lv_poles - design_grid_extension'
#layer_name = 'mv_poles'


current_timestamp = datetime.now()
output_excel_file = f'{str(current_timestamp).replace(":", "-")}_{layer_name}.xlsx'

table_headers = {'pole_number':'Pole Number', 'latitude': 'Latitude', 'longitude': 'Longitude', 
'height':'Class & height', 'line_angle': 'Angle', 'primary_back_span': 'Back span', 'primary_structure': 'Structure Type',  'back_span': 'Secondary Back span',
'structure_qty':'Structure Quantity', 'structure_unit': 'J', 'conductor': 'Conductor Size', 
'grounding_assembly': 'Ground Unit M','guy_qty':'Quantity', 'guy_type':'Guy Type', 
'guy_lead':'Guy Lead (m)', 'anchor_qty':'Anchor Quantity', 'anchor_type':'Anchor Type', 
'k_10': 'Single Phase Qty','single_phase_unit': 'Single phase unit', 'k_30': 'Three-Phase Qty', 'three_phase_unit': 'Three-phase unit',
'streetlight':'Streetlight M unit'}

layer = QgsProject.instance().mapLayersByName(layer_name)[0]

# Extract the field names and features
field_names = [field.name() for field in layer.fields()]
# get the features from the layer and sort by pole_id if line_type == 'mv' else do not sort
line_type = layer_name[:2]
features = layer.getFeatures()
features = sorted(features, key=lambda x: x['pole_id']) if line_type == 'mv' else list(features)

# print(field_names)
# Create a list of dictionaries for each feature's attributes
data = []
table_keys = list(table_headers.keys())
table_key_values = list(table_headers.values())


for feature in features:
    attritudes = feature.attributes()
    attrs = list(attritudes)
    pole_number = attrs[1]
    line_angle = attrs[16]
    back_span = attrs[3] if line_type == 'lv' else ''
    j_10 = attrs[8]
    j_19 = attrs[7]
    conductor = attrs[11]
    grounding_assembly = attrs[5] if attrs[5] != None else ''
    guy = attrs[6]
    k_10 = attrs[9] if attrs[9] != None else ''
    k_30 = attrs[10] if attrs[10] != None else ''
    streetlight = attrs[14] if attrs[14] != None else ''
    latitude = attrs[12]
    longitude = attrs[13]
    height = ''
    if attrs[4] == '30ft':
        height = '30\'/6'
    elif attrs[4] == '35ft':
        height = '35\'/5'
    else:
        height = '40\'/4'

    primary_structure = attrs[17]
    primary_back_span = attrs[3] if line_type == 'mv' else ''
    
    structure_qty = ''
    structure_unit = '' 
    if j_10 == None and j_10 == None:
        structure_unit = ''
    elif j_10 == 0:
        structure_qty = j_19
        structure_unit = 'J19'
    elif j_19 == 0:
        structure_qty = j_10
        structure_unit = 'J10'
    elif j_10 == 1 and j_19 == 1:
        structure_qty = 1
        structure_unit = 'J10 + J19'
    elif j_10 == 1:
        structure_qty =  1
        structure_unit = f'J10 + {j_19}J19'
    elif j_19 == 1:
        structure_qty =  1
        structure_unit = f'{j_10}J10 + J19'
    else:
        structure_qty =  1
        structure_unit = f'{j_10}J10 + {j_19}J19'
        
    guy_txt = str(guy).split(' x ')
    guy_qty = int(guy_txt[0]) if len(guy_txt) == 2 else ''
    guy_type = guy_txt[1] if len(guy_txt) == 2 else ''
    guy_lead = ''
    if guy_qty:
        guy_lead = 11 if line_type == 'mv' else 7
    
    anchor_qty = guy_qty;
    anchor_type = ''
    if line_type == 'mv':
        anchor_type = 'F1-2' if guy_qty else ''
    else:
        anchor_type = 'F1-1' if guy_qty else ''
    
    single_phase_unit = 'K10' if k_10 else ''
    three_phase_unit = 'K30' if k_30 else ''
    
    values = [pole_number, latitude, longitude, height, line_angle, primary_back_span, primary_structure, back_span, structure_qty, 
    structure_unit, conductor, grounding_assembly, guy_qty, guy_type, guy_lead, anchor_qty, anchor_type,
    k_10, single_phase_unit, k_30, three_phase_unit, streetlight]
    
    data.append(dict(zip(table_key_values, values)))

# Create a pandas DataFrame from the data and field names
df = pd.DataFrame(data, columns=table_key_values)

# #Write the DataFrame to an Excel file
df.to_excel(output_excel_file, index=True)
print(f'Exported {layer_name} to {output_excel_file}...')

# # Open the Excel file
print(f'Opening {output_excel_file}...')
os.startfile(output_excel_file)