from flask import Blueprint, request, jsonify
from app import db
from app.models.property import Property
from app.utils.auth import require_auth, require_role

bp = Blueprint('properties', __name__)

@bp.route('/', methods=['GET'])
@require_auth
def get_properties():
    """Get all properties"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    postcode = request.args.get('postcode')
    city = request.args.get('city')
    is_active = request.args.get('is_active', 'true')  # Default to active only
    
    query = Property.query
    if postcode:
        query = query.filter(Property.postcode.ilike(f'%{postcode}%'))
    if city:
        query = query.filter(Property.city.ilike(f'%{city}%'))
    # Filter by active status (default to active only)
    if is_active.lower() == 'true':
        query = query.filter(Property.is_active == True)
    elif is_active.lower() == 'false':
        query = query.filter(Property.is_active == False)
    # If is_active is not specified or is 'all', show all
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    properties = pagination.items
    
    return jsonify({
        'properties': [prop.to_dict() for prop in properties],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200

@bp.route('/<property_id>', methods=['GET'])
@require_auth
def get_property(property_id):
    """Get property by ID"""
    property = Property.query.get_or_404(property_id)
    return jsonify(property.to_dict()), 200

@bp.route('/', methods=['POST'])
@require_auth
@require_role('admin')
def create_property():
    """Create a new property (admin only)"""
    data = request.get_json()
    
    property = Property(
        inventorybase_id=data['inventorybase_id'],
        reference_number=data.get('reference_number'),
        uprn=data.get('uprn'),
        parent_property_id=data.get('parent_property_id'),
        address_line_1=data.get('address_line_1'),
        address_line_2=data.get('address_line_2'),
        city=data.get('city'),
        postcode=data['postcode'],
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        property_type=data.get('property_type'),
        bedrooms=data.get('bedrooms', 0),
        bathrooms=data.get('bathrooms', 0),
        has_parking=data.get('has_parking', False),
        client_name=data.get('client_name'),
        tags=data.get('tags', []),
        custom_fields=data.get('custom_fields', {}),
        notes=data.get('notes'),
        meter_location_notes=data.get('meter_location_notes')
    )
    
    db.session.add(property)
    db.session.commit()
    
    return jsonify(property.to_dict()), 201

@bp.route('/<property_id>', methods=['PUT'])
@require_auth
@require_role('admin')
def update_property(property_id):
    """Update property (admin only)"""
    property = Property.query.get_or_404(property_id)
    data = request.get_json()
    
    # Update allowed fields
    updatable_fields = [
        'address_line_1', 'address_line_2', 'city', 'postcode',
        'latitude', 'longitude', 'property_type', 'bedrooms', 'bathrooms',
        'has_parking', 'client_name', 'tags', 'custom_fields', 'notes',
        'meter_location_notes', 'status', 'is_active'
    ]
    
    for field in updatable_fields:
        if field in data:
            setattr(property, field, data[field])
    
    db.session.commit()
    return jsonify(property.to_dict()), 200

@bp.route('/sync', methods=['POST'])
@require_auth
@require_role('admin')
def sync_properties():
    """Sync properties from InventoryBase API (admin only)"""
    # TODO: Implement InventoryBase API sync
    return jsonify({'message': 'Property sync endpoint'}), 200

