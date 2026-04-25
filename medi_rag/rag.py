import os
import re
from difflib import SequenceMatcher

from dotenv import load_dotenv
from pypdf import PdfReader

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
DOCTOR_DISEASE_PDFS = (
    os.path.join(DATA_PATH, "doctors_list_updated.pdf"),
    os.path.join(DATA_PATH, "doctors_list.pdf"),
)
DOCTOR_SPECIALIZATION_PDF = os.path.join(DATA_PATH, "doctor_specializations.pdf")
NO_DOCTOR_FOUND = "No matching doctor found."

# Load env from project root reliably (even if current working dir changes).
load_dotenv(os.path.join(BASE_DIR, ".env"))
COHERE_API_KEY = (os.getenv("COHERE_API_KEY") or "").strip()

vector_db = None
rag_chain = None
doctor_disease_index = None
doctor_specialization_index = None

DOCTOR_ENTRY_PATTERN = re.compile(
    r"^\s*(?:\d+\.\s*)?(dr\.?\s+[A-Za-z.'\-\s]+?)\s*[-–]\s*(.+?)\s*$",
    re.IGNORECASE,
)
QUERY_SPLIT_PATTERN = re.compile(r"\s*(?:,|;|\band\b|\bor\b|\n)\s*", re.IGNORECASE)
NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")
SYMPTOM_SPECIALIZATION_KEYWORDS = {
    "Cardiologist": {
        "chest pain", "palpitations", "heart", "heart pain", "heartburn",
        "arrhythmia", "breathlessness", "shortness of breath", "pressure chest",
    },
    "Pulmonologist": {
        "cough", "wheezing", "asthma", "breathing", "breathlessness",
        "shortness of breath", "lung", "copd", "tb", "tuberculosis",
    },
    "Neurologist": {
        "headache", "migraine", "dizziness", "vertigo", "seizure",
        "numbness", "memory loss", "paralysis", "stroke", "neuropathy",
    },
    "Dermatologist": {
        "rash", "itching", "itchy skin", "acne", "eczema", "psoriasis",
        "skin allergy", "skin infection",
    },
    "Pediatrician": {
        "child fever", "baby", "infant", "pediatric", "vaccination",
        "newborn", "child cough",
    },
    "Ear, Nose & Throat Specialist": {
        "ear pain", "hearing loss", "sinus", "sore throat", "tonsil",
        "nose bleed", "blocked nose",
    },
    "General Physician": {
        "fever", "fatigue", "weakness", "body pain", "general checkup",
        "vomiting", "nausea", "infection",
    },
}


def _has_valid_saved_index():
    if not os.path.isdir(VECTORSTORE_PATH):
        return False
    if not os.path.isfile(VECTOR_INDEX_FAISS) or not os.path.isfile(VECTOR_INDEX_PKL):
        return False
    return os.path.getsize(VECTOR_INDEX_FAISS) > 0 and os.path.getsize(VECTOR_INDEX_PKL) > 0


def _normalize_text(value):
    normalized = NON_ALNUM_PATTERN.sub(" ", (value or "").lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def _tokenize(value):
    return {token for token in _normalize_text(value).split() if len(token) > 1}


def _format_doctor_name(name):
    cleaned = re.sub(r"\s+", " ", (name or "").strip())
    if not cleaned:
        return cleaned
    lower_cleaned = cleaned.lower()
    if lower_cleaned.startswith("dr. "):
        return "Dr. " + cleaned[4:].title()
    if lower_cleaned.startswith("dr "):
        return "Dr. " + cleaned[3:].title()
    return cleaned.title()


def _extract_pdf_text(path):
    reader = PdfReader(path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _parse_doctor_entries(pdf_paths):
    entries = []
    seen = set()
    for pdf_path in pdf_paths:
        if not os.path.isfile(pdf_path):
            continue
        text = _extract_pdf_text(pdf_path)
        for raw_line in text.splitlines():
            line = " ".join(raw_line.split())
            match = DOCTOR_ENTRY_PATTERN.match(line)
            if not match:
                continue
            doctor_name = _format_doctor_name(match.group(1))
            disease_name = re.sub(r"\s+", " ", match.group(2)).strip(" .")
            key = (_normalize_text(doctor_name), _normalize_text(disease_name))
            if not key[0] or not key[1] or key in seen:
                continue
            seen.add(key)
            entries.append(
                {
                    "doctor": doctor_name,
                    "label": disease_name,
                    "normalized_label": key[1],
                    "tokens": _tokenize(disease_name),
                }
            )
    return entries


def _load_doctor_indexes():
    global doctor_disease_index, doctor_specialization_index

    if doctor_disease_index is None:
        doctor_disease_index = _parse_doctor_entries(DOCTOR_DISEASE_PDFS)
    if doctor_specialization_index is None:
        doctor_specialization_index = _parse_doctor_entries((DOCTOR_SPECIALIZATION_PDF,))


def _query_parts(query):
    parts = [part.strip() for part in QUERY_SPLIT_PATTERN.split(query or "") if part.strip()]
    normalized_query = (query or "").strip()
    if parts:
        if normalized_query and normalized_query not in parts:
            parts.append(normalized_query)
        return parts
    return [normalized_query]


def _score_against_label(query, label, label_tokens):
    query_normalized = _normalize_text(query)
    label_normalized = _normalize_text(label)
    if not query_normalized or not label_normalized:
        return 0.0
    if query_normalized == label_normalized:
        return 1.0
    if label_normalized in query_normalized:
        return 0.95
    if query_normalized in label_normalized:
        return 0.9

    query_tokens = _tokenize(query)
    if not query_tokens or not label_tokens:
        return 0.0

    overlap = len(query_tokens & label_tokens) / len(label_tokens)
    coverage = len(query_tokens & label_tokens) / len(query_tokens)
    similarity = SequenceMatcher(None, query_normalized, label_normalized).ratio()
    return max(overlap * 0.8 + coverage * 0.2, similarity * 0.75)


def _format_recommendations(matches):
    lines = ["Recommended doctors:"]
    for index, match in enumerate(matches, start=1):
        lines.append(f"{index}. {match['doctor']} ({match['label']})")
    return "\n".join(lines)


def _find_ranked_disease_matches(query, limit=3):
    _load_doctor_indexes()
    scored_matches = []

    for part_index, part in enumerate(_query_parts(query)):
        for entry in doctor_disease_index:
            score = _score_against_label(part, entry["label"], entry["tokens"])
            if score >= 0.72:
                scored_matches.append(
                    {
                        "doctor": entry["doctor"],
                        "label": entry["label"],
                        "score": score,
                        "part_index": part_index,
                    }
                )

    if not scored_matches:
        return []

    ranked_matches = sorted(
        scored_matches,
        key=lambda item: (item["part_index"], -item["score"], item["doctor"], item["label"]),
    )
    unique_matches = []
    seen = set()
    for match in ranked_matches:
        key = (_normalize_text(match["doctor"]), _normalize_text(match["label"]))
        if key in seen:
            continue
        seen.add(key)
        unique_matches.append(match)
        if len(unique_matches) == limit:
            break
    return unique_matches


def _find_specialization_fallback(query, limit=3):
    _load_doctor_indexes()
    query_normalized = _normalize_text(query)
    if not query_normalized:
        return []

    matched_specialization = None
    matched_score = 0
    for specialization, keywords in SYMPTOM_SPECIALIZATION_KEYWORDS.items():
        score = sum(1 for keyword in keywords if _normalize_text(keyword) in query_normalized)
        if score > matched_score:
            matched_score = score
            matched_specialization = specialization

    if not matched_specialization:
        return []

    matches = []
    for entry in doctor_specialization_index:
        if _normalize_text(entry["label"]) == _normalize_text(matched_specialization):
            matches.append(
                {
                    "doctor": entry["doctor"],
                    "label": entry["label"],
                }
            )
        if len(matches) == limit:
            break
    return matches


def recommend_doctor(query: str):
    direct_matches = _find_ranked_disease_matches(query)
    if direct_matches:
        return _format_recommendations(direct_matches)

    specialization_matches = _find_specialization_fallback(query)
    if specialization_matches:
        return _format_recommendations(specialization_matches)

    return NO_DOCTOR_FOUND


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
