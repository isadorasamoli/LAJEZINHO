import os
from flask import Flask, jsonify
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "🎮 Bot da Liga de Jogos Eletrônicos está ativo e operacional!", 200

@app.route('/health')
def health_check():
    return jsonify({
        "status": "online",
        "service": "discord-ticket-bot",
        "league": "Liga Acadêmica de Jogos Eletrônicos"
    }), 200

def run():
    # O Render injeta automaticamente a porta na variável de ambiente PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    """Inicia o Flask em background sem bloquear o loop do Discord."""
    server_thread = Thread(target=run)
    server_thread.daemon = True
    server_thread.start()