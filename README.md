# TeacherTrack · English Teaching MA applications (2027/28)

An offline-capable, responsive, static university application dashboard covering **Ústí nad Labem, Liberec, Olomouc and Brno** only. All research references are official universities; old-cycle conditions are explicitly not presented as confirmed for 2027/28.

## Run now

Open `index.html` in a modern browser. Filters, application stages, document checklists, per-programme notes, compare mode, acknowledgement of source changes, and JSON backup/restore work offline. Personal selections are kept in that browser via `localStorage`.

## Enable daily checks and a public or private-access-controlled deployment

The website **does not automatically check university sites while you are offline**. To enable a genuine daily source change log:

1. Create a GitHub repository containing the **contents** of this folder. **GitHub Pages websites hosted from a normal repository are generally publicly accessible**, so don't publish private notes or application data to the repository. The personal notes in the app are stored in the visitor's browser, not committed.
2. Make sure the default branch is `main`; in GitHub **Settings → Pages → Build and deployment → Source**, choose **GitHub Actions**.
3. Go to **Actions → Daily university-source check → Run workflow** to initialise source fingerprints and deploy your site.
4. The GitHub workflow then attempts to check official university pages every day around **05:17 UTC**. GitHub may delay scheduled workflows or temporarily disable them in inactive repositories. The live site displays the *actual last successful workflow run timestamp*, never a fictional check.
5. Check the **Change log** after the workflow runs. Source changes are flagged for manual verification. The script **never overwrites admission facts or replaces unknowns based only on text differences**.

The workflow uses `requests`, `beautifulsoup4`, and `pypdf`. If a page becomes inaccessible, the daily log flags an error rather than claiming that programme facts changed. The workflow checks these hosts only: ujep.cz, tul.cz, upol.cz and muni.cz.

## Data model and maintenance

- `data/catalog.json`: authoritative hand-reviewed programme facts, statuses and links.
- `data/catalog.js`: browser-ready copy of catalog JSON. Regenerate after manual edits, e.g.:
  ```bash
  python -c 'import json,pathlib; p=pathlib.Path("data/catalog.json"); pathlib.Path("data/catalog.js").write_text("window.TEACHERTRACK_CATALOG = "+json.dumps(json.loads(p.read_text(encoding="utf8")),ensure_ascii=False)+";\\n",encoding="utf8")'
  ```
- `data/monitor.json`: latest daily checks and detected changes.
- `data/source_snapshots.json`: first-run baseline and future official-page text snapshots (created by the workflow).
- `scripts/check_updates.py`: date-stamped daily comparison, no fabricated field updates.

Changes are **source-level alerts**, not automatic declarations that a programme's actual deadline or exam policy changed. Inspect the official document, then manually revise `catalog.json` and `catalog.js`, changing field statuses to `confirmed` only when a 2027/28 official document supports them.

## Important limits

- This archive is a fully functional local website and contains a deployment workflow. It is **not deployed or scheduled until you connect it to a repository and run the workflow**.
- `file://` browsers may block fetching `monitor.json`; the site still works offline with its 15 November 2026 research baseline. Host locally (`python -m http.server 8000`) to see the dynamic log, or use GitHub Pages.
- `localStorage` is device/browser/origin-specific. Use **Export backup** and **Import backup** when moving between devices or origins.
- Original 2026/27 conditions are labelled as historic; not silently copied into 2027/28 deadlines.