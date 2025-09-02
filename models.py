from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """نموذج المستخدم لقاعدة البيانات"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # علاقة مع الاشتراك
    subscription = db.relationship('Subscription', backref='user', uselist=False)
    device_fingerprints = db.relationship('DeviceFingerprint', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        """تشفير وحفظ كلمة المرور"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """التحقق من كلمة المرور"""
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        """إرجاع معرف المستخدم للجلسة"""
        return str(self.id)
    
    def has_active_subscription(self):
        """التحقق من وجود اشتراك نشط"""
        if not self.subscription:
            return False
        return self.subscription.is_active()
    
    def get_trial_remaining_hours(self):
        """الحصول على ساعات التجربة المتبقية"""
        if not self.subscription:
            return 0
        return self.subscription.get_trial_remaining_hours()
    
    def can_access_dashboard(self):
        """التحقق من إمكانية الوصول للوحة التحكم"""
        return self.is_admin or self.has_active_subscription() or self.get_trial_remaining_hours() > 0
    
    def __repr__(self):
        return f'<User {self.email}>'


class Subscription(db.Model):
    """نموذج الاشتراك"""
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # معلومات الاشتراك
    status = db.Column(db.String(20), default='trial')  # trial, active, expired, cancelled
    amount = db.Column(db.Float, default=500.0)  # 500 ريال سعودي
    currency = db.Column(db.String(3), default='SAR')
    
    # تواريخ مهمة
    trial_start = db.Column(db.DateTime, default=datetime.utcnow)
    trial_end = db.Column(db.DateTime)
    subscription_start = db.Column(db.DateTime)
    subscription_end = db.Column(db.DateTime)
    
    # معلومات الدفع
    stripe_customer_id = db.Column(db.String(100))
    stripe_subscription_id = db.Column(db.String(100))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.trial_end and self.trial_start:
            self.trial_end = self.trial_start + timedelta(hours=12)
    
    def is_trial_active(self):
        """التحقق من نشاط فترة التجربة"""
        now = datetime.utcnow()
        return self.status == 'trial' and now < self.trial_end
    
    def get_trial_remaining_hours(self):
        """الحصول على ساعات التجربة المتبقية"""
        if not self.is_trial_active():
            return 0
        remaining = self.trial_end - datetime.utcnow()
        return max(0, remaining.total_seconds() / 3600)
    
    def is_active(self):
        """التحقق من نشاط الاشتراك"""
        if self.is_trial_active():
            return True
        
        if self.status == 'active' and self.subscription_end:
            return datetime.utcnow() < self.subscription_end
        
        return False
    
    def activate_subscription(self, months=1):
        """تفعيل الاشتراك المدفوع"""
        self.status = 'active'
        self.subscription_start = datetime.utcnow()
        self.subscription_end = self.subscription_start + timedelta(days=30 * months)
    
    def __repr__(self):
        return f'<Subscription {self.status} for User {self.user_id}>'


class DeviceFingerprint(db.Model):
    """نموذج بصمة الجهاز لمنع التلاعب بالتجربة المجانية"""
    __tablename__ = 'device_fingerprints'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # بصمة الجهاز
    fingerprint_hash = db.Column(db.String(64), nullable=False, index=True)
    user_agent = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    screen_resolution = db.Column(db.String(20))
    timezone = db.Column(db.String(50))
    language = db.Column(db.String(10))
    
    # تتبع الاستخدام
    trial_used = db.Column(db.Boolean, default=False)
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @staticmethod
    def generate_fingerprint(user_agent, ip_address, screen_resolution, timezone, language):
        """إنشاء بصمة الجهاز"""
        data = f"{user_agent}|{ip_address}|{screen_resolution}|{timezone}|{language}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    def has_used_trial(fingerprint_hash):
        """التحقق من استخدام التجربة المجانية مسبقاً"""
        device = DeviceFingerprint.query.filter_by(
            fingerprint_hash=fingerprint_hash,
            trial_used=True
        ).first()
        return device is not None
    
    def mark_trial_used(self):
        """تعيين التجربة المجانية كمستخدمة"""
        self.trial_used = True
        db.session.commit()
    
    def __repr__(self):
        return f'<DeviceFingerprint {self.fingerprint_hash[:8]}... for User {self.user_id}>'


class PaymentRequest(db.Model):
    """نموذج طلبات الدفع والتفعيل"""
    __tablename__ = 'payment_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # معلومات الدفع
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='SAR')
    payment_method = db.Column(db.String(20), nullable=False)  # bank_transfer, stripe
    
    # معلومات التحويل البنكي
    transfer_reference = db.Column(db.String(100))
    transfer_date = db.Column(db.String(20))
    notes = db.Column(db.Text)
    
    # حالة الطلب
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    admin_notes = db.Column(db.Text)
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    processed_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    user = db.relationship('User', foreign_keys=[user_id], backref='payment_requests')
    processor = db.relationship('User', foreign_keys=[processed_by])
    
    def approve_payment(self, admin_user_id):
        """الموافقة على الطلب وتفعيل الاشتراك"""
        self.status = 'approved'
        self.processed_by = admin_user_id
        self.processed_at = datetime.utcnow()
        
        # تفعيل اشتراك المستخدم
        if self.user.subscription:
            self.user.subscription.activate_subscription()
        else:
            subscription = Subscription()
            subscription.user_id = self.user_id
            subscription.status = 'active'
            subscription.subscription_start = datetime.utcnow()
            subscription.subscription_end = datetime.utcnow() + timedelta(days=30)
            db.session.add(subscription)
        
        db.session.commit()
    
    def reject_payment(self, admin_user_id, reason):
        """رفض الطلب"""
        self.status = 'rejected'
        self.processed_by = admin_user_id
        self.processed_at = datetime.utcnow()
        self.admin_notes = reason
        db.session.commit()
    
    def __repr__(self):
        return f'<PaymentRequest {self.status} for User {self.user_id}>'


class Comment(db.Model):
    """نموذج التعليقات على المنتج"""
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer)  # تقييم من 1 إلى 5 نجوم
    is_approved = db.Column(db.Boolean, default=False)  # موافقة المدير
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # علاقة مع المستخدم
    user = db.relationship('User', backref=db.backref('comments', lazy=True))
    
    def approve(self):
        """الموافقة على التعليق"""
        self.is_approved = True
        db.session.commit()
    
    def reject(self):
        """رفض التعليق"""
        db.session.delete(self)
        db.session.commit()
    
    def __repr__(self):
        return f'<Comment by {self.user.email if self.user else "Unknown"}>'


class TradingSignal(db.Model):
    """نموذج الإشارات التجارية"""
    __tablename__ = 'trading_signals'
    
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.String(20), nullable=False, index=True)
    asset_name = db.Column(db.String(50), nullable=False)
    signal_type = db.Column(db.String(10), nullable=False)  # BUY/SELL
    
    # بيانات الإشارة
    price = db.Column(db.Float, nullable=False)
    confidence = db.Column(db.Integer, nullable=False)  # 1-100
    reason = db.Column(db.Text)
    
    # مؤشرات فنية
    rsi = db.Column(db.Float)
    sma_short = db.Column(db.Float)
    sma_long = db.Column(db.Float)
    price_change_5 = db.Column(db.Float)
    
    # تحليل الاتجاه
    trend = db.Column(db.String(20))  # uptrend/downtrend/sideways
    trend_strength = db.Column(db.Integer)
    
    # معلومات الدعم والمقاومة
    support_level = db.Column(db.Float)
    resistance_level = db.Column(db.Float)
    
    # تحليل الشموع
    candlestick_pattern = db.Column(db.String(50))
    pattern_reliability = db.Column(db.Integer)  # 1-100
    
    # نتيجة الإشارة
    is_successful = db.Column(db.Boolean)  # null = لم يتم التقييم بعد
    profit_loss_percent = db.Column(db.Float)  # النسبة المئوية للربح/الخسارة
    evaluation_time = db.Column(db.DateTime)  # وقت تقييم النتيجة
    
    # معلومات AI
    ai_analysis = db.Column(db.Text)  # تحليل OpenAI
    ai_confidence = db.Column(db.Integer)  # ثقة AI في الإشارة
    learning_features = db.Column(db.Text)  # features للتعلم (JSON)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        """تحويل الإشارة إلى dictionary"""
        return {
            'id': self.id,
            'asset_id': self.asset_id,
            'asset_name': self.asset_name,
            'signal_type': self.signal_type,
            'price': self.price,
            'confidence': self.confidence,
            'reason': self.reason,
            'rsi': self.rsi,
            'sma_short': self.sma_short,
            'sma_long': self.sma_long,
            'price_change_5': self.price_change_5,
            'trend': self.trend,
            'trend_strength': self.trend_strength,
            'support_level': self.support_level,
            'resistance_level': self.resistance_level,
            'candlestick_pattern': self.candlestick_pattern,
            'pattern_reliability': self.pattern_reliability,
            'is_successful': self.is_successful,
            'profit_loss_percent': self.profit_loss_percent,
            'ai_analysis': self.ai_analysis,
            'ai_confidence': self.ai_confidence,
            'created_at': self.created_at.timestamp() if self.created_at else None
        }
    
    def evaluate_success(self, current_price: float, hours_later: int = 24):
        """تقييم نجاح الإشارة بناءً على السعر الحالي"""
        if self.evaluation_time:
            return  # تم التقييم مسبقاً
        
        price_change = ((current_price - self.price) / self.price) * 100
        
        if self.signal_type == 'BUY':
            self.is_successful = price_change > 0.5  # ربح أكثر من 0.5%
            self.profit_loss_percent = price_change
        else:  # SELL
            self.is_successful = price_change < -0.5  # انخفاض أكثر من 0.5%
            self.profit_loss_percent = -price_change
        
        self.evaluation_time = datetime.utcnow()
        db.session.commit()
    
    @staticmethod
    def get_failed_signals_patterns(asset_id = None, limit: int = 100):
        """الحصول على أنماط الإشارات الفاشلة للتعلم منها"""
        query = TradingSignal.query.filter(
            TradingSignal.is_successful == False,
            TradingSignal.evaluation_time != None
        )
        
        if asset_id:
            query = query.filter(TradingSignal.asset_id == asset_id)
        
        return query.order_by(TradingSignal.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_successful_signals_patterns(asset_id = None, limit: int = 100):
        """الحصول على أنماط الإشارات الناجحة للتعلم منها"""
        query = TradingSignal.query.filter(
            TradingSignal.is_successful == True,
            TradingSignal.evaluation_time != None
        )
        
        if asset_id:
            query = query.filter(TradingSignal.asset_id == asset_id)
        
        return query.order_by(TradingSignal.created_at.desc()).limit(limit).all()
    
    def __repr__(self):
        return f'<TradingSignal {self.signal_type} {self.asset_id} at {self.price}>'


class AILearningData(db.Model):
    """نموذج بيانات التعلم للذكاء الاصطناعي"""
    __tablename__ = 'ai_learning_data'
    
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.String(20), nullable=False, index=True)
    
    # أنماط الإشارات الفاشلة
    failed_pattern_type = db.Column(db.String(50))  # نوع النمط الفاشل
    failed_conditions = db.Column(db.Text)  # الشروط التي أدت للفشل (JSON)
    failure_reason = db.Column(db.Text)  # سبب الفشل
    
    # معايير التجنب
    avoid_when_rsi_above = db.Column(db.Float)
    avoid_when_rsi_below = db.Column(db.Float)
    avoid_when_trend = db.Column(db.String(20))
    avoid_when_volatility_above = db.Column(db.Float)
    
    # نمط الشموع المتجنب
    avoid_candlestick_pattern = db.Column(db.String(50))
    
    # إحصائيات
    failure_count = db.Column(db.Integer, default=1)
    last_failure_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # وزن التجنب (كلما زاد الوزن، كلما تم تجنب النمط أكثر)
    avoidance_weight = db.Column(db.Float, default=1.0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def increase_avoidance(self):
        """زيادة وزن التجنب عند تكرار الفشل"""
        self.failure_count += 1
        self.last_failure_date = datetime.utcnow()
        self.avoidance_weight = min(self.avoidance_weight * 1.2, 5.0)  # حد أقصى 5
        db.session.commit()
    
    @staticmethod
    def should_avoid_signal(asset_id: str, signal_data: dict) -> tuple[bool, str]:
        """فحص ما إذا كان يجب تجنب إرسال إشارة معينة"""
        learning_rules = AILearningData.query.filter_by(asset_id=asset_id).all()
        
        for rule in learning_rules:
            # فحص RSI
            if (rule.avoid_when_rsi_above and 
                signal_data.get('rsi', 0) > rule.avoid_when_rsi_above):
                return True, f"تجنب الإشارة: RSI أعلى من {rule.avoid_when_rsi_above}"
            
            if (rule.avoid_when_rsi_below and 
                signal_data.get('rsi', 100) < rule.avoid_when_rsi_below):
                return True, f"تجنب الإشارة: RSI أقل من {rule.avoid_when_rsi_below}"
            
            # فحص الاتجاه
            if (rule.avoid_when_trend and 
                signal_data.get('trend') == rule.avoid_when_trend):
                return True, f"تجنب الإشارة: الاتجاه {rule.avoid_when_trend}"
            
            # فحص نمط الشموع
            if (rule.avoid_candlestick_pattern and 
                signal_data.get('candlestick_pattern') == rule.avoid_candlestick_pattern):
                return True, f"تجنب الإشارة: نمط الشموع {rule.avoid_candlestick_pattern}"
        
        return False, ""
    
    def __repr__(self):
        return f'<AILearningData {self.asset_id} - {self.failed_pattern_type}>'


class MarketData(db.Model):
    """نموذج بيانات السوق التاريخية"""
    __tablename__ = 'market_data'
    
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.String(20), nullable=False, index=True)
    
    # بيانات السعر
    open_price = db.Column(db.Float, nullable=False)
    high_price = db.Column(db.Float, nullable=False)
    low_price = db.Column(db.Float, nullable=False)
    close_price = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Float, default=0)
    
    # مؤشرات محسوبة
    rsi = db.Column(db.Float)
    sma_5 = db.Column(db.Float)
    sma_10 = db.Column(db.Float)
    sma_20 = db.Column(db.Float)
    ema_12 = db.Column(db.Float)
    ema_26 = db.Column(db.Float)
    
    # مستويات الدعم والمقاومة
    support_level = db.Column(db.Float)
    resistance_level = db.Column(db.Float)
    
    # نمط الشموع
    candlestick_pattern = db.Column(db.String(50))
    pattern_strength = db.Column(db.Integer)  # 1-100
    
    # الاتجاه
    trend_direction = db.Column(db.String(20))  # uptrend/downtrend/sideways
    trend_strength = db.Column(db.Integer)  # 1-100
    
    # التقلبات
    volatility = db.Column(db.Float)
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    @staticmethod
    def get_recent_data(asset_id: str, hours: int = 24):
        """الحصول على البيانات الحديثة لأصل معين"""
        since = datetime.utcnow() - timedelta(hours=hours)
        return MarketData.query.filter(
            MarketData.asset_id == asset_id,
            MarketData.timestamp >= since
        ).order_by(MarketData.timestamp.asc()).all()
    
    @staticmethod
    def calculate_support_resistance(asset_id: str, days: int = 7):
        """حساب مستويات الدعم والمقاومة"""
        since = datetime.utcnow() - timedelta(days=days)
        data = MarketData.query.filter(
            MarketData.asset_id == asset_id,
            MarketData.timestamp >= since
        ).all()
        
        if len(data) < 10:
            return None, None
        
        highs = [d.high_price for d in data]
        lows = [d.low_price for d in data]
        
        # حساب الدعم والمقاومة كمتوسط للقمم والقيعان
        sorted_highs = sorted(highs, reverse=True)
        sorted_lows = sorted(lows)
        
        resistance = sum(sorted_highs[:3]) / 3  # متوسط أعلى 3 قيم
        support = sum(sorted_lows[:3]) / 3      # متوسط أقل 3 قيم
        
        return support, resistance
    
    def __repr__(self):
        return f'<MarketData {self.asset_id} - {self.close_price} at {self.timestamp}>'