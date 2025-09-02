import os
import logging
from datetime import timedelta, datetime
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
from models import db, User, Subscription, DeviceFingerprint, PaymentRequest, Comment
db.init_app(app)

# إعداد Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # type: ignore
login_manager.login_message = 'يرجى تسجيل الدخول للوصول لهذه الصفحة.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize SocketIO for maximum stability - polling only
socketio = SocketIO(app, 
                   cors_allowed_origins="*", 
                   ping_timeout=120,       # Very long timeout
                   ping_interval=30,       # Less frequent pings
                   logger=False,           # Reduce logging overhead
                   engineio_logger=False,  # Reduce logging overhead
                   async_mode=None,        # Let SocketIO choose best mode
                   transports=['polling']) # Use only polling for stability

# Initialize price service
price_service = PriceService()

# إنشاء جداول قاعدة البيانات وإنشاء المستخدم الافتراضي
with app.app_context():
    # حذف الجداول القديمة وإعادة إنشائها لتحديث البنية
    db.drop_all()
    db.create_all()
    
    # إنشاء المستخدم الافتراضي كمدير
    admin_email = "brq7787@gmail.com"
    admin_password = "Msken2009"
    
    admin_user = User()
    admin_user.email = admin_email
    admin_user.username = "Admin"
    admin_user.is_admin = True  # تعيين كمدير
    admin_user.set_password(admin_password)
    
    try:
        db.session.add(admin_user)
        db.session.commit()
        
        # إنشاء اشتراك دائم للمدير
        admin_subscription = Subscription()
        admin_subscription.user_id = admin_user.id
        admin_subscription.status = 'active'
        admin_subscription.subscription_start = datetime.now()
        admin_subscription.subscription_end = datetime.now() + timedelta(days=365 * 10)  # 10 سنوات
        
        db.session.add(admin_subscription)
        db.session.commit()
        
        logging.info(f"تم إنشاء المستخدم الافتراضي كمدير: {admin_email}")
    except Exception as e:
        db.session.rollback()
        logging.error(f"خطأ في إنشاء المستخدم الافتراضي: {e}")

@app.route('/')
@login_required
def index():
    """الصفحة الرئيسية للوحة التحكم - تتطلب تسجيل الدخول فقط"""
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

@app.route('/api/ai/stats')
def get_ai_stats():
    """الحصول على إحصائيات نظام التعلم الذكي"""
    try:
        if hasattr(price_service, 'ai_analyzer') and price_service.ai_analyzer:
            stats = price_service.ai_analyzer.get_ai_learning_stats()
            return jsonify({'success': True, 'data': stats})
        else:
            return jsonify({'success': True, 'data': {'ai_enabled': False, 'message': 'نظام الذكاء الاصطناعي غير متاح'}})
    except Exception as e:
        logging.error(f"خطأ في الحصول على إحصائيات AI: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# مسارات المصادقة
@app.route('/login', methods=['GET', 'POST'])
def login():
    """صفحة تسجيل الدخول - للمدير فقط"""
    from flask_login import login_user
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # التحقق من الإيميل والباسورد المحددين فقط
        if email == 'brq7787@gmail.com' and password == 'Msken2009':
            user = User.query.filter_by(email=email).first()
            if not user:
                # إنشاء المستخدم إذا لم يكن موجوداً
                user = User()
                user.email = email
                user.set_password(password)
                user.is_admin = True
                db.session.add(user)
                db.session.commit()
            
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('الإيميل أو كلمة المرور غير صحيحة', 'error')
    
    return render_template('login.html')



@app.route('/create-stripe-session', methods=['POST'])
@login_required
def create_stripe_session():
    """إنشاء جلسة دفع Stripe"""
    import stripe
    import os
    
    # التحقق من وجود مفتاح Stripe
    stripe_key = os.environ.get('STRIPE_SECRET_KEY')
    if not stripe_key:
        flash('نظام الدفع غير متاح حالياً. يرجى المحاولة لاحقاً.', 'error')
        return redirect(url_for('subscription'))
    
    stripe.api_key = stripe_key
    
    try:
        # الحصول على domain للتطبيق
        domain = os.environ.get('REPLIT_DEV_DOMAIN')
        if os.environ.get('REPLIT_DEPLOYMENT') != '':
            domain = os.environ.get('REPLIT_DOMAINS', '').split(',')[0]
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'sar',
                    'product_data': {
                        'name': 'اشتراك شهري - لوحة مراقبة الأصول المالية',
                        'description': 'اشتراك شهري للوصول الكامل للوحة مراقبة الأصول المالية',
                    },
                    'unit_amount': 50000,  # 500 ريال بالهلل
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'https://{domain}/payment/success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'https://{domain}/subscription',
            customer_email=current_user.email,
            metadata={
                'user_id': current_user.id,
                'subscription_type': 'monthly'
            }
        )
        
        return redirect(checkout_session.url or url_for('subscription'), code=303)
        
    except Exception as e:
        logging.error(f"خطأ في إنشاء جلسة Stripe: {e}")
        flash('حدث خطأ أثناء إعداد الدفع. يرجى المحاولة لاحقاً.', 'error')
        return redirect(url_for('subscription'))

@app.route('/payment/success')
@login_required
def payment_success():
    """صفحة نجاح الدفع"""
    session_id = request.args.get('session_id')
    
    if session_id:
        # التحقق من الدفع وتفعيل الاشتراك
        import stripe
        import os
        
        stripe_key = os.environ.get('STRIPE_SECRET_KEY')
        if stripe_key:
            stripe.api_key = stripe_key
            
            try:
                session = stripe.checkout.Session.retrieve(session_id)
                
                if session.payment_status == 'paid':
                    # تفعيل اشتراك المستخدم
                    if current_user.subscription:
                        current_user.subscription.activate_subscription()
                    else:
                        subscription = Subscription()
                        subscription.user_id = current_user.id
                        subscription.status = 'active'
                        subscription.subscription_start = datetime.utcnow()
                        subscription.subscription_end = datetime.utcnow() + timedelta(days=30)
                        db.session.add(subscription)
                    
                    # حفظ معلومات الدفع
                    payment_request = PaymentRequest()
                    payment_request.user_id = current_user.id
                    payment_request.amount = 500.0
                    payment_request.currency = 'SAR'
                    payment_request.payment_method = 'stripe'
                    payment_request.status = 'approved'
                    payment_request.processed_at = datetime.utcnow()
                    db.session.add(payment_request)
                    
                    db.session.commit()
                    
                    flash('تم تفعيل اشتراكك بنجاح! أهلاً بك في النسخة الكاملة.', 'success')
                    return redirect(url_for('index'))
                    
            except Exception as e:
                logging.error(f"خطأ في التحقق من الدفع: {e}")
        
        flash('حدث خطأ في التحقق من الدفع. يرجى التواصل مع الدعم.', 'error')
        return redirect(url_for('subscription'))
    
    flash('تم الدفع بنجاح!', 'success')
    return redirect(url_for('index'))

@app.route('/register')
def register():
    """صفحة التسجيل - معطلة"""
    flash('التسجيل غير متاح. يرجى استخدام الإيميل المخصص لك.', 'info')
    return redirect(url_for('login'))

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

@socketio.on('test_connection')
def handle_test_connection(data):
    """Handle connection test from client"""
    logging.info(f"Connection test received from client")
    emit('connection_confirmed', {
        'status': 'connected',
        'timestamp': data.get('timestamp'),
        'server_time': time.time()
    })

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
    """Background task to monitor prices and send updates - optimized for speed"""
    last_system_status_update = 0
    while True:
        start_time = time.time()
        try:
            # Get current prices - optimized call
            prices = price_service.get_all_prices_fast()
            
            # Only emit if prices actually changed to reduce network traffic
            if prices and price_service.has_price_changes():
                socketio.emit('price_update', prices)
            
            # Emit system status less frequently (every 15 seconds)
            current_time = time.time()
            if current_time - last_system_status_update > 15:
                status = price_service.get_system_status()
                socketio.emit('system_status', status)
                last_system_status_update = current_time
            
            # Check for triggered alerts - optimized
            triggered_alerts = price_service.check_alerts_fast(prices)
            for alert in triggered_alerts:
                socketio.emit('alert_triggered', alert)
                logging.info(f"Alert triggered: {alert}")
            
            # Generate trading signals - optimized frequency
            signals = price_service.generate_trading_signals_fast(prices)
            for signal in signals:
                socketio.emit('trading_signal', signal)
                logging.info(f"Trading signal: {signal['type']} {signal['asset_name']} at {signal['price']}")
            
        except Exception as e:
            logging.error(f"Error in price monitor: {e}")
        
        # Dynamic sleep time based on processing time
        processing_time = time.time() - start_time
        sleep_time = max(2, 3 - processing_time)  # Faster updates (2-3 seconds)
        time.sleep(sleep_time)

# Start background price monitoring
price_monitor_thread = threading.Thread(target=price_monitor, daemon=True)
price_monitor_thread.start()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False, log_output=True)
