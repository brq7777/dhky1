import os
import logging
from datetime import timedelta, datetime
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, login_required, logout_user, current_user
import threading
import time
from api_service import PriceService
from market_ai_engine import analyze_asset_with_ai, get_ai_engine_status
from comprehensive_trades_tracker import trades_tracker

# Set up logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# إعداد قاعدة البيانات مع إعدادات محسنة للاستقرار
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
    'pool_timeout': 20,
    'max_overflow': 10
}

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

# Initialize SocketIO optimized for gunicorn deployment
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   ping_timeout=60,        # مهلة مناسبة للنشر
                   ping_interval=25,       # فحص منتظم للاستقرار
                   logger=False,
                   engineio_logger=False,
                   async_mode='threading',
                   transports=['polling'],  # polling فقط لضمان الاستقرار مع gunicorn
                   allow_upgrades=False,    # منع الترقية لتجنب مشاكل WebSocket
                   cookie=False)

# Initialize price service
price_service = PriceService()

# إنشاء جداول قاعدة البيانات وإنشاء المستخدم الافتراضي
with app.app_context():
    # إعداد قاعدة البيانات بأمان
    try:
        # إنشاء الجداول إذا لم تكن موجودة
        db.create_all()
        logging.info("✅ تم إعداد قاعدة البيانات بنجاح")
    except Exception as e:
        logging.warning(f"تحذير في قاعدة البيانات: {e}")
        try:
            # إنشاء الجداول مرة أخرى
            db.create_all()
        except Exception as e2:
            logging.error(f"خطأ في إعداد قاعدة البيانات: {e2}")
    
    # إنشاء المستخدم الافتراضي كمدير
    admin_email = "brq7787@gmail.com"
    admin_password = "Msken2009"
    
    admin_user = User()
    admin_user.email = admin_email
    admin_user.username = "Admin"
    admin_user.is_admin = True  # تعيين كمدير
    admin_user.set_password(admin_password)
    
    try:
        # التحقق من وجود المستخدم أولاً
        existing_user = User.query.filter_by(email=admin_email).first()
        if not existing_user:
            db.session.add(admin_user)
            db.session.commit()
            
            # إنشاء اشتراك دائم للمدير
            admin_subscription = Subscription()
            admin_subscription.user_id = admin_user.id
            admin_subscription.status = 'active'
            admin_subscription.subscription_start = datetime.utcnow()
            admin_subscription.subscription_end = datetime.utcnow() + timedelta(days=365 * 10)
            
            db.session.add(admin_subscription)
            db.session.commit()
            
            logging.info(f"تم إنشاء المستخدم الافتراضي كمدير: {admin_email}")
        else:
            logging.info(f"المستخدم الافتراضي موجود مسبقاً: {admin_email}")
    except Exception as e:
        db.session.rollback()
        logging.warning(f"تحذير في إعداد المستخدم الافتراضي: {e}")

@app.route('/')
def index():
    """الصفحة الرئيسية للوحة التحكم - تتطلب تسجيل الدخول فقط"""
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

@app.route('/api/ai-status')
def get_ai_status():
    """Get AI engine status"""
    try:
        ai_status = get_ai_engine_status()
        return jsonify({'success': True, 'data': ai_status})
    except Exception as e:
        logging.error(f"Error getting AI status: {e}")
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
        # إعادة إحصائيات افتراضية لأن النظام يعمل بدون AI
        stats = {
            'ai_enabled': False,
            'message': 'النظام يعمل بالتحليل الفني المستقل',
            'analysis_mode': 'independent_technical'
        }
        return jsonify({'success': True, 'data': stats})
    except Exception as e:
        logging.error(f"خطأ في الحصول على إحصائيات AI: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-openai', methods=['POST'])
def test_openai_api():
    """اختبار اتصال OpenAI API"""
    try:
        # النظام يعمل بدون AI حالياً
        test_result = {
            'status': 'disabled',
            'connected': False,
            'message': 'النظام يعمل بالتحليل الفني المستقل بدون AI'
        }
        return jsonify({'success': True, 'data': test_result})
    except Exception as e:
        logging.error(f"خطأ في اختبار OpenAI API: {str(e)}")
        return jsonify({
            'success': False,
            'data': {
                'status': 'error',
                'connected': False,
                'message': f'خطأ في الاختبار: {str(e)}'
            }
        })

@app.route('/api/ai-chat', methods=['POST'])
def ai_chat():
    """دردشة مع الذكاء الاصطناعي للتحليل المالي"""
    try:
        # الحصول على رسالة المستخدم
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': 'يرجى كتابة رسالة'
            })
        
        # التحقق من طول الرسالة
        if len(user_message) > 500:
            return jsonify({
                'success': False,
                'error': 'الرسالة طويلة جداً (الحد الأقصى 500 حرف)'
            })
        
        # النظام يعمل بدون AI حالياً
        if True:  # النظام مصمم للعمل بدون AI
            return jsonify({
                'success': False,
                'error': 'نظام الذكاء الاصطناعي غير متاح حالياً'
            })
        
        # الحصول على البيانات الحالية للسوق
        current_prices = price_service.get_all_prices()
        
        # رد تلقائي بدون AI
        ai_response = f'النظام يعمل حالياً بالتحليل الفني المستقل. تم استلام رسالتك: "{user_message}" - يمكنك مراقبة الإشارات الفنية المتقدمة على الشاشة.'
        
        return jsonify({
            'success': True,
            'data': {
                'message': ai_response,
                'timestamp': datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        logging.error(f"خطأ في دردشة AI: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'حدث خطأ: {str(e)}'
        })

@app.route('/api/test-signal/<asset_id>')
def test_signal(asset_id):
    """إنشاء إشارة اختبارية للتجربة"""
    signal = {
        'asset_id': asset_id,
        'asset_name': asset_id,
        'type': 'BUY',
        'price': 50000,
        'confidence': 95,
        'timestamp': time.time(),
        'reason': 'اختبار الإشارة'
    }
    
    # إرسال إشارة اختبارية
    socketio.emit('trading_signal', signal)
    
    return jsonify({
        'success': True,
        'message': f'تم إرسال إشارة اختبارية لـ {asset_id}',
        'signal': signal
    })

# تم حذف نظام تسجيل الدخول - الوصول مفتوح للجميع



@app.route('/create-stripe-session', methods=['POST'])
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

# تم حذف نظام تسجيل الخروج

@socketio.on('connect')
def handle_connect():
    """Handle client connection with session management"""
    from flask import session
    try:
        # Use Flask-SocketIO session
        client_id = session.get('client_id', 'default')
    except:
        client_id = 'default'
    logging.info(f'Client connected: {client_id}')
    
    # Send immediate confirmation
    emit('connected', {
        'message': 'Connected to price updates',
        'session_id': client_id,
        'timestamp': time.time()
    })
    
    # Send current system status immediately
    try:
        status = price_service.get_system_status()
        emit('system_status', status)
    except:
        pass

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection with cleanup"""
    try:
        # Use Flask-SocketIO session
        client_id = session.get('client_id', 'default')
    except:
        client_id = 'default'
    logging.info(f'Client disconnected: {client_id}')
    
    # Clean up any client-specific data
    try:
        # تنظيف البيانات المرتبطة بالعميل
        pass  # تمت إزالة هذه الوظيفة مؤقتاً
    except:
        pass

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
    cycle_count = 0  # Initialize cycle_count as local variable
    while True:
        start_time = time.time()
        try:
            # Get current prices - optimized call
            prices = price_service.get_all_prices()
            
            # Emit updates much less frequently to reduce network load
            if prices:
                # Only send updates every few cycles to avoid overwhelming the connection
                cycle_count += 1
                
                # إرسال تحديثات الأسعار فورياً بدون تأخير
                socketio.emit('price_update', prices)
                
                # إرسال حالة النظام كل دورتين (كل 3-6 ثوان)
                if cycle_count % 2 == 0:
                    status = price_service.get_system_status()
                    socketio.emit('system_status', status)
            
            # Check for triggered alerts - optimized
            triggered_alerts = price_service.check_alerts_fast(prices)
            for alert in triggered_alerts:
                socketio.emit('alert_triggered', alert)
                logging.info(f"Alert triggered: {alert}")
            
            # تحديث الأسعار الحالية للمتتبع الحقيقي
            try:
                from real_trades_tracker import real_trades_tracker
                real_trades_tracker.update_current_prices(prices)
            except Exception as e:
                logging.error(f"Error updating prices for tracker: {e}")

            # Generate trading signals with AI optimization
            raw_signals = price_service.generate_trading_signals_fast(prices)
            
            # تطبيق الذكاء الاصطناعي لتحسين الإشارات
            try:
                from ai_signal_optimizer import ai_optimizer
                
                for raw_signal in raw_signals:
                    # فحص الإشارة بالذكاء الاصطناعي
                    should_proceed, ai_analysis = ai_optimizer.should_generate_signal(raw_signal)
                    
                    if should_proceed:
                        # تحسين جودة الإشارة
                        quality_analysis = ai_optimizer.analyze_signal_quality(raw_signal)
                        
                        # إضافة تحليل الذكاء الاصطناعي للإشارة
                        enhanced_signal = raw_signal.copy()
                        enhanced_signal.update({
                            'ai_quality_score': quality_analysis['quality_score'],
                            'ai_confidence': quality_analysis['ai_confidence'],
                            'ai_recommendations': quality_analysis['recommendations'][:2],  # أهم توصيتين
                            'risk_level': quality_analysis['risk_level'],
                            'ai_approved': True,
                            'reason': f"{raw_signal.get('reason', '')} - مُحسَّن بالذكاء الاصطناعي ✨"
                        })
                        
                        # تتبع الإشارة المحسنة
                        try:
                            from real_trades_tracker import real_trades_tracker
                            trade_id = real_trades_tracker.track_real_signal(enhanced_signal)
                            enhanced_signal['trade_id'] = trade_id
                        except Exception as e:
                            logging.error(f"Error tracking AI-enhanced signal: {e}")
                        
                        socketio.emit('trading_signal', enhanced_signal)
                        logging.info(f"🧠 AI-Enhanced signal: {enhanced_signal['type']} {enhanced_signal['asset_name']} (Quality: {quality_analysis['quality_score']}/100)")
                        
                    else:
                        logging.info(f"🚫 AI rejected signal: {raw_signal['asset_name']} - {ai_analysis.get('reason', 'Low quality')}")
                        
            except Exception as e:
                logging.error(f"Error in AI signal optimization: {e}")
                # في حالة خطأ، استخدم الإشارات العادية
                for signal in raw_signals:
                    try:
                        from real_trades_tracker import real_trades_tracker
                        trade_id = real_trades_tracker.track_real_signal(signal)
                        signal['trade_id'] = trade_id
                    except Exception as e:
                        logging.error(f"Error tracking fallback signal: {e}")
                    
                    socketio.emit('trading_signal', signal)
                    logging.info(f"Fallback signal: {signal['type']} {signal['asset_name']} at {signal['price']}")
            
        except Exception as e:
            logging.error(f"Error in price monitor: {e}")
        
        # تحديث فوري للبيانات الحية
        processing_time = time.time() - start_time
        sleep_time = max(1, 2 - processing_time)  # تحديث كل 1-2 ثانية للسرعة القصوى
        time.sleep(sleep_time)

# API للحصول على إحصائيات الصفقات الحقيقية
@app.route('/api/trades-stats')
def get_trades_stats():
    """إحصائيات الصفقات الحقيقية من السوق مع تحليل الذكاء الاصطناعي"""
    try:
        from real_trades_tracker import real_trades_tracker
        from ai_signal_optimizer import ai_optimizer
        
        stats = real_trades_tracker.get_real_statistics(30)
        recommendations = real_trades_tracker.generate_real_recommendations()
        ai_report = ai_optimizer.get_ai_performance_report()
        
        return jsonify({
            'success': True,
            'stats': stats,
            'recommendations': recommendations,
            'ai_performance': ai_report
        })
    except Exception as e:
        logging.error(f"خطأ في جلب الإحصائيات الحقيقية: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/finalize-trade', methods=['POST'])
def finalize_trade():
    """إنهاء صفقة وتحديد نتيجتها"""
    try:
        data = request.get_json()
        trade_id = data.get('trade_id')
        exit_price = data.get('exit_price')
        is_winning = data.get('is_winning', True)
        analysis = data.get('analysis')
        
        trades_tracker.finalize_trade(trade_id, exit_price, is_winning, analysis)
        
        return jsonify({
            'success': True,
            'message': 'تم إنهاء الصفقة بنجاح'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# Start background price monitoring
price_monitor_thread = threading.Thread(target=price_monitor, daemon=True)
price_monitor_thread.start()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False, log_output=True)
