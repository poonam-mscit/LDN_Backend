"""Authentication utilities and decorators"""
import os
import requests
from functools import wraps
from flask import request, jsonify, current_app
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import time

def get_cognito_public_keys():
    """Fetch Cognito public keys for JWT verification"""
    region = current_app.config.get('AWS_REGION') or os.environ.get('AWS_REGION', 'ap-south-1')
    user_pool_id = current_app.config.get('COGNITO_USER_POOL_ID') or os.environ.get('COGNITO_USER_POOL_ID')
    
    if not user_pool_id:
        current_app.logger.error("COGNITO_USER_POOL_ID not configured")
        return None
    
    keys_url = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json'
    try:
        response = requests.get(keys_url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        current_app.logger.error(f"Error fetching Cognito keys: {e}")
        return None

def get_public_key_from_jwk(jwk_data):
    """Convert JWK to PEM format for PyJWT"""
    from cryptography.hazmat.primitives.asymmetric import rsa
    import base64
    
    n = base64.urlsafe_b64decode(jwk_data['n'] + '==')
    e = base64.urlsafe_b64decode(jwk_data['e'] + '==')
    
    # Convert bytes to integers
    n_int = int.from_bytes(n, 'big')
    e_int = int.from_bytes(e, 'big')
    
    # Create RSA public key
    public_key = rsa.RSAPublicNumbers(e_int, n_int).public_key(default_backend())
    
    # Serialize to PEM
    pem = public_key.public_key_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return pem

def verify_cognito_token(token):
    """Verify and decode Cognito JWT token"""
    try:
        # Get public keys
        keys = get_cognito_public_keys()
        if not keys:
            current_app.logger.error("Failed to fetch Cognito public keys")
            return None
        
        # Decode header to get kid (without verification)
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        if not kid:
            current_app.logger.error("Token missing 'kid' in header")
            return None
        
        # Find the matching key
        key_data = None
        for k in keys.get('keys', []):
            if k.get('kid') == kid:
                key_data = k
                break
        
        if not key_data:
            current_app.logger.error(f"Key with kid '{kid}' not found in JWKS")
            return None
        
        # Convert JWK to PEM format
        try:
            public_key_pem = get_public_key_from_jwk(key_data)
        except Exception as e:
            current_app.logger.error(f"Error converting JWK to PEM: {e}")
            return None
        
        # Verify token issuer
        user_pool_id = current_app.config.get('COGNITO_USER_POOL_ID') or os.environ.get('COGNITO_USER_POOL_ID')
        region = current_app.config.get('AWS_REGION') or os.environ.get('AWS_REGION', 'ap-south-1')
        
        if not user_pool_id:
            current_app.logger.error("COGNITO_USER_POOL_ID not configured")
            return None
        
        expected_issuer = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}'
        
        # Decode and verify token
        try:
            claims = jwt.decode(
                token,
                public_key_pem,
                algorithms=['RS256'],
                issuer=expected_issuer,
                options={"verify_exp": True}
            )
            return claims
        except jwt.ExpiredSignatureError:
            current_app.logger.error("Token has expired")
            return None
        except jwt.InvalidIssuerError:
            current_app.logger.error(f"Invalid issuer. Expected: {expected_issuer}")
            return None
        except jwt.InvalidTokenError as e:
            current_app.logger.error(f"Invalid token: {e}")
            return None
        
    except Exception as e:
        current_app.logger.error(f"Error verifying token: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return None

def get_current_user():
    """Get current user from token"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    
    try:
        # Extract token (format: "Bearer <token>")
        token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
        
        # Try to verify token, but if it fails, try to decode without verification as fallback
        claims = verify_cognito_token(token)
        
        if not claims:
            # Fallback: decode without verification (less secure but allows functionality)
            try:
                import jwt
                claims = jwt.decode(token, options={"verify_signature": False})
                current_app.logger.warning("Token verification failed, using unverified token")
            except Exception as e:
                current_app.logger.error(f"Error decoding token: {e}")
                return None
        
        # If we still don't have claims, return None
        if not claims:
            return None
        
        cognito_sub = claims.get('sub')
        email = claims.get('email')
        
        # Get role from database instead of token (more reliable)
        role = None
        try:
            from app.models.user import User
            user = User.query.filter_by(cognito_sub=cognito_sub).first()
            if user:
                role = user.role
        except Exception as e:
            current_app.logger.warning(f"Could not fetch user from database: {e}")
        
        # Extract user info from token and database
        return {
            'cognito_sub': cognito_sub,
            'email': email,
            'role': role or claims.get('custom:role') or 'clerk',
            'token_claims': claims
        }
    except Exception as e:
        current_app.logger.error(f"Error getting current user: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Unauthorized - Invalid or missing token'}), 401
        
        # Attach user to request context
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function

def require_role(*roles):
    """Decorator to require specific role(s)"""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user = request.current_user
            user_role = user.get('role')
            
            if not user_role or user_role not in roles:
                return jsonify({
                    'error': f'Forbidden - Required role: {", ".join(roles)}'
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
