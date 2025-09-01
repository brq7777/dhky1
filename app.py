import os
import logging
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, login_required, logout_user, current_user
import threading
import time
from api_service import PriceService

# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# إعداد قاعدة البيانات
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# إستيراد نموذج المستخدم وإعداد قاعدة البيانات
from models import db, User
db.init_app(app)

# إعداد Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'يرجى تسجيل الدخول للوصول إلى هذه الصفحة.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize price service
price_service = PriceService()

# إنشاء جداول قاعدة البيانات
with app.app_context():
    db.create_all()

@app.route('/')
@login_required
def index():
    """الصفحة الرئيسية للوحة التحكم - تتطلب تسجيل الدخول"""
    return render_template('index.html', user=current_user)

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

# مسارات المصادقة
@app.route('/login', methods=['GET', 'POST'])
def login():
    """صفحة تسجيل الدخول"""
    from flask_login import login_user
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('يرجى إدخال اسم المستخدم وكلمة المرور', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """صفحة التسجيل"""
    from flask_login import login_user
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not password or not confirm_password:
            flash('يرجى ملء جميع الحقول', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('كلمات المرور غير متطابقة', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'error')
            return render_template('register.html')
        
        # التحقق من عدم وجود مستخدم بنفس الاسم
        if User.query.filter_by(username=username).first():
            flash('اسم المستخدم موجود بالفعل', 'error')
            return render_template('register.html')
        
        # إنشاء مستخدم جديد
        new_user = User()
        new_user.username = username
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash('تم إنشاء الحساب بنجاح', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating user: {e}")
            flash('حدث خطأ أثناء إنشاء الحساب', 'error')
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    """تسجيل الخروج"""
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'info')
    return redirect(url_for('login'))

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
    asset_name = next((a['name'] for a in price_service.assets if a['id'] == asset_id), 'BTCUSD')
    
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

@socketio.on('subscribe_alert')
def handle_subscribe_alert(data):
    """Handle general alert subscription"""
    asset_id = data.get('asset_id')
    alert_type = data.get('type', 'general')  # 'general' for all price movements
    
    logging.info(f"General alert subscription: {asset_id}, {alert_type}")
    
    # Store alert in price service  
    try:
        from flask import session
        client_id = session.get('client_id', 'default')
    except:
        client_id = 'default'
    price_service.add_alert(asset_id, None, alert_type, client_id)  # No threshold needed
    
    emit('alert_subscribed', {
        'asset_id': asset_id,
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
