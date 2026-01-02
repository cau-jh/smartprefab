import pandas as pd

# 엑셀(CSV) 파일 경로
CSV_PATH = "orcid_works.csv"
# 생성될 HTML 파일 이름
OUTPUT_HTML = "publications.html"

df = pd.read_csv(CSV_PATH)

# 최신 연도부터 정렬
df = df.sort_values(by="year", ascending=False)

items = []

for _, row in df.iterrows():
    title = row.get("title", "")
    year = row.get("year", "")
    doi = row.get("doi", "")
    cited = row.get("cited_by_count", "")

    if isinstance(doi, str) and doi.strip():
        doi_html = f'<a href="https://doi.org/{doi}" target="_blank">DOI</a>'
    else:
        doi_html = "No DOI"

    items.append(f"""
      <li class="publication-item">
        <h3 class="paper-title">{title}</h3>
        <p class="paper-meta">
          <strong>{year}</strong> · {doi_html} · Cited by {cited}
        </p>
      </li>
    """)

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>Publications | Smart Prefab Lab</title>
  <link rel="stylesheet" href="css/style.css">
</head>
<body>

<header>
  <h1>Publications</h1>
</header>

<nav>
  <a href="index.html">Home</a>
  <a href="members.html">Members</a>
  <a href="research.html">Research</a>
  <a href="publications.html">Publications</a>
  <a href="visualization.html">Visualization</a>
</nav>

<main>
  <section>
    <h2>Journal & Conference Papers</h2>
    <ul class="publication-list">
      {''.join(items)}
    </ul>
  </section>
</main>

<footer>
  <p>© Smart Prefab Lab (Chung-Ang University, ROK)</p>
</footer>

</body>
</html>
"""

with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

print("✅ publications.html 생성 완료")
