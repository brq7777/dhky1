"""
نظام تتبع الصفقات الخاسرة والتعلم من الأخطاء
تتبع جميع الإشارات الخاطئة وتحليل أسباب الفشل لتحسين الذكاء الاصطناعي
"""
import sqlite3
import time
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import statistics
import numpy as np

class LosingTradesTracker:
    def __init__(self, db_path='losing_trades.db'):
        """تهيئة متتبع الصفقات الخاسرة"""
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """إنشاء قاعدة البيانات وجداول التتبع"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # جدول الصفقات الخاسرة
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS losing_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_id TEXT NOT NULL,
                asset_name TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                signal_price REAL NOT NULL,
                entry_time REAL NOT NULL,
                exit_time REAL DEFAULT NULL,
                exit_price REAL DEFAULT NULL,
                loss_amount REAL DEFAULT NULL,
                loss_percentage REAL DEFAULT NULL,
                confidence INTEGER NOT NULL,
                
                -- مؤشرات فنية وقت الإشارة
                rsi REAL,
                sma_short REAL,
                sma_long REAL,
                price_change_5 REAL,
                trend TEXT,
                volatility REAL,
                
                -- تحليل أسباب الفشل
                failure_reason TEXT,
                market_condition TEXT,
                false_breakout BOOLEAN DEFAULT 0,
                whipsaw BOOLEAN DEFAULT 0,
                news_impact BOOLEAN DEFAULT 0,
                low_volume BOOLEAN DEFAULT 0,
                
                -- معلومات إضافية
                session_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول تحليل أنماط الفشل
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS failure_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_name TEXT UNIQUE NOT NULL,
                pattern_description TEXT,
                occurrence_count INTEGER DEFAULT 0,
                average_loss REAL DEFAULT 0,
                last_occurrence TIMESTAMP,
                pattern_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول إحصائيات التحسن
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_improvement_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                total_signals INTEGER DEFAULT 0,
                losing_signals INTEGER DEFAULT 0,
                loss_rate REAL DEFAULT 0,
                average_loss REAL DEFAULT 0,
                improvement_score REAL DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def track_signal(self, signal_data: Dict[str, Any], session_id: str = None) -> int:
        """تتبع إشارة جديدة"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO losing_trades (
                asset_id, asset_name, signal_type, signal_price, entry_time,
                confidence, rsi, sma_short, sma_long, price_change_5,
                trend, volatility, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal_data.get('asset_id'),
            signal_data.get('asset_name'),
            signal_data.get('type'),
            signal_data.get('price'),
            signal_data.get('timestamp', time.time()),
            signal_data.get('confidence'),
            signal_data.get('rsi'),
            signal_data.get('sma_short'),
            signal_data.get('sma_long'),
            signal_data.get('price_change_5'),
            signal_data.get('trend'),
            signal_data.get('volatility'),
            session_id or f"session_{int(time.time())}"
        ))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logging.info(f"تتبع إشارة جديدة: {signal_data.get('asset_id')} - ID: {trade_id}")
        return trade_id
    
    def mark_as_losing_trade(self, trade_id: int, exit_price: float, 
                           failure_analysis: Dict[str, Any] = None):
        """تحديد الصفقة كخاسرة مع تحليل أسباب الفشل"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # جلب بيانات الصفقة
        cursor.execute('''
            SELECT signal_price, signal_type FROM losing_trades WHERE id = ?
        ''', (trade_id,))
        
        result = cursor.fetchone()
        if not result:
            logging.warning(f"لم يتم العثور على الصفقة: {trade_id}")
            conn.close()
            return
            
        signal_price, signal_type = result
        
        # حساب الخسارة
        if signal_type == 'BUY':
            loss_amount = signal_price - exit_price
            loss_percentage = (loss_amount / signal_price) * 100
        else:  # SELL
            loss_amount = exit_price - signal_price
            loss_percentage = (loss_amount / signal_price) * 100
        
        # تحليل أسباب الفشل
        if failure_analysis is None:
            failure_analysis = self._analyze_failure_reason(trade_id, signal_type, 
                                                           signal_price, exit_price)
        
        # تحديث الصفقة
        cursor.execute('''
            UPDATE losing_trades SET
                exit_time = ?, exit_price = ?, loss_amount = ?, loss_percentage = ?,
                failure_reason = ?, market_condition = ?, false_breakout = ?,
                whipsaw = ?, news_impact = ?, low_volume = ?
            WHERE id = ?
        ''', (
            time.time(), exit_price, loss_amount, loss_percentage,
            failure_analysis.get('reason', 'غير محدد'),
            failure_analysis.get('market_condition', 'غير واضح'),
            failure_analysis.get('false_breakout', False),
            failure_analysis.get('whipsaw', False),
            failure_analysis.get('news_impact', False),
            failure_analysis.get('low_volume', False),
            trade_id
        ))
        
        conn.commit()
        conn.close()
        
        # تحديث أنماط الفشل
        self._update_failure_patterns(failure_analysis)
        
        logging.info(f"تم تحديد الصفقة {trade_id} كخاسرة: خسارة {loss_percentage:.2f}%")
        
    def _analyze_failure_reason(self, trade_id: int, signal_type: str, 
                               signal_price: float, exit_price: float) -> Dict[str, Any]:
        """تحليل ذكي لأسباب فشل الصفقة"""
        loss_percentage = abs(((exit_price - signal_price) / signal_price) * 100)
        
        analysis = {
            'reason': 'فشل في التحليل الفني',
            'market_condition': 'متقلب',
            'false_breakout': False,
            'whipsaw': False,
            'news_impact': False,
            'low_volume': False
        }
        
        # تحليل نوع الفشل حسب نسبة الخسارة
        if loss_percentage < 0.5:
            analysis['reason'] = 'تذبذب طبيعي - خسارة صغيرة'
            analysis['whipsaw'] = True
        elif loss_percentage < 1.5:
            analysis['reason'] = 'كسر كاذب للمقاومة/الدعم'
            analysis['false_breakout'] = True
        elif loss_percentage < 3.0:
            analysis['reason'] = 'تغير مفاجئ في اتجاه السوق'
            analysis['market_condition'] = 'متقلب بشدة'
        else:
            analysis['reason'] = 'أخبار مؤثرة أو حدث غير متوقع'
            analysis['news_impact'] = True
            
        return analysis
    
    def _update_failure_patterns(self, failure_analysis: Dict[str, Any]):
        """تحديث أنماط الفشل المتكررة"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        pattern_name = failure_analysis.get('reason', 'غير محدد')
        
        cursor.execute('''
            INSERT OR REPLACE INTO failure_patterns 
            (pattern_name, pattern_description, occurrence_count, last_occurrence, pattern_data)
            VALUES (?, ?, 
                COALESCE((SELECT occurrence_count FROM failure_patterns WHERE pattern_name = ?), 0) + 1,
                CURRENT_TIMESTAMP, ?)
        ''', (
            pattern_name,
            f"نمط فشل: {pattern_name}",
            pattern_name,
            json.dumps(failure_analysis)
        ))
        
        conn.commit()
        conn.close()
    
    def get_losing_trades_stats(self, days: int = 30) -> Dict[str, Any]:
        """إحصائيات الصفقات الخاسرة"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # الصفقات الخاسرة في الفترة المحددة
        since_timestamp = time.time() - (days * 24 * 3600)
        
        cursor.execute('''
            SELECT * FROM losing_trades 
            WHERE exit_time IS NOT NULL AND entry_time > ?
            ORDER BY entry_time DESC
        ''', (since_timestamp,))
        
        losing_trades = cursor.fetchall()
        
        if not losing_trades:
            conn.close()
            return {
                'total_losing_trades': 0,
                'average_loss': 0,
                'most_common_failure': 'لا توجد بيانات',
                'improvement_needed': []
            }
        
        # تحليل البيانات
        loss_percentages = [trade[9] for trade in losing_trades if trade[9]]  # loss_percentage
        failure_reasons = [trade[15] for trade in losing_trades if trade[15]]  # failure_reason
        
        # أكثر أسباب الفشل شيوعاً
        failure_counts = {}
        for reason in failure_reasons:
            failure_counts[reason] = failure_counts.get(reason, 0) + 1
        
        most_common_failure = max(failure_counts.items(), key=lambda x: x[1]) if failure_counts else ('لا توجد بيانات', 0)
        
        # توصيات التحسين
        improvement_recommendations = self._generate_improvement_recommendations(losing_trades, failure_counts)
        
        stats = {
            'total_losing_trades': len(losing_trades),
            'average_loss': round(statistics.mean(loss_percentages), 2) if loss_percentages else 0,
            'median_loss': round(statistics.median(loss_percentages), 2) if loss_percentages else 0,
            'max_loss': round(max(loss_percentages), 2) if loss_percentages else 0,
            'most_common_failure': most_common_failure[0],
            'failure_frequency': most_common_failure[1],
            'failure_breakdown': failure_counts,
            'improvement_needed': improvement_recommendations,
            'analyzed_period_days': days
        }
        
        conn.close()
        return stats
    
    def _generate_improvement_recommendations(self, losing_trades: List, 
                                            failure_counts: Dict[str, int]) -> List[str]:
        """توليد توصيات لتحسين النظام"""
        recommendations = []
        
        if not losing_trades:
            return recommendations
            
        # تحليل الثقة مقابل النجاح
        high_confidence_losses = [t for t in losing_trades if t[6] > 90]  # confidence > 90
        if len(high_confidence_losses) > len(losing_trades) * 0.3:
            recommendations.append("تحسين معايير الثقة - إشارات بثقة عالية تفشل كثيراً")
        
        # تحليل الأصول الأكثر خسارة
        asset_losses = {}
        for trade in losing_trades:
            asset = trade[1]  # asset_id
            asset_losses[asset] = asset_losses.get(asset, 0) + 1
            
        if asset_losses:
            worst_asset = max(asset_losses.items(), key=lambda x: x[1])
            if worst_asset[1] > 3:
                recommendations.append(f"مراجعة خوارزمية التحليل للأصل: {worst_asset[0]}")
        
        # تحليل أسباب الفشل الشائعة
        if 'كسر كاذب للمقاومة/الدعم' in failure_counts and failure_counts['كسر كاذب للمقاومة/الدعم'] > 5:
            recommendations.append("تحسين كشف الكسر الكاذب - إضافة تأكيد حجم التداول")
            
        if 'تذبذب طبيعي - خسارة صغيرة' in failure_counts and failure_counts['تذبذب طبيعي - خسارة صغيرة'] > 10:
            recommendations.append("تحسين فلاتر التذبذب - تجنب الإشارات أثناء التذبذبات الصغيرة")
            
        if not recommendations:
            recommendations.append("النظام يعمل بشكل جيد - مراقبة مستمرة مطلوبة")
            
        return recommendations
    
    def get_failure_patterns(self) -> List[Dict[str, Any]]:
        """جلب أنماط الفشل المتكررة"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM failure_patterns 
            ORDER BY occurrence_count DESC
        ''')
        
        patterns = cursor.fetchall()
        conn.close()
        
        result = []
        for pattern in patterns:
            result.append({
                'pattern_name': pattern[1],
                'description': pattern[2],
                'occurrence_count': pattern[3],
                'average_loss': pattern[4],
                'last_occurrence': pattern[5],
                'pattern_data': json.loads(pattern[6]) if pattern[6] else {}
            })
            
        return result
    
    def update_daily_improvement_stats(self):
        """تحديث إحصائيات التحسن اليومية"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # حساب إحصائيات اليوم
        today_start = time.time() - 24 * 3600  # منذ 24 ساعة
        
        cursor.execute('''
            SELECT COUNT(*) FROM losing_trades WHERE entry_time > ?
        ''', (today_start,))
        total_signals = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*), AVG(loss_percentage) FROM losing_trades 
            WHERE exit_time IS NOT NULL AND entry_time > ?
        ''', (today_start,))
        losing_signals, avg_loss = cursor.fetchone()
        
        loss_rate = (losing_signals / total_signals * 100) if total_signals > 0 else 0
        
        # حساب نقاط التحسن (كلما قل الرقم كان أفضل)
        improvement_score = 100 - loss_rate - (avg_loss or 0)
        
        cursor.execute('''
            INSERT OR REPLACE INTO ai_improvement_stats 
            (date, total_signals, losing_signals, loss_rate, average_loss, improvement_score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (today, total_signals, losing_signals or 0, loss_rate, avg_loss or 0, improvement_score))
        
        conn.commit()
        conn.close()
        
        return {
            'date': today,
            'total_signals': total_signals,
            'losing_signals': losing_signals or 0,
            'loss_rate': round(loss_rate, 2),
            'average_loss': round(avg_loss or 0, 2),
            'improvement_score': round(improvement_score, 2)
        }
    
    def get_ai_learning_insights(self) -> Dict[str, Any]:
        """رؤى التعلم للذكاء الاصطناعي"""
        stats = self.get_losing_trades_stats(30)
        patterns = self.get_failure_patterns()
        daily_stats = self.update_daily_improvement_stats()
        
        # تحليل الاتجاهات
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT date, loss_rate, improvement_score FROM ai_improvement_stats 
            ORDER BY date DESC LIMIT 7
        ''')
        weekly_trend = cursor.fetchall()
        conn.close()
        
        # حساب اتجاه التحسن
        if len(weekly_trend) >= 2:
            recent_scores = [row[2] for row in weekly_trend[:3]]
            older_scores = [row[2] for row in weekly_trend[3:]]
            
            if recent_scores and older_scores:
                trend_direction = "تحسن" if statistics.mean(recent_scores) > statistics.mean(older_scores) else "تراجع"
            else:
                trend_direction = "مستقر"
        else:
            trend_direction = "غير كافي للتحليل"
        
        return {
            'current_performance': {
                'loss_rate': stats.get('average_loss', 0),
                'most_common_failure': stats.get('most_common_failure', 'غير محدد'),
                'total_analyzed_trades': stats.get('total_losing_trades', 0)
            },
            'failure_patterns': patterns[:5],  # أهم 5 أنماط
            'improvement_recommendations': stats.get('improvement_needed', []),
            'weekly_trend': trend_direction,
            'daily_stats': daily_stats,
            'ai_learning_status': {
                'patterns_identified': len(patterns),
                'data_quality': "جيد" if stats.get('total_losing_trades', 0) > 10 else "يحتاج المزيد",
                'learning_readiness': len(patterns) >= 3
            }
        }

# إنشاء نسخة عامة من المتتبع
losing_trades_tracker = LosingTradesTracker()