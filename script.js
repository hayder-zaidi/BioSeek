// --- CONFIGURATION ---
const API_URL = "http://127.0.0.1:8000/ask_multimodal";

// --- ÉLÉMENTS DOM ---
const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const attachBtn = document.getElementById('attach-btn');
const fileInput = document.getElementById('file-input');
const fileIndicator = document.getElementById('file-indicator');

let selectedFile = null;

// --- ÉVÉNEMENTS ---

// 1. Clic sur le trombone -> Ouvre le sélecteur de fichier
attachBtn.addEventListener('click', () => fileInput.click());

// 2. Fichier sélectionné -> Met à jour la variable et l'interface
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        selectedFile = e.target.files[0];
        fileIndicator.style.display = 'block'; // Affiche le point vert
        attachBtn.style.color = '#10b981'; // Change la couleur du trombone
    }
});

// 3. Envoi du message
sendBtn.addEventListener('click', handleSend);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault(); // Empêche le saut de ligne
        handleSend();
    }
});

// --- FONCTIONS ---

async function handleSend() {
    const text = userInput.value.trim();

    // On ne fait rien si vide et pas de fichier
    if (!text && !selectedFile) return;

    // 1. Afficher le message utilisateur
    addMessage(text, 'user', selectedFile);
   
    // Reset de l'input
    userInput.value = "";
   
    // 2. Afficher "Analyse en cours..."
    const loadingId = addLoadingMessage();

    // 3. Préparer les données pour le Backend (FormData)
    const formData = new FormData();
    formData.append('question', text || "Analyse ce fichier."); // Fallback si pas de texte
    if (selectedFile) {
        formData.append('file', selectedFile);
    }

    try {
        // --- APPEL AU BACKEND PYTHON ---
        const response = await fetch(API_URL, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error("Erreur serveur");

        const data = await response.json();

        // 4. Supprimer le message de chargement
        removeMessage(loadingId);

        // 5. Afficher la réponse de l'IA
        addMessage(data.answer, 'ai', null, data.db_images);

    } catch (error) {
        removeMessage(loadingId);
        addMessage("❌ Erreur de connexion au backend. Vérifiez que `backend.py` est lancé.", 'ai');
        console.error(error);
    }

    // Reset du fichier après envoi
    selectedFile = null;
    fileInput.value = "";
    fileIndicator.style.display = 'none';
    attachBtn.style.color = '';
}

function addMessage(text, sender, localImage = null, dbImages = []) {
    const div = document.createElement('div');
    div.classList.add('message', sender);

    // Contenu HTML
    let contentHtml = '';
   
    // Si c'est l'IA, on met l'avatar
    if (sender === 'ai') {
        contentHtml += `<div class="avatar"><i class="fa-solid fa-robot"></i></div>`;
    }

    contentHtml += `<div class="content">`;

    // 1. Texte (Converti du Markdown vers HTML)
    // Si c'est l'utilisateur, texte brut. Si c'est l'IA, Markdown parsé.
    if (sender === 'ai') {
        contentHtml += marked.parse(text);
    } else {
        contentHtml += `<p>${text}</p>`;
    }

    // 2. Image locale (uploadée par l'user)
    if (localImage) {
        const url = URL.createObjectURL(localImage);
        contentHtml += `<img src="${url}" class="chat-image" alt="Upload">`;
    }

    // 3. Images renvoyées par la Base de Données (RAG)
    if (dbImages && dbImages.length > 0) {
        contentHtml += `<div style="margin-top:15px; border-top:1px solid rgba(255,255,255,0.1); padding-top:10px;">
                            <small style="color:#10b981;">📚 Références visuelles trouvées :</small><br>`;
        dbImages.forEach(img => {
            // Le backend renvoie parfois des liens relatifs ou absolus.
            // Si c'est relatif (static/...), on ajoute le domaine localhost.
            // Cependant, votre backend renvoie des URL d'images web (http...) OU locales.
           
            contentHtml += `
                <div style="display:inline-block; margin:5px; max-width:45%; vertical-align:top;">
                    <img src="${img.url}" class="chat-image" style="margin-top:0;">
                    <br><small style="color:#ccc; font-size:0.7em;">${img.caption}</small>
                </div>`;
        });
        contentHtml += `</div>`;
    }

    contentHtml += `</div>`; // Fin .content

    div.innerHTML = contentHtml;
    chatContainer.appendChild(div);
    chatContainer.scrollTop = chatContainer.scrollHeight; // Scroll vers le bas
}

function addLoadingMessage() {
    const id = "loading-" + Date.now();
    const div = document.createElement('div');
    div.classList.add('message', 'ai');
    div.id = id;
    div.innerHTML = `
        <div class="avatar"><i class="fa-solid fa-circle-notch fa-spin"></i></div>
        <div class="content"><p><i>Analyse biomédicale en cours...</i></p></div>
    `;
    chatContainer.appendChild(div);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return id;
}

function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

