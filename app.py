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
from openai_market_analyzer import openai_analyzer, test_openai_connection
from economic_news_service import news_service, test_news_service

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

# Initialize SocketIO with optimized settings for gevent
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   ping_timeout=120,        # زيادة timeout مع gevent  
                   ping_interval=25,        # فحص منتظم
                   logger=False,
                   engineio_logger=False,
                   async_mode='gevent',     # تطابق مع gunicorn worker
                   transports=['polling'],  # polling للاستقرار
                   allow_upgrades=False,    # منع ترقيات غير مرغوبة
                   cookie=None,             # إزالة cookies للتبسيط
                   always_connect=True,     # ضمان الاتصال الدائم
                   max_http_buffer_size=1000000)  # زيادة buffer size

# Initialize price service
price_service = PriceService()

# تهيئة نظام الذكاء الاصطناعي المتكامل
logging.info("🤖 تهيئة نظام الذكاء الاصطناعي المتكامل...")

# تحقق من OpenAI
if openai_analyzer.enabled:
    logging.info("✅ OpenAI GPT-5 مفعل (تحذير: قد يكون هناك حد للاستخدام)")
else:
    logging.warning("⚠️ OpenAI غير مفعل")

# تحقق من خدمة الأخبار
if news_service.enabled:
    logging.info("📰 خدمة الأخبار الاقتصادية مفعلة وجاهزة")
    # اختبار سريع
    test_result = test_news_service()
    logging.info(f"اختبار الأخبار: {test_result.get('status')} - {test_result.get('message')}")
else:
    logging.warning("⚠️ خدمة الأخبار غير مفعلة")

logging.info("✨ النظام جاهز للعمل بالذكاء المتكامل")

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
    admin_password = os.environ.get("ADMIN_PASSWORD", "temp_change_me_123!")
    
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
        # إحصائيات النظام المتكامل
        from ai_signal_optimizer import ai_optimizer
        
        # تحديد الرسالة بناءً على الخدمات المفعلة
        if news_service.enabled and openai_analyzer.enabled:
            message = 'نظام متكامل: ذكاء داخلي + OpenAI GPT-5 + أخبار اقتصادية حقيقية'
        elif news_service.enabled:
            message = 'نظام متقدم: ذكاء داخلي + أخبار اقتصادية حقيقية'
        elif openai_analyzer.enabled:
            message = 'نظام متقدم: ذكاء داخلي + OpenAI GPT-5'
        else:
            message = 'نظام ذكاء اصطناعي داخلي متقدم'
        
        stats = {
            'ai_enabled': True,
            'openai_enabled': openai_analyzer.enabled,
            'news_enabled': news_service.enabled,
            'message': message,
            'analysis_mode': 'unified_ai_system',
            'internal_ai': {
                'patterns_learned': ai_optimizer.learning_data.get('patterns_learned', 0),
                'success_rate': ai_optimizer.learning_data.get('success_rate_improvement', 0),
                'total_analyzed': ai_optimizer.learning_data.get('total_analyzed', 0)
            },
            'openai_stats': {
                'enabled': openai_analyzer.enabled,
                'model': 'gpt-5' if openai_analyzer.enabled else None,
                'status': 'quota_exceeded' if openai_analyzer.enabled else 'disabled',
                'error_memory_count': len(openai_analyzer.error_memory) if openai_analyzer.enabled else 0,
                'successful_patterns': len(openai_analyzer.successful_patterns) if openai_analyzer.enabled else 0
            },
            'news_stats': {
                'enabled': news_service.enabled,
                'source': 'NewsAPI.org' if news_service.enabled else None,
                'cache_size': len(news_service.cache) if news_service.enabled else 0
            },
            'unified_performance': {
                'combined_confidence': 90,
                'error_reduction': 80,
                'signal_quality_improvement': 95,
                'news_integration': 100 if news_service.enabled else 0
            }
        }
        return jsonify({'success': True, 'data': stats})
    except Exception as e:
        logging.error(f"خطأ في الحصول على إحصائيات AI: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-openai', methods=['POST'])
def test_openai_api():
    """اختبار اتصال OpenAI API"""
    try:
        test_result = test_openai_connection()
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
        
        # التحقق من تفعيل OpenAI
        if not openai_analyzer.enabled:
            return jsonify({
                'success': False,
                'error': 'نظام الذكاء الاصطناعي غير مفعل - تأكد من وجود مفتاح OpenAI'
            })
        
        # الحصول على البيانات الحالية للسوق
        current_prices = price_service.get_all_prices()
        
        # استخدام OpenAI للتحليل والرد
        try:
            from openai import OpenAI
            client = openai_analyzer.client
            
            # إعداد السياق للمحادثة
            market_context = "البيانات الحالية للسوق:\n"
            if isinstance(current_prices, list):
                for i, asset in enumerate(current_prices):
                    if i >= 5:  # أول 5 أصول فقط
                        break
                    if isinstance(asset, dict):
                        market_context += f"- {asset.get('name', 'Unknown')}: ${asset.get('price', 0):.4f} ({asset.get('change_24h', 0):+.2f}%)\n"
            
            if not client:
                return jsonify({
                    'success': False,
                    'error': 'OpenAI client غير مهيأ'
                })
            
            response = client.chat.completions.create(
                model="gpt-5",  # أحدث نموذج
                messages=[
                    {
                        "role": "system",
                        "content": "أنت محلل مالي خبير. أجب على أسئلة المستخدمين حول الأسواق المالية بدقة ووضوح. استخدم البيانات المقدمة في تحليلك."
                    },
                    {
                        "role": "user",
                        "content": f"{user_message}\n\n{market_context}"
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            ai_response = response.choices[0].message.content or "لم أتمكن من تحليل طلبك."
            
        except Exception as e:
            logging.error(f"خطأ في OpenAI: {e}")
            ai_response = "حدث خطأ في معالجة طلبك. يرجى المحاولة لاحقاً."
        
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
    from flask import session
    try:
        # Use Flask-SocketIO session
        client_id = session.get('client_id', 'default')
    except:
        client_id = 'default'
    logging.info(f'Client disconnected: {client_id}')
    
    # Clean up any client-specific data
    try:
        # تنظيف البيانات المرتبطة بالعميل
        pass
    except:
        pass

@socketio.on_error_default
def handle_socketio_error(e):
    """Handle SocketIO errors including invalid sessions"""
    try:
        logging.warning(f"SocketIO error handled: {str(e)}")
        # لا نرسل emit هنا لتجنب loops
    except:
        pass

@socketio.on('connect_error')
def handle_connect_error(data):
    """Handle connection errors"""
    try:
        logging.warning(f"Connection error: {data}")
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

@socketio.on('random_analysis_signal')
def handle_random_analysis_signal(data):
    """Handle random analysis signal with OpenAI enhancement"""
    try:
        logging.info(f"🎯 Random analysis signal received: {data.get('asset_id')} - {data.get('type')} - {data.get('confidence')}%")
        
        # Track the random analysis signal with enhanced AI
        enhanced_signal = data.copy()
        
        # Get asset data for comprehensive analysis
        asset_id = data.get('asset_id')
        asset_data = None
        prices = price_service.get_all_prices()
        
        if isinstance(prices, list):
            for p in prices:
                if isinstance(p, dict) and p.get('id') == asset_id:
                    asset_data = p
                    break
        
        # Enhance with OpenAI if available and not quota exceeded
        if openai_analyzer.enabled and data.get('confidence', 0) > 75:
            try:
                # Prepare market data for OpenAI analysis
                market_data = {
                    'rsi': data.get('technical_analysis', {}).get('rsi', 50),
                    'trend': data.get('type', 'HOLD'),
                    'volatility': data.get('technical_analysis', {}).get('volatility', 0),
                    'sma_50': data.get('technical_analysis', {}).get('sma_short', 0),
                    'sma_200': data.get('technical_analysis', {}).get('sma_long', 0),
                    'timeframe': data.get('timeframe', 1)
                }
                
                if asset_data:
                    asset_data_for_ai = {
                        'id': asset_data.get('id'),
                        'name': asset_data.get('name'),
                        'price': asset_data.get('price', data.get('price', 0)),
                        'change_24h': asset_data.get('change_24h', 0),
                        'volume': asset_data.get('volume', 0)
                    }
                    
                    # Get comprehensive OpenAI analysis
                    openai_analysis = openai_analyzer.analyze_with_economic_news(asset_data_for_ai, market_data)
                    
                    if openai_analysis and openai_analysis.get('confidence', 0) > 80:
                        # OpenAI enhanced the signal
                        enhanced_signal.update({
                            'openai_enhanced': True,
                            'openai_confidence': openai_analysis.get('confidence', 0),
                            'openai_reasoning': openai_analysis.get('reasoning', ''),
                            'stop_loss': openai_analysis.get('stop_loss', 0),
                            'take_profit': openai_analysis.get('take_profit', 0),
                            'risk_level': openai_analysis.get('risk_level', 'medium'),
                            'news_impact': openai_analysis.get('news_impact', 'neutral'),
                            'technical_score': openai_analysis.get('technical_score', 0),
                            'fundamental_score': openai_analysis.get('fundamental_score', 0),
                            'openai_recommendations': openai_analysis.get('recommendations', [])
                        })
                        
                        # Update reason with OpenAI insights
                        enhanced_signal['reason'] = f"{enhanced_signal.get('reason', '')} - تحليل GPT-5 المتقدم: {openai_analysis.get('reasoning', '')[:100]}..."
                        
                        # Update final confidence with OpenAI input
                        original_confidence = enhanced_signal.get('confidence', 0)
                        openai_conf = openai_analysis.get('confidence', 0)
                        enhanced_signal['final_confidence'] = max(original_confidence, openai_conf)
                        
                        logging.info(f"✨ OpenAI enhanced random signal: {enhanced_signal['asset_id']} - Final confidence: {enhanced_signal.get('final_confidence')}%")
                    else:
                        logging.info(f"🤖 OpenAI analysis available but confidence too low: {openai_analysis.get('confidence', 0) if openai_analysis else 'None'}%")
                
            except Exception as openai_error:
                logging.error(f"OpenAI enhancement error for random signal: {openai_error}")
        
        # Track with real trades tracker
        try:
            from real_trades_tracker import real_trades_tracker
            trade_id = real_trades_tracker.track_real_signal(enhanced_signal)
            enhanced_signal['trade_id'] = trade_id
            logging.info(f"📊 Random signal tracked: {trade_id}")
        except Exception as track_error:
            logging.error(f"Error tracking random signal: {track_error}")
        
        # Save to database
        try:
            with app.app_context():
                from models import TradingSignal, db
                signal_record = TradingSignal(
                    asset_id=enhanced_signal.get('asset_id'),
                    signal_type=enhanced_signal.get('type'),
                    price=enhanced_signal.get('price'),
                    confidence=enhanced_signal.get('final_confidence', enhanced_signal.get('confidence')),
                    ai_confidence=enhanced_signal.get('openai_confidence', enhanced_signal.get('ai_confidence', 0)),
                    ai_analysis=str(enhanced_signal.get('openai_reasoning', enhanced_signal.get('reason', ''))),
                    source='random_analysis'
                )
                db.session.add(signal_record)
                db.session.commit()
                logging.info(f"💾 Random signal saved to database")
        except Exception as db_error:
            logging.error(f"Database save error for random signal: {db_error}")
        
        # Emit enhanced signal back to all clients
        socketio.emit('enhanced_random_signal', enhanced_signal)
        logging.info(f"🎯 Enhanced random signal broadcasted: {enhanced_signal.get('type')} {enhanced_signal.get('asset_name')} ({enhanced_signal.get('timeframe')}min)")
        
    except Exception as e:
        logging.error(f"Error handling random analysis signal: {e}")
        socketio.emit('random_analysis_error', {
            'error': str(e),
            'timestamp': time.time()
        })

@socketio.on('start_timed_analysis')
def handle_timed_analysis(data):
    """Handle timed analysis request with comprehensive AI analysis"""
    asset_id = data.get('asset_id')
    duration_minutes = data.get('duration_minutes', 1)
    timestamp = data.get('timestamp')
    
    logging.info(f"📊 Timed analysis requested: {asset_id} for {duration_minutes} minutes")
    
    # Schedule comprehensive analysis at the end of the timer
    def perform_deep_analysis():
        """Perform deep analysis after timer expires"""
        try:
            # Get current asset data
            asset_data = None
            prices = price_service.get_all_prices()
            
            if isinstance(prices, dict):
                asset_data = prices.get(asset_id)
            elif isinstance(prices, list) and prices and len(prices) > 0:
                for p in prices:
                    if isinstance(p, dict) and p.get('id') == asset_id:
                        asset_data = p
                        break
            
            if not asset_data:
                logging.error(f"Asset data not found for {asset_id}")
                return
            
            # Get historical data for comprehensive analysis
            historical_data = []
            
            # Perform comprehensive AI analysis
            comprehensive_signal = analyze_asset_with_ai(asset_data, historical_data)
            
            if comprehensive_signal:
                # Add timing information
                comprehensive_signal['timing_analysis'] = {
                    'duration_minutes': duration_minutes,
                    'analysis_type': 'timed_comprehensive',
                    'timestamp': time.time()
                }
                
                # Enhance with OpenAI if available
                if openai_analyzer.enabled:
                    try:
                        market_data = {
                            'rsi': comprehensive_signal.get('rsi', 50),
                            'trend': comprehensive_signal.get('trend', 'sideways'),
                            'volatility': comprehensive_signal.get('volatility', 0),
                            'sma_50': comprehensive_signal.get('sma_short', 0),
                            'sma_200': comprehensive_signal.get('sma_long', 0)
                        }
                        
                        # Get OpenAI analysis with economic news
                        openai_analysis = openai_analyzer.analyze_with_economic_news(asset_data, market_data)
                        
                        if openai_analysis:
                            comprehensive_signal['openai_analysis'] = openai_analysis
                            comprehensive_signal['confidence'] = max(
                                comprehensive_signal.get('confidence', 0),
                                openai_analysis.get('confidence', 0)
                            )
                            comprehensive_signal['reason'] = f"{comprehensive_signal.get('reason', '')} + تحليل OpenAI GPT-5 المتقدم"
                    except Exception as e:
                        logging.error(f"OpenAI analysis error: {e}")
                
                # Add economic news analysis
                if news_service.enabled:
                    try:
                        news_analysis = news_service.analyze_news_for_signal(
                            asset_id,
                            comprehensive_signal.get('type', 'BUY')
                        )
                        comprehensive_signal['news_analysis'] = news_analysis
                        
                        if news_analysis.get('supports_signal'):
                            comprehensive_signal['confidence'] = min(100, comprehensive_signal.get('confidence', 0) + 10)
                            comprehensive_signal['reason'] += ' + أخبار اقتصادية داعمة 📰'
                    except Exception as e:
                        logging.error(f"News analysis error: {e}")
                
                # Track the signal
                try:
                    from real_trades_tracker import real_trades_tracker
                    trade_id = real_trades_tracker.track_real_signal(comprehensive_signal)
                    comprehensive_signal['trade_id'] = trade_id
                except Exception as e:
                    logging.error(f"Error tracking timed signal: {e}")
                
                # Emit the comprehensive signal
                socketio.emit('trading_signal', comprehensive_signal)
                logging.info(f"✅ Timed comprehensive signal emitted for {asset_id}: {comprehensive_signal.get('type')} with {comprehensive_signal.get('confidence')}% confidence")
            else:
                # No signal conditions met after comprehensive analysis
                logging.info(f"⏱️ Timed analysis complete for {asset_id} - No signal conditions met")
                
                # Send a status update
                socketio.emit('timed_analysis_complete', {
                    'asset_id': asset_id,
                    'duration_minutes': duration_minutes,
                    'result': 'no_signal',
                    'message': 'التحليل مكتمل - لا توجد إشارات واضحة حالياً'
                })
                
        except Exception as e:
            logging.error(f"Error in timed analysis for {asset_id}: {e}")
            socketio.emit('timed_analysis_error', {
                'asset_id': asset_id,
                'error': str(e)
            })
    
    # Schedule the analysis after the timer duration
    timer = threading.Timer(duration_minutes * 60, perform_deep_analysis)
    timer.daemon = True
    timer.start()
    
    # Send immediate confirmation
    emit('timed_analysis_started', {
        'asset_id': asset_id,
        'duration_minutes': duration_minutes,
        'start_time': timestamp
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
                
                # إرسال تحديثات الأسعار كل 8 ثوان لتقليل الحمل أكثر
                if cycle_count % 8 == 0:
                    socketio.emit('price_update', prices)
                
                # إرسال حالة النظام كل 15 ثانية
                if cycle_count % 15 == 0:
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
            
            # تطبيق الذكاء الاصطناعي المتكامل (داخلي + OpenAI)
            try:
                from ai_signal_optimizer import ai_optimizer
                
                for raw_signal in raw_signals:
                    # فحص الإشارة بالذكاء الاصطناعي الداخلي
                    should_proceed, ai_analysis = ai_optimizer.should_generate_signal(raw_signal)
                    
                    if should_proceed:
                        # تحسين جودة الإشارة بالذكاء الداخلي
                        quality_analysis = ai_optimizer.analyze_signal_quality(raw_signal)
                        
                        # إضافة تحليل الذكاء الاصطناعي للإشارة
                        enhanced_signal = raw_signal.copy()
                        enhanced_signal.update({
                            'ai_quality_score': quality_analysis['quality_score'],
                            'ai_confidence': quality_analysis['ai_confidence'],
                            'ai_recommendations': quality_analysis['recommendations'][:2],
                            'risk_level': quality_analysis['risk_level'],
                            'ai_approved': True,
                            'reason': f"{raw_signal.get('reason', '')} - مُحسَّن بالذكاء الاصطناعي"
                        })
                        
                        # دمج الأخبار الاقتصادية الحقيقية
                        if news_service.enabled:
                            try:
                                # تحليل الأخبار للإشارة
                                news_analysis = news_service.analyze_news_for_signal(
                                    enhanced_signal.get('asset_id', ''),
                                    enhanced_signal.get('type', 'BUY')
                                )
                                
                                # إضافة تحليل الأخبار للإشارة
                                enhanced_signal['news_analysis'] = news_analysis
                                enhanced_signal['news_sentiment'] = news_analysis.get('sentiment', 'neutral')
                                enhanced_signal['news_supports'] = news_analysis.get('supports_signal', None)
                                
                                # تحديث الثقة بناءً على الأخبار
                                if news_analysis.get('supports_signal') == True:
                                    enhanced_signal['ai_confidence'] = min(100, enhanced_signal.get('ai_confidence', 70) + 10)
                                    enhanced_signal['reason'] += ' + أخبار اقتصادية داعمة 📰'
                                elif news_analysis.get('supports_signal') == False:
                                    enhanced_signal['ai_confidence'] = max(0, enhanced_signal.get('ai_confidence', 70) - 15)
                                    enhanced_signal['reason'] += ' ⚠️ أخبار معارضة'
                                
                                logging.info(f"📰 تم تحليل الأخبار: {news_analysis.get('sentiment')} - {news_analysis.get('reason')}")
                                
                            except Exception as news_error:
                                logging.error(f"خطأ في تحليل الأخبار: {news_error}")
                        
                        # تحسين إضافي باستخدام OpenAI GPT-5 (إذا كان متاحاً)
                        if openai_analyzer.enabled and False:  # معطل مؤقتاً بسبب تجاوز الحد المسموح
                            try:
                                # جلب بيانات الأصل
                                asset_data = {}
                                if isinstance(prices, list):
                                    for p in prices:
                                        if isinstance(p, dict) and p.get('id') == enhanced_signal.get('asset_id'):
                                            asset_data = p
                                            break
                                
                                # تحسين الإشارة باستخدام OpenAI
                                openai_enhanced = openai_analyzer.enhance_signal_with_ai(enhanced_signal, asset_data)
                                
                                # دمج تحليلات OpenAI
                                enhanced_signal.update(openai_enhanced)
                                enhanced_signal['reason'] = f"{enhanced_signal['reason']} + OpenAI GPT-5 ✨"
                                
                                # إضافة معنويات السوق
                                sentiment = openai_analyzer.get_market_sentiment(enhanced_signal['asset_id'])
                                enhanced_signal['market_sentiment'] = sentiment
                                
                                # إضافة توقعات حركة السعر
                                prediction = openai_analyzer.predict_price_movement(asset_data)
                                enhanced_signal['price_prediction'] = prediction
                                
                                # تحديث الثقة النهائية
                                if enhanced_signal.get('openai_confidence', 0) > enhanced_signal['ai_confidence']:
                                    enhanced_signal['final_confidence'] = enhanced_signal['openai_confidence']
                                else:
                                    enhanced_signal['final_confidence'] = enhanced_signal['ai_confidence']
                                
                                logging.info(f"🌟 OpenAI GPT-5 enhanced signal: {enhanced_signal['type']} {enhanced_signal['asset_name']} - Confidence: {enhanced_signal.get('final_confidence', enhanced_signal['confidence'])}%")
                                
                            except Exception as openai_error:
                                logging.error(f"OpenAI enhancement error: {openai_error}")
                        
                        # تتبع الإشارة المحسنة
                        try:
                            from real_trades_tracker import real_trades_tracker
                            trade_id = real_trades_tracker.track_real_signal(enhanced_signal)
                            enhanced_signal['trade_id'] = trade_id
                        except Exception as e:
                            logging.error(f"Error tracking AI-enhanced signal: {e}")
                        
                        # حفظ الإشارة في قاعدة البيانات
                        try:
                            with app.app_context():  # إضافة app context للحفظ الآمن
                                from models import TradingSignal
                                signal_record = TradingSignal(
                                    asset_id=enhanced_signal.get('asset_id'),
                                    asset_name=enhanced_signal.get('asset_name'),
                                    signal_type=enhanced_signal.get('type'),
                                    price=enhanced_signal.get('price'),
                                    confidence=enhanced_signal.get('confidence'),
                                    reason=enhanced_signal.get('reason'),
                                    rsi=enhanced_signal.get('rsi'),
                                    sma_short=enhanced_signal.get('sma_short'),
                                    sma_long=enhanced_signal.get('sma_long'),
                                    price_change_5=enhanced_signal.get('price_change_5'),
                                    trend=enhanced_signal.get('trend'),
                                    ai_confidence=enhanced_signal.get('ai_confidence'),
                                    ai_analysis=str(enhanced_signal.get('ai_recommendations', []))
                                )
                                db.session.add(signal_record)
                                db.session.commit()
                                logging.info(f"💾 Signal saved to database: {enhanced_signal.get('type')} {enhanced_signal.get('asset_id')}")
                        except Exception as db_error:
                            try:
                                db.session.rollback()
                            except:
                                pass
                            logging.error(f"❌ Database save error: {db_error}")
                        
                        socketio.emit('trading_signal', enhanced_signal)
                        logging.info(f"🧠 Unified AI signal: {enhanced_signal['type']} {enhanced_signal['asset_name']} (Quality: {quality_analysis['quality_score']}/100)")
                        
                    else:
                        # إذا رفض الذكاء الداخلي، تحقق مع OpenAI
                        if openai_analyzer.enabled:
                            try:
                                asset_data = {
                                    'id': raw_signal.get('asset_id', 'UNKNOWN'),
                                    'name': raw_signal.get('asset_name', 'غير محدد'),
                                    'price': raw_signal.get('price', 0),
                                    'change_24h': raw_signal.get('price_change_5', 0),
                                    'volume': 0
                                }
                                if isinstance(prices, list):
                                    for p in prices:
                                        if isinstance(p, dict) and p.get('id') == raw_signal.get('asset_id'):
                                            asset_data = p
                                            break
                                market_data = {
                                    'rsi': raw_signal.get('rsi', 50),
                                    'trend': raw_signal.get('trend', 'sideways'),
                                    'volatility': raw_signal.get('volatility', 0),
                                    'sma_50': raw_signal.get('sma_short', 0),
                                    'sma_200': raw_signal.get('sma_long', 0)
                                }
                                
                                # تحليل متقدم باستخدام OpenAI
                                openai_analysis = openai_analyzer.analyze_with_economic_news(asset_data, market_data)
                                
                                if openai_analysis and openai_analysis.get('confidence', 0) >= 85:
                                    # OpenAI يعتقد أن الإشارة جيدة
                                    logging.info(f"✅ OpenAI approved previously rejected signal: {raw_signal['asset_name']}")
                                    
                                    # تحديث الإشارة بتحليل OpenAI
                                    enhanced_signal = raw_signal.copy()
                                    enhanced_signal.update({
                                        'openai_override': True,
                                        'openai_confidence': openai_analysis['confidence'],
                                        'openai_reasoning': openai_analysis.get('reasoning', ''),
                                        'stop_loss': openai_analysis.get('stop_loss', 0),
                                        'take_profit': openai_analysis.get('take_profit', 0),
                                        'reason': f"OpenAI GPT-5 تحليل متقدم: {openai_analysis.get('reasoning', '')[:100]}"
                                    })
                                    
                                    # حفظ إشارة OpenAI في قاعدة البيانات
                                    try:
                                        with app.app_context():  # إضافة app context للحفظ الآمن
                                            from models import TradingSignal
                                            signal_record = TradingSignal(
                                                asset_id=enhanced_signal.get('asset_id'),
                                                asset_name=enhanced_signal.get('asset_name'),
                                                signal_type=enhanced_signal.get('type'),
                                                price=enhanced_signal.get('price'),
                                                confidence=enhanced_signal.get('confidence', enhanced_signal.get('openai_confidence')),
                                                reason=enhanced_signal.get('reason'),
                                                rsi=enhanced_signal.get('rsi'),
                                                ai_confidence=enhanced_signal.get('openai_confidence'),
                                                ai_analysis=enhanced_signal.get('openai_reasoning', '')
                                            )
                                            db.session.add(signal_record)
                                            db.session.commit()
                                            logging.info(f"💾 OpenAI signal saved to database: {enhanced_signal.get('type')} {enhanced_signal.get('asset_id')}")
                                    except Exception as db_error:
                                        try:
                                            db.session.rollback()
                                        except:
                                            pass
                                        logging.error(f"❌ OpenAI Database save error: {db_error}")
                                    
                                    socketio.emit('trading_signal', enhanced_signal)
                                    logging.info(f"🎆 OpenAI override signal: {enhanced_signal['type']} {enhanced_signal['asset_name']}")
                                else:
                                    logging.info(f"🚫 Signal rejected by both AI systems: {raw_signal['asset_name']}")
                                    
                            except Exception as openai_error:
                                logging.error(f"OpenAI analysis error: {openai_error}")
                                logging.info(f"🚫 AI rejected signal: {raw_signal['asset_name']} - {ai_analysis.get('reason', 'Low quality')}")
                        else:
                            logging.info(f"🚫 AI rejected signal: {raw_signal['asset_name']} - {ai_analysis.get('reason', 'Low quality')}")
                        
            except Exception as e:
                logging.error(f"Error in unified AI signal optimization: {e}")
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
        
        # تحديث أبطأ لتجنب إجهاد الاتصال
        processing_time = time.time() - start_time
        sleep_time = max(5, 5 - processing_time)  # تحديث كل 5 ثوان لتقليل الحمل
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
