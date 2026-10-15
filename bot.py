# ==============================================================================
# BOT DE SUPORTE, ÁREAS E PROJETOS - LIGA ACADÊMICA DE JOGOS ELETRÔNICOS
# ==============================================================================
# Suporta Tickets com Google Gemini AI e Select Menu para Projetos da Liga
# ==============================================================================
import os
import asyncio
import discord
from discord.ext import commands
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Importa o mini-servidor Flask para manter o bot online no Render
from keep_alive import keep_alive

# Carrega variáveis de ambiente do .env
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TARGET_CHANNEL_NAME = os.getenv("CANAL_SUPORTE", "suporte").lower()
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

if not DISCORD_TOKEN:
    raise ValueError("ERRO CRÍTICO: DISCORD_TOKEN não foi configurado!")

if not GEMINI_API_KEY:
    raise ValueError("ERRO CRÍTICO: GEMINI_API_KEY não foi configurada!")

# ------------------------------------------------------------------------------
# 1. CONFIGURAÇÃO DA NOVA SDK DO GEMINI (GOOGLE-GENAI)
# ------------------------------------------------------------------------------
ai_client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = (
    "Você é o assistente virtual de suporte da Liga Acadêmica de Jogos Eletrônicos "
    "(focada em criação e desenvolvimento de jogos). Realize o primeiro atendimento aos membros. "
    "Seja amigável e direto. Categorize se o problema é de infraestrutura, "
    "dúvida técnica de gamedev (Godot, Unity, C#, GDScript, arte, áudio) ou projetos da liga. "
    "Dê uma dica prática rápida se souber, e sempre finalize dizendo que o ticket foi "
    "registrado para os mentores técnicos e diretoria."
)

# ------------------------------------------------------------------------------
# 2. CONFIGURAÇÃO DO BOT DISCORD
# ------------------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.members = True  # Necessário para gerenciar cargos dos membros

bot = commands.Bot(
    command_prefix="!", 
    intents=intents, 
    case_insensitive=True, 
    help_command=None
)

# ==============================================================================
# MAPEAMENTO OFICIAL DE CARGOS DA LIGA DE JOGOS
# ==============================================================================
# 1. Cargos de Especialidade / Área (comando: !cargos)
CARGOS_AREAS = {
    "💻": "Dev",
    "🎨": "Design",
    "🎵": "Sound",
    "✍️": "Writer"
}

# 2. Cargos de Projetos / Jogos da Liga em Ordem Alfabética (Sem emojis)
CARGOS_PROJETOS = [
    "CatCatchRat",
    "Depois do espetáculo",
    "Fronteira",
    "G.R.U.N.G.E",
    "Topo do Mundo"
]

def obter_cargo_por_emoji(emoji_str: str):
    """Verifica se o emoji pertence a uma Área de atuação."""
    clean = emoji_str.replace("\ufe0f", "")
    for e, cargo in CARGOS_AREAS.items():
        if e.replace("\ufe0f", "") == clean:
            return cargo
    return None

# ==============================================================================
# MENU DE SELEÇÃO INTERATIVO (DISCORD.UI.SELECT) PARA PROJETOS (SEM EMOJIS)
# ==============================================================================
class ProjetoSelect(discord.ui.Select):
    def __init__(self):
        # Opções do menu em ordem alfabética e sem emojis
        opcoes = [
            discord.SelectOption(
                label="CatCatchRat",
                value="CatCatchRat",
                description="Equipe do projeto CatCatchRat"
            ),
            discord.SelectOption(
                label="Depois do espetáculo",
                value="Depois do espetáculo",
                description="Equipe do projeto Depois do espetáculo"
            ),
            discord.SelectOption(
                label="Fronteira",
                value="Fronteira",
                description="Equipe do projeto Fronteira"
            ),
            discord.SelectOption(
                label="G.R.U.N.G.E",
                value="G.R.U.N.G.E",
                description="Equipe do projeto G.R.U.N.G.E"
            ),
            discord.SelectOption(
                label="Topo do Mundo",
                value="Topo do Mundo",
                description="Equipe do projeto Topo do Mundo"
            ),
        ]
        super().__init__(
            placeholder="Selecione os seus projetos aqui...",
            min_values=0,
            max_values=len(opcoes),
            options=opcoes,
            custom_id="liga_projetos_select_menu"
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user

        if not isinstance(member, discord.Member):
            member = await guild.fetch_member(interaction.user.id)

        selecionados = self.values
        adicionados = []
        removidos = []

        # Gerencia os 5 projetos oficiais da Liga
        for nome_proj in CARGOS_PROJETOS:
            role = discord.utils.find(lambda r: r.name.lower() == nome_proj.lower(), guild.roles)

            # Auto-criação do cargo se ainda não existir no Discord
            if not role:
                try:
                    role = await guild.create_role(
                        name=nome_proj,
                        color=discord.Color.teal(),
                        mentionable=True,
                        reason="Cargo de projeto criado via Select Menu da Liga"
                    )
                    print(f"✨ Cargo de projeto '{nome_proj}' criado automaticamente!")
                except discord.Forbidden:
                    await interaction.response.send_message(
                        "❌ O bot precisa da permissão 'Gerenciar Cargos' para criar os cargos de projeto!",
                        ephemeral=True
                    )
                    return

            # Adiciona os projetos selecionados no dropdown
            if nome_proj in selecionados:
                if role not in member.roles:
                    try:
                        await member.add_roles(role, reason="Projeto selecionado no Select Menu")
                        adicionados.append(nome_proj)
                    except discord.Forbidden:
                        await interaction.response.send_message(
                            "❌ Erro de hierarquia: O cargo do bot precisa estar ACIMA dos cargos de projetos!",
                            ephemeral=True
                        )
                        return
                else:
                    adicionados.append(nome_proj)
            # Remove os projetos desmarcados
            else:
                if role in member.roles:
                    try:
                        await member.remove_roles(role, reason="Projeto desmarcado no Select Menu")
                        removidos.append(nome_proj)
                    except discord.Forbidden:
                        pass

        # Resposta efêmera (apenas o membro que interagiu enxerga, chat 100% limpo!)
        if selecionados:
            lista_str = ", ".join([f"**{p}**" for p in selecionados])
            resposta = (
                f"✅ **Projetos Atualizados com Sucesso!**\n\n"
                f"Você agora faz parte da equipe de: {lista_str}.\n"
                f"🔓 *Os canais secretos e a categoria exclusiva desses projetos já estão liberados para você!*"
            )
        else:
            resposta = "ℹ️ Você desmarcou todos os projetos. Seus acessos aos canais de projetos foram removidos."

        await interaction.response.send_message(resposta, ephemeral=True)


class ProjetosView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # timeout=None para o menu nunca expirar no Render!
        self.add_item(ProjetoSelect())


# ------------------------------------------------------------------------------
# 3. EVENTOS DO BOT
# ------------------------------------------------------------------------------
@bot.event
async def on_ready():
    """Executado quando o bot se conecta com sucesso ao Discord."""
    # Registra a View persistente para que o Select Menu continue ativo mesmo após reinicializações
    bot.add_view(ProjetosView())

    print("=" * 60)
    print(f"🤖 Bot conectado como: {bot.user.name} ({bot.user.id})")
    print(f"📡 Monitorando canal de suporte: #{TARGET_CHANNEL_NAME}")
    print(f"🧠 Modelo Gemini ativo (google-genai): {MODEL_NAME}")
    print(f"🎭 Cargos de Área ativos: {list(CARGOS_AREAS.values())}")
    print(f"🎮 Projetos no Select Menu: {CARGOS_PROJETOS}")
    print("=" * 60)
    
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="dúvidas no #suporte | Liga de Jogos"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """Atribui o cargo de Área (Dev, Design, Sound, Writer) quando o membro clica na reação."""
    if payload.user_id == bot.user.id:
        return

    emoji_str = str(payload.emoji)
    nome_cargo = obter_cargo_por_emoji(emoji_str)
    if not nome_cargo:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    role = discord.utils.find(lambda r: r.name.lower() == nome_cargo.lower(), guild.roles)

    if not role:
        try:
            cores_areas = {
                "Dev": discord.Color.blue(),
                "Design": discord.Color.purple(),
                "Sound": discord.Color.green(),
                "Writer": discord.Color.gold()
            }
            cor = cores_areas.get(nome_cargo, discord.Color.blue())
            role = await guild.create_role(
                name=nome_cargo, 
                color=cor, 
                mentionable=True,
                reason="Cargo de área criado automaticamente pelo bot da Liga"
            )
            print(f"✨ Cargo de área '{nome_cargo}' criado no servidor!")
        except discord.Forbidden:
            print(f"❌ Permissão insuficiente: O bot precisa de 'Gerenciar Cargos' para criar '{nome_cargo}'.")
            return

    member = payload.member or guild.get_member(payload.user_id)
    if member and role:
        try:
            await member.add_roles(role, reason=f"Escolha de área {nome_cargo} por reação")
            print(f"✅ Cargo [{nome_cargo}] concedido a @{member.display_name}")
        except discord.Forbidden:
            print(
                f"❌ Erro de Hierarquia: O cargo do bot precisa estar POSICIONADO ACIMA "
                f"do cargo '{nome_cargo}' em Configurações do Servidor > Cargos!"
            )


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    """Remove o cargo de Área quando o membro desmarca a reação de emoji."""
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
            print(f"❌ Erro ao remover cargo '{nome_cargo}': verifique a hierarquia de cargos do bot.")


@bot.event
async def on_message(message: discord.Message):
    """Monitora mensagens para comandos e atendimento de tickets em #suporte."""
    if message.author.bot:
        return

    if message.content.strip().startswith("!"):
        await bot.process_commands(message)
        return

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
                    prompt_context = (
                        f"O membro {message.author.display_name} (ID: {message.author.id}) "
                        f"enviou a seguinte mensagem no suporte:\n\n\"{message.clean_content}\""
                    )

                    try:
                        response = await ai_client.aio.models.generate_content(
                            model=MODEL_NAME,
                            contents=prompt_context,
                            config=types.GenerateContentConfig(
                                system_instruction=SYSTEM_INSTRUCTION,
                                temperature=0.7,
                                top_p=0.95,
                                max_output_tokens=1000
                            )
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

                try:
                    await thread.send(content=f"👋 Olá {message.author.mention}, seja bem-vindo ao seu ticket!", embed=embed)
                except discord.Forbidden:
                    texto_puro = (
                        f"👋 Olá {message.author.mention}, seja bem-vindo ao seu ticket!\n\n"
                        f"**🎮 Atendimento Inicial da Liga de Jogos:**\n{resposta_ia}\n\n"
                        f"📌 **Próximos Passos:** Envie prints e logs aqui. Quando resolvido, use `!fechar`."
                    )
                    await thread.send(content=texto_puro)

            except discord.Forbidden:
                try:
                    await message.channel.send(
                        f"⚠️ {message.author.mention}, o bot precisa da permissão 'Criar Tópicos Públicos' para abrir o ticket!"
                    )
                except Exception:
                    pass
            except Exception as e:
                print(f"❌ Erro ao processar ticket: {e}")


# ------------------------------------------------------------------------------
# 4. COMANDOS ÚTEIS
# ------------------------------------------------------------------------------
@bot.command(name="projetos", aliases=["painelprojetos", "escolherprojetos"])
@commands.has_permissions(administrator=True)
async def criar_painel_projetos(ctx: commands.Context):
    """
    Cria o painel interativo com Menu de Seleção (Select Menu) para escolha de Projetos.
    Ao selecionar no menu suspenso, o membro ganha o cargo e tem acesso aos canais da equipe!
    Uso: !projetos (digite no canal desejado, ex: #escolha-seu-projeto ou #projetos)
    """
    linhas_projetos = "\n".join([
        f"• **{nome}**"
        for nome in CARGOS_PROJETOS
    ])

    embed = discord.Embed(
        title="Central de Projetos — Liga Acadêmica de Jogos",
        description=(
            "Seja bem-vindo(a) à área de desenvolvimento da **Liga Acadêmica de Jogos Eletrônicos**!\n\n"
            "Abra o **Menu de Seleção abaixo** e marque os projetos e jogos dos quais você faz parte "
            "para **liberar o acesso imediato aos canais privados e salas de reunião da sua equipe**:\n\n"
            f"{linhas_projetos}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "*(Dica: Você pode selecionar mais de um projeto ou alterar sua seleção a qualquer momento)*"
        ),
        color=discord.Color.from_rgb(46, 204, 113)  # Verde esmeralda de projetos
    )
    embed.set_footer(text="Liga Acadêmica de Jogos Eletrônicos · Menu Interativo de Equipes")

    # Envia o Embed acompanhado da View com o Menu de Seleção persistente
    await ctx.send(embed=embed, view=ProjetosView())

    try:
        await ctx.message.delete()
    except Exception:
        pass


@bot.command(name="cargos", aliases=["painelcargos", "escolhercargos"])
@commands.has_permissions(administrator=True)
async def criar_painel_cargos(ctx: commands.Context):
    """Cria a mensagem com reações para escolha de área de atuação."""
    embed = discord.Embed(
        title="🎮 Escolha sua Área na Liga Acadêmica de Jogos!",
        description=(
            "Selecione as áreas em que você atua ou tem interesse em colaborar:\n\n"
            "💻 **Dev** — Programação, Engines e Lógica\n"
            "🎨 **Design** — Arte 2D, 3D, Modelagem, UI/UX\n"
            "🎵 **Sound** — Trilha Sonora, SFX e Foley\n"
            "✍️ **Writer** — Roteiro, Narrativa e Game Design\n\n"
            "*(Reaja com o emoji correspondente para receber o cargo)*"
        ),
        color=discord.Color.from_rgb(88, 101, 242)
    )
    embed.set_footer(text="Liga Acadêmica de Jogos Eletrônicos · Sistema de Áreas")

    painel = await ctx.send(embed=embed)
    for emoji in CARGOS_AREAS.keys():
        await painel.add_reaction(emoji)

    try:
        await ctx.message.delete()
    except Exception:
        pass


@bot.command(name="ping", aliases=["teste"])
async def ping_teste(ctx: commands.Context):
    """Comando de teste rápido de latência."""
    latencia = round(bot.latency * 1000)
    await ctx.send(f"🏓 **Pong!** O bot da Liga está ativo e respondendo! (Latência: `{latencia}ms`)")


@bot.command(name="status", aliases=["mudarstatus"])
@commands.has_permissions(administrator=True)
async def mudar_status(ctx: commands.Context, tipo: str = "jogando", *, texto: str = "Criando jogos na Liga"):
    """Permite alterar o status do bot pelo chat."""
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
    await ctx.send(f"✅ Status do bot atualizado para: **{tipo.capitalize()} {texto}**")


@bot.command(name="fechar", aliases=["close"])
async def fechar_ticket(ctx: commands.Context):
    """Tranca e arquiva a thread de suporte."""
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
