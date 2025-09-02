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
        
        # Offline mode tracking
        self.offline_mode = False
        self.api_failure_count = {}
        self.last_api_success = {}
        self.offline_mode_threshold = 3  # Switch to offline after 3 consecutive failures for faster detection
        
        # Asset definitions
        self.assets = [
            {'id': 'BTCUSDT', 'name': 'BTCUSD', 'type': 'crypto', 'source': 'binance'},
            {'id': 'ETHUSDT', 'name': 'ETHUSD', 'type': 'crypto', 'source': 'binance'},
            {'id': 'XAU/USD', 'name': 'XAUUSD', 'type': 'metal', 'source': 'twelve'},
            {'id': 'EUR/USD', 'name': 'EUR/USD', 'type': 'forex', 'source': 'twelve'},
            {'id': 'GBP/USD', 'name': 'GBP/USD', 'type': 'forex', 'source': 'twelve'},
            {'id': 'EUR/JPY', 'name': 'EUR/JPY', 'type': 'forex', 'source': 'twelve'},
            {'id': 'USD/JPY', 'name': 'USD/JPY', 'type': 'forex', 'source': 'twelve'},
            {'id': 'NZD/USD', 'name': 'NZD/USD', 'type': 'forex', 'source': 'twelve'},
            {'id': 'USD/CHF', 'name': 'USD/CHF', 'type': 'forex', 'source': 'twelve'},
        ]
        
        # Store for price cache and alerts - optimized
        self.price_cache = {}
        self.previous_prices = {}  # Track price changes
        self.alerts = {}  # {asset_id: [{'threshold': float, 'type': str, 'client_id': str}]}
        self.signals_history = {}  # Track signal generation
        self.last_signal_time = {}
        self.last_alert_check = {}  # Optimize alert checking
        
        # Technical analysis data storage
        self.price_history = {}  # Store historical prices for analysis
        self.technical_indicators = {}  # Store calculated indicators
        
        # Demo data fallback for when APIs fail - more realistic starting prices
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
        
        # Persistent price tracking for offline mode
        self.price_trends = {asset_id: {'direction': 1, 'momentum': 0.001} for asset_id in self.demo_prices.keys()}
        
        # Connection optimization - reuse connections for better performance
        self.session = requests.Session()
        # Set connection pool size for better performance
        from requests.adapters import HTTPAdapter
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
        
    def get_binance_price(self, symbol: str) -> Optional[float]:
        """Get price from Binance API with offline mode detection"""
        # Skip API call if in offline mode
        if self.offline_mode:
            return None
            
        try:
            url = f"{self.binance_base_url}/ticker/price"
            params = {'symbol': symbol}
            
            response = self.session.get(url, params=params, timeout=2)  # Fast timeout for better responsiveness
            response.raise_for_status()
            
            data = response.json()
            price = float(data['price'])
            
            # Reset failure count on success
            self.api_failure_count[symbol] = 0
            self.last_api_success[symbol] = time.time()
            return price
            
        except Exception as e:
            logging.error(f"Error fetching Binance price for {symbol}: {e}")
            self._handle_api_failure(symbol)
            return None
    
    def get_twelve_data_price(self, symbol: str) -> Optional[float]:
        """Get price from TwelveData API with offline mode detection"""
        # Skip API call if in offline mode
        if self.offline_mode:
            return None
            
        try:
            url = f"{self.twelve_data_base_url}/price"
            params = {
                'symbol': symbol,
                'apikey': self.twelve_data_key
            }
            
            response = self.session.get(url, params=params, timeout=2)  # Fast timeout for better responsiveness
            response.raise_for_status()
            
            data = response.json()
            if 'price' in data:
                price = float(data['price'])
                # Reset failure count on success
                self.api_failure_count[symbol] = 0
                self.last_api_success[symbol] = time.time()
                return price
            else:
                logging.error(f"No price data in response for {symbol}: {data}")
                self._handle_api_failure(symbol)
                return None
                
        except Exception as e:
            logging.error(f"Error fetching TwelveData price for {symbol}: {e}")
            self._handle_api_failure(symbol)
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
        
        # Fallback to demo data if API fails - enhanced offline mode
        if price is None and asset_id in self.demo_prices:
            price = self._generate_offline_price(asset_id)
            status = "OFFLINE" if self.offline_mode else "DEMO"
            logging.info(f"Using {status} price for {asset_id}: {price}")
        
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
    
    def get_all_prices_fast(self) -> Dict[str, Dict]:
        """Get prices for all assets - optimized version"""
        prices = {}
        # Use threading for parallel API calls when not in offline mode
        if not self.offline_mode:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = {executor.submit(self.get_price, asset['id']): asset['id'] for asset in self.assets}
                for future in concurrent.futures.as_completed(futures, timeout=3):
                    try:
                        asset_id = futures[future]
                        price_data = future.result()
                        if price_data:
                            prices[asset_id] = price_data
                    except Exception as e:
                        logging.error(f"Error fetching price in parallel: {e}")
        else:
            # Sequential for offline mode
            for asset in self.assets:
                price_data = self.get_price(asset['id'])
                if price_data:
                    prices[asset['id']] = price_data
        
        return prices
    
    def has_price_changes(self) -> bool:
        """Check if prices have significantly changed since last update"""
        if not self.previous_prices:
            self.previous_prices = dict(self.price_cache)
            return True
        
        # Check for significant changes (>0.01%)
        for asset_id, current_data in self.price_cache.items():
            if asset_id in self.previous_prices:
                old_price = self.previous_prices[asset_id]['price']
                new_price = current_data['price']
                change_percent = abs((new_price - old_price) / old_price) * 100
                if change_percent > 0.01:  # 0.01% threshold
                    self.previous_prices = dict(self.price_cache)
                    return True
        
        return False
    
    def add_alert(self, asset_id: str, threshold: Optional[float] = None, alert_type: str = 'general', client_id: str = 'default'):
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
                
                # For general alerts, trigger on any significant price movement
                if alert['type'] == 'general':
                    # Check if price changed significantly (more than 0.5%)
                    if asset_id in self.price_cache:
                        prev_price = self.price_cache[asset_id]['price']
                        price_change_percent = abs((current_price - prev_price) / prev_price) * 100
                        if price_change_percent > 0.5:  # 0.5% change threshold
                            triggered = True
                    else:
                        triggered = True  # First time, always trigger
                elif alert['type'] == 'above' and alert['threshold'] and current_price >= alert['threshold']:
                    triggered = True
                elif alert['type'] == 'below' and alert['threshold'] and current_price <= alert['threshold']:
                    triggered = True
                
                if triggered:
                    triggered_alert = {
                        'asset_id': asset_id,
                        'asset_name': price_data['name'],
                        'current_price': current_price,
                        'threshold': alert.get('threshold'),
                        'type': alert['type'],
                        'client_id': alert['client_id']
                    }
                    triggered_alerts.append(triggered_alert)
                    
                    # Only remove specific threshold alerts, keep general alerts active
                    if alert['type'] != 'general':
                        alerts_to_remove.append(i)
            
            # Remove triggered threshold-based alerts
            for i in reversed(alerts_to_remove):
                del self.alerts[asset_id][i]
        
        return triggered_alerts
    
    def check_alerts_fast(self, current_prices: Dict[str, Dict]) -> List[Dict]:
        """Optimized alert checking - only check if prices changed significantly"""
        if not current_prices:
            return []
        
        current_time = time.time()
        triggered_alerts = []
        
        for asset_id, price_data in current_prices.items():
            # Skip if checked recently and no significant change
            if asset_id in self.last_alert_check:
                if current_time - self.last_alert_check[asset_id] < 2:  # Check every 2 seconds max
                    continue
            
            if asset_id in self.alerts and self.alerts[asset_id]:
                alerts = self.check_alerts({asset_id: price_data})
                triggered_alerts.extend(alerts)
                self.last_alert_check[asset_id] = current_time
        
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
    
    def generate_trading_signals_fast(self, current_prices: Dict[str, Dict]) -> List[Dict]:
        """Generate real technical analysis signals based on indicators"""
        signals = []
        current_time = time.time()
        
        for asset_id, price_data in current_prices.items():
            # Update price history for technical analysis
            self._update_price_history(asset_id, price_data['price'], current_time)
            
            # Only generate signals every 20-30 seconds per asset
            if asset_id in self.last_signal_time:
                time_since_last = current_time - self.last_signal_time[asset_id]
                if time_since_last < 20:  # Minimum 20 seconds between signals
                    continue
            
            # Calculate technical indicators and generate signals
            signal = self._analyze_technical_indicators(asset_id, price_data, current_time)
            
            if signal:
                signals.append(signal)
                self.last_signal_time[asset_id] = current_time
                
                # Store in history
                if asset_id not in self.signals_history:
                    self.signals_history[asset_id] = []
                self.signals_history[asset_id].append(signal)
                
                # Keep only last 5 signals per asset for performance
                if len(self.signals_history[asset_id]) > 5:
                    self.signals_history[asset_id] = self.signals_history[asset_id][-5:]
        
        return signals
    
    def _update_price_history(self, asset_id: str, price: float, timestamp: float):
        """Update price history for technical analysis"""
        if asset_id not in self.price_history:
            self.price_history[asset_id] = []
        
        self.price_history[asset_id].append({
            'price': price,
            'timestamp': timestamp
        })
        
        # Keep only last 50 price points for analysis
        if len(self.price_history[asset_id]) > 50:
            self.price_history[asset_id] = self.price_history[asset_id][-50:]
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI
        
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
        return rsi
    
    def _calculate_moving_average(self, prices: List[float], period: int) -> float:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        return sum(prices[-period:]) / period
    
    def _calculate_price_change_percent(self, prices: List[float], period: int = 5) -> float:
        """Calculate price change percentage over a period"""
        if len(prices) < period:
            return 0.0
        
        old_price = prices[-period]
        current_price = prices[-1]
        
        if old_price == 0:
            return 0.0
        
        return ((current_price - old_price) / old_price) * 100
    
    def _analyze_technical_indicators(self, asset_id: str, price_data: Dict, current_time: float) -> Optional[Dict]:
        """Analyze technical indicators and generate trading signal"""
        if asset_id not in self.price_history or len(self.price_history[asset_id]) < 10:
            return None  # Need more data for analysis
        
        prices = [p['price'] for p in self.price_history[asset_id]]
        current_price = price_data['price']
        
        # Calculate technical indicators
        rsi = self._calculate_rsi(prices)
        sma_short = self._calculate_moving_average(prices, 5)   # 5-period SMA
        sma_long = self._calculate_moving_average(prices, 15)   # 15-period SMA
        price_change_5 = self._calculate_price_change_percent(prices, 5)
        
        # Signal generation logic based on technical analysis
        signal_strength = 0
        signal_type = None
        reasons = []
        
        # RSI Analysis
        if rsi < 30:  # Oversold
            signal_strength += 30
            signal_type = 'BUY'
            reasons.append('RSI oversold')
        elif rsi > 70:  # Overbought
            signal_strength += 30
            signal_type = 'SELL'
            reasons.append('RSI overbought')
        
        # Moving Average Crossover
        if sma_short > sma_long and current_price > sma_short:
            signal_strength += 25
            if signal_type != 'SELL':
                signal_type = 'BUY'
                reasons.append('Price above MA')
        elif sma_short < sma_long and current_price < sma_short:
            signal_strength += 25
            if signal_type != 'BUY':
                signal_type = 'SELL'
                reasons.append('Price below MA')
        
        # Price momentum
        if abs(price_change_5) > 1.0:  # Strong momentum
            signal_strength += 20
            if price_change_5 > 0:
                if signal_type != 'SELL':
                    signal_type = 'BUY'
                    reasons.append('Strong upward momentum')
            else:
                if signal_type != 'BUY':
                    signal_type = 'SELL'
                    reasons.append('Strong downward momentum')
        
        # Only generate signal if strength is sufficient
        if signal_strength >= 40 and signal_type:
            confidence = min(signal_strength + 30, 95)  # Convert strength to confidence
            
            return {
                'asset_id': asset_id,
                'asset_name': price_data['name'],
                'type': signal_type,
                'price': current_price,
                'confidence': confidence,
                'timestamp': current_time,
                'reason': ', '.join(reasons),
                'rsi': round(rsi, 1),
                'sma_short': round(sma_short, 2),
                'sma_long': round(sma_long, 2),
                'price_change_5': round(price_change_5, 2)
            }
        
        return None
    
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
    
    def _handle_api_failure(self, symbol: str):
        """Handle API failure and detect offline mode"""
        if symbol not in self.api_failure_count:
            self.api_failure_count[symbol] = 0
        
        self.api_failure_count[symbol] += 1
        
        # Check if we should switch to offline mode
        total_failures = sum(self.api_failure_count.values())
        if total_failures >= self.offline_mode_threshold and not self.offline_mode:
            self.offline_mode = True
            logging.warning("SWITCHING TO OFFLINE MODE - APIs consistently failing")
    
    def _generate_offline_price(self, asset_id: str) -> float:
        """Generate realistic price movements for offline mode"""
        if asset_id not in self.demo_prices:
            return 0.0
        
        # Get base price - use cached price if available, otherwise demo price
        if asset_id in self.price_cache:
            base_price = self.price_cache[asset_id]['price']
        else:
            base_price = self.demo_prices[asset_id]
        
        # Get trend data
        trend = self.price_trends.get(asset_id, {'direction': 1, 'momentum': 0.001})
        
        # Generate realistic price movement
        # Random walk with momentum
        momentum_change = random.uniform(-0.0002, 0.0002)
        trend['momentum'] = max(-0.005, min(0.005, trend['momentum'] + momentum_change))
        
        # Occasional trend reversals
        if random.random() < 0.05:  # 5% chance of trend change
            trend['direction'] *= -1
        
        # Calculate price change
        base_variation = random.uniform(-0.001, 0.001)  # Small random noise
        trend_variation = trend['direction'] * trend['momentum']
        total_variation = base_variation + trend_variation
        
        # Apply change
        new_price = base_price * (1 + total_variation)
        
        # Update trend
        self.price_trends[asset_id] = trend
        
        return new_price
    
    def get_system_status(self) -> Dict:
        """Get system status including offline mode"""
        current_time = time.time()
        return {
            'offline_mode': self.offline_mode,
            'api_failures': dict(self.api_failure_count),
            'last_api_success': {k: current_time - v for k, v in self.last_api_success.items()},
            'total_assets': len(self.assets),
            'cached_prices': len(self.price_cache)
        }
