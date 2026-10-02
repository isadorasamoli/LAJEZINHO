# ==============================================================================
# BOT DE SUPORTE - LIGA ACADÊMICA DE JOGOS ELETRÔNICOS
# ==============================================================================
import os
import asyncio
import discord
from discord.ext import commands
import google.generativeai as genai
from dotenv import load_dotenv

# Importa o mini-servidor Flask para manter o bot acordado no Render 24/7
from keep_alive import keep_alive

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# ------------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DAS VARIÁVEIS DE AMBIENTE
# ------------------------------------------------------------------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TARGET_CHANNEL_NAME = os.getenv("CANAL_SUPORTE", "suporte").lower()
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

if not DISCORD_TOKEN:
    raise ValueError("ERRO CRÍTICO: DISCORD_TOKEN não foi configurado!")

if not GEMINI_API_KEY:
    raise ValueError("ERRO CRÍTICO: GEMINI_API_KEY não foi configurada!")

# ------------------------------------------------------------------------------
# 2. CONFIGURAÇÃO DA IA GEMINI (GOOGLE GENERATIVE AI)
# ------------------------------------------------------------------------------
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = (
    "Você é o assistente virtual de suporte da Liga Acadêmica de Jogos Eletrônicos "
    "(focada em criação e desenvolvimento de jogos). Realize o primeiro atendimento aos membros. "
    "Seja amigável e direto. Categorize se o problema é de infraestrutura do servidor, "
    "dúvida técnica de gamedev (Godot, Unity, C#, GDScript, arte, áudio) ou projetos da liga. "
    "Dê uma dica prática rápida se souber, e sempre finalize dizendo que o ticket foi "
    "registrado para os mentores técnicos e diretoria."
)

generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "max_output_tokens": 1000,
}

def get_generative_model(model_name=MODEL_NAME):
    try:
        return genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            system_instruction=SYSTEM_INSTRUCTION
        )
    except Exception as e:
        print(f"⚠️ Erro ao inicializar {model_name}: {e}. Usando modelo de fallback...")
        return genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
            system_instruction=SYSTEM_INSTRUCTION
        )

model = get_generative_model()

# ------------------------------------------------------------------------------
# 3. CONFIGURAÇÃO DO BOT DISCORD
# ------------------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True  # Obrigatório habilitar no Discord Developer Portal
intents.guilds = True
intents.messages = True

# case_insensitive=True: aceita !ping, !Ping, !PING sem erros
bot = commands.Bot(
    command_prefix="!", 
    intents=intents, 
    case_insensitive=True, 
    help_command=None
)

# ------------------------------------------------------------------------------
# 4. EVENTOS DO BOT
# ------------------------------------------------------------------------------
@bot.event
async def on_ready():
    """Executado quando o bot se conecta com sucesso ao Discord."""
    print("=" * 60)
    print(f"🤖 Bot conectado como: {bot.user.name} ({bot.user.id})")
    print(f"📡 Monitorando canal: #{TARGET_CHANNEL_NAME}")
    print(f"🧠 Modelo Gemini ativo: {MODEL_NAME}")
    print("=" * 60)
    
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="dúvidas no #suporte | Liga de Jogos"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)


@bot.event
async def on_message(message: discord.Message):
    """
    Monitora todas as mensagens do servidor.
    Se for no canal 'suporte' e não for um bot nem comando, cria uma Thread e responde via Gemini.
    """
    # 1. Ignora mensagens enviadas pelo próprio bot ou por outros bots
    if message.author.bot:
        return

    # 2. Log de diagnóstico no terminal / Render
    channel_name = getattr(message.channel, "name", "Thread/DM")
    print(f"[DEBUG] Mensagem de @{message.author.name} em #{channel_name}: '{message.clean_content[:50]}'")

    # 3. CRÍTICO: Se a mensagem começar com '!', é um comando e NÃO deve virar ticket!
    if message.content.strip().startswith("!"):
        await bot.process_commands(message)
        return

    # 4. Verifica se a mensagem foi enviada no canal de texto de suporte
    if isinstance(message.channel, discord.TextChannel):
        c_name = message.channel.name.lower()
        is_support = (
            c_name == TARGET_CHANNEL_NAME 
            or TARGET_CHANNEL_NAME in c_name 
            or str(message.channel.id) == TARGET_CHANNEL_NAME
        )

        if is_support:
            try:
                print(f"\n📩 Novo ticket no canal #{message.channel.name} por @{message.author.display_name}")

                if not message.clean_content.strip():
                    return

                # Cria um título amigável e resumido para a Thread
                preview = message.clean_content.strip().replace("\n", " ")
                if len(preview) > 35:
                    preview = preview[:35] + "..."
                elif len(preview) == 0:
                    preview = "Dúvida Geral"
                
                thread_title = f"🎫 Ticket: {message.author.display_name} - {preview}"
                
                # Cria a Thread vinculada à mensagem do autor
                thread = await message.create_thread(
                    name=thread_title,
                    auto_archive_duration=1440,
                    reason=f"Ticket aberto por {message.author.name}"
                )
                print(f"✅ Thread criada com sucesso: '{thread.name}' (ID: {thread.id})")

                # Exibe o status de digitando enquanto a IA processa
                async with thread.typing():
                    prompt_context = (
                        f"O membro {message.author.display_name} (ID: {message.author.id}) "
                        f"enviou a seguinte mensagem no suporte:\n\n\"{message.clean_content}\""
                    )

                    # Executa a geração em thread assíncrona para não travar o loop do bot
                    try:
                        loop = asyncio.get_running_loop()
                        response = await loop.run_in_executor(
                            None, 
                            lambda: model.generate_content(prompt_context)
                        )
                        resposta_ia = response.text.strip() if response.text else (
                            "Olá! Seu ticket foi registrado com sucesso. Nossa diretoria "
                            "vai analisar a sua solicitação em breve!"
                        )
                    except Exception as gemini_err:
                        print(f"⚠️ Erro ao consultar Gemini AI: {gemini_err}")
                        resposta_ia = (
                            f"Olá {message.author.mention}! Seu ticket foi registrado no sistema da Liga Acadêmica de Jogos 🎮.\n\n"
                            "Nossa diretoria e mentores técnicos foram notificados e responderão aqui em breve."
                        )

                # Monta o cartão Embed oficial da Liga
                embed = discord.Embed(
                    title="🎮 Liga Acadêmica de Jogos Eletrônicos | Atendimento Inicial",
                    description=resposta_ia,
                    color=discord.Color.from_rgb(88, 101, 242)
                )
                embed.set_author(
                    name=f"Atendimento: {message.author.display_name}",
                    icon_url=message.author.display_avatar.url if message.author.display_avatar else None
                )
                embed.add_field(
                    name="📌 Próximos Passos",
                    value=(
                        "• Se tiver prints de código, logs de erro ou arte, envie aqui nesta thread.\n"
                        "• Um mentor ou membro da diretoria responderá em breve.\n"
                        "• Quando o problema for resolvido, use `!fechar`."
                    ),
                    inline=False
                )
                embed.set_footer(text="Sistema de Tickets Automatizado · Liga de Jogos")

                # Envia na Thread (com fallback para texto puro se faltar permissão de Embed Links)
                try:
                    await thread.send(content=f"👋 Olá {message.author.mention}, seja bem-vindo ao seu ticket!", embed=embed)
                    print("🚀 Atendimento enviado com sucesso na Thread!")
                except discord.Forbidden:
                    print("⚠️ Permissão 'Inserir Links' ausente. Enviando como texto normal...")
                    texto_puro = (
                        f"👋 Olá {message.author.mention}, seja bem-vindo ao seu ticket!\n\n"
                        f"**🎮 Atendimento Inicial da Liga de Jogos:**\n{resposta_ia}\n\n"
                        f"📌 **Próximos Passos:** Envie prints e logs aqui. Quando resolvido, use `!fechar`."
                    )
                    await thread.send(content=texto_puro)

            except discord.Forbidden as perm_err:
                print(f"❌ ERRO DE PERMISSÃO no canal #{message.channel.name}: {perm_err}")
                try:
                    await message.channel.send(
                        f"⚠️ {message.author.mention}, o bot precisa da permissão **'Criar Tópicos Públicos'** "
                        "e **'Enviar Mensagens em Tópicos'** para abrir o seu ticket!"
                    )
                except Exception:
                    pass
            except Exception as e:
                print(f"❌ ERRO AO PROCESSAR TICKET: {e}")


# ------------------------------------------------------------------------------
# 5. COMANDOS ÚTEIS ADICIONAIS
# ------------------------------------------------------------------------------
@bot.command(name="ping", aliases=["teste"])
async def ping_teste(ctx: commands.Context):
    """Comando de teste rápido para saber se o bot está ouvindo mensagens."""
    latencia = round(bot.latency * 1000)
    try:
        await ctx.send(f"🏓 **Pong!** O bot da Liga está ativo e respondendo! (Latência: `{latencia}ms`)")
    except discord.Forbidden:
        print(f"❌ Sem permissão para enviar mensagens no canal #{ctx.channel.name}")
    except Exception as e:
        print(f"❌ Erro no comando ping: {e}")


@bot.command(name="diagnostico")
async def diagnostico_servidor(ctx: commands.Context):
    """Exibe o status do canal e permissões do bot."""
    canal_ok = TARGET_CHANNEL_NAME in ctx.channel.name.lower()
    perms = ctx.channel.permissions_for(ctx.guild.me)
    msg = (
        f"📊 **Diagnóstico do Bot na Liga:**\n"
        f"• Canal atual: `#{ctx.channel.name}` (Canal esperado: `{TARGET_CHANNEL_NAME}`)\n"
        f"• Reconhecido como canal de suporte: {'✅ SIM' if canal_ok else '❌ NÃO'}\n"
        f"• Permissão 'Criar Tópicos': {'✅' if perms.create_public_threads else '❌ FALTA PERMISSÃO'}\n"
        f"• Permissão 'Enviar Mensagens em Tópicos': {'✅' if perms.send_messages_in_threads else '❌ FALTA PERMISSÃO'}\n"
        f"• Permissão 'Inserir Links': {'✅' if perms.embed_links else '❌ FALTA PERMISSÃO'}"
    )
    await ctx.send(msg)


@bot.command(name="status", aliases=["mudarstatus", "setstatus"])
@commands.has_permissions(administrator=True)
async def mudar_status(ctx: commands.Context, tipo: str = "jogando", *, texto: str = "Criando jogos na Liga"):
    """
    Permite à diretoria alterar o status do bot pelo chat do Discord.
    Exemplos:
      !status jogando Godot Engine 4
      !status assistindo dúvidas no #suporte
      !status competindo na Game Jam da Liga
    """
    tipo_lower = tipo.lower()
    if tipo_lower in ["jogando", "game", "play"]:
        activity = discord.Game(name=texto)
    elif tipo_lower in ["assistindo", "watch"]:
        activity = discord.Activity(type=discord.ActivityType.watching, name=texto)
    elif tipo_lower in ["ouvindo", "listen"]:
        activity = discord.Activity(type=discord.ActivityType.listening, name=texto)
    elif tipo_lower in ["competindo", "jam"]:
        activity = discord.Activity(type=discord.ActivityType.competing, name=texto)
    else:
        activity = discord.Activity(type=discord.ActivityType.playing, name=f"{tipo} {texto}")

    await bot.change_presence(status=discord.Status.online, activity=activity)
    await ctx.send(f"✅ Status do bot atualizado para: **{tipo.capitalize()} {texto}**")


@bot.command(name="fechar", aliases=["fecharticket", "close"])
async def fechar_ticket(ctx: commands.Context):
    """Tranca e arquiva a Thread de suporte quando finalizada."""
    if isinstance(ctx.channel, discord.Thread):
        embed = discord.Embed(
            title="🔒 Ticket Finalizado",
            description=f"Este ticket foi marcado como resolvido por {ctx.author.mention}. A thread será trancada e arquivada.",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        await ctx.channel.edit(locked=True, archived=True)
    else:
        await ctx.send("⚠️ Este comando só pode ser utilizado dentro de uma Thread de ticket!", delete_after=5)


@bot.command(name="faq")
async def faq_gamedev(ctx: commands.Context):
    """Exibe links úteis e documentações para a Liga de Jogos."""
    embed = discord.Embed(
        title="📚 Recursos Úteis da Liga de Jogos",
        description="Confira os links oficiais das principais engines recomendadas pela Liga:",
        color=discord.Color.teal()
    )
    embed.add_field(name="Godot Engine", value="[Documentação Oficial](https://docs.godotengine.org/)", inline=True)
    embed.add_field(name="Unity Learn", value="[Tutoriais Unity](https://learn.unity.com/)", inline=True)
    embed.add_field(name="Blender 3D", value="[Manual do Blender](https://docs.blender.org/manual/)", inline=True)
    embed.set_footer(text="Liga Acadêmica de Jogos Eletrônicos")
    await ctx.send(embed=embed)


# ------------------------------------------------------------------------------
# 6. INICIALIZAÇÃO
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    print("🌐 Iniciando servidor Flask keep_alive...")
    keep_alive()

    print("🚀 Conectando ao Discord...")
    bot.run(DISCORD_TOKEN)
