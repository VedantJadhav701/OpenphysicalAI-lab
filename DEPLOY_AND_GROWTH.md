# Landing page: deploy on Vercel, direct download links, and growing GitHub stars

Repo: `https://github.com/VedantJadhav701/OpenphysicalAI-lab`

## 1. What is in this folder

```text
landing/
├─ index.html            page (no build step)
├─ css/style.css
├─ js/main.js            reveal, counters, GitHub stars + latest-release links, tabs, share
├─ js/arm.js             hero: 3D robot arm (Three.js) doing pick, slip, recover, place
├─ js/demo.js            interactive latency-tax illustration
├─ vendor/               three.module.min.js (r160) + two addons, so no CDN is needed
├─ assets/               logos, og.png (social card), poster, 60 s launch video (web encode)
├─ vercel.json           headers and clean URLs
└─ robots.txt
```

It is a static site. No Node, no bundler.

## 2. Deploy on Vercel

Option A: put it in the repo (recommended, one place for everything)

1. Copy this folder into the repo as `landing/` and push.
2. Vercel dashboard, Add New, Project, import the GitHub repo.
3. Framework Preset: **Other**. Root Directory: **landing**. Build command: leave empty. Output directory: leave empty.
4. Deploy. Every push to `main` redeploys.

Option B: CLI

```bash
cd landing
npx vercel          # first run, answer the prompts
npx vercel --prod
```

After it is live:

- Put the Vercel URL in the repo "Website" field (repo page, gear icon next to About).
- Replace `<link rel="canonical" href="/">` and the `og:image` / `twitter:image` values with absolute URLs (`https://YOUR-SITE.vercel.app/assets/og.png`). Social crawlers need absolute image URLs.
- Optional: add a custom domain in Vercel, Settings, Domains.

Test locally: `cd landing && python -m http.server 8080`, open `http://localhost:8080`. Open it over http, not by double-clicking the file, because the page uses ES modules.

## 3. Direct download links on GitHub Releases

The page already fetches `releases/latest` from the GitHub API and points the buttons at the real `.exe` files. If the API is blocked or rate limited it falls back to `https://github.com/VedantJadhav701/OpenphysicalAI-lab/releases/latest`.

Note: GitHub turns spaces in asset names into dots, so `OpenPhysicalAI Lab Setup 0.2.0.exe` becomes `OpenPhysicalAI.Lab.Setup.0.2.0.exe`. For a permanent direct link that never changes, give the files fixed names.

In `package.json` (electron-builder `build` section):

```json
"nsis":     { "artifactName": "OpenPhysicalAI-Lab-Setup.${ext}" },
"portable": { "artifactName": "OpenPhysicalAI-Lab-Portable.${ext}" },
"dmg":      { "artifactName": "OpenPhysicalAI-Lab-${arch}.${ext}" }
```

Then these links always work and always point at the newest release:

```text
https://github.com/VedantJadhav701/OpenphysicalAI-lab/releases/latest/download/OpenPhysicalAI-Lab-Setup.exe
https://github.com/VedantJadhav701/OpenphysicalAI-lab/releases/latest/download/OpenPhysicalAI-Lab-Portable.exe
```

Use the first one in the README badge/button. (I have not been able to test these URLs from here; confirm after your next release.)

Release checklist:

1. Tag: `git tag v0.2.1 && git push --tags` (your workflow publishes with `softprops/action-gh-release`).
2. Make sure `files:` in that action lists `dist/*.exe`, `dist/*.dmg`, `dist/*.zip`.
3. Add a `SHA256SUMS.txt` asset and mention that builds are unsigned.
4. Write real release notes: what is new, measured numbers with N, known limits.

Real assets found on your latest release (v0.2.1, checked through the GitHub API):

```text
https://github.com/VedantJadhav701/OpenphysicalAI-lab/releases/download/v0.2.1/OpenPhysicalAI.Lab.Setup.0.2.1.exe      (81.7 MB, Windows installer)
https://github.com/VedantJadhav701/OpenphysicalAI-lab/releases/download/v0.2.1/OpenPhysicalAI.Lab.0.2.1.exe            (81.5 MB, Windows portable)
https://github.com/VedantJadhav701/OpenphysicalAI-lab/releases/download/v0.2.1/OpenPhysicalAI.Lab-0.2.1-universal.dmg  (179.7 MB, macOS)
https://github.com/VedantJadhav701/OpenphysicalAI-lab/releases/download/v0.2.1/OpenPhysicalAI.Lab-0.2.1-universal-mac.zip
```

These are version-pinned. The landing page does not hard-code them; it reads the newest release at load time, so the buttons update on every release without editing the site.

The macOS `.dmg` is on the release, but a launch on a real Mac has not been verified by me. Test it (and say so in the release notes) before you promote macOS support.

## 4. Repository polish that moves the needle

Do these before any launch post. A visitor decides in about 10 seconds.

0. Right now the repo has **no description, no topics and 0 stars** (read from the GitHub API). Fix the next three items first.
1. **About box**: description "Open-source Physical AI evaluation lab: real MuJoCo physics, real-time latency, measured VRAM/RAM/energy budgets. Runs on a 4 GB laptop." Add the website URL.
2. **Topics** (up to 20): `physical-ai`, `robotics`, `embodied-ai`, `mujoco`, `benchmark`, `robot-learning`, `ollama`, `local-llm`, `llm-agents`, `simulation`, `vla`, `electron`, `python`, `edge-ai`, `reinforcement-learning`, `robot-manipulation`.
3. **Social preview image**: Settings, General, Social preview, upload `assets/og.png` (1280x640).
4. **README top**: logo, one-line promise, three badges at most on the first row, the video, then a 3-command quick start above the fold. Keep the long benchmark tables lower.
5. **README video**: the line `https://github.com/user-attachments/assets/OpenPhysicalAI_Lab_Launch_30s.mp4` is a placeholder and will not play. To get a real one: edit the README on github.com in the browser, drag the .mp4 into the editor, and GitHub inserts a working `user-attachments` URL. Max 100 MB (the 60 s file is about 12 MB). Also add a GIF or the `launch-poster.jpg` linked to the landing page as a fallback.
6. **README anchors**: the badge links to `#quick-start` but there is no heading with that name. Rename "### 1. Install via pip (PyPI)" section to a `## Quick start` heading.
7. **Add**: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, issue templates (bug, hardware result, new task), 10+ issues labelled `good first issue` and `help wanted`, and GitHub Discussions on.
8. **A releases page that looks alive**: ship small, frequent releases (every 1 to 2 weeks at first) with a changelog.
9. **Pin** the repo on your GitHub profile and link it from your portfolio site.

## 5. Launch plan (honest, no shortcuts)

Stars come from people who find it useful. Do not buy stars or trade them; fake stars violate GitHub's terms, get repos flagged and destroy credibility.

Day 0 to 2: prepare

- Re-run the verifier and latency benchmarks once more and make sure the README, the site and the video all show the same numbers.
- Record a 20 to 40 s screen capture of the real desktop app running a task (this is more convincing than any animation) and put it in the README.
- Write the first study as a short post: "What a 4 GB laptop can do: the latency tax in Physical AI", with the tables, N, CIs and the command to reproduce.

Launch day (Tuesday to Thursday, US morning works best for Hacker News)

1. **Show HN**: title `Show HN: OpenPhysicalAI Lab – benchmark Physical AI under real VRAM and latency budgets`. First comment: why you built it, the one surprising result (success falls from 38% to 0% when planning takes 1 s on a moving target), what is verified and what is not, how to run it in 3 commands. Reply to every comment for the first few hours.
2. **Reddit**: r/robotics, r/LocalLLaMA, r/MachineLearning (as a "Project" post), r/ROS only if relevant. Tailor each post; do not cross-post identical text. Read each subreddit's self-promotion rules first.
3. **X and LinkedIn**: a short thread with the video, one chart per post, and the repo link in the last post.
4. **Hugging Face**: post in the community / Spaces; consider a small Space that renders a Budget Card.
5. **Discord/Slack communities**: LeRobot, MuJoCo, Ollama, local-LLM servers. Share where self-promo is allowed.
6. **Direct outreach**: a short, personal message to 10 people who write about robot evaluation, with the one chart that matters. Ask for feedback, not stars.
7. **Awesome lists**: search for `awesome-robotics`, `awesome-mujoco`, `awesome-ollama`, `awesome-embodied-ai` and open PRs where the project fits their rules.

Days 3 to 30

- Answer issues within 24 hours. Fast replies are the strongest signal on a small project.
- Publish a Hardware Wall call: "Run `opai doctor` and add your GPU." Feature every contributor in the next release notes.
- Ship the roadmap items that people ask for most (CPU-only mode, macOS build, drawer task, learned-policy track).
- Post a short update per release with a new measured result.

Suggested X post (edit with your real numbers):

```text
Most Physical AI benchmarks pause the world while the model thinks.

So I built one that doesn't. On a 4 GB laptop GPU, a reactive agent drops from 38% to 0% success when planning takes just 1 second on a moving target. Velocity lead brings it back.

Open source, runs locally, every number has an N and a CI.
github.com/VedantJadhav701/OpenphysicalAI-lab
```

## 6. Data points to double-check before you publish (from your README)

- The velocity-lead row shows "N=50" in the table header but a CI of 72.2 to 100%, which corresponds to about 10 episodes. Re-run with N of at least 50 or label the row with its real N. The page and video label it "small sample".
- The three verifier success rates (74, 68, 73) have overlapping confidence intervals. The solid finding is the missed-failure gap (3.7% vs 0.3%). A paired test on the same seeds would make the claim stronger.
- "Signed Budget Card": make sure the code really signs it, or call it "hashed".
- The PyPI badge only works after `openphysicalai` is actually published; check the package page loads.
- State clearly that macOS and Linux desktop builds are not yet verified, and that the Windows builds are unsigned.
- The 432 FPS render figure is for the 3D renderer on your RTX 3050 laptop; keep the hardware named next to it, as the page does.

## 7. What the animations on the page are

The hero arm and the latency demo are illustrations written for the web (Three.js and canvas). They are not live MuJoCo streams, and the page says so ("illustrative animation"). The numbers on the page are the ones from your README. If you change a benchmark, update `index.html` (search for the number) and tell me so I can re-render the video.
