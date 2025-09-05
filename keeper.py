#!/usr/bin/env python3
"""
نظام مراقبة الموقع المالي - UptimeRobot Heartbeat
يحافظ على تشغيل الموقع ويرسل نبضات دورية
"""

import requests
import time
import logging
from datetime import datetime
import os

# إعدادات السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# إعدادات المراقبة
HEARTBEAT_URL = os.environ.get("HEARTBEAT_URL", "")  # رابط UptimeRobot اختياري
PROJECT_URL = "https://laalyly-abodhayymreplit.replit.app"  # رابط مشروعك
CHECK_INTERVAL = 60  # فترة التحقق بالثواني (دقيقة واحدة)
TIMEOUT = 30  # مهلة الاستجابة

class WebsiteKeeper:
    """مراقب الموقع المالي"""
    
    def __init__(self):
        self.project_url = PROJECT_URL
        self.heartbeat_url = HEARTBEAT_URL
        self.successful_checks = 0
        self.failed_checks = 0
        self.start_time = datetime.now()
        
    def check_website_health(self):
        """فحص حالة الموقع"""
        try:
            response = requests.get(
                self.project_url,
                timeout=TIMEOUT,
                headers={'User-Agent': 'UptimeKeeper/1.0'}
            )
            
            if response.status_code == 200:
                return True, f"الموقع يعمل بشكل طبيعي - كود: {response.status_code}"
            else:
                return False, f"الموقع يستجيب بخطأ - كود: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, f"انتهت مهلة الاتصال ({TIMEOUT}s)"
        except requests.exceptions.ConnectionError:
            return False, "فشل الاتصال بالموقع"
        except Exception as e:
            return False, f"خطأ غير متوقع: {str(e)}"

    def send_heartbeat(self):
        """إرسال نبضة إلى UptimeRobot"""
        if "xxxxx" in self.heartbeat_url:
            logging.warning("⚠️ لم يتم إعداد رابط UptimeRobot بعد")
            return False
            
        try:
            response = requests.get(self.heartbeat_url, timeout=10)
            if response.status_code == 200:
                logging.info("✅ تم إرسال النبضة بنجاح")
                return True
            else:
                logging.warning(f"⚠️ فشل إرسال النبضة - كود: {response.status_code}")
                return False
        except Exception as e:
            logging.error(f"❌ خطأ في إرسال النبضة: {e}")
            return False

    def run_monitoring_cycle(self):
        """دورة مراقبة واحدة"""
        is_healthy, status_message = self.check_website_health()
        
        if is_healthy:
            self.successful_checks += 1
            logging.info(f"✅ {status_message}")
            
            # إرسال نبضة فقط إذا كان الموقع يعمل
            heartbeat_sent = self.send_heartbeat()
            
        else:
            self.failed_checks += 1
            logging.error(f"❌ {status_message}")
            
        # إحصائيات دورية
        total_checks = self.successful_checks + self.failed_checks
        if total_checks % 10 == 0:  # كل 10 دقائق
            uptime_percentage = (self.successful_checks / total_checks) * 100
            running_time = datetime.now() - self.start_time
            
            logging.info(f"📊 إحصائيات المراقبة:")
            logging.info(f"   - وقت التشغيل: {running_time}")
            logging.info(f"   - نسبة التوفر: {uptime_percentage:.1f}%")
            logging.info(f"   - فحوصات ناجحة: {self.successful_checks}")
            logging.info(f"   - فحوصات فاشلة: {self.failed_checks}")

    def start_monitoring(self):
        """بدء المراقبة المستمرة"""
        logging.info("🚀 بدء مراقبة الموقع المالي...")
        logging.info(f"📍 الموقع المراقب: {self.project_url}")
        logging.info(f"⏰ فترة التحقق: {CHECK_INTERVAL} ثانية")
        
        try:
            while True:
                self.run_monitoring_cycle()
                time.sleep(CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            logging.info("⏹️ تم إيقاف المراقبة بواسطة المستخدم")
        except Exception as e:
            logging.error(f"❌ خطأ حرج في نظام المراقبة: {e}")

def main():
    """تشغيل نظام المراقبة"""
    print("=" * 50)
    print("🔄 نظام مراقبة الموقع المالي")
    print("=" * 50)
    
    keeper = WebsiteKeeper()
    keeper.start_monitoring()

if __name__ == "__main__":
    main()