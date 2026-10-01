# ==============================================================================
# BOT DE SUPORTE - LIGA ACADÊMICA DE JOGOS ELETRÔNICOS
# ==============================================================================
import os
import discord
from discord.ext import commands
import google.generativeai as genai
from dotenv import load_dotenv

# Importa o mini-servidor Flask para manter o bot online no Render
from keep_alive import keep_alive

# Carrega variáveis de ambiente do arquivo .env em desenvolvimento local
load_dotenv()

# ------------------------------------------------------------------------------
# 1. CARREGAMENTO E VALIDAÇÃO DAS VARIÁVEIS DE AMBIENTE
# ------------------------------------------------------------------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TARGET_CHANNEL_NAME = os.getenv("CANAL_SUPORTE", "suporte").lower()
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

if not DISCORD_TOKEN:
    raise ValueError("ERRO: A variável de ambiente DISCORD_TOKEN não foi configurada!")

if not GEMINI_API_KEY:
    raise ValueError("ERRO: A variável de ambiente GEMINI_API_KEY não foi configurada!")

# ------------------------------------------------------------------------------
# 2. CONFIGURAÇÃO DA IA GEMINI (GOOGLE GENERATIVE AI)
# ------------------------------------------------------------------------------
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

model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    generation_config=generation_config,
    system_instruction=SYSTEM_INSTRUCTION
)

# ------------------------------------------------------------------------------
# 3. CONFIGURAÇÃO DO BOT DISCORD (INTENTS)
# ------------------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True  # OBRIGATÓRIO: Habilitar no Developer Portal
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ------------------------------------------------------------------------------
# 4. EVENTOS DO DISCORD
# ------------------------------------------------------------------------------
@bot.event
async def on_ready():
    print("=" * 60)
    print(f"🤖 Bot online como: {bot.user.name} (ID: {bot.user.id})")
    print(f"📡 Monitorando canal: #{TARGET_CHANNEL_NAME}")
    print(f"🧠 Modelo Gemini ativo: {MODEL_NAME}")
    print("=" * 60)
    
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="dúvidas em #suporte | Liga de Jogos"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)


@bot.event
async def on_message(message: discord.Message):
    # Ignora mensagens de outros bots ou enviadas pelo próprio bot
    if message.author.bot:
        return

    # Processa comandos normais com prefixo (!)
    await bot.process_commands(message)

    # Verifica se a mensagem foi enviada no canal #suporte (fora de threads)
    if isinstance(message.channel, discord.TextChannel) and message.channel.name.lower() == TARGET_CHANNEL_NAME:
        try:
            print(f"\n📩 Novo ticket recebido de: {message.author.display_name}")
            
            # 1. Cria um título resumido para a Thread
            preview = message.clean_content.strip().replace("\n", " ")
            if len(preview) > 35:
                preview = preview[:35] + "..."
            elif len(preview) == 0:
                preview = "Chamado com Anexo"
            
            thread_title = f"🎫 Ticket: {message.author.display_name} - {preview}"

            # 2. Cria a Thread a partir da mensagem enviada
            thread = await message.create_thread(
                name=thread_title,
                auto_archive_duration=1440,  # 24 horas de inatividade
                reason=f"Ticket aberto por {message.author.name}"
            )

            # 3. Mostra status de digitação enquanto o Gemini processa
            async with thread.typing():
                prompt_context = (
                    f"O membro @{message.author.display_name} (ID: {message.author.id}) "
                    f"enviou a seguinte mensagem no canal de suporte:\n\n"
                    f"\"{message.clean_content}\""
                )
                
                response = model.generate_content(prompt_context)
                resposta_ia = response.text.strip() if response.text else (
                    "Olá! Seu ticket foi registrado. A diretoria da Liga vai analisar seu caso em breve!"
                )

            # 4. Envia a resposta dentro da Thread com um Embed formatado
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
                    "• Se tiver prints de código, logs de console ou arte, envie nesta thread.\n"
                    "• Um diretor ou mentor técnico responderá em breve.\n"
                    "• Quando finalizado, use `!fechar` para trancar o ticket."
                ),
                inline=False
            )
            embed.set_footer(text="Atendimento automatizado · Powered by Google Gemini AI")

            await thread.send(content=f"👋 Olá {message.author.mention}, seja bem-vindo ao seu ticket!", embed=embed)
            print("🚀 Atendimento enviado com sucesso na Thread!")

        except discord.Forbidden:
            print("❌ ERRO: O bot não tem permissão para criar Threads ou enviar mensagens!")
        except Exception as e:
            print(f"❌ ERRO ao gerar atendimento: {e}")


# ------------------------------------------------------------------------------
# 5. COMANDOS EXTRAS PARA A LIGA
# ------------------------------------------------------------------------------
@bot.command(name="fechar", aliases=["fecharticket", "close"])
async def fechar_ticket(ctx: commands.Context):
    """Comando para moderadores/membros arquivarem a thread após resolução."""
    if isinstance(ctx.channel, discord.Thread):
        embed = discord.Embed(
            title="🔒 Ticket Finalizado",
            description=f"Ticket marcado como resolvido por {ctx.author.mention}. Thread arquivada.",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        await ctx.channel.edit(locked=True, archived=True)
    else:
        await ctx.send("⚠️ Este comando só pode ser utilizado dentro de uma Thread de ticket!", delete_after=5)


@bot.command(name="faq")
async def faq_gamedev(ctx: commands.Context):
    """Atalhos úteis de documentações para a Liga."""
    embed = discord.Embed(
        title="📚 FAQ Rápido - Desenvolvimento de Jogos",
        description="Links oficiais recomendados pela Liga Acadêmica de Jogos Eletrônicos:",
        color=discord.Color.green()
    )
    embed.add_field(name="Godot Engine", value="[Docs Oficiais](https://docs.godotengine.org/)", inline=True)
    embed.add_field(name="Unity Learn", value="[Tutoriais](https://learn.unity.com/)", inline=True)
    embed.add_field(name="Blender 3D", value="[Manual](https://docs.blender.org/manual/)", inline=True)
    await ctx.send(embed=embed)


# ------------------------------------------------------------------------------
# 6. INICIALIZAÇÃO
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    print("🌐 Iniciando servidor Flask keep_alive...")
    keep_alive()

    print("🚀 Conectando ao Discord...")
    bot.run(DISCORD_TOKEN)