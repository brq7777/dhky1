// Trading Dashboard JavaScript
class TradingDashboard {
    constructor() {
        this.socket = null;
        this.assets = [
            { id: 'BTCUSDT', name: 'بيتكوين', type: 'crypto', source: 'binance' },
            { id: 'ETHUSDT', name: 'إيثريوم', type: 'crypto', source: 'binance' },
            { id: 'XAU/USD', name: 'الذهب', type: 'metal', source: 'twelve' },
            { id: 'EUR/USD', name: 'EUR/USD', type: 'forex', source: 'twelve' },
            { id: 'GBP/USD', name: 'GBP/USD', type: 'forex', source: 'twelve' },
            { id: 'EUR/JPY', name: 'EUR/JPY', type: 'forex', source: 'twelve' },
            { id: 'USD/JPY', name: 'USD/JPY', type: 'forex', source: 'twelve' },
            { id: 'NZD/USD', name: 'NZD/USD', type: 'forex', source: 'twelve' },
            { id: 'USD/CHF', name: 'USD/CHF', type: 'forex', source: 'twelve' },
        ];
        
        this.alertStates = JSON.parse(localStorage.getItem('alertStates') || '{}');
        this.prices = {};
        this.audioContext = null;
        this.currentAlertAsset = null;
        
        this.init();
    }
    
    init() {
        this.initializeSocket();
        this.renderSections();
        this.initializeAudio();
        this.setupModalHandlers();
        this.fetchInitialPrices();
        this.addSignalsPanel();
    }
    
    initializeSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.updateConnectionStatus(true);
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.updateConnectionStatus(false);
        });
        
        this.socket.on('price_update', (prices) => {
            this.updatePrices(prices);
        });
        
        this.socket.on('alert_triggered', (alert) => {
            this.handleAlertTriggered(alert);
        });
        
        this.socket.on('alert_subscribed', (data) => {
            console.log('Alert subscribed:', data);
        });
        
        this.socket.on('trading_signal', (signal) => {
            this.handleTradingSignal(signal);
        });
        
        this.socket.on('system_status', (status) => {
            this.updateSystemStatus(status);
        });
    }
    
    updateConnectionStatus(connected) {
        const statusDot = document.getElementById('connection-status');
        const statusText = document.getElementById('connection-text');
        
        if (connected) {
            statusDot.className = 'status-dot online';
            statusText.textContent = 'متصل';
        } else {
            statusDot.className = 'status-dot offline';
            statusText.textContent = 'غير متصل';
        }
    }
    
    updateSystemStatus(status) {
        const statusText = document.getElementById('connection-text');
        const statusDot = document.getElementById('connection-status');
        
        if (status.offline_mode) {
            statusDot.className = 'status-dot offline-mode';
            statusText.textContent = 'وضع عدم الاتصال - يعمل محلياً';
        } else {
            statusDot.className = 'status-dot online';
            statusText.textContent = 'متصل - بيانات حية';
        }
    }
    
    async fetchInitialPrices() {
        try {
            const response = await fetch('/api/prices');
            const data = await response.json();
            
            if (data.success) {
                this.updatePrices(data.data);
            } else {
                console.error('Error fetching prices:', data.error);
            }
        } catch (error) {
            console.error('Error fetching initial prices:', error);
        }
    }
    
    updatePrices(prices) {
        this.prices = prices;
        
        Object.keys(prices).forEach(assetId => {
            const priceElement = document.querySelector(`[data-price-id="${assetId}"]`);
            if (priceElement) {
                const price = prices[assetId].price;
                priceElement.textContent = this.formatPrice(price, assetId);
                priceElement.className = 'price';
            }
        });
    }
    
    formatPrice(price, assetId) {
        if (assetId.includes('USDT')) {
            return `$${parseFloat(price).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        } else {
            return parseFloat(price).toFixed(4);
        }
    }
    
    renderSections() {
        const cryptoMetals = document.getElementById('crypto-metals');
        const forex = document.getElementById('forex');
        
        cryptoMetals.innerHTML = '';
        forex.innerHTML = '';
        
        this.assets.forEach(asset => {
            const container = asset.type === 'forex' ? forex : cryptoMetals;
            container.appendChild(this.createAssetRow(asset));
        });
    }
    
    createAssetRow(asset) {
        const row = document.createElement('div');
        row.className = 'asset-row';
        row.setAttribute('data-asset-id', asset.id);
        
        const name = document.createElement('div');
        name.className = 'asset-name';
        name.innerHTML = `${asset.name} <span class="price" data-price-id="${asset.id}">--</span>`;
        
        const actions = document.createElement('div');
        actions.className = 'asset-actions';
        
        const toggle = document.createElement('button');
        toggle.className = 'toggle-btn ' + (this.isAlertOn(asset.id) ? 'on' : 'off');
        toggle.setAttribute('data-id', asset.id);
        toggle.textContent = this.isAlertOn(asset.id) ? 'شغال' : 'طافي';
        
        toggle.addEventListener('click', () => {
            this.toggleAlert(asset.id, toggle);
        });
        
        actions.appendChild(toggle);
        row.appendChild(name);
        row.appendChild(actions);
        
        return row;
    }
    
    createButton(text, onClick) {
        const button = document.createElement('button');
        button.textContent = text;
        button.className = 'sec-btn';
        button.addEventListener('click', onClick);
        return button;
    }
    
    isAlertOn(assetId) {
        return this.alertStates[assetId] === true;
    }
    
    toggleAlert(assetId, button) {
        const nowOn = !this.isAlertOn(assetId);
        this.alertStates[assetId] = nowOn;
        this.saveAlertStates();
        
        button.classList.toggle('on', nowOn);
        button.classList.toggle('off', !nowOn);
        button.textContent = nowOn ? 'شغال' : 'طافي';
    }
    
    saveAlertStates() {
        localStorage.setItem('alertStates', JSON.stringify(this.alertStates));
    }
    
    openAlertModal(asset) {
        this.currentAlertAsset = asset;
        const modal = document.getElementById('alert-modal');
        const assetInput = document.getElementById('alert-asset');
        
        assetInput.value = asset.name;
        modal.style.display = 'block';
    }
    
    setupModalHandlers() {
        const modal = document.getElementById('alert-modal');
        const closeBtn = document.querySelector('.close');
        const cancelBtn = document.getElementById('cancel-alert');
        const saveBtn = document.getElementById('save-alert');
        
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
        
        cancelBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });
        
        saveBtn.addEventListener('click', () => {
            this.saveAlert();
        });
        
        window.addEventListener('click', (event) => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
        
        // Add audio test button handler
        const audioTestBtn = document.getElementById('audio-test-btn');
        if (audioTestBtn) {
            audioTestBtn.addEventListener('click', () => {
                console.log('Audio test button clicked');
                this.playAlertSound({ frequency: 1200, duration: 800 });
                audioTestBtn.textContent = '✅ تم تشغيل الصوت';
                setTimeout(() => {
                    audioTestBtn.textContent = '🔊 اختبار الصوت';
                }, 2000);
            });
        }
    }
    
    saveAlert() {
        if (!this.currentAlertAsset) return;
        
        const threshold = parseFloat(document.getElementById('alert-threshold').value);
        const alertType = document.getElementById('alert-type').value;
        
        if (isNaN(threshold) || threshold <= 0) {
            alert('يرجى إدخال سعر صحيح');
            return;
        }
        
        // Subscribe to alert via socket
        this.socket.emit('subscribe_alerts', {
            asset_id: this.currentAlertAsset.id,
            threshold: threshold,
            type: alertType
        });
        
        // Enable alert locally
        this.alertStates[this.currentAlertAsset.id] = true;
        this.saveAlertStates();
        
        // Update button
        const button = document.querySelector(`[data-id="${this.currentAlertAsset.id}"]`);
        if (button) {
            button.classList.add('on');
            button.classList.remove('off');
            button.textContent = 'شغال';
        }
        
        // Close modal
        document.getElementById('alert-modal').style.display = 'none';
        
        // Clear form
        document.getElementById('alert-threshold').value = '';
        document.getElementById('alert-type').value = 'above';
    }
    
    viewAssetDetails(asset) {
        const price = this.prices[asset.id];
        if (price) {
            alert(`${asset.name}\nالسعر الحالي: ${this.formatPrice(price.price, asset.id)}\nآخر تحديث: ${new Date(price.timestamp * 1000).toLocaleString('ar-SA')}`);
        } else {
            alert('لا توجد بيانات أسعار متوفرة');
        }
    }
    
    deleteAlert(assetId) {
        if (confirm('هل أنت متأكد من حذف التنبيه؟')) {
            this.alertStates[assetId] = false;
            this.saveAlertStates();
            
            const button = document.querySelector(`[data-id="${assetId}"]`);
            if (button) {
                button.classList.remove('on');
                button.classList.add('off');
                button.textContent = 'طافي';
            }
        }
    }
    
    initializeAudio() {
        // Request notification permission
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
        
        // Initialize audio context immediately
        this.initAudioContext();
        
        // Add multiple event listeners to ensure audio context is enabled
        ['click', 'touchstart', 'mousedown', 'keydown'].forEach(event => {
            document.addEventListener(event, () => {
                this.initAudioContext();
            }, { once: true });
        });
    }
    
    initAudioContext() {
        try {
            if (!this.audioContext) {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                console.log('Audio context created');
            }
            
            if (this.audioContext && this.audioContext.state === 'suspended') {
                this.audioContext.resume().then(() => {
                    console.log('Audio context resumed successfully');
                }).catch(err => {
                    console.log('Error resuming audio context:', err);
                });
            }
        } catch (error) {
            console.log('Error with audio context:', error);
            // Fallback: try simple beep with audio element
            this.useFallbackAudio = true;
        }
    }
    
    playAlertSound(options = {}) {
        const { frequency = 880, duration = 180 } = options;
        
        console.log('Attempting to play alert sound:', { frequency, duration });
        
        // Ensure audio context is ready
        this.initAudioContext();
        
        try {
            if (this.useFallbackAudio || !this.audioContext) {
                this.playFallbackSound();
                return;
            }
            
            if (this.audioContext.state === 'suspended') {
                this.audioContext.resume();
            }
            
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();
            
            oscillator.type = 'sine';
            oscillator.frequency.value = frequency;
            
            gainNode.gain.setValueAtTime(0.0001, this.audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.3, this.audioContext.currentTime + 0.02);
            gainNode.gain.exponentialRampToValueAtTime(0.0001, this.audioContext.currentTime + duration / 1000);
            
            oscillator.connect(gainNode).connect(this.audioContext.destination);
            oscillator.start();
            oscillator.stop(this.audioContext.currentTime + duration / 1000);
            
            console.log('Alert sound played successfully');
        } catch (error) {
            console.log('Audio context error, using fallback:', error);
            this.playFallbackSound();
        }
    }
    
    playFallbackSound() {
        // Create a short beep using data URI
        try {
            const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEALQAAAFQBAAACABAAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhASE=');
            audio.volume = 0.3;
            audio.play().then(() => {
                console.log('Fallback sound played successfully');
            }).catch(err => {
                console.log('Fallback sound failed:', err);
            });
        } catch (error) {
            console.log('All audio methods failed:', error);
        }
    }
    
    handleAlertTriggered(alert) {
        if (!this.isAlertOn(alert.asset_id)) return;
        
        console.log('Alert triggered:', alert);
        
        // Play sound
        this.playAlertSound();
        
        // Flash the row
        this.flashRow(alert.asset_id);
        
        // Start countdown
        this.startCountdown(alert.asset_id, 60);
        
        // Show notification
        this.showNotification(alert);
    }
    
    flashRow(assetId) {
        const row = document.querySelector(`[data-asset-id="${assetId}"]`);
        if (row) {
            row.classList.add('flash');
            setTimeout(() => row.classList.remove('flash'), 2000);
        }
    }
    
    startCountdown(assetId, seconds = 60) {
        let remaining = seconds;
        const button = document.querySelector(`[data-id="${assetId}"]`);
        if (!button) return;
        
        let countdown = button.parentElement.querySelector('.countdown');
        if (!countdown) {
            countdown = document.createElement('div');
            countdown.className = 'countdown';
            button.parentElement.appendChild(countdown);
        }
        
        const timer = setInterval(() => {
            remaining--;
            countdown.textContent = remaining + 'ث';
            
            if (remaining > seconds * 0.6) {
                countdown.className = 'countdown green';
            } else if (remaining > seconds * 0.3) {
                countdown.className = 'countdown yellow';
            } else {
                countdown.className = 'countdown red';
            }
            
            if (remaining <= 0) {
                clearInterval(timer);
                countdown.textContent = 'انتهى';
                setTimeout(() => countdown.remove(), 2000);
            }
        }, 1000);
        
        countdown.textContent = seconds + 'ث';
        countdown.className = 'countdown green';
    }
    
    showNotification(alert) {
        const message = `تنبيه: ${alert.asset_name}\nالسعر الحالي: ${this.formatPrice(alert.current_price, alert.asset_id)}\nالسعر المستهدف: ${alert.threshold}`;
        
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('تنبيه سعر', {
                body: message,
                icon: '/static/favicon.ico'
            });
        } else if ('Notification' in window && Notification.permission !== 'denied') {
            Notification.requestPermission().then(permission => {
                if (permission === 'granted') {
                    new Notification('تنبيه سعر', {
                        body: message,
                        icon: '/static/favicon.ico'
                    });
                }
            });
        } else {
            alert(message);
        }
    }
    
    addSignalsPanel() {
        const container = document.querySelector('.container');
        const signalsPanel = document.createElement('div');
        signalsPanel.className = 'signals-panel';
        signalsPanel.innerHTML = `
            <div class="card signals-card">
                <h4>🔔 إشارات الصفقات المباشرة</h4>
                <div id="signals-list">لا توجد إشارات حتى الآن...</div>
                <button id="test-signal-btn" class="test-btn">اختبار إشارة</button>
            </div>
        `;
        container.insertBefore(signalsPanel, container.firstChild);
        
        // Add test signal button handler
        document.getElementById('test-signal-btn').addEventListener('click', () => {
            // Test audio immediately when button is clicked
            this.playAlertSound({ frequency: 1000, duration: 500 });
            this.socket.emit('test_signal', { asset_id: 'BTCUSDT' });
        });
    }
    
    handleTradingSignal(signal) {
        console.log('Trading signal received:', signal);
        
        // Play sound for signal
        this.playAlertSound({ frequency: signal.type === 'BUY' ? 1000 : 600, duration: 300 });
        
        // Add to signals list
        this.addSignalToList(signal);
        
        // Show notification
        const message = `🚨 إشارة ${signal.type}\n${signal.asset_name}\nالسعر: ${this.formatPrice(signal.price, signal.asset_id)}\nالثقة: ${signal.confidence}%\n${signal.reason}`;
        
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(`إشارة ${signal.type} - ${signal.asset_name}`, {
                body: message,
                icon: '/static/favicon.ico'
            });
        }
        
        // Start countdown for signal
        this.startSignalCountdown(signal.asset_id, 60);
    }
    
    addSignalToList(signal) {
        const signalsList = document.getElementById('signals-list');
        
        // Create signal element
        const signalElement = document.createElement('div');
        signalElement.className = `signal-item ${signal.type.toLowerCase()}`;
        signalElement.setAttribute('data-asset-id', signal.asset_id);
        signalElement.innerHTML = `
            <div class="signal-header">
                <span class="signal-type ${signal.type.toLowerCase()}">${signal.type}</span>
                <span class="signal-asset">${signal.asset_name}</span>
                <span class="signal-confidence">${signal.confidence}%</span>
            </div>
            <div class="signal-details">
                <div class="signal-price">السعر: ${this.formatPrice(signal.price, signal.asset_id)}</div>
                <div class="signal-reason">${signal.reason}</div>
                <div class="signal-time">${new Date(signal.timestamp * 1000).toLocaleTimeString('ar-SA')}</div>
            </div>
        `;
        
        // Remove "no signals" message if exists
        if (signalsList.textContent.includes('لا توجد إشارات')) {
            signalsList.innerHTML = '';
        }
        
        // Add to top of list
        signalsList.insertBefore(signalElement, signalsList.firstChild);
        
        // Keep only last 5 signals
        while (signalsList.children.length > 5) {
            signalsList.removeChild(signalsList.lastChild);
        }
        
        // Flash animation
        signalElement.classList.add('flash');
        setTimeout(() => signalElement.classList.remove('flash'), 2000);
    }
    
    startSignalCountdown(assetId, seconds = 60) {
        const signalElement = document.querySelector(`[data-asset-id="${assetId}"]`);
        if (!signalElement) return;
        
        let remaining = seconds;
        let countdown = signalElement.querySelector('.signal-countdown');
        
        if (!countdown) {
            countdown = document.createElement('div');
            countdown.className = 'signal-countdown';
            signalElement.appendChild(countdown);
        }
        
        const timer = setInterval(() => {
            remaining--;
            countdown.textContent = `⏰ ${remaining}ث`;
            
            if (remaining > seconds * 0.6) {
                countdown.className = 'signal-countdown green';
            } else if (remaining > seconds * 0.3) {
                countdown.className = 'signal-countdown yellow';
            } else {
                countdown.className = 'signal-countdown red';
            }
            
            if (remaining <= 0) {
                clearInterval(timer);
                countdown.textContent = '⌛ انتهى';
                setTimeout(() => countdown.remove(), 3000);
            }
        }, 1000);
        
        countdown.textContent = `⏰ ${seconds}ث`;
        countdown.className = 'signal-countdown green';
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    new TradingDashboard();
});
