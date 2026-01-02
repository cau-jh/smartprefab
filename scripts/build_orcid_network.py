import time
print("SCRIPT STARTED")
import requests
import pandas as pd
import networkx as nx
import os
from collections import defaultdict
from itertools import combinations

# =========================
# 설정
# =========================
ORCID = "0000-0001-7557-9553"
MAILTO = "csshim@cau.ac.kr"
UA = f"orcid-citation-network (mailto:{MAILTO})"

# 결과 저장 폴더 (프로젝트 루트 기준)
BASE_DIR = "./vis"
os.makedirs(BASE_DIR, exist_ok=True)

# =========================
# OpenAlex API 설정
# =========================
S = requests.Session()
S.headers.update({"User-Agent": UA})

def get_json(url, params=None, sleep=0.12):
    if params is None:
        params = {}
    params = dict(params)
    params["mailto"] = MAILTO
    r = S.get(url, params=params, timeout=60)
    r.raise_for_status()
    time.sleep(sleep)
    return r.json()

def iter_openalex_results(url, params=None, max_items=5000):
    if params is None:
        params = {}
    params = dict(params)
    params.setdefault("per-page", 200)
    params["cursor"] = "*"
    n = 0
    while True:
        data = get_json(url, params=params)
        results = data.get("results", []) or []
        for item in results:
            yield item
            n += 1
            if n >= max_items:
                return
        next_cursor = (data.get("meta") or {}).get("next_cursor")
        if not next_cursor:
            return
        params["cursor"] = next_cursor

# =========================
# 1) ORCID → Author 정보
# =========================
author = get_json(f"https://api.openalex.org/authors/orcid:{ORCID}")
author_id = author["id"]
author_name = author.get("display_name", f"ORCID:{ORCID}")

# =========================
# 2) 내 논문 목록
# =========================
works_url = "https://api.openalex.org/works"
my_works = []

for w in iter_openalex_results(
    works_url,
    params={
        "filter": f"authorships.author.id:{author_id}",
        "select": "id,doi,display_name,publication_year,cited_by_count,cited_by_api_url"
    },
    max_items=3000
):
    my_works.append(w)

my_works_df = pd.DataFrame([{
    "work_id": w.get("id"),
    "doi": w.get("doi"),
    "title": w.get("display_name"),
    "year": w.get("publication_year"),
    "cited_by_count": w.get("cited_by_count"),
    "cited_by_api_url": w.get("cited_by_api_url")
} for w in my_works])

my_works_df.to_csv(
    f"{BASE_DIR}/orcid_works.csv",
    index=False,
    encoding="utf-8-sig"
)

# =========================
# 3) 인용한 저자 수집
# =========================
authors_meta = {}
edges = []

def safe_str(x):
    return x if isinstance(x, str) else ""

for w in my_works:
    if not w.get("cited_by_api_url"):
        continue

    for cw in iter_openalex_results(
        w["cited_by_api_url"],
        params={"select": "id,display_name,publication_year,authorships"},
        max_items=2000
    ):
        for a in (cw.get("authorships") or []):
            au = a.get("author") or {}
            au_id = au.get("id")
            au_name = au.get("display_name")
            if not au_id or not au_name:
                continue

            inst = ""
            insts = a.get("institutions") or []
            if insts:
                inst = insts[0].get("display_name") or ""

            authors_meta.setdefault(au_id, {
                "name": au_name,
                "orcid": safe_str(au.get("orcid")),
                "institution": inst
            })

            edges.append({
                "from_author_id": au_id,
                "from_author_name": au_name,
                "to_work_id": w["id"],
                "to_work_title": w.get("display_name"),
                "to_work_doi": w.get("doi"),
                "citing_work_id": cw.get("id"),
                "citing_work_title": cw.get("display_name"),
                "citing_year": cw.get("publication_year")
            })

pd.DataFrame(edges).to_csv(
    f"{BASE_DIR}/edges_citingAuthor_to_orcidWorks.csv",
    index=False,
    encoding="utf-8-sig"
)

pd.DataFrame(
    [{"author_id": k, **v} for k, v in authors_meta.items()]
).to_csv(
    f"{BASE_DIR}/citing_authors.csv",
    index=False,
    encoding="utf-8-sig"
)

# =========================
# 4) NetworkX 그래프 생성
# =========================
G = nx.Graph()

G.add_node(
    author_id,
    node_type="target_author",
    label=author_name,
    orcid=f"https://orcid.org/{ORCID}"
)

for _, r in my_works_df.iterrows():
    if pd.notna(r["work_id"]):
        G.add_node(
            r["work_id"],
            node_type="target_work",
            label=str(r["title"]),
            doi=str(r["doi"]),
            year=str(r["year"])
        )

for au_id, meta in authors_meta.items():
    G.add_node(
        au_id,
        node_type="citing_author",
        label=meta["name"],
        orcid=meta["orcid"],
        institution=meta["institution"]
    )

for e in edges:
    u, v = e["from_author_id"], e["to_work_id"]
    if G.has_edge(u, v):
        G[u][v]["weight"] += 1
    else:
        G.add_edge(u, v, edge_type="cites_target_work", weight=1)

for _, r in my_works_df.iterrows():
    if pd.notna(r["work_id"]):
        G.add_edge(author_id, r["work_id"], edge_type="authored", weight=1)

nx.write_graphml(G, f"{BASE_DIR}/orcid_citation_network.graphml")

# =========================
# 5) PyVis 시각화 HTML 생성
# =========================
from pyvis.network import Network

net = Network(
    notebook=False,
    height="800px",
    width="100%",
    bgcolor="#ffffff",
    font_color="black",
    cdn_resources="in_line"
)

for node, data in G.nodes(data=True):
    ntype = data.get("node_type", "")
    label = data.get("label", node)

    if ntype == "target_author":
        net.add_node(node, label=label, color="red", size=40)
    elif ntype == "target_work":
        net.add_node(node, label=label, color="blue", size=20)
    else:
        net.add_node(node, label=label, color="green", size=30)

for u, v, data in G.edges(data=True):
    net.add_edge(u, v, value=data.get("weight", 1))

# html_path = f"{BASE_DIR}/orcid_citation_network.html"
# net.write_html(html_path, encoding="utf-8")
html_path = f"{BASE_DIR}/orcid_citation_network.html"

html = net.generate_html()

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)


print("Done.")
print(f"Output saved to: {html_path}")
