"""
نظام التحليل الفني المتقدم والذكي
Advanced Smart Technical Analysis System

هذا النظام يحل المشاكل التالية:
1. استقرار تحليل الاتجاه - مربوط بوقت الإشارة
2. ربط التحليل بالمؤشرات الفنية المتعددة
3. نظام تعلم ذاتي لتطوير الدقة
4. تجنب الإشارات الخاطئة
"""

import time
import random
import math
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class TrendDirection(Enum):
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    SIDEWAYS = "sideways"

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class MarketState:
    """حالة السوق مع المؤشرات الفنية"""
    price: float
    rsi: float
    macd: float
    bollinger_upper: float
    bollinger_lower: float
    volume_sma: float
    atr: float  # Average True Range
    stochastic: float
    williams_r: float
    timestamp: float

@dataclass
class TechnicalSignal:
    """إشارة تحليل فني محسنة"""
    asset_id: str
    signal_type: SignalType
    confidence: float
    trend: TrendDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    timestamp: float
    technical_reasoning: str
    indicators_consensus: Dict[str, float]
    risk_reward_ratio: float
    volatility_score: float
    locked_until: float  # الإشارة مقفلة حتى هذا الوقت

class SmartTechnicalAnalyzer:
    """محلل فني ذكي متطور مع نظام تعلم ذاتي"""
    
    def __init__(self):
        # بيانات تاريخية للتعلم الذاتي
        self.historical_signals = []
        self.signal_accuracy_log = {}
        self.learning_weights = {
            'rsi': 0.2,
            'macd': 0.25,
            'bollinger': 0.2,
            'volume': 0.15,
            'stochastic': 0.1,
            'williams_r': 0.1
        }
        
        # إعدادات النظام الذكي
        self.min_signal_interval = 300  # 5 دقائق حد أدنى بين الإشارات
        self.trend_stability_threshold = 0.7
        self.confidence_threshold = 75.0
        self.active_signals = {}  # الإشارات النشطة المقفلة
        
        # إحصائيات الأداء
        self.performance_stats = {
            'total_signals': 0,
            'successful_signals': 0,
            'accuracy_rate': 0.0,
            'avg_profit_loss': 0.0
        }

    def calculate_technical_indicators(self, asset_id: str, current_price: float) -> MarketState:
        """حساب المؤشرات الفنية المتقدمة"""
        
        # محاكاة بيانات تاريخية واقعية للمؤشرات
        price_volatility = random.uniform(0.5, 3.0)
        
        # RSI (Relative Strength Index)
        rsi_base = random.uniform(25, 75)
        rsi = max(0, min(100, rsi_base + random.gauss(0, 5)))
        
        # MACD (Moving Average Convergence Divergence)
        macd = random.uniform(-0.5, 0.5) * current_price * 0.001
        
        # Bollinger Bands
        bollinger_width = current_price * 0.02 * price_volatility
        bollinger_upper = current_price + bollinger_width
        bollinger_lower = current_price - bollinger_width
        
        # Volume SMA
        volume_sma = random.uniform(0.8, 1.2)
        
        # ATR (Average True Range)
        atr = current_price * random.uniform(0.01, 0.03)
        
        # Stochastic Oscillator
        stochastic = random.uniform(0, 100)
        
        # Williams %R
        williams_r = random.uniform(-100, 0)
        
        return MarketState(
            price=current_price,
            rsi=rsi,
            macd=macd,
            bollinger_upper=bollinger_upper,
            bollinger_lower=bollinger_lower,
            volume_sma=volume_sma,
            atr=atr,
            stochastic=stochastic,
            williams_r=williams_r,
            timestamp=time.time()
        )

    def analyze_trend_stability(self, market_state: MarketState) -> Tuple[TrendDirection, float]:
        """تحليل الاتجاه مع التركيز على الاستقرار"""
        
        indicators_vote = {}
        
        # تصويت RSI
        if market_state.rsi > 70:
            indicators_vote['rsi'] = ('overbought', 0.8)
        elif market_state.rsi < 30:
            indicators_vote['rsi'] = ('oversold', 0.8)
        elif 45 <= market_state.rsi <= 55:
            indicators_vote['rsi'] = ('neutral', 0.6)
        elif market_state.rsi > 55:
            indicators_vote['rsi'] = ('bullish', 0.7)
        else:
            indicators_vote['rsi'] = ('bearish', 0.7)
        
        # تصويت MACD
        if market_state.macd > 0:
            indicators_vote['macd'] = ('bullish', 0.8)
        elif market_state.macd < 0:
            indicators_vote['macd'] = ('bearish', 0.8)
        else:
            indicators_vote['macd'] = ('neutral', 0.5)
        
        # تصويت Bollinger Bands
        if market_state.price > market_state.bollinger_upper:
            indicators_vote['bollinger'] = ('overbought', 0.9)
        elif market_state.price < market_state.bollinger_lower:
            indicators_vote['bollinger'] = ('oversold', 0.9)
        else:
            indicators_vote['bollinger'] = ('neutral', 0.6)
        
        # تصويت Stochastic
        if market_state.stochastic > 80:
            indicators_vote['stochastic'] = ('overbought', 0.7)
        elif market_state.stochastic < 20:
            indicators_vote['stochastic'] = ('oversold', 0.7)
        else:
            indicators_vote['stochastic'] = ('neutral', 0.5)
        
        # حساب الاتجاه النهائي بناءً على الأوزان المحدثة
        bullish_score = 0
        bearish_score = 0
        neutral_score = 0
        
        for indicator, (sentiment, confidence) in indicators_vote.items():
            weight = self.learning_weights.get(indicator, 0.1)
            weighted_confidence = confidence * weight
            
            if sentiment in ['bullish', 'oversold']:
                bullish_score += weighted_confidence
            elif sentiment in ['bearish', 'overbought']:
                bearish_score += weighted_confidence
            else:
                neutral_score += weighted_confidence
        
        # تحديد الاتجاه النهائي
        max_score = max(bullish_score, bearish_score, neutral_score)
        stability = max_score / (bullish_score + bearish_score + neutral_score)
        
        if max_score == bullish_score and stability > self.trend_stability_threshold:
            return TrendDirection.UPTREND, stability
        elif max_score == bearish_score and stability > self.trend_stability_threshold:
            return TrendDirection.DOWNTREND, stability
        else:
            return TrendDirection.SIDEWAYS, stability

    def generate_smart_signal(self, asset_id: str, market_state: MarketState) -> Optional[TechnicalSignal]:
        """توليد إشارة ذكية مع نظام القفل الزمني"""
        
        current_time = time.time()
        
        # فحص القفل الزمني للإشارات النشطة
        if asset_id in self.active_signals:
            if current_time < self.active_signals[asset_id].locked_until:
                return None  # الإشارة مازالت مقفلة
        
        # تحليل الاتجاه مع الاستقرار
        trend, stability = self.analyze_trend_stability(market_state)
        
        # حساب الثقة الإجمالية
        base_confidence = stability * 100
        
        # تطبيق التعلم الذاتي - تعديل الثقة بناءً على الأداء السابق
        asset_history = self.signal_accuracy_log.get(asset_id, {'accuracy': 0.7, 'count': 0})
        learning_factor = min(1.2, max(0.8, asset_history['accuracy']))
        adjusted_confidence = base_confidence * learning_factor
        
        # فحص عتبة الثقة
        if adjusted_confidence < self.confidence_threshold:
            return None
        
        # تحديد نوع الإشارة بناءً على الاتجاه المستقر
        if trend == TrendDirection.UPTREND:
            signal_type = SignalType.BUY
            entry_price = market_state.price
            stop_loss = entry_price - (market_state.atr * 2)
            take_profit = entry_price + (market_state.atr * 3)
        elif trend == TrendDirection.DOWNTREND:
            signal_type = SignalType.SELL
            entry_price = market_state.price
            stop_loss = entry_price + (market_state.atr * 2)
            take_profit = entry_price - (market_state.atr * 3)
        else:
            return None  # لا إشارة في الاتجاه الجانبي غير المستقر
        
        # حساب نسبة المخاطرة للعائد
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        # فحص نسبة المخاطرة للعائد
        if risk_reward_ratio < 1.5:  # نسبة مخاطرة ضعيفة
            return None
        
        # حساب مدة القفل للإشارة (بناءً على التقلبات)
        volatility_score = market_state.atr / market_state.price
        lock_duration = max(300, min(1800, 600 * volatility_score * 10))  # 5-30 دقيقة
        
        # إنشاء الإشارة المحسنة
        signal = TechnicalSignal(
            asset_id=asset_id,
            signal_type=signal_type,
            confidence=min(95, adjusted_confidence),
            trend=trend,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            timestamp=current_time,
            technical_reasoning=self._generate_reasoning(market_state, trend, signal_type),
            indicators_consensus={
                'rsi': market_state.rsi,
                'macd': market_state.macd,
                'bollinger_position': (market_state.price - market_state.bollinger_lower) / 
                                    (market_state.bollinger_upper - market_state.bollinger_lower),
                'stochastic': market_state.stochastic,
                'williams_r': market_state.williams_r
            },
            risk_reward_ratio=risk_reward_ratio,
            volatility_score=volatility_score,
            locked_until=current_time + lock_duration
        )
        
        # حفظ الإشارة كإشارة نشطة مقفلة
        self.active_signals[asset_id] = signal
        
        # تحديث الإحصائيات
        self.performance_stats['total_signals'] += 1
        
        return signal

    def _generate_reasoning(self, market_state: MarketState, trend: TrendDirection, signal_type: SignalType) -> str:
        """توليد تفسير تقني للإشارة"""
        
        reasoning_parts = []
        
        # تحليل RSI
        if market_state.rsi > 70:
            reasoning_parts.append("RSI مرتفع يشير لذروة شراء")
        elif market_state.rsi < 30:
            reasoning_parts.append("RSI منخفض يشير لذروة بيع")
        elif 45 <= market_state.rsi <= 55:
            reasoning_parts.append("RSI متوازن")
        
        # تحليل MACD
        if market_state.macd > 0:
            reasoning_parts.append("MACD إيجابي يدعم الصعود")
        else:
            reasoning_parts.append("MACD سلبي يشير للهبوط")
        
        # تحليل Bollinger Bands
        bollinger_pos = (market_state.price - market_state.bollinger_lower) / (market_state.bollinger_upper - market_state.bollinger_lower)
        if bollinger_pos > 0.8:
            reasoning_parts.append("السعر قرب الحد العلوي لبولنجر")
        elif bollinger_pos < 0.2:
            reasoning_parts.append("السعر قرب الحد السفلي لبولنجر")
        
        # ربط التحليل بالاتجاه
        trend_text = {"uptrend": "صاعد", "downtrend": "هابط", "sideways": "جانبي"}
        signal_text = {"BUY": "شراء", "SELL": "بيع", "HOLD": "انتظار"}
        
        base_reasoning = f"تحليل متقدم: اتجاه {trend_text[trend.value]} مستقر → إشارة {signal_text[signal_type.value]} مؤكدة"
        
        if reasoning_parts:
            detailed_reasoning = " | ".join(reasoning_parts)
            return f"{base_reasoning} | {detailed_reasoning}"
        
        return base_reasoning

    def update_learning_system(self, asset_id: str, signal_timestamp: float, actual_outcome: float):
        """تحديث نظام التعلم الذاتي بناءً على النتائج الفعلية"""
        
        # العثور على الإشارة المقابلة
        if asset_id not in self.signal_accuracy_log:
            self.signal_accuracy_log[asset_id] = {'accuracy': 0.7, 'count': 0, 'total_profit': 0.0}
        
        # تحديث الإحصائيات
        asset_stats = self.signal_accuracy_log[asset_id]
        asset_stats['count'] += 1
        asset_stats['total_profit'] += actual_outcome
        
        # حساب معدل الدقة الجديد
        if actual_outcome > 0:
            self.performance_stats['successful_signals'] += 1
        
        new_accuracy = self.performance_stats['successful_signals'] / self.performance_stats['total_signals']
        asset_stats['accuracy'] = new_accuracy
        
        # تحديث الأوزان بناءً على الأداء
        self._update_indicator_weights(actual_outcome)
        
        # تحديث الإحصائيات العامة
        self.performance_stats['accuracy_rate'] = new_accuracy
        self.performance_stats['avg_profit_loss'] = asset_stats['total_profit'] / asset_stats['count']

    def _update_indicator_weights(self, outcome: float):
        """تحديث أوزان المؤشرات بناءً على الأداء"""
        
        # نظام تعلم بسيط: زيادة وزن المؤشرات الناجحة
        learning_rate = 0.01
        
        if outcome > 0:  # إشارة ناجحة
            # زيادة أوزان جميع المؤشرات قليلاً
            for indicator in self.learning_weights:
                self.learning_weights[indicator] = min(0.4, self.learning_weights[indicator] + learning_rate)
        else:  # إشارة فاشلة
            # تقليل أوزان المؤشرات قليلاً
            for indicator in self.learning_weights:
                self.learning_weights[indicator] = max(0.05, self.learning_weights[indicator] - learning_rate)
        
        # إعادة توازن الأوزان
        total_weight = sum(self.learning_weights.values())
        for indicator in self.learning_weights:
            self.learning_weights[indicator] /= total_weight

    def get_system_status(self) -> Dict[str, Any]:
        """حصول على حالة النظام والإحصائيات"""
        
        return {
            'system_mode': 'advanced_smart_analysis',
            'performance': self.performance_stats,
            'active_signals_count': len(self.active_signals),
            'learning_weights': self.learning_weights,
            'confidence_threshold': self.confidence_threshold,
            'trend_stability_threshold': self.trend_stability_threshold
        }

    def clean_expired_signals(self):
        """تنظيف الإشارات المنتهية الصلاحية"""
        current_time = time.time()
        expired_assets = [
            asset_id for asset_id, signal in self.active_signals.items()
            if current_time > signal.locked_until
        ]
        
        for asset_id in expired_assets:
            del self.active_signals[asset_id]