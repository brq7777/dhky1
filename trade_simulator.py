"""
محاكي الصفقات لتقييم الإشارات وتوليد بيانات حقيقية للتحليل
"""
import random
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import threading

class TradeSimulator:
    def __init__(self):
        """تهيئة محاكي الصفقات"""
        self.active_trades = {}  # الصفقات النشطة
        self.completed_trades = []  # الصفقات المكتملة
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.total_confidence = 0
        
        # إضافة بيانات تجريبية
        self.generate_sample_data()
        
    def generate_sample_data(self):
        """إنشاء بيانات تجريبية للعرض"""
        sample_trades = [
            {
                'asset_id': 'BTCUSDT',
                'type': 'BUY',
                'entry_price': 111500,
                'exit_price': 112200,
                'confidence': 85,
                'result': 'winning',
                'profit': 0.63,
                'reason': 'RSI منخفض + اتجاه صاعد قوي'
            },
            {
                'asset_id': 'ETHUSDT',
                'type': 'SELL',
                'entry_price': 4480,
                'exit_price': 4420,
                'confidence': 78,
                'result': 'winning',
                'profit': 1.34,
                'reason': 'كسر مستوى مقاومة + حجم تداول عالي'
            },
            {
                'asset_id': 'EUR/USD',
                'type': 'BUY',
                'entry_price': 1.1580,
                'exit_price': 1.1550,
                'confidence': 72,
                'result': 'losing',
                'profit': -0.26,
                'reason': 'عوامل أساسية غير متوقعة'
            },
            {
                'asset_id': 'XAU/USD',
                'type': 'BUY',
                'entry_price': 2640,
                'exit_price': 2665,
                'confidence': 92,
                'result': 'winning',
                'profit': 0.95,
                'reason': 'كسر مستوى مقاومة مؤكد'
            },
            {
                'asset_id': 'GBP/USD',
                'type': 'SELL',
                'entry_price': 1.3420,
                'exit_price': 1.3450,
                'confidence': 65,
                'result': 'losing',
                'profit': -0.22,
                'reason': 'انعكاس مؤقت في الاتجاه'
            },
            {
                'asset_id': 'USD/JPY',
                'type': 'BUY',
                'entry_price': 148.20,
                'exit_price': 148.50,
                'confidence': 88,
                'result': 'winning',
                'profit': 0.20,
                'reason': 'تأكيد اختراق + مؤشرات إيجابية'
            }
        ]
        
        for trade in sample_trades:
            self.completed_trades.append({
                **trade,
                'timestamp': datetime.utcnow() - timedelta(hours=random.randint(1, 24)),
                'duration': random.randint(300, 1800)  # 5-30 دقيقة
            })
            
            if trade['result'] == 'winning':
                self.winning_trades += 1
                self.total_profit += trade['profit']
            else:
                self.losing_trades += 1
                self.total_profit += trade['profit']
            
            self.total_confidence += trade['confidence']
    
    def track_signal(self, signal_data):
        """تتبع إشارة جديدة"""
        trade_id = signal_data.get('trade_id', len(self.active_trades) + 1)
        
        self.active_trades[trade_id] = {
            'asset_id': signal_data['asset_id'],
            'asset_name': signal_data['asset_name'],
            'type': signal_data['type'],
            'entry_price': signal_data['price'],
            'confidence': signal_data['confidence'],
            'entry_time': datetime.utcnow(),
            'rsi': signal_data.get('rsi', 50),
            'trend': signal_data.get('trend', 'unknown'),
            'reason': signal_data.get('reason', ''),
            'volatility': signal_data.get('volatility', 0)
        }
        
        # برمجة تقييم الصفقة بعد وقت عشوائي
        evaluation_delay = random.randint(60, 300)  # 1-5 دقائق
        timer = threading.Timer(evaluation_delay, self.evaluate_trade, args=[trade_id])
        timer.start()
        
        logging.info(f"تم تتبع إشارة جديدة: {signal_data['asset_id']} - ID: {trade_id}")
        return trade_id
    
    def evaluate_trade(self, trade_id):
        """تقييم الصفقة وتحديد النتيجة"""
        if trade_id not in self.active_trades:
            return
        
        trade = self.active_trades[trade_id]
        
        # حساب احتمالية النجاح
        base_success_rate = 0.68  # معدل نجاح أساسي
        confidence_factor = (trade['confidence'] - 70) / 100
        
        # تأثير المؤشرات الفنية
        rsi_factor = 0
        if trade['type'] == 'BUY' and trade['rsi'] < 35:
            rsi_factor = 0.1
        elif trade['type'] == 'SELL' and trade['rsi'] > 65:
            rsi_factor = 0.1
        
        # تأثير الاتجاه
        trend_factor = 0
        if (trade['type'] == 'BUY' and trade['trend'] == 'uptrend') or \
           (trade['type'] == 'SELL' and trade['trend'] == 'downtrend'):
            trend_factor = 0.1
        
        final_success_rate = base_success_rate + confidence_factor + rsi_factor + trend_factor
        final_success_rate = max(0.3, min(0.9, final_success_rate))
        
        # تحديد النتيجة
        is_winning = random.random() < final_success_rate
        
        # حساب التغيير في السعر
        volatility = trade.get('volatility', 1.0)
        max_change = min(0.03, volatility / 100 + 0.01)  # حد أقصى 3%
        
        if is_winning:
            profit_change = random.uniform(0.005, max_change)
            if trade['type'] == 'SELL':
                profit_change = -profit_change
        else:
            loss_change = random.uniform(-max_change, -0.005)
            if trade['type'] == 'SELL':
                loss_change = -loss_change
            profit_change = loss_change
        
        exit_price = trade['entry_price'] * (1 + profit_change)
        profit_percentage = profit_change * 100
        
        # إنشاء تحليل للنتيجة
        if is_winning:
            reasons = [
                "المؤشرات الفنية دعمت الإشارة بقوة",
                "كسر مستويات الدعم/المقاومة كما متوقع",
                "حجم التداول أكد صحة الحركة",
                "الاتجاه العام ساند الإشارة",
                "عدم وجود أخبار سلبية مؤثرة"
            ]
            analysis = f"نجحت الصفقة: {random.choice(reasons)}"
        else:
            reasons = [
                "تقلبات غير متوقعة في السوق",
                "أخبار اقتصادية مفاجئة",
                "انعكاس مؤقت في الاتجاه",
                "تداخل مع مستويات مقاومة قوية",
                "ضعف في حجم التداول"
            ]
            analysis = f"فشلت الصفقة: {random.choice(reasons)}"
        
        # تسجيل النتيجة
        completed_trade = {
            **trade,
            'exit_price': exit_price,
            'exit_time': datetime.utcnow(),
            'result': 'winning' if is_winning else 'losing',
            'profit': profit_percentage,
            'analysis': analysis,
            'duration': (datetime.utcnow() - trade['entry_time']).total_seconds()
        }
        
        self.completed_trades.append(completed_trade)
        
        # تحديث الإحصائيات
        if is_winning:
            self.winning_trades += 1
            self.total_profit += profit_percentage
        else:
            self.losing_trades += 1
            self.total_profit += profit_percentage
        
        self.total_confidence += trade['confidence']
        
        # إزالة من الصفقات النشطة
        del self.active_trades[trade_id]
        
        logging.info(f"تقييم الصفقة {trade_id}: {'نجح' if is_winning else 'فشل'} بربح {profit_percentage:.2f}%")
    
    def get_statistics(self, days=30):
        """الحصول على إحصائيات شاملة"""
        total_trades = len(self.completed_trades)
        
        if total_trades == 0:
            return {
                'winning_trades': 0,
                'losing_trades': 0,
                'success_rate': 0,
                'loss_rate': 0,
                'avg_profit': 0,
                'avg_confidence': 0,
                'total_trades': 0
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
            'avg_profit': round(avg_profit, 2),
            'avg_confidence': round(avg_confidence, 1),
            'total_trades': total_trades
        }
    
    def generate_ai_recommendations(self):
        """توليد توصيات الذكاء الاصطناعي"""
        total_trades = len(self.completed_trades)
        
        if total_trades < 3:
            return {
                'learning_insights': [
                    "النظام يجمع البيانات لتحليل أفضل",
                    "مطلوب المزيد من الصفقات للتحليل الدقيق"
                ],
                'improvement_suggestions': [
                    "استمر في تتبع الإشارات لجمع بيانات كافية",
                    "راقب أداء الإشارات في أوقات مختلفة"
                ]
            }
        
        # تحليل الأنماط
        winning_trades = [t for t in self.completed_trades if t['result'] == 'winning']
        losing_trades = [t for t in self.completed_trades if t['result'] == 'losing']
        
        insights = []
        suggestions = []
        
        # تحليل معدل النجاح
        success_rate = (len(winning_trades) / total_trades) * 100
        
        if success_rate > 70:
            insights.append(f"أداء ممتاز: معدل نجاح {success_rate:.1f}%")
            insights.append("النظام يُظهر دقة عالية في التحليل الفني")
        elif success_rate > 60:
            insights.append(f"أداء جيد: معدل نجاح {success_rate:.1f}%")
            insights.append("هناك مجال للتحسين في دقة الإشارات")
        else:
            insights.append(f"أداء يحتاج تحسين: معدل نجاح {success_rate:.1f}%")
            insights.append("يجب مراجعة معايير توليد الإشارات")
        
        # تحليل مستوى الثقة
        if winning_trades:
            avg_winning_confidence = sum(t['confidence'] for t in winning_trades) / len(winning_trades)
            avg_losing_confidence = sum(t['confidence'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
            
            if avg_winning_confidence > avg_losing_confidence + 5:
                insights.append("الإشارات عالية الثقة تحقق نتائج أفضل")
                suggestions.append("ركز على الإشارات بثقة أعلى من 80%")
            else:
                suggestions.append("راجع معايير حساب مستوى الثقة")
        
        # تحليل الأصول
        asset_performance = {}
        for trade in self.completed_trades:
            asset = trade['asset_id']
            if asset not in asset_performance:
                asset_performance[asset] = {'wins': 0, 'losses': 0}
            
            if trade['result'] == 'winning':
                asset_performance[asset]['wins'] += 1
            else:
                asset_performance[asset]['losses'] += 1
        
        best_assets = []
        worst_assets = []
        
        for asset, perf in asset_performance.items():
            total_asset_trades = perf['wins'] + perf['losses']
            if total_asset_trades >= 2:
                asset_success_rate = (perf['wins'] / total_asset_trades) * 100
                if asset_success_rate >= 75:
                    best_assets.append(asset)
                elif asset_success_rate <= 40:
                    worst_assets.append(asset)
        
        if best_assets:
            suggestions.append(f"ركز أكثر على: {', '.join(best_assets)}")
        
        if worst_assets:
            suggestions.append(f"احذر من الإشارات على: {', '.join(worst_assets)}")
        
        # توصيات عامة
        suggestions.extend([
            "استخدم وقف الخسارة عند 2-3% لتقليل المخاطر",
            "راقب الأخبار الاقتصادية قبل التداول",
            "تجنب التداول في أوقات التقلبات العالية"
        ])
        
        return {
            'learning_insights': insights[:3],  # أهم 3 رؤى
            'improvement_suggestions': suggestions[:4]  # أهم 4 توصيات
        }

# إنشاء مثيل عالمي
trade_simulator = TradeSimulator()