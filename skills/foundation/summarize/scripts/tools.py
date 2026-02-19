import os
import google.generativeai as genai
from typing import Dict, Any

# Configure Gemini
# In a real production skill, we'd inject configuration or use a shared service.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

def execute(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Summarizes the provided text.
    Arguments:
      - text: The content to summarize.
      - context: Optional context (e.g., "YouTube Video", "News Article").
      - language: Optional language (default: Ukrainian).
    """
    text = arguments.get("text")
    context = arguments.get("context", "General Content")
    language = arguments.get("language", "Ukrainian")

    if not text:
        return {"error": "Missing 'text' argument."}

    if not model:
        return {"error": "AI Model not configured (Missing GEMINI_API_KEY)."}

    try:
        # Check if it's a transcription request (hacky routing within skill for now)
        if arguments.get("audio_path"):
            audio_path = arguments.get("audio_path")
            audio_file = genai.upload_file(audio_path)
            prompt = "Listen to this audio carefully and provide a full, accurate transcription. Then provide a brief summary of the key points."
            response = model.generate_content([prompt, audio_file])
            return {"transcript": response.text, "status": "success"}

        prompt = f"""
        Analyze the following content and provide a comprehensive summary in {language}.
        
        CONTEXT: {context}
        
        Structure:
        1. 📌 **Main Topic** (1 sentence)
        2. 🔑 **Key Points** (Bullet points)
        3. 💡 **Conclusions**
        
        INPUT TEXT:
        {text[:50000]} 
        """
        
        response = model.generate_content(prompt)
        return {
            "summary": response.text,
            "status": "success"
        }
    except Exception as e:
        return {"error": f"Summarization failed: {str(e)}"}
