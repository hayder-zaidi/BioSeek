# 🧬 BioSeek: Multimodal Biological Discovery System

## 🎯 Vision
BioSeek is designed to be a **multimodal discovery system** that connects diverse biological data types—text, sequences, structures, and experimental results.

Our goal is to move beyond simple keyword search to a system that can:
* **Find similar candidates** across different data modalities.
* **Propose design hypotheses** based on structural and functional similarity.
* **Prioritize promising variants** for wet-lab testing.

## 🏗️ Current Architecture 
The current prototype implements the **Sequence Discovery Module**:
* **Model:** Facebook ESM-2 (150M Parameters) for protein language modeling.
* **Database:** Qdrant Cloud (Vector Database) for semantic retrieval.
* **Data Source:** Live integration with UniProtKB (Review Status: True).
* **Interface:** Streamlit-based dashboard for real-time vector search.

**✅ What works today:**
- Ingesting protein sequences from UniProt.
- Generating high-dimensional vector embeddings (640-dim) representing protein structure.
- Performing semantic similarity searches (e.g., finding functional analogs even with low sequence identity).

---

## 🔮 Future Roadmap: Multimodal Integration
We are currently expanding the system to support the following data types and capabilities:

### Data Scope
* **📝 Text:** Integrating paper abstracts, protocols, and unstructured lab notes (RAG pipeline).
* **🖼️ Images:** Ingesting gel electrophoresis images, microscopy data, and spectral analysis.
* **🧪 Experimental Results:** Linking success/failure labels and measurement conditions to sequence data.

### Planned Features
**Cross-Modal Search:** Query a sequence to find relevant papers (Sequence-to-Text).
**Image Analysis:** Use CLIP-based models to index biological imagery.
**3D Visualization:** Integrated Py3Dmol viewer for structure comparison.

---

### Setup
1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/bioseek.git](https://github.com/YOUR_USERNAME/bioseek.git)
   cd bioseek