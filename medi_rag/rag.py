import os
from dotenv import load_dotenv

from langchain_cohere import ChatCohere, CohereEmbeddings
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data")
VECTORSTORE_PATH = os.path.join(BASE_DIR, "vectorstore")
VECTOR_INDEX_FAISS = os.path.join(VECTORSTORE_PATH, "index.faiss")
VECTOR_INDEX_PKL = os.path.join(VECTORSTORE_PATH, "index.pkl")

# Load env from project root reliably (even if current working dir changes).
load_dotenv(os.path.join(BASE_DIR, ".env"))
COHERE_API_KEY = (os.getenv("COHERE_API_KEY") or "").strip()

vector_db = None
rag_chain = None


def _has_valid_saved_index():
    if not os.path.isdir(VECTORSTORE_PATH):
        return False
    if not os.path.isfile(VECTOR_INDEX_FAISS) or not os.path.isfile(VECTOR_INDEX_PKL):
        return False
    return os.path.getsize(VECTOR_INDEX_FAISS) > 0 and os.path.getsize(VECTOR_INDEX_PKL) > 0


def setup_rag():
    global vector_db, rag_chain

    if rag_chain is not None:
        return

    if not COHERE_API_KEY:
        raise RuntimeError("COHERE_API_KEY is missing. Set it in the project .env file.")

    loader = PyPDFDirectoryLoader(DATA_PATH)
    docs = loader.load()
    if not docs:
        raise RuntimeError(f"No PDF documents found in: {DATA_PATH}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )

    chunks = splitter.split_documents(docs)

    embeddings = CohereEmbeddings(
        model="embed-english-v3.0",
        cohere_api_key=COHERE_API_KEY
    )

    os.makedirs(VECTORSTORE_PATH, exist_ok=True)

   
    if _has_valid_saved_index():
        try:
            vector_db = FAISS.load_local(
                VECTORSTORE_PATH,
                embeddings,
                allow_dangerous_deserialization=True
            )
        except Exception:
            vector_db = FAISS.from_documents(chunks, embeddings)
            vector_db.save_local(VECTORSTORE_PATH)
    else:
        vector_db = FAISS.from_documents(chunks, embeddings)
        vector_db.save_local(VECTORSTORE_PATH)

    llm = ChatCohere(
        model="command-r7b-12-2024",
        cohere_api_key=COHERE_API_KEY
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a medical assistant. Provide concise factual answers. "
         "Always add: This is not medical advice."),
        ("human", "Context: {context}\n\nQuestion: {input}")
    ])

    doc_chain = create_stuff_documents_chain(llm, prompt)

    rag_chain = create_retrieval_chain(
        vector_db.as_retriever(search_kwargs={"k": 3}),
        doc_chain
    )


def ask_rag(question: str):
    setup_rag()
    response = rag_chain.invoke({"input": question})
    return response["answer"]
