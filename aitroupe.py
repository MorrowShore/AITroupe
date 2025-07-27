# Sample invite link: https://discord.com/oauth2/authorize?client_id=123123123123123&permissions=1126589853457472&integration_type=0&scope=bot
# Make sure you give "create webhook" permission to the bot, and some other obvious ones.

import discord
from discord.ext import commands, tasks
from discord import app_commands
import requests
import asyncio
import random
import json
from datetime import datetime, timedelta
import aiohttp

# Configuration - Change these with your stuff. You only really need one of the AI API providers. Gemini is recommended.
DISCORD_TOKEN = '123123123123123123123123123123123123123123123123123123123123'
DEEPSEEK_API_KEY = 'sk-123123123123123123123123'
CHATGPT_API_KEY = '12312321321321312312312312323213213213212312'
GEMINI_API_KEY = '123123213123123213123231323213123231223213'  
QWEN_API_KEY = '12321321321312321312323123123123213123231231231'

CHANNEL_ID = None  # You can set it, or leave it empty. You can set it using the channel command - no default required
CURRENT_AI = "gemini"  # Default AI provider (gemini is often free)

PERSONAS = [
    {
        "name": "Raven", 
        "role": "A cunning and intelligent trickster with a sharp wit. Observant and resourceful, often speaking in riddles. Represents transformation and adaptability.",
        "color": 0x000000,  
        "avatar_url": "https://cdn.discordapp.com/attachments/1103962947413356545/1397865383423119491/image.png",
        "emote": "🪶"
    },
    {
        "name": "Wolf", 
        "role": "A loyal and strong pack leader. Protective of their community, with keen instincts and strategic thinking. Represents leadership and intuition.",
        "color": 0x808080,  
        "avatar_url": "https://cdn.discordapp.com/attachments/1103962947413356545/1398902220535234610/image.png",
        "emote": "🐺"
    },
    {
        "name": "Owl", 
        "role": "The ancient sage of the forest. Patient, wise, and deeply knowledgeable. Speaks slowly with profound insight. Represents wisdom and mystery.",
        "color": 0x4B5320,  
        "avatar_url": "https://cdn.discordapp.com/attachments/1103962947413356545/1398902667241197608/image.png",
        "emote": "🦉"
    },
    {
        "name": "Fox", 
        "role": "Clever and adaptable trickster. Quick-witted and playful, but with hidden depths. Represents cunning and adaptability.",
        "color": 0xFF6600,  
        "avatar_url": "https://cdn.discordapp.com/attachments/1103962947413356545/1397864731259174912/image.png",
        "emote": "🦊"
    },
    {
        "name": "Bear", 
        "role": "Strong and protective guardian. Calm but formidable when provoked. Values strength and solitude. Represents power and introspection.",
        "color": 0x8B4513,  
        "avatar_url": "https://cdn.discordapp.com/attachments/1103962947413356545/1398901304008642690/image.png",
        "emote": "🐻"
    },
    {
        "name": "Hawk", 
        "role": "Sharp-eyed and decisive hunter. Focused and direct, with clear vision of goals. Represents clarity and purpose.",
        "color": 0x5F9EA0,  
        "avatar_url": "https://cdn.discordapp.com/attachments/1103962947413356545/1398900074511073382/image.png",
        "emote": "🦅"
    },
    {
        "name": "Snake", 
        "role": "Mysterious and transformative. Speaks in cryptic phrases and represents cycles of change. Both feared and respected. Represents rebirth and healing.",
        "color": 0x228B22,  
        "avatar_url": "https://cdn.discordapp.com/attachments/1103962947413356545/1398903857949708400/image.png",
        "emote": "🐍"
    },
    {
        "name": "Deer", 
        "role": "Gentle but alert observer of the forest. Moves gracefully through life while remaining aware of danger. Represents gentleness and awareness.",
        "color": 0xD2B48C,  
        "avatar_url": "https://cdn.discordapp.com/attachments/1103962947413356545/1397863634587095171/image.png",
        "emote": "🦌"
    },
    {
        "name": "Otter", 
        "role": "Playful and energetic water-dweller. Brings joy and laughter to any conversation. Represents joy and curiosity.",
        "color": 0x4682B4,  
        "avatar_url": "https://cdn.discordapp.com/attachments/1103962947413356545/1398904502958034975/image.png",
        "emote": "🦦"
    }
]

SYSTEM_PROMPT = "Answer with dialogue only; don't describe actions or expressions. Keep responses concise (1-3 sentences). Never break character. Never mention you're an AI. Respond naturally to the conversation. Don't be cringe. Be organic. Don't mention your own personality or environment."





# You should probably ignore the rest of the stuff below. 
# The only thing you might wanna change is:
# 1: Better prompt for technical answers    --- This defines how the bots respond to actual humans
# 2: @tasks.loop(seconds=60)      --- This defines how often the bot sends messages
# 3: response_chance = 0.8     --- This also defines how reliably the bot sends messages.








# Initialize
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!aitroupe ', intents=intents)
conversation_history = []
last_human_message = datetime.now()
HUMAN_TIMEOUT = timedelta(minutes=5)  # Wait longer if humans are active
BOT_ACTIVITY_TIMEOUT = timedelta(hours=5)  # Bot stays active for 6 hours after last human message
human_just_spoke = False  # Track if human just spoke for uncapped responses

# Store webhooks for each persona
persona_webhooks = {}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot ID: {bot.user.id}')
    print(f'Bot application ID: {bot.application_id}')
    
    # Generate proper invite URL
    permissions = discord.Permissions()
    permissions.send_messages = True
    permissions.manage_webhooks = True
    permissions.read_message_history = True
    
    invite_url = discord.utils.oauth_url(
        bot.application_id, 
        permissions=permissions, 
        scopes=('bot', 'applications.commands')
    )
    print(f'\nIMPORTANT: Make sure the bot has the needed permissions both in the permission integar, and in the Discord role settings.')
    print(f'Join our Discord for support: https://discord.gg/2sbnwze753\n')
    
    # Try syncing commands
    try:
        synced = await bot.tree.sync()
        print(f"Successfully synced {len(synced)} slash command(s)")
        for command in synced:
            print(f"- {command.name}: {command.description}")
    except discord.HTTPException as e:
        print(f"HTTPException syncing commands: {e}")
        if e.status == 403:
            print("ERROR: Bot missing 'applications.commands' scope!")
            print("Please re-invite the bot using the URL above.")
    except discord.Forbidden as e:
        print(f"Forbidden error syncing commands: {e}")
        print("Bot may be missing 'applications.commands' scope")
        print("Please re-invite the bot using the URL above.")
    except Exception as e:
        print(f"Unexpected error syncing commands: {e}")
        import traceback
        traceback.print_exc()
    
    # Only start shit if channel is set and valid
    if CHANNEL_ID:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            print(f"Initializing AI features for channel: #{channel.name} ({CHANNEL_ID})")
            # Create webhooks for each persona
            await setup_persona_webhooks(channel)
            # Load recent messages to build context
            await load_recent_messages(channel)
            conversation_loop.start(channel)
        else:
            print(f"Warning: Channel ID {CHANNEL_ID} not found. Use the channel command to set a valid channel.")
    else:
        print("No channel set. Use the '!aitroupe channel <channel_id>' or '/aitroupe_channel' command to set an active channel.")

async def setup_persona_webhooks(channel):
    """Create or get webhooks for each persona"""
    global persona_webhooks
    
    try:
        # Get existing webhooks
        existing_webhooks = await channel.webhooks()
        
        # Clean up old/invalid webhooks first
        current_persona_names = {p['name'] for p in PERSONAS}
        for webhook in existing_webhooks:
            # Check if webhook is for a persona that no longer exists
            if webhook.name.startswith("Persona-"):
                persona_name = webhook.name.replace("Persona-", "")
                if persona_name not in current_persona_names:
                    try:
                        await webhook.delete()
                        print(f"Deleted old webhook for removed persona: {persona_name}")
                    except Exception as e:
                        print(f"Error deleting old webhook {webhook.name}: {e}")
        
        # Create or get webhooks for current personas
        for persona in PERSONAS:
            webhook_name = f"Persona-{persona['name']}"
            
            # Check if webhook already exists
            existing_webhook = None
            for webhook in existing_webhooks:
                if webhook.name == webhook_name:
                    existing_webhook = webhook
                    break
            
            if existing_webhook:
                # Verify the webhook is still valid
                try:
                    await existing_webhook.fetch()
                    persona_webhooks[persona['name']] = existing_webhook
                    print(f"Using existing valid webhook for {persona['name']}")
                except discord.NotFound:
                    print(f"Found invalid webhook for {persona['name']}, creating new one")
                    existing_webhook = None
            
            if not existing_webhook:
                try:
                    # Create new webhook if needed
                    webhook = await channel.create_webhook(name=webhook_name)
                    persona_webhooks[persona['name']] = webhook
                    print(f"Created new webhook for {persona['name']}")
                except discord.Forbidden:
                    print(f"Missing permissions to create webhook for {persona['name']}")
                    raise
                except discord.HTTPException as e:
                    print(f"HTTP error creating webhook for {persona['name']}: {e}")
                    raise
                
    except Exception as e:
        print(f"Error setting up webhooks: {e}")
        raise

async def send_message_as_persona(persona_name, message):
    """Send a message using the persona's webhook"""
    try:
        if persona_name in persona_webhooks:
            webhook = persona_webhooks[persona_name]
            
            # Find the persona to get avatar and emote
            persona = next((p for p in PERSONAS if p['name'] == persona_name), None)
            
            # Add emote to the username display
            display_name = f"{persona_name} {persona['emote']}" if persona and 'emote' in persona else persona_name
            
            # Split message into chunks of 2000 characters or less
            message_chunks = [message[i:i+2000] for i in range(0, len(message), 2000)]
            
            # Send each chunk with a small delay between them
            for chunk in message_chunks:
                await webhook.send(
                    content=chunk,
                    username=display_name,
                    avatar_url=persona['avatar_url'] if persona else None,
                    wait=True
                )
                await asyncio.sleep(0.5)  # 1 second delay between chunks
        else:
            print(f"No webhook found for persona: {persona_name}")
    except Exception as e:
        print(f"Error sending message as {persona_name}: {e}")

async def load_recent_messages(channel):
    """Load recent messages to build conversation context"""
    global conversation_history
    try:
        messages = []
        async for message in channel.history(limit=20):
            # Skip bot commands and system messages
            if not message.content.startswith('!') and message.author != bot.user:
                # Format messages to match conversation history structure
                role = "assistant" if message.author.bot else "user"
                content = f"{message.author.display_name}: {message.content}"
                messages.append({"role": role, "content": content})
        
        # Reverse to chronological order
        conversation_history = list(reversed(messages))[-15:]  # Keep last 15 messages
    except Exception as e:
        print(f"Error loading messages: {e}")

@bot.event
async def on_message(message):
    global conversation_history, last_human_message, human_just_spoke, CURRENT_AI, CHANNEL_ID
    
    # Skip processing if no channel is set or message is from wrong channel/bot
    if not CHANNEL_ID or message.channel.id != CHANNEL_ID or message.author.bot:
        return
        
    # Process commands
    await bot.process_commands(message)
    
    # Track human messages (including those right after bot messages)
    if not message.author.bot and not message.content.startswith('!aitroupe'):
        # Find all mentioned personas
        mentioned_personas = []
        for persona in PERSONAS:
            if persona['name'].lower() in message.content.lower():
                mentioned_personas.append(persona)
                
        # Check if message is a reply to a persona's message
        replied_persona = None
        if message.reference:
            try:
                replied_message = await message.channel.fetch_message(message.reference.message_id)
                if replied_message.author.bot:
                    # Check both message content and webhook username for persona name
                    for persona in PERSONAS:
                        persona_lower = persona['name'].lower()
                        content_check = persona_lower in replied_message.content.lower()
                        username_check = (replied_message.webhook_id and 
                                        persona_lower in replied_message.author.display_name.lower())
                        if content_check or username_check:
                            replied_persona = persona
                            # Only add if not already in mentioned_personas
                            if persona not in mentioned_personas:
                                mentioned_personas.append(persona)
                            break
            except Exception as e:
                print(f"Error checking replied message: {e}")
                
        conversation_history.append({
            "role": "user", 
            "content": f"{message.author.display_name}: {message.content}"
        })
        # Keep only last 15 messages
        conversation_history = conversation_history[-15:]
        last_human_message = datetime.now()
        
        # Only set uncapped flag if no personas were mentioned
        human_just_spoke = len(mentioned_personas) == 0

        # Generate responses from all mentioned personas
        for persona in mentioned_personas:
            # Build prompt for this persona
            context_messages = [clean_emotes_from_conversation(msg["content"]) for msg in conversation_history[-8:]]
            context = "\n".join(context_messages)
            prompt = f"{SYSTEM_PROMPT}\n\nCurrent conversation:\n{context}\n\n{persona['name']} ({persona['role']}):"
                
            # Get response from this persona (always uncapped for direct mentions)
            reply = await get_ai_response(persona, prompt, uncapped=True)
            
            if reply and not reply.isspace():
                reply = reply.strip()
                reply = reply.replace(f"{persona['name']}:", "").strip()
                
                # Remove common AI response prefixes
                prefixes_to_remove = [
                    f"{persona['name']}:",
                    f"**{persona['name']}**:",
                    f"{persona['name']} says:",
                    f"{persona['name']} responds:",
                ]
                
                for prefix in prefixes_to_remove:
                    if reply.startswith(prefix):
                        reply = reply[len(prefix):].strip()
                
                reply = clean_response(reply)
                
                if reply:
                    # Add to history
                    ai_message = {"role": "assistant", "content": f"{persona['name']}: {reply}"}
                    conversation_history.append(ai_message)
                    conversation_history = conversation_history[-15:]
                    
                    # Send message using webhook as the persona
                    await send_message_as_persona(persona['name'], reply)
                    await asyncio.sleep(1)  # Brief delay between persona responses

def is_admin_or_owner():
    """Check if user is admin or bot owner"""
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator or await ctx.bot.is_owner(ctx.author)
    return commands.check(predicate)

@bot.command(name='ai')
@is_admin_or_owner()
async def switch_ai(ctx, ai_provider: str = None):
    """Switch AI provider (deepseek, chatgpt, gemini, qwen)"""
    global CURRENT_AI
    
    if not ai_provider:
        await ctx.send(f"Current AI: **{CURRENT_AI}**\nAvailable: `deepseek`, `chatgpt`, `gemini`, `qwen`\nUsage: `!aitroupe ai <provider>`")
        return
    
    ai_provider = ai_provider.lower()
    valid_providers = ["deepseek", "chatgpt", "gemini", "qwen"]
    
    if ai_provider not in valid_providers:
        await ctx.send(f"Invalid AI provider. Available: {', '.join(valid_providers)}")
        return
    
    previous_ai = CURRENT_AI
    CURRENT_AI = ai_provider
    await ctx.send(f"Switched AI from **{previous_ai}** to **{CURRENT_AI}**")

@bot.command(name='status')
@is_admin_or_owner()
async def status(ctx):
    """Show current AI provider and channel (admin only)"""
    channel_status = f"<#{CHANNEL_ID}>" if CHANNEL_ID else "None (use `!aitroupe channel <id>` to set)"
    await ctx.send(f"Current AI provider: **{CURRENT_AI}**\nActive channel: {channel_status}")

@bot.command(name='channel')
@is_admin_or_owner()
async def set_channel(ctx, channel_id: int = None):
    """Set the active channel for AI responses (admin only). If no ID provided, uses current channel."""
    global CHANNEL_ID
    
    # If no channel_id provided, use current channel
    if channel_id is None:
        channel = ctx.channel
        channel_id = channel.id
    else:
        # Verify the channel exists
        channel = bot.get_channel(channel_id)
        if not channel:
            await ctx.send("Channel not found!")
            return
    
    # Stop existing conversation loop if running
    if conversation_loop.is_running():
        conversation_loop.cancel()
    
    CHANNEL_ID = channel_id
    await ctx.send(f"Active channel set to <#{channel_id}>")
    
    # Reinitialize webhooks and conversation loop for the new channel
    await setup_persona_webhooks(channel)
    await load_recent_messages(channel)
    conversation_loop.start(channel)

@bot.command(name='invite')
@is_admin_or_owner()
async def generate_invite(ctx):
    """Generate invite URL with proper permissions (admin only)"""
    permissions = discord.Permissions()
    permissions.send_messages = True
    permissions.manage_webhooks = True
    permissions.read_message_history = True
    permissions.use_slash_commands = True
    
    invite_url = discord.utils.oauth_url(
        bot.application_id, 
        permissions=permissions, 
        scopes=('bot', 'applications.commands')
    )
    
    embed = discord.Embed(
        title="Bot Invite URL",
        description=f"Use this URL to re-invite the bot with slash command support:\n\n[Click here to invite]({invite_url})",
        color=0x00ff00
    )
    embed.add_field(name="Required Scopes", value="• bot\n• applications.commands", inline=False)
    embed.add_field(name="Required Permissions", value="• Send Messages\n• Manage Webhooks\n• Read Message History\n• Use Slash Commands", inline=False)
    
    await ctx.send(embed=embed)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle application command errors"""
    print(f"Application command error: {error}")
    print(f"Command: {interaction.command}")
    print(f"User: {interaction.user}")
    print(f"Guild: {interaction.guild}")
    
    if isinstance(error, app_commands.CommandNotFound):
        await interaction.response.send_message("Command not found.", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message(f"An error occurred: {str(error)}", ephemeral=True)

# Individual slash commands (avoiding command groups which can cause issues)
@bot.tree.command(name="aitroupe_ai", description="Switch AI provider")
@app_commands.describe(ai_provider="The AI provider to switch to")
@app_commands.choices(ai_provider=[
    app_commands.Choice(name='DeepSeek', value='deepseek'),
    app_commands.Choice(name='ChatGPT', value='chatgpt'),
    app_commands.Choice(name='Gemini', value='gemini'),
    app_commands.Choice(name='Qwen', value='qwen')
])
async def slash_ai(interaction: discord.Interaction, ai_provider: str = None):
    """Switch AI provider"""
    # Check if user is admin or owner
    if not (interaction.user.guild_permissions.administrator or await bot.is_owner(interaction.user)):
        await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
        return
        
    global CURRENT_AI
    
    if not ai_provider:
        await interaction.response.send_message(f"Current AI: **{CURRENT_AI}**\nAvailable: `deepseek`, `chatgpt`, `gemini`, `qwen`", ephemeral=True)
        return
    
    ai_provider = ai_provider.lower()
    valid_providers = ["deepseek", "chatgpt", "gemini", "qwen"]
    
    if ai_provider not in valid_providers:
        await interaction.response.send_message(f"Invalid AI provider. Available: {', '.join(valid_providers)}", ephemeral=True)
        return
    
    previous_ai = CURRENT_AI
    CURRENT_AI = ai_provider
    await interaction.response.send_message(f"Switched AI from **{previous_ai}** to **{CURRENT_AI}**")

@bot.tree.command(name="aitroupe_status", description="Show current AI provider and channel")
async def slash_status(interaction: discord.Interaction):
    """Show current AI provider and channel"""
    # Check if user is admin or owner
    if not (interaction.user.guild_permissions.administrator or await bot.is_owner(interaction.user)):
        await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
        return
    
    channel_status = f"<#{CHANNEL_ID}>" if CHANNEL_ID else "None (use `/aitroupe_channel` to set)"
    await interaction.response.send_message(f"Current AI provider: **{CURRENT_AI}**\nActive channel: {channel_status}", ephemeral=True)

@bot.tree.command(name="aitroupe_channel", description="Set the active channel for AI responses")
@app_commands.describe(channel_name="The channel name to set as active")
async def slash_channel(interaction: discord.Interaction, channel_name: str):
    """Set the active channel for AI responses"""
    # Check if user is admin or owner
    if not (interaction.user.guild_permissions.administrator or await bot.is_owner(interaction.user)):
        await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
        return
        
    global CHANNEL_ID
    
    # Find the channel by name
    channel = None
    for guild_channel in interaction.guild.channels:
        if isinstance(guild_channel, discord.TextChannel) and guild_channel.name == channel_name:
            channel = guild_channel
            break
    
    if not channel:
        await interaction.response.send_message(f"Channel '{channel_name}' not found.", ephemeral=True)
        return
    
    # Stop existing conversation loop if running
    if conversation_loop.is_running():
        conversation_loop.cancel()
        
    CHANNEL_ID = channel.id
    await interaction.response.send_message(f"Active channel set to <#{channel.id}>")
    
    # Reinitialize webhooks and conversation loop for the new channel
    await setup_persona_webhooks(channel)
    await load_recent_messages(channel)
    conversation_loop.start(channel)

@slash_channel.autocomplete('channel_name')
async def channel_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for channel names"""
    channels = [channel for channel in interaction.guild.channels if isinstance(channel, discord.TextChannel)]
    return [
        app_commands.Choice(name=f"#{channel.name}", value=channel.name)
        for channel in channels
        if current.lower() in channel.name.lower()
    ][:25]  # Discord limits to 25 choices

def clean_emotes_from_conversation(text):
    """Remove persona emotes from conversation text for AI processing"""
    if not text:
        return text
    
    # Remove emotes from persona names in conversation history
    for persona in PERSONAS:
        if 'emote' in persona:
            # Remove "PersonaName emote:" pattern
            text = text.replace(f"{persona['name']} {persona['emote']}:", f"{persona['name']}:")
    
    return text

def clean_response(text):
    """Remove quotation marks and clean up the response"""
    if not text:
        return text
    
    # Remove various types of quotation marks
    text = text.strip()
    
    # Remove quotes at the beginning and end
    quote_chars = ['"', "'", '"', '"', ''', ''']
    for quote in quote_chars:
        if text.startswith(quote) and text.endswith(quote):
            text = text[1:-1].strip()
    
    return text

async def get_ai_response(speaker, prompt, uncapped=False):
    """Get response from the current AI provider"""
    global CURRENT_AI
    
    # Detect if question is technical/complex
    technical_keywords = ['solve', 'calculate', 'conclude', 'derive', 'step by step', 'steps', 'method']
    is_technical = any(keyword in prompt.lower() for keyword in technical_keywords)
    
    # Always use uncapped mode for technical questions
    if uncapped or is_technical:
        # Better prompt for technical answers
        technical_prompt = (
            "You are {speaker_name}, {speaker_role}. Answer with dialogue only. don't describe actions or expressions."
            "For technical or complex questions, provide a detailed, step-by-step explanation. "
            "Be thorough and precise. Use clear examples if helpful. "
            "Break down concepts into understandable parts. "
            "If the question isn't technical or doesn't need a long answer, keep the answer super short and concise."
            "Never break character. Never mention you're an AI. "
            "Current conversation:\n{context}\n\n"
            "{speaker_name}:"
        ).format(
            speaker_name=speaker['name'],
            speaker_role=speaker['role'],
            context=prompt.split('\n\nCurrent conversation:\n')[-1]
        )
        prompt = technical_prompt
    
    response = None
    if CURRENT_AI == "deepseek":
        response = await get_deepseek_response(speaker, prompt, uncapped)
    elif CURRENT_AI == "chatgpt":
        response = await get_chatgpt_response(speaker, prompt, uncapped)
    elif CURRENT_AI == "gemini":
        response = await get_gemini_response(speaker, prompt, uncapped)
    elif CURRENT_AI == "qwen":
        response = await get_qwen_response(speaker, prompt, uncapped)
    else:
        return "Error: Unknown AI provider"
    
    # Clean the response to remove quotation marks
    return clean_response(response) if response else response

async def get_deepseek_response(speaker, prompt, uncapped=False):
    """Get response from DeepSeek"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    # Use higher token limit if uncapped response requested
    max_tokens = 1000 if uncapped else 150
    
    # Use longer timeout for uncapped responses
    timeout = 120 if uncapped else 30
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": f"You are {speaker['name']}, {speaker['role']}."},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "max_tokens": max_tokens,
        "temperature": 0.8,
        "top_p": 0.95
    }
    
    try:
        print(f"DEBUG: DeepSeek request - max_tokens={max_tokens}, timeout={timeout}s")
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                timeout=timeout
            )
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        else:
            print(f"DeepSeek API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"DeepSeek Error: {e}")
        return None

async def get_chatgpt_response(speaker, prompt, uncapped=False):
    """Get response from ChatGPT"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHATGPT_API_KEY}"
    }
    
    # Use higher token limit if uncapped response requested
    max_tokens = 1000 if uncapped else 150
    
    # Use longer timeout for uncapped responses
    timeout = 120 if uncapped else 30
    
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": f"You are {speaker['name']}, {speaker['role']}."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.8
    }
    
    try:
        print(f"DEBUG: ChatGPT request - max_tokens={max_tokens}, timeout={timeout}s")
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                timeout=timeout
            )
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        else:
            print(f"ChatGPT API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"ChatGPT Error: {e}")
        return None

async def get_gemini_response(speaker, prompt, uncapped=False):
    """Get response from Google Gemini"""
    headers = {
        "Content-Type": "application/json"
    }
    
    # Use higher token limit if uncapped response requested
    max_tokens = 1000 if uncapped else 150
    
    # Use longer timeout for uncapped responses
    timeout = 120 if uncapped else 30
    
    payload = {
        "contents": [{
            "parts": [{
                "text": f"You are {speaker['name']}, {speaker['role']}.\n\n{prompt}"
            }]
        }],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.8
        }
    }
    
    try:
        print(f"DEBUG: Gemini request - max_tokens={max_tokens}, timeout={timeout}s")
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_API_KEY}",
                headers=headers,
                data=json.dumps(payload),
                timeout=timeout
            )
        )
        
        if response.status_code == 200:
            result = response.json()
            if "candidates" in result and len(result["candidates"]) > 0:
                return result["candidates"][0]["content"]["parts"][0]["text"].strip()
            else:
                return None
        else:
            print(f"Gemini API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Gemini Error: {e}")
        return None

async def get_qwen_response(speaker, prompt, uncapped=False):
    """Get response from Qwen (Tongyi)"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {QWEN_API_KEY}"
    }
    
    # Use higher token limit if uncapped response requested
    max_tokens = 1000 if uncapped else 150
    
    # Use longer timeout for uncapped responses
    timeout = 120 if uncapped else 30
    
    payload = {
        "model": "qwen-turbo",
        "input": {
            "messages": [
                {"role": "system", "content": f"You are {speaker['name']}, {speaker['role']}."},
                {"role": "user", "content": prompt}
            ]
        },
        "parameters": {
            "max_tokens": max_tokens,
            "temperature": 0.8
        }
    }
    
    try:
        print(f"DEBUG: Qwen request - max_tokens={max_tokens}, timeout={timeout}s")
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: requests.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                headers=headers,
                data=json.dumps(payload),
                timeout=timeout
            )
        )
        
        if response.status_code == 200:
            result = response.json()
            if "output" in result and "text" in result["output"]:
                return result["output"]["text"].strip()
            else:
                return None
        else:
            print(f"Qwen API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Qwen Error: {e}")
        return None

@tasks.loop(seconds=60)  # Check every minute
async def conversation_loop(channel):
    global conversation_history, last_human_message, human_just_spoke, CHANNEL_ID
    
    # Verify channel is still valid and matches current CHANNEL_ID
    if not CHANNEL_ID or not channel or channel.id != CHANNEL_ID:
        print("Channel no longer valid, stopping conversation loop")
        conversation_loop.cancel()
        return
    
    # Check if bot should still be active (6 hours after last human message)
    time_since_last_human = datetime.now() - last_human_message
    if time_since_last_human > BOT_ACTIVITY_TIMEOUT:
        print(f"Bot going inactive - {time_since_last_human.total_seconds()/3600:.1f} hours since last human message")
        return
    
    # Check if humans are recently active
    human_active = time_since_last_human < HUMAN_TIMEOUT
    
    # Random chance to respond (lower chance if humans active)
    # So basically, every 60 seconds, there's a 80% chance a bot responds.
    response_chance = 0.8 if human_active else 1
    if random.random() > response_chance:
        return
        
    # Wait additional time if humans are active
    if human_active:
        await asyncio.sleep(random.randint(3, 5))
    
    # Select random speaker, making sure it's not the same as last time
    last_speaker = None
    if len(conversation_history) > 0 and conversation_history[-1]["role"] == "assistant":
        last_speaker_name = conversation_history[-1]["content"].split(":")[0]
        last_speaker = next((p for p in PERSONAS if p["name"] == last_speaker_name), None)
    
    # Filter out last speaker if they exist
    available_speakers = [p for p in PERSONAS if p != last_speaker] if last_speaker else PERSONAS
    speaker = random.choice(available_speakers)
    
    # Build conversation context (clean emotes for AI processing)
    context_messages = [clean_emotes_from_conversation(msg["content"]) for msg in conversation_history[-8:]]
    context = "\n".join(context_messages)
    prompt = f"{SYSTEM_PROMPT}\n\nCurrent conversation:\n{context}\n\n{speaker['name']} ({speaker['role']}):"
    
    try:
        # Store the uncapped flag before it gets reset
        is_uncapped = human_just_spoke
        print(f"DEBUG: Generating response - uncapped={is_uncapped}, human_just_spoke={human_just_spoke}")
        
        # Get AI response (use uncapped if human just spoke)
        reply = await get_ai_response(speaker, prompt, uncapped=is_uncapped)
        
        if reply and not reply.isspace():
            print(f"DEBUG: Raw AI response length: {len(reply)} chars")
            
            # For uncapped responses, don't limit to first line only
            if is_uncapped:
                reply = reply.strip()
                print(f"DEBUG: Using uncapped response (full text)")
            else:
                reply = reply.split('\n')[0].strip()  # Take first line only
                print(f"DEBUG: Using capped response (first line only)")
            
            reply = reply.replace(f"{speaker['name']}:", "").strip()
            
            # Remove common AI response prefixes
            prefixes_to_remove = [
                f"{speaker['name']}:",
                f"**{speaker['name']}**:",
                f"{speaker['name']} says:",
                f"{speaker['name']} responds:",
            ]
            
            for prefix in prefixes_to_remove:
                if reply.startswith(prefix):
                    reply = reply[len(prefix):].strip()
            
            # Apply additional quote cleaning
            reply = clean_response(reply)
            
            print(f"DEBUG: Final response length: {len(reply)} chars")
            
            if reply:
                # Add to history
                ai_message = {"role": "assistant", "content": f"{speaker['name']}: {reply}"}
                conversation_history.append(ai_message)
                conversation_history = conversation_history[-15:]  # Keep last 15
                
                # Send message using webhook as the persona
                await send_message_as_persona(speaker['name'], reply)
                
                # Reset the flag after one response
                human_just_spoke = False
        else:
            print(f"Empty response from {CURRENT_AI}")
            
    except Exception as e:
        print(f"Error getting AI response: {e}")



# Run bot
bot.run(DISCORD_TOKEN)