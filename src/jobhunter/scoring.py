"""Score jobs against candidate profile. Falls back to keyword scoring if no LLM key."""
from __future__ import annotations
import os, json, re
from typing import Any
from jobhunter.models import JobListing, ScoredJob, DailyShortlist
from datetime import datetime

_SYS_PROMPT = """You are a career-matching assistant.

Candidate: Technical PM / backend engineer + data science + ML skills.
Python (FastAPI/Django), SQL, A/B testing, product-led growth, Nigerian-based, remote-first.

Return JSON ONLY:
{"score": 0-10, "reasons": ["pro reason","con reason"], "personal_note": "2-3 sentence intro"}

Rules:
- 8+: strong match
- 6-7: apply
- 4-5: reach
- 0-3: skip
"""

_USER_PROMPT = """Title: {title}
Company: {company}
Location: {location}
Salary: {salary}
Tags: {tags}
Description:\n{desc}

JSON response:"""

def _llm_call(system: str, user: str) -> str:
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return _fallback(user)
    import httpx
    resp = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model":"gpt-4o-mini","messages":[{"role":"system","content":system},{"role":"user","content":user}],"temperature":0.3,"max_tokens":150},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

def _fallback(user: str) -> str:
    text = user.lower()
    score = 4
    hits = []
    for kw, delta in [
        ("product manager", +3), ("backend", +2), ("python", +1),
        ("fastapi", +1), ("remote", +1), ("salary", +1), ("nigeria", +1),
        ("ml", +1), ("data science", +1), ("saas", +1),
    ]:
        if kw in text:
            score += delta
            hits.append(kw)
    score = min(10, max(0, score))
    reasons_str = " + ".join(hits) if hits else "keyword scan"
    note = f"This role aligns with your {reasons_str} background. Apply if location/stack fits."
    return json.dumps({"score": score, "reasons": [reasons_str, "No LLM — rule-based score"], "personal_note": note})

def score_job(listing: JobListing, bio: str) -> ScoredJob:
    system = _SYS_PROMPT
    user   = _USER_PROMPT.format(
        title=listing.title, company=listing.company, location=listing.location,
        salary=listing.salary_raw, tags=", ".join(listing.tags),
        desc=listing.description[:3000],
    )
    raw = _llm_call(system, user)
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    blob = m.group(0) if m else raw
    try:
        data = json.loads(blob)
    except Exception:
        data = {"score": 5, "reasons": ["parse error"], "personal_note": "Review manually."}
    return ScoredJob(
        listing=listing, score=int(data.get("score", 0)),
        reasons=data.get("reasons", []),
        personal_note=data.get("personal_note", ""),
    )

def build_shortlist(jobs: list[JobListing], cfg: Any, bio: str) -> DailyShortlist:
    scored = [score_job(j, bio) for j in jobs]
    approved = sorted([s for s in scored if s.score >= cfg.score_threshold], key=lambda s: s.score, reverse=True)[:cfg.max_results]
    return DailyShortlist(
        generated_at=datetime.now().isoformat(timespec="minutes"),
        criteria=f"roles={cfg.roles} locations={cfg.locations} salary>=${cfg.salary_min_usd:,}",
        jobs=approved,
    )
