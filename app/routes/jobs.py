from flask import Blueprint, request, jsonify
from app import db
from app.models.job import Job
from app.models.property import Property
from app.models.user import User
from app.models.assignment_log import AssignmentLog
from app.models.availability import ClerkAvailability
from app.utils.auth import require_auth, require_role, get_current_user
from app.utils.helpers import convert_handover_camel_to_snake, calculate_distance
from datetime import datetime, date, time

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
    
    # Include property details for each job
    jobs_data = []
    for job in jobs:
        job_dict = job.to_dict()
        if job.property:
            job_dict['property'] = job.property.to_dict()
        # Include assigned clerk details if available
        if job.assigned_clerk:
            job_dict['clerk'] = {
                'id': str(job.assigned_clerk.id),
                'name': job.assigned_clerk.full_name
            }
        jobs_data.append(job_dict)
    
    return jsonify({
        'jobs': jobs_data,
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
    # Include assigned clerk details if available
    if job.assigned_clerk:
        job_dict['clerk'] = {
            'id': str(job.assigned_clerk.id),
            'name': job.assigned_clerk.full_name
        }
    # Include assigned agent details if available
    if job.assigned_agent:
        job_dict['assigned_agent'] = {
            'id': str(job.assigned_agent.id),
            'full_name': job.assigned_agent.full_name
        }
    return jsonify(job_dict), 200

def auto_assign_job(job, property_obj):
    """Auto-assign job to best available clerk"""
    appointment_date = job.appointment_date.date()
    is_today = appointment_date == date.today()
    
    # Find available clerks
    query = User.query.filter_by(role='clerk', is_active=True)
    
    # For today's jobs, check is_on_shift
    if is_today:
        query = query.filter_by(is_on_shift=True)
    
    clerks = query.all()
    
    if not clerks:
        return None
    
    # Filter by availability for future dates
    available_clerks = []
    for clerk in clerks:
        if is_today:
            # For today, just check if they have location
            if clerk.current_lat and clerk.current_lng:
                available_clerks.append(clerk)
        else:
            # For future dates, check availability calendar
            availability = ClerkAvailability.query.filter_by(
                user_id=clerk.id,
                available_date=appointment_date,
                is_available=True
            ).first()
            if availability:
                available_clerks.append(clerk)
    
    if not available_clerks:
        return None
    
    # Check for previous clerk at same property
    previous_job = Job.query.filter_by(
        property_id=property_obj.id,
        status='completed'
    ).order_by(Job.check_out_at.desc()).first()
    
    # Calculate scores for each clerk
    clerk_scores = []
    for clerk in available_clerks:
        score = 0
        
        # Previous clerk bonus (+50 points)
        if previous_job and previous_job.assigned_clerk_id == clerk.id:
            score += 50
        
        # Distance score (closer = higher score)
        if property_obj.latitude and property_obj.longitude:
            if clerk.current_lat and clerk.current_lng:
                distance = calculate_distance(
                    float(property_obj.latitude),
                    float(property_obj.longitude),
                    float(clerk.current_lat),
                    float(clerk.current_lng)
                )
                # Inverse distance score (closer = higher, max 100 points)
                score += max(0, 100 - (distance * 10))
            elif not is_today:
                # For future dates, use availability postcode if available
                availability = ClerkAvailability.query.filter_by(
                    user_id=clerk.id,
                    available_date=appointment_date
                ).first()
                if availability and availability.postcode:
                    # Use postcode matching as fallback (simplified)
                    if availability.postcode[:4] == property_obj.postcode[:4]:
                        score += 30
        
        # Current job count (fewer = higher score)
        current_jobs = Job.query.filter(
            Job.assigned_clerk_id == clerk.id,
            Job.status.in_(['assigned', 'on_route', 'in_progress'])
        ).count()
        score += max(0, 20 - current_jobs)
        
        clerk_scores.append((clerk.id, score))
    
    # Sort by score and return best clerk
    if not clerk_scores:
        return None
    
    clerk_scores.sort(key=lambda x: x[1], reverse=True)
    return clerk_scores[0][0]

@bp.route('/', methods=['POST'])
@require_auth
@require_role('admin', 'agent')
def create_job():
    """Create a new job"""
    data = request.get_json()
    current_user = request.current_user
    
    # Get property
    property_obj = Property.query.get_or_404(data['property_id'])
    
    # Resolve created_by_user_id from cognito_sub
    created_by_user_id = None
    assigned_agent_id = None
    if current_user.get('cognito_sub'):
        user = User.query.filter_by(cognito_sub=current_user['cognito_sub']).first()
        if user:
            created_by_user_id = user.id
            # If the user is an agent, set assigned_agent_id
            if user.role == 'agent':
                assigned_agent_id = user.id
    
    # Create job
    job = Job(
        property_id=data['property_id'],
        created_by_user_id=created_by_user_id,
        assigned_agent_id=assigned_agent_id,
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
    db.session.flush()  # Get job.id
    
    # Handle assignment
    assignment_type = data.get('assignment_type', 'manual')
    if assignment_type == 'auto':
        clerk_id = auto_assign_job(job, property_obj)
        if clerk_id:
            previous_clerk_id = job.assigned_clerk_id
            job.assigned_clerk_id = clerk_id
            job.status = 'assigned'
            
            # Log assignment
            log = AssignmentLog(
                job_id=job.id,
                previous_clerk_id=previous_clerk_id,
                new_clerk_id=clerk_id,
                action_type='AUTO_ASSIGN',
                reason='Auto-assigned by system based on availability and location'
            )
            db.session.add(log)
    elif assignment_type == 'manual':
        # Manual assignment - clerk_id should be provided
        clerk_id = data.get('clerk_id')
        if clerk_id:
            # Verify clerk exists and is active
            clerk = User.query.filter_by(id=clerk_id, role='clerk', is_active=True).first()
            if not clerk:
                db.session.rollback()
                return jsonify({'error': 'Invalid clerk selected'}), 400
            
            previous_clerk_id = job.assigned_clerk_id
            job.assigned_clerk_id = clerk_id
            job.status = 'assigned'
            
            # Log assignment
            log = AssignmentLog(
                job_id=job.id,
                previous_clerk_id=previous_clerk_id,
                new_clerk_id=clerk_id,
                action_type='MANUAL_OVERRIDE',
                reason=data.get('reason', 'Manual assignment during job creation')
            )
            db.session.add(log)
    
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
    
    # Check if location is far from property (100m = 0.1km threshold)
    if job.property and job.property.latitude and job.property.longitude:
        if job.check_in_lat and job.check_in_lng:
            distance = calculate_distance(
                float(job.property.latitude),
                float(job.property.longitude),
                float(job.check_in_lat),
                float(job.check_in_lng)
            )
            # Set warning flag if distance > 100m (0.1km)
            job.location_warning_flag = distance > 0.1
    
    db.session.commit()
    return jsonify(job.to_dict()), 200

@bp.route('/<job_id>/reject', methods=['POST'])
@require_auth
@require_role('clerk')
def reject_job(job_id):
    """Clerk rejects job assignment - triggers auto-reassignment"""
    job = Job.query.get_or_404(job_id)
    current_user = request.current_user
    
    # Verify this clerk is assigned to the job
    user = User.query.filter_by(cognito_sub=current_user.get('cognito_sub')).first()
    if not user or job.assigned_clerk_id != user.id:
        return jsonify({'error': 'You are not assigned to this job'}), 403
    
    previous_clerk_id = job.assigned_clerk_id
    
    # Unassign job
    job.assigned_clerk_id = None
    job.status = 'pending_assignment'
    
    # Log rejection
    log = AssignmentLog(
        job_id=job.id,
        previous_clerk_id=previous_clerk_id,
        new_clerk_id=None,
        action_type='REJECTION',
        triggered_by_user_id=user.id,
        reason='Clerk rejected assignment'
    )
    db.session.add(log)
    
    # Try to auto-reassign to another clerk
    if job.property:
        new_clerk_id = auto_assign_job(job, job.property)
        if new_clerk_id:
            job.assigned_clerk_id = new_clerk_id
            job.status = 'assigned'
            
            # Log auto-reassignment
            reassign_log = AssignmentLog(
                job_id=job.id,
                previous_clerk_id=None,
                new_clerk_id=new_clerk_id,
                action_type='AUTO_ASSIGN',
                reason='Auto-reassigned after rejection'
            )
            db.session.add(reassign_log)
    
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

@bp.route('/<job_id>/assignment-logs', methods=['GET'])
@require_auth
def get_job_assignment_logs(job_id):
    """Get assignment logs for a specific job"""
    logs = AssignmentLog.query.filter_by(job_id=job_id).order_by(AssignmentLog.created_at.desc()).all()
    return jsonify([log.to_dict() for log in logs]), 200

@bp.route('/assignment-logs', methods=['GET'])
@require_auth
def get_all_assignment_logs():
    """Get all assignment logs"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    query = AssignmentLog.query.order_by(AssignmentLog.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items
    
    # Include clerk names in response
    logs_data = []
    for log in logs:
        log_dict = log.to_dict()
        if log.previous_clerk_id:
            prev_clerk = User.query.get(log.previous_clerk_id)
            log_dict['previous_clerk_name'] = prev_clerk.full_name if prev_clerk else None
        if log.new_clerk_id:
            new_clerk = User.query.get(log.new_clerk_id)
            log_dict['new_clerk_name'] = new_clerk.full_name if new_clerk else None
        logs_data.append(log_dict)
    
    return jsonify({
        'logs': logs_data,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }), 200

