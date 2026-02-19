import os
import yaml
import sys

def generate_docs(skills_dir="skills", output_dir="docs/skills"):
    """
    Generates Markdown documentation for all skills in the directory.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"📖 Generating documentation from {skills_dir}...")
    
    for root, dirs, files in os.walk(skills_dir):
        if "metadata.yaml" in files:
            try:
                with open(os.path.join(root, "metadata.yaml"), "r") as f:
                    meta = yaml.safe_load(f)
                
                skill_id = meta.get("id", "unknown")
                doc_path = os.path.join(output_dir, f"{skill_id}.md")
                
                with open(doc_path, "w") as f:
                    f.write(f"# {meta.get('name', skill_id)}\n\n")
                    f.write(f"**ID**: `{skill_id}`\n")
                    f.write(f"**Description**: {meta.get('description', 'No description provided.')}\n\n")
                    
                    if "triggers" in meta:
                        f.write("## Triggers\n")
                        for t in meta["triggers"]:
                            f.write(f"- `{t}`\n")
                        f.write("\n")
                        
                    f.write("## Usage\n")
                    f.write("To use this skill, include its ID in your `agent.yaml` skills list.\n")
                
                print(f"✅ Generated docs for {skill_id}")
            except Exception as e:
                print(f"❌ Failed to generate docs for {root}: {e}")

if __name__ == "__main__":
    skills_path = sys.argv[1] if len(sys.argv) > 1 else "../skills"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "../docs/skills"
    generate_docs(skills_path, out_path)
