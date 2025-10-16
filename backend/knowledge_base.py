import os
import re
import traceback
from typing import List, Dict

import chromadb
import docx
import PyPDF2
from qianfan import Embedding
from qianfan.resources.typing import QfResponse

# 设置环境变量
os.environ['QIANFAN_AK'] = "yYtEDe6gusHBq0uwpXpqWTcZ"
os.environ['QIANFAN_SK'] = "Zu8vwN6cv7VMa7vsiT4PXqsqyQYu09uc"


class QianfanEmbeddingWrapper:
    """千帆嵌入模型的包装类，提供一个与通用嵌入模型兼容的接口。"""
    def __init__(self, model: str = "Embedding-V1"):
        self.embedding_client = Embedding()
        self.model = model

    def encode(self, texts: List[str]) -> List[List[float]]:
        if not texts or not all(isinstance(t, str) and t.strip() for t in texts):
            print("错误: 输入必须是一个非空的、只包含非空字符串的列表。")
            return []
        try:
            print(f"正在为 {len(texts)} 个文本片段生成向量...")
            resp = self.embedding_client.do(texts=texts, model=self.model)
            if isinstance(resp, QfResponse) and resp.code == 200 and 'data' in resp.body:
                embeddings = [item['embedding'] for item in resp.body['data']]
                print(f"成功生成 {len(embeddings)} 个向量。")
                return embeddings
            else:
                print(f"向量化API返回错误: code={resp.code}, body={resp.body}")
                return []
        except Exception as e:
            print(f"向量化过程中出现严重错误: {e}")
            traceback.print_exc()
            return []


class KnowledgeBase:
    """基于千帆向量嵌入和ChromaDB的本地知识库管理系统。"""
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.embedding_model = QianfanEmbeddingWrapper(model="Embedding-V1")
        self.chroma_client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.chroma_client.get_or_create_collection(
            name="medical_products_kb",
            metadata={"description": "医美产品知识库"}
        )
        print(f"知识库初始化完成，数据存储在: {persist_directory}")

    def add_texts(self, texts: List[str], metadatas: List[dict], ids: List[str]):
        if not (len(texts) == len(metadatas) == len(ids)):
            print("错误: texts, metadatas, 和 ids 的列表长度必须一致。")
            return False
        
        print("正在为直接提供的文本生成向量...")
        embeddings = self.embedding_model.encode(texts)
        if not embeddings or len(embeddings) != len(texts):
            print("向量生成失败或数量不匹配，无法添加到知识库。")
            return False
        try:
            print(f"正在将 {len(texts)} 个项目添加到向量数据库...")
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            print("项目添加成功！")
            return True
        except Exception as e:
            print(f"添加到ChromaDB时出错: {e}")
            traceback.print_exc()
            return False

    def search_similar(self, query: str, n_results: int = 2) -> List[Dict]:
        if not query.strip():
            print("查询内容不能为空。")
            return []
        print(f"接收到搜索查询: '{query}'")
        query_embedding = self.embedding_model.encode([query])
        if not query_embedding:
            print("查询文本向量化失败，无法进行搜索。")
            return []
        try:
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            formatted_results = []
            if results.get('documents') and results['documents'][0]:
                for doc, meta, dist in zip(results['documents'][0], results['metadatas'][0], results['distances'][0]):
                    formatted_results.append({
                        "content": doc,
                        "metadata": meta,
                        "similarity_score": 1 - dist,
                    })
                print(f"成功找到 {len(formatted_results)} 个相关结果。")
                return formatted_results
            else:
                print("未找到相关结果。")
                return []
        except Exception as e:
            print(f"向量搜索过程中出错: {e}")
            traceback.print_exc()
            return []

    def _read_pdf(self, file_path: str) -> str:
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    def _read_docx(self, file_path: str) -> str:
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])

    def _split_text(self, text: str, chunk_size: int = 500) -> List[str]:
        sentences = re.split(r'([。！？!?\n])', text)
        chunks, current_chunk = [], ""
        for i in range(0, len(sentences), 2):
            sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
            if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            current_chunk += sentence
        if current_chunk:
            chunks.append(current_chunk)
        return [c.strip() for c in chunks if c.strip()]
    
    def add_file_to_knowledge_base(self, file_path: str):
        if not os.path.exists(file_path):
            print(f"文件 '{file_path}' 不存在。")
            return False
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1].lower()
        if file_ext == ".pdf":
            text = self._read_pdf(file_path)
        elif file_ext == ".docx":
            text = self._read_docx(file_path)
        else:
            print(f"不支持的文件类型: {file_ext}")
            return False
        if not text.strip():
            print(f"文件 '{file_path}' 内容为空。")
            return False
        chunks = self._split_text(text)
        if not chunks:
            print(f"文件 '{file_path}' 内容太短，无法分割。")
            return False
        metadatas = [{"file_name": file_name, "file_path": file_path}] * len(chunks)
        ids = [f"{file_name}_{i}" for i in range(len(chunks))]
        return self.add_texts(texts=chunks, metadatas=metadatas, ids=ids)