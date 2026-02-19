import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import os
import uuid
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

class VectorHandler:
    def __init__(self, persist_directory=None):
        if not persist_directory:
            # Default to project structure: 10_Business_Admin/Knowledge_Base/03_System/chroma_db
            # Assuming this script is in 06_Operations/ai_core/vector_handler.py
            # So we go up 3 levels: ../../../
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            persist_directory = os.path.join(base_dir, "10_Business_Admin", "Knowledge_Base", "03_System", "chroma_db")
        
        self.persist_directory = persist_directory
        
        # Ensure parent directory exists
        path_to_create = os.path.dirname(self.persist_directory)
        if not os.path.exists(path_to_create):
            os.makedirs(path_to_create)
            
        print(f"Initializing Vector DB at: {self.persist_directory}")
        
        # Initialize Client
        try:
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            # Create or get collection
            self.collection = self.client.get_or_create_collection(name="antigravity_knowledge")
            print("Vector DB initialized successfully.")
        except Exception as e:
            print(f"Error initializing ChromaDB: {e}")
            self.client = None
            self.collection = None

        # Initialize Embedding Model (lightweight)
        print("Loading embedding model...")
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            print("Embedding model loaded.")
        except Exception as e:
            print(f"Error loading embedding model: {e}")
            self.model = None

    def add_document(self, text, metadata=None):
        """
        Adds a document to the vector database.
        Request: text (str), metadata (dict)
        Returns: document_id (str)
        """
        if not text or not self.collection or not self.model:
            return None
            
        try:
            # Generate ID
            doc_id = str(uuid.uuid4())
            
            # Generate Embedding
            embedding = self.model.encode(text).tolist()
            
            # Prepare Metadata
            if metadata is None:
                metadata = {}
            
            # Ensure metadata values are supported types (str, int, float, bool)
            clean_metadata = {}
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_metadata[k] = v
                else:
                    clean_metadata[k] = str(v)
            
            # Add to Collection
            self.collection.add(
                documents=[text],
                embeddings=[embedding],
                metadatas=[clean_metadata],
                ids=[doc_id]
            )
            return doc_id
        except Exception as e:
            print(f"Error adding document: {e}")
            return None

    def search(self, query, n_results=5):
        """
        Searches for similar documents.
        Returns: list of results with metadata and distance.
        """
        if not query or not self.collection or not self.model:
            return []
            
        try:
            # Generate Query Embedding
            query_embedding = self.model.encode(query).tolist()
            
            # Search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            # Format Results
            formatted_results = []
            if not results['ids']:
                return []
                
            ids = results['ids'][0]
            distances = results['distances'][0]
            metadatas = results['metadatas'][0]
            documents = results['documents'][0]
            
            for i in range(len(ids)):
                formatted_results.append({
                    'id': ids[i],
                    'score': 1 - distances[i], # Convert distance to similarity score approx
                    'metadata': metadatas[i],
                    'text': documents[i]
                })
                
            return formatted_results
        except Exception as e:
            print(f"Error searching: {e}")
            return []

    def count(self):
        if self.collection:
            return self.collection.count()
        return 0

    def reset(self):
        """Clears the database"""
        if self.client:
            self.client.delete_collection("antigravity_knowledge")
            self.collection = self.client.get_or_create_collection(name="antigravity_knowledge")

    def index_skills(self, skills: list):
        """
        Indexes skill definitions for semantic routing.
        skills: List of dicts (metadata)
        """
        if not self.collection or not self.model:
            return
            
        try:
            # We create a separate collection or use a prefix in ID?
            # Let's use a separate collection for skills to avoid polluting knowledge.
            skill_collection = self.client.get_or_create_collection(name="antigravity_skills")
            
            # Clear old skills to ensure sync (simple but effective for small sets)
            # Or we can upsert. Let's upsert based on ID.
            
            ids = []
            docs = []
            metadatas = []
            embeddings = []
            
            for skill in skills:
                sid = skill["id"]
                # Create semantic representation
                name = skill.get("name", "")
                desc = skill.get("description", "")
                keywords = " ".join(skill.get("activation_keywords", []))
                text = f"{name}: {desc}. Keywords: {keywords}"
                
                ids.append(sid)
                docs.append(text)
                metadatas.append(skill) # Store full metadata for recovery
                
            embeddings = self.model.encode(docs).tolist()
            
            skill_collection.upsert(
                ids=ids,
                documents=docs,
                embeddings=embeddings,
                metadatas=metadatas
            )
            print(f"Indexed {len(skills)} skills into Vector DB.")
            
        except Exception as e:
            print(f"Error indexing skills: {e}")

    def search_skills(self, query: str, n_results=5):
        """
        Semantically searches for skills.
        """
        if not self.client or not self.model:
            return []
            
        try:
            skill_collection = self.client.get_collection(name="antigravity_skills")
            query_embedding = self.model.encode(query).tolist()
            
            results = skill_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            formatted = []
            if not results['ids']: return []
            
            ids = results['ids'][0]
            distances = results['distances'][0]
            metadatas = results['metadatas'][0]
            
            for i in range(len(ids)):
                formatted.append({
                    "id": ids[i],
                    "score": 1 - distances[i],
                    "metadata": metadatas[i]
                })
            return formatted
            
        except Exception as e:
            # Collection might not exist yet
            return []

if __name__ == "__main__":
    # Test script
    vh = VectorHandler()
    
    # Add dummy data
    print("Adding test data...")
    try:
        vh.add_document("Bitcoin is a decentralized digital currency.", {"category": "crypto", "source": "test"})
        vh.add_document("The sun is a star at the center of the solar system.", {"category": "space", "source": "test"})
        
        # Search
        print("Searching for 'money'...")
        results = vh.search("money")
        for r in results:
            print(f"[{r['score']:.2f}] {r['text']}")
            
    except Exception as e:
        print(f"Test failed: {e}")
