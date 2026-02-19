import sys
import os
import asyncio
import logging

# Add path to find ai_core
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(current_dir, "../..")))

from ai_core.skill_manager import SkillManager

logging.basicConfig(level=logging.INFO)

async def test_invoice_skill():
    print("--- Testing Invoice Skill ---")
    
    # Init Manager
    skills_path = os.path.abspath(os.path.join(current_dir, "../../skills"))
    manager = SkillManager(skills_dir=skills_path)
    
    skill_id = "search_invoices"
    if skill_id in manager.skills:
        print(f"✅ Skill '{skill_id}' found.")
        
        # Load tools
        tools = manager.get_skill_tools(skill_id)
        if tools:
            print("✅ Tools module loaded.")
            
            # Find available profiles
            # Look for token_*.json in 06_Operations/integrations/google
            # current_dir is 06_Operations/ai_core/tests
            # we need 06_Operations/integrations/google
            ops_root = os.path.abspath(os.path.join(current_dir, "../../"))
            google_dir = os.path.join(ops_root, "integrations/google")
            
            profiles = []
            if os.path.exists(google_dir):
                for f in os.listdir(google_dir):
                    if f.startswith("token_") and f.endswith(".json"):
                        profiles.append(f.replace("token_", "").replace(".json", ""))
            
            print(f"Found profiles: {profiles}")
            
            if not profiles:
                 print("⚠️ No Google profiles found. Cannot test execution.")
                 return

            # Test execution on all profiles
            for profile in profiles:
                print(f"\n--- Testing on profile: {profile} ---")
                results = tools.search_top_invoices(days=21, profile_name=profile, limit=5)
                
                if isinstance(results, list):
                    print(f"✅ Found {len(results)} items:")
                    for item in results:
                        print(f"  - [{item['date']}] {item['sender']}: {item['subject']}")
                        print(f"    Link: {item['link']}")
                else:
                    print(f"ℹ️  {results}")
            
        else:
            print("❌ Tools module NOT loaded.")
    else:
        print(f"❌ Skill '{skill_id}' NOT found.")
        print(f"Loaded skills: {list(manager.skills.keys())}")

if __name__ == "__main__":
    asyncio.run(test_invoice_skill())
