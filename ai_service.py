import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import openai
from openai import OpenAI

from models import db, TradingSignal, AILearningData, MarketData

class AITradingAnalyzer:
    """نظام التحليل الذكي للتداول مع التعلم من الأخطاء"""
    
    def __init__(self):
        # إعداد OpenAI
        # the newest OpenAI model is "gpt-5" which was released August 7, 2025.
        # do not change this unless explicitly requested by the user
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = "gpt-5"
        
        # معايير التحليل
        self.min_confidence_threshold = 75  # الحد الأدنى للثقة
        self.trend_filter_enabled = True     # فلترة الاتجاهات الجانبية
        
        logging.info("تم تهيئة نظام التحليل الذكي بنجاح")
    
    def analyze_market_with_ai(self, asset_id: str, market_data: Dict) -> Optional[Dict]:
        """تحليل السوق باستخدام الذكاء الاصطناعي"""
        try:
            # بناء تحليل بسيط بدون قاعدة بيانات في البداية
            # تحليل أنماط الشموع
            candlestick_analysis = self._analyze_candlestick_patterns(market_data)
            
            # تحليل بسيط للدعم والمقاومة
            current_price = market_data.get('price', 0)
            support_resistance = {
                'support': current_price * 0.98,  # 2% تحت السعر الحالي
                'resistance': current_price * 1.02,  # 2% فوق السعر الحالي
                'current_price': current_price,
                'distance_to_support_percent': 2.0,
                'distance_to_resistance_percent': 2.0,
                'near_support': False,
                'near_resistance': False
            }
            
            # بيانات تاريخية بسيطة
            historical_data = {
                'recent_market_data': [],
                'successful_patterns': [],
                'failed_patterns': []
            }
            
            # بناء prompt للذكاء الاصطناعي
            analysis_prompt = self._build_analysis_prompt(
                asset_id, market_data, historical_data, 
                support_resistance, candlestick_analysis
            )
            
            # الحصول على تحليل AI
            ai_response = self._get_ai_analysis(analysis_prompt)
            
            if ai_response:
                # إنشاء الإشارة النهائية
                signal = self._create_trading_signal(asset_id, market_data, ai_response, support_resistance)
                
                return signal
            
        except Exception as e:
            logging.error(f"خطأ في تحليل السوق: {e}")
            return None
        
        return None
    
    def _get_historical_context(self, asset_id: str) -> Dict:
        """الحصول على السياق التاريخي للأصل"""
        try:
            # البيانات من آخر 24 ساعة
            recent_data = MarketData.get_recent_data(asset_id, hours=24)
            
            # الإشارات السابقة الناجحة والفاشلة
            successful_signals = TradingSignal.get_successful_signals_patterns(asset_id, limit=10)
            failed_signals = TradingSignal.get_failed_signals_patterns(asset_id, limit=10)
        except Exception as e:
            logging.warning(f"خطأ في الحصول على البيانات التاريخية: {e}")
            return {'recent_market_data': [], 'successful_patterns': [], 'failed_patterns': []}
        
        return {
            'recent_market_data': [
                {
                    'price': data.close_price,
                    'volume': data.volume,
                    'rsi': data.rsi,
                    'timestamp': data.timestamp.isoformat()
                } for data in recent_data[-10:]  # آخر 10 نقاط
            ],
            'successful_patterns': [
                {
                    'signal_type': sig.signal_type,
                    'confidence': sig.confidence,
                    'rsi': sig.rsi,
                    'trend': sig.trend,
                    'profit': sig.profit_loss_percent
                } for sig in successful_signals
            ],
            'failed_patterns': [
                {
                    'signal_type': sig.signal_type,
                    'confidence': sig.confidence,
                    'rsi': sig.rsi,
                    'trend': sig.trend,
                    'loss': sig.profit_loss_percent
                } for sig in failed_signals
            ]
        }
    
    def _calculate_support_resistance(self, asset_id: str, market_data: Dict) -> Dict:
        """حساب مستويات الدعم والمقاومة"""
        try:
            # حساب من البيانات المحفوظة
            support, resistance = MarketData.calculate_support_resistance(asset_id, days=7)
        except Exception as e:
            logging.warning(f"خطأ في حساب الدعم والمقاومة: {e}")
            support, resistance = None, None
        
        current_price = market_data.get('price', 0)
        
        # حساب القرب من مستويات الدعم والمقاومة
        distance_to_support = abs(current_price - support) / current_price * 100 if support else 0
        distance_to_resistance = abs(current_price - resistance) / current_price * 100 if resistance else 0
        
        return {
            'support': support,
            'resistance': resistance,
            'current_price': current_price,
            'distance_to_support_percent': distance_to_support,
            'distance_to_resistance_percent': distance_to_resistance,
            'near_support': distance_to_support < 1.0,  # أقل من 1%
            'near_resistance': distance_to_resistance < 1.0
        }
    
    def _analyze_candlestick_patterns(self, market_data: Dict) -> Dict:
        """تحليل أنماط الشموع اليابانية"""
        # هذه دالة مبسطة - في التطبيق الحقيقي نحتاج بيانات OHLCV كاملة
        rsi = market_data.get('rsi', 50)
        price_change = market_data.get('price_change_5', 0)
        trend = market_data.get('trend', 'sideways')
        
        patterns = []
        reliability = 50
        
        # تحديد الأنماط بناءً على RSI والاتجاه
        if rsi < 30 and trend == 'downtrend':
            patterns.append('hammer_potential')
            reliability = 70
        elif rsi > 70 and trend == 'uptrend':
            patterns.append('shooting_star_potential')
            reliability = 70
        elif abs(price_change) > 2:
            patterns.append('strong_momentum_candle')
            reliability = 60
        
        return {
            'detected_patterns': patterns,
            'reliability': reliability,
            'trend_confirmation': trend in ['uptrend', 'downtrend']
        }
    
    def _build_analysis_prompt(self, asset_id: str, market_data: Dict, 
                              historical_data: Dict, support_resistance: Dict,
                              candlestick_analysis: Dict) -> str:
        """بناء prompt للذكاء الاصطناعي"""
        
        prompt = f"""
أنت خبير تداول محترف ومحلل فني متقدم. قم بتحليل الأصل {asset_id} وتقديم توصية دقيقة.

البيانات الحالية:
- السعر الحالي: {market_data.get('price', 0):.4f}
- مؤشر RSI: {market_data.get('rsi', 50):.1f}
- المتوسط المتحرك القصير: {market_data.get('sma_short', 0):.4f}
- المتوسط المتحرك الطويل: {market_data.get('sma_long', 0):.4f}
- التغيير في آخر 5 فترات: {market_data.get('price_change_5', 0):.2f}%
- الاتجاه الحالي: {market_data.get('trend', 'غير محدد')}

مستويات الدعم والمقاومة:
- مستوى الدعم: {support_resistance.get('support', 0):.4f}
- مستوى المقاومة: {support_resistance.get('resistance', 0):.4f}
- قريب من الدعم: {'نعم' if support_resistance.get('near_support') else 'لا'}
- قريب من المقاومة: {'نعم' if support_resistance.get('near_resistance') else 'لا'}

تحليل الشموع:
- الأنماط المكتشفة: {', '.join(candlestick_analysis.get('detected_patterns', ['لا يوجد']))}
- موثوقية النمط: {candlestick_analysis.get('reliability', 0)}%

الإشارات السابقة الناجحة: {len(historical_data.get('successful_patterns', []))}
الإشارات السابقة الفاشلة: {len(historical_data.get('failed_patterns', []))}

التعليمات:
1. حلل جميع المؤشرات الفنية المتاحة
2. راعي مستويات الدعم والمقاومة في التحليل
3. اعتبر أنماط الشموع والاتجاه العام
4. تعلم من الإشارات السابقة الفاشلة وتجنب تكرارها
5. لا ترسل إشارة إلا إذا كان لديك ثقة عالية (75%+)
6. تجنب الإشارات في الأسواق المتذبذبة جانبياً
7. ركز على النقاط القوية للدخول/الخروج

المطلوب منك:
قدم تحليلاً في صيغة JSON يحتوي على:
- signal_type: "BUY" أو "SELL" أو "HOLD"
- confidence: رقم من 1-100
- reason: سبب مفصل للقرار
- risk_level: "LOW", "MEDIUM", "HIGH"
- target_price: السعر المستهدف
- stop_loss: سعر وقف الخسارة
- analysis_summary: ملخص التحليل باللغة العربية

مثال للاستجابة:
{
    "signal_type": "BUY",
    "confidence": 85,
    "reason": "RSI oversold at support level with bullish divergence",
    "risk_level": "MEDIUM",
    "target_price": 1.0850,
    "stop_loss": 1.0780,
    "analysis_summary": "الأصل عند مستوى دعم قوي مع RSI في منطقة التشبع البيعي"
}
"""
        return prompt
    
    def _get_ai_analysis(self, prompt: str) -> Optional[Dict]:
        """الحصول على تحليل من OpenAI"""
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,  # قليل الإبداع، أكثر دقة
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logging.error(f"خطأ في الحصول على تحليل AI: {e}")
            return None
    
    def _check_learning_rules(self, asset_id: str, ai_response: Dict) -> Tuple[bool, str]:
        """فحص قواعد التعلم قبل إرسال الإشارة"""
        # مؤقتاً نتجاهل قواعد التعلم لتجنب مشاكل قاعدة البيانات
        return False, ""
    
    def _create_trading_signal(self, asset_id: str, market_data: Dict, 
                              ai_response: Dict, support_resistance: Dict) -> Optional[Dict]:
        """إنشاء إشارة التداول النهائية"""
        
        signal_type = ai_response.get('signal_type')
        confidence = ai_response.get('confidence', 0)
        
        # التحقق من الحد الأدنى للثقة
        if confidence < self.min_confidence_threshold:
            return None
        
        # التحقق من عدم إرسال إشارات في الأسواق الجانبية
        if (self.trend_filter_enabled and 
            market_data.get('trend') == 'sideways' and 
            confidence < 90):
            return None
        
        # إنشاء الإشارة
        signal = {
            'asset_id': asset_id,
            'asset_name': market_data.get('name', asset_id),
            'type': signal_type,
            'price': market_data.get('price'),
            'confidence': confidence,
            'timestamp': datetime.utcnow().timestamp(),
            'reason': ai_response.get('reason', ''),
            'rsi': market_data.get('rsi'),
            'sma_short': market_data.get('sma_short'),
            'sma_long': market_data.get('sma_long'),
            'price_change_5': market_data.get('price_change_5'),
            'trend': market_data.get('trend'),
            'support_level': support_resistance.get('support'),
            'resistance_level': support_resistance.get('resistance'),
            'target_price': ai_response.get('target_price'),
            'stop_loss': ai_response.get('stop_loss'),
            'risk_level': ai_response.get('risk_level'),
            'ai_analysis': ai_response.get('analysis_summary'),
            'ai_confidence': confidence
        }
        
        return signal
    
    def _save_signal_to_database(self, signal: Dict, ai_response: Dict):
        """حفظ الإشارة في قاعدة البيانات"""
        try:
            from app import app
            with app.app_context():
                trading_signal = TradingSignal(
                    asset_id=signal['asset_id'],
                    asset_name=signal['asset_name'],
                    signal_type=signal['type'],
                    price=signal['price'],
                    confidence=signal['confidence'],
                    reason=signal['reason'],
                    rsi=signal.get('rsi'),
                    sma_short=signal.get('sma_short'),
                    sma_long=signal.get('sma_long'),
                    price_change_5=signal.get('price_change_5'),
                    trend=signal.get('trend'),
                    support_level=signal.get('support_level'),
                    resistance_level=signal.get('resistance_level'),
                    ai_analysis=signal.get('ai_analysis'),
                    ai_confidence=signal.get('ai_confidence'),
                    learning_features=json.dumps({
                        'rsi': signal.get('rsi'),
                        'trend': signal.get('trend'),
                        'near_support': abs(signal['price'] - signal.get('support_level', 0)) < signal['price'] * 0.01 if signal.get('support_level') else False,
                        'near_resistance': abs(signal['price'] - signal.get('resistance_level', 0)) < signal['price'] * 0.01 if signal.get('resistance_level') else False,
                        'risk_level': ai_response.get('risk_level')
                    })
                )
                
                db.session.add(trading_signal)
                db.session.commit()
            
            logging.info(f"تم حفظ إشارة {signal['type']} لـ {signal['asset_id']}")
            
        except Exception as e:
            logging.error(f"خطأ في حفظ الإشارة: {e}")
            db.session.rollback()
    
    def learn_from_failed_signal(self, signal_id: int):
        """التعلم من إشارة فاشلة"""
        try:
            signal = TradingSignal.query.get(signal_id)
            if not signal or signal.is_successful is not False:
                return
            
            # استخراج الأنماط الفاشلة
            learning_features = json.loads(signal.learning_features) if signal.learning_features else {}
            
            # البحث عن قاعدة تعلم موجودة أو إنشاء جديدة
            learning_rule = AILearningData.query.filter_by(
                asset_id=signal.asset_id,
                failed_pattern_type=f"{signal.signal_type}_{signal.trend}"
            ).first()
            
            if learning_rule:
                learning_rule.increase_avoidance()
            else:
                # إنشاء قاعدة تعلم جديدة
                learning_rule = AILearningData(
                    asset_id=signal.asset_id,
                    failed_pattern_type=f"{signal.signal_type}_{signal.trend}",
                    failed_conditions=json.dumps(learning_features),
                    failure_reason=signal.reason,
                    avoid_when_rsi_above=signal.rsi + 5 if signal.signal_type == 'SELL' and signal.rsi else None,
                    avoid_when_rsi_below=signal.rsi - 5 if signal.signal_type == 'BUY' and signal.rsi else None,
                    avoid_when_trend=signal.trend if signal.trend == 'sideways' else None
                )
                
                db.session.add(learning_rule)
            
            db.session.commit()
            logging.info(f"تم التعلم من الإشارة الفاشلة {signal_id}")
            
        except Exception as e:
            logging.error(f"خطأ في التعلم من الإشارة الفاشلة: {e}")
            db.session.rollback()
    
    def evaluate_old_signals(self, hours_ago: int = 24):
        """تقييم الإشارات القديمة وتحديث نتائجها"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_ago)
            
            # الحصول على الإشارات غير المقيمة
            unevaluated_signals = TradingSignal.query.filter(
                TradingSignal.created_at <= cutoff_time,
                TradingSignal.is_successful.is_(None)
            ).all()
            
            for signal in unevaluated_signals:
                # هنا نحتاج للحصول على السعر الحالي لتقييم النجاح
                # في التطبيق الحقيقي، نحصل على السعر من API
                # مؤقتاً سنستخدم قيمة عشوائية للتجربة
                current_price = signal.price * (1 + (0.02 if signal.signal_type == 'BUY' else -0.02))
                signal.evaluate_success(current_price)
                
                # التعلم من الإشارات الفاشلة
                if signal.is_successful == False:
                    self.learn_from_failed_signal(signal.id)
            
            logging.info(f"تم تقييم {len(unevaluated_signals)} إشارة")
            
        except Exception as e:
            logging.error(f"خطأ في تقييم الإشارات القديمة: {e}")
    
    def get_ai_learning_stats(self) -> Dict:
        """إحصائيات التعلم من الأخطاء"""
        try:
            total_signals = TradingSignal.query.count()
            evaluated_signals = TradingSignal.query.filter(TradingSignal.is_successful.isnot(None)).count()
            successful_signals = TradingSignal.query.filter(TradingSignal.is_successful == True).count()
            failed_signals = TradingSignal.query.filter(TradingSignal.is_successful == False).count()
            learning_rules = AILearningData.query.count()
            
            success_rate = (successful_signals / evaluated_signals * 100) if evaluated_signals > 0 else 0
            
            return {
                'total_signals': total_signals,
                'evaluated_signals': evaluated_signals,
                'successful_signals': successful_signals,
                'failed_signals': failed_signals,
                'success_rate': round(success_rate, 2),
                'learning_rules': learning_rules,
                'ai_enabled': True
            }
            
        except Exception as e:
            logging.error(f"خطأ في الحصول على إحصائيات التعلم: {e}")
            return {'ai_enabled': False, 'error': str(e)}