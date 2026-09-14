# -*- coding: utf-8 -*-
"""ChromaDB 벡터 데이터베이스 구축 스크립트"""
import os
import glob
from pypdf import PdfReader  # type: ignore
import chromadb  # type: ignore
from chromadb.utils import embedding_functions  # type: ignore

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")

def build_chroma_db():
    pdf_files = glob.glob(os.path.join(DATA_DIR, "*.pdf"))
    if not pdf_files:
        print("에러: data/ 폴더에 PDF 파일이 없습니다.")
        return

    embedding_fn = embedding_functions.DefaultEmbeddingFunction()

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    
    try:
        client.delete_collection("ace_etf_prospectus")
    except Exception:
        pass

    collection = client.create_collection(
        name="ace_etf_prospectus",
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )

    documents = []
    metadatas = []
    ids = []
    doc_id_counter = 1

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        reader = PdfReader(pdf_path)
        
        for page_idx, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            lines = [l.strip() for l in page_text.split("\n") if l.strip()]
            
            chunk_buffer = []
            curr_len = 0
            
            for line in lines:
                chunk_buffer.append(line)
                curr_len += len(line)
                
                if curr_len >= 300:
                    chunk_text = f"[{filename} p.{page_idx + 1}]\n" + "\n".join(chunk_buffer)
                    documents.append(chunk_text)
                    metadatas.append({
                        "source_file": filename,
                        "page": page_idx + 1,
                        "chunk_id": doc_id_counter
                    })
                    ids.append(f"doc_{doc_id_counter}")
                    doc_id_counter += 1
                    
                    chunk_buffer = []
                    curr_len = 0
                    
            if chunk_buffer:
                chunk_text = f"[{filename} p.{page_idx + 1}]\n" + "\n".join(chunk_buffer)
                documents.append(chunk_text)
                metadatas.append({
                    "source_file": filename,
                    "page": page_idx + 1,
                    "chunk_id": doc_id_counter
                })
                ids.append(f"doc_{doc_id_counter}")
                doc_id_counter += 1

    if documents:
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

if __name__ == "__main__":
    build_chroma_db()
