import argparse
import os
import sys

def create_skill(name):
    print(f"🛠️  Scaffolding skill: {name}...")
    base_dir = name
    os.makedirs(os.path.join(base_dir, "scripts"), exist_ok=True)
    
    # metadata.yaml
    with open(os.path.join(base_dir, "metadata.yaml"), "w") as f:
        f.write(f"""id: {name}
description: Description for {name}
version: 1.0.0
author: User
triggers:
  - {name} command
""")
    
    # skill.md
    with open(os.path.join(base_dir, "skill.md"), "w") as f:
        f.write(f"""# {name} Skill
This skill does something useful.
""")

    # tools.py
    with open(os.path.join(base_dir, "scripts", "tools.py"), "w") as f:
        f.write(f"""def execute(args):
    return "Hello from {name}!"
""")
    
    print(f"✅ Skill {name} created successfully!")

def create_agent(name):
    print(f"🤖 Scaffolding agent: {name}...")
    base_dir = name
    os.makedirs(base_dir, exist_ok=True)
    
    # agent.yaml
    with open(os.path.join(base_dir, "agent.yaml"), "w") as f:
        f.write(f"""name: {name}
description: An OSP Agent
model: gemini-pro
skills:
  - osp.std.fs
  - osp.std.http
""")
    
    # main.py
    with open(os.path.join(base_dir, "main.py"), "w") as f:
        f.write("""from osp_core import Agent

def main():
    agent = Agent.load("agent.yaml")
    print(f"Agent {agent.name} is ready.")

if __name__ == "__main__":
    main()
""")

    print(f"✅ Agent {name} created successfully!")

def main():
    parser = argparse.ArgumentParser(description="OSP CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # New command
    new_parser = subparsers.add_parser("new", help="Create new resources")
    new_subparsers = new_parser.add_subparsers(dest="resource", help="Resource to create")

    # New Skill
    skill_parser = new_subparsers.add_parser("skill", help="Create a new skill")
    skill_parser.add_argument("name", help="Name of the skill")

    # New Agent
    agent_parser = new_subparsers.add_parser("agent", help="Create a new agent")
    agent_parser.add_argument("name", help="Name of the agent")

    args = parser.parse_args()

    if args.command == "new":
        if args.resource == "skill":
            create_skill(args.name)
        elif args.resource == "agent":
            create_agent(args.name)
        else:
            new_parser.print_help()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
