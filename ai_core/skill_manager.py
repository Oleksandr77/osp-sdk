import os
import yaml
import logging
import importlib.util
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SkillManager:
    def __init__(self, skills_dir: str = "../skills", model=None):
        """
        Initialize SkillManager.
        :param skills_dir: Path to the skills directory (relative to this file or absolute).
        :param model: GenerativeModel instance for intent detection (optional).
        """
        # Resolve absolute path for skills_dir
        if not os.path.isabs(skills_dir):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.skills_dir = os.path.join(base_dir, skills_dir)
        else:
            self.skills_dir = skills_dir

        self.model = model
        self.skill_registry = {}  # skill_id -> metadata
        self.loaded_skills = {}   # skill_id -> module
        
        # Load Standard Library Skills
        self._load_std_lib()
        self.load_skills()

    def _load_std_lib(self):
        """
        Loads the OSP Standard Library (osp-std).
        """
        try:
            from osp_std import fs, http, system
            
            std_skills = {
                "osp.std.fs": fs,
                "osp.std.http": http,
                "osp.std.system": system
            }
            
            for skill_id, module in std_skills.items():
                self.loaded_skills[skill_id] = module
                self.skill_registry[skill_id] = {
                    "id": skill_id, 
                    "name": skill_id.split(".")[-1].upper(),
                    "description": f"Standard Library Skill: {skill_id}",
                    "files": []
                }
                # Also add to the main skills dict for compatibility
                if not hasattr(self, 'skills'):
                    self.skills = {}
                self.skills[skill_id] = {
                    "metadata": self.skill_registry[skill_id],
                    "path": "internal",
                    "instruction": f"Standard Library Skill: {skill_id}",
                    "tools": module
                }
                print(f"📦 Loaded Standard Library: {skill_id}")
                
        except ImportError as e:
            print(f"⚠️ Failed to load osp-std: {e}")
    def load_skills(self):
        """Scans the skills directory and loads metadata for all found skills."""
        logger.info(f"Loading skills from: {self.skills_dir}")
        self.skills = {}

        if not os.path.exists(self.skills_dir):
            logger.warning(f"Skills directory not found: {self.skills_dir}")
            return

        # Walk through directories to find skill.yaml or metadata.yaml
        for root, dirs, files in os.walk(self.skills_dir):
            if "metadata.yaml" in files:
                self._load_skill_from_dir(root)

        logger.info(f"Loaded {len(self.skills)} skills: {list(self.skills.keys())}")

    def _load_skill_from_dir(self, skill_path: str):
        """Loads a single skill from a directory."""
        try:
            meta_path = os.path.join(skill_path, "metadata.yaml")
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = yaml.safe_load(f)

            skill_id = metadata.get("id")
            if not skill_id:
                logger.warning(f"Skill at {skill_path} missing 'id' in metadata.yaml")
                return

            # Load instruction (skill.md)
            skill_md_path = os.path.join(skill_path, "skill.md")
            instruction = ""
            if os.path.exists(skill_md_path):
                with open(skill_md_path, "r", encoding="utf-8") as f:
                    instruction = f.read()

            # Store skill data
            self.skills[skill_id] = {
                "metadata": metadata,
                "path": skill_path,
                "instruction": instruction,
                "tools": self._load_tools(skill_path)
            }
        except Exception as e:
            logger.error(f"Failed to load skill from {skill_path}: {e}")

    def _load_tools(self, skill_path: str):
        """Loads python tools if scripts/tools.py exists."""
        tools_path = os.path.join(skill_path, "scripts", "tools.py")
        if not os.path.exists(tools_path):
            return None
        
        try:
            spec = importlib.util.spec_from_file_location("skill_tools", tools_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            logger.error(f"Failed to load tools for {skill_path}: {e}")
            return None

    async def detect_intent(self, user_input: str) -> Optional[str]:
        """
        Determines which skill should handle the user input.
        Returns the skill_id or None.
        """
        # 1. Exact trigger match (Fast)
        user_lower = user_input.lower().strip()
        for skill_id, data in self.skills.items():
            triggers = data["metadata"].get("triggers", [])
            for trigger in triggers:
                if trigger.lower() in user_lower:
                    logger.info(f"Intent detected via trigger '{trigger}': {skill_id}")
                    return skill_id

        # 2. LLM Semantic Match (Slower but starter)
        # For now, we rely on triggers. In future steps, we can use vector search 
        # or a lightweight router call here.
        
        return None

    def get_skill_instruction(self, skill_id: str) -> str:
        """Returns the system prompt/instruction for a skill."""
        skill = self.skills.get(skill_id)
        if not skill:
            return ""
        return skill["instruction"]

    def get_skill_tools(self, skill_id: str):
        """Returns the module containing tools for the skill."""
        skill = self.skills.get(skill_id)
        if not skill:
            return None
        return skill["tools"]
