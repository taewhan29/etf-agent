# -*- coding: utf-8 -*-
"""
[공통 경로 설정 모듈] (config/paths.py)
프로젝트 내 정형 DB, 비정형 ChromaDB, 데이터 폴더 등의 기준 경로를 중앙 집중 관리한다.
"""
import os

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(SRC_DIR)
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "etf_spec.db")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")
