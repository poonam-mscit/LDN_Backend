from flask import Blueprint, request, jsonify
from app import db
from app.models.job import Job
from app.models.property import Property
from app.models.user import User
from app.models.assignment_log import AssignmentLog
from app.utils.auth import require_auth, require_role
from app.utils.helpers import convert_handover_camel_to_snake
from datetime import datetime

bp = Blueprint('jobs', __name__)

@bp.route('/', methods=['GET'])
@require_auth
def get_jobs():
    """Get all jobs with filters"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    clerk_id = request.args.get('clerk_id')
    agent_id = request.args.get('agent_id')
    property_id = request.args.get('property_id')
    
    query = Job.query
    if status:
        query = query.filter_by(status=status)
    if clerk_id:
        query = query.filter_by(assigned_clerk_id=clerk_id)
    if agent_id:
        query = query.filter_by(assigned_agent_id=agent_id)
    if property_id:
        query = query.filter_by(property_id=property_id)
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    jobs = pagination.items
    
    return jsonify({
        'jobs': [job.to_dict() for job in jobs],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200

@bp.route('/<job_id>', methods=['GET'])
@require_auth
def get_job(job_id):
    """Get job by ID"""
    job = Job.query.get_or_404(job_id)
    job_dict = job.to_dict()
    # Include property details
    if job.property:
        job_dict['property'] = job.property.to_dict()
    return jsonify(job_dict), 200

@bp.route('/', methods=['POST'])
@require_auth
@require_role('admin', 'agent')
def create_job():
    """Create a new job"""
    data = request.get_json()
    
    job = Job(
        property_id=data['property_id'],
        created_by_user_id=data.get('created_by_user_id'),
        job_type=data.get('job_type', 'Logistics_Visit'),
        priority=data.get('priority', 'normal'),
        appointment_date=datetime.fromisoformat(data['appointment_date'].replace('Z', '+00:00')),
        estimated_duration_minutes=data.get('estimated_duration_minutes', 60),
        access_instructions=data.get('access_instructions'),
        key_location=data.get('key_location'),
        admin_attachments=data.get('admin_attachments', []),
        admin_notes=data.get('admin_notes'),
        booking_questions=data.get('booking_questions', {})
    )
    
    db.session.add(job)
    db.session.commit()
    
    return jsonify(job.to_dict()), 201

@bp.route('/<job_id>', methods=['PUT'])
@require_auth
def update_job(job_id):
    """Update job"""
    job = Job.query.get_or_404(job_id)
    data = request.get_json()
    
    # Update allowed fields
    updatable_fields = [
        'job_type', 'priority', 'appointment_date', 'estimated_duration_minutes',
        'access_instructions', 'key_location', 'admin_attachments', 'admin_notes',
        'booking_questions', 'status', 'assigned_clerk_id', 'assigned_agent_id'
    ]
    
    for field in updatable_fields:
        if field in data:
            if field == 'appointment_date':
                job.appointment_date = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
            else:
                setattr(job, field, data[field])
    
    db.session.commit()
    return jsonify(job.to_dict()), 200

@bp.route('/<job_id>/assign', methods=['POST'])
@require_auth
@require_role('admin')
def assign_job(job_id):
    """Assign job to clerk (manual assignment)"""
    job = Job.query.get_or_404(job_id)
    data = request.get_json()
    clerk_id = data.get('clerk_id')
    
    previous_clerk_id = job.assigned_clerk_id
    job.assigned_clerk_id = clerk_id
    job.status = 'assigned'
    
    # Log assignment
    log = AssignmentLog(
        job_id=job.id,
        previous_clerk_id=previous_clerk_id,
        new_clerk_id=clerk_id,
        action_type='MANUAL_OVERRIDE',
        reason=data.get('reason', 'Admin manual assignment')
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify(job.to_dict()), 200

@bp.route('/<job_id>/start', methods=['POST'])
@require_auth
@require_role('clerk')
def start_job(job_id):
    """Clerk starts job (on_route status)"""
    job = Job.query.get_or_404(job_id)
    job.status = 'on_route'
    job.on_route_at = datetime.utcnow()
    db.session.commit()
    return jsonify(job.to_dict()), 200

@bp.route('/<job_id>/check-in', methods=['POST'])
@require_auth
@require_role('clerk')
def check_in(job_id):
    """Clerk checks in at property"""
    job = Job.query.get_or_404(job_id)
    data = request.get_json()
    
    job.check_in_at = datetime.utcnow()
    job.check_in_lat = data.get('lat')
    job.check_in_lng = data.get('lng')
    job.status = 'in_progress'
    
    # Check if location is far from property
    if job.property and job.property.latitude and job.property.longitude:
        # TODO: Calculate distance and set location_warning_flag
        pass
    
    db.session.commit()
    return jsonify(job.to_dict()), 200

@bp.route('/<job_id>/complete', methods=['POST'])
@require_auth
@require_role('clerk')
def complete_job(job_id):
    """Clerk completes job"""
    job = Job.query.get_or_404(job_id)
    data = request.get_json()
    
    job.status = 'completed'
    job.check_out_at = datetime.utcnow()
    job.check_out_lat = data.get('lat')
    job.check_out_lng = data.get('lng')
    
    # Convert handover_data from frontend camelCase to database snake_case
    handover_data = data.get('handover_data', {})
    if handover_data:
        handover_data = convert_handover_camel_to_snake(handover_data)
    job.handover_data = handover_data
    
    db.session.commit()
    return jsonify(job.to_dict()), 200

