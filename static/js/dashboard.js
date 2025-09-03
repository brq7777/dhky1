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
        this.audioContext = null;
        this.currentAlertAsset = null;
        this.autoRefresh = JSON.parse(localStorage.getItem('autoRefresh') || 'true');
        this.selectedTheme = localStorage.getItem('selectedTheme') || 'default';
        
        this.init();
    }
    
    init() {
        this.initializeSocket();
        this.renderSections();
        this.initializeAudio();
        this.setupModalHandlers();
        this.fetchInitialPrices();
        this.addSignalsPanel();
        this.initializeThemeSelector();
        this.applyTheme(this.selectedTheme);
    }
    
    initializeSocket() {
        // Initialize with polling-only for maximum stability
        this.socket = io({
            timeout: 30000,             // Very long timeout
            reconnection: true,         // Enable auto-reconnection
            reconnectionDelay: 2000,    // Wait longer before reconnecting
            reconnectionAttempts: Infinity, // Never stop trying
            reconnectionDelayMax: 30000, // Very long max delay
            forceNew: false,            // Reuse connection
            transports: ['polling'],    // ONLY polling for maximum stability
            upgrade: false,             // Never upgrade to websocket
            rememberUpgrade: false,     // Always use polling
            forceBase64: false,         // Use binary if possible
            timestampRequests: true     // Add timestamps to prevent caching
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
            this.handleTradingSignal(signal);
        });
        
        this.socket.on('system_status', (status) => {
            this.updateSystemStatus(status);
        });
        
        this.socket.on('connection_confirmed', (data) => {
            console.log('Connection confirmed by server:', data);
            this.updateConnectionStatus(true);
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
            
            if (priceElement) {
                const price = prices[assetId].price;
                priceElement.textContent = this.formatPrice(price, assetId);
                priceElement.className = 'price';
            }
            
            // Update trend indicator
            if (trendElement && prices[assetId].trend) {
                const trend = prices[assetId].trend;
                if (trend.trend && trend.trend !== 'unknown') {
                    trendElement.innerHTML = `
                        <span class="trend-icon" style="color: ${trend.color}">${trend.direction}</span>
                        <span class="trend-text" style="color: ${trend.color}">${trend.trend_ar}</span>
                        <span class="trend-strength">${trend.strength}%</span>
                    `;
                    trendElement.style.borderColor = trend.color;
                    trendElement.style.display = 'block';
                } else {
                    trendElement.style.display = 'none';
                }
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
        name.innerHTML = `
            <div class="asset-title">${asset.name}</div>
            <div class="price" data-price-id="${asset.id}">--</div>
            <div class="trend-indicator" data-trend-id="${asset.id}" style="display: none;"></div>
        `;
        
        // Create signal display area
        const signalArea = document.createElement('div');
        signalArea.className = 'asset-signal';
        signalArea.setAttribute('data-signal-id', asset.id);
        
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
        const { frequency = 880, duration = 180 } = options;
        
        console.log('Attempting to play alert sound:', { frequency, duration });
        
        try {
            // Use the uploaded MP3 file for all alerts
            const audio = new Audio('/static/sounds/alert.mp3');
            audio.volume = 0.8;
            audio.currentTime = 0; // Reset to beginning
            
            // Try to play immediately
            audio.play().then(() => {
                console.log('Alert sound played successfully');
            }).catch(err => {
                console.log('MP3 alert sound failed, using fallback:', err);
                this.playFallbackSound();
            });
            
        } catch (error) {
            console.log('MP3 audio error, using fallback:', error);
            this.playFallbackSound();
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
        
        // Test OpenAI button
        const testOpenAIBtn = document.createElement('button');
        testOpenAIBtn.textContent = '🤖 اختبار OpenAI';
        testOpenAIBtn.className = 'test-openai-btn';
        testOpenAIBtn.id = 'test-openai-btn';
        testOpenAIBtn.addEventListener('click', () => {
            this.testOpenAIConnection();
        });
        
        headerControls.appendChild(testBtn);
        headerControls.appendChild(testOpenAIBtn);
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
    
    testOpenAIConnection() {
        const testBtn = document.getElementById('test-openai-btn');
        if (!testBtn) return;
        
        // تعطيل الزر أثناء الاختبار
        testBtn.disabled = true;
        testBtn.textContent = '⏳ يتم الاختبار...';
        
        fetch('/api/test-openai', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(result => {
            console.log('OpenAI test result:', result);
            
            if (result.success && result.data) {
                const data = result.data;
                if (data.connected) {
                    // نجح الاختبار
                    this.showNotification(`✅ OpenAI متصل بنجاح!
النموذج: ${data.model}
الرد: ${data.test_response}
${data.message}`, 'success');
                    testBtn.textContent = '✅ متصل';
                    testBtn.style.backgroundColor = '#10b981';
                } else {
                    // فشل الاتصال
                    this.showNotification(`❌ فشل الاتصال مع OpenAI
السبب: ${data.message}`, 'error');
                    testBtn.textContent = '❌ غير متصل';
                    testBtn.style.backgroundColor = '#ef4444';
                }
            } else {
                throw new Error(result.data ? result.data.message : 'فشل الاختبار');
            }
        })
        .catch(error => {
            console.error('Error testing OpenAI:', error);
            this.showNotification(`❌ خطأ في اختبار OpenAI: ${error.message}`, 'error');
            testBtn.textContent = '❌ خطأ';
            testBtn.style.backgroundColor = '#ef4444';
        })
        .finally(() => {
            // إعادة تفعيل الزر بعد 3 ثوان
            setTimeout(() => {
                testBtn.disabled = false;
                testBtn.textContent = '🤖 اختبار OpenAI';
                testBtn.style.backgroundColor = '';
            }, 3000);
        });
    }

    testInlineSignal() {
        const assets = ['BTCUSDT', 'ETHUSDT', 'XAU/USD', 'EUR/USD'];
        const randomAsset = assets[Math.floor(Math.random() * assets.length)];
        const testSignal = {
            asset_id: randomAsset,
            asset_name: randomAsset, 
            type: Math.random() > 0.5 ? 'BUY' : 'SELL',
            price: 50000,
            confidence: 95,
            timestamp: Date.now() / 1000,
            reason: 'اختبار الإشارة'
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
                setTimeout(() => {
                    // Clear the signal after countdown ends
                    const signalArea = document.querySelector(`[data-signal-id="${assetId}"]`);
                    if (signalArea) {
                        signalArea.innerHTML = '';
                    }
                }, 3000);
            }
        }, 1000);
    }
    
    handleTradingSignal(signal) {
        console.log('Trading signal received:', signal);
        
        // Play sound for signal
        this.playAlertSound({ frequency: signal.type === 'BUY' ? 1000 : 600, duration: 300 });
        
        // Display signal inline with asset
        this.displayInlineSignal(signal);
        
        // Enhanced notification with technical indicators
        let technicalDetails = '';
        if (signal.rsi) {
            technicalDetails = `\nRSI: ${signal.rsi} | SMA5: ${signal.sma_short} | تغير: ${signal.price_change_5}%`;
        }
        
        const message = `🚨 إشارة ${signal.type}\n${signal.asset_name}\nالسعر: ${this.formatPrice(signal.price, signal.asset_id)}\nالثقة: ${signal.confidence}%\n${signal.reason}${technicalDetails}`;
        
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(`إشارة ${signal.type} - ${signal.asset_name}`, {
                body: message,
                icon: '/static/favicon.ico'
            });
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
        
        // Start countdown
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
    
    // AI Chat functionality
    initializeAIChat() {
        const aiChatInput = document.getElementById('ai-chat-input');
        const aiSendBtn = document.getElementById('ai-send-btn');
        const testOpenAIBtn = document.getElementById('test-openai-btn');
        
        if (aiChatInput && aiSendBtn) {
            // Enable/disable send button based on input
            aiChatInput.addEventListener('input', () => {
                const hasText = aiChatInput.value.trim().length > 0;
                aiSendBtn.disabled = !hasText;
            });
            
            // Send message on button click
            aiSendBtn.addEventListener('click', () => {
                this.sendAIMessage();
            });
            
            // Send message on Enter key
            aiChatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendAIMessage();
                }
            });
        }
        
        // Test OpenAI connection
        if (testOpenAIBtn) {
            testOpenAIBtn.addEventListener('click', () => {
                this.testOpenAIConnection();
            });
        }
        
        // Initial AI status check
        this.updateAIStatus();
    }
    
    async sendAIMessage() {
        const aiChatInput = document.getElementById('ai-chat-input');
        const aiSendBtn = document.getElementById('ai-send-btn');
        const typingIndicator = document.getElementById('typing-indicator');
        
        const message = aiChatInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        this.addChatMessage(message, 'user');
        
        // Clear input and disable button
        aiChatInput.value = '';
        aiSendBtn.disabled = true;
        
        // Show typing indicator
        typingIndicator.style.display = 'block';
        
        try {
            const response = await fetch('/api/ai-chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: message })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Add AI response to chat
                this.addChatMessage(result.data.message, 'ai');
            } else {
                // Add error message
                this.addChatMessage(`❌ ${result.error}`, 'error');
            }
            
        } catch (error) {
            console.error('Error sending AI message:', error);
            this.addChatMessage('❌ حدث خطأ في الاتصال مع الذكاء الاصطناعي', 'error');
        } finally {
            // Hide typing indicator
            typingIndicator.style.display = 'none';
        }
    }
    
    addChatMessage(message, type) {
        const chatMessages = document.getElementById('ai-chat-messages');
        const messageDiv = document.createElement('div');
        
        const currentTime = new Date().toLocaleTimeString('ar-SA', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        if (type === 'user') {
            messageDiv.className = 'user-message';
            messageDiv.innerHTML = `
                <div class="message-content">${message}</div>
                <div class="message-time">${currentTime}</div>
            `;
        } else if (type === 'ai') {
            messageDiv.className = 'ai-message';
            messageDiv.innerHTML = `
                <div class="message-content">${message}</div>
                <div class="message-time">${currentTime}</div>
            `;
        } else if (type === 'error') {
            messageDiv.className = 'error-message';
            messageDiv.innerHTML = `
                <div class="message-content">${message}</div>
                <div class="message-time">${currentTime}</div>
            `;
        }
        
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    async testOpenAIConnection() {
        const testBtn = document.getElementById('test-openai-btn');
        if (!testBtn) return;
        
        // Disable button during test
        testBtn.disabled = true;
        testBtn.textContent = '⏳ يتم الاختبار...';
        
        try {
            const response = await fetch('/api/test-openai', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.success && result.data.connected) {
                this.showNotification(`✅ OpenAI متصل بنجاح!`, 'success');
                testBtn.textContent = '✅ متصل';
                testBtn.style.backgroundColor = '#10b981';
                this.updateAIStatus(true);
            } else {
                this.showNotification(`❌ فشل الاتصال مع OpenAI`, 'error');
                testBtn.textContent = '❌ غير متصل';
                testBtn.style.backgroundColor = '#ef4444';
                this.updateAIStatus(false);
            }
        } catch (error) {
            console.error('Error testing OpenAI:', error);
            this.showNotification(`❌ خطأ في اختبار OpenAI`, 'error');
            testBtn.textContent = '❌ خطأ';
            testBtn.style.backgroundColor = '#ef4444';
            this.updateAIStatus(false);
        } finally {
            // Reset button after 3 seconds
            setTimeout(() => {
                testBtn.disabled = false;
                testBtn.textContent = '🤖 اختبار OpenAI';
                testBtn.style.backgroundColor = '';
            }, 3000);
        }
    }
    
    updateAIStatus(isConnected = null) {
        const statusIndicator = document.getElementById('ai-status-indicator');
        const statusText = document.getElementById('ai-status-text');
        
        if (statusIndicator && statusText) {
            if (isConnected === true) {
                statusIndicator.className = 'status-dot online';
                statusText.textContent = 'متصل';
            } else if (isConnected === false) {
                statusIndicator.className = 'status-dot offline';
                statusText.textContent = 'غير متصل';
            } else {
                // Default/unknown state
                statusIndicator.className = 'status-dot offline';
                statusText.textContent = 'جاري التحقق...';
            }
        }
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    const dashboard = new TradingDashboard();
    
    // Initialize AI chat after dashboard
    if (dashboard.initializeAIChat) {
        dashboard.initializeAIChat();
    }
});
