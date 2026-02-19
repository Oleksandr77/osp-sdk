import os
import sys
import json
import logging
from tqdm import tqdm

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # Add 06_Operations

from ai_core.vector_handler import VectorHandler

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reindex_knowledge_base():
    """
    Scans the Knowledge Base directory and adds all entries to ChromaDB.
    """
    base_dir = "../../10_Business_Admin/Knowledge_Base"
    abs_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), base_dir))
    
    if not os.path.exists(abs_base_dir):
        logger.error(f"Knowledge Base directory not found: {abs_base_dir}")
        return

    logger.info(f"Scanning Knowledge Base at: {abs_base_dir}")
    
    # Initialize VectorDB
    try:
        vh = VectorHandler()
        if not vh.client:
            logger.error("Failed to initialize Vector Handler.")
            return
            
        # Optional: Reset DB? 
        # vh.reset() # Uncomment to clear before re-indexing
        
    except Exception as e:
        logger.error(f"VectorDB Init Error: {e}")
        return

    count = 0
    errors = 0

    # Walk through directory
    for root, dirs, files in os.walk(abs_base_dir):
        if "metadata.json" in files:
            meta_path = os.path.join(root, "metadata.json")
            summary_path = os.path.join(root, "summary.md")
            transcript_path = os.path.join(root, "transcript.txt")
            
            try:
                # Load Metadata
                with open(meta_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load Content
                content = ""
                if os.path.exists(summary_path):
                    with open(summary_path, 'r', encoding='utf-8') as f:
                        content += f"SUMMARY:\n{f.read()}\n\n"
                
                if os.path.exists(transcript_path):
                    with open(transcript_path, 'r', encoding='utf-8') as f:
                        content += f"TRANSCRIPT:\n{f.read()[:5000]}" # Limit size for embedding if needed
                
                # Prepare Metadata for DB
                skill = data.get('skill', 'General')
                direction = data.get('direction', 'Uncategorized')
                
                # Construct Embedding Text (Enriched)
                text_to_embed = f"{data.get('title')}\nSkill: {skill}\nDirection: {direction}\n{content}"
                
                db_metadata = {
                    "title": data.get('title', 'Untitled'),
                    "path": root,
                    "category": data.get('source', 'Unknown'),
                    "skill": skill,
                    "direction": direction,
                    "type": data.get('type', 'unknown'),
                    "date": data.get('date', '')
                }
                
                # Add to DB
                vh.add_document(text_to_embed, db_metadata)
                count += 1
                print(f"Index: {data.get('title')}")
                
            except Exception as e:
                logger.error(f"Failed to index {root}: {e}")
                errors += 1

    logger.info(f"✅ Re-indexing Complete!")
    logger.info(f"Total Documents: {count}")
    logger.info(f"Errors: {errors}")
    logger.info(f"Total in DB: {vh.count()}")

if __name__ == "__main__":
    reindex_knowledge_base()
