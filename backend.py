import os
import shutil
import uuid
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware # <--- NEW: For Browser Connection
from fastapi.responses import FileResponse # <--- NEW: To serve your HTML file
from pydantic import BaseModel
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer, CrossEncoder
import google.generativeai as genai
from collections import defaultdict
from PIL import Image
import config

# --- INITIALISATION ---
app = FastAPI()

# 1. SETUP CORS (Indispensable pour que le Frontend JS puisse parler au Backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Autorise toutes les origines (pour le dév)
    allow_credentials=True,
    allow_methods=["*"],  # Autorise GET, POST, etc.
    allow_headers=["*"],
)

# Création automatique des dossiers
os.makedirs("static/images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

print("🔌 Démarrage du Backend Bio-Médical (Mode HTML/JS + AGENT)...")

# --- CONNEXIONS API & MODÈLES ---
try:
    # 1. Le modèle pour la recherche rapide (Vecteurs)
    encoder = SentenceTransformer(config.EMBEDDING_MODEL)
    
    # 2. Le modèle pour la précision (Re-Ranking)
    reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    print("✅ Modèle de Re-Ranking chargé.")

    qdrant = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY)
    genai.configure(api_key=config.GEMINI_API_KEY)
    print("✅ Connexions API réussies.")
except Exception as e:
    print(f"❌ ERREUR DE CONNEXION : {e}")

# Stockage temporaire des images trouvées par l'agent
request_images_context = defaultdict(list)

# --- OUTIL (TOOL) AMÉLIORÉ ---
def search_medical_database(search_term: str):
    """
    Utilise cet outil pour rechercher des informations médicales, cliniques ou biologiques
    dans la base de connaissances vectorielle (Qdrant).
    """
    print(f"🕵️  Recherche Intelligente pour : '{search_term}'")
    
    try:
        vector = encoder.encode(search_term).tolist()
        
        # 1. ÉTAPE 1 : Récupération large
        hits_text = qdrant.query_points(
            collection_name="bio_knowledge_base",
            query=vector,
            limit=10 
        ).points

        # 2. ÉTAPE 2 : Recherche d'images
        hits_images = []
        try:
            if qdrant.collection_exists("bio_images"):
                hits_images = qdrant.query_points(
                    collection_name="bio_images",
                    query=vector,
                    limit=3
                ).points
        except:
            pass

        if not hits_text and not hits_images:
            return "Aucune information trouvée dans la base."

        # 3. ÉTAPE 3 : Re-Ranking
        valid_hits = [hit for hit in hits_text if 'text' in hit.payload]
        
        if valid_hits:
            cross_inp = [[search_term, hit.payload['text']] for hit in valid_hits]
            cross_scores = reranker.predict(cross_inp)
            scored_hits = sorted(zip(valid_hits, cross_scores), key=lambda x: x[1], reverse=True)
            top_hits = [hit for hit, score in scored_hits[:3]]
            print(f"   👉 Re-Ranking: {len(hits_text)} candidats -> 3 meilleurs retenus.")
        else:
            top_hits = []

        # 4. Construction de la réponse
        results_text = ""
        request_images_context["current"] = [] 

        for hit in top_hits:
            results_text += f"- Connaissance (Pertinence élevée): {hit.payload['text']}\n"
            
        for hit in hits_images:
            desc = hit.payload.get('caption', 'Image')
            url = hit.payload.get('image_url', '')
            results_text += f"- Description Image Trouvée: {desc}\n"
            
            if url:
                request_images_context["current"].append({"url": url, "desc": desc, "source": "Base de Données", "caption": desc})

        return results_text

    except Exception as e:
        print(f"⚠️ Erreur Search: {e}")
        return f"Erreur lors de la recherche: {str(e)}"

# --- CONFIGURATION DE L'AGENT ---
tools_list = [search_medical_database]

agent_model = genai.GenerativeModel(
    'gemini-2.5-flash',
    tools=tools_list,
    system_instruction="""
    Tu es un assistant expert biomédical.
    Ta mission est de répondre aux questions scientifiques en utilisant PRÉCISÉMENT les informations trouvées via tes outils.
    
    Règles :
    1. Si la question est médicale, utilise l'outil 'search_medical_database'.
    2. Utilise le format Markdown pour formater ta réponse (Gras, Listes).
    3. Si l'outil ne renvoie rien, dis que tu ne sais pas. N'invente pas.
    """
)

vision_model = genai.GenerativeModel('gemini-2.5-flash')

# --- NOUVEAUX ENDPOINTS POUR SERVIR LE FRONTEND ---
@app.get("/")
async def read_index():
    return FileResponse('index.html')

@app.get("/style.css")
async def read_css():
    return FileResponse('style.css')

@app.get("/script.js")
async def read_js():
    return FileResponse('script.js')

# --- API ENDPOINTS ---

@app.post("/ask_multimodal")
async def ask_multimodal(
    question: str = Form(...), 
    file: UploadFile = File(None)
):
    try:
        request_images_context["current"] = []
        user_prompt_parts = [question]

        if file:
            file_extension = file.filename.split(".")[-1]
            unique_name = f"{uuid.uuid4()}.{file_extension}"
            file_path = f"static/images/{unique_name}"
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            img = Image.open(file_path)
            user_prompt_parts.append(img)
            user_prompt_parts.append("Analyse cette image et utilise-la avec la question.")

        chat = agent_model.start_chat(enable_automatic_function_calling=True)
        response = chat.send_message(user_prompt_parts)

        return {
            "answer": response.text,
            "db_images": request_images_context["current"]
        }

    except Exception as e:
        print(f"❌ Erreur Multimodal : {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # MODIFICATION: Port 8000 pour correspondre à votre script.js
    uvicorn.run(app, host="127.0.0.1", port=8000)