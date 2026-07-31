"""Shared gold set and scoring helpers for the skill-matching eval scripts.

Extracted out of compare_v1_v2.py so threshold_ablation.py can score against
the exact same 20 hand-labeled snippets instead of forking a second copy of
hand-labeled data that would silently drift from the first.
"""

from __future__ import annotations

# (text, set of skill ids that a human says are genuinely present)
# Labels use v2 taxonomy ids; the v1 mapping lives in compare_v1_v2.py.
GOLD: list[tuple[str, set[str]]] = [
    ("Looking for a JavaScript developer comfortable with loops and recursion.",
     {"javascript"}),
    ("Strong Java background, Spring Boot microservices, and JUnit testing.",
     {"java", "spring", "testing"}),
    ("Experience with RESTful APIs and Object-Oriented Programming principles.",
     {"rest-api", "oop"}),
    ("Built the CI/CD pipeline on GitHub Actions with Docker and Kubernetes.",
     {"cicd", "github-actions", "docker", "kubernetes"}),
    ("Deep learning research using PyTorch and Hugging Face transformers.",
     {"deep-learning", "pytorch", "transformers"}),
    ("Helped the organisation go to market faster and continued to excel.",
     set()),
    ("Backend microservices written in Go, deployed on AWS.",
     {"go", "microservices", "aws"}),
    ("Advanced Excel including pivot tables, plus Power BI dashboards.",
     {"excel", "power-bi"}),
    ("Worked closely with many teams over several years across projects.",
     set()),
    ("Node.js and Express.js REST API with JWT authentication and RBAC.",
     {"nodejs", "express", "rest-api", "jwt", "rbac"}),
    ("Proficient in C++ and C#; some exposure to Rust for systems programming.",
     {"cpp", "csharp", "rust"}),
    ("Built a semantic search feature using embeddings and a vector database.",
     {"information-retrieval", "embeddings"}),
    ("Managed PostgreSQL and Redis in production behind Nginx.",
     {"postgresql", "redis", "nginx"}),
    ("Machine learning pipelines with scikit-learn, pandas and NumPy.",
     {"machine-learning", "scikit-learn", "pandas", "numpy"}),
    ("Shipped a Next.js frontend styled with Tailwind CSS.",
     {"nextjs", "tailwind"}),
    ("Ran ETL jobs on Apache Spark and stored results in Elasticsearch.",
     {"spark", "elasticsearch"}),
    ("Solid understanding of data structures, algorithms and system design.",
     {"data-structures", "algorithms", "system-design"}),
    ("Owned Google Analytics 4 reporting and SEO strategy for the site.",
     {"ga4", "seo"}),
    ("Responsible for stakeholder management and clear written communication.",
     {"stakeholder-management", "communication"}),
    ("Deployed with Terraform; strong Linux and Bash scripting skills.",
     {"terraform", "linux", "bash"}),
]


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def evaluate(predict, name: str, *, restrict_to: set[str] | None = None):
    tp = fp = fn = 0
    false_positives: list[tuple[str, str]] = []
    for text, gold in GOLD:
        # Only score skills the system could possibly know about, so a
        # smaller vocabulary isn't punished for it — this measures
        # *matching* quality, not vocabulary size.
        expected = gold & restrict_to if restrict_to is not None else gold
        pred = predict(text)
        if restrict_to is not None:
            pred &= restrict_to
        tp += len(pred & expected)
        for wrong in pred - expected:
            fp += 1
            false_positives.append((text[:46] + "...", wrong))
        fn += len(expected - pred)
    p, r, f = prf(tp, fp, fn)
    return {"name": name, "tp": tp, "fp": fp, "fn": fn,
            "precision": p, "recall": r, "f1": f, "examples": false_positives}
