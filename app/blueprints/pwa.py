
from flask import Blueprint, jsonify, request, send_file, current_app
import os

pwa_bp = Blueprint('pwa', __name__)

@pwa_bp.route('/manifest.json')
def manifest():
    manifest_path = os.path.join(current_app.root_path, 'templates', 'manifest.json')
    return send_file(manifest_path, mimetype='application/json')

@pwa_bp.route('/service-worker.js')
def service_worker():
    sw_path = os.path.join(current_app.root_path, '..', 'static', 'js', 'service-worker.js')
    return send_file(sw_path, mimetype='application/javascript')

@pwa_bp.route('/api/push-subscribe', methods=['POST'])
def push_subscribe():
    subscription = request.get_json()
    # Store subscription in database for push notifications
    # This is a placeholder - implement actual storage logic
    print(f"Push subscription received: {subscription}")
    return jsonify({'success': True})

@pwa_bp.route('/api/sync-offline-data', methods=['POST'])
def sync_offline_data():
    # Handle background sync for offline data
    # This is a placeholder - implement actual sync logic
    return jsonify({'success': True, 'synced': True})

@pwa_bp.route('/offline')
def offline():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Offline - SnapTravels</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                text-align: center; 
                padding: 50px;
                background: linear-gradient(135deg, #1D2C78 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
                margin: 0;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            }
            h1 { margin-bottom: 20px; }
            p { margin-bottom: 30px; }
            .offline-icon { font-size: 64px; margin-bottom: 20px; }
            .retry-btn {
                background: white;
                color: #1D2C78;
                border: none;
                padding: 12px 24px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 16px;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="offline-icon">📶</div>
        <h1>You're Offline</h1>
        <p>Please check your internet connection and try again.</p>
        <button class="retry-btn" onclick="window.location.reload()">Try Again</button>
    </body>
    </html>
    '''
