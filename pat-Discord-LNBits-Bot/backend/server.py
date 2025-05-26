from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import subprocess
import threading
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configuration
DATA_DIR = os.environ.get('APP_DATA_DIR', '/app/data')
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')
LOG_FILE = os.path.join(DATA_DIR, 'bot.log')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# Bot process management
bot_process = None
bot_thread = None

def run_bot():
    """Run the Discord bot in a subprocess"""
    global bot_process
    try:
        bot_process = subprocess.Popen(
            ['python', 'backend/bot.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Stream output to log
        for line in bot_process.stdout:
            logging.info(f"BOT: {line.strip()}")
            
    except Exception as e:
        logging.error(f"Error running bot: {e}")
    finally:
        if bot_process:
            bot_process.wait()
            logging.info(f"Bot process ended with code: {bot_process.returncode}")

def start_bot():
    """Start the bot in a separate thread"""
    global bot_thread
    
    if bot_thread and bot_thread.is_alive():
        return False, "Bot is already running"
    
    if not os.path.exists(CONFIG_FILE):
        return False, "Configuration not found. Please save settings first."
    
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    return True, "Bot started successfully"

def stop_bot():
    """Stop the running bot"""
    global bot_process
    
    if bot_process and bot_process.poll() is None:
        bot_process.terminate()
        bot_process.wait(timeout=5)
        return True, "Bot stopped successfully"
    
    return False, "Bot is not running"

# Routes
@app.route('/')
def index():
    """Serve the frontend"""
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('../frontend', path)

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    response_data = {'configured': False, 'lnbits_available': False}
    
    # Check if LNBits is available
    try:
        import requests as req
        resp = req.get('http://lnbits:5000/api/v1/health', timeout=2)
        response_data['lnbits_available'] = resp.status_code == 200
    except:
        response_data['lnbits_available'] = False
    
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Don't send sensitive data to frontend
            safe_config = {k: v for k, v in config.items() if k not in ['discord_token', 'lnbits_api_key']}
            safe_config['configured'] = bool(config.get('discord_token')) and bool(config.get('lnbits_api_key'))
            response_data.update(safe_config)
    
    return jsonify(response_data)

@app.route('/api/config', methods=['POST'])
def save_config():
    """Save configuration"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['discord_token', 'guild_id', 'role_id', 
                          'lnbits_api_key', 'price', 'channelid', 'command_name']
        
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Set defaults
        data.setdefault('invoicemessage', 'Please pay this Lightning invoice to receive your role!')
        
        # Auto-configure LNBits URL for Umbrel environment
        # LNBits runs on port 5000 inside the Umbrel network
        data['lnbits_url'] = 'http://lnbits:5000'
        
        # Save configuration
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        logging.info("Configuration saved successfully")
        return jsonify({'success': True, 'message': 'Configuration saved successfully'})
        
    except Exception as e:
        logging.error(f"Error saving config: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bot/start', methods=['POST'])
def start_bot_endpoint():
    """Start the Discord bot"""
    success, message = start_bot()
    return jsonify({'success': success, 'message': message})

@app.route('/api/bot/stop', methods=['POST'])
def stop_bot_endpoint():
    """Stop the Discord bot"""
    success, message = stop_bot()
    return jsonify({'success': success, 'message': message})

@app.route('/api/bot/status', methods=['GET'])
def bot_status():
    """Get bot status"""
    is_running = bot_process and bot_process.poll() is None
    return jsonify({
        'running': is_running,
        'configured': os.path.exists(CONFIG_FILE)
    })

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get recent log entries"""
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()
                # Return last 100 lines
                recent_logs = lines[-100:]
                return jsonify({'logs': recent_logs})
        return jsonify({'logs': []})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-connection', methods=['POST'])
def test_connection():
    """Test Discord and LNBits connections"""
    data = request.json
    results = {}
    
    # Test Discord token (basic validation)
    discord_token = data.get('discord_token', '')
    results['discord'] = {
        'valid': len(discord_token) > 50 and '.' in discord_token,
        'message': 'Token format appears valid' if len(discord_token) > 50 else 'Invalid token format'
    }
    
    # Test LNBits connection
    import requests as req
    lnbits_url = 'http://lnbits:5000'  # Fixed URL for Umbrel LNBits
    lnbits_key = data.get('lnbits_api_key', '')
    
    try:
        response = req.get(
            f"{lnbits_url}/api/v1/wallet",
            headers={"X-Api-Key": lnbits_key},
            timeout=5
        )
        results['lnbits'] = {
            'valid': response.status_code == 200,
            'message': 'Connected successfully' if response.status_code == 200 else f'Error: {response.status_code}'
        }
    except Exception as e:
        results['lnbits'] = {
            'valid': False,
            'message': f'Connection failed: {str(e)}'
        }
    
    return jsonify(results)

if __name__ == '__main__':
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Start with saved config if exists
    if os.path.exists(CONFIG_FILE):
        logging.info("Found existing configuration, starting bot...")
        start_bot()
    
    # Start Flask server
    app.run(host='0.0.0.0', port=3050, debug=False)