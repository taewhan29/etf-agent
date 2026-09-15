# -*- coding: utf-8 -*-
"""[도구 2] 비정형 RAG 공시 문맥 탐색 모듈 (Search_PDF_RAG)"""
import os
import chromadb  # type: ignore
from chromadb.utils import embedding_functions  # type: ignore

from config.paths import CHROMA_DIR

_chroma_client = None
_embedding_fn = None
_collection = None


def get_chroma_collection():
    global _chroma_client, _embedding_fn, _collection
    if _collection is None:
        if not os.path.exists(CHROMA_DIR):
            return None
        try:
            _embedding_fn = embedding_functions.DefaultEmbeddingFunction()
            _chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
            _collection = _chroma_client.get_collection(name="ace_etf_prospectus", embedding_function=_embedding_fn)
        except Exception:
            return None
    return _collection


def search_pdf_rag(query: str, target_filename: str = None, top_k: int = 2) -> dict:
    collection = get_chroma_collection()
    if collection is None:
        if not os.path.exists(CHROMA_DIR):
            return {"status": "ERROR", "message": "ChromaDB 저장소가 존재하지 않습니다."}
        return {"status": "ERROR", "message": "ChromaDB 컬렉션을 찾을 수 없습니다."}

    where_clause = None
    if target_filename:
        where_clause = {"source_file": target_filename}

    try:
        results = collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_clause
        )
    except Exception as e:
        return {"status": "ERROR", "message": f"검색 중 오류가 발생했습니다: {str(e)}"}

    if not results or not results['documents'] or not results['documents'][0]:
        return {"status": "NOT_FOUND", "text": "해당 정보는 제공된 간이투자설명서 공시 문서에서 찾을 수 없습니다."}

    matched_docs = results['documents'][0]
    matched_metas = results['metadatas'][0]
    matched_dists = results['distances'][0]

    valid_results = []
    for doc, meta, dist in zip(matched_docs, matched_metas, matched_dists):
        if dist <= 0.59:
            valid_results.append({
                "content": doc,
                "source_file": meta.get("source_file", ""),
                "page": meta.get("page", 1),
                "distance": dist
            })

    if not valid_results:
        return {"status": "NOT_FOUND", "text": "해당 정보는 제공된 간이투자설명서 공시 문서에서 찾을 수 없습니다."}

    response_text = "[간이투자설명서 공시 문맥 검색 결과]\n\n"
    for idx, item in enumerate(valid_results):
        cleaned_content = item['content'].replace("*", "")
        response_text += f"{idx + 1}. 발췌 내용:\n{cleaned_content}\n"
        response_text += f"출처: {item['source_file']} (p.{item['page']})\n\n"

    response_text += "안내: 본 정보는 제공된 간이투자설명서 원본 공시 문서에서 직접 발췌되었습니다."

    return {
        "status": "SUCCESS",
        "results": valid_results,
        "text": response_text
    }
