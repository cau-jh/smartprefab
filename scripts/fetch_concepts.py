import time
import requests
import pandas as pd

MAILTO = "csshim@cau.ac.kr"
S = requests.Session()
S.headers.update({"User-Agent": f"topic-fetch (mailto:{MAILTO})"})

def get_json(url, params=None):
    params = params or {}
    params["mailto"] = MAILTO
    r = S.get(url, params=params, timeout=30)

    # 🔒 방어 코드
    if r.status_code != 200 or not r.text.strip():
        print("⚠️ Skipped:", url)
        return {}

    time.sleep(0.12)
    return r.json()

works = pd.read_csv("orcid_works.csv")

rows = []
for _, r in works.iterrows():
    wid = r["work_id"]
    api_url = wid.replace(
        "https://openalex.org/",
        "https://api.openalex.org/works/"
    )

    data = get_json(api_url)
    concepts = data.get("concepts", [])[:10]

    for c in concepts:
        rows.append({
            "work_id": wid,
            "concept_id": c.get("id"),
            "concept_name": c.get("display_name"),
            "score": c.get("score", 0)
        })

df = pd.DataFrame(rows)
df.to_csv("paper_concepts.csv", index=False, encoding="utf-8-sig")
print("✅ paper_concepts.csv 생성 완료")
