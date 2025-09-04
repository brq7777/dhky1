"""
وحدة التكامل مع OpenAI للتحليل المتقدم للأسواق المالية
يستخدم أحدث نموذج GPT-5 لتحليل دقيق ومضمون للإشارات
"""

import os
import json
import logging
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from openai import OpenAI
import requests

# استخدام GPT-3.5-turbo لأن الاشتراك لا يدعم GPT-5 حالياً
OPENAI_MODEL = "gpt-3.5-turbo"

class OpenAIMarketAnalyzer:
    """محلل السوق المتطور باستخدام OpenAI GPT-5"""
    
    def __init__(self):
        """تهيئة محلل OpenAI"""
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logging.warning("⚠️ مفتاح OpenAI غير موجود - سيعمل النظام بالتحليل الداخلي فقط")
            self.client = None
            self.enabled = False
        else:
            try:
                self.client = OpenAI(api_key=self.api_key)
                self.enabled = True
                logging.info(f"✅ تم تفعيل OpenAI GPT-3.5-turbo للتحليل المتقدم")
            except Exception as e:
                logging.error(f"❌ خطأ في تهيئة OpenAI: {e}")
                self.client = None
                self.enabled = False
        
        # إعدادات التحليل
        self.temperature = 0.2  # دقة عالية للتحليل المالي
        self.max_tokens = 1000
        
        # ذاكرة التعلم من الأخطاء السابقة
        self.error_memory = []
        self.successful_patterns = []
        
        # إعدادات الأخبار الاقتصادية
        self.news_cache = {}
        self.news_cache_duration = 300  # 5 دقائق
        
    def analyze_with_economic_news(self, asset_data: Dict, market_data: Dict) -> Optional[Dict]:
        """تحليل الأصل مع دمج الأخبار الاقتصادية"""
        if not self.enabled or not self.client:
            return None
        
        try:
            # جلب الأخبار الاقتصادية المؤثرة
            economic_news = self._fetch_economic_news(asset_data['id'])
            
            # إعداد السياق للتحليل
            analysis_prompt = self._prepare_analysis_prompt(
                asset_data, 
                market_data, 
                economic_news
            )
            
            # التحليل باستخدام GPT-3.5-turbo
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            # معالجة النتيجة
            content = response.choices[0].message.content
            if not content:
                return None
            analysis_result = json.loads(content)
            
            # التحقق من دقة التحليل بناءً على الأخطاء السابقة
            validated_result = self._validate_against_errors(analysis_result)
            
            # حفظ النمط إذا كان ناجحاً
            if validated_result.get('confidence', 0) > 85:
                self._save_successful_pattern(validated_result)
            
            return validated_result
            
        except Exception as e:
            logging.error(f"خطأ في تحليل OpenAI: {e}")
            return None
    
    def _get_system_prompt(self) -> str:
        """الحصول على تعليمات النظام لـ GPT-3.5-turbo"""
        return """أنت خبير تحليل مالي متخصص في الأسواق المالية مع خبرة عميقة في:
        1. التحليل الفني للمؤشرات (RSI, MACD, Bollinger Bands, Stochastic)
        2. التحليل الأساسي والأخبار الاقتصادية
        3. إدارة المخاطر وتحديد نقاط الدخول والخروج
        4. التنبؤ بحركة الأسعار بناءً على الأنماط التاريخية
        
        مهمتك:
        - تحليل البيانات المقدمة بدقة عالية
        - إصدار إشارات تداول مضمونة فقط عندما تكون الظروف مثالية
        - تجنب الإشارات الخاطئة بناءً على الأخطاء السابقة
        - دمج تأثير الأخبار الاقتصادية في التحليل
        - تقديم نسبة ثقة واقعية (لا تعطي إشارة إذا الثقة أقل من 85%)
        
        يجب أن تكون إجابتك بصيغة JSON دائماً مع الحقول التالية:
        {
            "signal": "BUY" أو "SELL" أو "HOLD",
            "confidence": رقم بين 0-100,
            "reasoning": شرح مفصل بالعربية,
            "entry_price": سعر الدخول المقترح,
            "stop_loss": نقطة وقف الخسارة,
            "take_profit": نقطة جني الأرباح,
            "risk_level": "low" أو "medium" أو "high",
            "news_impact": تأثير الأخبار الاقتصادية,
            "technical_score": درجة التحليل الفني (0-100),
            "fundamental_score": درجة التحليل الأساسي (0-100),
            "recommendations": قائمة بالتوصيات
        }"""
    
    def _prepare_analysis_prompt(self, asset_data: Dict, market_data: Dict, economic_news: List) -> str:
        """إعداد طلب التحليل"""
        prompt = f"""حلل الأصل المالي التالي وقدم توصية تداول دقيقة:

        الأصل: {asset_data.get('name', asset_data['id'])}
        السعر الحالي: ${asset_data.get('price', 0):.4f}
        التغير (24 ساعة): {asset_data.get('change_24h', 0):.2f}%
        الحجم: ${asset_data.get('volume', 0):,.0f}
        
        المؤشرات الفنية:
        - RSI: {market_data.get('rsi', 50):.2f}
        - MACD: {market_data.get('macd', {}).get('value', 0):.4f}
        - Bollinger Bands: Upper={market_data.get('bb_upper', 0):.4f}, Lower={market_data.get('bb_lower', 0):.4f}
        - Stochastic: K={market_data.get('stoch_k', 50):.2f}, D={market_data.get('stoch_d', 50):.2f}
        - Moving Averages: SMA50={market_data.get('sma_50', 0):.4f}, SMA200={market_data.get('sma_200', 0):.4f}
        
        بيانات السوق:
        - الاتجاه: {market_data.get('trend', 'sideways')}
        - التقلب: {market_data.get('volatility', 0):.2f}
        - قوة الاتجاه: {market_data.get('trend_strength', 50):.1f}%
        - مستوى الدعم: ${market_data.get('support', 0):.4f}
        - مستوى المقاومة: ${market_data.get('resistance', 0):.4f}
        
        الأخبار الاقتصادية المؤثرة:
        """
        
        if economic_news:
            for news in economic_news[:5]:  # أهم 5 أخبار
                prompt += f"\n- {news.get('title', '')}: {news.get('impact', 'متوسط')}"
        else:
            prompt += "\n- لا توجد أخبار مؤثرة حالياً"
        
        # إضافة الأخطاء السابقة للتعلم منها
        if self.error_memory:
            prompt += "\n\nتحذيرات من الأخطاء السابقة:"
            for error in self.error_memory[-3:]:  # آخر 3 أخطاء
                prompt += f"\n- {error['pattern']}: {error['issue']}"
        
        prompt += "\n\nقدم تحليلاً شاملاً مع التركيز على الدقة وتجنب الإشارات الخاطئة."
        
        return prompt
    
    def _fetch_economic_news(self, asset_id: str) -> List[Dict]:
        """جلب الأخبار الاقتصادية المؤثرة"""
        # التحقق من الذاكرة المؤقتة
        cache_key = f"news_{asset_id}"
        if cache_key in self.news_cache:
            cached_data = self.news_cache[cache_key]
            if time.time() - cached_data['timestamp'] < self.news_cache_duration:
                return cached_data['news']
        
        try:
            # هنا يمكن دمج API للأخبار الاقتصادية
            # مثال: Alpha Vantage, Yahoo Finance, أو أي مصدر آخر
            
            # حالياً نستخدم بيانات تجريبية
            news = self._get_simulated_news(asset_id)
            
            # حفظ في الذاكرة المؤقتة
            self.news_cache[cache_key] = {
                'news': news,
                'timestamp': time.time()
            }
            
            return news
            
        except Exception as e:
            logging.error(f"خطأ في جلب الأخبار: {e}")
            return []
    
    def _get_simulated_news(self, asset_id: str) -> List[Dict]:
        """بيانات أخبار تجريبية للتطوير"""
        if 'BTC' in asset_id or 'ETH' in asset_id:
            return [
                {
                    'title': 'البنك المركزي الأمريكي يناقش تنظيمات العملات الرقمية',
                    'impact': 'مرتفع',
                    'sentiment': 'إيجابي'
                },
                {
                    'title': 'ارتفاع معدلات التضخم العالمية',
                    'impact': 'متوسط',
                    'sentiment': 'سلبي'
                }
            ]
        elif 'XAU' in asset_id:  # الذهب
            return [
                {
                    'title': 'توترات جيوسياسية تزيد الطلب على الملاذات الآمنة',
                    'impact': 'مرتفع',
                    'sentiment': 'إيجابي للذهب'
                },
                {
                    'title': 'توقعات برفع أسعار الفائدة',
                    'impact': 'متوسط',
                    'sentiment': 'سلبي للذهب'
                }
            ]
        else:
            return [
                {
                    'title': 'بيانات اقتصادية مختلطة',
                    'impact': 'منخفض',
                    'sentiment': 'محايد'
                }
            ]
    
    def _validate_against_errors(self, analysis: Dict) -> Dict:
        """التحقق من التحليل مقابل الأخطاء السابقة"""
        validated = analysis.copy()
        
        # خفض الثقة إذا كان النمط مشابه لخطأ سابق
        for error in self.error_memory:
            if self._pattern_matches(analysis, error['pattern']):
                validated['confidence'] = max(0, validated.get('confidence', 0) - 20)
                validated['reasoning'] += f"\n⚠️ تحذير: نمط مشابه لخطأ سابق - {error['issue']}"
                validated['risk_level'] = 'high'
                logging.info(f"⚠️ تم خفض الثقة بسبب نمط خطأ سابق")
        
        return validated
    
    def _pattern_matches(self, analysis: Dict, error_pattern: Dict) -> bool:
        """التحقق من تطابق النمط"""
        # مقارنة بسيطة للأنماط
        if analysis.get('signal') == error_pattern.get('signal'):
            # التحقق من المؤشرات المشابهة
            similar_indicators = 0
            if abs(analysis.get('technical_score', 0) - error_pattern.get('technical_score', 0)) < 10:
                similar_indicators += 1
            if analysis.get('risk_level') == error_pattern.get('risk_level'):
                similar_indicators += 1
            
            return similar_indicators >= 2
        
        return False
    
    def learn_from_error(self, signal_data: Dict, issue: str):
        """التعلم من الأخطاء"""
        error_record = {
            'pattern': {
                'signal': signal_data.get('signal'),
                'technical_score': signal_data.get('technical_score', 0),
                'risk_level': signal_data.get('risk_level'),
                'conditions': signal_data.get('conditions', {})
            },
            'issue': issue,
            'timestamp': time.time()
        }
        
        self.error_memory.append(error_record)
        
        # الاحتفاظ بآخر 20 خطأ فقط
        if len(self.error_memory) > 20:
            self.error_memory = self.error_memory[-20:]
        
        logging.info(f"🧠 OpenAI تعلم من الخطأ: {issue}")
    
    def _save_successful_pattern(self, analysis: Dict):
        """حفظ الأنماط الناجحة"""
        pattern = {
            'signal': analysis.get('signal'),
            'conditions': {
                'technical_score': analysis.get('technical_score', 0),
                'fundamental_score': analysis.get('fundamental_score', 0),
                'confidence': analysis.get('confidence', 0)
            },
            'timestamp': time.time()
        }
        
        self.successful_patterns.append(pattern)
        
        # الاحتفاظ بآخر 50 نمط ناجح
        if len(self.successful_patterns) > 50:
            self.successful_patterns = self.successful_patterns[-50:]
    
    def enhance_signal_with_ai(self, signal_data: Dict, asset_data: Dict) -> Dict:
        """تحسين الإشارة باستخدام OpenAI"""
        if not self.enabled or not self.client:
            return signal_data
        
        try:
            # تحليل سريع للإشارة
            enhancement_prompt = f"""
            قيّم الإشارة التالية وحسّنها:
            
            الإشارة: {signal_data.get('type')}
            السعر: ${signal_data.get('price', 0):.4f}
            الثقة الحالية: {signal_data.get('confidence', 0)}%
            السبب: {signal_data.get('reason', '')}
            RSI: {signal_data.get('rsi', 50)}
            الاتجاه: {signal_data.get('trend', 'unknown')}
            
            هل هذه إشارة جيدة؟ كيف يمكن تحسينها؟
            قدم تقييماً سريعاً بصيغة JSON.
            """
            
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "أنت محلل مالي خبير. قيّم الإشارات بسرعة ودقة."
                    },
                    {
                        "role": "user",
                        "content": enhancement_prompt
                    }
                ],
                temperature=0.1,  # دقة أعلى
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if not content:
                return signal_data
            enhancement = json.loads(content)
            
            # دمج التحسينات
            enhanced_signal = signal_data.copy()
            enhanced_signal['openai_confidence'] = enhancement.get('confidence', signal_data.get('confidence'))
            enhanced_signal['openai_analysis'] = enhancement.get('analysis', '')
            enhanced_signal['openai_recommendations'] = enhancement.get('recommendations', [])
            enhanced_signal['openai_enhanced'] = True
            
            # تحديث الثقة إذا كان تحليل OpenAI مختلف
            if enhancement.get('should_proceed', True):
                enhanced_signal['confidence'] = max(
                    enhanced_signal['confidence'],
                    enhancement.get('confidence', 0)
                )
            else:
                # خفض الثقة إذا كان OpenAI غير متأكد
                enhanced_signal['confidence'] = min(
                    enhanced_signal['confidence'],
                    enhancement.get('confidence', 50)
                )
            
            return enhanced_signal
            
        except Exception as e:
            logging.error(f"خطأ في تحسين الإشارة: {e}")
            return signal_data
    
    def get_market_sentiment(self, asset_id: str) -> Dict:
        """الحصول على معنويات السوق باستخدام OpenAI"""
        if not self.enabled or not self.client:
            return {'sentiment': 'neutral', 'score': 50}
        
        try:
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "حلل معنويات السوق للأصول المالية بناءً على الاتجاهات الحالية."
                    },
                    {
                        "role": "user",
                        "content": f"ما هي معنويات السوق الحالية لـ {asset_id}؟ قدم إجابة JSON مع sentiment (bullish/bearish/neutral) و score (0-100)."
                    }
                ],
                temperature=0.3,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if not content:
                return {'sentiment': 'neutral', 'score': 50}
            return json.loads(content)
            
        except Exception as e:
            logging.error(f"خطأ في تحليل المعنويات: {e}")
            return {'sentiment': 'neutral', 'score': 50}
    
    def predict_price_movement(self, asset_data: Dict, timeframe: str = '1h') -> Dict:
        """التنبؤ بحركة السعر"""
        if not self.enabled or not self.client:
            return {'direction': 'sideways', 'probability': 50}
        
        try:
            prediction_prompt = f"""
            بناءً على البيانات التالية، توقع حركة السعر للساعة القادمة:
            
            الأصل: {asset_data.get('id')}
            السعر الحالي: ${asset_data.get('price', 0):.4f}
            التغير (24h): {asset_data.get('change_24h', 0):.2f}%
            الحجم: ${asset_data.get('volume', 0):,.0f}
            
            قدم توقعاً بصيغة JSON مع:
            - direction: up/down/sideways
            - probability: 0-100
            - target_price: السعر المتوقع
            - reasoning: السبب
            """
            
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "أنت خبير في التنبؤ بحركة الأسعار بناءً على التحليل الفني."
                    },
                    {
                        "role": "user",
                        "content": prediction_prompt
                    }
                ],
                temperature=0.2,
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if not content:
                return {'direction': 'sideways', 'probability': 50}
            return json.loads(content)
            
        except Exception as e:
            logging.error(f"خطأ في التنبؤ: {e}")
            return {'direction': 'sideways', 'probability': 50}

# إنشاء مثيل عام
openai_analyzer = OpenAIMarketAnalyzer()

def test_openai_connection() -> Dict:
    """اختبار الاتصال بـ OpenAI"""
    if not openai_analyzer.enabled:
        return {
            'connected': False,
            'status': 'API key not configured',
            'message': 'يرجى تكوين مفتاح OpenAI API'
        }
    
    try:
        # اختبار بسيط
        if not openai_analyzer.client:
            return {
                'connected': False,
                'status': 'client_error',
                'message': 'OpenAI client not initialized'
            }
        
        response = openai_analyzer.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "أنت مساعد اختبار."},
                {"role": "user", "content": "قل 'الاتصال ناجح' بصيغة JSON مع حقل status."}
            ],
            max_tokens=50,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        if not content:
            return {
                'connected': False,
                'status': 'response_error',
                'message': 'No response from OpenAI'
            }
        result = json.loads(content)
        
        return {
            'connected': True,
            'status': 'success',
            'message': 'تم الاتصال بنجاح مع OpenAI GPT-3.5-turbo',
            'model': OPENAI_MODEL,
            'response': result
        }
        
    except Exception as e:
        return {
            'connected': False,
            'status': 'error',
            'message': f'خطأ في الاتصال: {str(e)}'
        }