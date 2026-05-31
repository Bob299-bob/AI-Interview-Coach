import pdfplumber
import faiss
import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter as RCTS
splitter=RCTS(chunk_size=500,chunk_overlap=100)
from sentence_transformers import SentenceTransformer
model=SentenceTransformer(
    "all-MiniLM-L6-v2"
)
#Rag Sysytem
def Rag(pdf_text):
    resume=splitter.split_text(pdf_text)
    resume_embedding=model.encode(resume).astype('float32')
    faiss.normalize_L2(resume_embedding)
    index=faiss.IndexFlatIP(resume_embedding.shape[1])
    index.add(resume_embedding)
    return index,resume
def Retrieve(query,index,resume):
    chunks=[]
    query=model.encode([query]).astype('float32')
    faiss.normalize_L2(query)
    distance,indices=index.search(query,k=min(10,len(resume)))
    for idx in indices[0]:
        print('skills\n',resume[idx])
        chunks.append(resume[idx])
    return chunks
def pdf_extract(data_path):
    pdf_text=""
    with pdfplumber.open(data_path) as file:
        for page in file.pages:
            page_text=page.extract_text()
            if page_text:
                pdf_text+=page_text+"\n"
    return pdf_text

from sklearn.metrics.pairwise import cosine_similarity
def analyze(query,chunks):
    if not chunks:
        return 0.0
    jd_embed=model.encode([query]).astype('float32')
    jd_embed = np.array(jd_embed).reshape(1, -1)
    chunks_embed=model.encode(chunks).astype('float32')
    score=cosine_similarity(chunks_embed,jd_embed).flatten()
    label=float(score.max())
    return label
def extract_skills(context):
    skills = ""
    projects = ""
    for chunk in context:
        if "skill" in chunk.lower():
            skills += chunk + "\n"
        if "project" in chunk.lower():
            projects += chunk + "\n"
    return skills, projects