# ==============================================================================
# KEEP_ALIVE.PY - SERVIDOR FLASK COM PÁGINAS LEGAIS PARA O DISCORD
# ==============================================================================
import os
from flask import Flask, jsonify
from threading import Thread

app = Flask(__name__)

BASE_STYLE = """
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0f1117;
    color: #e2e8f0;
    line-height: 1.6;
    margin: 0;
    padding: 2rem 1rem;
"""

CARD_STYLE = """
    max-width: 760px;
    margin: 0 auto;
    background: #181a20;
    border: 1px solid #2b2d31;
    border-radius: 12px;
    padding: 2.5rem;
    box-shadow: 0 8px 30px rgba(0,0,0,0.5);
"""

@app.route('/')
def home():
    """Página raiz para monitoramento e links legais do Discord."""
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
        <head>
            <meta charset="utf-8">
            <title>Lajezinho · Bot da Liga Acadêmica de Jogos Eletrônicos</title>
            <style>
                body {{ {BASE_STYLE} display: flex; justify-content: center; align-items: center; min-height: 90vh; }}
                .card {{ {CARD_STYLE} text-align: center; }}
                h1 {{ color: #5865F2; margin-top: 0; font-size: 1.8rem; }}
                .status {{ color: #22c55e; font-weight: 600; margin: 1rem 0; }}
                .links {{ margin-top: 2rem; display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap; }}
                .btn {{ background: #2b2d31; color: #fff; text-decoration: none; padding: 0.6rem 1.2rem; border-radius: 8px; font-size: 0.9rem; border: 1px solid #3f4147; }}
                .btn:hover {{ background: #5865F2; border-color: #5865F2; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>🎮 Lajezinho</h1>
                <p>Bot Oficial da <strong>Liga Acadêmica de Jogos Eletrônicos</strong></p>
                <p class="status">● Status: Operacional e Ativo 24/7</p>
                <p style="color: #94a3b8; font-size: 0.9rem;">Atendimento automatizado com Google Gemini AI e gestão de cargos por reação.</p>
                <div class="links">
                    <a class="btn" href="/termos">📜 Termos de Serviço</a>
                    <a class="btn" href="/privacidade">🛡️ Política de Privacidade</a>
                </div>
            </div>
        </body>
    </html>
    """, 200

@app.route('/termos')
@app.route('/terms')
def termos():
    """Página oficial de Termos de Serviço para o Discord Developer Portal."""
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
        <head>
            <meta charset="utf-8">
            <title>Termos de Serviço · Lajezinho Bot</title>
            <style>
                body {{ {BASE_STYLE} }}
                .container {{ {CARD_STYLE} }}
                h1 {{ color: #5865F2; border-bottom: 1px solid #2b2d31; padding-bottom: 0.8rem; }}
                h2 {{ color: #93c5fd; font-size: 1.15rem; margin-top: 1.8rem; }}
                p, li {{ color: #cbd5e1; font-size: 0.95rem; }}
                a {{ color: #60a5fa; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                .footer {{ margin-top: 2.5rem; border-top: 1px solid #2b2d31; padding-top: 1rem; font-size: 0.85rem; color: #64748b; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <p><a href="/">← Voltar para a página inicial</a></p>
                <h1>📜 Termos de Serviço</h1>
                <p><strong>Aplicação:</strong> Lajezinho (Bot de Discord)<br>
                <strong>Entidade:</strong> Liga Acadêmica de Jogos Eletrônicos<br>
                <strong>Última atualização:</strong> Outubro de 2026</p>

                <h2>1. Aceitação dos Termos</h2>
                <p>Ao interagir com o bot <strong>Lajezinho</strong> ("o Bot") em qualquer servidor do Discord, você concorda com estes Termos de Serviço. O Bot é um assistente comunitário sem fins lucrativos da Liga Acadêmica de Jogos Eletrônicos.</p>

                <h2>2. Descrição dos Serviços</h2>
                <p>O Bot oferece as seguintes funções aos membros da Liga:</p>
                <ul>
                    <li>Abertura automática de Threads de suporte (Tickets) no canal <code>#suporte</code>.</li>
                    <li>Triagem inicial e dicas rápidas de desenvolvimento de jogos com inteligência artificial (Google Gemini).</li>
                    <li>Atribuição voluntária de cargos por reação de emojis (<code>💻 Dev</code>, <code>🎨 Design</code>, <code>🎵 Sound</code>, <code>✍️ Writer</code>) através do comando <code>!cargos</code>.</li>
                    <li>Comandos utilitários (<code>!ping</code>, <code>!faq</code>, <code>!status</code>, <code>!fechar</code>).</li>
                </ul>

                <h2>3. Conduta do Usuário</h2>
                <p>É estritamente proibido abusar de comandos, gerar spam no canal de suporte, tentar explorar vulnerabilidades ou enviar conteúdo ilegal que viole as Diretrizes da Comunidade do Discord.</p>

                <h2>4. Isenção de Responsabilidade</h2>
                <p>O Bot é fornecido "como está" (<em>as-is</em>), sem garantias de operação ininterrupta. A Liga Acadêmica não se responsabiliza por indisponibilidades temporárias do Discord ou da API Google Gemini.</p>

                <div class="footer">
                    Liga Acadêmica de Jogos Eletrônicos · Todos os direitos reservados.
                </div>
            </div>
        </body>
    </html>
    """, 200

@app.route('/privacidade')
@app.route('/privacy')
def privacidade():
    """Página oficial de Política de Privacidade para o Discord Developer Portal."""
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
        <head>
            <meta charset="utf-8">
            <title>Política de Privacidade · Lajezinho Bot</title>
            <style>
                body {{ {BASE_STYLE} }}
                .container {{ {CARD_STYLE} }}
                h1 {{ color: #22c55e; border-bottom: 1px solid #2b2d31; padding-bottom: 0.8rem; }}
                h2 {{ color: #86efac; font-size: 1.15rem; margin-top: 1.8rem; }}
                p, li {{ color: #cbd5e1; font-size: 0.95rem; }}
                a {{ color: #60a5fa; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                .footer {{ margin-top: 2.5rem; border-top: 1px solid #2b2d31; padding-top: 1rem; font-size: 0.85rem; color: #64748b; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <p><a href="/">← Voltar para a página inicial</a></p>
                <h1>🛡️ Política de Privacidade</h1>
                <p><strong>Aplicação:</strong> Lajezinho (Bot de Discord)<br>
                <strong>Entidade:</strong> Liga Acadêmica de Jogos Eletrônicos<br>
                <strong>Última atualização:</strong> Outubro de 2026</p>

                <h2>1. Coleta Mínima de Dados</h2>
                <p>O Bot opera sob o princípio da privacidade por design e minimização de dados. Coletamos estritamente:</p>
                <ul>
                    <li><strong>ID de Usuário e Username:</strong> para identificar o autor do chamado, criar o título do ticket e mencioná-lo na nova thread.</li>
                    <li><strong>Mensagens no Canal de Suporte:</strong> o conteúdo textual de mensagens enviadas exclusivamente no canal designado (<code>#suporte</code>) e comandos com prefixo <code>!</code>.</li>
                    <li><strong>Reações a Emojis:</strong> apenas cliques nas reações do painel de cargos oficial para atribuir ou retirar áreas.</li>
                </ul>

                <h2>2. O Que Não Coletamos</h2>
                <p>O Bot <strong>NÃO</strong> lê Mensagens Diretas (DMs), não monitora conversas de outros canais do servidor, e não coleta dados bancários, senhas, e-mails ou localização.</p>

                <h2>3. Tratamento de Dados por Inteligência Artificial</h2>
                <p>O texto das dúvidas de suporte é enviado de maneira segura via HTTPS para a API oficial do <strong>Google Gemini</strong> estritamente para formular a orientação inicial. Nenhum dado pessoal é vendido ou comercializado.</p>

                <h2>4. Retenção e Exclusão</h2>
                <p>O Bot não mantém banco de dados externo com mensagens armazenadas. As conversas residem dentro dos canais/tópicos do próprio Discord e podem ser arquivadas ou excluídas a qualquer momento pelos administradores ou com o comando <code>!fechar</code>.</p>

                <div class="footer">
                    Liga Acadêmica de Jogos Eletrônicos · Em conformidade com o Discord Developer Terms of Service.
                </div>
            </div>
        </body>
    </html>
    """, 200

@app.route('/health')
def health_check():
    """Endpoint de health check para serviços de uptime retornando JSON."""
    return jsonify({
        "status": "online",
        "service": "discord-ticket-bot",
        "league": "Liga Acadêmica de Jogos Eletrônicos"
    }), 200

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    """Inicia o servidor Flask em background sem travar o loop principal do Discord."""
    server_thread = Thread(target=run)
    server_thread.daemon = True
    server_thread.start()
