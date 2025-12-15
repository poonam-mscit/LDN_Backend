from flask import Blueprint, request, jsonify
from app import db
from app.models.invoice import ClerkInvoice
from app.utils.auth import require_auth, require_role
from datetime import datetime, date

bp = Blueprint('invoices', __name__)

@bp.route('/', methods=['GET'])
@require_auth
def get_invoices():
    """
    Get invoices (filtered by clerk if not admin)
    ---
    tags:
      - Invoices
    parameters:
      - in: query
        name: clerk_id
        schema:
          type: string
        description: Filter by clerk ID
      - in: query
        name: month_period
        schema:
          type: string
          format: date
        description: Filter by month period (YYYY-MM-DD)
    security:
      - Bearer: []
    responses:
      200:
        description: List of invoices
        content:
          application/json:
            schema:
              type: array
              items:
                type: object
      401:
        description: Unauthorized
    """
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
    """
    Submit invoice for a month period
    ---
    tags:
      - Invoices
    security:
      - Bearer: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - clerk_id
              - month_period
            properties:
              clerk_id:
                type: string
              month_period:
                type: string
                format: date
                description: Month period (YYYY-MM-DD)
              invoice_url:
                type: string
    responses:
      201:
        description: Invoice submitted successfully
        content:
          application/json:
            schema:
              type: object
      400:
        description: Bad request
      401:
        description: Unauthorized
      403:
        description: Forbidden (clerk only)
    """
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
def update_invoice_status(invoice_id):
    """
    Update invoice status
    ---
    tags:
      - Invoices
    parameters:
      - in: path
        name: invoice_id
        required: true
        schema:
          type: string
        description: Invoice ID
    security:
      - Bearer: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              status:
                type: string
              admin_notes:
                type: string
    responses:
      200:
        description: Invoice updated successfully
        content:
          application/json:
            schema:
              type: object
      404:
        description: Invoice not found
      401:
        description: Unauthorized
    """
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
    """
    Check if invoice submitted for a month
    ---
    tags:
      - Invoices
    parameters:
      - in: query
        name: clerk_id
        required: true
        schema:
          type: string
        description: Clerk ID
      - in: query
        name: month_period
        required: true
        schema:
          type: string
          format: date
        description: Month period (YYYY-MM-DD)
    security:
      - Bearer: []
    responses:
      200:
        description: Submission status
        content:
          application/json:
            schema:
              type: object
              properties:
                submitted:
                  type: boolean
                invoice:
                  type: object
                  nullable: true
      400:
        description: Missing required parameters
      401:
        description: Unauthorized
    """
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

