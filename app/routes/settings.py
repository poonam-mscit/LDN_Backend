from flask import Blueprint, request, jsonify
from app import db
from app.models.integration import IntegrationSettings
from app.models.settings import GeneralSettings
from app.utils.auth import require_auth, require_role
from datetime import datetime, timedelta, timezone

bp = Blueprint('settings', __name__)

@bp.route('/general', methods=['GET'])
@require_auth
@require_role('admin')
def get_general_settings():
    """Get general company settings"""
    # Get the first (and only) settings record, or create default if none exists
    settings = GeneralSettings.query.first()
    
    if not settings:
        # Create default settings if none exist
        settings = GeneralSettings()
        db.session.add(settings)
        db.session.commit()
    
    return jsonify(settings.to_dict()), 200

@bp.route('/general', methods=['PUT'])
@require_auth
@require_role('admin')
def update_general_settings():
    """Update general company settings"""
    data = request.get_json()
    
    # Get existing settings or create new
    settings = GeneralSettings.query.first()
    
    if not settings:
        settings = GeneralSettings()
        db.session.add(settings)
    
    # Update fields
    if 'company_name' in data:
        settings.company_name = data['company_name']
    if 'email' in data:
        settings.email = data['email']
    if 'telephone' in data:
        settings.telephone = data.get('telephone')
    if 'website' in data:
        settings.website = data.get('website')
    if 'address_line_1' in data:
        settings.address_line_1 = data.get('address_line_1')
    if 'address_line_2' in data:
        settings.address_line_2 = data.get('address_line_2')
    if 'city' in data:
        settings.city = data.get('city')
    if 'postcode' in data:
        settings.postcode = data.get('postcode')
    
    settings.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    
    return jsonify({
        'message': 'Settings updated successfully',
        'settings': settings.to_dict()
    }), 200

@bp.route('/integrations', methods=['GET'])
@require_auth
@require_role('admin')
def get_integrations():
    """Get all integration settings"""
    integrations = IntegrationSettings.query.all()
    return jsonify([integration.to_dict() for integration in integrations]), 200

@bp.route('/integrations/inventorybase', methods=['GET'])
@require_auth
@require_role('admin')
def get_inventorybase_integration():
    """Get InventoryBase integration settings"""
    integration = IntegrationSettings.query.filter_by(service_name='inventorybase').first()
    
    if not integration:
        return jsonify({
            'service_name': 'inventorybase',
            'client_id': '',
            'connected': False
        }), 200
    
    result = integration.to_dict()
    result['connected'] = True
    # Mask sensitive tokens in response (show only last 4 chars)
    if result.get('access_token'):
        result['access_token'] = '***' + result['access_token'][-4:] if len(result['access_token']) > 4 else '***'
    if result.get('refresh_token'):
        result['refresh_token'] = '***' + result['refresh_token'][-4:] if len(result['refresh_token']) > 4 else '***'
    
    return jsonify(result), 200

@bp.route('/integrations/inventorybase', methods=['POST'])
@require_auth
@require_role('admin')
def update_inventorybase_integration():
    """Update or create InventoryBase integration settings"""
    data = request.get_json()
    
    # Check if integration exists
    integration = IntegrationSettings.query.filter_by(service_name='inventorybase').first()
    
    if integration:
        # Update existing
        if 'client_id' in data:
            integration.client_id = data['client_id']
        if 'access_token' in data:
            integration.access_token = data['access_token']
        if 'refresh_token' in data:
            integration.refresh_token = data['refresh_token']
        if 'token_expires_at' in data:
            integration.token_expires_at = datetime.fromisoformat(data['token_expires_at'])
        integration.updated_at = datetime.now(timezone.utc)
    else:
        # Create new
        if not all(k in data for k in ['client_id', 'access_token', 'refresh_token']):
            return jsonify({'error': 'Missing required fields: client_id, access_token, refresh_token'}), 400
        
        token_expires_at = datetime.fromisoformat(data.get('token_expires_at')) if data.get('token_expires_at') else datetime.now(timezone.utc) + timedelta(hours=2)
        
        integration = IntegrationSettings(
            service_name='inventorybase',
            client_id=data['client_id'],
            access_token=data['access_token'],
            refresh_token=data['refresh_token'],
            token_expires_at=token_expires_at,
            scope=data.get('scope', 'properties.read')
        )
        db.session.add(integration)
    
    db.session.commit()
    
    result = integration.to_dict()
    result['connected'] = True
    # Mask sensitive tokens
    if result.get('access_token'):
        result['access_token'] = '***' + result['access_token'][-4:] if len(result['access_token']) > 4 else '***'
    if result.get('refresh_token'):
        result['refresh_token'] = '***' + result['refresh_token'][-4:] if len(result['refresh_token']) > 4 else '***'
    
    return jsonify(result), 200

@bp.route('/integrations/inventorybase/test', methods=['POST'])
@require_auth
@require_role('admin')
def test_inventorybase_connection():
    """Test InventoryBase connection"""
    data = request.get_json()
    client_id = data.get('client_id')
    client_secret = data.get('client_secret')  # This would be used for OAuth flow
    
    # For now, just validate that credentials are provided
    if not client_id:
        return jsonify({'error': 'Client ID is required', 'connected': False}), 400
    
    # In production, this would make an actual API call to InventoryBase
    # For now, return success if client_id is provided
    return jsonify({
        'message': 'Connection test successful',
        'connected': True
    }), 200

@bp.route('/integrations/inventorybase/sync', methods=['POST'])
@require_auth
@require_role('admin')
def sync_inventorybase_properties():
    """Trigger property sync from InventoryBase"""
    integration = IntegrationSettings.query.filter_by(service_name='inventorybase').first()
    
    if not integration:
        return jsonify({'error': 'InventoryBase integration not configured'}), 400
    
    # Update last_synced_at
    integration.last_synced_at = datetime.now(timezone.utc)
    db.session.commit()
    
    # In production, this would trigger the actual sync process
    # For now, just return success
    return jsonify({
        'message': 'Property sync initiated',
        'last_synced_at': integration.last_synced_at.isoformat()
    }), 200

