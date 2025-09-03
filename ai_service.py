import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import openai
from openai import OpenAI

class AITradingAnalyzer:
    """نظام الذكاء الاصطناعي المتطور للتحليل المالي والتداول"""
    
    def __init__(self):
        # إعداد OpenAI
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
        # do not change this unless explicitly requested by the user
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = "gpt-5"
        
        # ذاكرة المحادثة للمحافظة على السياق
        self.conversation_memory = []
        
        # قاعدة معرفة مالية
        self.financial_knowledge = {
            'crypto': {
                'BTCUSDT': {
                    'name': 'بيتكوين',
                    'volatility': 'عالية',
                    'key_levels': [50000, 60000, 70000, 100000],
                    'market_cap_rank': 1,
                    'adoption': 'واسع',
                    'institutional': True
                },
                'ETHUSDT': {
                    'name': 'إيثيريوم',
                    'volatility': 'عالية',
                    'key_levels': [2000, 3000, 4000, 5000],
                    'market_cap_rank': 2,
                    'adoption': 'واسع',
                    'defi': True
                }
            },
            'forex': {
                'EUR/USD': {
                    'name': 'اليورو دولار',
                    'volatility': 'متوسطة',
                    'key_levels': [1.0000, 1.0500, 1.1000, 1.2000],
                    'major_pair': True,
                    'economic_factors': ['ECB', 'Fed', 'GDP', 'inflation']
                },
                'GBP/USD': {
                    'name': 'الجنيه الإسترليني دولار',
                    'volatility': 'متوسطة إلى عالية',
                    'key_levels': [1.2000, 1.2500, 1.3000, 1.4000],
                    'major_pair': True,
                    'economic_factors': ['BoE', 'Brexit', 'inflation']
                },
                'USD/JPY': {
                    'name': 'الدولار الأمريكي ين ياباني',
                    'volatility': 'متوسطة',
                    'key_levels': [100, 110, 140, 150],
                    'major_pair': True,
                    'economic_factors': ['BoJ', 'carry_trade']
                }
            },
            'metals': {
                'XAU/USD': {
                    'name': 'الذهب',
                    'volatility': 'متوسطة',
                    'key_levels': [1800, 2000, 2500, 3000],
                    'safe_haven': True,
                    'inflation_hedge': True,
                    'economic_factors': ['Fed', 'inflation', 'geopolitics']
                }
            }
        }
        
        logging.info("تم تهيئة نظام الذكاء الاصطناعي المتطور بنجاح")
    
    def test_openai_connection(self) -> Dict:
        """اختبار اتصال OpenAI API"""
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "اختبار الاتصال - أجب بكلمة واحدة: نجح"}
                ],
                max_completion_tokens=10
            )
            
            if response.choices and response.choices[0].message:
                result_text = response.choices[0].message.content
                if result_text:
                    result_text = result_text.strip()
                else:
                    result_text = "استجابة فارغة"
            else:
                result_text = "لا توجد استجابة"
            
            return {
                "status": "success",
                "connected": True,
                "model": self.model,
                "response_time": "سريع",
                "test_response": result_text,
                "message": "OpenAI API متصل ويعمل بشكل طبيعي"
            }
            
        except Exception as e:
            error_message = str(e)
            logging.error(f"فشل في اختبار OpenAI API: {error_message}")
            
            return {
                "status": "error", 
                "connected": False,
                "model": self.model,
                "error": error_message,
                "message": "فشل الاتصال مع OpenAI API - تحقق من مفتاح API أو الاتصال بالإنترنت"
            }
    
    def chat_with_ai(self, user_message: str, current_prices: Optional[Dict] = None) -> str:
        """دردشة ذكية مع الذكاء الاصطناعي حول الأسواق المالية"""
        try:
            # إضافة رسالة المستخدم إلى الذاكرة
            self.conversation_memory.append({
                "role": "user", 
                "content": user_message,
                "timestamp": datetime.now().isoformat()
            })
            
            # الحد الأقصى لحجم الذاكرة
            if len(self.conversation_memory) > 20:
                self.conversation_memory = self.conversation_memory[-15:]
            
            # بناء السياق للمحادثة
            system_prompt = self._build_system_prompt(current_prices)
            
            # تحضير رسائل المحادثة
            messages = [{"role": "system", "content": system_prompt}]
            
            # إضافة الذاكرة
            for msg in self.conversation_memory[-10:]:  # آخر 10 رسائل
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # الحصول على الاستجابة من OpenAI
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=1000,
                
                response_format={"type": "json_object"}
            )
            
            if response.choices and response.choices[0].message and response.choices[0].message.content:
                try:
                    ai_response_json = json.loads(response.choices[0].message.content)
                    ai_message = ai_response_json.get("message", "عذراً، لم أتمكن من فهم طلبك")
                    
                    # إضافة استجابة الذكاء الاصطناعي إلى الذاكرة
                    self.conversation_memory.append({
                        "role": "assistant",
                        "content": ai_message,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    return ai_message
                    
                except json.JSONDecodeError:
                    # في حالة فشل تحليل JSON، استخدم النص مباشرة
                    ai_message = response.choices[0].message.content or "عذراً، حدث خطأ في المعالجة"
                    
                    self.conversation_memory.append({
                        "role": "assistant",
                        "content": ai_message,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    return ai_message
            
            return "عذراً، لم أتمكن من الحصول على استجابة من النظام"
            
        except Exception as e:
            error_msg = f"خطأ في المحادثة مع الذكاء الاصطناعي: {str(e)}"
            logging.error(error_msg)
            return "عذراً، حدث خطأ تقني. يرجى المحاولة مرة أخرى"
    
    def _build_system_prompt(self, current_prices: Optional[Dict] = None) -> str:
        """بناء prompt النظام للذكاء الاصطناعي"""
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        base_prompt = f"""
أنت خبير مالي متطور ومحلل اقتصادي محترف مدعوم بـ GPT-5 باللغة العربية. اسمك "محلل الأسواق AI المتطور".

مهامك المتطورة:
1. تقديم تحليلات مالية دقيقة ومفصلة مع توقعات ذكية
2. شرح المفاهيم المالية بطريقة مبسطة وممتعة
3. تقديم نصائح استثمارية متوازنة وإستراتيجيات مخصصة
4. تحليل متقدم للأسواق المالية (العملات الرقمية، الفوركس، المعادن الثمينة)
5. مساعدة المستخدمين في اتخاذ قرارات مالية مدروسة وذكية
6. اكتشاف الأنماط والاتجاهات المخفية في البيانات
7. تحليل المشاعر السوقية والتنبؤ بالتحركات
8. تقديم تحليلات مقارنة بين الأصول المختلفة
9. مساعدة في إدارة المخاطر وتنويع المحافظ
10. تقديم رؤى استثمارية طويلة وقصيرة المدى

قواعد مهمة:
- أجب دائماً باللغة العربية
- كن دقيقاً وموضوعياً في تحليلاتك
- اذكر المخاطر دائماً مع الفرص
- لا تقدم نصائح مالية مضمونة النتائج
- استخدم البيانات الحالية عند توفرها
- كن مفيداً وودوداً في تعاملك

التوقيت الحالي: {current_time}

معلومات السوق الحالية:
"""
        
        if current_prices:
            base_prompt += "\nالأسعار الحالية:\n"
            for asset_id, data in current_prices.items():
                asset_name = self._get_asset_name(asset_id)
                price = data.get('price', 0)
                change = data.get('price_change_5', 0)
                rsi = data.get('rsi', 50)
                
                base_prompt += f"- {asset_name} ({asset_id}): {price:.4f}"
                if change > 0:
                    base_prompt += f" (↗ +{change:.2f}%)"
                elif change < 0:
                    base_prompt += f" (↘ {change:.2f}%)"
                base_prompt += f" | RSI: {rsi:.1f}\n"
        
        base_prompt += """
يجب أن تكون إجابتك في صيغة JSON بالشكل التالي:
{
    "message": "رسالتك هنا باللغة العربية",
    "analysis_type": "نوع التحليل (تحليل فني، أساسي، عام، إجابة عامة)",
    "confidence": "مستوى الثقة في التحليل (منخفض، متوسط، عالي)",
    "recommendations": ["قائمة بالتوصيات إن وجدت"],
    "risk_warning": "تحذير من المخاطر إن وجد"
}
"""
        
        return base_prompt
    
    def _get_asset_name(self, asset_id: str) -> str:
        """الحصول على اسم الأصل باللغة العربية"""
        # البحث في قاعدة المعرفة
        for category in self.financial_knowledge.values():
            if asset_id in category:
                return category[asset_id]['name']
        
        # إذا لم يتم العثور على الاسم، استخدم المعرف
        return asset_id
    
    def analyze_market_with_ai(self, asset_id: str, market_data: Dict) -> Optional[Dict]:
        """تحليل السوق باستخدام الذكاء الاصطناعي المتطور"""
        try:
            # الحصول على معلومات الأصل
            asset_info = self._get_asset_info(asset_id)
            
            # بناء تحليل شامل
            analysis_prompt = self._build_market_analysis_prompt(asset_id, market_data, asset_info)
            
            # الحصول على التحليل من الذكاء الاصطناعي
            ai_analysis = self._get_ai_market_analysis(analysis_prompt)
            
            if ai_analysis:
                # إنشاء إشارة التداول المطورة
                signal = self._create_enhanced_trading_signal(asset_id, market_data, ai_analysis, asset_info)
                return signal
            
        except Exception as e:
            logging.error(f"خطأ في تحليل السوق بالذكاء الاصطناعي: {str(e)}")
            return None
        
        return None
    
    def _get_asset_info(self, asset_id: str) -> Dict:
        """الحصول على معلومات الأصل من قاعدة المعرفة"""
        for category_name, category in self.financial_knowledge.items():
            if asset_id in category:
                info = category[asset_id].copy()
                info['category'] = category_name
                return info
        
        # معلومات افتراضية
        return {
            'name': asset_id,
            'category': 'unknown',
            'volatility': 'متوسطة',
            'key_levels': []
        }
    
    def _build_market_analysis_prompt(self, asset_id: str, market_data: Dict, asset_info: Dict) -> str:
        """بناء prompt تحليل السوق المتطور"""
        
        current_price = market_data.get('price', 0)
        rsi = market_data.get('rsi', 50)
        sma_short = market_data.get('sma_short', 0)
        sma_long = market_data.get('sma_long', 0)
        price_change = market_data.get('price_change_5', 0)
        trend = market_data.get('trend', 'sideways')
        
        prompt = f"""
أنت خبير تحليل فني ومالي متقدم. قم بتحليل {asset_info['name']} ({asset_id}) وتقديم إشارة تداول دقيقة.

معلومات الأصل:
- الاسم: {asset_info['name']}
- الفئة: {asset_info['category']}
- مستوى التقلب: {asset_info['volatility']}
- المستويات المهمة: {asset_info.get('key_levels', [])}

البيانات الفنية الحالية:
- السعر الحالي: {current_price}
- مؤشر RSI: {rsi}
- المتوسط المتحرك القصير (20): {sma_short}
- المتوسط المتحرك الطويل (50): {sma_long}
- التغيير في آخر 5 فترات: {price_change}%
- الاتجاه العام: {trend}

التحليل المطلوب:
1. تحديد اتجاه السوق (صاعد/هابط/جانبي)
2. تقييم قوة الاتجاه
3. تحديد مستويات الدعم والمقاومة
4. تقييم حالة التشبع الشرائي/البيعي
5. تقديم توصية (شراء/بيع/انتظار)
6. تحديد مستوى الثقة في التحليل
7. تحديد أهداف السعر ووقف الخسارة

أجب بصيغة JSON:
{{
    "signal_type": "BUY/SELL/HOLD",
    "confidence": 75-95,
    "reason": "سبب الإشارة",
    "market_condition": "حالة السوق",
    "trend_strength": "قوة الاتجاه",
    "support_level": "مستوى الدعم",
    "resistance_level": "مستوى المقاومة", 
    "target_price": "السعر المستهدف",
    "stop_loss": "وقف الخسارة",
    "risk_level": "LOW/MEDIUM/HIGH",
    "time_horizon": "قصير/متوسط/طويل المدى",
    "analysis_summary": "ملخص التحليل"
}}
"""
        
        return prompt
    
    def _get_ai_market_analysis(self, prompt: str) -> Optional[Dict]:
        """الحصول على تحليل السوق من الذكاء الاصطناعي"""
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=800,
                response_format={"type": "json_object"}
            )
            
            if response.choices and response.choices[0].message and response.choices[0].message.content:
                try:
                    analysis = json.loads(response.choices[0].message.content)
                    return analysis
                except json.JSONDecodeError as e:
                    logging.error(f"خطأ في تحليل استجابة الذكاء الاصطناعي: {str(e)}")
                    return None
            
        except Exception as e:
            logging.error(f"خطأ في الحصول على تحليل الذكاء الاصطناعي: {str(e)}")
            return None
        
        return None
    
    def _create_enhanced_trading_signal(self, asset_id: str, market_data: Dict, 
                                      ai_analysis: Dict, asset_info: Dict) -> Dict:
        """إنشاء إشارة تداول محسنة"""
        
        current_time = datetime.now()
        
        # استخراج البيانات من التحليل
        signal_type = ai_analysis.get('signal_type', 'HOLD')
        confidence = min(95, max(75, ai_analysis.get('confidence', 80)))
        reason = ai_analysis.get('reason', 'تحليل فني متوازن')
        
        # حساب معلومات إضافية
        current_price = market_data.get('price', 0)
        target_price = ai_analysis.get('target_price')
        stop_loss = ai_analysis.get('stop_loss')
        
        # تحويل إلى أرقام إذا كانت نصوص
        try:
            if isinstance(target_price, str):
                target_price = float(target_price) if target_price.replace('.', '').isdigit() else current_price * 1.02
            elif target_price is None:
                target_price = current_price * 1.02 if signal_type == 'BUY' else current_price * 0.98
        except:
            target_price = current_price * 1.02 if signal_type == 'BUY' else current_price * 0.98
            
        try:
            if isinstance(stop_loss, str):
                stop_loss = float(stop_loss) if stop_loss.replace('.', '').isdigit() else current_price * 0.98
            elif stop_loss is None:
                stop_loss = current_price * 0.98 if signal_type == 'BUY' else current_price * 1.02
        except:
            stop_loss = current_price * 0.98 if signal_type == 'BUY' else current_price * 1.02
        
        signal = {
            'asset_id': asset_id,
            'asset_name': asset_info['name'],
            'type': signal_type,
            'price': current_price,
            'confidence': confidence,
            'timestamp': current_time.timestamp(),
            'reason': reason,
            'rsi': market_data.get('rsi', 50),
            'sma_short': market_data.get('sma_short', current_price),
            'sma_long': market_data.get('sma_long', current_price),
            'price_change_5': market_data.get('price_change_5', 0),
            'target_price': target_price,
            'stop_loss': stop_loss,
            'risk_level': ai_analysis.get('risk_level', 'MEDIUM'),
            'market_condition': ai_analysis.get('market_condition', 'متوازن'),
            'trend_strength': ai_analysis.get('trend_strength', 'متوسط'),
            'time_horizon': ai_analysis.get('time_horizon', 'قصير المدى'),
            'analysis_summary': ai_analysis.get('analysis_summary', 'تحليل فني شامل'),
            'ai_powered': True
        }
        
        return signal
    
    def get_market_insights(self, user_question: str) -> str:
        """الحصول على رؤى السوق العامة"""
        try:
            insights_prompt = f"""
أنت خبير اقتصادي ومحلل أسواق مالية. المستخدم يسأل: "{user_question}"

قدم إجابة شاملة ومفيدة تتضمن:
1. تحليل السؤال والسياق
2. معلومات ذات صلة بالأسواق المالية
3. نصائح عملية إن أمكن
4. تحذيرات من المخاطر

أجب باللغة العربية بصيغة JSON:
{{
    "message": "إجابتك الشاملة هنا",
    "insights": ["رؤية 1", "رؤية 2", "رؤية 3"],
    "recommendations": ["توصية 1", "توصية 2"],
    "risk_warning": "تحذير من المخاطر"
}}
"""
            
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": insights_prompt}],
                max_completion_tokens=1000,
                
                response_format={"type": "json_object"}
            )
            
            if response.choices and response.choices[0].message and response.choices[0].message.content:
                try:
                    insights = json.loads(response.choices[0].message.content)
                    return insights.get('message', 'عذراً، لم أتمكن من تقديم رؤى مفيدة')
                except json.JSONDecodeError:
                    return response.choices[0].message.content or "عذراً، حدث خطأ في المعالجة"
            
            return "عذراً، لم أتمكن من الحصول على رؤى السوق"
            
        except Exception as e:
            logging.error(f"خطأ في الحصول على رؤى السوق: {str(e)}")
            return "عذراً، حدث خطأ تقني. يرجى المحاولة مرة أخرى"
    
    def reset_conversation(self):
        """إعادة تعيين ذاكرة المحادثة"""
        self.conversation_memory = []
        logging.info("تم إعادة تعيين ذاكرة المحادثة")
    
    def get_ai_learning_stats(self) -> Dict:
        """الحصول على إحصائيات نظام التعلم الذكي"""
        try:
            return {
                'ai_enabled': True,
                'model': self.model,
                'conversation_count': len(self.conversation_memory),
                'status': 'متصل',
                'last_updated': datetime.now().isoformat(),
                'features': {
                    'market_analysis': self.analysis_settings.get('market_analysis_enabled', True),
                    'technical_indicators': self.analysis_settings.get('technical_indicators', True),
                    'sentiment_analysis': self.analysis_settings.get('sentiment_analysis', True),
                    'risk_assessment': self.analysis_settings.get('risk_assessment', True)
                }
            }
        except Exception as e:
            logging.error(f"خطأ في إحصائيات AI: {str(e)}")
            return {
                'ai_enabled': False,
                'error': str(e),
                'status': 'خطأ'
            }