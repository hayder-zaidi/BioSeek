import os
from dotenv import load_dotenv

load_dotenv()

# --- CLÉS API (À mettre dans un fichier .env ou ici directement) ---
QDRANT_URL = os.getenv("QDRANT_URL", "https://ba523fdb-eb75-4bfc-9cdb-221ef5273f8c.europe-west3-0.gcp.cloud.qdrant.io")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.S0ImbMJeSVUp9LqlEW1Iy3MESKoS_gO0TSWeCvhSHUs")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCyZaEdaeIwp4vEgdBvbxZMIuFSKb2KRjI")

# --- CONFIGURATION SCIENTIFIQUE ---
COLLECTION_TEXT_NAME = "bio_knowledge_base"
COLLECTION_IMAGES_NAME = "bio_images"
# Modèle spécialisé pour le biomédical (Sortie: 768 dimensions)
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
VECTOR_SIZE = 768

# Email pour NCBI (Obligatoire pour ne pas être banni)
ENTREZ_EMAIL = "balazihsan@gmail.com"



