from flask import Blueprint, request, jsonify
from app import db
from app.models.invoice import ClerkInvoice
from app.utils.auth import require_auth, require_role
from datetime import datetime, date

bp = Blueprint('invoices', __name__)

@bp.route('/', methods=['GET'])
@require_auth
def get_invoices():
    """Get invoices (filtered by clerk if not admin)"""
    clerk_id = request.args.get('clerk_id')
    month_period = request.args.get('month_period')
    
    query = ClerkInvoice.query
    if clerk_id:
        query = query.filter_by(clerk_id=clerk_id)
    if month_period:
        query = query.filter_by(month_period=month_period)
    
    invoices = query.all()
    return jsonify([invoice.to_dict() for invoice in invoices]), 200

@bp.route('/', methods=['POST'])
@require_auth
@require_role('clerk')
def submit_invoice():
    """Submit invoice for a month period"""
    data = request.get_json()
    
    # Parse month_period (e.g., '2024-11-01' for November 2024)
    month_period = datetime.fromisoformat(data['month_period']).date()
    
    invoice = ClerkInvoice(
        clerk_id=data['clerk_id'],
        month_period=month_period,
        invoice_url=data.get('invoice_url'),
        status='submitted'
    )
    
    db.session.add(invoice)
    db.session.commit()
    
    return jsonify(invoice.to_dict()), 201

@bp.route('/<invoice_id>', methods=['PUT'])
@require_auth
@require_role('admin')
def update_invoice_status(invoice_id):
    """Update invoice status (admin only)"""
    invoice = ClerkInvoice.query.get_or_404(invoice_id)
    data = request.get_json()
    
    if 'status' in data:
        invoice.status = data['status']
    if 'admin_notes' in data:
        invoice.admin_notes = data['admin_notes']
    
    db.session.commit()
    return jsonify(invoice.to_dict()), 200

@bp.route('/check-submission', methods=['GET'])
@require_auth
def check_submission():
    """Check if invoice submitted for a month"""
    clerk_id = request.args.get('clerk_id')
    month_period = request.args.get('month_period')
    
    if not clerk_id or not month_period:
        return jsonify({'error': 'Missing clerk_id or month_period'}), 400
    
    month_date = datetime.fromisoformat(month_period).date()
    invoice = ClerkInvoice.query.filter_by(clerk_id=clerk_id, month_period=month_date).first()
    
    return jsonify({
        'submitted': invoice is not None,
        'invoice': invoice.to_dict() if invoice else None
    }), 200

