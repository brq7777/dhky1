# Gunicorn configuration optimized for SocketIO and real-time applications

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = 1  # SocketIO requires 1 worker for proper operation
worker_class = "gevent"  # Better for WebSocket connections
worker_connections = 1000

# Timeouts
timeout = 300  # Increased for WebSocket connections
keepalive = 5

# Restart workers
max_requests = 1000
max_requests_jitter = 50

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = 'financial_dashboard'

# Reload on code changes (only for development)
reload = True
reload_engine = 'auto'

# Preload app for better performance
preload_app = True

# Environment variables
raw_env = [
    'PYTHONPATH=/home/runner/workspace',
]