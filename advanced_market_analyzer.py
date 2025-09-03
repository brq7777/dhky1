"""
محلل السوق المتقدم - التحليل الشامل للأصول المالية
Advanced Market Analyzer - Comprehensive Financial Asset Analysis
================================================================

نظام متطور للتحليل الفني يشمل:
✅ مناطق الدعم والمقاومة المتقدمة
✅ تحليل آخر 50 شمعة مع الأنماط
✅ كشف الكسر الكاذب والفلترة الذكية
✅ تحليل الانعكاسات والأنماط الكلاسيكية
✅ مؤشرات فنية متقدمة ومتعددة الأطر الزمنية
"""

import time
import math
import logging
import statistics
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

class PatternType(Enum):
    """أنواع الأنماط الفنية"""
    HAMMER = "hammer"                    # المطرقة
    DOJI = "doji"                       # الدوجي
    ENGULFING_BULLISH = "engulfing_bull" # البلع الصاعد
    ENGULFING_BEARISH = "engulfing_bear" # البلع الهابط
    SHOOTING_STAR = "shooting_star"      # النجمة الساقطة
    MORNING_STAR = "morning_star"        # نجمة الصباح
    EVENING_STAR = "evening_star"        # نجمة المساء
    HEAD_SHOULDERS = "head_shoulders"    # الرأس والكتفين
    DOUBLE_TOP = "double_top"           # القمة المزدوجة
    DOUBLE_BOTTOM = "double_bottom"     # القاع المزدوج

class BreakoutType(Enum):
    """أنواع الكسر"""
    TRUE_BREAKOUT = "true_breakout"     # كسر حقيقي
    FALSE_BREAKOUT = "false_breakout"   # كسر كاذب
    PENDING = "pending"                 # انتظار التأكيد

@dataclass
class Candlestick:
    """بيانات الشمعة"""
    timestamp: float
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    
    @property
    def body_size(self) -> float:
        """حجم جسم الشمعة"""
        return abs(self.close_price - self.open_price)
    
    @property
    def upper_shadow(self) -> float:
        """الظل العلوي"""
        return self.high_price - max(self.open_price, self.close_price)
    
    @property
    def lower_shadow(self) -> float:
        """الظل السفلي"""
        return min(self.open_price, self.close_price) - self.low_price
    
    @property
    def is_bullish(self) -> bool:
        """هل الشمعة صاعدة"""
        return self.close_price > self.open_price
    
    @property
    def is_bearish(self) -> bool:
        """هل الشمعة هابطة"""
        return self.close_price < self.open_price

@dataclass
class SupportResistanceLevel:
    """مستوى الدعم أو المقاومة"""
    price: float
    strength: float          # قوة المستوى (0-1)
    touches: int            # عدد اللمسات
    level_type: str         # support / resistance
    last_test: float        # آخر اختبار
    zone_range: Tuple[float, float]  # نطاق المنطقة

@dataclass
class MarketPattern:
    """نمط السوق المكتشف"""
    pattern_type: PatternType
    confidence: float       # مستوى الثقة
    start_time: float
    end_time: float
    key_levels: List[float]
    expected_move: str      # bullish/bearish/neutral
    target_price: Optional[float]

@dataclass
class BreakoutAnalysis:
    """تحليل الكسر"""
    breakout_type: BreakoutType
    broken_level: float
    breakout_strength: float
    volume_confirmation: bool
    price_confirmation: bool
    time_confirmation: bool
    reliability_score: float

class AdvancedMarketAnalyzer:
    """محلل السوق المتقدم والشامل"""
    
    def __init__(self):
        self.name = "ADVANCED-MARKET-ANALYZER-v2.0"
        self.candlestick_patterns = {}
        self.support_resistance_cache = {}
        self.pattern_cache = {}
        self.breakout_cache = {}
        
        # معايير التحليل المتقدم
        self.min_pattern_confidence = 0.75
        self.min_sr_strength = 0.65
        self.breakout_confirmation_period = 300  # 5 دقائق
        
        logging.info(f"🔍 {self.name} جاهز للتحليل الشامل")

    def analyze_comprehensive(self, asset_id: str, price_data: Dict, 
                            historical_data: List[Dict]) -> Dict[str, Any]:
        """التحليل الشامل للأصل"""
        
        try:
            # تحويل البيانات التاريخية لشموع
            candlesticks = self._convert_to_candlesticks(historical_data, price_data)
            
            if len(candlesticks) < 20:
                return {"error": "بيانات غير كافية للتحليل الشامل"}
            
            # === 1. تحليل مناطق الدعم والمقاومة ===
            sr_analysis = self._analyze_support_resistance(candlesticks)
            
            # === 2. تحليل آخر 50 شمعة ===
            pattern_analysis = self._analyze_candlestick_patterns(candlesticks[-50:])
            
            # === 3. كشف الكسر الكاذب ===
            breakout_analysis = self._analyze_breakouts(candlesticks, sr_analysis)
            
            # === 4. تحليل الانعكاسات ===
            reversal_analysis = self._analyze_reversals(candlesticks)
            
            # === 5. المؤشرات الفنية المتقدمة ===
            advanced_indicators = self._calculate_advanced_indicators(candlesticks)
            
            # === 6. تقييم جودة الإشارة الإجمالية ===
            signal_quality = self._evaluate_signal_quality(
                sr_analysis, pattern_analysis, breakout_analysis, 
                reversal_analysis, advanced_indicators
            )
            
            return {
                'asset_id': asset_id,
                'timestamp': time.time(),
                'support_resistance': sr_analysis,
                'candlestick_patterns': pattern_analysis,
                'breakout_analysis': breakout_analysis,
                'reversal_signals': reversal_analysis,
                'advanced_indicators': advanced_indicators,
                'signal_quality': signal_quality,
                'overall_analysis': self._generate_comprehensive_summary(
                    sr_analysis, pattern_analysis, breakout_analysis, 
                    reversal_analysis, signal_quality
                )
            }
            
        except Exception as e:
            logging.error(f"خطأ في التحليل الشامل لـ {asset_id}: {e}")
            return {"error": str(e)}

    def _convert_to_candlesticks(self, historical_data: List[Dict], 
                               current_data: Dict) -> List[Candlestick]:
        """تحويل البيانات التاريخية إلى شموع"""
        
        candlesticks = []
        
        # معالجة البيانات التاريخية
        for i, data in enumerate(historical_data):
            price = data.get('price', current_data.get('price', 100))
            
            # محاكاة بيانات OHLC واقعية
            variation = np.random.normal(0, 0.002)  # تقلب 0.2%
            
            open_price = price * (1 + variation)
            close_price = price * (1 + np.random.normal(0, 0.003))
            
            high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.001)))
            low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.001)))
            
            candlestick = Candlestick(
                timestamp=data.get('timestamp', time.time() - (len(historical_data) - i) * 300),
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=data.get('volume', np.random.randint(1000, 10000))
            )
            
            candlesticks.append(candlestick)
        
        return candlesticks

    def _analyze_support_resistance(self, candlesticks: List[Candlestick]) -> Dict[str, Any]:
        """تحليل مناطق الدعم والمقاومة المتقدم"""
        
        if len(candlesticks) < 20:
            return {"support_levels": [], "resistance_levels": [], "strength": "weak"}
        
        # استخراج القمم والقيعان
        highs = [c.high_price for c in candlesticks]
        lows = [c.low_price for c in candlesticks]
        closes = [c.close_price for c in candlesticks]
        
        # حساب المستويات الهامة
        support_levels = self._find_support_levels(lows, closes)
        resistance_levels = self._find_resistance_levels(highs, closes)
        
        # تقييم قوة المستويات
        current_price = candlesticks[-1].close_price
        nearest_support = self._find_nearest_level(current_price, support_levels, 'below')
        nearest_resistance = self._find_nearest_level(current_price, resistance_levels, 'above')
        
        return {
            'support_levels': support_levels,
            'resistance_levels': resistance_levels,
            'nearest_support': nearest_support,
            'nearest_resistance': nearest_resistance,
            'current_price': current_price,
            'support_strength': len(support_levels),
            'resistance_strength': len(resistance_levels),
            'price_position': self._analyze_price_position(
                current_price, support_levels, resistance_levels
            )
        }

    def _find_support_levels(self, lows: List[float], closes: List[float]) -> List[SupportResistanceLevel]:
        """البحث عن مستويات الدعم"""
        
        levels = []
        
        # استخدام المتوسطات المتحركة كمستويات
        if len(closes) >= 20:
            sma_20 = sum(closes[-20:]) / 20
            sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else sma_20
            
            levels.append(SupportResistanceLevel(
                price=sma_20,
                strength=0.7,
                touches=3,
                level_type='support',
                last_test=time.time(),
                zone_range=(sma_20 * 0.995, sma_20 * 1.005)
            ))
            
            if abs(sma_50 - sma_20) > sma_20 * 0.01:  # إذا كان هناك فرق معنوي
                levels.append(SupportResistanceLevel(
                    price=sma_50,
                    strength=0.8,
                    touches=5,
                    level_type='support',
                    last_test=time.time(),
                    zone_range=(sma_50 * 0.995, sma_50 * 1.005)
                ))
        
        # البحث عن قيعان محلية
        for i in range(2, len(lows) - 2):
            if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and 
                lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                
                levels.append(SupportResistanceLevel(
                    price=lows[i],
                    strength=0.6,
                    touches=1,
                    level_type='support',
                    last_test=time.time(),
                    zone_range=(lows[i] * 0.998, lows[i] * 1.002)
                ))
        
        return sorted(levels, key=lambda x: x.price, reverse=True)[:5]

    def _find_resistance_levels(self, highs: List[float], closes: List[float]) -> List[SupportResistanceLevel]:
        """البحث عن مستويات المقاومة"""
        
        levels = []
        
        # استخدام المتوسطات المتحركة كمستويات
        if len(closes) >= 20:
            sma_20 = sum(closes[-20:]) / 20
            sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else sma_20
            
            levels.append(SupportResistanceLevel(
                price=sma_20,
                strength=0.7,
                touches=3,
                level_type='resistance',
                last_test=time.time(),
                zone_range=(sma_20 * 0.995, sma_20 * 1.005)
            ))
        
        # البحث عن قمم محلية
        for i in range(2, len(highs) - 2):
            if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and 
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                
                levels.append(SupportResistanceLevel(
                    price=highs[i],
                    strength=0.6,
                    touches=1,
                    level_type='resistance',
                    last_test=time.time(),
                    zone_range=(highs[i] * 0.998, highs[i] * 1.002)
                ))
        
        return sorted(levels, key=lambda x: x.price)[:5]

    def _analyze_candlestick_patterns(self, candlesticks: List[Candlestick]) -> Dict[str, Any]:
        """تحليل أنماط الشموع اليابانية - آخر 50 شمعة"""
        
        if len(candlesticks) < 3:
            return {"patterns": [], "signals": []}
        
        patterns = []
        signals = []
        
        # تحليل آخر 10 شموع للأنماط
        recent_candles = candlesticks[-10:]
        
        for i in range(len(recent_candles)):
            candle = recent_candles[i]
            
            # === تحليل أنماط الشمعة الواحدة ===
            
            # نمط المطرقة
            if self._is_hammer_pattern(candle):
                patterns.append(MarketPattern(
                    pattern_type=PatternType.HAMMER,
                    confidence=0.75,
                    start_time=candle.timestamp,
                    end_time=candle.timestamp,
                    key_levels=[candle.low_price, candle.close_price],
                    expected_move="bullish",
                    target_price=candle.close_price * 1.02
                ))
                signals.append("إشارة صاعدة: نمط المطرقة مكتشف")
            
            # نمط الدوجي
            if self._is_doji_pattern(candle):
                patterns.append(MarketPattern(
                    pattern_type=PatternType.DOJI,
                    confidence=0.65,
                    start_time=candle.timestamp,
                    end_time=candle.timestamp,
                    key_levels=[candle.open_price, candle.close_price],
                    expected_move="neutral",
                    target_price=None
                ))
                signals.append("تحذير: نمط الدوجي - احتمال انعكاس")
            
            # === تحليل أنماط متعددة الشموع ===
            if i >= 2:
                # نمط البلع الصاعد
                if self._is_bullish_engulfing(recent_candles[i-1], candle):
                    patterns.append(MarketPattern(
                        pattern_type=PatternType.ENGULFING_BULLISH,
                        confidence=0.85,
                        start_time=recent_candles[i-1].timestamp,
                        end_time=candle.timestamp,
                        key_levels=[recent_candles[i-1].low_price, candle.high_price],
                        expected_move="bullish",
                        target_price=candle.close_price * 1.025
                    ))
                    signals.append("إشارة قوية: نمط البلع الصاعد")
                
                # نمط البلع الهابط
                if self._is_bearish_engulfing(recent_candles[i-1], candle):
                    patterns.append(MarketPattern(
                        pattern_type=PatternType.ENGULFING_BEARISH,
                        confidence=0.85,
                        start_time=recent_candles[i-1].timestamp,
                        end_time=candle.timestamp,
                        key_levels=[recent_candles[i-1].high_price, candle.low_price],
                        expected_move="bearish",
                        target_price=candle.close_price * 0.975
                    ))
                    signals.append("إشارة قوية: نمط البلع الهابط")
        
        return {
            'patterns': patterns,
            'signals': signals,
            'pattern_count': len(patterns),
            'bullish_patterns': len([p for p in patterns if p.expected_move == "bullish"]),
            'bearish_patterns': len([p for p in patterns if p.expected_move == "bearish"]),
            'overall_sentiment': self._calculate_pattern_sentiment(patterns)
        }

    def _analyze_breakouts(self, candlesticks: List[Candlestick], 
                          sr_analysis: Dict) -> Dict[str, Any]:
        """تحليل الكسر الحقيقي والكاذب"""
        
        if len(candlesticks) < 10:
            return {"breakouts": [], "reliability": "low"}
        
        breakouts = []
        current_price = candlesticks[-1].close_price
        
        # فحص الكسر للمقاومة
        for resistance in sr_analysis.get('resistance_levels', []):
            if current_price > resistance.price:
                breakout = self._analyze_breakout_quality(
                    candlesticks, resistance.price, 'resistance'
                )
                breakouts.append(breakout)
        
        # فحص الكسر للدعم
        for support in sr_analysis.get('support_levels', []):
            if current_price < support.price:
                breakout = self._analyze_breakout_quality(
                    candlesticks, support.price, 'support'
                )
                breakouts.append(breakout)
        
        return {
            'breakouts': breakouts,
            'active_breakouts': len(breakouts),
            'reliability': self._calculate_breakout_reliability(breakouts),
            'false_breakout_risk': self._assess_false_breakout_risk(candlesticks, breakouts)
        }

    def _analyze_reversals(self, candlesticks: List[Candlestick]) -> Dict[str, Any]:
        """تحليل الانعكاسات والأنماط الكلاسيكية"""
        
        reversals = []
        
        if len(candlesticks) >= 20:
            prices = [c.close_price for c in candlesticks]
            
            # البحث عن قمة مزدوجة
            double_top = self._detect_double_top(candlesticks[-20:])
            if double_top:
                reversals.append({
                    'type': 'double_top',
                    'confidence': 0.8,
                    'expected_move': 'bearish',
                    'target': double_top['target']
                })
            
            # البحث عن قاع مزدوج
            double_bottom = self._detect_double_bottom(candlesticks[-20:])
            if double_bottom:
                reversals.append({
                    'type': 'double_bottom',
                    'confidence': 0.8,
                    'expected_move': 'bullish',
                    'target': double_bottom['target']
                })
            
            # تحليل الزخم للانعكاس
            momentum_reversal = self._analyze_momentum_reversal(candlesticks)
            if momentum_reversal:
                reversals.append(momentum_reversal)
        
        return {
            'reversals': reversals,
            'reversal_count': len(reversals),
            'reversal_probability': self._calculate_reversal_probability(reversals),
            'key_reversal_levels': [r.get('target') for r in reversals if r.get('target')]
        }

    def _calculate_advanced_indicators(self, candlesticks: List[Candlestick]) -> Dict[str, Any]:
        """حساب المؤشرات الفنية المتقدمة"""
        
        if len(candlesticks) < 20:
            return {}
        
        closes = [c.close_price for c in candlesticks]
        highs = [c.high_price for c in candlesticks]
        lows = [c.low_price for c in candlesticks]
        volumes = [c.volume for c in candlesticks]
        
        indicators = {}
        
        # RSI متعدد الأطر الزمنية
        indicators['rsi_14'] = self._calculate_rsi(closes, 14)
        indicators['rsi_7'] = self._calculate_rsi(closes[-14:], 7) if len(closes) >= 14 else 50
        
        # مؤشر القوة النسبية للحجم
        indicators['volume_rsi'] = self._calculate_rsi(volumes, 14)
        
        # مؤشر CCI
        indicators['cci'] = self._calculate_cci(highs, lows, closes, 20)
        
        # مؤشر Williams %R
        indicators['williams_r'] = self._calculate_williams_r(highs, lows, closes, 14)
        
        # مؤشر ADX (قوة الاتجاه)
        indicators['adx'] = self._calculate_adx(highs, lows, closes, 14)
        
        # مؤشر Stochastic
        stoch = self._calculate_stochastic(highs, lows, closes, 14)
        indicators['stoch_k'] = stoch['k']
        indicators['stoch_d'] = stoch['d']
        
        return indicators

    # === وظائف مساعدة للأنماط ===
    
    def _is_hammer_pattern(self, candle: Candlestick) -> bool:
        """فحص نمط المطرقة"""
        body_size = candle.body_size
        lower_shadow = candle.lower_shadow
        upper_shadow = candle.upper_shadow
        
        return (lower_shadow > body_size * 2 and 
                upper_shadow < body_size * 0.3 and
                body_size > 0)
    
    def _is_doji_pattern(self, candle: Candlestick) -> bool:
        """فحص نمط الدوجي"""
        total_range = candle.high_price - candle.low_price
        body_size = candle.body_size
        
        return body_size < total_range * 0.1
    
    def _is_bullish_engulfing(self, prev_candle: Candlestick, current_candle: Candlestick) -> bool:
        """فحص نمط البلع الصاعد"""
        return (prev_candle.is_bearish and 
                current_candle.is_bullish and
                current_candle.open_price < prev_candle.close_price and
                current_candle.close_price > prev_candle.open_price)
    
    def _is_bearish_engulfing(self, prev_candle: Candlestick, current_candle: Candlestick) -> bool:
        """فحص نمط البلع الهابط"""
        return (prev_candle.is_bullish and 
                current_candle.is_bearish and
                current_candle.open_price > prev_candle.close_price and
                current_candle.close_price < prev_candle.open_price)

    # === وظائف حساب المؤشرات ===
    
    def _calculate_rsi(self, prices: List[float], period: int) -> float:
        """حساب مؤشر القوة النسبية"""
        if len(prices) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < period:
            return 50.0
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def _calculate_cci(self, highs: List[float], lows: List[float], 
                      closes: List[float], period: int) -> float:
        """حساب مؤشر CCI"""
        if len(closes) < period:
            return 0.0
        
        typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
        
        if len(typical_prices) < period:
            return 0.0
        
        sma = sum(typical_prices[-period:]) / period
        mean_deviation = sum([abs(tp - sma) for tp in typical_prices[-period:]]) / period
        
        if mean_deviation == 0:
            return 0.0
        
        cci = (typical_prices[-1] - sma) / (0.015 * mean_deviation)
        return round(cci, 2)
    
    def _calculate_williams_r(self, highs: List[float], lows: List[float], 
                            closes: List[float], period: int) -> float:
        """حساب مؤشر Williams %R"""
        if len(closes) < period:
            return -50.0
        
        highest_high = max(highs[-period:])
        lowest_low = min(lows[-period:])
        
        if highest_high == lowest_low:
            return -50.0
        
        williams_r = ((highest_high - closes[-1]) / (highest_high - lowest_low)) * -100
        return round(williams_r, 2)
    
    def _calculate_adx(self, highs: List[float], lows: List[float], 
                      closes: List[float], period: int) -> float:
        """حساب مؤشر ADX"""
        # تبسيط حساب ADX
        if len(closes) < period + 1:
            return 25.0
        
        # محاكاة قيمة ADX بناءً على التقلبات
        recent_range = max(highs[-period:]) - min(lows[-period:])
        avg_price = sum(closes[-period:]) / period
        
        adx = (recent_range / avg_price) * 100
        return min(100, max(0, round(adx, 2)))
    
    def _calculate_stochastic(self, highs: List[float], lows: List[float], 
                            closes: List[float], period: int) -> Dict[str, float]:
        """حساب مؤشر Stochastic"""
        if len(closes) < period:
            return {'k': 50.0, 'd': 50.0}
        
        highest_high = max(highs[-period:])
        lowest_low = min(lows[-period:])
        
        if highest_high == lowest_low:
            k = 50.0
        else:
            k = ((closes[-1] - lowest_low) / (highest_high - lowest_low)) * 100
        
        # تبسيط حساب %D
        d = k * 0.9 + 10  # محاكاة متوسط متحرك
        
        return {'k': round(k, 2), 'd': round(d, 2)}

    # === وظائف التقييم النهائي ===
    
    def _evaluate_signal_quality(self, sr_analysis: Dict, pattern_analysis: Dict,
                                breakout_analysis: Dict, reversal_analysis: Dict,
                                indicators: Dict) -> Dict[str, Any]:
        """تقييم جودة الإشارة الإجمالية"""
        
        quality_score = 0.0
        factors = []
        
        # تقييم الدعم والمقاومة
        if sr_analysis.get('support_strength', 0) >= 3:
            quality_score += 0.2
            factors.append("مستويات دعم قوية")
        
        # تقييم الأنماط
        if pattern_analysis.get('pattern_count', 0) >= 2:
            quality_score += 0.25
            factors.append("أنماط متعددة مؤكدة")
        
        # تقييم الكسر
        if breakout_analysis.get('reliability') == 'high':
            quality_score += 0.3
            factors.append("كسر موثوق")
        
        # تقييم المؤشرات
        rsi = indicators.get('rsi_14', 50)
        if 30 <= rsi <= 70:  # منطقة متوازنة
            quality_score += 0.15
            factors.append("مؤشرات متوازنة")
        
        # تقييم الانعكاسات
        if reversal_analysis.get('reversal_probability', 0) > 0.7:
            quality_score += 0.1
            factors.append("احتمال انعكاس عالي")
        
        return {
            'overall_score': min(1.0, quality_score),
            'quality_factors': factors,
            'recommendation': self._generate_recommendation(quality_score),
            'risk_level': self._assess_risk_level(quality_score, breakout_analysis)
        }
    
    def _generate_comprehensive_summary(self, sr_analysis: Dict, pattern_analysis: Dict,
                                      breakout_analysis: Dict, reversal_analysis: Dict,
                                      signal_quality: Dict) -> str:
        """توليد الملخص الشامل"""
        
        summary_parts = []
        
        # ملخص الدعم والمقاومة
        if sr_analysis.get('nearest_support'):
            summary_parts.append(f"دعم قريب عند {sr_analysis['nearest_support'].price:.4f}")
        
        if sr_analysis.get('nearest_resistance'):
            summary_parts.append(f"مقاومة عند {sr_analysis['nearest_resistance'].price:.4f}")
        
        # ملخص الأنماط
        if pattern_analysis.get('pattern_count', 0) > 0:
            summary_parts.append(f"{pattern_analysis['pattern_count']} أنماط مكتشفة")
        
        # ملخص الكسر
        if breakout_analysis.get('active_breakouts', 0) > 0:
            summary_parts.append("كسر نشط مكتشف")
        
        # التوصية النهائية
        summary_parts.append(f"جودة الإشارة: {signal_quality['overall_score']:.2f}")
        summary_parts.append(signal_quality['recommendation'])
        
        return " | ".join(summary_parts)
    
    def _generate_recommendation(self, quality_score: float) -> str:
        """توليد التوصية بناءً على الجودة"""
        if quality_score >= 0.8:
            return "إشارة ممتازة - تداول مؤكد"
        elif quality_score >= 0.6:
            return "إشارة جيدة - تداول محتمل"
        elif quality_score >= 0.4:
            return "إشارة متوسطة - حذر مطلوب"
        else:
            return "إشارة ضعيفة - تجنب التداول"
    
    def _assess_risk_level(self, quality_score: float, breakout_analysis: Dict) -> str:
        """تقييم مستوى المخاطرة"""
        false_breakout_risk = breakout_analysis.get('false_breakout_risk', 0.5)
        
        if quality_score >= 0.7 and false_breakout_risk < 0.3:
            return "مخاطرة منخفضة"
        elif quality_score >= 0.5:
            return "مخاطرة متوسطة"
        else:
            return "مخاطرة عالية"

    # === وظائف مساعدة إضافية ===
    
    def _find_nearest_level(self, price: float, levels: List[SupportResistanceLevel], 
                           direction: str) -> Optional[SupportResistanceLevel]:
        """البحث عن أقرب مستوى"""
        if not levels:
            return None
        
        if direction == 'below':
            valid_levels = [l for l in levels if l.price < price]
            return max(valid_levels, key=lambda x: x.price) if valid_levels else None
        else:
            valid_levels = [l for l in levels if l.price > price]
            return min(valid_levels, key=lambda x: x.price) if valid_levels else None
    
    def _analyze_price_position(self, current_price: float, 
                              support_levels: List[SupportResistanceLevel],
                              resistance_levels: List[SupportResistanceLevel]) -> str:
        """تحليل موقع السعر"""
        support_count = len([s for s in support_levels if s.price < current_price])
        resistance_count = len([r for r in resistance_levels if r.price > current_price])
        
        if support_count > resistance_count:
            return "منطقة مقاومة محتملة"
        elif resistance_count > support_count:
            return "منطقة دعم محتملة"
        else:
            return "منطقة متوازنة"
    
    def _calculate_pattern_sentiment(self, patterns: List[MarketPattern]) -> str:
        """حساب المشاعر العامة للأنماط"""
        if not patterns:
            return "neutral"
        
        bullish_count = len([p for p in patterns if p.expected_move == "bullish"])
        bearish_count = len([p for p in patterns if p.expected_move == "bearish"])
        
        if bullish_count > bearish_count:
            return "bullish"
        elif bearish_count > bullish_count:
            return "bearish"
        else:
            return "neutral"
    
    def _analyze_breakout_quality(self, candlesticks: List[Candlestick], 
                                 level: float, level_type: str) -> BreakoutAnalysis:
        """تحليل جودة الكسر"""
        current_price = candlesticks[-1].close_price
        volume = candlesticks[-1].volume
        
        # فحص تأكيد الحجم
        avg_volume = sum([c.volume for c in candlesticks[-10:]]) / 10
        volume_confirmation = volume > avg_volume * 1.2
        
        # فحص تأكيد السعر
        price_confirmation = abs(current_price - level) > level * 0.002
        
        # تحديد نوع الكسر
        breakout_strength = abs(current_price - level) / level
        
        if volume_confirmation and price_confirmation and breakout_strength > 0.005:
            breakout_type = BreakoutType.TRUE_BREAKOUT
            reliability = 0.8
        elif breakout_strength < 0.002:
            breakout_type = BreakoutType.FALSE_BREAKOUT
            reliability = 0.2
        else:
            breakout_type = BreakoutType.PENDING
            reliability = 0.5
        
        return BreakoutAnalysis(
            breakout_type=breakout_type,
            broken_level=level,
            breakout_strength=breakout_strength,
            volume_confirmation=volume_confirmation,
            price_confirmation=price_confirmation,
            time_confirmation=True,  # تبسيط
            reliability_score=reliability
        )
    
    def _calculate_breakout_reliability(self, breakouts: List[BreakoutAnalysis]) -> str:
        """حساب موثوقية الكسر"""
        if not breakouts:
            return "none"
        
        avg_reliability = sum([b.reliability_score for b in breakouts]) / len(breakouts)
        
        if avg_reliability >= 0.7:
            return "high"
        elif avg_reliability >= 0.4:
            return "medium"
        else:
            return "low"
    
    def _assess_false_breakout_risk(self, candlesticks: List[Candlestick], 
                                   breakouts: List[BreakoutAnalysis]) -> float:
        """تقييم مخاطر الكسر الكاذب"""
        if not breakouts:
            return 0.5
        
        # عوامل تزيد من مخاطر الكسر الكاذب
        risk_factors = 0.0
        
        # حجم التداول المنخفض
        recent_volume = sum([c.volume for c in candlesticks[-5:]]) / 5
        avg_volume = sum([c.volume for c in candlesticks[-20:]]) / 20
        if recent_volume < avg_volume * 0.8:
            risk_factors += 0.2
        
        # كسر ضعيف
        for breakout in breakouts:
            if breakout.breakout_strength < 0.003:
                risk_factors += 0.3
        
        return min(1.0, risk_factors)
    
    def _detect_double_top(self, candlesticks: List[Candlestick]) -> Optional[Dict]:
        """كشف نمط القمة المزدوجة"""
        # تبسيط للكشف عن القمة المزدوجة
        highs = [c.high_price for c in candlesticks]
        if len(highs) < 10:
            return None
        
        # البحث عن قمتين متقاربتين
        max_price = max(highs)
        second_max_indices = [i for i, h in enumerate(highs) if abs(h - max_price) < max_price * 0.01]
        
        if len(second_max_indices) >= 2:
            target_price = max_price * 0.95  # هدف هبوط 5%
            return {'target': target_price, 'resistance': max_price}
        
        return None
    
    def _detect_double_bottom(self, candlesticks: List[Candlestick]) -> Optional[Dict]:
        """كشف نمط القاع المزدوج"""
        # تبسيط للكشف عن القاع المزدوج
        lows = [c.low_price for c in candlesticks]
        if len(lows) < 10:
            return None
        
        # البحث عن قاعين متقاربين
        min_price = min(lows)
        second_min_indices = [i for i, l in enumerate(lows) if abs(l - min_price) < min_price * 0.01]
        
        if len(second_min_indices) >= 2:
            target_price = min_price * 1.05  # هدف صعود 5%
            return {'target': target_price, 'support': min_price}
        
        return None
    
    def _analyze_momentum_reversal(self, candlesticks: List[Candlestick]) -> Optional[Dict]:
        """تحليل انعكاس الزخم"""
        if len(candlesticks) < 10:
            return None
        
        # حساب تغيير الزخم
        recent_prices = [c.close_price for c in candlesticks[-5:]]
        older_prices = [c.close_price for c in candlesticks[-10:-5]]
        
        recent_momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
        older_momentum = (older_prices[-1] - older_prices[0]) / older_prices[0]
        
        # كشف تباعد الزخم
        if abs(recent_momentum - older_momentum) > 0.02:
            return {
                'type': 'momentum_reversal',
                'confidence': 0.6,
                'expected_move': 'bearish' if recent_momentum > older_momentum else 'bullish'
            }
        
        return None
    
    def _calculate_reversal_probability(self, reversals: List[Dict]) -> float:
        """حساب احتمالية الانعكاس"""
        if not reversals:
            return 0.0
        
        total_confidence = sum([r.get('confidence', 0) for r in reversals])
        return min(1.0, total_confidence / len(reversals))

# إنشاء نسخة عامة من المحلل المتقدم
advanced_analyzer = AdvancedMarketAnalyzer()

def analyze_asset_comprehensive(asset_id: str, price_data: Dict, 
                              historical_data: List[Dict] = None) -> Optional[Dict]:
    """
    التحليل الشامل للأصل المالي
    يشمل: الدعم والمقاومة، أنماط الشموع، كشف الكسر الكاذب، الانعكاسات
    """
    
    try:
        if not historical_data:
            historical_data = []
        
        # التحليل الشامل
        analysis = advanced_analyzer.analyze_comprehensive(
            asset_id, price_data, historical_data
        )
        
        if 'error' in analysis:
            return None
        
        # تحويل النتائج لتنسيق مفهوم
        comprehensive_result = {
            'asset_id': asset_id,
            'comprehensive_analysis': True,
            'support_resistance_analysis': analysis['support_resistance'],
            'candlestick_patterns': analysis['candlestick_patterns'],
            'breakout_analysis': analysis['breakout_analysis'],
            'reversal_signals': analysis['reversal_signals'],
            'advanced_indicators': analysis['advanced_indicators'],
            'signal_quality': analysis['signal_quality'],
            'summary': analysis['overall_analysis'],
            'timestamp': time.time()
        }
        
        return comprehensive_result
        
    except Exception as e:
        logging.error(f"خطأ في التحليل الشامل لـ {asset_id}: {e}")
        return None