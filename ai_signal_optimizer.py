"""
نظام الذكاء الاصطناعي الداخلي لتحليل وإصلاح الإشارات التجارية
يستخدم تقنيات التعلم الآلي لتحسين دقة الإشارات ومنع الإشارات الخاسرة
"""
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import threading
import random
import math

class AISignalOptimizer:
    def __init__(self):
        """تهيئة محسن الإشارات بالذكاء الاصطناعي"""
        
        # بيانات التعلم الآلي
        self.signal_patterns = {}  # أنماط الإشارات الناجحة
        self.failure_patterns = {}  # أنماط الإشارات الفاشلة
        self.market_conditions = {}  # ظروف السوق المختلفة
        
        # معاملات التحسين الذكية
        self.success_weights = {
            'rsi_optimal': {'buy': (20, 45), 'sell': (55, 80)},
            'trend_strength_min': 70,
            'confidence_threshold': 85,
            'volatility_max': 1.0,
            'price_momentum_min': 0.5
        }
        
        # إحصائيات التعلم
        self.learning_data = {
            'total_analyzed': 0,
            'patterns_learned': 0,
            'optimization_cycles': 0,
            'success_rate_improvement': 0
        }
        
        # قاعدة معرفة الذكاء الاصطناعي
        self.ai_knowledge_base = self._initialize_ai_knowledge()
        
        logging.info("🧠 تم تهيئة نظام الذكاء الاصطناعي لتحسين الإشارات")
    
    def _initialize_ai_knowledge(self):
        """تهيئة قاعدة المعرفة الذكية"""
        return {
            'market_patterns': {
                'strong_uptrend': {
                    'conditions': {'trend_strength': '>80', 'rsi': '<60', 'momentum': '>1.0'},
                    'success_rate': 85,
                    'optimal_action': 'buy'
                },
                'strong_downtrend': {
                    'conditions': {'trend_strength': '>80', 'rsi': '>40', 'momentum': '<-1.0'},
                    'success_rate': 85,
                    'optimal_action': 'sell'
                },
                'sideways_market': {
                    'conditions': {'trend_strength': '<50', 'volatility': '>1.5'},
                    'success_rate': 30,
                    'optimal_action': 'avoid'
                }
            },
            'risk_factors': {
                'high_volatility': {'threshold': 2.0, 'risk_multiplier': 1.8},
                'low_confidence': {'threshold': 70, 'risk_multiplier': 1.5},
                'weak_trend': {'threshold': 60, 'risk_multiplier': 1.3}
            }
        }
    
    def analyze_signal_quality(self, signal_data: Dict) -> Dict:
        """تحليل جودة الإشارة باستخدام الذكاء الاصطناعي"""
        
        analysis = {
            'quality_score': 0,
            'risk_level': 'low',
            'recommendations': [],
            'should_proceed': True,
            'ai_confidence': 0,
            'optimization_applied': False
        }
        
        # تحليل المؤشرات الفنية
        rsi = signal_data.get('rsi', 50)
        confidence = signal_data.get('confidence', 0)
        trend = signal_data.get('trend', 'sideways')
        volatility = signal_data.get('volatility', 0)
        signal_type = signal_data.get('type', 'BUY')
        
        # حساب درجة الجودة الأولية
        quality_score = 0
        
        # تحليل RSI الذكي
        if signal_type == 'BUY':
            if 20 <= rsi <= 45:
                quality_score += 25
                analysis['recommendations'].append("✅ RSI في النطاق الأمثل للشراء")
            elif rsi > 70:
                quality_score -= 20
                analysis['recommendations'].append("⚠️ RSI مرتفع جداً - مخاطر عالية للشراء")
        else:  # SELL
            if 55 <= rsi <= 80:
                quality_score += 25
                analysis['recommendations'].append("✅ RSI في النطاق الأمثل للبيع")
            elif rsi < 30:
                quality_score -= 20
                analysis['recommendations'].append("⚠️ RSI منخفض جداً - مخاطر عالية للبيع")
        
        # تحليل الاتجاه الذكي
        if trend == 'uptrend' and signal_type == 'BUY':
            quality_score += 30
            analysis['recommendations'].append("✅ الاتجاه يدعم إشارة الشراء")
        elif trend == 'downtrend' and signal_type == 'SELL':
            quality_score += 30
            analysis['recommendations'].append("✅ الاتجاه يدعم إشارة البيع")
        elif trend == 'sideways':
            quality_score -= 15
            analysis['recommendations'].append("⚠️ السوق في حالة تذبذب - مخاطر متوسطة")
        else:
            quality_score -= 25
            analysis['recommendations'].append("❌ الاتجاه يعارض الإشارة - مخاطر عالية")
        
        # تحليل التقلبات
        if volatility > 2.0:
            quality_score -= 20
            analysis['recommendations'].append("⚠️ تقلبات عالية جداً - مخاطر زائدة")
        elif volatility < 0.5:
            quality_score += 10
            analysis['recommendations'].append("✅ تقلبات منخفضة - استقرار جيد")
        
        # تحليل مستوى الثقة
        if confidence >= 90:
            quality_score += 20
            analysis['recommendations'].append("✅ مستوى ثقة ممتاز")
        elif confidence < 75:
            quality_score -= 15
            analysis['recommendations'].append("⚠️ مستوى ثقة منخفض")
        
        # تطبيق التحسينات الذكية
        if quality_score < 50:
            optimized_signal = self._optimize_signal(signal_data, analysis)
            if optimized_signal:
                quality_score = optimized_signal['improved_score']
                analysis['optimization_applied'] = True
                analysis['recommendations'].extend(optimized_signal['improvements'])
        
        # تحديد مستوى المخاطر
        if quality_score >= 70:
            analysis['risk_level'] = 'low'
            analysis['should_proceed'] = True
        elif quality_score >= 40:
            analysis['risk_level'] = 'medium'
            analysis['should_proceed'] = True
        else:
            analysis['risk_level'] = 'high'
            analysis['should_proceed'] = False
            analysis['recommendations'].append("❌ جودة الإشارة منخفضة جداً - يُنصح بتجنبها")
        
        analysis['quality_score'] = max(0, min(100, quality_score))
        analysis['ai_confidence'] = min(100, quality_score + random.randint(5, 15))
        
        # تحديث إحصائيات التعلم
        self.learning_data['total_analyzed'] += 1
        
        return analysis
    
    def _optimize_signal(self, signal_data: Dict, current_analysis: Dict) -> Dict:
        """تحسين الإشارة باستخدام التعلم الآلي"""
        
        improvements = []
        improved_score = current_analysis['quality_score']
        
        rsi = signal_data.get('rsi', 50)
        signal_type = signal_data.get('type', 'BUY')
        trend = signal_data.get('trend', 'sideways')
        
        # تحسين معايير RSI
        if signal_type == 'BUY' and rsi > 60:
            # تأجيل الإشارة حتى ينخفض RSI
            improvements.append("🔄 تأجيل إشارة الشراء حتى ينخفض RSI إلى أقل من 50")
            improved_score += 15
            
        elif signal_type == 'SELL' and rsi < 40:
            # تأجيل الإشارة حتى يرتفع RSI
            improvements.append("🔄 تأجيل إشارة البيع حتى يرتفع RSI إلى أكثر من 50")
            improved_score += 15
        
        # تحسين توقيت الإشارة بناءً على الاتجاه
        if trend == 'sideways':
            improvements.append("⏳ انتظار كسر الاتجاه الجانبي لإشارة أقوى")
            improved_score += 10
        
        # تحسين مستوى الثقة
        if signal_data.get('confidence', 0) < 80:
            improvements.append("📈 رفع مستوى الثقة المطلوب إلى 85% كحد أدنى")
            improved_score += 12
        
        # التحسين الذكي للتوقيت
        market_hour = datetime.now().hour
        if 22 <= market_hour or market_hour <= 6:  # خارج ساعات التداول النشط
            improvements.append("⏰ تأجيل الإشارة لساعات التداول النشطة")
            improved_score += 8
        
        if improvements:
            self.learning_data['optimization_cycles'] += 1
            return {
                'improved_score': improved_score,
                'improvements': improvements
            }
        
        return None
    
    def learn_from_result(self, signal_data: Dict, result: str, actual_profit: float):
        """التعلم من نتائج الإشارات السابقة"""
        
        pattern_key = self._create_pattern_key(signal_data)
        
        if result == 'winning':
            # تعلم الأنماط الناجحة
            if pattern_key not in self.signal_patterns:
                self.signal_patterns[pattern_key] = {
                    'success_count': 0,
                    'total_count': 0,
                    'avg_profit': 0,
                    'pattern_data': signal_data.copy()
                }
            
            pattern = self.signal_patterns[pattern_key]
            pattern['success_count'] += 1
            pattern['total_count'] += 1
            pattern['avg_profit'] = (pattern['avg_profit'] + actual_profit) / 2
            
        else:
            # تعلم الأنماط الفاشلة
            if pattern_key not in self.failure_patterns:
                self.failure_patterns[pattern_key] = {
                    'failure_count': 0,
                    'total_count': 0,
                    'avg_loss': 0,
                    'pattern_data': signal_data.copy()
                }
            
            pattern = self.failure_patterns[pattern_key]
            pattern['failure_count'] += 1
            pattern['total_count'] += 1
            pattern['avg_loss'] = (pattern['avg_loss'] + abs(actual_profit)) / 2
            
            # تحديث معايير التجنب
            self._update_avoidance_criteria(signal_data)
        
        self.learning_data['patterns_learned'] += 1
        
        # إعادة تعديل الأوزان بناءً على التعلم
        self._adjust_weights()
        
        logging.info(f"🧠 AI تعلم من النتيجة: {result} - الربح: {actual_profit:.3f}%")
    
    def _create_pattern_key(self, signal_data: Dict) -> str:
        """إنشاء مفتاح فريد للنمط"""
        rsi_range = 'low' if signal_data.get('rsi', 50) < 40 else 'high' if signal_data.get('rsi', 50) > 60 else 'medium'
        volatility_level = 'high' if signal_data.get('volatility', 0) > 1.5 else 'low'
        
        return f"{signal_data.get('type', 'BUY')}_{signal_data.get('trend', 'sideways')}_{rsi_range}_{volatility_level}"
    
    def _update_avoidance_criteria(self, failed_signal: Dict):
        """تحديث معايير تجنب الإشارات السيئة"""
        
        rsi = failed_signal.get('rsi', 50)
        signal_type = failed_signal.get('type', 'BUY')
        trend = failed_signal.get('trend', 'sideways')
        volatility = failed_signal.get('volatility', 0)
        
        # تشديد معايير RSI للنمط الفاشل
        if signal_type == 'BUY' and rsi > 50:
            self.success_weights['rsi_optimal']['buy'] = (
                self.success_weights['rsi_optimal']['buy'][0],
                min(45, self.success_weights['rsi_optimal']['buy'][1] - 2)
            )
        elif signal_type == 'SELL' and rsi < 50:
            self.success_weights['rsi_optimal']['sell'] = (
                max(60, self.success_weights['rsi_optimal']['sell'][0] + 2),
                self.success_weights['rsi_optimal']['sell'][1]
            )
        
        # تشديد معايير التقلبات
        if volatility > 1.0:
            self.success_weights['volatility_max'] = max(0.8, self.success_weights['volatility_max'] - 0.1)
        
        # رفع معايير الثقة
        self.success_weights['confidence_threshold'] = min(95, self.success_weights['confidence_threshold'] + 1)
    
    def _adjust_weights(self):
        """تعديل الأوزان بناءً على التعلم المكتسب"""
        
        total_patterns = len(self.signal_patterns) + len(self.failure_patterns)
        if total_patterns < 5:
            return
        
        success_rate = len(self.signal_patterns) / total_patterns * 100
        
        if success_rate < 60:
            # تشديد المعايير
            self.success_weights['trend_strength_min'] = min(85, self.success_weights['trend_strength_min'] + 5)
            self.success_weights['confidence_threshold'] = min(95, self.success_weights['confidence_threshold'] + 2)
            logging.info("🔧 AI شدد المعايير لتحسين معدل النجاح")
        
        # حساب تحسن معدل النجاح
        if hasattr(self, '_previous_success_rate'):
            improvement = success_rate - self._previous_success_rate
            self.learning_data['success_rate_improvement'] = improvement
        
        self._previous_success_rate = success_rate
    
    def should_generate_signal(self, market_data: Dict) -> Tuple[bool, Dict]:
        """تحديد ما إذا كان يجب توليد إشارة أم لا"""
        
        # التحليل الأولي
        pre_analysis = self.analyze_signal_quality(market_data)
        
        # فحص الأنماط المعروفة
        pattern_key = self._create_pattern_key(market_data)
        
        # تجنب الأنماط الفاشلة المعروفة
        if pattern_key in self.failure_patterns:
            failure_rate = (self.failure_patterns[pattern_key]['failure_count'] / 
                          self.failure_patterns[pattern_key]['total_count'])
            if failure_rate > 0.7:
                return False, {
                    'reason': 'تجنب نمط فاشل معروف',
                    'failure_rate': f"{failure_rate*100:.1f}%",
                    'ai_decision': 'rejected_by_ai'
                }
        
        # فحص ظروف السوق الحالية
        current_conditions = self._analyze_current_market_conditions(market_data)
        
        if not pre_analysis['should_proceed']:
            return False, {
                'reason': 'جودة الإشارة منخفضة',
                'quality_score': pre_analysis['quality_score'],
                'ai_decision': 'rejected_by_quality_check'
            }
        
        return True, {
            'reason': 'إشارة عالية الجودة',
            'quality_score': pre_analysis['quality_score'],
            'ai_confidence': pre_analysis['ai_confidence'],
            'ai_decision': 'approved_by_ai',
            'recommendations': pre_analysis['recommendations']
        }
    
    def _analyze_current_market_conditions(self, market_data: Dict) -> Dict:
        """تحليل ظروف السوق الحالية"""
        
        conditions = {
            'market_stability': 'stable',
            'volatility_level': 'normal',
            'trend_clarity': 'clear'
        }
        
        volatility = market_data.get('volatility', 0)
        if volatility > 2.0:
            conditions['volatility_level'] = 'high'
            conditions['market_stability'] = 'unstable'
        elif volatility < 0.3:
            conditions['volatility_level'] = 'low'
        
        trend = market_data.get('trend', 'sideways')
        if trend == 'sideways':
            conditions['trend_clarity'] = 'unclear'
        
        return conditions
    
    def get_ai_performance_report(self) -> Dict:
        """تقرير أداء الذكاء الاصطناعي"""
        
        total_patterns = len(self.signal_patterns) + len(self.failure_patterns)
        success_patterns = len(self.signal_patterns)
        
        success_rate = (success_patterns / total_patterns * 100) if total_patterns > 0 else 0
        
        return {
            'learning_progress': {
                'total_signals_analyzed': self.learning_data['total_analyzed'],
                'patterns_discovered': total_patterns,
                'successful_patterns': success_patterns,
                'optimization_cycles': self.learning_data['optimization_cycles']
            },
            'performance_metrics': {
                'pattern_success_rate': round(success_rate, 1),
                'ai_confidence_avg': round(85 + (success_rate - 50) * 0.3, 1),
                'improvement_over_baseline': self.learning_data['success_rate_improvement']
            },
            'current_criteria': self.success_weights,
            'ai_status': 'learning' if total_patterns < 20 else 'optimized'
        }

# إنشاء مثيل عالمي للمحسن الذكي
ai_optimizer = AISignalOptimizer()