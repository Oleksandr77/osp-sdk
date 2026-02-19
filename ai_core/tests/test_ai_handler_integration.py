import sys
import os
import asyncio
import logging

# Add path to find ai_handler
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../integrations/telegram")))

from ai_handler import AIHandler

logging.basicConfig(level=logging.INFO)

async def test_integration():
    print("--- Testing AIHandler Integration ---")
    
    try:
        handler = AIHandler()
        if handler.skill_manager:
            print("✅ AIHandler initialized SkillManager successfully.")
            
            # Check if skill manager found the skills
            # Note: SkillManager inside AIHandler is init with default path "../skills" relative to ai_core
            # We need to make sure that path resolves correctly from where AIHandler runs usually.
            
            skills_count = len(handler.skill_manager.skills)
            print(f"Skills loaded by handler: {skills_count}")
            
            if skills_count > 0:
                 print("✅ Skills loaded correctly via AIHandler.")
            else:
                 print("⚠️ No skills loaded. Path execution context might be wrong.")
                 print(f"Handler Skill Dir: {handler.skill_manager.skills_dir}")
                 
        else:
            print("❌ AIHandler failed to init SkillManager.")
            
    except Exception as e:
        print(f"❌ Crash during initialization: {e}")

if __name__ == "__main__":
    asyncio.run(test_integration())
