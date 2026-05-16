"""jobhunter CLI — run, status, export."""
from __future__ import annotations
import json, sys
from pathlib import Path
import click
from jobhunter.config import Config
from jobhunter.models import DailyShortlist, ScoredJob, JobListing
from jobhunter.scrapers.remoteok import RemoteOKScraper
from jobhunter.scrapers.remotive import RemotiveScraper
from jobhunter.scrapers.wellfound import WellfoundScraper
from jobhunter.scrapers.wwr import WWRScraper
from jobhunter.scrapers.duckduckgo import DuckDuckGoScraper
from jobhunter.scrapers.naukri     import NaukriScraper
from jobhunter.scrapers.indeed     import IndeedScraper
from jobhunter.scrapers.jobberman  import JobbermanScraper
from jobhunter.scrapers.linkedin   import LinkedinScraper
from jobhunter.scoring import build_shortlist

OUT  = Path(__file__).parent.parent.parent / "output"
OUT.mkdir(exist_ok=True)

def _collect_jobs(cfg: Config) -> list[JobListing]:
    jobs: list[JobListing] = []
    scrapers = [
        ("remoteok",    RemoteOKScraper),
        ("remotive",    RemotiveScraper),
        ("indeed",      IndeedScraper),
        ("jobberman",   JobbermanScraper),
        ("linkedin",    LinkedinScraper),
        ("wellfound",   WellfoundScraper),
        ("wwr",         WWRScraper),
        ("duckduckgo",  DuckDuckGoScraper),
        ("naukri",      NaukriScraper),
    ]
    for key, cls in scrapers:
        src_cfg = cfg.sources.get(key, {})
        if not src_cfg.get("enabled", False):
            continue
        pages = src_cfg.get("pages", 1)
        try:
            jobs += cls(cfg.roles, cfg.locations).fetch(pages)
            print(f"  [{key}]  {len([j for j in jobs if j.source == key])} jobs collected")
        except Exception as exc:
            print(f"  [{key}]  FAILED: {exc}")
    return jobs

@click.group()
def main():
    """jobhunter — daily job opportunity pipeline."""

@main.command()
@click.option("--roles",    default=None, help="comma-separated roles")
@click.option("--locations",default=None, help="comma-separated locations")
@click.option("--salary",   default=None, type=int, help="min salary USD")
@click.option("--min-score",default=None, type=int, help="threshold")
@click.option("--output",   default="daily.json", help="output path")
def run(roles, locations, salary, min_score, output):
    """Scrape boards → score → write daily shortlist."""
    cfg = Config.load()
    if roles:     cfg.roles = [r.strip() for r in roles.split(",")]
    if locations: cfg.locations = [l.strip() for l in locations.split(",")]
    if salary is not None: cfg.salary_min_usd = salary
    if min_score is not None: cfg.score_threshold = min_score
    out_path = Path(output)

    print(f"▶  jobhunter run — roles={cfg.roles} score>={cfg.score_threshold}")
    raw_jobs = _collect_jobs(cfg)
    if not raw_jobs:
        print("⚠  No jobs collected — check network / source config.")
        sys.exit(0)
    print(f"  {len(raw_jobs)} raw jobs — scoring...")
    shortlist = build_shortlist(raw_jobs, cfg, cfg.bio)
    out_path.write_text(json.dumps(shortlist.to_dict(), indent=2, default=str))
    print(f"  ✓  {len(shortlist.jobs)} roles written to {out_path}")

@main.command()
@click.argument("json_file", default="daily.json")
def status(json_file):
    """Show shortlisted roles."""
    p = Path(json_file)
    if not p.exists():
        print(f"No file: {p}")
        sys.exit(1)
    data = json.loads(p.read_text())
    jobs  = data.get("jobs", [])
    print(f"Shortlisted: {len(jobs)} roles  (generated {data.get('generated_at','')})")
    for j in jobs:
        sc = j["score"]
        tag = "✓" if sc >= 7 else "~" if sc >= 5 else "?"
        print(f"  [{tag}] {j['score']:2d}  {j['title'][:40]:<40}  {j['company'][:25]}  loc={j['location'][:20]}")

@main.command()
@click.argument("json_file", default="daily.json")
@click.argument("csv_file",  default="daily.csv")
def export(json_file, csv_file):
    """Export shortlist to CSV."""
    import csv
    p = Path(json_file)
    if not p.exists():
        print(f"No file: {p}"); sys.exit(1)
    rows = json.loads(p.read_text()).get("jobs", [])
    if not rows:
        print("No jobs to export."); sys.exit(0)
    with open(csv_file, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["score","title","company","location","salary_raw","tags","source_url","personal_note"])
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k,"") for k in w.fieldnames})
    print(f"✓  {len(rows)} rows → {csv_file}")


if __name__ == "__main__":
    main()
