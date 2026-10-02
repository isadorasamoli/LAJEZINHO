# ==============================================================================
# BOT DE SUPORTE - LIGA ACADÊMICA DE JOGOS ELETRÔNICOS
# ==============================================================================
import os
import asyncio
import discord
from discord.ext import commands
import google.generativeai as genai
from dotenv import load_dotenv

# Importa o servidor Flask para manter o bot online no Render
from keep_alive import keep_alive

# Carrega variáveis de ambiente do .env
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TARGET_CHANNEL_NAME = os.getenv("CANAL_SUPORTE", "suporte").lower()
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

if not DISCORD_TOKEN:
    raise ValueError("ERRO: DISCORD_TOKEN não foi configurado!")

if not GEMINI_API_KEY:
    raise ValueError("ERRO: GEMINI_API_KEY não foi configurada!")

# Configuração da IA Gemini
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = (
    "Você é o assistente virtual de suporte da Liga Acadêmica de Jogos Eletrônicos "
    "(focada em criação de jogos). Realize o primeiro atendimento aos membros no Discord. "
    "Seja amigável, curto. Categorize se o problema é de infraestrutura do servidor, "
    "dúvida técnica (Unity, Godot, código, arte) ou sobre os projetos da liga. "
    "Dê uma dica rápida se souber, mas sempre finalize dizendo que o ticket foi "
    "registrado e a diretoria vai analisar."
)

generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "max_output_tokens": 1000,
}

try:
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config=generation_config,
        system_instruction=SYSTEM_INSTRUCTION
    )
except Exception:
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
        system_instruction=SYSTEM_INSTRUCTION
    )

# Configuração do Bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

# case_insensitive=True: aceita !ping, !Ping, !PING
bot = commands.Bot(
    command_prefix="!", 
    intents=intents, 
    case_insensitive=True, 
    help_command=None
)

@bot.event
async def on_ready():
    print("=" * 60)
    print(f"🤖 Bot conectado como: {bot.user.name} ({bot.user.id})")
    print(f"📡 Monitorando canal: #{TARGET_CHANNEL_NAME}")
    print("=" * 60)
    
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="dúvidas no #suporte | Liga de Jogos"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)


@bot.event
async def on_message(message: discord.Message):
    # 1. Ignora mensagens enviadas por bots
    if message.author.bot:
        return

    # 2. SE FOR UM COMANDO (começa com !), executa e NÃO cria ticket!
    if message.content.strip().startswith("!"):
        await bot.process_commands(message)
        return

    # 3. Se for mensagem comum no canal de suporte, abre o ticket
    if isinstance(message.channel, discord.TextChannel):
        c_name = message.channel.name.lower()
        is_support = (c_name == TARGET_CHANNEL_NAME or TARGET_CHANNEL_NAME in c_name or str(message.channel.id) == TARGET_CHANNEL_NAME)

        if is_support:
            try:
                if not message.clean_content.strip():
                    return

                # Cria o título do Ticket
                preview = message.clean_content.strip().replace("\n", " ")
                if len(preview) > 35:
                    preview = preview[:35] + "..."
                elif len(preview) == 0:
                    preview = "Dúvida Geral"
                
                thread_title = f"🎫 Ticket: {message.author.display_name} - {preview}"
                
                # Abre a Thread no Discord
                thread = await message.create_thread(
                    name=thread_title,
                    auto_archive_duration=1440,
                    reason=f"Ticket aberto por {message.author.name}"
                )

                # Mostra o status de digitação enquanto a IA responde
                async with thread.typing():
                    prompt = f"O membro {message.author.display_name} enviou no suporte:\n\n\"{message.clean_content}\""

                    # Executa a chamada do Gemini de forma assíncrona para não travar o bot
                    try:
                        loop = asyncio.get_running_loop()
                        response = await loop.run_in_executor(None, lambda: model.generate_content(prompt))
                        resposta_ia = response.text.strip() if response.text else "Olá! Seu ticket foi registrado. A diretoria vai analisar em breve!"
                    except Exception as err:
                        print(f"Erro Gemini: {err}")
                        resposta_ia = f"Olá {message.author.mention}! Seu ticket foi registrado. A diretoria e os mentores técnicos foram notificados!"

                # Tenta enviar como Embed (cartão visual)
                embed = discord.Embed(
                    title="🎮 Liga Acadêmica de Jogos Eletrônicos | Atendimento",
                    description=resposta_ia,
                    color=discord.Color.from_rgb(88, 101, 242)
                )
                embed.add_field(
                    name="📌 Próximos Passos",
                    value="• Envie prints, logs ou arquivos aqui nesta thread.\n• Quando resolver, use `!fechar`.",
                    inline=False
                )

                try:
                    await thread.send(content=f"👋 Olá {message.author.mention}, seja bem-vindo ao seu ticket!", embed=embed)
                except discord.Forbidden:
                    # Se o bot não tiver permissão de Embed Links, envia como texto normal!
                    await thread.send(
                        content=f"👋 Olá {message.author.mention}!\n\n**Atendimento da Liga:**\n{resposta_ia}\n\n📌 *Quando resolvido, use `!fechar`.*"
                    )

            except discord.Forbidden:
                try:
                    await message.channel.send(f"⚠️ {message.author.mention}, o bot precisa da permissão 'Criar Tópicos Públicos' para abrir o ticket!")
                except Exception:
                    pass
            except Exception as e:
                print(f"Erro no ticket: {e}")


# ==============================================================================
# COMANDOS ÚTEIS
# ==============================================================================
@bot.command(name="ping", aliases=["teste"])
async def ping_teste(ctx: commands.Context):
    """Responde imediatamente com a latência para testar se está vivo."""
    latencia = round(bot.latency * 1000)
    await ctx.send(f"🏓 **Pong!** O bot da Liga está ativo e respondendo! (Latência: `{latencia}ms`)")


@bot.command(name="status", aliases=["mudarstatus"])
@commands.has_permissions(administrator=True)
async def mudar_status(ctx: commands.Context, tipo: str = "jogando", *, texto: str = "Criando jogos na Liga"):
    """Exemplo: !status jogando Godot 4"""
    tipo_lower = tipo.lower()
    if tipo_lower in ["jogando", "game", "play"]:
        act = discord.Game(name=texto)
    elif tipo_lower in ["assistindo", "watch"]:
        act = discord.Activity(type=discord.ActivityType.watching, name=texto)
    elif tipo_lower in ["ouvindo", "listen"]:
        act = discord.Activity(type=discord.ActivityType.listening, name=texto)
    else:
        act = discord.Activity(type=discord.ActivityType.playing, name=f"{tipo} {texto}")

    await bot.change_presence(status=discord.Status.online, activity=act)
    await ctx.send(f"✅ Status atualizado para: **{tipo.capitalize()} {texto}**")


@bot.command(name="fechar", aliases=["fecharticket", "close"])
async def fechar_ticket(ctx: commands.Context):
    """Tranca e arquiva a thread."""
    if isinstance(ctx.channel, discord.Thread):
        embed = discord.Embed(
            title="🔒 Ticket Finalizado",
            description=f"Ticket finalizado por {ctx.author.mention}. Thread arquivada.",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        await ctx.channel.edit(locked=True, archived=True)
    else:
        await ctx.send("⚠️ Este comando só pode ser usado dentro de uma Thread de ticket!", delete_after=5)


if __name__ == "__main__":
    print("🌐 Iniciando servidor Flask keep_alive...")
    keep_alive()

    print("🚀 Conectando ao Discord...")
    bot.run(DISCORD_TOKEN)
