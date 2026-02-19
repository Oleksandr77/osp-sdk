import os
import sys
import logging
import json
import pandas as pd
import google.generativeai as genai

logger = logging.getLogger(__name__)

# TODO: Replace with secure retrieval or user input
# For this demo, we need an API Key. 
# I will add a placeholder and log a warning if missing.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 

class AIHandler:
    PROMPTS_FILE = "prompts.json"
    
    # Default Professional Prompts
    DEFAULT_PROMPTS = {
        "general": {
            "name": "📝 General Summary",
            "icon": "📝",
            "text": """
            Analyze the following content. Provide a comprehensive summary in Ukrainian.
            Structure:
            1. 📌 **Main Topic** (1 sentence)
            2. 🔑 **Key Points** (Bullet points)
            3. 💡 **Conclusions**
            """
        },
        "business": {
            "name": "💼 Business Analyst",
            "icon": "💼",
            "text": """
            Act as a Senior Business Analyst. Analyze the text for business opportunities and risks.
            Output in Ukrainian, Markdown format:
            ## 💼 Business Analysis
            - **Market Insights:** What are the key trends mentioned?
            - **Opportunities:** Potential revenue streams or ideas.
            - **Risks:** Potential pitfalls or competitors.
            - **Action Plan:** 3 concrete steps to take based on this info.
            """
        },
        "tech": {
            "name": "🛠 Tech Deep Dive",
            "icon": "🛠",
            "text": """
            Act as a CTO / Tech Lead. Analyze the technical content.
            Output in Ukrainian:
            ## 🛠 Technical Deep Dive
            - **Technology Stack:** What tools/languages are discussed?
            - **Innovation:** What is new or unique here?
            - **Pros/Cons:** Technical advantages and limitations.
            - **Implementation:** Difficulty level and prerequisites.
            """
        },
        "crypto": {
            "name": "💰 Crypto/Market",
            "icon": "💰",
            "text": """
            Act as a Crypto Market Analyst. Focus on tokens, price action, and sentiment.
            Output in Ukrainian:
            ## 💰 Crypto/Market Report
            - **Assets:** tokens/coins mentioned.
            - **Sentiment:** Bullish 🐂 / Bearish 🐻 / Neutral.
            - **Catalysts:** Upcoming events or news.
            - **Risk Level:** High/Medium/Low.
            """
        },
        "news": {
            "name": "📰 Journalist",
            "icon": "📰",
            "text": """
            Act as an Investigative Journalist. Summarize the facts.
            Output in Ukrainian:
            ## 📰 News Brief
            - **What happened?** (The core event)
            - **Who?** (Key figures)
            - **Why it matters?** (Global/Local impact)
            - **Fact Check:** Are there any controversial claims?
            """
        }
    }

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        # Initialize Skill Manager
        try:
            # Add parent dir to path to import ai_core
            current_dir = os.path.dirname(os.path.abspath(__file__))
            ai_core_path = os.path.abspath(os.path.join(current_dir, "../../ai_core"))
            if ai_core_path not in sys.path:
                sys.path.append(ai_core_path)
            
            from skill_manager import SkillManager
            # Skills dir is ../../skills relative to ai_core, so effectively ../../../skills from here?
            # actually SkillManager default is "../skills" relative to itself.
            # So if we import it, it should work if the dir exists relative to it.
            self.skill_manager = SkillManager()
        except Exception as e:
            logger.error(f"Failed to init SkillManager: {e}")
            self.skill_manager = None

        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.is_active = True
        else:
            logger.warning("GEMINI_API_KEY not found. AI features disabled.")
            self.is_active = False

    async def summarize_text(self, text, template_type="general", context="YouTube Video"):
        """Summarizes text using the 'summarize_content' skill."""
        if not self.is_active:
            return "⚠️ AI module not configured (Missing API Key)."
            
        try:
            # 1. Try to get skill instruction
            instruction = ""
            if self.skill_manager:
                # We assume 'summarize_content' is the ID for general summarization
                # In a real scenario, we might use detect_intent(text)
                instruction = self.skill_manager.get_skill_instruction("summarize_content")
            
            # Fallback if skill not found
            if not instruction:
                instruction = "Analyze the following content and provide a comprehensive summary in Ukrainian."

            full_prompt = f"""
            {instruction}
            
            ---
            CONTEXT: {context}
            TEMPLATE TYPE: {template_type}
            INPUT TEXT:
            {text[:30000]} 
            """
            
            response = await self.model.generate_content_async(full_prompt)
            return response.text
        except Exception as e:
            logger.error(f"AI Error: {e}")
            return f"❌ AI Error: {e}"

    async def transcribe_audio(self, file_path):
        """Transcribes audio using Gemini 1.5 Flash (Native Audio Support)."""
        logger.info(f"Transcribing audio: {file_path}")
        try:
            # Upload the file to Gemini
            audio_file = genai.upload_file(file_path)
            
            # Create a prompt for transcription
            prompt = "Listen to this audio carefully and provide a full, accurate transcription. Then provide a brief summary of the key points."
            
            # Generate content
            response = self.model.generate_content([prompt, audio_file])
            
            # Return the text
            return response.text
            
        except Exception as e:
            logger.error(f"Transcription Error: {e}")
            return f"Error transcribing audio: {e}"

    async def classify_content(self, text, context=""):
        """Classifies content into a Skill/Domain and Direction using AI."""
        if not self.is_active:
            return "General", "Uncategorized"
            
        try:
            prompt = f"""
            Analyze the following text and classify it into:
            1. **Skill/Domain**: (e.g., Python, Marketing, Crypto, Management, Health, History, News)
            2. **Direction/Type**: (e.g., Guide, Analysis, News, Tutorial, Idea, Reference)
            
            Return strictly in JSON format: {{"skill": "...", "direction": "..."}}
            
            Context: {context}
            Text (first 1000 chars): {text[:1000]}
            """
            response = await self.model.generate_content_async(prompt)
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(clean_text)
            return data.get("skill", "General"), data.get("direction", "Uncategorized")
        except Exception as e:
            logger.error(f"Classification Error: {e}")
            return "General", "Uncategorized"

    async def save_to_knowledge_base(self, data, category="Web"):
        """Saves analysis to the local Knowledge Base structure."""
        try:
            # 1. auto-classify if not provided
            content_text = data.get('transcript') or data.get('summary') or data.get('text') or ""
            skill, direction = await self.classify_content(content_text, context=f"Source: {category}")
            
            # 2. Determine Path
            # Structure: 10_Business_Admin/Knowledge_Base/{Skill}/{Direction}/{Title}
            base_dir = "../../../10_Business_Admin/Knowledge_Base"
            
            # Clean strings for filenames
            def clean_name(name):
                return "".join([c if c.isalnum() or c in " -_" else "" for c in name]).strip()[:50]

            safe_skill = clean_name(skill)
            safe_direction = clean_name(direction)
            title = clean_name(data.get('title', 'Untitled'))
            
            # Add date to folder name to avoid collisions and sort by recency
            date_str = pd.Timestamp.now().strftime('%Y-%m-%d')
            folder_name = f"{date_str}_{title}"
            
            folder_path = os.path.join(base_dir, safe_skill, safe_direction, folder_name)

            if not os.path.exists(folder_path):
                os.makedirs(folder_path)

            # 3. Save Summary (Markdown)
            summary_path = os.path.join(folder_path, "summary.md")
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(f"# {data.get('title')}\n\n")
                f.write(f"**Source:** {data.get('url', 'N/A')}\n")
                f.write(f"**Skill:** {skill} | **Direction:** {direction}\n")
                f.write(f"**Date:** {pd.Timestamp.now()}\n\n")
                f.write(data.get('summary', 'No summary generated.'))

            # 4. Save Transcript/Content (Text)
            content_path = os.path.join(folder_path, "transcript.txt")
            with open(content_path, "w", encoding="utf-8") as f:
                f.write(content_text)

            # 5. Save Metadata (JSON)
            data['skill'] = skill
            data['direction'] = direction
            data['local_path'] = folder_path
            
            meta_path = os.path.join(folder_path, "metadata.json")
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            logger.info(f"✅ Saved to Knowledge Base: {folder_path}")
            
            # 6. Update Global Index (Fast Search)
            await self.update_index(data, folder_path, category)

            # 7. Index in Vector DB
            if hasattr(self, 'vector_db') and self.vector_db:
                try:
                    # Construct rich text for embedding
                    text_to_embed = f"{data.get('title')}\nSkill: {skill}\nDirection: {direction}\n{data.get('summary')}\n{content_text}"
                    metadata = {
                        "title": data.get('title', 'Untitled'),
                        "path": folder_path,
                        "category": category,
                        "skill": skill,
                        "direction": direction,
                        "type": data.get('type', 'unknown'),
                        "date": date_str
                    }
                    self.vector_db.add_document(text_to_embed, metadata)
                    logger.info("✅ Indexed in Vector DB")
                except Exception as e:
                    logger.error(f"Vector Indexing Error: {e}")
            
            return folder_path

        except Exception as e:
            logger.error(f"Save to KB Error: {e}")
            return None

    async def update_index(self, data, folder_path, category):
        """Updates the lightweight JSON index for O(1) search."""
        index_path = "../../../10_Business_Admin/Knowledge_Base/index.json"
        
        entry = {
            "id": data.get("id") or str(pd.Timestamp.now().timestamp()), # Unique ID
            "title": data.get("title"),
            "path": folder_path,
            "category": category,
            "date": pd.Timestamp.now().strftime('%Y-%m-%d'),
            "tags": data.get("tags", []), # Future: AI auto-tagging
            "type": data.get("type", "unknown")
        }
        
        try:
            if os.path.exists(index_path):
                with open(index_path, "r", encoding="utf-8") as f:
                    index = json.load(f)
            else:
                index = []
                
            # Append new entry
            index.append(entry)
            
            # Write back (Atomic rewrite usually better, but simple write for now)
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Index Update Error: {e}")

    async def search_knowledge_base(self, query):
        """Fast search using index.json."""
        index_path = "../../../10_Business_Admin/Knowledge_Base/index.json"
        if not os.path.exists(index_path):
            return []
            
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
            
            query = query.lower()
            results = []
            
            # 1. Fast Scan (Title/Tags)
            for item in index:
                if query in item["title"].lower() or query in item["category"].lower():
                    results.append(item)
                    if len(results) >= 10: break # Limit for speed
            
            return results
            
        except Exception as e:
            logger.error(f"Search Error: {e}")
            return []

    async def analyze_intent(self, message):
        """Determines if a message is a task, reminder, or general query."""
        if not self.is_active:
            return "unknown"

        try:
            prompt = f"""
            Analyze the user's message and classify intent:
            - "task" (if asking to do something)
            - "reminder" (if asking to remind)
            - "search" (if asking to find info)
            - "chat" (general conversation)
            
            Return ONLY the label.
            
            Message: "{message}"
            """
            response = await self.model.generate_content_async(prompt)
            return response.text.strip().lower()
        except:
             return "unknown"
