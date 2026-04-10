"""
Cognito OAuth2 Authentication for Flask
Handles login redirect, callback, token exchange, and session management.
Only active when COGNITO_USER_POOL_ID environment variable is set.
"""
import os
import json
import time
import base64
import hashlib
import secrets
import urllib.request
import urllib.parse
from functools import wraps
from flask import request, redirect, session, jsonify, make_response

# Cognito configuration from environment
COGNITO_USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID')
COGNITO_CLIENT_ID = os.environ.get('COGNITO_CLIENT_ID')
COGNITO_CLIENT_SECRET = os.environ.get('COGNITO_CLIENT_SECRET')
COGNITO_DOMAIN = os.environ.get('COGNITO_DOMAIN')
APP_URL = os.environ.get('APP_URL', '')

COGNITO_ENABLED = bool(COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID and COGNITO_DOMAIN)

# Public paths that don't require authentication
PUBLIC_PATHS = [
    '/api/health',
    '/auth/login',
    '/auth/callback',
    '/auth/logout',
]


def is_cognito_enabled():
    return COGNITO_ENABLED


def get_cognito_login_url():
    """Build Cognito hosted UI login URL"""
    params = urllib.parse.urlencode({
        'client_id': COGNITO_CLIENT_ID,
        'response_type': 'code',
        'scope': 'openid email profile',
        'redirect_uri': f'{APP_URL}/auth/callback',
    })
    return f'https://{COGNITO_DOMAIN}/login?{params}'


def exchange_code_for_tokens(code):
    """Exchange authorization code for tokens via Cognito token endpoint"""
    token_url = f'https://{COGNITO_DOMAIN}/oauth2/token'
    
    data = urllib.parse.urlencode({
        'grant_type': 'authorization_code',
        'client_id': COGNITO_CLIENT_ID,
        'code': code,
        'redirect_uri': f'{APP_URL}/auth/callback',
    }).encode('utf-8')
    
    # Build Basic auth header
    credentials = f'{COGNITO_CLIENT_ID}:{COGNITO_CLIENT_SECRET}'
    auth_header = base64.b64encode(credentials.encode()).decode()
    
    req = urllib.request.Request(
        token_url,
        data=data,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {auth_header}',
        },
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"Token exchange error: {e}")
        return None


def decode_id_token(id_token):
    """Decode JWT id_token payload (no signature verification — ALB/Cognito is trusted)"""
    try:
        parts = id_token.split('.')
        if len(parts) != 3:
            return None
        payload = parts[1]
        # Add padding
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        print(f"JWT decode error: {e}")
        return None


def get_user_from_session():
    """Get user info from Flask session"""
    user = session.get('user')
    if not user:
        return None
    # Check token expiry
    if user.get('exp') and time.time() > user['exp']:
        session.pop('user', None)
        return None
    return user


def register_auth_routes(app):
    """Register Cognito auth routes on the Flask app"""
    
    @app.route('/auth/login')
    def auth_login():
        return redirect(get_cognito_login_url())
    
    @app.route('/auth/callback')
    def auth_callback():
        code = request.args.get('code')
        error = request.args.get('error')
        
        if error:
            return jsonify({'error': error, 'description': request.args.get('error_description')}), 400
        
        if not code:
            return redirect('/auth/login')
        
        tokens = exchange_code_for_tokens(code)
        if not tokens or 'id_token' not in tokens:
            return jsonify({'error': 'Token exchange failed'}), 500
        
        user_info = decode_id_token(tokens['id_token'])
        if not user_info:
            return jsonify({'error': 'Invalid token'}), 500
        
        # Store user in session
        given_name = (user_info.get('given_name') or
                      user_info.get('name', '').split()[0] if user_info.get('name') else
                      user_info.get('email', 'User').split('@')[0])
        
        session['user'] = {
            'sub': user_info.get('sub'),
            'email': user_info.get('email'),
            'name': user_info.get('name'),
            'given_name': given_name,
            'family_name': user_info.get('family_name'),
            'exp': user_info.get('exp', time.time() + 3600),
        }
        session['access_token'] = tokens.get('access_token')
        
        return redirect('/')
    
    @app.route('/auth/logout')
    def auth_logout():
        session.clear()
        # Redirect to Cognito logout
        params = urllib.parse.urlencode({
            'client_id': COGNITO_CLIENT_ID,
            'logout_uri': APP_URL,
        })
        return redirect(f'https://{COGNITO_DOMAIN}/logout?{params}')
    
    @app.before_request
    def require_auth():
        """Middleware: redirect unauthenticated requests to Cognito login"""
        # Skip auth for public paths
        path = request.path
        if any(path.startswith(p) for p in PUBLIC_PATHS):
            return None
        
        # Skip auth for static assets
        if path.startswith('/static/') or path.startswith('/assets/'):
            return None
        
        # Check session
        user = get_user_from_session()
        if user:
            return None
        
        # API requests get 401, browser requests get redirected
        if path.startswith('/api/'):
            return jsonify({'error': 'Not authenticated', 'login_url': '/auth/login'}), 401
        
        return redirect('/auth/login')
