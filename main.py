import os
from app import app, socketio

# هذا السطر يخلي المتغير application متاح إذا احتاجته المنصة
application = app

if __name__ == "__main__":
    # قراءة المنفذ من البيئة أو استخدام 10000 كافتراضي
    port = int(os.environ.get("PORT", 10000))
    
    # تشغيل التطبيق مع Socket.IO
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        use_reloader=False,
        log_output=True
    )
