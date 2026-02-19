import os
import sys
import json
from typing import Dict, Any, List, Optional
import logging
from .skill_manager import SkillManager
from .memory.memory_store import MemoryStore, MemoryScope

logger = logging.getLogger(__name__)

class AgentSession:
    """
    Represents an active agent session with specific expertise and shared memory.
    """
    def __init__(self, agent_id: str, expertise_profile: Dict[str, Any], skill_manager: SkillManager):
        self.session_id = agent_id # For now, simple mapping
        self.expertise = expertise_profile
        self.memory = MemoryStore()
        self.skill_manager = skill_manager
        self.active_skills = []
        
        # Load skills from profile
        self._load_skills()
        # Initialize memory with persona context
        self._init_memory()

    def _load_skills(self):
        # Flatten skill groups into a list of skill_ids
        # This is a simplified implementation. Real one would parse SkillGroupManifests.
        # For now, we assume expertise_profile directly lists skills or groups we can resolve.
        
        # NOTE: In a full implementation, we would load SkillGroupManifests here.
        # For this PoC, we will assume 'skill_groups' in expertise are just lists of skill_ids,
        # or we might need to look them up.
        pass

    def _init_memory(self):
        persona = self.expertise.get('persona', {})
        self.memory.set("agent.persona.system_prompt", persona.get('system_prompt'), MemoryScope.SESSION)
        self.memory.set("agent.persona.tone", persona.get('tone'), MemoryScope.SESSION)

class AgentManager:
    """
    Manages higher-level Agent constructs (Expertise, Skill Groups).
    """
    def __init__(self, skill_manager: SkillManager, degradation_controller=None, vector_db=None):
        self.skill_manager = skill_manager
        self.degradation_controller = degradation_controller
        self.vector_db = vector_db
        self.active_sessions: Dict[str, AgentSession] = {}
        self.schemas_dir = os.path.join(os.path.dirname(__file__), "../../schemas") # Mock path
        
    def create_session(self, expertise_profile: Dict[str, Any]) -> AgentSession:
        """
        Creates a new agent session based on an expertise profile.
        """
        import uuid
        session_id = str(uuid.uuid4())
        session = AgentSession(session_id, expertise_profile, self.skill_manager)
        self.active_sessions[session_id] = session
        logger.info(f"Created AgentSession {session_id} for expertise '{expertise_profile.get('name')}'")
        return session

    # ... (inside AgentManager)

    def execute_agent(self, session_id: str, input_text: str, image_data: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes a request within an agent session using LLM for orchestration.
        Supports Image Data for Vision.
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        # 1. Update Memory
        session.memory.set("input.text", input_text, MemoryScope.SESSION)
        
        # 2. Get LLM Provider
        from .llm.providers import get_llm_provider
        llm = get_llm_provider()
        
        # 3. Construct Prompt / Messages
        system_prompt = session.memory.get("agent.persona.system_prompt", MemoryScope.SESSION) or "You are a helpful agent."
        
        # --- RAG INTEGRATION START ---
        rag_context = ""
        if self.vector_db and not image_data: # Skip RAG if handling image to reduce tokens/complexity
             try:
                 # Search for relevant knowledge
                 results = self.vector_db.search(input_text, n_results=3)
                 if results:
                     rag_context = "\n\nRELEVANT KNOWLEDGE FROM MEMORY:\n"
                     for r in results:
                         rag_context += f"- [{r['metadata'].get('category', 'General')}] {r['metadata'].get('title', 'Untitled')}: {r['text'][:300]}...\n"
                     
                     logger.info(f"RAG retrieved {len(results)} context items.")
             except Exception as e:
                 logger.error(f"RAG Search failed: {e}")
        
        if rag_context:
            system_prompt += rag_context
        # --- RAG INTEGRATION END ---

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_text}
        ]
        
        # 4. Define Tools (Skills)
        # Get all available skills (in a real scenario, this would be filtered by ExpertiseProfile permissions)
        all_skills = list(self.skill_manager.skills.values())
        
        # 4a. Hybrid Routing (Stage 1 + Stage 2)
        # --------------------------------------
        
        # Ensure skills are indexed (optimally this should be done on startup)
        # user might add skills at runtime, so we do it here loosely or check hash
        if self.vector_db:
             skill_metas = [s["metadata"] for s in all_skills]
             self.vector_db.index_skills(skill_metas) # Idempotent-ish upsert

        # Stage 1: Lexical (BM25)
        from .routing.deterministic import DeterministicRouter
        router = DeterministicRouter()
        all_metas = [s["metadata"] for s in all_skills]
        
        lexical_candidates = router.filter_candidates(input_text, all_metas, top_k=5)
        
        # Stage 2: Semantic (Vector)
        semantic_candidates = []
        if self.vector_db:
            semantic_candidates = self.vector_db.search_skills(input_text, n_results=5)
            
        # Merge Candidates (Union)
        # We prefer Semantic for understanding intent, but Lexical for precise keywords
        final_candidates = {}
        
        for c in lexical_candidates:
            c["_source"] = "lexical"
            final_candidates[c["id"]] = c
            
        for c in semantic_candidates:
            # If already exists, we could boost score
            if c["id"] in final_candidates:
                final_candidates[c["id"]]["_routing_score"] += c["score"] # Boost
                final_candidates[c["id"]]["_source"] = "hybrid"
            else:
                # Need to map back to full metadata format if vector returns partial
                # Our vector search returns 'metadata' which is the dict
                # But let's ensure consistency
                meta = c["metadata"]
                meta["_routing_score"] = c["score"]
                meta["_source"] = "semantic"
                final_candidates[c["id"]] = meta
                
        # Sort by hybrid score
        sorted_candidates = sorted(final_candidates.values(), key=lambda x: x.get("_routing_score", 0), reverse=True)
        filtered_metas = sorted_candidates[:5] # Top 5 generic

        # Define tools for LLM
        openai_tools = []
        for meta in filtered_metas:
            tool_def = {
                "type": "function",
                "function": {
                    "name": meta["id"],
                    "description": meta.get("description", ""),
                    "parameters": {
                        "type": "object",
                        "properties": meta.get("parameters", {}),
                        "required": [] 
                    }
                }
            }
            openai_tools.append(tool_def)
            
        logger.info(f"Hybrid Routing candidates: {[m['id'] for m in filtered_metas]}")

        # 5. Routing Decision (LLM vs Deterministic based on Degradation)
        skill_result = None
        target_skill_id = None
        arguments = {}
        processed_via = "Hybrid Routing (Stage 1: Deterministic -> Stage 2: LLM)"

        # Determine if LLM is allowed based on degradation level
        should_use_llm = self.degradation_controller.should_use_llm() if self.degradation_controller else True
        current_level_name = self.degradation_controller.current_level.name if self.degradation_controller else "D0_NORMAL"

        if should_use_llm:
            # D0: Use LLM
            response = llm.chat_completion(messages, tools=openai_tools, image_data=image_data)
            
            if response.get("tool_calls"):
                tool_call = response["tool_calls"][0]
                target_skill_id = tool_call["function"]["name"]
                arguments_json = tool_call["function"]["arguments"]
                arguments = json.loads(arguments_json) if isinstance(arguments_json, str) else arguments_json
                logger.info(f"LLM routed to {target_skill_id} with args {arguments}")
            else:
                skill_result = {"message": response.get("content")}
        
        else:
            # D1/D2: Deterministic Execution Only (No LLM)
            # Pick first candidate from Stage 1
            if filtered_metas:
                target_meta = filtered_metas[0]
                target_skill_id = target_meta["id"]
                processed_via = f"Degraded Routing (Stage 1 Only: {current_level_name})"
                
                # Simple Heuristic Parameter Extraction (Fallback)
                import re
                if "youtube" in target_skill_id:
                    url_match = re.search(r'(https?://[^\s]+)', input_text)
                    if url_match: arguments = {"url": url_match.group(0)}
                elif "drive" in target_skill_id:
                    # simplistic extraction
                    parts = input_text.split("for")
                    if len(parts) > 1: arguments = {"query": parts[-1].strip()}
                    else: arguments = {"query": input_text}
                
                logger.info(f"Degraded Routing selected {target_skill_id} with args {arguments}")
            else:
                skill_result = {"message": "Service degraded. No skill matched and Chat is disabled."}

        # 6. Execute Skill (if selected) — Generic dispatch via SkillManager
        if target_skill_id:
            try:
                tools_module = self.skill_manager.get_skill_tools(target_skill_id)
                if tools_module and hasattr(tools_module, 'execute'):
                    result_data = tools_module.execute(arguments)
                else:
                    result_data = {"error": f"Skill '{target_skill_id}' not found or has no execute()"}
                
                skill_result = result_data
                session.memory.set("last.result", skill_result, MemoryScope.SESSION)
                
            except Exception as e:
                logger.error(f"Skill Execution Error for {target_skill_id}: {e}")
                skill_result = {"error": str(e)}
        elif skill_result is None: # If no skill was targeted AND skill_result wasn't set by LLM chat or degraded routing
             skill_result = {"message": "No skill executed."}


        return {
            "session_id": session_id,
            "status": "success",
            "target_skill": target_skill_id,
            "result": skill_result,
            "memory_snapshot": session.memory.list(MemoryScope.SESSION),
            "message": processed_via
        }

    def delegate_task(self, from_session_id: str, to_role: str, task_description: str) -> Dict[str, Any]:
        """
        Delegates a task from one agent to a specialized sub-agent (Swarm Mode).
        """
        logger.info(f"Swarm Delegation: {from_session_id} -> {to_role} : {task_description[:50]}...")
        
        # 1. Create/Get Sub-Agent based on role
        # in a real system, we'd have a pool. Here we create ad-hoc.
        role_prompts = {
            "researcher": "You are an expert Researcher. Search the web and memory to provide comprehensive reports.",
            "coder": "You are a Senior Software Engineer. Write clean, efficient, and well-documented Python code.",
            "analyst": "You are a Data Analyst. Interpret data and provide key insights."
        }
        
        system_prompt = role_prompts.get(to_role.lower(), "You are a helpful assistant.")
        
        sub_session = self.create_session({
            "name": f"Swarm-{to_role.capitalize()}",
            "role": to_role,
            "system_prompt": system_prompt
        })
        
        # 2. Execute Task
        result = self.execute_agent(sub_session.session_id, task_description)
        
        # 3. Clean up (optional, or keep alive for context)
        # self.active_sessions.pop(sub_session.session_id) 
        
        return {
            "delegated_to": sub_session.session_id,
            "role": to_role,
            "result": result
        }
