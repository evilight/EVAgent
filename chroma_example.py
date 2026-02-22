import chromadb

# 1. 创建客户端
client = chromadb.Client()

# 2. 创建或获取一个Collection。如果不指定embedding_function，会使用默认的 all-MiniLM-L6-v2
collection = client.get_or_create_collection(
    name="my_docs",
    metadata={"hnsw:space": "cosine"} # 设置使用余弦距离计算相似度
)

# 3. 添加数据。Chroma会自动使用默认模型将documents转换为向量
collection.add(
    documents=["猫喜欢吃鱼", "狗喜欢追球", "这是一种水生哺乳动物"],
    metadatas=[
        {"category": "宠物", "source": "wiki"},
        {"category": "宠物", "source": "blog"},
        {"category": "动物", "source": "wiki"}
    ],
    ids=["id1", "id2", "id3"]
)

# 4. 查询与“猫”最相关的前2条记录，并过滤出“宠物”类别
results = collection.query(
    query_texts=["猫爱吃啥？"],
    n_results=2,
    where={"category": "宠物"} # 元数据过滤
)

print(results['documents']) 
# 输出应该会包含 ['猫喜欢吃鱼', '狗喜欢追球']
print(results['distances']) # 可以看到语义距离