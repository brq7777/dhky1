#!/usr/bin/env python3
"""
سكريبت تشغيل سريع لنظام المراقبة
استخدم هذا لبدء تشغيل المراقبة بسهولة
"""

import subprocess
import sys
import os

def start_keeper():
    """تشغيل نظام المراقبة"""
    try:
        print("🔄 بدء تشغيل نظام مراقبة الموقع...")
        
        # التأكد من وجود الملف
        if not os.path.exists('keeper.py'):
            print("❌ ملف keeper.py غير موجود!")
            return
            
        # تشغيل نظام المراقبة
        subprocess.run([sys.executable, 'keeper.py'])
        
    except KeyboardInterrupt:
        print("\n⏹️ تم إيقاف المراقبة")
    except Exception as e:
        print(f"❌ خطأ في تشغيل المراقبة: {e}")

if __name__ == "__main__":
    start_keeper()