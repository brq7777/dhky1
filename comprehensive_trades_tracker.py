"""
نظام شامل لتتبع جميع الصفقات - الناجحة والخاسرة
تحليل أسباب النجاح والفشل لتحسين دقة الإشارات المستقبلية
"""
import sqlite3
import time
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import statistics
import numpy as np

class ComprehensiveTradesTracker:
    def __init__(self, db_path='comprehensive_trades.db'):
        """تهيئة متتبع الصفقات الشامل"""
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """إنشاء قاعدة البيانات وجداول التتبع الشاملة"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # جدول جميع الصفقات (ناجحة وخاسرة)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS all_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_id TEXT NOT NULL,
                asset_name TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                signal_price REAL NOT NULL,
                entry_time REAL NOT NULL,
                exit_time REAL DEFAULT NULL,
                exit_price REAL DEFAULT NULL,
                
                -- نتيجة الصفقة
                trade_result TEXT DEFAULT 'pending', -- 'winning', 'losing', 'pending'
                profit_loss_amount REAL DEFAULT NULL,
                profit_loss_percentage REAL DEFAULT NULL,
                
                -- معلومات الإشارة
                confidence INTEGER NOT NULL,
                rsi REAL,
                sma_short REAL,
                sma_long REAL,
                price_change_5 REAL,
                trend TEXT,
                volatility REAL,
                
                -- تحليل أسباب النتيجة
                success_reason TEXT,
                failure_reason TEXT,
                market_condition TEXT,
                
                -- عوامل التحليل
                false_breakout BOOLEAN DEFAULT 0,
                whipsaw BOOLEAN DEFAULT 0,
                news_impact BOOLEAN DEFAULT 0,
                volume_confirmation BOOLEAN DEFAULT 0,
                trend_continuation BOOLEAN DEFAULT 0,
                support_resistance_respect BOOLEAN DEFAULT 0,
                
                -- معلومات إضافية
                session_id TEXT,
                tracking_duration REAL DEFAULT NULL, -- مدة تتبع الصفقة بالثواني
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول أنماط النجاح والفشل
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS success_failure_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL, -- 'success' or 'failure'
                pattern_name TEXT NOT NULL,
                pattern_description TEXT,
                occurrence_count INTEGER DEFAULT 0,
                average_result REAL DEFAULT 0, -- متوسط الربح/الخسارة
                confidence_range TEXT, -- نطاق الثقة الأكثر نجاحاً
                best_conditions TEXT, -- أفضل ظروف السوق
                pattern_data TEXT, -- بيانات إضافية JSON
                last_occurrence TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول إحصائيات الأداء اليومي
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                total_signals INTEGER DEFAULT 0,
                winning_signals INTEGER DEFAULT 0,
                losing_signals INTEGER DEFAULT 0,
                pending_signals INTEGER DEFAULT 0,
                
                success_rate REAL DEFAULT 0,
                average_profit REAL DEFAULT 0,
                average_loss REAL DEFAULT 0,
                net_performance REAL DEFAULT 0,
                
                best_asset TEXT,
                worst_asset TEXT,
                improvement_score REAL DEFAULT 0,
                ai_learning_points TEXT, -- نقاط التعلم JSON
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول توصيات تحسين الذكاء الاصطناعي
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_improvement_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recommendation_type TEXT NOT NULL, -- 'signal_quality', 'pattern_recognition', 'risk_management'
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                priority INTEGER DEFAULT 1, -- 1=عالي, 2=متوسط, 3=منخفض
                implementation_status TEXT DEFAULT 'pending', -- 'pending', 'implemented', 'testing'
                success_impact_expected REAL DEFAULT 0, -- التحسن المتوقع في نسبة النجاح
                data_supporting TEXT, -- البيانات الداعمة JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def track_new_signal(self, signal_data: Dict[str, Any], session_id: str = None) -> int:
        """تتبع إشارة جديدة"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO all_trades (
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
            session_id if session_id is not None else f"session_{int(time.time())}"
        ))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logging.info(f"تتبع إشارة جديدة: {signal_data.get('asset_id')} - ID: {trade_id}")
        return trade_id if trade_id is not None else 0
    
    def finalize_trade(self, trade_id: int, exit_price: float, 
                      is_winning: bool = True, analysis: Dict[str, Any] = None):
        """إنهاء الصفقة وتحديد نتيجتها"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # جلب بيانات الصفقة
        cursor.execute('''
            SELECT signal_price, signal_type, entry_time, asset_id FROM all_trades WHERE id = ?
        ''', (trade_id,))
        
        result = cursor.fetchone()
        if not result:
            logging.warning(f"لم يتم العثور على الصفقة: {trade_id}")
            conn.close()
            return
            
        signal_price, signal_type, entry_time, asset_id = result
        
        # حساب الربح/الخسارة
        if signal_type == 'BUY':
            profit_loss = exit_price - signal_price
        else:  # SELL
            profit_loss = signal_price - exit_price
            
        profit_loss_percentage = (profit_loss / signal_price) * 100
        trade_result = 'winning' if is_winning else 'losing'
        tracking_duration = time.time() - entry_time
        
        # تحليل أسباب النجاح/الفشل
        if analysis is None:
            analysis = self._analyze_trade_outcome(trade_id, is_winning, 
                                                 profit_loss_percentage, asset_id)
        
        # تحديث الصفقة
        cursor.execute('''
            UPDATE all_trades SET
                exit_time = ?, exit_price = ?, trade_result = ?,
                profit_loss_amount = ?, profit_loss_percentage = ?,
                success_reason = ?, failure_reason = ?, market_condition = ?,
                false_breakout = ?, whipsaw = ?, news_impact = ?,
                volume_confirmation = ?, trend_continuation = ?, support_resistance_respect = ?,
                tracking_duration = ?
            WHERE id = ?
        ''', (
            time.time(), exit_price, trade_result,
            profit_loss, profit_loss_percentage,
            analysis.get('success_reason') if is_winning else None,
            analysis.get('failure_reason') if not is_winning else None,
            analysis.get('market_condition', 'غير محدد'),
            analysis.get('false_breakout', False),
            analysis.get('whipsaw', False),
            analysis.get('news_impact', False),
            analysis.get('volume_confirmation', False),
            analysis.get('trend_continuation', False),
            analysis.get('support_resistance_respect', False),
            tracking_duration,
            trade_id
        ))
        
        conn.commit()
        conn.close()
        
        # تحديث أنماط النجاح/الفشل
        self._update_patterns(is_winning, analysis, profit_loss_percentage)
        
        status = "ناجحة" if is_winning else "خاسرة"
        logging.info(f"تم إنهاء الصفقة {trade_id} كصفقة {status}: {profit_loss_percentage:.2f}%")
        
    def _analyze_trade_outcome(self, trade_id: int, is_winning: bool, 
                              profit_loss_percentage: float, asset_id: str) -> Dict[str, Any]:
        """تحليل ذكي لأسباب نجاح/فشل الصفقة"""
        
        analysis = {
            'market_condition': 'طبيعي',
            'false_breakout': False,
            'whipsaw': False,
            'news_impact': False,
            'volume_confirmation': False,
            'trend_continuation': False,
            'support_resistance_respect': False
        }
        
        abs_percentage = abs(profit_loss_percentage)
        
        if is_winning:
            # تحليل أسباب النجاح
            if abs_percentage > 3.0:
                analysis['success_reason'] = 'اختراق قوي للمقاومة/الدعم'
                analysis['support_resistance_respect'] = True
            elif abs_percentage > 1.5:
                analysis['success_reason'] = 'اتجاه واضح مع تأكيد حجم'
                analysis['volume_confirmation'] = True
                analysis['trend_continuation'] = True
            elif abs_percentage > 0.5:
                analysis['success_reason'] = 'تحليل فني دقيق - اتجاه صحيح'
                analysis['trend_continuation'] = True
            else:
                analysis['success_reason'] = 'تحرك سعري صغير لكن صحيح'
                
        else:
            # تحليل أسباب الفشل
            if abs_percentage < 0.5:
                analysis['failure_reason'] = 'تذبذب طبيعي - خسارة صغيرة'
                analysis['whipsaw'] = True
            elif abs_percentage < 1.5:
                analysis['failure_reason'] = 'كسر كاذب للمقاومة/الدعم'
                analysis['false_breakout'] = True
            elif abs_percentage < 3.0:
                analysis['failure_reason'] = 'تغير مفاجئ في اتجاه السوق'
                analysis['market_condition'] = 'متقلب'
            else:
                analysis['failure_reason'] = 'أخبار مؤثرة أو حدث غير متوقع'
                analysis['news_impact'] = True
                analysis['market_condition'] = 'متقلب بشدة'
                
        return analysis
    
    def _update_patterns(self, is_winning: bool, analysis: Dict[str, Any], 
                        result_percentage: float):
        """تحديث أنماط النجاح والفشل"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        pattern_type = 'success' if is_winning else 'failure'
        if is_winning:
            pattern_name = analysis.get('success_reason', 'نجاح غير محدد')
        else:
            pattern_name = analysis.get('failure_reason', 'فشل غير محدد')
        
        # البحث عن النمط الموجود
        cursor.execute('''
            SELECT id, occurrence_count, average_result FROM success_failure_patterns
            WHERE pattern_type = ? AND pattern_name = ?
        ''', (pattern_type, pattern_name))
        
        existing = cursor.fetchone()
        
        if existing:
            # تحديث النمط الموجود
            pattern_id, count, avg_result = existing
            new_count = count + 1
            new_avg = ((avg_result * count) + result_percentage) / new_count
            
            cursor.execute('''
                UPDATE success_failure_patterns SET
                    occurrence_count = ?, average_result = ?,
                    pattern_data = ?, last_occurrence = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_count, new_avg, json.dumps(analysis), pattern_id))
        else:
            # إنشاء نمط جديد
            cursor.execute('''
                INSERT INTO success_failure_patterns 
                (pattern_type, pattern_name, pattern_description, occurrence_count, 
                 average_result, pattern_data, last_occurrence)
                VALUES (?, ?, ?, 1, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                pattern_type, pattern_name, f"نمط {pattern_type}: {pattern_name}",
                result_percentage, json.dumps(analysis)
            ))
        
        conn.commit()
        conn.close()
    
    def get_comprehensive_stats(self, days: int = 30) -> Dict[str, Any]:
        """إحصائيات شاملة للأداء"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since_timestamp = time.time() - (days * 24 * 3600)
        
        # إحصائيات عامة
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN trade_result = 'winning' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN trade_result = 'losing' THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN trade_result = 'pending' THEN 1 ELSE 0 END) as pending,
                AVG(CASE WHEN trade_result = 'winning' THEN profit_loss_percentage ELSE NULL END) as avg_profit,
                AVG(CASE WHEN trade_result = 'losing' THEN ABS(profit_loss_percentage) ELSE NULL END) as avg_loss,
                AVG(confidence) as avg_confidence
            FROM all_trades WHERE entry_time > ?
        ''', (since_timestamp,))
        
        stats = cursor.fetchone()
        total, wins, losses, pending, avg_profit, avg_loss, avg_confidence = stats
        
        success_rate = (wins / total * 100) if total > 0 else 0
        
        # أفضل وأسوأ الأصول
        cursor.execute('''
            SELECT asset_id, 
                   SUM(CASE WHEN trade_result = 'winning' THEN 1 ELSE 0 END) as wins,
                   COUNT(*) as total
            FROM all_trades 
            WHERE entry_time > ? AND trade_result != 'pending'
            GROUP BY asset_id
            HAVING total >= 3
            ORDER BY (wins * 1.0 / total) DESC
        ''', (since_timestamp,))
        
        asset_performance = cursor.fetchall()
        
        # أنماط النجاح الأكثر شيوعاً
        cursor.execute('''
            SELECT pattern_name, occurrence_count, average_result
            FROM success_failure_patterns 
            WHERE pattern_type = 'success'
            ORDER BY occurrence_count DESC
            LIMIT 5
        ''', ())
        
        success_patterns = cursor.fetchall()
        
        # أنماط الفشل الأكثر شيوعاً
        cursor.execute('''
            SELECT pattern_name, occurrence_count, average_result
            FROM success_failure_patterns 
            WHERE pattern_type = 'failure'
            ORDER BY occurrence_count DESC
            LIMIT 5
        ''', ())
        
        failure_patterns = cursor.fetchall()
        
        conn.close()
        
        return {
            'summary': {
                'total_trades': total or 0,
                'winning_trades': wins or 0,
                'losing_trades': losses or 0,
                'pending_trades': pending or 0,
                'success_rate': round(success_rate, 2),
                'average_profit': round(avg_profit or 0, 2),
                'average_loss': round(avg_loss or 0, 2),
                'average_confidence': round(avg_confidence or 0, 1)
            },
            'asset_performance': {
                'best_asset': asset_performance[0] if asset_performance else None,
                'worst_asset': asset_performance[-1] if asset_performance else None,
                'all_assets': asset_performance
            },
            'success_patterns': [
                {
                    'pattern': pattern[0],
                    'frequency': pattern[1],
                    'avg_profit': round(pattern[2], 2)
                } for pattern in success_patterns
            ],
            'failure_patterns': [
                {
                    'pattern': pattern[0], 
                    'frequency': pattern[1],
                    'avg_loss': round(abs(pattern[2]), 2)
                } for pattern in failure_patterns
            ],
            'analyzed_period_days': days
        }
    
    def generate_ai_recommendations(self) -> List[Dict[str, Any]]:
        """توليد توصيات لتحسين الذكاء الاصطناعي"""
        stats = self.get_comprehensive_stats(30)
        recommendations = []
        
        # تحليل معدل النجاح
        success_rate = stats['summary']['success_rate']
        if success_rate < 60:
            recommendations.append({
                'type': 'signal_quality',
                'title': 'تحسين جودة الإشارات',
                'description': f'معدل النجاح الحالي {success_rate:.1f}% يحتاج تحسين. يُنصح برفع معايير الثقة.',
                'priority': 1,
                'expected_improvement': 15
            })
        
        # تحليل أنماط الفشل
        failure_patterns = stats['failure_patterns']
        if failure_patterns:
            common_failure = failure_patterns[0]
            if common_failure['frequency'] > 5:
                recommendations.append({
                    'type': 'pattern_recognition',
                    'title': f'تحسين كشف: {common_failure["pattern"]}',
                    'description': f'هذا النمط حدث {common_failure["frequency"]} مرة. يحتاج تحسين خوارزمية الكشف.',
                    'priority': 1,
                    'expected_improvement': 10
                })
        
        # تحليل الثقة مقابل النجاح
        avg_confidence = stats['summary']['average_confidence']
        if avg_confidence > 85 and success_rate < 70:
            recommendations.append({
                'type': 'signal_quality',
                'title': 'مراجعة معايير الثقة',
                'description': 'الثقة عالية لكن النجاح منخفض. يحتاج مراجعة حساب الثقة.',
                'priority': 1,
                'expected_improvement': 20
            })
        
        # حفظ التوصيات في قاعدة البيانات
        self._save_recommendations(recommendations)
        
        return recommendations
    
    def _save_recommendations(self, recommendations: List[Dict[str, Any]]):
        """حفظ التوصيات في قاعدة البيانات"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for rec in recommendations:
            cursor.execute('''
                INSERT OR REPLACE INTO ai_improvement_recommendations 
                (recommendation_type, title, description, priority, success_impact_expected, data_supporting)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                rec['type'], rec['title'], rec['description'],
                rec['priority'], rec.get('expected_improvement', 0),
                json.dumps(rec)
            ))
        
        conn.commit()
        conn.close()
    
    def update_daily_performance(self):
        """تحديث إحصائيات الأداء اليومي"""
        today = datetime.now().strftime('%Y-%m-%d')
        stats = self.get_comprehensive_stats(1)  # آخر 24 ساعة
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        summary = stats['summary']
        
        # نقاط التعلم
        learning_points = {
            'success_rate_trend': 'improving' if summary['success_rate'] > 60 else 'needs_work',
            'best_performing_pattern': stats['success_patterns'][0] if stats['success_patterns'] else None,
            'main_challenge': stats['failure_patterns'][0] if stats['failure_patterns'] else None
        }
        
        cursor.execute('''
            INSERT OR REPLACE INTO daily_performance 
            (date, total_signals, winning_signals, losing_signals, pending_signals,
             success_rate, average_profit, average_loss, net_performance,
             best_asset, worst_asset, improvement_score, ai_learning_points)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            today,
            summary['total_trades'],
            summary['winning_trades'], 
            summary['losing_trades'],
            summary['pending_trades'],
            summary['success_rate'],
            summary['average_profit'],
            summary['average_loss'],
            summary['average_profit'] - summary['average_loss'],
            stats['asset_performance']['best_asset'][0] if stats['asset_performance']['best_asset'] else None,
            stats['asset_performance']['worst_asset'][0] if stats['asset_performance']['worst_asset'] else None,
            summary['success_rate'] + summary['average_profit'] - summary['average_loss'],
            json.dumps(learning_points)
        ))
        
        conn.commit()
        conn.close()
        
        return {
            'date': today,
            'performance_score': summary['success_rate'],
            'learning_status': learning_points
        }

# إنشاء نسخة عامة من المتتبع الشامل
trades_tracker = ComprehensiveTradesTracker()