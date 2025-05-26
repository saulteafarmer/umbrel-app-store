// API base URL
const API_BASE = '/api';

// State
let botRunning = false;
let configLoaded = false;

// DOM Elements
const configForm = document.getElementById('config-form');
const startBtn = document.getElementById('start-btn');
const stopBtn = document.getElementById('stop-btn');
const testBtn = document.getElementById('test-btn');
const refreshLogsBtn = document.getElementById('refresh-logs');
const logsContent = document.getElementById('logs-content');
const botStatus = document.getElementById('bot-status');
const configStatus = document.getElementById('config-status');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    checkBotStatus();
    setInterval(checkBotStatus, 5000); // Check status every 5 seconds
});

// Tab switching
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(`${tabName}-tab`).classList.add('active');
    event.target.classList.add('active');
    
    // Load logs if logs tab is selected
    if (tabName === 'logs') {
        loadLogs();
    }
}

// Load configuration
async function loadConfig() {
    try {
        const response = await fetch(`${API_BASE}/config`);
        const config = await response.json();
        
        if (config.configured) {
            configStatus.textContent = 'Configured';
            configStatus.className = 'status-value running';
            
            // Populate form fields (except sensitive ones)
            Object.keys(config).forEach(key => {
                const field = document.getElementById(key);
                if (field && key !== 'discord_token' && key !== 'lnbits_api_key') {
                    field.value = config[key];
                }
            });
        } else {
            configStatus.textContent = 'Not Configured';
            configStatus.className = 'status-value stopped';
        }
        
        configLoaded = true;
    } catch (error) {
        console.error('Error loading config:', error);
        showNotification('Error loading configuration', 'error');
    }
}

// Check bot status
async function checkBotStatus() {
    try {
        const response = await fetch(`${API_BASE}/bot/status`);
        const status = await response.json();
        
        botRunning = status.running;
        updateBotControls();
        
        if (status.running) {
            botStatus.textContent = 'Running';
            botStatus.className = 'status-value running';
        } else {
            botStatus.textContent = 'Stopped';
            botStatus.className = 'status-value stopped';
        }
    } catch (error) {
        console.error('Error checking bot status:', error);
    }
}

// Update bot control buttons
function updateBotControls() {
    startBtn.disabled = botRunning;
    stopBtn.disabled = !botRunning;
}

// Save configuration
configForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(configForm);
    const config = Object.fromEntries(formData);
    
    try {
        const response = await fetch(`${API_BASE}/config`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showNotification('Configuration saved successfully!', 'success');
            loadConfig();
        } else {
            showNotification(result.error || 'Error saving configuration', 'error');
        }
    } catch (error) {
        console.error('Error saving config:', error);
        showNotification('Error saving configuration', 'error');
    }
});

// Test connections
testBtn.addEventListener('click', async () => {
    const formData = new FormData(configForm);
    const config = Object.fromEntries(formData);
    
    testBtn.disabled = true;
    testBtn.textContent = 'Testing...';
    
    try {
        const response = await fetch(`${API_BASE}/test-connection`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        const results = await response.json();
        
        let message = 'Test Results:\n';
        message += `Discord: ${results.discord.valid ? '✅' : '❌'} ${results.discord.message}\n`;
        message += `LNBits: ${results.lnbits.valid ? '✅' : '❌'} ${results.lnbits.message}`;
        
        showNotification(message, results.discord.valid && results.lnbits.valid ? 'success' : 'error');
    } catch (error) {
        console.error('Error testing connections:', error);
        showNotification('Error testing connections', 'error');
    } finally {
        testBtn.disabled = false;
        testBtn.textContent = 'Test Connections';
    }
});

// Start bot
startBtn.addEventListener('click', async () => {
    startBtn.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE}/bot/start`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Bot started successfully!', 'success');
            setTimeout(checkBotStatus, 1000);
        } else {
            showNotification(result.message || 'Error starting bot', 'error');
        }
    } catch (error) {
        console.error('Error starting bot:', error);
        showNotification('Error starting bot', 'error');
    } finally {
        startBtn.disabled = false;
    }
});

// Stop bot
stopBtn.addEventListener('click', async () => {
    stopBtn.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE}/bot/stop`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Bot stopped successfully!', 'success');
            setTimeout(checkBotStatus, 1000);
        } else {
            showNotification(result.message || 'Error stopping bot', 'error');
        }
    } catch (error) {
        console.error('Error stopping bot:', error);
        showNotification('Error stopping bot', 'error');
    } finally {
        stopBtn.disabled = false;
    }
});

// Load logs
async function loadLogs() {
    try {
        const response = await fetch(`${API_BASE}/logs`);
        const result = await response.json();
        
        if (result.logs) {
            logsContent.textContent = result.logs.join('');
            // Scroll to bottom
            const container = document.getElementById('logs-container');
            container.scrollTop = container.scrollHeight;
        }
    } catch (error) {
        console.error('Error loading logs:', error);
        logsContent.textContent = 'Error loading logs';
    }
}

// Refresh logs
refreshLogsBtn.addEventListener('click', loadLogs);

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type} show`;
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 5000);
}

// Auto-refresh logs if on logs tab
setInterval(() => {
    if (document.getElementById('logs-tab').classList.contains('active')) {
        loadLogs();
    }
}, 3000);
