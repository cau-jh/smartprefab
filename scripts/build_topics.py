import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering

# -----------------------
# 설정: 허용할 개념 키워드
# -----------------------
ALLOWED_KEYWORDS = [
    "construct",
    "structure",
    "structural",
    "bridge",
    "precast",
    "prefab",
    "concrete",
    "digital",
    "twin",
    "monitor",
    "health",
    "ai",
    "learning",
    "automation",
    "3d",
    "printing",
]

def is_allowed(concept):
    c = concept.lower()
    return any(k in c for k in ALLOWED_KEYWORDS)

# -----------------------
# Load data
# -----------------------
concepts = pd.read_csv("paper_concepts.csv")
works = pd.read_csv("orcid_works.csv")

# -----------------------
# 🔥 핵심: 개념 필터링
# -----------------------
concepts = concepts[concepts["concept_name"].apply(is_allowed)]

print(f"✅ Filtered concepts: {len(concepts)} rows")

# -----------------------
# Concept vector
# -----------------------
pivot = concepts.pivot_table(
    index="work_id",
    columns="concept_name",
    values="score",
    fill_value=0
)

# 안전 장치
if len(pivot) < 2:
    raise ValueError("❌ 논문 수가 너무 적어 클러스터링 불가")

# -----------------------
# Similarity & Distance
# -----------------------
sim = cosine_similarity(pivot.values)
dist = 1 - sim

# -----------------------
# Clustering
# -----------------------
n_topics = min(4, len(pivot))  # 우리 연구실 규모에 맞게

model = AgglomerativeClustering(
    n_clusters=n_topics,
    metric="precomputed",
    linkage="average"
)

labels = model.fit_predict(dist)

# -----------------------
# Output 1: paper_topics.csv
# -----------------------
paper_topics = pd.DataFrame({
    "work_id": pivot.index,
    "topic_id": labels
}).merge(
    works[["work_id", "title"]],
    on="work_id",
    how="left"
)

paper_topics.to_csv(
    "paper_topics.csv",
    index=False,
    encoding="utf-8-sig"
)

# -----------------------
# Output 2: topic_summary.csv
# -----------------------
topic_summary = (
    concepts.merge(paper_topics, on="work_id")
    .groupby(["topic_id", "concept_name"])
    .score.mean()
    .reset_index()
    .sort_values(["topic_id", "score"], ascending=[True, False])
)

topic_summary = topic_summary.groupby("topic_id").head(5)

topic_summary.to_csv(
    "topic_summary.csv",
    index=False,
    encoding="utf-8-sig"
)

print("✅ A안 적용 완료: paper_topics.csv / topic_summary.csv 재생성")
