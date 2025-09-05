# إعدادات Gunicorn محسّنة لـ SocketIO والاستقرار

import multiprocessing
import os

# إعدادات الـ Workers
workers = 1  # عامل واحد فقط للتطبيقات الصغيرة
worker_class = "gevent"  # استخدام gevent للـ async operations
worker_connections = 1000

# إعدادات الشبكة  
bind = "0.0.0.0:5000"
backlog = 2048
keepalive = 5

# إعدادات المهلة الزمنية - محسّنة لـ SocketIO
timeout = 120  # زيادة timeout للعمليات الطويلة
graceful_timeout = 60
max_requests = 0  # لا حد أقصى للطلبات
max_requests_jitter = 0

# إعدادات الذاكرة والأداء
preload_app = False  # تجنب مشاكل الـ memory sharing
worker_tmp_dir = "/tmp"
tmp_upload_dir = "/tmp"

# إعدادات الـ Logging
accesslog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
errorlog = "-"
loglevel = "info"
capture_output = True
enable_stdio_inheritance = True

# إعدادات الأمان
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190

# إعدادات خاصة بـ SocketIO
# تقليل keep-alive لتجنب hanging connections
raw_env = [
    'PYTHONUNBUFFERED=TRUE',
    'PYTHONPATH=.',
]

# تحسين الأداء
worker_tmp_dir = "/dev/shm" if os.path.exists("/dev/shm") else "/tmp"

# Callback functions لمراقبة العمال
def when_ready(server):
    server.log.info("✅ Gunicorn server ready - SocketIO optimized")

def worker_abort(worker):
    worker.log.info(f"⚠️  Worker {worker.pid} aborted - restarting")

def on_exit(server):
    server.log.info("🔄 Gunicorn server shutting down")