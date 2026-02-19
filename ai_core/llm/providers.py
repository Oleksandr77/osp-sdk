from typing import List, Dict, Any, Optional
import os
import json
import logging

logger = logging.getLogger(__name__)

class LLMProvider:
    """Abstract base class for LLM providers."""
    def chat_completion(self, messages: List[Dict[str, Any]], tools: List[Dict] = None, image_data: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates a completion from the LLM.
        :param messages: List of {"role": "user/system", "content": "..."}
        :param tools: List of function definitions (OpenAI format)
        :param image_data: Base64 encoded image string (optional)
        :return: JSON response with content or tool_calls
        """
        raise NotImplementedError

class MockLLM(LLMProvider):
    """Heuristic-based mock for testing without API keys."""
    def chat_completion(self, messages: List[Dict[str, Any]], tools: List[Dict] = None, image_data: Optional[str] = None) -> Dict[str, Any]:
        content = messages[-1]["content"]
        lower_content = content.lower()
        
        # Mock Vision Response
        if image_data:
            return {"content": "I see an image. Since I am a Mock LLM, I'll guess it's a cat or a diagram of OSP architecture."}
        
        allowed_tool_names = [t["function"]["name"] for t in tools] if tools else None
        
        # Simple heuristics to simulate "Intelligence"
        if "youtube" in lower_content or "video" in lower_content:
             # Check if allowed
             target = "org.antigravity.youtube.analyzer"
             if allowed_tool_names is None or target in allowed_tool_names:
                 # Simulate tool call
                 import re
                 url_match = re.search(r'(https?://[^\s]+)', content)
                 url = url_match.group(0) if url_match else "https://youtube.com/watch?v=mock"
                 
                 return {
                     "content": None,
                     "tool_calls": [{
                         "function": {
                             "name": target,
                             "arguments": json.dumps({"url": url})
                         }
                     }]
                 }
        
        if "drive" in lower_content or "file" in lower_content:
            target = "org.antigravity.google.drive"
            if allowed_tool_names is None or target in allowed_tool_names:
                # "search drive for elephants" -> query="elephants"
                query = content.split("for")[-1].strip() if "for" in content else "file"
                return {
                     "content": None,
                     "tool_calls": [{
                         "function": {
                             "name": target,
                             "arguments": json.dumps({"query": query})
                         }
                     }]
                 }

        return {"content": "I am a mock LLM and I didn't understand that."}

class GeminiLLM(LLMProvider):
    """Adapter for Google Gemini (Generative AI)."""
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning("GeminiLLM initialized without API Key. Will act as Mock if called.")
            
    def chat_completion(self, messages: List[Dict[str, Any]], tools: List[Dict] = None, image_data: Optional[str] = None) -> Dict[str, Any]:
        if not self.api_key:
            return MockLLM().chat_completion(messages, tools, image_data)
            
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            
            # Select Model
            model_name = "gemini-1.5-flash" if image_data else "gemini-1.5-flash" # Use Flash for speed
            model = genai.GenerativeModel(model_name)
            
            # Prepare Content
            prompt_parts = []
            
            # System Prompt (Gemini API handles system instructions differently in v1beta, 
            # but for simple generation we can prepend)
            system_msg = next((m for m in messages if m["role"] == "system"), None)
            if system_msg:
                prompt_parts.append(system_msg["content"])
                
            user_msg = next((m for m in reversed(messages) if m["role"] == "user"), None)
            if user_msg:
                prompt_parts.append(user_msg["content"])
                
            # Add Image if present
            if image_data:
                import base64
                from io import BytesIO
                from PIL import Image
                
                try:
                    # Remove header if present (data:image/jpeg;base64,...)
                    if "base64," in image_data:
                        image_data = image_data.split("base64,")[1]
                        
                    image_bytes = base64.b64decode(image_data)
                    img = Image.open(BytesIO(image_bytes))
                    prompt_parts.append(img)
                except Exception as e:
                    logger.error(f"Failed to process image: {e}")
                    return {"error": f"Image processing failed: {str(e)}"}

            # Generate
            # Note: Tool calling with python `google-generativeai` is complex. 
            # For this Phase 13 PoC, we prioritize Vision > Tools if image is present.
            # Or we implement tools properly if no image.
            
            if tools and not image_data:
                 # TODO: Implement proper Tool Mapping for Gemini
                 # For now, we fallback to text generation
                 pass

            response = model.generate_content(prompt_parts)
            return {"content": response.text}

        except ImportError:
            logger.error("google-generativeai not installed")
            return {"error": "google-generativeai library missing"}
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            return {"error": str(e)}

def get_llm_provider() -> LLMProvider:
    """Factory to get the best available provider."""
    # Always prefer Real Gemini if key exists
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
         return GeminiLLM()
    return MockLLM()
