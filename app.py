import os
import logging
from datetime import timedelta
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

# إنشاء جداول قاعدة البيانات وإنشاء المستخدم الافتراضي
with app.app_context():
    # حذف الجداول القديمة وإعادة إنشائها لتحديث البنية
    db.drop_all()
    db.create_all()
    
    # إنشاء المستخدم الافتراضي كمدير
    admin_email = "abodhayym2020@gmail.com"
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
        from datetime import datetime
        admin_subscription = Subscription()
        admin_subscription.user_id = admin_user.id
        admin_subscription.status = 'active'
        admin_subscription.subscription_start = datetime.utcnow()
        admin_subscription.subscription_end = datetime.utcnow() + timedelta(days=365 * 10)  # 10 سنوات
        
        db.session.add(admin_subscription)
        db.session.commit()
        
        logging.info(f"تم إنشاء المستخدم الافتراضي كمدير: {admin_email}")
    except Exception as e:
        db.session.rollback()
        logging.error(f"خطأ في إنشاء المستخدم الافتراضي: {e}")

@app.route('/')
@login_required
def index():
    """الصفحة الرئيسية للوحة التحكم - تتطلب تسجيل الدخول واشتراك نشط"""
    # التحقق من إمكانية الوصول للوحة التحكم
    if not current_user.can_access_dashboard():
        flash('انتهت فترة التجربة المجانية. يرجى الاشتراك للمتابعة.', 'warning')
        return redirect(url_for('subscription'))
    
    # عرض معلومات الاشتراك للمستخدم
    trial_hours = current_user.get_trial_remaining_hours()
    subscription_info = {
        'is_trial': current_user.subscription and current_user.subscription.status == 'trial',
        'trial_remaining_hours': trial_hours,
        'is_admin': current_user.is_admin,
        'has_active_subscription': current_user.has_active_subscription()
    }
    
    # إضافة معلومات الاشتراك بشكل أكثر تفصيل
    subscription_status = {
        'is_trial': current_user.subscription and current_user.subscription.status == 'trial',
        'trial_remaining_hours': trial_hours,
        'is_active': current_user.has_active_subscription() and current_user.subscription.status != 'trial',
        'end_date': current_user.subscription.subscription_end if current_user.subscription else None
    }
    
    return render_template('index.html', user=current_user, subscription=subscription_info, subscription_status=subscription_status)

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
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('يرجى إدخال الإيميل وكلمة المرور', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('الإيميل أو كلمة المرور غير صحيحة', 'error')
    
    return render_template('login.html')

@app.route('/subscription')
@login_required
def subscription():
    """صفحة الاشتراك والدفع"""
    # التحقق من وجود اشتراك نشط
    if current_user.has_active_subscription() and not current_user.subscription.status == 'trial':
        flash('لديك اشتراك نشط بالفعل', 'info')
        return redirect(url_for('index'))
    
    trial_hours = current_user.get_trial_remaining_hours()
    subscription_info = {
        'is_trial': current_user.subscription and current_user.subscription.status == 'trial',
        'trial_remaining_hours': trial_hours,
        'amount': 500,
        'currency': 'SAR'
    }
    
    return render_template('subscription.html', subscription=subscription_info)

@app.route('/payment/bank-transfer')
@login_required
def bank_transfer_payment():
    """صفحة الدفع عبر التحويل البنكي"""
    bank_info = {
        'iban': 'SA1234567890123456789012',  # ضع الإيبان الفعلي هنا
        'bank_name': 'البنك الأهلي السعودي',
        'account_name': 'شركة الأصول المالية للاستثمار',
        'amount': 500,
        'currency': 'ريال سعودي',
        'monthly_fee': '500 ريال شهرياً'
    }
    
    return render_template('bank_transfer.html', bank_info=bank_info)

# مسارات الإدارة
@app.route('/admin')
@login_required
def admin_dashboard():
    """لوحة الإدارة - للمدير فقط"""
    if not current_user.is_admin:
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('index'))
    
    # إحصائيات سريعة
    stats = {
        'total_users': User.query.count(),
        'active_subscribers': User.query.join(Subscription).filter(
            Subscription.status == 'active'
        ).count(),
        'trial_users': User.query.join(Subscription).filter(
            Subscription.status == 'trial'
        ).count(),
        'pending_payments': PaymentRequest.query.filter_by(status='pending').count()
    }
    
    # طلبات الدفع المعلقة
    payment_requests = PaymentRequest.query.filter_by(status='pending').order_by(
        PaymentRequest.created_at.desc()
    ).all()
    
    # جميع المستخدمين
    users = User.query.order_by(User.created_at.desc()).all()
    
    # التعليقات المعلقة
    pending_comments = Comment.query.filter_by(is_approved=False).order_by(
        Comment.created_at.desc()
    ).all()
    
    return render_template('admin.html', 
                         stats=stats, 
                         payment_requests=payment_requests,
                         users=users,
                         pending_comments=pending_comments)

@app.route('/admin/approve-payment/<int:request_id>', methods=['POST'])
@login_required
def admin_approve_payment(request_id):
    """الموافقة على طلب دفع"""
    if not current_user.is_admin:
        flash('ليس لديك صلاحية لهذا الإجراء', 'error')
        return redirect(url_for('index'))
    
    payment_request = PaymentRequest.query.get_or_404(request_id)
    
    try:
        payment_request.approve_payment(current_user.id)
        flash(f'تم الموافقة على طلب الدفع للمستخدم {payment_request.user.email}', 'success')
    except Exception as e:
        flash(f'خطأ في الموافقة على الطلب: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reject-payment/<int:request_id>', methods=['POST'])  
@login_required
def admin_reject_payment(request_id):
    """رفض طلب دفع"""
    if not current_user.is_admin:
        flash('ليس لديك صلاحية لهذا الإجراء', 'error')
        return redirect(url_for('index'))
    
    payment_request = PaymentRequest.query.get_or_404(request_id)
    
    try:
        payment_request.reject_payment(current_user.id, 'تم الرفض من قبل المدير')
        flash(f'تم رفض طلب الدفع للمستخدم {payment_request.user.email}', 'info')
    except Exception as e:
        flash(f'خطأ في رفض الطلب: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve-comment/<int:comment_id>', methods=['POST'])
@login_required
def admin_approve_comment(comment_id):
    """الموافقة على تعليق"""
    if not current_user.is_admin:
        flash('ليس لديك صلاحية لهذا الإجراء', 'error')
        return redirect(url_for('index'))
    
    comment = Comment.query.get_or_404(comment_id)
    
    try:
        comment.approve()
        flash('تم الموافقة على التعليق', 'success')
    except Exception as e:
        flash(f'خطأ في الموافقة على التعليق: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reject-comment/<int:comment_id>', methods=['POST'])
@login_required
def admin_reject_comment(comment_id):
    """رفض وحذف تعليق"""
    if not current_user.is_admin:
        flash('ليس لديك صلاحية لهذا الإجراء', 'error')
        return redirect(url_for('index'))
    
    comment = Comment.query.get_or_404(comment_id)
    
    try:
        comment.reject()
        flash('تم رفض وحذف التعليق', 'info')
    except Exception as e:
        flash(f'خطأ في رفض التعليق: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

# صفحة الشروط والأحكام
@app.route('/terms')
def terms():
    """صفحة الشروط والأحكام"""
    return render_template('terms.html')

@app.route('/payment/submit-transfer', methods=['POST'])
@login_required
def submit_transfer():
    """إرسال إثبات التحويل البنكي"""
    transfer_reference = request.form.get('transfer_reference')
    transfer_date = request.form.get('transfer_date')
    transfer_amount = request.form.get('transfer_amount')
    notes = request.form.get('notes', '')
    
    if not transfer_reference or not transfer_date or not transfer_amount:
        flash('يرجى إدخال جميع البيانات المطلوبة', 'error')
        return redirect(url_for('bank_transfer_payment'))
    
    # التحقق من المبلغ
    try:
        amount = float(transfer_amount)
        if amount < 500:
            flash('المبلغ المحول يجب أن يكون 500 ريال على الأقل', 'error')
            return redirect(url_for('bank_transfer_payment'))
    except ValueError:
        flash('يرجى إدخال مبلغ صحيح', 'error')
        return redirect(url_for('bank_transfer_payment'))
    
    # إنشاء طلب تفعيل اشتراك
    payment_request = PaymentRequest()
    payment_request.user_id = current_user.id
    payment_request.amount = amount
    payment_request.currency = 'SAR'
    payment_request.payment_method = 'bank_transfer'
    payment_request.transfer_reference = transfer_reference
    payment_request.transfer_date = transfer_date
    payment_request.notes = notes
    payment_request.status = 'pending'
    
    try:
        db.session.add(payment_request)
        db.session.commit()
        flash('تم إرسال طلب التفعيل بنجاح! سيتم مراجعته خلال 24 ساعة وتفعيل اشتراكك.', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        db.session.rollback()
        logging.error(f"خطأ في حفظ طلب الدفع: {e}")
        flash('حدث خطأ أثناء إرسال الطلب', 'error')
        return redirect(url_for('bank_transfer_payment'))

@app.route('/register-new-user', methods=['GET', 'POST'])
def register_new_user():
    """تسجيل مستخدم جديد للتجربة المجانية"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # جمع معلومات بصمة الجهاز
        user_agent = request.headers.get('User-Agent', '')
        ip_address = request.remote_addr
        screen_resolution = request.form.get('screen_resolution', '')
        timezone = request.form.get('timezone', '')
        language = request.form.get('language', 'ar')
        
        # إنشاء بصمة الجهاز
        fingerprint_hash = DeviceFingerprint.generate_fingerprint(
            user_agent, ip_address, screen_resolution, timezone, language
        )
        
        # التحقق من استخدام التجربة المجانية مسبقاً
        if DeviceFingerprint.has_used_trial(fingerprint_hash):
            flash('تم استخدام التجربة المجانية مسبقاً من هذا الجهاز. يرجى الاشتراك للمتابعة.', 'error')
            return render_template('register_new.html')
        
        # التحقق من صحة البيانات
        if not email or not password or not confirm_password:
            flash('يرجى ملء جميع الحقول', 'error')
            return render_template('register_new.html')
        
        if password != confirm_password:
            flash('كلمات المرور غير متطابقة', 'error')
            return render_template('register_new.html')
        
        if len(password) < 6:
            flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'error')
            return render_template('register_new.html')
        
        # التحقق من عدم وجود مستخدم بنفس الإيميل
        if User.query.filter_by(email=email).first():
            flash('الإيميل موجود بالفعل', 'error')
            return render_template('register_new.html')
        
        # إنشاء مستخدم جديد
        from flask_login import login_user
        new_user = User()
        new_user.email = email
        new_user.username = email.split('@')[0]
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            
            # إنشاء اشتراك تجريبي
            trial_subscription = Subscription()
            trial_subscription.user_id = new_user.id
            trial_subscription.status = 'trial'
            db.session.add(trial_subscription)
            
            # حفظ بصمة الجهاز
            device_fingerprint = DeviceFingerprint()
            device_fingerprint.user_id = new_user.id
            device_fingerprint.fingerprint_hash = fingerprint_hash
            device_fingerprint.user_agent = user_agent
            device_fingerprint.ip_address = ip_address
            device_fingerprint.screen_resolution = screen_resolution
            device_fingerprint.timezone = timezone
            device_fingerprint.language = language
            device_fingerprint.trial_used = True
            db.session.add(device_fingerprint)
            
            db.session.commit()
            
            login_user(new_user)
            flash(f'مرحباً بك! لديك فترة تجريبية مجانية لمدة 12 ساعة.', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating user: {e}")
            flash('حدث خطأ أثناء إنشاء الحساب', 'error')
    
    return render_template('register_new.html')

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
        
        return redirect(checkout_session.url, code=303)
        
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
