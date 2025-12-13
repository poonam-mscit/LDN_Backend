"""Helper utility functions"""
from math import radians, cos, sin, asin, sqrt
import re

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    Returns distance in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r

def validate_coordinates(lat, lng):
    """Validate latitude and longitude values"""
    if lat is None or lng is None:
        return False
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return False
    return True

def camel_to_snake(name):
    """Convert camelCase to snake_case"""
    # Insert an underscore before any uppercase letter that follows a lowercase letter or digit
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    # Insert an underscore before any uppercase letter that follows a lowercase letter
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def snake_to_camel(name):
    """Convert snake_case to camelCase"""
    components = name.split('_')
    return components[0] + ''.join(x.capitalize() for x in components[1:])

def convert_handover_camel_to_snake(data):
    """
    Convert handover_data from frontend camelCase format to database snake_case format.
    
    Frontend format: { "gasReading": "...", "electricReading": "...", "keyReturn": "..." }
    Database format: { "gas_reading": "...", "electric_reading": "...", "key_return_info": "..." }
    """
    if not isinstance(data, dict):
        return data
    
    converted = {}
    # Mapping from frontend camelCase to database snake_case
    field_mapping = {
        'gasReading': 'gas_reading',
        'electricReading': 'electric_reading',
        'keyReturn': 'key_return_info',
        'proofPhotoUrl': 'proof_photo_url'
    }
    
    for key, value in data.items():
        # Use mapping if available, otherwise convert using camel_to_snake
        db_key = field_mapping.get(key, camel_to_snake(key))
        converted[db_key] = value
    
    return converted

def convert_handover_snake_to_camel(data):
    """
    Convert handover_data from database snake_case format to frontend camelCase format.
    
    Database format: { "gas_reading": "...", "electric_reading": "...", "key_return_info": "..." }
    Frontend format: { "gasReading": "...", "electricReading": "...", "keyReturn": "..." }
    """
    if not isinstance(data, dict):
        return data
    
    converted = {}
    # Mapping from database snake_case to frontend camelCase
    field_mapping = {
        'gas_reading': 'gasReading',
        'electric_reading': 'electricReading',
        'key_return_info': 'keyReturn',
        'key_return': 'keyReturn',  # Alternative field name
        'proof_photo_url': 'proofPhotoUrl'
    }
    
    for key, value in data.items():
        # Use mapping if available, otherwise convert using snake_to_camel
        frontend_key = field_mapping.get(key, snake_to_camel(key))
        converted[frontend_key] = value
    
    return converted

