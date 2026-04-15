import os
import time
import hashlib
import warnings
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# Suppress the deprecation warning from google.generativeai
import re
warnings.filterwarnings("ignore", category=FutureWarning, module="langchain_google_genai")

VECTOR_STORE_DIR = "faiss_index"

# ─── PII Detector (Security Feature) ─────────────────────────
def _detect_pii(text):
    """Simple regex scan for SSNs, excessive emails/phones."""
    pii_flags = []
    # SSN pattern (simple)
    if re.search(r'\b\d{3}-\d{2}-\d{4}\b', text):
        pii_flags.append("SSN Detected")
    # Email pattern
    if len(re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)) > 3:
        pii_flags.append("High Volume of Emails (PII Risk)")
    # Phone numbers
    if len(re.findall(r'\(?\b[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}\b', text)) > 3:
        pii_flags.append("High Volume of Phone Numbers (PII Risk)")
        
    if pii_flags:
        return "\n\n⚠️ **[SECURITY ALERT]**: " + ", ".join(pii_flags) + "\n"
    return ""

# ─── Simple In-Memory Response Cache ─────────────────────────
_response_cache = {}
MAX_CACHE_SIZE = 100

def _cache_key(query):
    return hashlib.md5(query.strip().lower().encode()).hexdigest()

def _get_cached(query):
    key = _cache_key(query)
    if key in _response_cache:
        entry = _response_cache[key]
        # Cache entries valid for 10 minutes
        if time.time() - entry['time'] < 600:
            return entry['data']
        else:
            del _response_cache[key]
    return None

def _set_cache(query, data):
    if len(_response_cache) >= MAX_CACHE_SIZE:
        # Evict oldest entry
        oldest_key = min(_response_cache, key=lambda k: _response_cache[k]['time'])
        del _response_cache[oldest_key]
    _response_cache[_cache_key(query)] = {'data': data, 'time': time.time()}

def clear_cache():
    """Clears the entire response cache."""
    _response_cache.clear()

# ─── Model Factories ─────────────────────────────────────────

# Global embeddings singleton to avoid recreating it on every query
_embeddings_instance = None

def get_embeddings():
    """Uses Google Generative AI Embeddings. Singleton pattern for performance."""
    global _embeddings_instance
    if _embeddings_instance is None:
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set in the environment variables.")
        _embeddings_instance = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=api_key,
        )
    return _embeddings_instance

# ─── Model Override (rate-limit safety net) ──────────────────
# Set to None to enable free model selection from the UI dropdown.
# Using the highest-tier model for maximum quality agentic outputs.
MODEL_OVERRIDE = None

def get_llm(model_name="gemini-2.5-pro"):
    """
    Model factory with override support.

    Display name → API name mapping (for reference):
      Gemini 2.5 Pro (Best)         → gemini-2.5-pro
      Gemini 2.5 Flash              → gemini-2.5-flash
      Gemini 2.5 Flash-Lite         → gemini-2.5-flash-lite
      Gemini 2.5 Flash (Preview)    → gemini-2.5-flash-preview-04-17
      Gemini 2.5 Pro (Preview)      → gemini-2.5-pro-preview-03-25
      Gemini 2.0 Flash              → gemini-2.0-flash

    To let the UI dropdown choose the model freely, set MODEL_OVERRIDE = None above.
    """
    effective_model = MODEL_OVERRIDE if MODEL_OVERRIDE else model_name
    return ChatGoogleGenerativeAI(model=effective_model)

# ─── Document Processing ─────────────────────────────────────

def get_full_text_from_uploads():
    """Concatenates text from current uploads. Highly optimized using cached .parsed.txt files."""
    upload_dir = 'uploads'
    full_text = ""
    if not os.path.exists(upload_dir):
        return ""
    
    # Fast path: Read pre-parsed text blobs
    files = os.listdir(upload_dir)
    for filename in files:
        if filename.endswith('.parsed.txt'):
            filepath = os.path.join(upload_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    orig_name = filename.replace('.parsed.txt', '')
                    full_text += f"\n\n--- DOCUMENT: {orig_name} ---\n\n"
                    full_text += f.read()
            except Exception as e:
                print(f"Error reading parsed cache for {filename}: {e}")
                
    # If we found parsed texts, return immediately
    if full_text:
        return full_text
        
    # Slow path fallback (legacy setup)
    for filename in files:
        if filename.endswith('.parsed.txt'): continue
        filepath = os.path.join(upload_dir, filename)
        try:
            if filepath.lower().endswith('.pdf'):
                loader = PyPDFLoader(filepath)
            else:
                loader = TextLoader(filepath, encoding='utf-8')
            docs = loader.load()
            full_text += f"\n\n--- DOCUMENT: {filename} ---\n\n"
            full_text += "\n".join([d.page_content for d in docs])
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            
    return full_text

def process_file(filepath):
    """
    Ingests PDF or text files, chunks them, and stores embeddings into FAISS vector store.
    Returns (chunk_count, full_text) — full_text is used for summary generation.
    """
    if filepath.lower().endswith('.pdf'):
        loader = PyPDFLoader(filepath)
    else:
        loader = TextLoader(filepath, encoding='utf-8')
    
    documents = loader.load()
    
    if not documents:
        raise ValueError("No content could be extracted from the uploaded file.")
    
    # Extract full text for summary generation
    full_text = "\n".join([doc.page_content for doc in documents])
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = text_splitter.split_documents(documents)
    
    if not chunks:
        raise ValueError("The document produced no text chunks. It may be empty or contain only images.")
    
    # Add source metadata to each chunk
    source_name = os.path.basename(filepath)
    for i, chunk in enumerate(chunks):
        chunk.metadata['source'] = source_name
        chunk.metadata['chunk_index'] = i
        
    # Optimization: Save parsed text to disk to speed up Long/Audit queries
    try:
        parsed_path = filepath + ".parsed.txt"
        with open(parsed_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
    except Exception as e:
        print(f"Warning: Could not save parsed cache: {e}")
    
    # Generate embeddings and store
    embeddings = get_embeddings()
    if os.path.exists(VECTOR_STORE_DIR):
        vector_store = FAISS.load_local(VECTOR_STORE_DIR, embeddings, allow_dangerous_deserialization=True)
        vector_store.add_documents(chunks)
    else:
        vector_store = FAISS.from_documents(chunks, embeddings)
        
    vector_store.save_local(VECTOR_STORE_DIR)
    
    # Clear cache since KB changed
    clear_cache()
    
    return len(chunks), full_text

# ─── Summary Generation ──────────────────────────────────────

def generate_summary(full_text, max_text_len=8000, model_name="gemini-2.5-flash-lite"):
    """Uses the LLM to generate a concise summary of the document."""
    llm = get_llm(model_name)
    
    # Truncate if very long to avoid token limits
    truncated = full_text[:max_text_len]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a professional document analyst. Generate a clear, structured summary of the following document. Include key topics, entities, and important facts. Keep the summary concise (150-300 words). Use bullet points where appropriate."),
        ("human", "{text}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"text": truncated})
    return response.content

# ─── RAG Query ────────────────────────────────────────────────

def query_rag(user_query, model_name="gemini-2.5-flash-lite"):
    """
    Queries FAISS with similarity scores and uses Gemini to format the final answer.
    Returns answer, chunks, similarity scores, sources, and timing info.
    """
    start_time = time.time()
    
    # Check cache first
    cached = _get_cached(user_query)
    if cached:
        cached['cached'] = True
        return cached
    
    embeddings = get_embeddings()
    if not os.path.exists(VECTOR_STORE_DIR):
        return {
            "answer": "The Knowledge Base is currently empty. Please upload documents before asking questions.",
            "chunks": [], "scores": [], "sources": [], "response_time_ms": 0, "cached": False
        }
    
    vector_store = FAISS.load_local(VECTOR_STORE_DIR, embeddings, allow_dangerous_deserialization=True)
    
    # Use similarity_search_with_score for explainability
    results_with_scores = vector_store.similarity_search_with_score(user_query, k=4)
    
    # Extract documents and scores
    context_docs = [doc for doc, score in results_with_scores]
    similarity_scores = [round(float(score), 4) for doc, score in results_with_scores]
    sources = list(set([doc.metadata.get('source', 'Unknown') for doc in context_docs]))
    
    # Build context string manually for the LLM
    context_str = "\n\n---\n\n".join([
        f"[Source: {doc.metadata.get('source', 'Unknown')} | Chunk {doc.metadata.get('chunk_index', '?')}]\n{doc.page_content}"
        for doc in context_docs
    ])
    
    # RAG prompt with source attribution instruction
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an advanced AI knowledge worker. Use the following retrieved context to answer the user's question with clarity, accuracy, and professionalism.

IMPORTANT RULES:
1. Base your answer ONLY on the provided context.
2. If the answer is not in the context, clearly state that.
3. When possible, mention which source document the information comes from.
4. Format your answer with proper markdown (bold, bullets, headers) for readability.

Context:
{context}"""),
        ("human", "{input}")
    ])
    
    llm = get_llm(model_name)
    chain = qa_prompt | llm
    response = chain.invoke({"context": context_str, "input": user_query})
    
    answer = response.content
    chunks = [doc.page_content for doc in context_docs]
    
    # Run PII detection on answer
    alert = _detect_pii(answer)
    if alert:
        answer = alert + answer
        
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    result = {
        "answer": answer,
        "chunks": chunks,
        "scores": similarity_scores,
        "sources": sources,
        "response_time_ms": elapsed_ms,
        "cached": False
    }
    
    # Cache the result
    _set_cache(user_query, result)
    
    return result

# ─── Query Stream Support ──────────────────────────────────────

def query_rag_stream(user_query, model_name="gemini-2.5-flash-lite"):
    """
    Returns a tuple of (metadata_dict, generator).
    The generator yields chunks of the LLM response text.
    """
    start_time = time.time()
    
    embeddings = get_embeddings()
    if not os.path.exists(VECTOR_STORE_DIR):
        def empty_gen():
            yield "The Knowledge Base is currently empty. Please upload documents before asking questions."
        return {"chunks": [], "scores": [], "sources": [], "response_time_ms": 0, "cached": False}, empty_gen()
        
    vector_store = FAISS.load_local(VECTOR_STORE_DIR, embeddings, allow_dangerous_deserialization=True)
    results_with_scores = vector_store.similarity_search_with_score(user_query, k=4)
    
    context_docs = [doc for doc, score in results_with_scores]
    similarity_scores = [round(float(score), 4) for doc, score in results_with_scores]
    sources = list(set([doc.metadata.get('source', 'Unknown') for doc in context_docs]))
    
    context_str = "\n\n---\n\n".join([
        f"[Source: {doc.metadata.get('source', 'Unknown')} | Chunk {doc.metadata.get('chunk_index', '?')}]\n{doc.page_content}"
        for doc in context_docs
    ])
    
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an advanced AI knowledge worker. Use the following retrieved context to answer the user's question with clarity, accuracy, and professionalism.

IMPORTANT RULES:
1. Base your answer ONLY on the provided context.
2. If the answer is not in the context, clearly state that.
3. When possible, mention which source document the information comes from.
4. Format your answer with proper markdown (bold, bullets, headers) for readability.

Context:
{context}"""),
        ("human", "{input}")
    ])
    
    llm = get_llm(model_name)
    chain = qa_prompt | llm
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    metadata = {
        "chunks": [doc.page_content for doc in context_docs],
        "scores": similarity_scores,
        "sources": sources,
        "response_time_ms": elapsed_ms,
        "cached": False
    }
    
    def chunk_generator():
        for chunk in chain.stream({"context": context_str, "input": user_query}):
            yield chunk.content
            
    return metadata, chunk_generator()

# ─── Direct LLM Query (No RAG — for comparison mode) ─────────

def query_direct_llm(user_query, model_name="gemini-2.5-flash-lite"):
    """
    Queries the LLM directly WITHOUT any retrieval (no RAG).
    Used for comparison: RAG vs No-RAG.
    """
    start_time = time.time()
    
    llm = get_llm(model_name)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful AI assistant. Answer the user's question to the best of your knowledge. If you are unsure, say so."),
        ("human", "{input}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"input": user_query})
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    return {
        "answer": response.content,
        "chunks": [],
        "scores": [],
        "sources": [],
        "response_time_ms": elapsed_ms,
        "cached": False
    }

def query_direct_llm_stream(user_query, model_name="gemini-2.5-flash-lite"):
    start_time = time.time()
    llm = get_llm(model_name)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful AI assistant. Answer the user's question to the best of your knowledge. If you are unsure, say so."),
        ("human", "{input}")
    ])
    chain = prompt | llm
    elapsed_ms = int((time.time() - start_time) * 1000)
    metadata = {
        "chunks": [], "scores": [], "sources": [], "response_time_ms": elapsed_ms, "cached": False
    }
    def chunk_generator():
        for chunk in chain.stream({"input": user_query}):
            yield chunk.content
    return metadata, chunk_generator()

# ─── Long Context Query (The "No-Vector" Rare Feature) ────────

def query_long_context(user_query, model_name="gemini-2.5-flash-lite"):
    """
    Bypasses RAG/FAISS and feeds the ENTIRE document text to the LLM.
    This demonstrates handling of massive context windows (unique to Gemini).
    """
    start_time = time.time()
    
    full_text = get_full_text_from_uploads()
    if not full_text:
        return {"answer": "Knowledge base is empty.", "chunks": [], "sources": [], "response_time_ms": 0}
        
    llm = get_llm(model_name)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an elite Knowledge Agent. You have access to the FULL text of all uploaded documents below. 
        Analyze the entire context to provide a exhaustive, high-fidelity answer.
        
        FULL CONTEXT:
        {context}"""),
        ("human", "{input}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"context": full_text[:500000], "input": user_query}) # 500k limit for safety
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    return {
        "answer": response.content,
        "chunks": ["FULL DOCUMENT CONTEXT (Long Context Window Used)"],
        "scores": [0.0],
        "sources": ["All Documents"],
        "response_time_ms": elapsed_ms,
        "mode": "long_context"
    }

def query_long_context_stream(user_query, model_name="gemini-2.5-flash-lite"):
    start_time = time.time()
    full_text = get_full_text_from_uploads()
    if not full_text:
        def empty_gen(): yield "Knowledge base is empty."
        return {"chunks": [], "scores": [], "sources": [], "response_time_ms": 0, "mode": "long_context"}, empty_gen()
        
    llm = get_llm(model_name)
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an elite Knowledge Agent. You have access to the FULL text of all uploaded documents below. 
        Analyze the entire context to provide a exhaustive, high-fidelity answer.
        
        FULL CONTEXT:
        {context}"""),
        ("human", "{input}")
    ])
    chain = prompt | llm
    elapsed_ms = int((time.time() - start_time) * 1000)
    metadata = {
        "chunks": ["FULL DOCUMENT CONTEXT (Long Context Window Used)"],
        "scores": [0.0], "sources": ["All Documents"], "response_time_ms": elapsed_ms, "mode": "long_context"
    }
    def chunk_generator():
        for chunk in chain.stream({"context": full_text[:500000], "input": user_query}):
            yield chunk.content
    return metadata, chunk_generator()

# ─── Automated Audit Logic (Interview Winner) ────────────────

def perform_document_audit(audit_type="general", model_name="gemini-2.5-pro"):
    """
    Specialized agentic function to detect 'red flags' or 'deep insights'.
    """
    full_text = get_full_text_from_uploads()
    if not full_text:
        return "No documents found to audit."
        
    llm = get_llm(model_name)  # Respects MODEL_OVERRIDE; uses Pro when override is None
    
    audit_prompts = {
        "general": ("General Auditor Agent", "Perform a comprehensive audit of these documents. Identify the core purpose, key participants, and any potential inconsistencies."),
        "risk": ("Risk Auditor Agent", "Act as a Risk Auditor. Identify 5 high-priority 'Red Flags', legal risks, or missing clauses in these documents."),
        "professional": ("Professional Profiler Agent", "Extract a professional profile summary including key achievements, rare skills, and potential interview questions for this candidate."),
        "legal": ("Legal Compliance Agent (India)", 
                  "Audit the documents based on the latest Indian IT Act 2000 and Digital Personal Data Protection (DPDP) Act 2023. "
                  "Check for: 1) Data privacy compliance, 2) Section 43A (compensation for failure to protect data), 3) Intermediary due diligence (if applicable), "
                  "4) Similar case studies/precedents in Indian courts, and 5) Summary with Pros and Cons for the owner.")
    }
    
    agent_name, task_desc = audit_prompts.get(audit_type, audit_prompts["general"])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the {agent_name}. Use the provided context to perform a deep-dive {audit_type} audit. Format your findings with clear headings and bullet points."),
        ("human", "CONTEXT:\n{context}\n\nTASK: {task}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({
        "context": full_text[:400000], 
        "audit_type": audit_type,
        "agent_name": agent_name,
        "task": task_desc
    })
    
    return response.content
