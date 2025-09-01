# Gunicorn configuration for stable SocketIO connections

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes - Use sync workers for maximum stability
workers = 1
worker_class = "sync"  # Most stable for SocketIO
worker_connections = 1000

# Timeouts - Much longer for stability
timeout = 600  # 10 minutes for WebSocket connections
keepalive = 60  # Keep connections alive longer

# Restart workers - Less frequent restarts
max_requests = 0  # Disable automatic restarts
max_requests_jitter = 0

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'warning'  # Reduce logging noise
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = 'financial_dashboard'

# Reload on code changes
reload = True
reload_engine = 'auto'

# Preload app
preload_app = False  # Disable for stability

# Environment variables
raw_env = [
    'PYTHONPATH=/home/runner/workspace',
]