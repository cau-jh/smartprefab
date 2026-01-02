import pandas as pd

# -----------------------
# Load data
# -----------------------
concepts = pd.read_csv("paper_concepts.csv")
works = pd.read_csv("orcid_works.csv")
topics = pd.read_csv("topic_definition.csv")

# -----------------------
# Prepare keyword map
# -----------------------
topic_keywords = {
    row.topic_id: [k.strip().lower() for k in row.keywords.split(",")]
    for _, row in topics.iterrows()
}

# -----------------------
# Assign topic to each paper
# -----------------------
results = []

for work_id, group in concepts.groupby("work_id"):
    scores = {}

    for _, r in group.iterrows():
        concept = r.concept_name.lower()
        score = r.score

        for tid, keywords in topic_keywords.items():
            if any(k in concept for k in keywords):
                scores[tid] = scores.get(tid, 0) + score

    if scores:
        best_topic = max(scores, key=scores.get)
    else:
        best_topic = -1  # 미분류

    results.append({
        "work_id": work_id,
        "topic_id": best_topic
    })

# -----------------------
# Output: paper_topics.csv
# -----------------------
paper_topics = (
    pd.DataFrame(results)
    .merge(works[["work_id", "title"]], on="work_id", how="left")
    .merge(topics[["topic_id", "topic_name"]], on="topic_id", how="left")
)

paper_topics.to_csv(
    "paper_topics.csv",
    index=False,
    encoding="utf-8-sig"
)

# -----------------------
# Output: topic_summary.csv
# -----------------------
topic_summary = (
    concepts.merge(paper_topics, on="work_id")
    .groupby(["topic_id", "topic_name", "concept_name"])
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

print("✅ 논문 → 주제 배정 완료")
