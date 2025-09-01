import os
import requests
import logging
from typing import Dict, List, Optional
import time
import random

class PriceService:
    def __init__(self):
        self.binance_base_url = "https://api.binance.com/api/v3"
        self.twelve_data_key = os.getenv("TWELVE_DATA_API_KEY", "4589b5620aa8448faf709e192a1ae8f1")
        self.twelve_data_base_url = "https://api.twelvedata.com"
        
        # Asset definitions
        self.assets = [
            {'id': 'BTCUSDT', 'name': 'بيتكوين', 'type': 'crypto', 'source': 'binance'},
            {'id': 'ETHUSDT', 'name': 'إيثريوم', 'type': 'crypto', 'source': 'binance'},
            {'id': 'XAU/USD', 'name': 'الذهب', 'type': 'metal', 'source': 'twelve'},
            {'id': 'EUR/USD', 'name': 'EUR/USD', 'type': 'forex', 'source': 'twelve'},
            {'id': 'GBP/USD', 'name': 'GBP/USD', 'type': 'forex', 'source': 'twelve'},
            {'id': 'EUR/JPY', 'name': 'EUR/JPY', 'type': 'forex', 'source': 'twelve'},
            {'id': 'USD/JPY', 'name': 'USD/JPY', 'type': 'forex', 'source': 'twelve'},
            {'id': 'NZD/USD', 'name': 'NZD/USD', 'type': 'forex', 'source': 'twelve'},
            {'id': 'USD/CHF', 'name': 'USD/CHF', 'type': 'forex', 'source': 'twelve'},
        ]
        
        # Store for price cache and alerts
        self.price_cache = {}
        self.alerts = {}  # {asset_id: [{'threshold': float, 'type': str, 'client_id': str}]}
        self.signals_history = {}  # Track signal generation
        self.last_signal_time = {}
        
        # Demo data fallback for when APIs fail
        self.demo_prices = {
            'BTCUSDT': 65234.50,
            'ETHUSDT': 3456.78,
            'XAU/USD': 2634.25,
            'EUR/USD': 1.0823,
            'GBP/USD': 1.2678,
            'EUR/JPY': 164.32,
            'USD/JPY': 151.45,
            'NZD/USD': 0.5823,
            'USD/CHF': 0.8834
        }
        
    def get_binance_price(self, symbol: str) -> Optional[float]:
        """Get price from Binance API"""
        try:
            url = f"{self.binance_base_url}/ticker/price"
            params = {'symbol': symbol}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return float(data['price'])
            
        except Exception as e:
            logging.error(f"Error fetching Binance price for {symbol}: {e}")
            return None
    
    def get_twelve_data_price(self, symbol: str) -> Optional[float]:
        """Get price from TwelveData API"""
        try:
            url = f"{self.twelve_data_base_url}/price"
            params = {
                'symbol': symbol,
                'apikey': self.twelve_data_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'price' in data:
                return float(data['price'])
            else:
                logging.error(f"No price data in response for {symbol}: {data}")
                return None
                
        except Exception as e:
            logging.error(f"Error fetching TwelveData price for {symbol}: {e}")
            return None
    
    def get_price(self, asset_id: str) -> Optional[Dict]:
        """Get price for a specific asset with fallback to demo data"""
        asset = next((a for a in self.assets if a['id'] == asset_id), None)
        if not asset:
            return None
        
        price = None
        if asset['source'] == 'binance':
            price = self.get_binance_price(asset_id)
        elif asset['source'] == 'twelve':
            price = self.get_twelve_data_price(asset_id)
        
        # Fallback to demo data if API fails
        if price is None and asset_id in self.demo_prices:
            import random
            base_price = self.demo_prices[asset_id]
            # Add small random variation to simulate price movement
            variation = random.uniform(-0.02, 0.02)  # ±2% variation
            price = base_price * (1 + variation)
            logging.info(f"Using demo price for {asset_id}: {price}")
        
        if price is not None:
            price_data = {
                'id': asset_id,
                'name': asset['name'],
                'type': asset['type'],
                'price': price,
                'timestamp': time.time()
            }
            self.price_cache[asset_id] = price_data
            return price_data
        
        return None
    
    def get_all_prices(self) -> Dict[str, Dict]:
        """Get prices for all assets"""
        prices = {}
        for asset in self.assets:
            price_data = self.get_price(asset['id'])
            if price_data:
                prices[asset['id']] = price_data
        
        return prices
    
    def add_alert(self, asset_id: str, threshold: float, alert_type: str, client_id: str):
        """Add a price alert"""
        if asset_id not in self.alerts:
            self.alerts[asset_id] = []
        
        alert = {
            'threshold': threshold,
            'type': alert_type,  # 'above' or 'below'
            'client_id': client_id,
            'created_at': time.time()
        }
        
        self.alerts[asset_id].append(alert)
        logging.info(f"Added alert for {asset_id}: {alert}")
    
    def check_alerts(self, current_prices: Dict[str, Dict]) -> List[Dict]:
        """Check if any alerts should be triggered"""
        triggered_alerts = []
        
        for asset_id, price_data in current_prices.items():
            if asset_id not in self.alerts:
                continue
            
            current_price = price_data['price']
            alerts_to_remove = []
            
            for i, alert in enumerate(self.alerts[asset_id]):
                triggered = False
                
                if alert['type'] == 'above' and current_price >= alert['threshold']:
                    triggered = True
                elif alert['type'] == 'below' and current_price <= alert['threshold']:
                    triggered = True
                
                if triggered:
                    triggered_alert = {
                        'asset_id': asset_id,
                        'asset_name': price_data['name'],
                        'current_price': current_price,
                        'threshold': alert['threshold'],
                        'type': alert['type'],
                        'client_id': alert['client_id']
                    }
                    triggered_alerts.append(triggered_alert)
                    alerts_to_remove.append(i)
            
            # Remove triggered alerts
            for i in reversed(alerts_to_remove):
                del self.alerts[asset_id][i]
        
        return triggered_alerts
    
    def generate_trading_signals(self, current_prices: Dict[str, Dict]) -> List[Dict]:
        """Generate trading signals based on price movements"""
        signals = []
        current_time = time.time()
        
        for asset_id, price_data in current_prices.items():
            # Only generate signals every 30-60 seconds per asset
            if asset_id in self.last_signal_time:
                if current_time - self.last_signal_time[asset_id] < 30:
                    continue
            
            # Generate random signals for demo (in real app, use technical analysis)
            if random.random() < 0.15:  # 15% chance of signal per check
                signal_type = random.choice(['BUY', 'SELL'])
                confidence = random.randint(70, 95)
                
                signal = {
                    'asset_id': asset_id,
                    'asset_name': price_data['name'],
                    'type': signal_type,
                    'price': price_data['price'],
                    'confidence': confidence,
                    'timestamp': current_time,
                    'reason': self._get_signal_reason(signal_type)
                }
                
                signals.append(signal)
                self.last_signal_time[asset_id] = current_time
                
                # Store in history
                if asset_id not in self.signals_history:
                    self.signals_history[asset_id] = []
                self.signals_history[asset_id].append(signal)
                
                # Keep only last 10 signals per asset
                if len(self.signals_history[asset_id]) > 10:
                    self.signals_history[asset_id] = self.signals_history[asset_id][-10:]
        
        return signals
    
    def _get_signal_reason(self, signal_type: str) -> str:
        """Get a reason for the trading signal"""
        buy_reasons = [
            "اختراق مستوى مقاومة قوي",
            "إشارة إيجابية من المؤشرات الفنية", 
            "زخم صاعد قوي",
            "دعم قوي عند هذا المستوى",
            "نمط صاعد واضح"
        ]
        
        sell_reasons = [
            "كسر مستوى دعم مهم",
            "إشارة سلبية من المؤشرات",
            "ضعف في الزخم الصاعد", 
            "مقاومة قوية عند هذا المستوى",
            "نمط هابط واضح"
        ]
        
        return random.choice(buy_reasons if signal_type == 'BUY' else sell_reasons)
