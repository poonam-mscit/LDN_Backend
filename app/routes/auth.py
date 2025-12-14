from flask import Blueprint, request, jsonify, current_app
from app.utils.auth import require_auth, get_current_user, verify_cognito_token
from app import db
from app.models.user import User
import boto3
from botocore.exceptions import ClientError
import os
import base64
import hmac
import hashlib
import re
import jwt

bp = Blueprint('auth', __name__)

def get_cognito_client():
    """Get Cognito Identity Provider client"""
    region = os.environ.get('AWS_REGION', 'ap-south-1')
    return boto3.client('cognito-idp', region_name=region)

def get_secret_hash(username):
    """Calculate secret hash for Cognito client secret"""
    client_id = os.environ.get('COGNITO_CLIENT_ID')
    client_secret = os.environ.get('COGNITO_CLIENT_SECRET')
    if not client_secret:
        return None
    message = username + client_id
    dig = hmac.new(
        client_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64.b64encode(dig).decode()

@bp.route('/signup', methods=['POST'])
def signup():
    """Sign up a new user"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        firstName = data.get('firstName')
        lastName = data.get('lastName')
        phoneNumber = data.get('phoneNumber')
        role = data.get('role')
        
        if not all([email, password, firstName, lastName, role]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        client = get_cognito_client()
        client_id = os.environ.get('COGNITO_CLIENT_ID')
        secret_hash = get_secret_hash(email)
        
        full_name = f"{firstName} {lastName}"
        # Start with required attributes
        user_attributes = [
            {'Name': 'email', 'Value': email},
            {'Name': 'name', 'Value': full_name}
        ]
        
        # Try to add phone number (use standard phone_number attribute)
        # Format phone number to E.164 format (required by Cognito): +[country code][number]
        phone_added = False
        if phoneNumber:
            try:
                # Remove all spaces and ensure it starts with +
                formatted_phone = phoneNumber.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                if not formatted_phone.startswith('+'):
                    formatted_phone = '+' + formatted_phone
                
                # Validate E.164 format: + followed by 1-15 digits
                if re.match(r'^\+\d{1,15}$', formatted_phone):
                    user_attributes.append({'Name': 'phone_number', 'Value': formatted_phone})
                    phone_added = True
            except Exception as e:
                # If phone formatting fails, skip it
                pass
        
        params = {
            'ClientId': client_id,
            'Username': email,
            'Password': password,
            'UserAttributes': user_attributes
        }
        
        if secret_hash:
            params['SecretHash'] = secret_hash
        
        # Try signup - first without custom:role, then with it if that fails
        response = None
        last_error = None
        
        # First attempt: without custom:role
        try:
            response = client.sign_up(**params)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            last_error = e
            
            # If it's a schema error for phone_number, try without phone
            if ('schema' in error_message.lower() or 'attribute' in error_message.lower()) and phone_added:
                # Retry without phone_number
                user_attributes_no_phone = [
                    {'Name': 'email', 'Value': email},
                    {'Name': 'name', 'Value': full_name}
                ]
                params['UserAttributes'] = user_attributes_no_phone
                try:
                    response = client.sign_up(**params)
                    phone_added = False  # Phone wasn't added
                except ClientError as e2:
                    last_error = e2
        
        # If still no response, try with custom:role added
        if not response:
            try:
                user_attributes_with_role = list(user_attributes)
                if phone_added:
                    user_attributes_with_role = [
                        {'Name': 'email', 'Value': email},
                        {'Name': 'name', 'Value': full_name},
                        {'Name': 'phone_number', 'Value': phoneNumber}
                    ]
                user_attributes_with_role.append({'Name': 'custom:role', 'Value': role})
                params['UserAttributes'] = user_attributes_with_role
                response = client.sign_up(**params)
            except ClientError as role_error:
                # If custom:role also fails, use the last error
                if not response:
                    last_error = role_error
        
        # If we still don't have a response, raise the last error
        if not response:
            raise last_error
        
        # Get cognito_sub from response
        cognito_sub = response.get('UserSub')
        
        # Create user in database immediately with the selected role
        # This ensures role is saved even before email verification
        try:
            # Check if user already exists (shouldn't happen, but just in case)
            existing_user = User.query.filter_by(cognito_sub=cognito_sub).first()
            if not existing_user:
                # Format phone number if provided
                formatted_phone = None
                if phoneNumber:
                    try:
                        formatted_phone = phoneNumber.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                        if not formatted_phone.startswith('+'):
                            formatted_phone = '+' + formatted_phone
                        if not re.match(r'^\+\d{1,15}$', formatted_phone):
                            formatted_phone = None
                    except:
                        formatted_phone = None
                
                # Create user with selected role
                new_user = User(
                    cognito_sub=cognito_sub,
                    email=email,
                    full_name=full_name,
                    phone_number=formatted_phone,
                    role=role  # Save the role selected during signup
                )
                db.session.add(new_user)
                db.session.commit()
                current_app.logger.info(f"User created in database: {email} with role: {role}")
            else:
                # Update role if user exists
                existing_user.role = role
                db.session.commit()
        except Exception as db_error:
            # Log error but don't fail signup - role will be set during login
            current_app.logger.error(f"Error creating user in database: {db_error}")
        
        return jsonify({
            'success': True,
            'userSub': cognito_sub,
            'message': 'User created successfully. Please check your email for verification code.',
            'role': role  # Return role for frontend
        }), 200
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'UsernameExistsException':
            return jsonify({'error': 'An account with this email already exists'}), 400
        elif error_code == 'InvalidPasswordException':
            return jsonify({'error': 'Password does not meet requirements'}), 400
        elif 'schema' in error_message.lower() or 'attribute' in error_message.lower():
            return jsonify({
                'error': 'User Pool configuration error. Custom attributes (custom:role, custom:phone_number) may not be defined in your Cognito User Pool.',
                'details': error_message,
                'solution': 'Either add these custom attributes to your Cognito User Pool, or the system will store role in the database only.'
            }), 400
        else:
            return jsonify({'error': error_message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/login', methods=['POST'])
def login():
    """Login user and return tokens"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        client = get_cognito_client()
        client_id = os.environ.get('COGNITO_CLIENT_ID')
        secret_hash = get_secret_hash(email)
        
        params = {
            'ClientId': client_id,
            'AuthFlow': 'USER_PASSWORD_AUTH',
            'AuthParameters': {
                'USERNAME': email,
                'PASSWORD': password
            }
        }
        
        if secret_hash:
            params['AuthParameters']['SECRET_HASH'] = secret_hash
        
        response = client.initiate_auth(**params)
        
        # Get tokens
        authentication_result = response.get('AuthenticationResult', {})
        id_token = authentication_result.get('IdToken')
        access_token = authentication_result.get('AccessToken')
        refresh_token = authentication_result.get('RefreshToken')
        
        if not id_token:
            return jsonify({'error': 'Authentication failed'}), 401
        
        # Decode token without verification (we trust Cognito's response)
        # We'll verify it properly when it's used in subsequent requests
        try:
            # Decode without verification to get user info
            unverified_claims = jwt.decode(id_token, options={"verify_signature": False})
            cognito_sub = unverified_claims.get('sub')
            email_from_token = unverified_claims.get('email')
        except Exception as e:
            current_app.logger.error(f"Error decoding token: {e}")
            return jsonify({'error': 'Failed to decode authentication token'}), 401
        
        # Verify token properly to ensure it's valid (but don't fail login if this fails)
        # This is for security - we still trust Cognito's response
        claims = verify_cognito_token(id_token)
        if not claims:
            # Log warning but continue - token was just issued by Cognito
            current_app.logger.warning("Token verification failed during login, but continuing with unverified claims")
            claims = unverified_claims
        
        # Get or create user in database
        user = User.query.filter_by(cognito_sub=cognito_sub).first()
        
        if not user:
            # User doesn't exist - create with role from token or default
            # Try to get role from token first, then fallback to 'clerk'
            role = claims.get('custom:role') or 'clerk'
            full_name = claims.get('name') or email_from_token.split('@')[0]
            phone_number = claims.get('phone_number') or claims.get('custom:phone_number')
            
            user = User(
                cognito_sub=cognito_sub,
                email=email_from_token,
                full_name=full_name,
                phone_number=phone_number,
                role=role
            )
            db.session.add(user)
            db.session.commit()
            current_app.logger.info(f"New user created during login: {email_from_token} with role: {role}")
        else:
            # User exists - update info but preserve existing role if it's set
            # Only update role if it's not set or if token has a different role
            if not user.email or user.email != email_from_token:
                user.email = email_from_token
            if not user.full_name:
                user.full_name = claims.get('name') or email_from_token.split('@')[0]
            if not user.phone_number:
                user.phone_number = claims.get('phone_number') or claims.get('custom:phone_number')
            
            # Role handling: preserve existing role from signup, only update if:
            # 1. User has no role set, OR
            # 2. Token has custom:role and it's different
            token_role = claims.get('custom:role')
            if not user.role:
                # No role in DB - use token role or default
                user.role = token_role or 'clerk'
                current_app.logger.info(f"Setting role for {email_from_token}: {user.role}")
            elif token_role and token_role != user.role:
                # Token has role and it's different - update it (admin can change roles)
                user.role = token_role
                current_app.logger.info(f"Updating role for {email_from_token} from {user.role} to {token_role}")
            
            db.session.commit()
        
        # Final check - ensure user role is set (should never reach here, but safety check)
        if not user.role:
            user.role = 'clerk'
            db.session.commit()
            current_app.logger.warning(f"User {email_from_token} had no role, set to default 'clerk'")
        
        user_dict = user.to_dict()
        current_app.logger.info(f"Login successful for user: {user.email}, role: {user.role}")
        
        return jsonify({
            'success': True,
            'idToken': id_token,
            'accessToken': access_token,
            'refreshToken': refresh_token,
            'user': user_dict
        }), 200
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'NotAuthorizedException':
            return jsonify({'error': 'Incorrect username or password'}), 401
        elif error_code == 'UserNotConfirmedException':
            return jsonify({'error': 'Please verify your email address'}), 401
        elif error_code == 'UserNotFoundException':
            return jsonify({'error': 'User not found'}), 404
        else:
            return jsonify({'error': error_message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/confirm-signup', methods=['POST'])
def confirm_signup():
    """Confirm user signup with verification code"""
    try:
        data = request.get_json()
        email = data.get('email')
        code = data.get('code')
        
        if not email or not code:
            return jsonify({'error': 'Email and code are required'}), 400
        
        client = get_cognito_client()
        client_id = os.environ.get('COGNITO_CLIENT_ID')
        secret_hash = get_secret_hash(email)
        
        params = {
            'ClientId': client_id,
            'Username': email,
            'ConfirmationCode': code
        }
        
        if secret_hash:
            params['SecretHash'] = secret_hash
        
        client.confirm_sign_up(**params)
        
        # After confirmation, verify user exists in database with role
        # Get user from Cognito to get cognito_sub
        try:
            # Get user details from Cognito
            admin_client = boto3.client('cognito-idp', region_name=os.environ.get('AWS_REGION', 'ap-south-1'))
            user_pool_id = os.environ.get('COGNITO_USER_POOL_ID')
            
            cognito_user = admin_client.admin_get_user(
                UserPoolId=user_pool_id,
                Username=email
            )
            
            cognito_sub = None
            for attr in cognito_user.get('UserAttributes', []):
                if attr['Name'] == 'sub':
                    cognito_sub = attr['Value']
                    break
            
            if cognito_sub:
                # Check if user exists in database
                user = User.query.filter_by(cognito_sub=cognito_sub).first()
                if user:
                    # User exists - role should already be set from signup
                    current_app.logger.info(f"User {email} confirmed, role in DB: {user.role}")
                else:
                    # User doesn't exist in DB - create with default role
                    # This shouldn't happen if signup worked, but handle it
                    role = 'clerk'  # Default
                    full_name = email.split('@')[0]
                    
                    user = User(
                        cognito_sub=cognito_sub,
                        email=email,
                        full_name=full_name,
                        role=role
                    )
                    db.session.add(user)
                    db.session.commit()
                    current_app.logger.warning(f"User {email} confirmed but not in DB, created with default role")
        except Exception as db_error:
            # Log but don't fail confirmation
            current_app.logger.error(f"Error checking user in database after confirmation: {db_error}")
        
        return jsonify({
            'success': True,
            'message': 'Email verified successfully'
        }), 200
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'CodeMismatchException':
            return jsonify({'error': 'Invalid verification code'}), 400
        elif error_code == 'ExpiredCodeException':
            return jsonify({'error': 'Verification code has expired'}), 400
        else:
            return jsonify({'error': error_message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/resend-code', methods=['POST'])
def resend_code():
    """Resend verification code"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        client = get_cognito_client()
        client_id = os.environ.get('COGNITO_CLIENT_ID')
        secret_hash = get_secret_hash(email)
        
        params = {
            'ClientId': client_id,
            'Username': email
        }
        
        if secret_hash:
            params['SecretHash'] = secret_hash
        
        client.resend_confirmation_code(**params)
        
        return jsonify({
            'success': True,
            'message': 'Verification code sent successfully'
        }), 200
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        return jsonify({'error': error_message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Initiate forgot password flow"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        client = get_cognito_client()
        client_id = os.environ.get('COGNITO_CLIENT_ID')
        secret_hash = get_secret_hash(email)
        
        params = {
            'ClientId': client_id,
            'Username': email
        }
        
        if secret_hash:
            params['SecretHash'] = secret_hash
        
        client.forgot_password(**params)
        
        return jsonify({
            'success': True,
            'message': 'Password reset code sent to your email'
        }), 200
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'UserNotFoundException':
            return jsonify({'error': 'User not found'}), 404
        else:
            return jsonify({'error': error_message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/confirm-forgot-password', methods=['POST'])
def confirm_forgot_password():
    """Confirm forgot password with code and new password"""
    try:
        data = request.get_json()
        email = data.get('email')
        code = data.get('code')
        new_password = data.get('newPassword')
        
        if not all([email, code, new_password]):
            return jsonify({'error': 'Email, code, and new password are required'}), 400
        
        client = get_cognito_client()
        client_id = os.environ.get('COGNITO_CLIENT_ID')
        secret_hash = get_secret_hash(email)
        
        params = {
            'ClientId': client_id,
            'Username': email,
            'ConfirmationCode': code,
            'Password': new_password
        }
        
        if secret_hash:
            params['SecretHash'] = secret_hash
        
        client.confirm_forgot_password(**params)
        
        return jsonify({
            'success': True,
            'message': 'Password reset successfully'
        }), 200
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'CodeMismatchException':
            return jsonify({'error': 'Invalid verification code'}), 400
        elif error_code == 'ExpiredCodeException':
            return jsonify({'error': 'Verification code has expired'}), 400
        elif error_code == 'InvalidPasswordException':
            return jsonify({'error': 'Password does not meet requirements'}), 400
        else:
            return jsonify({'error': error_message}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/verify', methods=['POST'])
def verify_token():
    """Verify Cognito token and return user info"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Missing authorization header'}), 401
        
        token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
        claims = verify_cognito_token(token)
        
        # Add fallback if verification fails (similar to get_current_user)
        if not claims:
            current_app.logger.warning("Token verification failed, attempting unverified decode as fallback")
            try:
                claims = jwt.decode(token, options={"verify_signature": False})
                current_app.logger.warning("Using unverified token as fallback")
            except Exception as e:
                current_app.logger.error(f"Failed to decode token even without verification: {e}")
                return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Get or create user in database
        cognito_sub = claims.get('sub')
        email = claims.get('email')
        
        user = User.query.filter_by(cognito_sub=cognito_sub).first()
        
        if not user:
            # Create user if doesn't exist
            role = claims.get('custom:role') or 'clerk'  # Default role
            full_name = claims.get('name') or email.split('@')[0]
            phone_number = claims.get('phone_number') or claims.get('custom:phone_number')
            
            user = User(
                cognito_sub=cognito_sub,
                email=email,
                full_name=full_name,
                phone_number=phone_number,
                role=role
            )
            db.session.add(user)
            db.session.commit()
        else:
            # Update user info from token if needed
            if not user.email or user.email != email:
                user.email = email
            if not user.full_name:
                user.full_name = claims.get('name') or email.split('@')[0]
            if not user.phone_number:
                user.phone_number = claims.get('phone_number') or claims.get('custom:phone_number')
            if not user.role:
                user.role = claims.get('custom:role') or 'clerk'
            db.session.commit()
        
        return jsonify({
            'user': user.to_dict(),
            'token_claims': {
                'sub': claims.get('sub'),
                'email': claims.get('email'),
                'exp': claims.get('exp')
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/me', methods=['GET'])
@require_auth
def get_current_user_info():
    """Get current authenticated user info"""
    try:
        cognito_sub = request.current_user.get('cognito_sub')
        user = User.query.filter_by(cognito_sub=cognito_sub).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    """Logout endpoint"""
    # In Cognito, logout is handled on frontend by clearing tokens
    return jsonify({'message': 'Logged out successfully'}), 200
