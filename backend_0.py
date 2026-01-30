import os
import shutil
import uuid
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer, CrossEncoder  # <--- Added CrossEncoder
import google.generativeai as genai
from collections import defaultdict
from PIL import Image
import config

# --- INITIALISATION ---
app = FastAPI()

# Création automatique des dossiers
os.makedirs("static/images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

print("🔌 Démarrage du Backend Bio-Médical (Mode AGENT + RE-RANKING)...")

# --- CONNEXIONS API & MODÈLES ---
try:
    # 1. Le modèle pour la recherche rapide (Vecteurs)
    encoder = SentenceTransformer(config.EMBEDDING_MODEL)
    
    # 2. Le modèle pour la précision (Re-Ranking) - NOUVEAU 🚀
    # Ce modèle est plus lent mais beaucoup plus intelligent pour trier les résultats.
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
        
        # 1. ÉTAPE 1 : Récupération large (On demande 10 résultats au lieu de 2)
        hits_text = qdrant.query_points(
            collection_name="bio_knowledge_base",
            query=vector,
            limit=10  # On ratisse large
        ).points

        # 2. ÉTAPE 2 : Recherche d'images (Optionnel)
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

        # 3. ÉTAPE 3 : Re-Ranking (Le tri intelligent)
        # On prépare des paires [Question, Réponse potentielle] pour que le juge (CrossEncoder) décide.
        valid_hits = [hit for hit in hits_text if 'text' in hit.payload]
        
        if valid_hits:
            # On crée les paires [Query, Document Text]
            cross_inp = [[search_term, hit.payload['text']] for hit in valid_hits]
            
            # Le modèle donne un score de pertinence à chaque paire
            cross_scores = reranker.predict(cross_inp)
            
            # On combine les résultats avec leurs scores et on trie du meilleur au moins bon
            scored_hits = sorted(zip(valid_hits, cross_scores), key=lambda x: x[1], reverse=True)
            
            # On garde seulement les 3 MEILLEURS (Top 3)
            top_hits = [hit for hit, score in scored_hits[:3]]
            print(f"   👉 Re-Ranking: {len(hits_text)} candidats -> 3 meilleurs retenus.")
        else:
            top_hits = []

        # 4. Construction de la réponse pour l'Agent
        results_text = ""
        request_images_context["current"] = [] 

        # Ajout des textes triés
        for hit in top_hits:
            results_text += f"- Connaissance (Pertinence élevée): {hit.payload['text']}\n"
            
        # Ajout des images (On les garde telles quelles, le re-ranking d'images est plus complexe)
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

# Configuration stricte pour la compétition
agent_model = genai.GenerativeModel(
    'gemini-2.5-flash',
    tools=tools_list,
    system_instruction="""
    Tu es un assistant expert biomédical.
    Ta mission est de répondre aux questions scientifiques en utilisant PRÉCISÉMENT les informations trouvées via tes outils.
    
    Règles :
    1. Si la question est médicale, utilise l'outil 'search_medical_database'.
    2. Si l'outil ne renvoie rien, dis que tu ne sais pas. N'invente pas.
    3. Si la question n'est PAS médicale (ex: cuisine, sport, politique), refuse poliment de répondre.
    """
)

vision_model = genai.GenerativeModel('gemini-2.5-flash')

# --- ENDPOINTS (Identiques au code précédent) ---
class Query(BaseModel):
    question: str

@app.post("/upload_analyze")
async def upload_analyze(file: UploadFile = File(...)):
    try:
        file_extension = file.filename.split(".")[-1]
        unique_name = f"{uuid.uuid4()}.{file_extension}"
        file_path = f"static/images/{unique_name}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        img = Image.open(file_path)
        response = vision_model.generate_content(["Analyse cette image médicale en détail.", img])
        description = response.text
        
        vector = encoder.encode(description).tolist()
        qdrant.upsert(
            collection_name="bio_images",
            points=[models.PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "image_url": f"http://127.0.0.1:8002/{file_path}",
                    "caption": description,
                    "type": "uploaded_user",
                    "source": "Utilisateur"
                }
            )]
        )
        return {"filename": unique_name, "filepath": file_path, "analysis": description}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask")
async def ask_agent(query: Query):
    try:
        request_images_context["current"] = []
        
        # Agent Automatique
        chat = agent_model.start_chat(enable_automatic_function_calling=True)
        response = chat.send_message(query.question)
        
        return {
            "response": response.text,
            "images": request_images_context["current"]
        }
    except Exception as e:
        print(f"❌ Erreur Agent : {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
    uvicorn.run(app, host="127.0.0.1", port=8002)