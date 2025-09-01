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
        if not self.trial_end:
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