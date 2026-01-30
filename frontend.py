import streamlit as st
import requests
from PIL import Image

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Expert Bio-Médical", layout="wide", page_icon="🩺")
API_URL = "http://127.0.0.1:8002"  # Match the backend port here

# --- CSS POUR LE STYLE ---
st.markdown("""
    <style>
    .stTextArea textarea {font-size: 16px;}
    .reportview-container {background: #f0f2f6;}
    div.stButton > button:first-child {
        background-color: #0099ff;
        color: white;
        font-size: 20px;
        height: 3em;
        width: 100%;
        border-radius: 10px; 
    }
    </style>
""", unsafe_allow_html=True)

# --- TITRE ---
st.title("🩺 Assistant Expert & Analyse d'Images")
st.markdown("---")

# --- MISE EN PAGE : 2 COLONNES ---
col_input, col_result = st.columns([1, 2])

# === COLONNE DE GAUCHE : SAISIE ===
with col_input:
    st.header("1. Votre Requête")
    st.info("Posez une question ou envoyez une radio/schéma pour analyse.")
    
    with st.form("chat_form", clear_on_submit=False):
        # A. Upload
        uploaded_file = st.file_uploader("📷 Joindre une image (Optionnel)", type=["jpg", "png", "jpeg"])
        
        # B. Question
        user_question = st.text_area("✍️ Votre question scientifique :", height=150, placeholder="Ex: Décris l'anatomie de ce coeur. Ou explique l'insuline.")
        
        # C. Bouton
        submitted = st.form_submit_button("Envoyer à l'Expert 🚀")

    # Aperçu de l'image si uploadée
    if uploaded_file:
        st.image(uploaded_file, caption="Aperçu de votre image", use_container_width=True)

# === COLONNE DE DROITE : RÉSULTATS ===
with col_result:
    st.header("2. Analyse de l'IA")
    
    if submitted:
        if not user_question and not uploaded_file:
            st.warning("⚠️ Veuillez écrire une question ou mettre une image.")
        else:
            with st.spinner("🔄 Consultation de la base Qdrant et analyse Gemini..."):
                try:
                    # Préparation des fichiers
                    files = {}
                    if uploaded_file:
                        uploaded_file.seek(0)
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    
                    # Préparation des données
                    data = {"question": user_question if user_question else "Analyse cette image."}
                    
                    # Envoi au Backend
                    response = requests.post(f"{API_URL}/ask_multimodal", data=data, files=files)
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # A. La Réponse Texte
                        st.success("✅ Analyse terminée !")
                        st.markdown(f"### 📝 Rapport :\n{result['answer']}")
                        
                        st.markdown("---")
                        
                        # B. Les Images trouvées en Base de Données
                        db_images = result.get("db_images", [])
                        if db_images:
                            st.subheader(f"📚 {len(db_images)} Images de référence trouvées :")
                            
                            cols = st.columns(3) # 3 images par ligne
                            for i, img in enumerate(db_images):
                                with cols[i % 3]:
                                    st.image(img['url'], use_container_width=True)
                                    st.caption(f"**{img['caption']}**\n*(Source: {img['source']})*")
                        else:
                            st.info("ℹ️ Aucune image supplémentaire trouvée dans la base de connaissances.")
                            
                    else:
                        st.error(f"❌ Erreur Serveur ({response.status_code}) : {response.text}")
                
                except requests.exceptions.ConnectionError:
                    st.error("🚫 Impossible de contacter le Backend.")
                    st.warning("👉 Vérifiez que vous avez bien lancé 'python backend.py' dans l'autre terminal.")
    else:
        st.info("👈 Remplissez le formulaire à gauche pour commencer.")