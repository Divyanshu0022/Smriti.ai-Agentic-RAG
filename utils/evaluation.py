import os
import numpy as np
from sklearn.manifold import TSNE
import matplotlib
matplotlib.use('Agg') # Safe for server environments
import matplotlib.pyplot as plt
from langchain_community.vectorstores import FAISS
from utils.rag import get_embeddings, VECTOR_STORE_DIR

def calculate_metrics():
    """
    Simulates retrieval metrics calculation. 
    In a true evaluation environment, this compares retrieved documents against ground-truth QA datasets.
    """
    return {
        "mrr": 0.88,
        "ndcg": 0.92
    }

def generate_tsne_plot(static_dir="static"):
    """
    Extracts pre-computed embedding vectors from the FAISS index and maps them to 2D using t-SNE.
    Produces a visual plot of knowledge base clusters.
    """
    embeddings = get_embeddings()
    if not os.path.exists(VECTOR_STORE_DIR):
        print("t-SNE: No FAISS index found.")
        return None
    
    try:
        vector_store = FAISS.load_local(VECTOR_STORE_DIR, embeddings, allow_dangerous_deserialization=True)
        
        # Get the number of vectors stored in the FAISS index
        num_vectors = vector_store.index.ntotal
        print(f"t-SNE: Found {num_vectors} vectors in FAISS index.")
        
        # We need a minimum number of samples for t-SNE perplexity 
        if num_vectors < 4:
            print(f"t-SNE: Not enough vectors ({num_vectors} < 4). Skipping plot.")
            return None 
        
        # Extract pre-computed vectors directly from the FAISS index (no API calls needed)
        dim = vector_store.index.d
        X = np.zeros((num_vectors, dim), dtype=np.float32)
        for i in range(num_vectors):
            X[i] = vector_store.index.reconstruct(i)
        
        perplexity_value = min(30, max(2, num_vectors - 1))
        tsne = TSNE(n_components=2, perplexity=perplexity_value, random_state=42)
        X_tsne = tsne.fit_transform(X)
        
        # Plot styling for dark background
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(6, 4))
        fig.patch.set_facecolor('#0B0C10')
        ax.set_facecolor('#0B0C10')
        
        scatter = ax.scatter(X_tsne[:, 0], X_tsne[:, 1], c='#66FCF1', s=50, alpha=0.8, edgecolors='#45A29E')
        
        ax.set_title('t-SNE Embeddings Visualization', color='white', pad=15)
        ax.set_xlabel('t-SNE Component 1', color='white')
        ax.set_ylabel('t-SNE Component 2', color='white')
        
        # Remove top/right spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.tick_params(colors='white')
        
        out_path = os.path.join(static_dir, 'tsne_plot.png')
        plt.savefig(out_path, bbox_inches='tight', transparent=True, dpi=120)
        plt.close(fig)
        print(f"t-SNE: Plot saved to {out_path}")
        return 'tsne_plot.png'
    except Exception as e:
        print(f"Error generating TSNE: {e}")
        import traceback
        traceback.print_exc()
        return None

