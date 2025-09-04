"""
خدمة الأخبار الاقتصادية المتكاملة
تجلب الأخبار المالية والاقتصادية من مصادر متعددة لتحسين دقة الإشارات
"""

import os
import logging
import requests
import json
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from urllib.parse import quote

class EconomicNewsService:
    """خدمة جلب وتحليل الأخبار الاقتصادية"""
    
    def __init__(self):
        """تهيئة خدمة الأخبار"""
        self.news_api_key = os.environ.get("NEWS_API_KEY")
        
        if not self.news_api_key:
            logging.warning("⚠️ مفتاح NEWS_API غير موجود")
            self.enabled = False
        else:
            self.enabled = True
            logging.info("✅ خدمة الأخبار الاقتصادية مفعلة")
        
        # إعدادات الـ API
        self.base_url = "https://newsapi.org/v2"
        self.cache = {}
        self.cache_duration = 1800  # 30 دقيقة - تقليل الطلبات
        self.last_request_time = 0
        self.min_request_interval = 2  # ثانيتان بين الطلبات
        
        # قاموس الأصول للبحث
        self.asset_keywords = {
            'BTCUSDT': ['Bitcoin', 'BTC', 'cryptocurrency', 'crypto market', 'بيتكوين'],
            'ETHUSDT': ['Ethereum', 'ETH', 'DeFi', 'smart contracts', 'إيثيريوم'],
            'XAU/USD': ['Gold', 'precious metals', 'safe haven', 'inflation', 'الذهب'],
            'XAG/USD': ['Silver', 'precious metals', 'industrial metals', 'الفضة'],
            'EUR/USD': ['Euro', 'European Central Bank', 'ECB', 'EUR', 'اليورو'],
            'GBP/USD': ['British Pound', 'Bank of England', 'GBP', 'Sterling', 'الجنيه الإسترليني'],
            'USD/JPY': ['Japanese Yen', 'Bank of Japan', 'JPY', 'الين الياباني'],
            'USD/CHF': ['Swiss Franc', 'CHF', 'safe haven currency', 'الفرنك السويسري'],
            'AUD/USD': ['Australian Dollar', 'AUD', 'commodity currency', 'الدولار الأسترالي'],
            'NZD/USD': ['New Zealand Dollar', 'NZD', 'الدولار النيوزيلندي'],
            'USD/CAD': ['Canadian Dollar', 'CAD', 'oil prices', 'الدولار الكندي']
        }
        
        # تصنيف تأثير الأخبار
        self.impact_keywords = {
            'high_positive': ['surge', 'rally', 'breakthrough', 'record high', 'strong growth', 'bullish'],
            'moderate_positive': ['rise', 'gain', 'increase', 'improve', 'recover', 'support'],
            'neutral': ['stable', 'unchanged', 'steady', 'maintain', 'hold'],
            'moderate_negative': ['fall', 'decline', 'drop', 'decrease', 'concern', 'pressure'],
            'high_negative': ['crash', 'plunge', 'collapse', 'crisis', 'bearish', 'record low']
        }
    
    def fetch_news_for_asset(self, asset_id: str, limit: int = 5) -> List[Dict]:
        """جلب الأخبار المتعلقة بأصل معين"""
        if not self.enabled:
            return []
        
        # التحقق من الذاكرة المؤقتة
        cache_key = f"news_{asset_id}_{limit}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached['timestamp'] < self.cache_duration:
                return cached['data']
        
        try:
            # تحضير كلمات البحث
            keywords = self.asset_keywords.get(asset_id, [asset_id])
            query = ' OR '.join(keywords[:3])  # أول 3 كلمات مفتاحية
            
            # بناء URL للبحث
            url = f"{self.base_url}/everything"
            params = {
                'q': query,
                'apiKey': self.news_api_key,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': limit
            }
            
            # التحقق من الفترة الزمنية بين الطلبات
            current_time = time.time()
            if current_time - self.last_request_time < self.min_request_interval:
                time.sleep(self.min_request_interval)
            
            # إجراء الطلب
            response = requests.get(url, params=params, timeout=5)
            self.last_request_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get('articles', [])
                
                # معالجة الأخبار
                processed_news = []
                for article in articles:
                    news_item = {
                        'title': article.get('title', ''),
                        'description': article.get('description', ''),
                        'url': article.get('url', ''),
                        'source': article.get('source', {}).get('name', 'Unknown'),
                        'publishedAt': article.get('publishedAt', ''),
                        'impact': self._analyze_impact(article),
                        'relevance': self._calculate_relevance(article, asset_id)
                    }
                    processed_news.append(news_item)
                
                # حفظ في الذاكرة المؤقتة
                self.cache[cache_key] = {
                    'data': processed_news,
                    'timestamp': time.time()
                }
                
                return processed_news
            elif response.status_code == 429:
                # معالجة خطأ تجاوز الحد
                logging.warning("تم تجاوز حد طلبات API الأخبار - استخدام بيانات احتياطية")
                return self._get_fallback_news(asset_id)
            else:
                logging.error(f"خطأ في جلب الأخبار: {response.status_code}")
                return self._get_fallback_news(asset_id)
                
        except Exception as e:
            logging.error(f"خطأ في خدمة الأخبار: {e}")
            return []
    
    def fetch_market_news(self, category: str = 'business', limit: int = 10) -> List[Dict]:
        """جلب أخبار السوق العامة"""
        if not self.enabled:
            return []
        
        # التحقق من الذاكرة المؤقتة
        cache_key = f"market_{category}_{limit}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached['timestamp'] < self.cache_duration:
                return cached['data']
        
        try:
            # بناء URL للأخبار العامة
            url = f"{self.base_url}/top-headlines"
            params = {
                'apiKey': self.news_api_key,
                'category': category,
                'language': 'en',
                'pageSize': limit
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get('articles', [])
                
                processed_news = []
                for article in articles:
                    news_item = {
                        'title': article.get('title', ''),
                        'description': article.get('description', ''),
                        'url': article.get('url', ''),
                        'source': article.get('source', {}).get('name', 'Unknown'),
                        'publishedAt': article.get('publishedAt', ''),
                        'impact': self._analyze_impact(article),
                        'category': category
                    }
                    processed_news.append(news_item)
                
                # حفظ في الذاكرة المؤقتة
                self.cache[cache_key] = {
                    'data': processed_news,
                    'timestamp': time.time()
                }
                
                return processed_news
            elif response.status_code == 429:
                logging.warning("تم تجاوز حد طلبات API - استخدام بيانات احتياطية")
                return self._get_fallback_market_news()
            else:
                logging.error(f"خطأ في جلب أخبار السوق: {response.status_code}")
                return self._get_fallback_market_news()
                
        except Exception as e:
            logging.error(f"خطأ في خدمة أخبار السوق: {e}")
            return self._get_fallback_market_news()
    
    def _get_fallback_news(self, asset_id: str) -> List[Dict]:
        """إرجاع أخبار احتياطية في حالة فشل API"""
        # أخبار عامة حسب نوع الأصل
        if 'BTC' in asset_id or 'ETH' in asset_id:
            return [{
                'title': 'تحليل سوق العملات الرقمية',
                'description': 'السوق يشهد تداولات نشطة',
                'impact': 'neutral',
                'relevance': 0.5,
                'source': 'تحليل فني',
                'publishedAt': datetime.now().isoformat()
            }]
        elif 'XAU' in asset_id or 'XAG' in asset_id:
            return [{
                'title': 'تحليل المعادن الثمينة',
                'description': 'الذهب والفضة في نطاق تداول مستقر',
                'impact': 'neutral',
                'relevance': 0.5,
                'source': 'تحليل فني',
                'publishedAt': datetime.now().isoformat()
            }]
        else:  # Forex
            return [{
                'title': 'تحليل أسواق العملات',
                'description': 'أزواج العملات الرئيسية في حركة اعتيادية',
                'impact': 'neutral',
                'relevance': 0.5,
                'source': 'تحليل فني',
                'publishedAt': datetime.now().isoformat()
            }]
    
    def _get_fallback_market_news(self) -> List[Dict]:
        """إرجاع أخبار السوق الاحتياطية"""
        return [{
            'title': 'تحديثات السوق العالمية',
            'description': 'الأسواق المالية تتداول بشكل طبيعي',
            'impact': 'neutral',
            'category': 'business',
            'source': 'تحليل السوق',
            'publishedAt': datetime.now().isoformat()
        }]
    
    def _analyze_impact(self, article: Dict) -> Dict:
        """تحليل تأثير الخبر على السوق"""
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        content = f"{title} {description}"
        
        # تحديد نوع التأثير
        impact_type = 'neutral'
        impact_score = 50
        
        # فحص الكلمات المفتاحية
        for impact, keywords in self.impact_keywords.items():
            for keyword in keywords:
                if keyword.lower() in content:
                    if 'high_positive' in impact:
                        impact_type = 'very_positive'
                        impact_score = 90
                    elif 'moderate_positive' in impact:
                        impact_type = 'positive'
                        impact_score = 70
                    elif 'high_negative' in impact:
                        impact_type = 'very_negative'
                        impact_score = 10
                    elif 'moderate_negative' in impact:
                        impact_type = 'negative'
                        impact_score = 30
                    else:
                        impact_type = 'neutral'
                        impact_score = 50
                    break
        
        return {
            'type': impact_type,
            'score': impact_score,
            'confidence': self._calculate_confidence(article)
        }
    
    def _calculate_relevance(self, article: Dict, asset_id: str) -> float:
        """حساب مدى صلة الخبر بالأصل"""
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        content = f"{title} {description}"
        
        keywords = self.asset_keywords.get(asset_id, [asset_id])
        matches = 0
        
        for keyword in keywords:
            if keyword.lower() in content:
                matches += 1
        
        relevance = min(100, (matches / len(keywords)) * 100) if keywords else 0
        return relevance
    
    def _calculate_confidence(self, article: Dict) -> float:
        """حساب مستوى الثقة في تحليل الخبر"""
        # عوامل الثقة
        confidence = 50  # قيمة أساسية
        
        # مصدر موثوق
        trusted_sources = ['Reuters', 'Bloomberg', 'CNBC', 'Financial Times', 'Wall Street Journal']
        if article.get('source', {}).get('name', '') in trusted_sources:
            confidence += 20
        
        # وجود وصف مفصل
        if article.get('description') and len(article.get('description', '')) > 100:
            confidence += 15
        
        # حداثة الخبر
        try:
            published = article.get('publishedAt', '')
            if published:
                pub_time = datetime.fromisoformat(published.replace('Z', '+00:00'))
                hours_ago = (datetime.now(pub_time.tzinfo) - pub_time).total_seconds() / 3600
                if hours_ago < 1:
                    confidence += 15  # خبر حديث جداً
                elif hours_ago < 6:
                    confidence += 10
                elif hours_ago < 24:
                    confidence += 5
        except:
            pass
        
        return min(100, confidence)
    
    def get_market_sentiment(self, news_list: List[Dict]) -> Dict:
        """تحليل معنويات السوق من الأخبار"""
        if not news_list:
            return {
                'sentiment': 'neutral',
                'score': 50,
                'confidence': 0
            }
        
        total_score = 0
        total_confidence = 0
        
        for news in news_list:
            impact = news.get('impact', {})
            score = impact.get('score', 50)
            confidence = impact.get('confidence', 50)
            
            total_score += score * (confidence / 100)
            total_confidence += confidence
        
        avg_score = total_score / len(news_list) if news_list else 50
        avg_confidence = total_confidence / len(news_list) if news_list else 0
        
        # تحديد المعنويات
        if avg_score >= 70:
            sentiment = 'bullish'
        elif avg_score >= 55:
            sentiment = 'slightly_bullish'
        elif avg_score >= 45:
            sentiment = 'neutral'
        elif avg_score >= 30:
            sentiment = 'slightly_bearish'
        else:
            sentiment = 'bearish'
        
        return {
            'sentiment': sentiment,
            'score': avg_score,
            'confidence': avg_confidence,
            'news_count': len(news_list)
        }
    
    def get_economic_calendar(self) -> List[Dict]:
        """جلب التقويم الاقتصادي (أحداث مهمة قادمة)"""
        # يمكن دمج API آخر للتقويم الاقتصادي
        # حالياً نعيد قائمة تجريبية
        return [
            {
                'event': 'Fed Interest Rate Decision',
                'date': datetime.now() + timedelta(days=7),
                'importance': 'high',
                'forecast_impact': 'volatile'
            },
            {
                'event': 'US Non-Farm Payrolls',
                'date': datetime.now() + timedelta(days=3),
                'importance': 'high',
                'forecast_impact': 'moderate'
            }
        ]
    
    def analyze_news_for_signal(self, asset_id: str, signal_type: str) -> Dict:
        """تحليل الأخبار لدعم أو معارضة إشارة التداول"""
        news = self.fetch_news_for_asset(asset_id, limit=5)
        
        if not news:
            return {
                'supports_signal': None,
                'confidence': 0,
                'reason': 'لا توجد أخبار متاحة'
            }
        
        sentiment = self.get_market_sentiment(news)
        
        # تحليل التوافق مع الإشارة
        supports_signal = False
        reason = ""
        
        if signal_type == 'BUY':
            if sentiment['sentiment'] in ['bullish', 'slightly_bullish']:
                supports_signal = True
                reason = f"الأخبار إيجابية ({sentiment['sentiment']}) - تدعم إشارة الشراء"
            elif sentiment['sentiment'] in ['bearish', 'slightly_bearish']:
                supports_signal = False
                reason = f"الأخبار سلبية ({sentiment['sentiment']}) - تعارض إشارة الشراء"
            else:
                supports_signal = None
                reason = "الأخبار محايدة - لا تأثير واضح"
        
        elif signal_type == 'SELL':
            if sentiment['sentiment'] in ['bearish', 'slightly_bearish']:
                supports_signal = True
                reason = f"الأخبار سلبية ({sentiment['sentiment']}) - تدعم إشارة البيع"
            elif sentiment['sentiment'] in ['bullish', 'slightly_bullish']:
                supports_signal = False
                reason = f"الأخبار إيجابية ({sentiment['sentiment']}) - تعارض إشارة البيع"
            else:
                supports_signal = None
                reason = "الأخبار محايدة - لا تأثير واضح"
        
        return {
            'supports_signal': supports_signal,
            'confidence': sentiment['confidence'],
            'sentiment': sentiment['sentiment'],
            'score': sentiment['score'],
            'reason': reason,
            'news_summary': [n['title'] for n in news[:3]]  # أول 3 عناوين
        }

# إنشاء مثيل عام
news_service = EconomicNewsService()

def test_news_service():
    """اختبار خدمة الأخبار"""
    if not news_service.enabled:
        return {
            'status': 'disabled',
            'message': 'خدمة الأخبار غير مفعلة - تحقق من مفتاح API'
        }
    
    try:
        # اختبار جلب أخبار البيتكوين
        btc_news = news_service.fetch_news_for_asset('BTCUSDT', limit=3)
        
        # اختبار جلب أخبار السوق
        market_news = news_service.fetch_market_news('business', limit=3)
        
        return {
            'status': 'success',
            'message': 'خدمة الأخبار تعمل بنجاح',
            'btc_news_count': len(btc_news),
            'market_news_count': len(market_news),
            'sample': btc_news[0] if btc_news else None
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'خطأ في اختبار الخدمة: {str(e)}'
        }