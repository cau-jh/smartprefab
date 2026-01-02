# scripts/visualize_topics.py
import os
import pandas as pd
import networkx as nx
from pyvis.network import Network

# =========================
# Paths (프로젝트 루트 기준)
# =========================
GRAPH_PATH = "vis/orcid_citation_network.graphml"
PAPER_TOPICS_PATH = "paper_topics.csv"          # work_id, topic_id, title, topic_name
OUTPUT_HTML = "vis/orcid_topic_network.html"    # 결과물

# =========================
# Load data
# =========================
G = nx.read_graphml(GRAPH_PATH)
topics_df = pd.read_csv(PAPER_TOPICS_PATH, encoding="utf-8-sig")

# work_id -> topic_id, topic_name, title
work_to_topic = {}
topic_id_to_name = {}

for _, r in topics_df.iterrows():
    wid = str(r.get("work_id", "")).strip()
    tid = int(r.get("topic_id", -1)) if pd.notna(r.get("topic_id", None)) else -1
    tname = str(r.get("topic_name", "")).strip() if pd.notna(r.get("topic_name", None)) else ""
    title = str(r.get("title", "")).strip() if pd.notna(r.get("title", None)) else ""

    if wid:
        work_to_topic[wid] = {"topic_id": tid, "topic_name": tname, "title": title}
    if tid not in topic_id_to_name and tname:
        topic_id_to_name[tid] = tname

# =========================
# Topic color map
# =========================
TOPIC_COLORS = {
    0: "#1f77b4",   # blue
    2: "#ff7f0e",   # orange
    3: "#9467bd",   # purple
    -1: "#aaaaaa"   # gray (unassigned)
}

def color_for_topic(tid: int) -> str:
    return TOPIC_COLORS.get(tid, "#aaaaaa")

# =========================
# Build PyVis network
# =========================
net = Network(
    height="800px",
    width="100%",
    bgcolor="#ffffff",
    font_color="black",
    cdn_resources="in_line"
)

# -------------------------
# 1) Add TOPIC nodes (새 노드)
# -------------------------
# paper_topics.csv에 있는 topic_id 목록 기준으로 생성
topic_nodes = set()
for tid, name in topic_id_to_name.items():
    topic_node_id = f"topic::{tid}"
    topic_nodes.add(topic_node_id)

    net.add_node(
        topic_node_id,
        label=name if name else f"Topic {tid}",
        title=f"Topic {tid}: {name}",
        color=color_for_topic(tid),
        shape="box",
        size=28
    )

# 미분류(-1) topic도 노드로 만들고 싶으면 아래 주석 해제
# topic_nodes.add("topic::-1")
# net.add_node("topic::-1", label="Unassigned", title="Unassigned", color=color_for_topic(-1), shape="box", size=28)

# -------------------------
# 2) Add nodes from GraphML
#    - Paper는 label 숨기고 hover로만 표시
#    - Citing author는 작게
#    - Target author(ORCID)는 표시하되, paper와 직접 연결은 하지 않음 (핵심)
# -------------------------
target_author_ids = set()

for node, data in G.nodes(data=True):
    ntype = data.get("node_type", "")
    label = data.get("label", str(node))

    if ntype == "target_author":
        target_author_ids.add(node)
        net.add_node(
            node,
            label=label,
            title=label,
            color="red",
            shape="dot",
            size=30
        )

    elif ntype == "target_work":
        # 논문 노드
        wid = str(node)
        tinfo = work_to_topic.get(wid, {"topic_id": -1, "topic_name": "", "title": label})
        tid = int(tinfo.get("topic_id", -1))
        paper_title = tinfo.get("title", label)

        net.add_node(
            wid,
            label=None,            # 글자 숨김 (겹침 방지)
            title=paper_title,     # hover시에 제목 표시
            color=color_for_topic(tid),
            shape="dot",
            size=14
        )

    elif ntype == "citing_author":
        net.add_node(
            node,
            label=None,          # 저자 이름도 숨기고 hover로만 (너무 많아서)
            title=label,
            color="#2ca02c",
            shape="dot",
            size=8
        )
    else:
        # 혹시 다른 타입이 있으면 작게 처리
        net.add_node(
            node,
            label=None,
            title=label,
            color="#888888",
            shape="dot",
            size=6
        )

# -------------------------
# 3) Add edges
#    핵심: Topic -> Paper 를 새로 추가
#         Paper -> CitingAuthor 는 기존 GraphML edge 사용
#         ORCID -> Paper(edge_type=authored) 는 제거/미표시 (방사형 구조 방지)
# -------------------------

# (A) Topic -> Paper edge 추가
for wid, info in work_to_topic.items():
    tid = int(info.get("topic_id", -1))
    topic_node_id = f"topic::{tid}"
    if topic_node_id in topic_nodes and G.has_node(wid):
        net.add_edge(
            topic_node_id,
            wid,
            value=1,
            color=color_for_topic(tid)
        )

# (B) GraphML에서 Paper-Author edges 추가
# authored(edge_type="authored")는 제외하고, cites_target_work만 추가
for u, v, edata in G.edges(data=True):
    etype = edata.get("edge_type", "")

    # ORCID authored 엣지 제거 (방사형 원인)
    if etype == "authored":
        continue

    # 나머지 엣지 추가
    w = edata.get("weight", 1)
    try:
        w = float(w)
    except:
        w = 1

    net.add_edge(u, v, value=w)

# -------------------------
# 4) Physics options (JSON 형태로 넣어야 함)
# -------------------------
net.set_options("""
{
  "physics": {
    "solver": "forceAtlas2Based",
    "forceAtlas2Based": {
      "gravitationalConstant": -60,
      "centralGravity": 0.01,
      "springLength": 140,
      "springConstant": 0.08
    },
    "maxVelocity": 50,
    "timestep": 0.35,
    "stabilization": { "enabled": true, "iterations": 1000 }
  },
  "interaction": {
    "hover": true,
    "tooltipDelay": 80,
    "hideEdgesOnDrag": false
  }
}
""")

# =========================
# Output (Windows cp949 회피: generate_html로 저장)
# =========================
os.makedirs(os.path.dirname(OUTPUT_HTML), exist_ok=True)

html = net.generate_html()
with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

print("✅ Topic-cluster visualization generated:")
print("   ", OUTPUT_HTML)
print("👉 브라우저에서 확인:")
print("   http://localhost:8000/vis/orcid_topic_network.html")
