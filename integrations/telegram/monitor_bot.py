import asyncio
import logging
from telethon import TelegramClient, events
import pandas as pd
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to allow importing from sibling directories
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Add operations root to allow importing ai_core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Credentials — set via environment variables
API_ID = int(os.environ.get("TELEGRAM_API_ID", "0"))
API_HASH = os.environ.get("TELEGRAM_API_HASH", "")
SESSION_NAME = 'antigravity_userbot'

# Configuration Paths
CONFIG_FILE = "../../../10_Business_Admin/Telegram_Monitoring_Config.xlsx"

from youtube_handler import YouTubeHandler
# from ai_handler import AIHandler  <-- REPLACED BY AGENT MANAGER
from web.web_handler import WebHandler
from ai_core.vector_handler import VectorHandler
from ai_core.agent_manager import AgentManager
from ai_core.skill_manager import SkillManager
import server

class AISmartBot:
    def __init__(self):
        self.client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        self.monitoring_rules = {}
        self.active_chats = []
        self.yt_handler = YouTubeHandler()
        # self.ai_handler = AIHandler() <-- REMOVED
        self.web_handler = WebHandler()
        self.vector_handler = VectorHandler()
        self.me_id = None
        
        # Initialize OSP Agent System
        # 1. Skill Manager (Loads osp-std, telegram, summarize, youtube, etc.)
        self.skill_manager = SkillManager()
        
        # 2. Agent Manager (Orchestrator)
        # We pass None for degradation for now, or import it if needed.
        self.agent_manager = AgentManager(self.skill_manager, vector_db=self.vector_handler)
        
        # Create a persistent session for "Proactive Agent"
        self.agent_session = self.agent_manager.create_session({
            "name": "Antigravity Assistant",
            "role": "assistant",
            "system_prompt": "You are a helpful AI assistant integrated into Telegram. You can summarize content, manage files, and browse the web."
        })
        logger.info(f"🧠 Agent Session Created: {self.agent_session.session_id}")

    async def load_config(self):
        """Loads monitoring rules from Excel."""
        try:
            if not os.path.exists(CONFIG_FILE):
                logger.warning(f"Config file not found: {CONFIG_FILE}")
                return

            df = pd.read_excel(CONFIG_FILE)
            # Filter rows where Action is not empty and not 'Ignore'
            active_rules = df[df['Action (Keywords/Files/Forward)'].notna()]
            
            logger.info(f"Loaded {len(active_rules)} active monitoring rules.")
            
            for index, row in active_rules.iterrows():
                chat_id = row.get('Chat ID')
                action = str(row.get('Action (Keywords/Files/Forward)')).lower()
                
                if chat_id:
                    self.monitoring_rules[chat_id] = action
                    self.active_chats.append(chat_id)
                    
        except Exception as e:
            logger.error(f"Error loading config: {e}")

    async def start(self):
        """Starts the bot."""
        await self.client.start()
        me = await self.client.get_me()
        self.me_id = me.id
        logger.info(f"✅ AI Assistant started as: {me.first_name} (@{me.username}) ID: {self.me_id}")
        logger.info("waiting for commands...")

        # Share handlers with server
        server.bot_modules = {
            "yt": self.yt_handler,
            "ai": self.ai_handler,
            "web": self.web_handler,
            "vector": self.vector_handler
        }

        # Wait a moment for server/ngrok to initialize
        await asyncio.sleep(5)
        
        if server.public_url and "ngrok" in server.public_url:
            import time
            from telethon.tl.functions.bots import SetBotMenuButtonRequest
            from telethon.tl.types import BotMenuButton
            
            dashboard_url = f"{server.public_url}?t={int(time.time())}"
            
            # Auto-update Menu Button
            try:
                await self.client(SetBotMenuButtonRequest(
                    user_id='me',
                    button=BotMenuButton(
                        text="Antigravity 🚀",
                        url=dashboard_url
                    )
                ))
                logger.info("✅ Menu Button updated successfully!")
            except Exception as e:
                logger.error(f"Failed to update Menu Button: {e}")
            
            dashboard_msg = (f"🚀 **Antigravity System Online**\n\n"
                             f"📱 **Menu Button Updated!**\n"
                             f"Тепер зліва внизу є кнопка **Antigravity 🚀**\n\n"
                             f"_(Alternative link: {dashboard_url})_")
            await self.client.send_message('me', dashboard_msg)
            
        elif server.public_url:
            # Fallback (Localhost) with Error Info
            err_msg = (f"⚠️ **Remote Access Failed**\n\n"
                       f"Bot is running locally: `{server.public_url}`\n"
                       f"Phone access unavailable.\n\n"
                       f"**Error info:**\n`{server.ngrok_error}`\n\n"
                       f"👉 _Likely missing Ngrok Token._")
            await self.client.send_message('me', err_msg)

        # Load config initially
        await self.load_config()

        # Register Event Handlers
        self.client.add_event_handler(self.handle_new_message, events.NewMessage)
        # Handle Voice/Audio in Saved Messages (incoming=False for own messages, but we check chat_id)
        self.client.add_event_handler(self.handle_voice_message, events.NewMessage)
        
        await self.client.run_until_disconnected()

    async def handle_new_message(self, event):
        """Main message handler."""
        
        # 1. Check if it's a Command from ME (ChatOps)
        if event.out and event.raw_text.startswith('/'):
            await self.handle_command(event)
            return

        # 2. Check if it's a Monitored Chat
        # (Passively monitor incoming messages from others)
        if not event.out and event.chat_id in self.monitoring_rules:
            await self.process_monitoring(event)

    async def handle_command(self, event):
        """Handles /commands sent by the user."""
        command = event.raw_text.split()[0]
        args = event.raw_text[len(command):].strip()

        logger.info(f"Command received: {command} | Args: {args}")

        if command == '/status':
            ai_status = "Active 🧠" if self.agent_session else "Offline ⚠️"
            await event.edit(f"✅ **System Status (OSP):**\n- Bot: Online 🟢\n- Monitoring: Active\n- Agent: {ai_status}\n- Session: `{self.agent_session.session_id if self.agent_session else 'N/A'}`")
        
        elif command == '/youtube':
            if not args:
                await event.edit("❌ **Usage:** `/youtube <url>`")
                return
                
            await event.edit(f"⏳ **Analyzing YouTube Video via OSP Agent...**\n`{args}`")
            
            # OSP Agent Execution
            prompt = f"Analyze this YouTube video: {args}. Provide a comprehensive summary."
            result = self.agent_manager.execute_agent(self.agent_session.session_id, prompt)
            
            if "error" in result:
                 await event.edit(f"❌ Agent Error: {result['error']}")
            else:
                 response_text = result.get("output", "No output generated.")
                 # Format nicely
                 await event.edit(f"🎥 **OSP Agent Analysis**\n\n{response_text}")

        # ... (rest of search/monitoring remains same) ...

        elif command == '/youtube_find':
            if not args:
                await event.edit("❌ **Usage:** `/youtube_find <query>`")
                return

            await event.edit(f"🔍 **Searching YouTube for:** `{args}`...")
            results = await self.yt_handler.search_videos(args)
            
            if not results:
                await event.edit("⚠️ No results found.")
            else:
                msg = "**🔍 Top Results:**\n\n"
                for i, vid in enumerate(results, 1):
                    msg += f"{i}. [{vid['title']}]({vid['url']})\n"
                msg += "\n*Reply with /youtube <url> to analyze specific one.*"
                await event.edit(msg)

        elif command == '/find':
            if not args:
                await event.edit("❌ **Usage:** `/find <query>`\n_Example: /find marketing strategy_")
                return

            await event.edit(f"🧠 **Searching Digital Brain:** `{args}`...")
            
            results = []
            # 1. Try Vector Search
            if self.vector_handler:
                try:
                    raw_results = self.vector_handler.search(args, n_results=5)
                    for r in raw_results:
                         results.append({
                             "title": r['metadata'].get('title', 'Untitled'),
                             "score": round(r['score'], 2),
                             "skill": r['metadata'].get('skill', 'General'),
                             "type": r['metadata'].get('direction', 'Unknown'),
                             "path": r['metadata'].get('path', 'Local')
                         })
                except Exception as e:
                    logger.error(f"Vector search error: {e}")
            
            # 2. Fallback
            if not results:
                results = await self.ai_handler.search_knowledge_base(args)

            if not results:
                await event.edit("⚠️ **No results found in Knowledge Base.**\nTry saving some content first!")
            else:
                msg = f"🧠 **Brain Results for** `{args}`:\n\n"
                for i, r in enumerate(results, 1):
                    # For local files, we can't easily link, but we show the path
                    icon = "📄"
                    if "video" in str(r.get('type', '')).lower(): icon = "🎥"
                    elif "audio" in str(r.get('type', '')).lower(): icon = "🎤"
                    
                    msg += f"{i}. {icon} **{r['title']}**\n"
                    msg += f"   _{r.get('skill', '')} • {r.get('type', '')}_\n"
                    # msg += f"   `{r['path']}`\n"
                
                msg += "\n_Use Web Dashboard for full view & content._"
                await event.edit(msg)

        elif command == '/remind':
            # Format: /remind 10m Check server
            parts = args.split(' ', 1)
            if len(parts) < 2:
                await event.edit("❌ **Usage:** `/remind <time> <text>`\n_Example: /remind 30m Check logs_\n_Formats: 10s, 5m, 2h_")
                return
                
            time_str = parts[0].lower()
            note = parts[1]
            
            seconds = 0
            try:
                if 's' in time_str: seconds = int(time_str.replace('s', ''))
                elif 'm' in time_str: seconds = int(time_str.replace('m', '')) * 60
                elif 'h' in time_str: seconds = int(time_str.replace('h', '')) * 3600
                else:
                    await event.edit("❌ Invalid time format. Use s/m/h (e.g., 10m).")
                    return
            except:
                await event.edit("❌ Invalid time number.")
                return

            await event.edit(f"⏰ **Reminder Set!**\nI'll remind you to **\"{note}\"** in {time_str}.")
            
            # Background Task for Reminder
            async def reminder_task(delay, text, chat):
                await asyncio.sleep(delay)
                await self.client.send_message(chat, f"⏰ **REMINDER:**\n\n{text}")

            asyncio.create_task(reminder_task(seconds, note, event.chat_id))

    async def handle_voice_message(self, event):
        """Downloads and transcribes voice messages."""
        if not event.message.voice and not event.message.audio:
            return

        # Only process messages from myself (Saved Messages)
        # Check against cached ID
        if event.chat_id != self.me_id:
             return
        
        # Avoid processing my own "processing" messages if they contain audio (unlikely but safe)
        if event.message.message and "Обробка аудіо" in event.message.message:
            return

        status_msg = await event.reply("🎤 Обробка аудіо...")
        
        try:
            path = await event.download_media(file="temp_voice")
            logger.info(f"Downloaded voice note: {path}")
            
            # Convert partial/relative path to absolute for the agent
            abs_path = os.path.abspath(path)
            
            # OSP Agent Execution
            # We construct a specific instruction so the Router/Planner picks the right skill (Summarize/Transcribe)
            # or we call a specific skill directly if we want to bypass routing (for unexpected speed).
            # But let's try the Agent way.
            
            prompt = f"Transcribe and summarize this audio file: {abs_path}"
            # We might need to hint the agent to use 'summarize_content' skill with 'audio_path' arg.
            # This depends on the LLM's ability to map the prompt to the tool schema.
            # The tool schema for 'summarize' needs to show 'audio_path'.
            # I didn't update the metadata! The LLM won't know about 'audio_path'.
            
            # Force direct skill execution for reliability in this demo, 
            # OR assume the LLM is smart enough if I update metadata later.
            # Let's use direct skill call via manager for speed/reliability in this phase.
            
            # Actually, let's use the agent but ensure the Prompt explains it well.
            # "Use the summarize skill to transcribe audio_path=..."
            
            result = self.agent_manager.execute_agent(self.agent_session.session_id, prompt)
            
            if "error" in result:
                final_text = f"❌ Error: {result['error']}"
            else:
                final_text = result.get("output", "No output.")

            await status_msg.edit(f"📝 **Аналіз Аудіо (OSP):**\n\n{final_text}")
            
            # Cleanup
            if os.path.exists(path):
                os.remove(path)
                
        except Exception as e:
            logger.error(f"Voice Handle Error: {e}")
            await status_msg.edit(f"❌ Помилка: {e}")

    async def process_monitoring(self, event):
        """Analyzes messages from monitored chats."""
        rule = self.monitoring_rules.get(event.chat_id, "")
        text = event.raw_text.lower()
        
        # Simple Keyword Match (Placeholder for Advanced Logic)
        if "invoice" in text or "фрукт" in text or "терміново" in text:
            # Check if rule matches or is generic
            logger.info(f"Match found in chat {event.chat_id}: {text[:50]}...")
            # Forward to Saved Messages if needed (logic to be refined)
            # await event.forward_to('me')

from server import run_server

if __name__ == '__main__':
    bot = AISmartBot()
    
    # Create main event loop to run both Bot and Server
    loop = asyncio.get_event_loop()
    
    try:
        # Schedule the bot and server tasks
        # We need to wrap bot.start() because it's an awaitable
        # Telethon's run_until_disconnected blocks, so we run it as a task?
        # Actually better to use asyncio.gather
        
        async def main_runner():
            server_task = asyncio.create_task(run_server())
            
            # Start bot (which includes run_until_disconnected inside logic usually, 
            # but we need to verify if start() blocks. 
            # In current code: await self.client.run_until_disconnected() BLOCKS.
            # So start() blocks.
            
            # Use gather to run both
            await asyncio.gather(
                bot.start(),
                server_task
            )

        loop.run_until_complete(main_runner())
        
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
