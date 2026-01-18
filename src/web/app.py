"""
Flask web layer for QR attendance
- Token generation endpoint
- Attendance verification endpoint
- QR attendance HTML page
- Health check endpoint
"""

import logging
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime

logger = logging.getLogger(__name__)

# HTML template for QR attendance page (embedded in response)
QR_ATTENDANCE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gym Attendance QR Check-In</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 {
            margin-top: 0;
            color: #333;
            text-align: center;
        }
        .location-info {
            background: #f0f4ff;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }
        .location-info p {
            margin: 5px 0;
            color: #555;
        }
        button {
            width: 100%;
            padding: 12px;
            font-size: 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
        }
        .btn-primary {
            background: #667eea;
            color: white;
            margin-bottom: 10px;
        }
        .btn-primary:hover {
            background: #5568d3;
            transform: translateY(-2px);
        }
        .btn-primary:active {
            transform: translateY(0);
        }
        .status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
            display: none;
        }
        .status.loading {
            background: #fff3cd;
            color: #856404;
            display: block;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
            display: block;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
            display: block;
        }
        .status-message {
            font-weight: 600;
            margin-bottom: 10px;
        }
        .status-detail {
            font-size: 14px;
            margin-top: 10px;
        }
        .gps-coords {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏋️ Gym Check-In</h1>
        
        <div class="location-info">
            <p><strong>📍 Location:</strong> Main Gym</p>
            <p><strong>Coordinates:</strong> 19.996429, 73.754282</p>
            <p><strong>Status:</strong> Ready to scan</p>
        </div>

        <button class="btn-primary" onclick="startCheckIn()">
            📍 Start Check-In with GPS
        </button>

        <div id="status" class="status">
            <div class="status-message" id="statusMessage"></div>
            <div class="status-detail" id="statusDetail"></div>
            <div class="gps-coords" id="gpsCoords"></div>
        </div>
    </div>

    <script>
        const GYM_LAT = 19.996429;
        const GYM_LON = 73.754282;

        async function startCheckIn() {
            const statusDiv = document.getElementById('status');
            const messageDiv = document.getElementById('statusMessage');
            const detailDiv = document.getElementById('statusDetail');
            const coordsDiv = document.getElementById('gpsCoords');

            // Request GPS permission
            if (!navigator.geolocation) {
                showStatus('error', 'GPS not available', 'Your browser does not support geolocation');
                return;
            }

            showStatus('loading', 'Requesting location...', '');

            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    const userLat = position.coords.latitude;
                    const userLon = position.coords.longitude;
                    const accuracy = position.coords.accuracy;

                    coordsDiv.textContent = `Latitude: ${userLat.toFixed(6)}, Longitude: ${userLon.toFixed(6)}, Accuracy: ±${Math.round(accuracy)}m`;

                    try {
                        showStatus('loading', 'Sending attendance...', '');

                        // First get token
                        const tokenResponse = await fetch('/api/token/generate', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                user_id: window.userId || 0  // Will be set from context
                            })
                        });

                        if (!tokenResponse.ok) {
                            throw new Error(`Token generation failed: ${tokenResponse.status}`);
                        }

                        const tokenData = await tokenResponse.json();
                        if (!tokenData.success) {
                            throw new Error(tokenData.reason || 'Token generation failed');
                        }

                        // Now verify attendance
                        const verifyResponse = await fetch('/api/attendance/verify', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                token: tokenData.token,
                                user_lat: userLat,
                                user_lon: userLon
                            })
                        });

                        const verifyData = await verifyResponse.json();

                        if (verifyData.success) {
                            showStatus('success', '✅ Check-In Successful!', `Distance: ${verifyData.distance_m?.toFixed(0)}m from gym`);
                        } else {
                            showStatus('error', '❌ Check-In Failed', verifyData.reason || 'Unknown error');
                        }

                    } catch (error) {
                        showStatus('error', '❌ Error', error.message);
                    }
                },
                (error) => {
                    let message = 'Unable to get location';
                    switch(error.code) {
                        case error.PERMISSION_DENIED:
                            message = 'Location permission denied. Please enable location access.';
                            break;
                        case error.POSITION_UNAVAILABLE:
                            message = 'Location information unavailable.';
                            break;
                        case error.TIMEOUT:
                            message = 'Location request timeout.';
                            break;
                    }
                    showStatus('error', '❌ GPS Error', message);
                }
            );
        }

        function showStatus(type, message, detail) {
            const statusDiv = document.getElementById('status');
            const messageDiv = document.getElementById('statusMessage');
            const detailDiv = document.getElementById('statusDetail');

            statusDiv.className = 'status ' + type;
            messageDiv.textContent = message;
            detailDiv.textContent = detail;
            statusDiv.style.display = 'block';
        }

        // Try to extract user_id from URL params or Telegram context
        window.userId = new URLSearchParams(window.location.search).get('user_id') || 0;
    </script>
</body>
</html>
"""


def create_app():
    """Create and configure Flask app"""
    app = Flask(__name__)
    app.config['JSON_SORT_KEYS'] = False
    
    logger.info("Flask app created")
    
    # ============================================================================
    # ENDPOINTS
    # ============================================================================
    
    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()}), 200
    
    
    @app.route('/qr/attendance', methods=['GET'])
    def qr_attendance_page():
        """Serve QR attendance HTML page"""
        try:
            user_id = request.args.get('user_id', 0, type=int)
            html = QR_ATTENDANCE_TEMPLATE.replace('window.userId || 0', str(user_id))
            return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
        except Exception as e:
            logger.error(f"Error serving QR page: {e}")
            return jsonify({'error': 'Failed to load page'}), 500
    
    
    @app.route('/api/token/generate', methods=['POST'])
    def generate_token():
        """
        Generate single-use token for attendance
        POST /api/token/generate
        Body: {'user_id': 123456}
        Response: {'success': true, 'token': 'abc123...', 'expires_in': 120}
        """
        try:
            data = request.get_json() or {}
            user_id = data.get('user_id')
            
            if not user_id:
                return jsonify({
                    'success': False,
                    'reason': 'MISSING_USER_ID'
                }), 400
            
            # Import here to avoid circular imports
            from src.utils.attendance_tokens import token_store
            
            token = token_store.generate_token(user_id)
            logger.info(f"Token generated for user {user_id}: {token[:8]}...")
            
            return jsonify({
                'success': True,
                'token': token,
                'expires_in': 120
            }), 200
            
        except Exception as e:
            logger.error(f"Error generating token: {e}")
            return jsonify({
                'success': False,
                'reason': 'SERVER_ERROR'
            }), 500
    
    
    @app.route('/api/attendance/verify', methods=['POST'])
    def verify_attendance():
        """
        Verify attendance with token + GPS location
        POST /api/attendance/verify
        Body: {
            'token': 'abc123...',
            'user_lat': 19.996429,
            'user_lon': 73.754282
        }
        Response: {
            'success': true,
            'distance_m': 5.2,
            'message': 'Attendance marked'
        }
        """
        try:
            data = request.get_json() or {}
            token = data.get('token')
            user_lat = data.get('user_lat')
            user_lon = data.get('user_lon')
            
            # Validate input
            if not token or user_lat is None or user_lon is None:
                return jsonify({
                    'success': False,
                    'reason': 'MISSING_PARAMETERS',
                    'distance_m': None
                }), 400
            
            # Step 1: Validate and consume token (ATOMIC)
            # ================================================
            from src.utils.attendance_tokens import token_store
            
            is_valid, result = token_store.validate_and_consume_token(token)
            if not is_valid:
                logger.warning(f"Invalid token: {result}")
                return jsonify({
                    'success': False,
                    'reason': result,
                    'distance_m': None
                }), 401
            
            user_id = result
            logger.debug(f"Token valid for user {user_id}")
            
            # Step 2: Check subscription/eligibility
            # ================================================
            from src.utils.attendance_eligibility import check_attendance_eligibility
            
            eligibility = check_attendance_eligibility(user_id)
            if not eligibility['eligible']:
                logger.warning(f"User {user_id} not eligible: {eligibility['reason']}")
                return jsonify({
                    'success': False,
                    'reason': eligibility['reason'],
                    'distance_m': None
                }), 403
            
            # Step 3: Check geofence
            # ================================================
            from src.utils.geofence import is_within_geofence
            
            GYM_LAT = 19.996429
            GYM_LON = 73.754282
            GEOFENCE_RADIUS = 20  # meters
            
            is_within, distance = is_within_geofence(
                user_lat, user_lon,
                GYM_LAT, GYM_LON,
                GEOFENCE_RADIUS
            )
            
            logger.debug(f"User {user_id} distance from gym: {distance:.1f}m")
            
            if not is_within:
                logger.warning(f"User {user_id} outside geofence: {distance:.1f}m > {GEOFENCE_RADIUS}m")
                return jsonify({
                    'success': False,
                    'reason': 'OUTSIDE_GEOFENCE',
                    'distance_m': round(distance, 1)
                }), 403
            
            # Step 4: Check duplicate attendance
            # ================================================
            from src.database.attendance_operations import check_duplicate_attendance
            
            if check_duplicate_attendance(user_id):
                logger.warning(f"Duplicate attendance attempt for user {user_id}")
                return jsonify({
                    'success': False,
                    'reason': 'DUPLICATE_ATTENDANCE',
                    'distance_m': round(distance, 1)
                }), 409
            
            # Step 5: Create attendance record
            # ================================================
            from src.database.attendance_operations import create_attendance_request
            
            try:
                request_id = create_attendance_request(user_id, 'QR', None)
                logger.info(f"Attendance created for user {user_id}: request_id={request_id}")
            except Exception as e:
                logger.error(f"Failed to create attendance for user {user_id}: {e}")
                return jsonify({
                    'success': False,
                    'reason': 'DATABASE_ERROR',
                    'distance_m': round(distance, 1)
                }), 500
            
            # Step 6: Queue admin notification (async)
            # ================================================
            try:
                from src.utils.admin_notifications import queue_admin_notification
                queue_admin_notification(
                    'attendance_marked',
                    user_id=user_id,
                    distance_m=distance,
                    timestamp=datetime.now().isoformat()
                )
            except Exception as e:
                logger.error(f"Failed to queue admin notification: {e}")
                # Don't fail attendance on notification error
            
            return jsonify({
                'success': True,
                'reason': 'ATTENDANCE_MARKED',
                'distance_m': round(distance, 1),
                'message': f'✅ Check-in successful! ({distance:.0f}m from gym)'
            }), 200
            
        except Exception as e:
            logger.error(f"Unexpected error in verify_attendance: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'reason': 'SERVER_ERROR',
                'distance_m': None
            }), 500
    
    
    return app
