from flask import Blueprint, request, jsonify
from app import db
from app.models.availability import ClerkAvailability
from app.utils.auth import require_auth, require_role
from datetime import datetime, time

bp = Blueprint('availability', __name__)

@bp.route('/', methods=['GET'])
@require_auth
def get_availability():
    """
    Get availability records
    ---
    tags:
      - Availability
    parameters:
      - in: query
        name: user_id
        schema:
          type: string
        description: Filter by user ID
      - in: query
        name: available_date
        schema:
          type: string
          format: date
        description: Filter by specific date
      - in: query
        name: start_date
        schema:
          type: string
          format: date
        description: Start date for range filter
      - in: query
        name: end_date
        schema:
          type: string
          format: date
        description: End date for range filter
    security:
      - Bearer: []
    responses:
      200:
        description: List of availability records
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
      401:
        description: Unauthorized
    """
    user_id = request.args.get('user_id')
    available_date = request.args.get('available_date')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = ClerkAvailability.query
    if user_id:
        query = query.filter_by(user_id=user_id)
    if available_date:
        query = query.filter_by(available_date=datetime.fromisoformat(available_date).date())
    if start_date and end_date:
        start = datetime.fromisoformat(start_date).date()
        end = datetime.fromisoformat(end_date).date()
        query = query.filter(ClerkAvailability.available_date.between(start, end))
    
    records = query.all()
    return jsonify([record.to_dict() for record in records]), 200

@bp.route('/', methods=['POST'])
@require_auth
@require_role('clerk')
def create_availability():
    """
    Create availability record(s) - supports single or bulk creation
    ---
    tags:
      - Availability
    security:
      - Bearer: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            oneOf:
              - type: object
                properties:
                  user_id:
                    type: string
                  available_date:
                    type: string
                    format: date
                  is_available:
                    type: boolean
                  start_time:
                    type: string
                    format: time
                  end_time:
                    type: string
                    format: time
                  postcode:
                    type: string
                  notes:
                    type: string
              - type: array
                items:
                  type: object
              - type: object
                properties:
                  user_id:
                    type: string
                  availability:
                    type: object
    responses:
      201:
        description: Availability record(s) created successfully
        content:
          application/json:
            schema:
              oneOf:
                - type: object
                - type: array
                  items:
                    type: object
      400:
        description: Bad request
      401:
        description: Unauthorized
      403:
        description: Forbidden (clerk only)
    """
    data = request.get_json()
    
    # Check if this is a bulk save (array of records or object with date keys)
    if isinstance(data, list):
        # Bulk save from array
        records = []
        for item in data:
            available_date = datetime.fromisoformat(item['available_date']).date()
            start_time = time.fromisoformat(item.get('start_time', '08:00:00'))
            end_time = time.fromisoformat(item.get('end_time', '18:00:00'))
            
            # Check if record already exists (upsert behavior)
            existing = ClerkAvailability.query.filter_by(
                user_id=item['user_id'],
                available_date=available_date
            ).first()
            
            if existing:
                # Update existing record
                existing.is_available = item.get('is_available', True)
                existing.start_time = start_time
                existing.end_time = end_time
                existing.postcode = item.get('postcode')
                existing.notes = item.get('notes')
                records.append(existing)
            else:
                # Create new record
                availability = ClerkAvailability(
                    user_id=item['user_id'],
                    available_date=available_date,
                    is_available=item.get('is_available', True),
                    start_time=start_time,
                    end_time=end_time,
                    postcode=item.get('postcode'),
                    notes=item.get('notes')
                )
                db.session.add(availability)
                records.append(availability)
        
        db.session.commit()
        return jsonify([record.to_dict() for record in records]), 201
    
    elif isinstance(data, dict) and 'availability' in data:
        # Bulk save from object with date keys (frontend format)
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        availability_dict = data['availability']
        records = []
        
        for date_str, avail_data in availability_dict.items():
            if not avail_data.get('isAvailable', False):
                # Skip unavailable dates or delete if exists
                existing = ClerkAvailability.query.filter_by(
                    user_id=user_id,
                    available_date=datetime.fromisoformat(date_str).date()
                ).first()
                if existing:
                    db.session.delete(existing)
                continue
            
            available_date = datetime.fromisoformat(date_str).date()
            start_time = time.fromisoformat(avail_data.get('startTime', '08:00'))
            end_time = time.fromisoformat(avail_data.get('endTime', '18:00'))
            
            # Check if record already exists (upsert behavior)
            existing = ClerkAvailability.query.filter_by(
                user_id=user_id,
                available_date=available_date
            ).first()
            
            if existing:
                # Update existing record
                existing.is_available = True
                existing.start_time = start_time
                existing.end_time = end_time
                existing.postcode = avail_data.get('postcode')
                existing.notes = avail_data.get('notes')
                records.append(existing)
            else:
                # Create new record
                availability = ClerkAvailability(
                    user_id=user_id,
                    available_date=available_date,
                    is_available=True,
                    start_time=start_time,
                    end_time=end_time,
                    postcode=avail_data.get('postcode'),
                    notes=avail_data.get('notes')
                )
                db.session.add(availability)
                records.append(availability)
        
        db.session.commit()
        return jsonify([record.to_dict() for record in records]), 201
    
    else:
        # Single record creation (original behavior)
        available_date = datetime.fromisoformat(data['available_date']).date()
        start_time = time.fromisoformat(data.get('start_time', '08:00:00'))
        end_time = time.fromisoformat(data.get('end_time', '18:00:00'))
        
        availability = ClerkAvailability(
            user_id=data['user_id'],
            available_date=available_date,
            is_available=data.get('is_available', True),
            start_time=start_time,
            end_time=end_time,
            postcode=data.get('postcode'),
            notes=data.get('notes')
        )
        
        db.session.add(availability)
        db.session.commit()
        
        return jsonify(availability.to_dict()), 201

@bp.route('/<availability_id>', methods=['PUT'])
@require_auth
@require_role('clerk')
def update_availability(availability_id):
    """
    Update availability record
    ---
    tags:
      - Availability
    parameters:
      - in: path
        name: availability_id
        required: true
        schema:
          type: string
        description: Availability record ID
    security:
      - Bearer: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              available_date:
                type: string
                format: date
              is_available:
                type: boolean
              start_time:
                type: string
                format: time
              end_time:
                type: string
                format: time
              postcode:
                type: string
              notes:
                type: string
    responses:
      200:
        description: Availability record updated successfully
        content:
          application/json:
            schema:
              type: object
      404:
        description: Availability record not found
      401:
        description: Unauthorized
      403:
        description: Forbidden (clerk only)
    """
    availability = ClerkAvailability.query.get_or_404(availability_id)
    data = request.get_json()
    
    if 'available_date' in data:
        availability.available_date = datetime.fromisoformat(data['available_date']).date()
    if 'is_available' in data:
        availability.is_available = data['is_available']
    if 'start_time' in data:
        availability.start_time = time.fromisoformat(data['start_time'])
    if 'end_time' in data:
        availability.end_time = time.fromisoformat(data['end_time'])
    if 'postcode' in data:
        availability.postcode = data['postcode']
    if 'notes' in data:
        availability.notes = data['notes']
    
    db.session.commit()
    return jsonify(availability.to_dict()), 200

@bp.route('/<availability_id>', methods=['DELETE'])
@require_auth
@require_role('clerk')
def delete_availability(availability_id):
    """
    Delete availability record
    ---
    tags:
      - Availability
    parameters:
      - in: path
        name: availability_id
        required: true
        schema:
          type: string
        description: Availability record ID
    security:
      - Bearer: []
    responses:
      200:
        description: Availability record deleted successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
      404:
        description: Availability record not found
      401:
        description: Unauthorized
      403:
        description: Forbidden (clerk only)
    """
    availability = ClerkAvailability.query.get_or_404(availability_id)
    db.session.delete(availability)
    db.session.commit()
    return jsonify({'message': 'Availability record deleted'}), 200

