# ==============================================================================
# BOT DE SUPORTE E CARGOS - LIGA ACADÊMICA DE JOGOS ELETRÔNICOS
# ==============================================================================
import os
import asyncio
import discord
from discord.ext import commands
import google.generativeai as genai
from dotenv import load_dotenv

# Importa o mini-servidor Flask para manter o bot online no Render
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

# ------------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DA IA GEMINI
# ------------------------------------------------------------------------------
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = (
    "Você é o assistente virtual de suporte da Liga Acadêmica de Jogos Eletrônicos "
    "(focada em criação e desenvolvimento de jogos). Realize o primeiro atendimento aos membros. "
    "Seja amigável e direto. Categorize se o problema é de infraestrutura, "
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
# 2. CONFIGURAÇÃO DO BOT DISCORD E REACTION ROLES
# ------------------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.members = True  # Necessário para adicionar/remover cargos dos membros

bot = commands.Bot(
    command_prefix="!", 
    intents=intents, 
    case_insensitive=True, 
    help_command=None
)

# Mapeamento oficial das Áreas e Emojis da Liga
CARGOS_EMOJIS = {
    "💻": "Dev",
    "🎨": "Design",
    "🎵": "Sound",
    "✍️": "Writer"
}

def obter_cargo_por_emoji(emoji_str: str):
    """Trata variações de emojis Unicode (com ou sem variação gráfica)."""
    clean = emoji_str.replace("\ufe0f", "")
    for e, cargo in CARGOS_EMOJIS.items():
        if e.replace("\ufe0f", "") == clean:
            return cargo
    return None

# ------------------------------------------------------------------------------
# 3. EVENTOS DO BOT
# ------------------------------------------------------------------------------
@bot.event
async def on_ready():
    print("=" * 60)
    print(f"🤖 Bot conectado como: {bot.user.name} ({bot.user.id})")
    print(f"📡 Monitorando canal de suporte: #{TARGET_CHANNEL_NAME}")
    print(f"🎭 Cargos por reação ativados: {list(CARGOS_EMOJIS.values())}")
    print("=" * 60)
    
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="dúvidas no #suporte | Liga de Jogos"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """Atribui o cargo quando o membro clica na reação de emoji."""
    if payload.user_id == bot.user.id:
        return

    emoji_str = str(payload.emoji)
    nome_cargo = obter_cargo_por_emoji(emoji_str)
    if not nome_cargo:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    # Procura o cargo no servidor
    role = discord.utils.find(lambda r: r.name.lower() == nome_cargo.lower(), guild.roles)

    # Se o cargo não existir, o bot cria automaticamente com cor personalizada!
    if not role:
        try:
            cores = {
                "Dev": discord.Color.blue(),
                "Design": discord.Color.purple(),
                "Sound": discord.Color.green(),
                "Writer": discord.Color.gold()
            }
            role = await guild.create_role(
                name=nome_cargo, 
                color=cores.get(nome_cargo, discord.Color.default()),
                mentionable=True,
                reason="Cargo de área criado automaticamente pelo bot da Liga"
            )
            print(f"✨ Cargo '{nome_cargo}' criado no servidor!")
        except discord.Forbidden:
            print(f"❌ Permissão insuficiente: O bot precisa de 'Gerenciar Cargos' para criar '{nome_cargo}'.")
            return

    # Adiciona o cargo ao membro
    member = payload.member or guild.get_member(payload.user_id)
    if member and role:
        try:
            await member.add_roles(role, reason=f"Escolha de área {nome_cargo} por reação")
            print(f"✅ Cargo [{nome_cargo}] concedido a @{member.display_name}")
        except discord.Forbidden:
            print(f"❌ Erro de Hierarquia: O cargo do bot precisa estar ACIMA do cargo '{nome_cargo}' em Configurações do Servidor > Cargos!")


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    """Remove o cargo quando o membro desmarca o emoji."""
    emoji_str = str(payload.emoji)
    nome_cargo = obter_cargo_por_emoji(emoji_str)
    if not nome_cargo:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    role = discord.utils.find(lambda r: r.name.lower() == nome_cargo.lower(), guild.roles)
    if not role:
        return

    member = guild.get_member(payload.user_id)
    if not member:
        try:
            member = await guild.fetch_member(payload.user_id)
        except Exception:
            return

    if member and role in member.roles:
        try:
            await member.remove_roles(role, reason=f"Remoção de área {nome_cargo} por retirada de reação")
            print(f"🗑️ Cargo [{nome_cargo}] removido de @{member.display_name}")
        except discord.Forbidden:
            print(f"❌ Erro ao remover cargo: verifique a hierarquia de cargos do bot.")


@bot.event
async def on_message(message: discord.Message):
    """Monitora mensagens para comandos e tickets no canal #suporte."""
    if message.author.bot:
        return

    # Se for comando, executa e não abre ticket
    if message.content.strip().startswith("!"):
        await bot.process_commands(message)
        return

    # Atendimento de Tickets no canal de suporte
    if isinstance(message.channel, discord.TextChannel):
        c_name = message.channel.name.lower()
        is_support = (
            c_name == TARGET_CHANNEL_NAME 
            or TARGET_CHANNEL_NAME in c_name 
            or str(message.channel.id) == TARGET_CHANNEL_NAME
        )

        if is_support:
            try:
                if not message.clean_content.strip():
                    return

                preview = message.clean_content.strip().replace("\n", " ")
                if len(preview) > 35:
                    preview = preview[:35] + "..."
                elif len(preview) == 0:
                    preview = "Dúvida Geral"
                
                thread_title = f"🎫 Ticket: {message.author.display_name} - {preview}"
                
                thread = await message.create_thread(
                    name=thread_title,
                    auto_archive_duration=1440,
                    reason=f"Ticket aberto por {message.author.name}"
                )

                async with thread.typing():
                    prompt = f"O membro {message.author.display_name} enviou no suporte:\n\n\"{message.clean_content}\""

                    try:
                        loop = asyncio.get_running_loop()
                        response = await loop.run_in_executor(None, lambda: model.generate_content(prompt))
                        resposta_ia = response.text.strip() if response.text else "Olá! Seu ticket foi registrado. A diretoria vai analisar em breve!"
                    except Exception as gemini_err:
                        print(f"Erro Gemini: {gemini_err}")
                        resposta_ia = f"Olá {message.author.mention}! Seu ticket foi registrado. A diretoria e os mentores técnicos foram notificados!"

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


# ------------------------------------------------------------------------------
# 4. COMANDOS ÚTEIS
# ------------------------------------------------------------------------------
@bot.command(name="cargos", aliases=["painelcargos", "escolhercargos"])
@commands.has_permissions(administrator=True)
async def criar_painel_cargos(ctx: commands.Context):
    """
    Cria a mensagem com as reações de emoji para os membros escolherem sua área.
    Uso: !cargos (digite no canal desejado, ex: #cargos ou #boas-vindas)
    """
    embed = discord.Embed(
        title="🎮 Escolha sua Área na Liga Acadêmica de Jogos!",
        description=(
            "Seja muito bem-vindo(a) à **Liga Acadêmica de Jogos Eletrônicos**!\n\n"
            "Selecione as áreas em que você atua ou tem interesse em aprender e colaborar "
            "em nossas Game Jams, projetos e workshops.\n\n"
            "**Clique no emoji correspondente abaixo para receber seu cargo:**\n\n"
            "💻 **Dev** — Programação, Engines (Godot, Unity, Unreal), C#, GDScript, Python e Lógica\n\n"
            "🎨 **Design** — Arte 2D, Arte 3D, Modelagem (Blender), Animação, Pixel Art e UI/UX\n\n"
            "🎵 **Sound** — Trilha Sonora, Composição Musical, Efeitos Sonoros (SFX) e Foley\n\n"
            "✍️ **Writer** — Roteiro, Narrativa, Diálogos, Worldbuilding e Game Design\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "*(Dica: Você pode escolher mais de uma área e pode remover a reação quando quiser para retirar o cargo)*"
        ),
        color=discord.Color.from_rgb(88, 101, 242)
    )
    embed.set_footer(text="Liga Acadêmica de Jogos Eletrônicos · Sistema de Cargos")

    painel = await ctx.send(embed=embed)

    # O bot adiciona os 4 emojis automaticamente na mensagem
    for emoji in CARGOS_EMOJIS.keys():
        await painel.add_reaction(emoji)

    try:
        await ctx.message.delete()
    except Exception:
        pass


@bot.command(name="ping", aliases=["teste"])
async def ping_teste(ctx: commands.Context):
    """Comando de teste rápido de conexão."""
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
    elif tipo_lower in ["competindo", "jam"]:
        act = discord.Activity(type=discord.ActivityType.competing, name=texto)
    else:
        act = discord.Activity(type=discord.ActivityType.playing, name=f"{tipo} {texto}")

    await bot.change_presence(status=discord.Status.online, activity=act)
    await ctx.send(f"✅ Status atualizado para: **{tipo.capitalize()} {texto}**")


@bot.command(name="fechar", aliases=["close"])
async def fechar_ticket(ctx: commands.Context):
    """Tranca e arquiva a Thread de suporte."""
    if isinstance(ctx.channel, discord.Thread):
        embed = discord.Embed(
            title="🔒 Ticket Finalizado",
            description=f"Ticket finalizado por {ctx.author.mention}. Thread arquivada.",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        await ctx.channel.edit(locked=True, archived=True)
    else:
        await ctx.send("⚠️ Este comando só pode ser utilizado dentro de uma Thread de ticket!", delete_after=5)


@bot.command(name="faq")
async def faq_gamedev(ctx: commands.Context):
    """Exibe links úteis de desenvolvimento."""
    embed = discord.Embed(
        title="📚 Recursos Úteis da Liga de Jogos",
        description="Links oficiais das principais engines recomendadas pela Liga:",
        color=discord.Color.teal()
    )
    embed.add_field(name="Godot Engine", value="[Documentação Oficial](https://docs.godotengine.org/)", inline=True)
    embed.add_field(name="Unity Learn", value="[Tutoriais Unity](https://learn.unity.com/)", inline=True)
    embed.add_field(name="Blender 3D", value="[Manual do Blender](https://docs.blender.org/manual/)", inline=True)
    embed.set_footer(text="Liga Acadêmica de Jogos Eletrônicos")
    await ctx.send(embed=embed)


# ------------------------------------------------------------------------------
# 5. INICIALIZAÇÃO
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    print("🌐 Iniciando servidor Flask keep_alive...")
    keep_alive()

    print("🚀 Conectando ao Discord...")
    bot.run(DISCORD_TOKEN)
