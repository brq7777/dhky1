import os
import logging
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import time
from api_service import PriceService

# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize price service
price_service = PriceService()

@app.route('/')
def index():
    """Serve the main dashboard page"""
    return render_template('index.html')

@app.route('/api/prices')
def get_prices():
    """Get current prices for all assets"""
    try:
        prices = price_service.get_all_prices()
        return jsonify({'success': True, 'data': prices})
    except Exception as e:
        logging.error(f"Error fetching prices: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/price/<asset_id>')
def get_price(asset_id):
    """Get price for a specific asset"""
    try:
        price = price_service.get_price(asset_id)
        if price is not None:
            return jsonify({'success': True, 'data': price})
        else:
            return jsonify({'success': False, 'error': 'Asset not found'}), 404
    except Exception as e:
        logging.error(f"Error fetching price for {asset_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/status')
def get_system_status():
    """Get system status including offline mode"""
    try:
        status = price_service.get_system_status()
        return jsonify({'success': True, 'data': status})
    except Exception as e:
        logging.error(f"Error fetching system status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logging.info('Client connected')
    emit('connected', {'message': 'Connected to price updates'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logging.info('Client disconnected')

@socketio.on('test_signal')
def handle_test_signal(data):
    """Generate a test trading signal"""
    asset_id = data.get('asset_id', 'BTCUSDT')
    asset_name = next((a['name'] for a in price_service.assets if a['id'] == asset_id), 'بيتكوين')
    
    test_signal = {
        'asset_id': asset_id,
        'asset_name': asset_name,
        'type': 'BUY',
        'price': 65000.00,
        'confidence': 85,
        'timestamp': time.time(),
        'reason': 'إشارة تجريبية للاختبار'
    }
    
    emit('trading_signal', test_signal)
    logging.info(f"Test signal sent: {test_signal}")

@socketio.on('subscribe_alerts')
def handle_subscribe_alerts(data):
    """Handle alert subscription"""
    asset_id = data.get('asset_id')
    threshold = data.get('threshold')
    alert_type = data.get('type', 'above')  # 'above' or 'below'
    
    logging.info(f"Alert subscription: {asset_id}, {threshold}, {alert_type}")
    
    # Store alert in price service  
    try:
        from flask import session
        client_id = session.get('client_id', 'default')
    except:
        client_id = 'default'
    price_service.add_alert(asset_id, threshold, alert_type, client_id)
    
    emit('alert_subscribed', {
        'asset_id': asset_id,
        'threshold': threshold,
        'type': alert_type
    })

def price_monitor():
    """Background task to monitor prices and send updates"""
    while True:
        try:
            # Get current prices
            prices = price_service.get_all_prices()
            
            # Emit price updates to all connected clients
            socketio.emit('price_update', prices)
            
            # Emit system status including offline mode
            status = price_service.get_system_status()
            socketio.emit('system_status', status)
            
            # Check for triggered alerts
            triggered_alerts = price_service.check_alerts(prices)
            for alert in triggered_alerts:
                socketio.emit('alert_triggered', alert)
                logging.info(f"Alert triggered: {alert}")
            
            # Generate trading signals
            signals = price_service.generate_trading_signals(prices)
            for signal in signals:
                socketio.emit('trading_signal', signal)
                logging.info(f"Trading signal: {signal['type']} {signal['asset_name']} at {signal['price']}")
            
        except Exception as e:
            logging.error(f"Error in price monitor: {e}")
        
        time.sleep(5)  # Update every 5 seconds

# Start background price monitoring
price_monitor_thread = threading.Thread(target=price_monitor, daemon=True)
price_monitor_thread.start()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False, log_output=True)
