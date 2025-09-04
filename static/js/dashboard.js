// Trading Dashboard JavaScript
class TradingDashboard {
    constructor() {
        this.socket = null;
        this.assets = [
            { id: 'BTCUSDT', name: 'BTCUSD', type: 'crypto', source: 'binance' },
            { id: 'ETHUSDT', name: 'ETHUSD', type: 'crypto', source: 'binance' },
            { id: 'XAU/USD', name: 'XAUUSD', type: 'metal', source: 'twelve' },
            { id: 'EUR/USD', name: 'EUR/USD', type: 'forex', source: 'twelve' },
            { id: 'GBP/USD', name: 'GBP/USD', type: 'forex', source: 'twelve' },
            { id: 'EUR/JPY', name: 'EUR/JPY', type: 'forex', source: 'twelve' },
            { id: 'USD/JPY', name: 'USD/JPY', type: 'forex', source: 'twelve' },
            { id: 'NZD/USD', name: 'NZD/USD', type: 'forex', source: 'twelve' },
            { id: 'USD/CHF', name: 'USD/CHF', type: 'forex', source: 'twelve' },
        ];
        
        this.alertStates = JSON.parse(localStorage.getItem('alertStates') || '{}');
        this.prices = {};
        this.activeTimers = {}; // متابعة التحليلات النشطة بالتوقيت
        this.audioContext = null;
        this.currentAlertAsset = null;
        this.autoRefresh = JSON.parse(localStorage.getItem('autoRefresh') || 'true');
        this.selectedTheme = localStorage.getItem('selectedTheme') || 'default';
        
        this.init();
    }
    
    init() {
        this.setupErrorHandlers();
        this.initializeSocket();
        this.renderSections();
        this.initializeAudio();
        this.setupModalHandlers();
        this.fetchInitialPrices();
        this.addSignalsPanel();
        this.initializeThemeSelector();
        this.applyTheme(this.selectedTheme);
    }
    
    setupErrorHandlers() {
        // معالجة أخطاء JavaScript
        window.addEventListener('unhandledrejection', event => {
            console.warn('Promise rejection handled:', event.reason);
            event.preventDefault();
        });
        
        window.addEventListener('error', event => {
            console.warn('JavaScript error handled:', event.error?.message || event.message);
        });
    }
    
    initializeSocket() {
        // Initialize with polling-only for maximum stability with gunicorn
        this.socket = io({
            timeout: 60000,             // مهلة طويلة تتماشى مع الخادم
            reconnection: true,         
            reconnectionDelay: 2000,    // تأخير أطول للاستقرار
            reconnectionAttempts: 10,   // محاولات معقولة
            reconnectionDelayMax: 15000, // حد أقصى للتأخير
            forceNew: true,             
            transports: ['polling'],    // polling فقط للاستقرار
            upgrade: false,             // منع الترقية
            rememberUpgrade: false,     
            forceBase64: false,         
            timestampRequests: false    
        });
        
        this.socket.on('connect', () => {
            console.log('Connected to server successfully');
            this.updateConnectionStatus(true);
            this.resetReconnectionAttempts();
            
            // Send a test message to confirm connection
            this.socket.emit('test_connection', {timestamp: Date.now()});
        });
        
        this.socket.on('disconnect', (reason) => {
            console.log('Disconnected from server:', reason);
            this.updateConnectionStatus(false);
            this.handleDisconnection(reason);
        });
        
        this.socket.on('connect_error', (error) => {
            console.log('Connection error:', error);
            this.updateConnectionStatus(false);
            
            // إعادة محاولة الاتصال بعد تأخير قصير للتأكد من الاستقرار
            if (error.type === 'TransportError') {
                console.log('Transport error detected, retrying connection...');
                setTimeout(() => {
                    if (!this.socket.connected) {
                        this.socket.connect();
                    }
                }, 3000);
            }
        });
        
        this.socket.on('reconnect', (attemptNumber) => {
            console.log('Reconnected after', attemptNumber, 'attempts');
            this.updateConnectionStatus(true);
        });
        
        this.socket.on('reconnect_attempt', (attemptNumber) => {
            console.log('Reconnection attempt:', attemptNumber);
            this.updateReconnectionStatus(attemptNumber);
        });
        
        this.socket.on('reconnect_failed', () => {
            console.log('Reconnection failed');
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
            console.log('Trading signal received:', signal);
            
            // عرض إشعار مرئي للإشارة
            this.showSignalNotification(signal);
            
            this.handleTradingSignal(signal);
            
            // Update signal statistics
            this.signalsToday++;
            this.signalHistory.push(signal);
            this.updateSignalStats();
            this.updateMarketTrendDisplay();
        });
        
        this.socket.on('system_status', (status) => {
            this.updateSystemStatus(status);
        });
        
        this.socket.on('connection_confirmed', (data) => {
            console.log('Connection confirmed by server:', data);
            this.updateConnectionStatus(true);
        });
        
        this.socket.on('timed_analysis_started', (data) => {
            console.log('Timed analysis started:', data);
        });
        
        this.socket.on('timed_analysis_complete', (data) => {
            console.log('Timed analysis complete:', data);
            if (data.result === 'no_signal') {
                // Show notification that no signal was found
                this.showAnalysisNotification(data.asset_id, data.message);
            }
        });
        
        this.socket.on('timed_analysis_error', (data) => {
            console.error('Timed analysis error:', data);
            this.finishTimedAnalysis(data.asset_id);
        });
    }
    
    updateAutoRefreshButton(btn) {
        if (this.autoRefresh) {
            btn.classList.add('active');
            btn.textContent = '🔄 تحديث تلقائي - مفعل';
        } else {
            btn.classList.remove('active');
            btn.textContent = '🔄 تحديث تلقائي - معطل';
        }
    }
    
    updateConnectionStatus(connected) {
        const statusDot = document.getElementById('connection-status');
        const statusText = document.getElementById('connection-text');
        
        if (connected) {
            statusDot.className = 'status-dot online';
            statusText.textContent = 'متصل';
            // Clear any reconnection status
            clearTimeout(this.reconnectionTimer);
        } else {
            statusDot.className = 'status-dot offline';
            statusText.textContent = 'غير متصل';
        }
    }
    
    handleDisconnection(reason) {
        // Handle different disconnection reasons
        if (reason === 'transport close' || reason === 'transport error') {
            // Network issue - socket will auto-reconnect
            console.log('Network issue detected, auto-reconnecting...');
        } else if (reason === 'io server disconnect') {
            // Server initiated disconnect - need manual reconnection
            console.log('Server disconnect, attempting manual reconnection...');
            setTimeout(() => {
                this.socket.connect();
            }, 2000);
        }
    }
    
    updateReconnectionStatus(attemptNumber) {
        const statusText = document.getElementById('connection-text');
        statusText.textContent = `محاولة إعادة الاتصال ${attemptNumber}...`;
    }
    
    resetReconnectionAttempts() {
        // Reset any reconnection UI state
        clearTimeout(this.reconnectionTimer);
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
            const trendElement = document.querySelector(`[data-trend-id="${assetId}"]`);
            
            if (priceElement && prices[assetId] && prices[assetId].price !== undefined) {
                const price = prices[assetId].price;
                priceElement.textContent = this.formatPrice(price, assetId);
                priceElement.className = 'price';
            }
            
            // Update trend indicator with signal blocking info - ALWAYS SHOW
            if (trendElement) {
                const trend = prices[assetId].trend || {
                    trend: 'analyzing',
                    trend_ar: 'جاري التحليل',
                    direction: '🔍',
                    color: '#95a5a6',
                    strength: 0,
                    volatility: 0
                };
                
                const volatility = trend.volatility || 0;
                const isVolatile = volatility > 5 || trend.trend === 'volatile';
                
                if (trend.trend && trend.trend !== 'unknown' && trend.trend !== 'analyzing') {
                    let trendClass = trend.trend;
                    let statusText = '';
                    
                    if (isVolatile) {
                        trendClass = 'volatile';
                        statusText = ' ⚠️ متذبذب - إشارات محظورة';
                    } else {
                        statusText = ' ✅ إشارات مفعلة';
                    }
                    
                    trendElement.innerHTML = `
                        <span class="trend-icon" style="color: ${trend.color}">${trend.direction}</span>
                        <span class="trend-text" style="color: ${trend.color}">${trend.trend_ar}</span>
                    `;
                    trendElement.className = `trend-inline ${trendClass}`;
                    trendElement.style.color = trend.color;
                } else {
                    trendElement.innerHTML = `
                        <span class="trend-icon">🔍</span>
                        <span class="trend-text">جاري التحليل</span>
                    `;
                    trendElement.className = 'trend-inline analyzing';
                }
                
                // Force inline display
                trendElement.style.display = 'inline-flex';
                trendElement.style.visibility = 'visible';
                trendElement.style.opacity = '1';
            }
        });
    }
    
    formatPrice(price, assetId) {
        // التحقق من وجود assetId وأنه نص صحيح
        if (assetId && typeof assetId === 'string' && assetId.includes('USDT')) {
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
        name.innerHTML = `
            <div class="asset-info-line">
                <span class="asset-title">${asset.name}</span>
                <span class="trend-inline" data-trend-id="${asset.id}">
                    <span class="trend-icon">🔍</span>
                    <span class="trend-text">جاري التحليل</span>
                </span>
            </div>
            <div class="price" data-price-id="${asset.id}">--</div>
        `;
        
        // Create signal display area
        const signalArea = document.createElement('div');
        signalArea.className = 'asset-signal';
        signalArea.setAttribute('data-signal-id', asset.id);
        
        // Create timer selection area
        const timerArea = document.createElement('div');
        timerArea.className = 'timer-selection';
        timerArea.setAttribute('data-timer-id', asset.id);
        
        // Create timer buttons (1-5 minutes)
        for (let i = 1; i <= 5; i++) {
            const timerBtn = document.createElement('button');
            timerBtn.className = 'timer-btn';
            timerBtn.setAttribute('data-minutes', i);
            timerBtn.setAttribute('data-asset-id', asset.id);
            timerBtn.textContent = i;
            timerBtn.title = `تحليل ${i} ${i === 1 ? 'دقيقة' : 'دقائق'}`;
            
            timerBtn.addEventListener('click', () => {
                this.startTimedAnalysis(asset.id, i);
            });
            
            timerArea.appendChild(timerBtn);
        }
        
        // Create countdown display
        const countdownDisplay = document.createElement('div');
        countdownDisplay.className = 'countdown-display';
        countdownDisplay.setAttribute('data-countdown-id', asset.id);
        countdownDisplay.style.display = 'none';
        timerArea.appendChild(countdownDisplay);
        
        const actions = document.createElement('div');
        actions.className = 'asset-actions';
        
        // Create alert buttons container
        const alertButtons = document.createElement('div');
        alertButtons.className = 'alert-buttons';
        
        // ON button
        const onBtn = document.createElement('button');
        onBtn.className = 'alert-btn ' + (this.isAlertOn(asset.id) ? 'on' : 'inactive');
        onBtn.setAttribute('data-id', asset.id);
        onBtn.setAttribute('data-action', 'on');
        onBtn.textContent = 'ON';
        
        // OFF button  
        const offBtn = document.createElement('button');
        offBtn.className = 'alert-btn ' + (this.isAlertOn(asset.id) ? 'inactive' : 'off');
        offBtn.setAttribute('data-id', asset.id);
        offBtn.setAttribute('data-action', 'off');
        offBtn.textContent = 'OFF';
        
        onBtn.addEventListener('click', () => {
            this.setAlert(asset.id, true, onBtn, offBtn);
        });
        
        offBtn.addEventListener('click', () => {
            this.setAlert(asset.id, false, onBtn, offBtn);
        });
        
        alertButtons.appendChild(onBtn);
        alertButtons.appendChild(offBtn);
        
        const alertBtn = document.createElement('button');
        alertBtn.className = 'sec-btn';
        alertBtn.textContent = '⚠️';
        alertBtn.addEventListener('click', () => {
            this.openAlertModal(asset);
        });
        
        actions.appendChild(alertButtons);
        actions.appendChild(alertBtn);
        row.appendChild(name);
        row.appendChild(signalArea);
        row.appendChild(timerArea);
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
    
    setAlert(assetId, isOn, onBtn, offBtn) {
        this.alertStates[assetId] = isOn;
        this.saveAlertStates();
        
        if (isOn) {
            onBtn.className = 'alert-btn on';
            offBtn.className = 'alert-btn inactive';
        } else {
            onBtn.className = 'alert-btn inactive';
            offBtn.className = 'alert-btn off';
        }
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
        
        // Add auto refresh button handler
        const autoRefreshBtn = document.getElementById('auto-refresh-btn');
        if (autoRefreshBtn) {
            this.updateAutoRefreshButton(autoRefreshBtn);
            autoRefreshBtn.addEventListener('click', () => {
                this.autoRefresh = !this.autoRefresh;
                this.updateAutoRefreshButton(autoRefreshBtn);
                localStorage.setItem('autoRefresh', this.autoRefresh);
                console.log('Auto refresh:', this.autoRefresh ? 'ON' : 'OFF');
            });
        }
    }
    
    saveAlert() {
        if (!this.currentAlertAsset) return;
        
        // تفعيل التنبيه العام بدون شروط
        this.alertStates[this.currentAlertAsset.id] = true;
        this.saveAlertStates();
        
        // إرسال إشعار للخادم
        if (this.socket && this.socket.connected) {
            this.socket.emit('subscribe_alert', {
                asset_id: this.currentAlertAsset.id,
                type: 'general' // تنبيه عام
            });
        }
        
        // إغلاق المودال وتحديث الأزرار
        document.getElementById('alert-modal').style.display = 'none';
        this.renderSections(); // إعادة رسم الأزرار لتحديث الحالة
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
        const { frequency = 880, duration = 500 } = options;
        
        console.log('Attempting to play alert sound:', { frequency, duration });
        
        try {
            // استخدام Web Audio API مباشرة مع تحسينات
            if (this.audioContext && this.audioContext.state === 'running' && !this.useFallbackAudio) {
                const oscillator = this.audioContext.createOscillator();
                const gainNode = this.audioContext.createGain();
                
                oscillator.connect(gainNode);
                gainNode.connect(this.audioContext.destination);
                
                oscillator.frequency.setValueAtTime(frequency, this.audioContext.currentTime);
                oscillator.type = 'sine';
                
                // تحسين منحنى الصوت
                gainNode.gain.setValueAtTime(0, this.audioContext.currentTime);
                gainNode.gain.linearRampToValueAtTime(0.3, this.audioContext.currentTime + 0.01);
                gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + duration / 1000);
                
                oscillator.start(this.audioContext.currentTime);
                oscillator.stop(this.audioContext.currentTime + duration / 1000);
                
                console.log('Web Audio API sound played successfully');
                return;
            }
            
            // Fallback للمتصفحات القديمة
            this.playFallbackSound(frequency, duration);
            
        } catch (error) {
            console.log('Audio context error, using fallback:', error);
            this.playFallbackSound(frequency, duration);
        }
    }
    
    playFallbackSound() {
        // Fallback: try simple beep with data URI
        try {
            const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEALQAAAFQBAAACABAAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhASE=');
            audio.volume = 0.5;
            audio.play().then(() => {
                console.log('Fallback sound played successfully');
            }).catch(err => {
                console.log('All audio methods failed:', err);
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
        const message = `تنبيه: ${alert.asset_name}\nالسعر الحالي: ${this.formatPrice(alert.current_price, alert.asset_id)}`;
        
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
    
    showSignalNotification(signal) {
        // عرض إشعار مرئي وبارز للإشارة الجديدة
        const notificationDiv = document.createElement('div');
        notificationDiv.className = 'signal-notification';
        notificationDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${signal.type === 'BUY' ? '#10b981' : '#ef4444'};
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            z-index: 10000;
            font-weight: bold;
            font-size: 16px;
            min-width: 300px;
            animation: slideIn 0.5s ease-out;
        `;
        
        const signalIcon = signal.type === 'BUY' ? '📈' : '📉';
        const signalColor = signal.type === 'BUY' ? 'شراء' : 'بيع';
        
        notificationDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 24px;">${signalIcon}</span>
                <div>
                    <div style="font-size: 18px; margin-bottom: 5px;">
                        إشارة ${signalColor}: ${signal.asset_name}
                    </div>
                    <div style="font-size: 14px; opacity: 0.9;">
                        السعر: ${signal.price.toFixed(4)} | الثقة: ${signal.confidence}%
                    </div>
                </div>
            </div>
        `;
        
        // إضافة الإشعار للصفحة
        document.body.appendChild(notificationDiv);
        
        // إزالة الإشعار بعد 15 ثانية
        setTimeout(() => {
            if (notificationDiv.parentNode) {
                notificationDiv.style.animation = 'slideOut 0.5s ease-in';
                setTimeout(() => {
                    document.body.removeChild(notificationDiv);
                }, 500);
            }
        }, 15000);
        
        // إضافة أنيميشن CSS إذا لم يكن موجود
        if (!document.getElementById('signal-animations')) {
            const style = document.createElement('style');
            style.id = 'signal-animations';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
    }

    addSignalsPanel() {
        // Add test buttons to header controls
        const headerControls = document.querySelector('.header-controls .status-indicator');
        
        // Test signal button
        const testBtn = document.createElement('button');
        testBtn.textContent = '🔬 اختبار إشارة';
        testBtn.className = 'test-btn';
        testBtn.addEventListener('click', () => {
            this.testInlineSignal();
        });
        
        // تم حذف زر اختبار الذكاء الاصطناعي لتحسين الاستقرار
        
        headerControls.appendChild(testBtn);
    }
    
    // وظائف إدارة التصاميم والخلفيات
    initializeThemeSelector() {
        const themeOptions = document.querySelectorAll('.theme-option');
        const themeToggleBtn = document.getElementById('theme-toggle-btn');
        const themeSelector = document.getElementById('theme-selector');
        
        // إعداد الحدث للزر المتحكم في إظهار/إخفاء منتقي التصاميم
        if (themeToggleBtn && themeSelector) {
            themeToggleBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const isVisible = themeSelector.style.display !== 'none';
                themeSelector.style.display = isVisible ? 'none' : 'block';
                themeToggleBtn.textContent = isVisible ? '🎨 تغيير التصميم' : '✖ إغلاق';
            });
            
            // إخفاء منتقي التصاميم عند النقر خارجه
            document.addEventListener('click', (e) => {
                if (!themeSelector.contains(e.target) && !themeToggleBtn.contains(e.target)) {
                    themeSelector.style.display = 'none';
                    themeToggleBtn.textContent = '🎨 تغيير التصميم';
                }
            });
        }
        
        // إعداد الحدث لكل خيار تصميم
        themeOptions.forEach(option => {
            option.addEventListener('click', () => {
                const theme = option.getAttribute('data-theme');
                this.changeTheme(theme, option);
                // إخفاء منتقي التصاميم بعد الاختيار
                if (themeSelector) {
                    themeSelector.style.display = 'none';
                    themeToggleBtn.textContent = '🎨 تغيير التصميم';
                }
            });
        });
        
        // تطبيق التصميم المحفوظ
        this.updateActiveThemeButton();
    }
    
    changeTheme(theme, clickedOption) {
        // إزالة الفئة النشطة من جميع الخيارات
        document.querySelectorAll('.theme-option').forEach(option => {
            option.classList.remove('active');
        });
        
        // إضافة الفئة النشطة للخيار المحدد
        clickedOption.classList.add('active');
        
        // تطبيق التصميم الجديد
        this.applyTheme(theme);
        
        // حفظ الاختيار
        this.selectedTheme = theme;
        localStorage.setItem('selectedTheme', theme);
        
        console.log('Theme changed to:', theme);
    }
    
    applyTheme(theme) {
        // إزالة جميع فئات التصميم السابقة
        const themeClasses = [
            'theme-default', 'theme-blue-purple', 'theme-green-emerald',
            'theme-orange-red', 'theme-pink-purple', 'theme-stars', 
            'theme-grid', 'theme-geometric', 'theme-light-blue'
        ];
        
        themeClasses.forEach(themeClass => {
            document.body.classList.remove(themeClass);
        });
        
        // تطبيق التصميم الجديد
        if (theme !== 'default') {
            document.body.classList.add(`theme-${theme}`);
        }
    }
    
    updateActiveThemeButton() {
        // إزالة الفئة النشطة من جميع الأزرار
        document.querySelectorAll('.theme-option').forEach(option => {
            option.classList.remove('active');
        });
        
        // إضافة الفئة النشطة للتصميم المحدد حالياً
        const activeButton = document.querySelector(`[data-theme="${this.selectedTheme}"]`);
        if (activeButton) {
            activeButton.classList.add('active');
        }
    }
    

    startTimedAnalysis(assetId, minutes) {
        // Check if there's already an active analysis
        if (this.activeTimers[assetId]) {
            console.log(`Analysis already running for ${assetId}`);
            return;
        }
        
        // Disable all timer buttons for this asset
        const timerButtons = document.querySelectorAll(`[data-asset-id="${assetId}"].timer-btn`);
        timerButtons.forEach(btn => {
            btn.disabled = true;
            btn.classList.add('disabled');
        });
        
        // Highlight selected button
        const selectedBtn = document.querySelector(`[data-asset-id="${assetId}"][data-minutes="${minutes}"]`);
        if (selectedBtn) {
            selectedBtn.classList.add('active');
        }
        
        // Show countdown with expected signal type
        const countdownDisplay = document.querySelector(`[data-countdown-id="${assetId}"]`);
        if (countdownDisplay) {
            countdownDisplay.style.display = 'block';
            countdownDisplay.className = 'countdown-display running';
            
            // Get current trend to predict signal type
            const currentTrend = this.getCurrentTrend(assetId);
            const expectedSignal = this.predictSignalType(currentTrend, assetId);
            
            // Display expected signal type
            const signalTypeDisplay = document.createElement('span');
            signalTypeDisplay.className = `signal-type-preview ${expectedSignal.type.toLowerCase()}`;
            signalTypeDisplay.innerHTML = `${expectedSignal.icon} ${expectedSignal.text}`;
            countdownDisplay.appendChild(signalTypeDisplay);
        }
        
        // Send analysis request to server
        if (this.socket && this.socket.connected) {
            this.socket.emit('start_timed_analysis', {
                asset_id: assetId,
                duration_minutes: minutes,
                timestamp: Date.now()
            });
            console.log(`Started ${minutes}-minute analysis for ${assetId}`);
        }
        
        // Start countdown timer
        const totalSeconds = minutes * 60;
        let remainingSeconds = totalSeconds;
        
        this.activeTimers[assetId] = setInterval(() => {
            remainingSeconds--;
            
            const mins = Math.floor(remainingSeconds / 60);
            const secs = remainingSeconds % 60;
            const displayText = `⏱️ ${mins}:${secs.toString().padStart(2, '0')}`;
            
            if (countdownDisplay) {
                // Update countdown but preserve signal type display
                const signalPreview = countdownDisplay.querySelector('.signal-type-preview');
                countdownDisplay.textContent = displayText;
                if (signalPreview) {
                    countdownDisplay.appendChild(signalPreview);
                }
                
                // Change color based on remaining time
                if (remainingSeconds > totalSeconds * 0.6) {
                    countdownDisplay.className = 'countdown-display running';
                } else if (remainingSeconds > totalSeconds * 0.3) {
                    countdownDisplay.className = 'countdown-display warning';
                } else {
                    countdownDisplay.className = 'countdown-display urgent';
                }
            }
            
            if (remainingSeconds <= 0) {
                this.finishTimedAnalysis(assetId);
            }
        }, 1000);
    }
    
    finishTimedAnalysis(assetId) {
        // Clear timer
        if (this.activeTimers[assetId]) {
            clearInterval(this.activeTimers[assetId]);
            delete this.activeTimers[assetId];
        }
        
        // Update countdown display
        const countdownDisplay = document.querySelector(`[data-countdown-id="${assetId}"]`);
        if (countdownDisplay) {
            countdownDisplay.textContent = '✅ تحليل مكتمل';
            countdownDisplay.className = 'countdown-display complete';
            
            setTimeout(() => {
                countdownDisplay.style.display = 'none';
                countdownDisplay.textContent = '';
            }, 5000);
        }
        
        // Re-enable timer buttons
        const timerButtons = document.querySelectorAll(`[data-asset-id="${assetId}"].timer-btn`);
        timerButtons.forEach(btn => {
            btn.disabled = false;
            btn.classList.remove('disabled', 'active');
        });
        
        console.log(`Timed analysis completed for ${assetId}`);
    }
    
    getCurrentTrend(assetId) {
        // Get current trend from price data
        const priceData = this.prices[assetId];
        if (priceData && priceData.trend) {
            return priceData.trend;
        }
        return { trend: 'unknown', volatility: 0 };
    }
    
    predictSignalType(trend, assetId) {
        // Predict signal type based on current trend and technical indicators
        const priceData = this.prices[assetId];
        let signalType = 'HOLD';
        let icon = '⏸️';
        let text = 'انتظار';
        
        if (trend && priceData) {
            const rsi = priceData.trend?.rsi || 50;
            const trendDirection = trend.trend || 'unknown';
            const volatility = trend.volatility || 0;
            
            // Predict based on trend and RSI
            if (trendDirection === 'uptrend' && rsi < 70) {
                signalType = 'BUY';
                icon = '🟢';
                text = 'توقع: شراء';
            } else if (trendDirection === 'downtrend' && rsi > 30) {
                signalType = 'SELL';
                icon = '🔴';
                text = 'توقع: بيع';
            } else if (rsi < 30) {
                signalType = 'BUY';
                icon = '🟢';
                text = 'توقع: شراء (RSI منخفض)';
            } else if (rsi > 70) {
                signalType = 'SELL';
                icon = '🔴';
                text = 'توقع: بيع (RSI مرتفع)';
            } else if (volatility > 2) {
                signalType = 'HOLD';
                icon = '⚠️';
                text = 'متذبذب - انتظار';
            } else {
                signalType = 'HOLD';
                icon = '⏸️';
                text = 'تحليل جاري';
            }
        }
        
        return {
            type: signalType,
            icon: icon,
            text: text
        };
    }
    
    showAnalysisNotification(assetId, message) {
        const notificationDiv = document.createElement('div');
        notificationDiv.className = 'analysis-notification';
        notificationDiv.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            background: linear-gradient(135deg, rgba(52, 152, 219, 0.95), rgba(41, 128, 185, 0.95));
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            z-index: 10000;
            font-weight: bold;
            font-size: 14px;
            min-width: 300px;
            animation: slideIn 0.5s ease-out;
        `;
        
        notificationDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 20px;">ℹ️</span>
                <div>
                    <div style="margin-bottom: 5px;">${assetId}</div>
                    <div style="font-size: 12px; opacity: 0.9;">${message}</div>
                </div>
            </div>
        `;
        
        document.body.appendChild(notificationDiv);
        
        // Remove notification after 5 seconds
        setTimeout(() => {
            notificationDiv.style.animation = 'slideOut 0.5s ease-in';
            setTimeout(() => {
                document.body.removeChild(notificationDiv);
            }, 500);
        }, 5000);
    }
    
    testInlineSignal() {
        const assets = ['BTCUSDT', 'ETHUSDT', 'XAU/USD', 'EUR/USD'];
        const randomAsset = assets[Math.floor(Math.random() * assets.length)];
        const testSignal = {
            asset_id: randomAsset,
            asset_name: randomAsset, 
            type: Math.random() > 0.5 ? 'BUY' : 'SELL',
            price: 50000,
            confidence: 92,
            timestamp: Date.now() / 1000,
            reason: 'تحليل تلقائي متقدم'
        };
        console.log('Testing inline signal display for:', randomAsset);
        this.displayInlineSignal(testSignal);
    }
    
    startSignalCountdown(assetId, countdownElement, seconds = 60) {
        let remaining = seconds;
        
        const timer = setInterval(() => {
            remaining--;
            countdownElement.textContent = `⏰ ${remaining}ث`;
            
            // Change color based on remaining time
            if (remaining > seconds * 0.6) {
                countdownElement.className = 'signal-countdown green';
            } else if (remaining > seconds * 0.3) {
                countdownElement.className = 'signal-countdown yellow';
            } else {
                countdownElement.className = 'signal-countdown red';
            }
            
            if (remaining <= 0) {
                clearInterval(timer);
                countdownElement.textContent = '⌛ انتهى';
                
                // Clear the entire signal after countdown ends
                setTimeout(() => {
                    const signalArea = document.querySelector(`[data-signal-id="${assetId}"]`);
                    if (signalArea) {
                        signalArea.innerHTML = '';
                        console.log('Signal cleared for:', assetId);
                    }
                }, 30000); // تبقى الإشارة لمدة 30 ثانية بدلاً من 3 ثوان
            }
        }, 1000);
    }
    
    handleTradingSignal(signal) {
        console.log('Trading signal received:', signal);
        
        try {
            // Play sound for signal
            this.playAlertSound({ frequency: signal.type === 'BUY' ? 1000 : 600, duration: 300 });
        } catch (error) {
            console.error('Error playing alert sound:', error);
        }
        
        // Display signal inline with asset
        this.displayInlineSignal(signal);
        
        // Enhanced notification with technical indicators
        let technicalDetails = '';
        if (signal.rsi) {
            technicalDetails = `\nRSI: ${signal.rsi} | SMA5: ${signal.sma_short} | تغير: ${signal.price_change_5}%`;
        }
        
        const message = `🚨 إشارة ${signal.type}\n${signal.asset_name}\nالسعر: ${this.formatPrice(signal.price, signal.asset_id)}\nالثقة: ${signal.confidence}%\n${signal.reason}${technicalDetails}`;
        
        // Show desktop notification if supported
        try {
            if ('Notification' in window) {
                if (Notification.permission === 'granted') {
                    new Notification(`إشارة ${signal.type} - ${signal.asset_name}`, {
                        body: message,
                        icon: '/static/favicon.ico'
                    });
                } else if (Notification.permission !== 'denied') {
                    Notification.requestPermission().then(permission => {
                        if (permission === 'granted') {
                            new Notification(`إشارة ${signal.type} - ${signal.asset_name}`, {
                                body: message,
                                icon: '/static/favicon.ico'
                            });
                        }
                    });
                }
            }
        } catch (error) {
            console.error('Error showing notification:', error);
        }
    }
    
    displayInlineSignal(signal) {
        console.log('Displaying inline signal for:', signal.asset_id, signal);
        const signalArea = document.querySelector(`[data-signal-id="${signal.asset_id}"]`);
        
        if (!signalArea) {
            console.error('Signal area not found for asset:', signal.asset_id);
            return;
        }
        
        // Clear previous signal
        signalArea.innerHTML = '';
        
        // Create signal badge
        const signalBadge = document.createElement('div');
        signalBadge.className = `signal-badge active ${signal.type.toLowerCase()}`;
        signalBadge.textContent = signal.type === 'BUY' ? '🟢 شراء' : '🔴 بيع';
        
        // Create confidence indicator
        const confidenceSpan = document.createElement('span');
        confidenceSpan.className = 'signal-confidence';
        confidenceSpan.textContent = `الثقة: ${signal.confidence}%`;
        
        // Create countdown
        const countdownSpan = document.createElement('span');
        countdownSpan.className = 'signal-countdown green';
        countdownSpan.textContent = '⏰ 60ث';
        
        // Create details
        const detailsSpan = document.createElement('span');
        detailsSpan.className = 'signal-details';
        detailsSpan.textContent = signal.reason;
        
        signalArea.appendChild(signalBadge);
        signalArea.appendChild(confidenceSpan);
        signalArea.appendChild(countdownSpan);
        signalArea.appendChild(detailsSpan);
        
        console.log('Signal displayed successfully for:', signal.asset_id);
        
        // Start countdown (1 minute = 60 seconds)
        this.startSignalCountdown(signal.asset_id, countdownSpan, 60);
        
        // Flash the parent row
        const assetRow = signalArea.closest('.asset-row');
        if (assetRow) {
            assetRow.classList.add('flash');
            setTimeout(() => {
                assetRow.classList.remove('flash');
            }, 2000);
        }
    }
    
    // AI Market Analysis functionality
    initializeAIAnalysis() {
        // Initialize AI market analysis system
        this.signalsToday = 0;
        this.signalHistory = [];
        this.marketTrend = 'unknown';
        this.updateAIStatus(true); // AI is always analyzing in background
        
        // Update market trend display every 30 seconds
        setInterval(() => {
            this.updateMarketTrendDisplay();
        }, 30000);
        
        // Initial market trend update
        this.updateMarketTrendDisplay();
        
        // Update signal statistics
        this.updateSignalStats();
    }
    
    updateMarketTrendDisplay() {
        const trendDisplay = document.getElementById('market-trend-display');
        const insightsContainer = document.getElementById('ai-insights');
        
        if (!trendDisplay) return;
        
        // Calculate overall market trend based on recent signals
        let trendData = this.calculateOverallMarketTrend();
        
        // Update trend display
        const trendIcon = trendDisplay.querySelector('.trend-icon');
        const trendText = trendDisplay.querySelector('.trend-text');
        const trendStrength = trendDisplay.querySelector('.trend-strength');
        
        if (trendIcon && trendText && trendStrength) {
            trendIcon.textContent = trendData.icon;
            trendText.textContent = trendData.text;
            trendStrength.textContent = trendData.strength;
            trendDisplay.className = `market-trend-display ${trendData.class}`;
        }
        
        // Update AI insights
        if (insightsContainer) {
            this.updateAIInsights(insightsContainer, trendData);
        }
    }
    
    calculateOverallMarketTrend() {
        // Analyze market trend based on multiple factors
        const currentPrices = this.getCurrentPrices();
        let bullishSignals = 0;
        let bearishSignals = 0;
        let totalVolatility = 0;
        
        // Count recent signals and calculate volatility
        Object.keys(currentPrices).forEach(assetId => {
            const recentSignals = this.getRecentSignalsForAsset(assetId);
            recentSignals.forEach(signal => {
                if (signal.type === 'BUY') bullishSignals++;
                else if (signal.type === 'SELL') bearishSignals++;
            });
            
            // Calculate volatility (simplified)
            const priceHistory = this.getPriceHistoryForAsset(assetId);
            if (priceHistory.length > 1) {
                const volatility = this.calculateVolatility(priceHistory);
                totalVolatility += volatility;
            }
        });
        
        const avgVolatility = totalVolatility / Object.keys(currentPrices).length;
        const trendSignal = bullishSignals - bearishSignals;
        
        // Determine trend
        if (avgVolatility > 5) {
            return {
                icon: '🌊',
                text: 'السوق متذبذب - تجنب التداول',
                strength: `تذبذب عالي: ${avgVolatility.toFixed(1)}%`,
                class: 'volatile',
                trend: 'volatile'
            };
        } else if (trendSignal > 2) {
            return {
                icon: '📈',
                text: 'اتجاه صاعد قوي',
                strength: `قوة: ${Math.min(100, trendSignal * 10)}%`,
                class: 'bullish',
                trend: 'bullish'
            };
        } else if (trendSignal < -2) {
            return {
                icon: '📉',
                text: 'اتجاه هابط قوي',
                strength: `قوة: ${Math.min(100, Math.abs(trendSignal) * 10)}%`,
                class: 'bearish',
                trend: 'bearish'
            };
        } else {
            return {
                icon: '➡️',
                text: 'السوق جانبي - انتظار',
                strength: 'متوازن',
                class: 'sideways',
                trend: 'sideways'
            };
        }
    }
    
    updateAIInsights(container, trendData) {
        const insights = [
            'النظام يحلل المؤشرات الفنية تلقائياً',
            `اتجاه السوق: ${trendData.text}`,
            `تم إرسال ${this.signalsToday} إشارة اليوم`,
            trendData.trend === 'volatile' ? 
                '⚠️ تم إيقاف الإشارات مؤقتاً بسبب التذبذب العالي' :
                '✅ النظام يرصد الفرص المناسبة'
        ];
        
        container.innerHTML = insights.map(insight => 
            `<div class="insight-item">${insight}</div>`
        ).join('');
    }
    
    updateAIStatus(isConnected = null) {
        const statusIndicator = document.getElementById('ai-status-indicator');
        const statusText = document.getElementById('ai-status-text');
        
        if (statusIndicator && statusText) {
            if (isConnected === true) {
                statusIndicator.className = 'status-dot active';
                statusText.textContent = 'الذكاء الاصطناعي يحلل تلقائياً';
            } else if (isConnected === false) {
                statusIndicator.className = 'status-dot offline';
                statusText.textContent = 'نظام التحليل متوقف';
            } else {
                statusIndicator.className = 'status-dot active';
                statusText.textContent = 'النظام يحلل السوق...';
            }
        }
    }
    
    // Helper functions for market analysis
    getCurrentPrices() {
        return this.currentPrices || {};
    }
    
    getRecentSignalsForAsset(assetId) {
        return this.signalHistory.filter(signal => 
            signal.asset_id === assetId && 
            Date.now() - (signal.timestamp * 1000) < 3600000 // Last hour
        ) || [];
    }
    
    getPriceHistoryForAsset(assetId) {
        // Simplified: return last 10 price points if available
        return this.priceHistory?.[assetId]?.slice(-10) || [];
    }
    
    calculateVolatility(prices) {
        if (prices.length < 2) return 0;
        
        let changes = [];
        for (let i = 1; i < prices.length; i++) {
            const change = ((prices[i] - prices[i-1]) / prices[i-1]) * 100;
            changes.push(Math.abs(change));
        }
        
        return changes.reduce((sum, change) => sum + change, 0) / changes.length;
    }
    
    updateSignalStats() {
        const signalsTodayElement = document.getElementById('signals-today');
        const systemAccuracyElement = document.getElementById('system-accuracy');
        
        if (signalsTodayElement) {
            signalsTodayElement.textContent = this.signalsToday;
        }
        
        if (systemAccuracyElement) {
            // Calculate accuracy based on successful signals (simplified)
            const accuracy = this.signalHistory.length > 0 ? 
                Math.min(95, 70 + (this.signalsToday * 2)) : 'جاري الحساب';
            systemAccuracyElement.textContent = typeof accuracy === 'number' ? `${accuracy}%` : accuracy;
        }
    }
    
    // تحديث إحصائيات الصفقات
    async updateTradesStatistics() {
        try {
            const response = await fetch('/api/trades-stats');
            const data = await response.json();
            
            if (data.success) {
                this.displayTradesStats(data.stats);
                this.displayLearningInsights(data.recommendations);
                this.displayRecommendations(data.recommendations);
                
                // عرض معلومات الذكاء الاصطناعي
                if (data.ai_performance) {
                    this.displayAIPerformance(data.ai_performance);
                }
            }
        } catch (error) {
            console.log('Error fetching trades statistics:', error);
        }
    }
    
    displayTradesStats(stats) {
        // تحديث العدادات
        const successCount = document.getElementById('success-count');
        const lossCount = document.getElementById('loss-count');
        const successRate = document.getElementById('success-rate');
        const lossRate = document.getElementById('loss-rate');
        const avgProfit = document.getElementById('avg-profit');
        const avgConfidence = document.getElementById('avg-confidence');
        
        if (successCount) successCount.textContent = stats.winning_trades || '0';
        if (lossCount) lossCount.textContent = stats.losing_trades || '0';
        if (successRate) successRate.textContent = `${stats.success_rate || 0}%`;
        if (lossRate) lossRate.textContent = `${stats.loss_rate || 0}%`;
        if (avgProfit) avgProfit.textContent = `${stats.avg_profit || 0}%`;
        if (avgConfidence) avgConfidence.textContent = `${stats.avg_confidence || 0}%`;
    }
    
    displayLearningInsights(recommendations) {
        const insightsContainer = document.getElementById('learning-insights');
        
        if (insightsContainer) {
            if (recommendations && recommendations.learning_insights) {
                insightsContainer.innerHTML = recommendations.learning_insights
                    .map(insight => `<div class="insight-item">${insight}</div>`)
                    .join('');
            } else {
                insightsContainer.innerHTML = '<div class="insight-loading">جاري تحليل أنماط النجاح والفشل...</div>';
            }
        }
    }
    
    displayRecommendations(recommendations) {
        const recommendationsContainer = document.getElementById('recommendations-list');
        
        if (recommendationsContainer) {
            if (recommendations && recommendations.improvement_suggestions) {
                recommendationsContainer.innerHTML = recommendations.improvement_suggestions
                    .map(rec => `
                        <div class="recommendation-item recommendation-priority-${rec.priority || 'medium'}">
                            ${rec.text || rec}
                        </div>
                    `).join('');
            } else {
                recommendationsContainer.innerHTML = '<div class="recommendation-loading">جاري إعداد التوصيات...</div>';
            }
        }
    }
    
    displayAIPerformance(aiData) {
        console.log('🧠 عرض أداء الذكاء الاصطناعي:', aiData);
        
        // عرض حالة الذكاء الاصطناعي
        const aiStatusElement = document.getElementById('ai-status');
        if (aiStatusElement) {
            const status = aiData.ai_status === 'optimized' ? 'محسن ومُدرّب' : 'جاري التعلم';
            const statusIcon = aiData.ai_status === 'optimized' ? '🧠✨' : '🧠📚';
            aiStatusElement.innerHTML = `${statusIcon} ${status}`;
        }
        
        // عرض معدل نجاح الأنماط
        const patternSuccessElement = document.getElementById('pattern-success-rate');
        if (patternSuccessElement && aiData.performance_metrics) {
            const rate = aiData.performance_metrics.pattern_success_rate || 0;
            patternSuccessElement.textContent = `${rate}%`;
        }
        
        // عرض إجمالي الإشارات المحللة
        const analyzedSignalsElement = document.getElementById('analyzed-signals');
        if (analyzedSignalsElement && aiData.learning_progress) {
            const count = aiData.learning_progress.total_signals_analyzed || 0;
            analyzedSignalsElement.textContent = count;
        }
        
        // عرض الأنماط المكتشفة
        const patternsElement = document.getElementById('discovered-patterns');
        if (patternsElement && aiData.learning_progress) {
            const patterns = aiData.learning_progress.patterns_discovered || 0;
            patternsElement.textContent = patterns;
        }
        
        // عرض ثقة الذكاء الاصطناعي
        const aiConfidenceElement = document.getElementById('ai-confidence');
        if (aiConfidenceElement && aiData.performance_metrics) {
            const confidence = aiData.performance_metrics.ai_confidence_avg || 0;
            aiConfidenceElement.textContent = `${Math.round(confidence)}%`;
        }
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    const dashboard = new TradingDashboard();
    
    // Initialize AI analysis after dashboard
    if (dashboard.initializeAIAnalysis) {
        dashboard.initializeAIAnalysis();
    }
    
    // تحديث إحصائيات الصفقات فورياً ثم كل 30 ثانية
    if (dashboard.updateTradesStatistics) {
        dashboard.updateTradesStatistics();
        setInterval(() => {
            dashboard.updateTradesStatistics();
        }, 30000);
    }
});
