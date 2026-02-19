import sys
import os
import asyncio
import logging

# Add parent directory to path to import SkillManager
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from ai_core.skill_manager import SkillManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestSkillManager")

async def test_manager():
    print("--- Testing SkillManager ---")
    
    # 1. Initialize
    # Point to the skills directory we just created
    skills_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../skills"))
    print(f"Skills Path: {skills_path}")
    
    manager = SkillManager(skills_dir=skills_path)
    
    # 2. Check loaded skills
    if "summarize_content" in manager.skills:
        print("✅ Skill 'summarize_content' loaded successfully.")
    else:
        print("❌ Failed to load 'summarize_content'.")
        print(f"Loaded skills: {list(manager.skills.keys())}")
        return

    # 3. Test Intent Detection (Exact Match)
    print("\n--- Testing Intent Detection ---")
    
    test_inputs = [
        ("Please summarize this text", "summarize_content"),
        ("Give me a summary", "summarize_content"),
        ("Hello world", None)
    ]
    
    for text, expected in test_inputs:
        result = await manager.detect_intent(text)
        status = "✅" if result == expected else "❌"
        print(f"{status} Input: '{text}' -> Detected: {result} (Expected: {expected})")

    # 4. Check Instruction
    instruction = manager.get_skill_instruction("summarize_content")
    if "Content Analyst" in instruction:
         print("\n✅ Instruction loaded correctly.")
    else:
         print("\n❌ Instruction loading failed.")

if __name__ == "__main__":
    asyncio.run(test_manager())
