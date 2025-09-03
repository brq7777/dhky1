"""
نظام تتبع الصفقات الحقيقية - بناءً على الإشارات الفعلية وحركة الأسعار الحقيقية
"""
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import threading

class RealTradesTracker:
    def __init__(self):
        """تهيئة متتبع الصفقات الحقيقية"""
        self.active_trades = {}  # الصفقات النشطة الحقيقية
        self.completed_trades = []  # الصفقات المكتملة
        self.current_prices = {}  # الأسعار الحالية للمتابعة
        
        # إحصائيات حقيقية
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.total_confidence = 0
        
        # خيارات التقييم
        self.evaluation_period = 300  # 5 دقائق لتقييم الصفقة
        
    def update_current_prices(self, prices_data):
        """تحديث الأسعار الحالية للمتابعة"""
        if prices_data:
            for asset_id, price_info in prices_data.items():
                if isinstance(price_info, dict) and 'price' in price_info:
                    self.current_prices[asset_id] = {
                        'price': price_info['price'],
                        'timestamp': time.time()
                    }
    
    def track_real_signal(self, signal_data):
        """تتبع إشارة حقيقية من النظام"""
        trade_id = signal_data.get('trade_id', f"trade_{int(time.time())}")
        
        # تسجيل الصفقة الجديدة
        self.active_trades[trade_id] = {
            'trade_id': trade_id,
            'asset_id': signal_data['asset_id'],
            'asset_name': signal_data['asset_name'],
            'signal_type': signal_data['type'],
            'entry_price': signal_data['price'],
            'entry_time': datetime.utcnow(),
            'confidence': signal_data['confidence'],
            'rsi': signal_data.get('rsi', 50),
            'trend': signal_data.get('trend', 'unknown'),
            'reason': signal_data.get('reason', ''),
            'volatility': signal_data.get('volatility', 0),
            'is_evaluated': False
        }
        
        # برمجة تقييم الصفقة بعد 5 دقائق
        timer = threading.Timer(self.evaluation_period, self.evaluate_real_trade, args=[trade_id])
        timer.start()
        
        logging.info(f"تم تتبع إشارة حقيقية: {signal_data['asset_id']} - {signal_data['type']} - ID: {trade_id}")
        return trade_id
    
    def evaluate_real_trade(self, trade_id):
        """تقييم الصفقة بناءً على الأسعار الحقيقية"""
        if trade_id not in self.active_trades:
            return
        
        trade = self.active_trades[trade_id]
        
        if trade['is_evaluated']:
            return
        
        asset_id = trade['asset_id']
        
        # الحصول على السعر الحالي
        current_price_info = self.current_prices.get(asset_id)
        
        if not current_price_info:
            # إذا لم نحصل على سعر حالي، نؤجل التقييم
            timer = threading.Timer(30, self.evaluate_real_trade, args=[trade_id])
            timer.start()
            return
        
        current_price = current_price_info['price']
        entry_price = trade['entry_price']
        signal_type = trade['signal_type']
        
        # حساب التغيير في السعر
        price_change_percentage = ((current_price - entry_price) / entry_price) * 100
        
        # تحديد نتيجة الصفقة بناءً على نوع الإشارة
        is_winning = False
        actual_profit = 0.0
        
        if signal_type == 'BUY':
            # للشراء: ربح إذا ارتفع السعر
            actual_profit = price_change_percentage
            is_winning = price_change_percentage > 0.1  # ربح أكثر من 0.1%
        else:  # SELL
            # للبيع: ربح إذا انخفض السعر
            actual_profit = -price_change_percentage
            is_winning = price_change_percentage < -0.1  # انخفاض أكثر من 0.1%
        
        # تحليل سبب النجاح أو الفشل
        analysis = self.analyze_trade_result(trade, current_price, is_winning, actual_profit)
        
        # تسجيل النتيجة
        completed_trade = {
            **trade,
            'exit_price': current_price,
            'exit_time': datetime.utcnow(),
            'duration': self.evaluation_period,
            'result': 'winning' if is_winning else 'losing',
            'actual_profit': round(actual_profit, 3),
            'price_change': round(price_change_percentage, 3),
            'analysis': analysis,
            'is_real': True
        }
        
        self.completed_trades.append(completed_trade)
        
        # تحديث الإحصائيات
        if is_winning:
            self.winning_trades += 1
            self.total_profit += actual_profit
        else:
            self.losing_trades += 1
            self.total_profit += actual_profit
        
        self.total_confidence += trade['confidence']
        
        # تحديد أن الصفقة تم تقييمها
        trade['is_evaluated'] = True
        
        # إزالة من الصفقات النشطة بعد فترة
        threading.Timer(60, lambda: self.active_trades.pop(trade_id, None)).start()
        
        result_text = 'نجحت' if is_winning else 'فشلت'
        logging.info(f"تقييم الصفقة الحقيقية {trade_id}: {result_text} بربح حقيقي {actual_profit:.3f}%")
    
    def analyze_trade_result(self, trade, current_price, is_winning, profit):
        """تحليل سبب نجاح أو فشل الصفقة"""
        confidence = trade['confidence']
        trend = trade['trend']
        signal_type = trade['signal_type']
        rsi = trade['rsi']
        
        if is_winning:
            reasons = []
            
            if confidence >= 90:
                reasons.append("مستوى ثقة عالي جداً")
            elif confidence >= 80:
                reasons.append("مستوى ثقة جيد")
            
            if (signal_type == 'BUY' and trend == 'uptrend') or \
               (signal_type == 'SELL' and trend == 'downtrend'):
                reasons.append("الاتجاه العام ساند الإشارة")
            
            if signal_type == 'BUY' and rsi < 40:
                reasons.append("RSI منخفض دعم إشارة الشراء")
            elif signal_type == 'SELL' and rsi > 60:
                reasons.append("RSI مرتفع دعم إشارة البيع")
            
            if profit > 1.0:
                reasons.append("حققت الصفقة ربحاً ممتازاً")
            elif profit > 0.5:
                reasons.append("حققت الصفقة ربحاً جيداً")
            
            analysis = f"✅ نجحت الصفقة: " + " + ".join(reasons[:3])
            
        else:
            reasons = []
            
            if confidence < 75:
                reasons.append("مستوى ثقة منخفض")
            
            if (signal_type == 'BUY' and trend == 'downtrend') or \
               (signal_type == 'SELL' and trend == 'uptrend'):
                reasons.append("الاتجاه العام ضد الإشارة")
            elif trend == 'sideways':
                reasons.append("السوق في حالة تذبذب جانبي")
            
            if abs(profit) > 1.0:
                reasons.append("تقلبات سوق قوية ضد الإشارة")
            else:
                reasons.append("تحرك سعري محدود")
            
            analysis = f"❌ فشلت الصفقة: " + " + ".join(reasons[:3])
        
        return analysis
    
    def get_real_statistics(self, days=30):
        """الحصول على إحصائيات الصفقات الحقيقية"""
        total_trades = len(self.completed_trades)
        
        if total_trades == 0:
            return {
                'winning_trades': 0,
                'losing_trades': 0,
                'success_rate': 0,
                'loss_rate': 0,
                'avg_profit': 0,
                'avg_confidence': 0,
                'total_trades': 0,
                'data_source': 'real_market_data'
            }
        
        success_rate = (self.winning_trades / total_trades) * 100
        loss_rate = (self.losing_trades / total_trades) * 100
        avg_profit = self.total_profit / total_trades if total_trades > 0 else 0
        avg_confidence = self.total_confidence / total_trades if total_trades > 0 else 0
        
        return {
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'success_rate': round(success_rate, 1),
            'loss_rate': round(loss_rate, 1),
            'avg_profit': round(avg_profit, 3),
            'avg_confidence': round(avg_confidence, 1),
            'total_trades': total_trades,
            'data_source': 'real_market_data'
        }
    
    def generate_real_recommendations(self):
        """توليد توصيات بناءً على البيانات الحقيقية"""
        total_trades = len(self.completed_trades)
        
        if total_trades == 0:
            return {
                'learning_insights': [
                    "النظام يجمع بيانات حقيقية من الصفقات الفعلية",
                    "ستظهر الإحصائيات بعد تقييم الإشارات الأولى (5 دقائق لكل إشارة)"
                ],
                'improvement_suggestions': [
                    "انتظر تقييم الإشارات الحالية للحصول على توصيات دقيقة",
                    "النظام يحلل الأسعار الحقيقية من السوق للحصول على نتائج موثوقة"
                ]
            }
        
        # تحليل الأنماط الحقيقية
        winning_trades = [t for t in self.completed_trades if t['result'] == 'winning']
        losing_trades = [t for t in self.completed_trades if t['result'] == 'losing']
        
        insights = []
        suggestions = []
        
        # تحليل معدل النجاح الحقيقي
        success_rate = (len(winning_trades) / total_trades) * 100
        
        insights.append(f"📊 معدل النجاح الحقيقي: {success_rate:.1f}% من {total_trades} صفقة")
        
        if success_rate > 65:
            insights.append("🎯 أداء ممتاز في التحليل الفني")
            suggestions.append("استمر بنفس الاستراتيجية - النتائج إيجابية")
        elif success_rate > 50:
            insights.append("📈 أداء جيد مع إمكانية للتحسين")
            suggestions.append("راجع الإشارات منخفضة الثقة لتحسين الدقة")
        else:
            insights.append("⚠️ يحتاج النظام لمراجعة المعايير")
            suggestions.append("ركز على الإشارات عالية الثقة فقط (>85%)")
        
        # تحليل الربحية الحقيقية
        if winning_trades:
            avg_winning_profit = sum(t['actual_profit'] for t in winning_trades) / len(winning_trades)
            avg_losing_loss = sum(t['actual_profit'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
            
            insights.append(f"💰 متوسط الربح الحقيقي: {avg_winning_profit:.2f}%")
            
            if avg_winning_profit > abs(avg_losing_loss):
                suggestions.append("نسبة المخاطر/العائد إيجابية - استمر")
            else:
                suggestions.append("اضبط نقاط وقف الخسارة لتحسين النسبة")
        
        # تحليل الأصول الأفضل أداءً
        asset_performance = {}
        for trade in self.completed_trades:
            asset = trade['asset_id']
            if asset not in asset_performance:
                asset_performance[asset] = {'wins': 0, 'losses': 0, 'profits': []}
            
            asset_performance[asset]['profits'].append(trade['actual_profit'])
            if trade['result'] == 'winning':
                asset_performance[asset]['wins'] += 1
            else:
                asset_performance[asset]['losses'] += 1
        
        best_assets = []
        for asset, perf in asset_performance.items():
            total_asset_trades = perf['wins'] + perf['losses']
            if total_asset_trades >= 2:
                asset_success_rate = (perf['wins'] / total_asset_trades) * 100
                avg_profit = sum(perf['profits']) / len(perf['profits'])
                
                if asset_success_rate >= 70 and avg_profit > 0:
                    best_assets.append(f"{asset} ({asset_success_rate:.0f}%)")
        
        if best_assets:
            suggestions.append(f"🏆 أفضل أداء على: {', '.join(best_assets[:2])}")
        
        return {
            'learning_insights': insights[:4],
            'improvement_suggestions': suggestions[:4]
        }

# إنشاء مثيل عالمي للتتبع الحقيقي
real_trades_tracker = RealTradesTracker()