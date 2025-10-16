import json
from knowledge_base import KnowledgeBase
import os

def main():
    """
    此脚本用于初始化向量知识库。
    它会读取 products.json 文件，将其内容转换为适合检索的文本格式，
    然后将这些文本向量化后存入 ChromaDB。
    """
    # 确保持久化目录与 KnowledgeBase 类中的默认值一致
    db_directory = os.path.join(os.path.dirname(__file__), "chroma_db")
    kb = KnowledgeBase(persist_directory=db_directory)

    # 清空现有集合，确保每次运行都是全新的开始
    # 注意：在生产环境中可能不需要这一步
    print(f"正在清空旧的集合 '{kb.collection.name}'...")
    kb.chroma_client.delete_collection(name=kb.collection.name)
    kb.collection = kb.chroma_client.get_or_create_collection(name=kb.collection.name)
    print("旧集合已清空，并已创建新集合。")

    products_file = os.path.join(os.path.dirname(__file__), "products.json")
    try:
        with open(products_file, 'r', encoding='utf-8') as f:
            products = json.load(f)
    except FileNotFoundError:
        print(f"错误: 未找到商品数据文件 '{products_file}'")
        return
    
    # 准备要添加到知识库的数据
    texts_to_add = []
    metadatas_to_add = []
    ids_to_add = []

    for p in products:
        # 将每个产品转换为一个详细的文本“文档”
        text = (
            f"产品名称: {p['name']}。\n"
            f"价格: {p['price']}元。\n"
            f"适用部位: {', '.join(p['area'])}。\n"
            f"主要功效或关键词: {', '.join(p['keywords'])}。\n"
            f"详细描述: {p['description']}"
        )
        texts_to_add.append(text)
        
        # 元数据可以存储一些结构化信息，便于后续使用
        metadatas_to_add.append({
            "source": "products.json",
            "product_id": p['id'],
            "name": p['name'],
            "price": p['price']
        })
        
        # ID 必须是唯一的字符串
        ids_to_add.append(p['id'])

    if not texts_to_add:
        print("没有从 products.json 中加载到任何数据。")
        return

    # 调用 knowledge_base 中的方法批量添加
    success = kb.add_texts(
        texts=texts_to_add,
        metadatas=metadatas_to_add,
        ids=ids_to_add
    )

    if success:
        print("\n知识库初始化成功！")
        print(f"总共添加了 {len(texts_to_add)} 个产品到向量数据库。")
    else:
        print("\n知识库初始化失败。")

if __name__ == "__main__":
    main()