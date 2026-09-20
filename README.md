# PTE BluePrep

A practice web app for the PTE Academic test. Students practise all 22 task types with real exam timing, get an instant practice score for every answer, and can ask Claude for examiner-style feedback on their speaking and writing.

> Every score in this app is a **practice estimate** to help students prepare. It is not an official Pearson PTE Academic result, and this project is not affiliated with Pearson.

## What's inside

- **A full mock test**: all three parts back to back with real exam timing, no feedback until the end, then a full score report. See "The full mock test" below.
- **All 22 task types**: speaking and writing, reading, and listening, each with its own screen.
- **15 random questions per set.** Questions a student saw in their last 3 sets of that type are left out where possible.
- **A question bank in MySQL with a backup pool.** Every type ships with 45 original questions: 30 active and 15 backup. Retiring a question (or 3 reports from students) promotes the oldest backup automatically.
- **Real exam timing**: audio lead-in, preparation and answer countdowns. Writing boxes lock when time is up.
- **Speaking practice in the browser.** The browser records you, turns your speech into text (in Chrome and Edge) and lets you listen back. Recordings never leave the device; only the transcript is sent.
- **Server-side scoring** for every task, including partial credit, minus marks for wrong choices, and the form rules that zero out summaries and essays.
- **Examiner feedback from Claude** for speaking and writing tasks, limited to 30 requests per student per day.
- **An admin area** to browse, edit, retire and promote questions and handle reports.

## How it's built

| Part | Technology |
| --- | --- |
| API | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, PyMySQL, Gunicorn with Uvicorn workers |
| Web | React 18, Vite, TypeScript, React Router, TanStack Query, CSS modules |
| Database | MySQL 8 (DigitalOcean Managed MySQL in production) |
| Hosting | DigitalOcean App Platform |

```
backend/
  app/            API code: models, routes, scoring/, services/ (draw, pool, feedback), variants.py
  alembic/        database migrations
  scripts/        validate_bank, seed, export_bank, create_admin
  tests/          pytest (runs against a real MySQL 8 database)
frontend/
  src/tasks/      one component per task type, plus shared pieces
  src/hooks/      useExamTimer, useSpeech, useRecorder
  src/pages/      home, practice, results, sign in and sign up
  src/admin/      question bank admin
  e2e/            Playwright smoke test
seed/generated/   the question bank as JSON
.do/app.yaml      App Platform spec
.github/workflows/bank-backup.yml   weekly JSON backup to Spaces
```

## Run it on your computer

You need **Docker Desktop** and **Node.js 22.12 or newer**. You don't need Python installed, because the API runs in Docker.

```bash
cp .env.example .env          # add your ANTHROPIC_API_KEY if you want examiner feedback
make install                  # build the API image and install frontend packages
docker compose up -d db api   # start MySQL 8 and the API
make migrate                  # create the tables
make seed                     # load the 22 task types and 990 questions
make create-admin EMAIL=you@example.com NAME="Your Name"
cd frontend && npm run dev    # open http://localhost:5174
```

The local ports are 3318 (MySQL), 8010 (API) and 5174 (web) so they don't clash with other projects. You can change them in `.env`. The API docs are at http://localhost:8010/api/docs.

Local MySQL runs with `sql_require_primary_key=ON`, the same as DigitalOcean.

### Everyday commands

| Command | What it does |
| --- | --- |
| `make dev` | Start MySQL, the API (auto-reloads) and the web dev server |
| `make migrate` | Apply database migrations |
| `make seed` | Load task types and the question bank. Safe to run again: nothing is duplicated and admin status changes are kept |
| `make validate-bank` | Check every question bank file |
| `make export-bank` | Write the whole bank, including retired questions, to `bank-export.json` |
| `make test` | Backend tests (against MySQL) and frontend tests |
| `make e2e` | Playwright smoke test: sign up, answer a Write from Dictation question, see a score |

## The full mock test

A mock test copies the shape of the real exam. Everything about it comes from one file,
`backend/app/exam/blueprint.py`: the order of the parts, how many questions of each type, how long
each one allows, and which skills each type counts towards. The item counts and the skill mapping
follow the PTE Academic Score Guide.

| Part | Timing | Questions |
| --- | --- | --- |
| Part 1: Speaking and Writing | about 73 to 84 minutes, each question timed on its own | Read Aloud, Repeat Sentence, Describe Image, Retell Lecture, Answer Short Question, Summarize Group Discussion, Respond to a Situation, Summarize Written Text, Write Essay |
| Part 2: Reading | 30 minutes for the whole part | Reading & Writing FIB, Multiple Choice (multiple), Reorder Paragraphs, Reading FIB, Multiple Choice (single) |
| Part 3: Listening | about 36 to 49 minutes | Summarize Spoken Text, Multiple Choice (multiple), FIB, Highlight Correct Summary, Multiple Choice (single), Select Missing Word, Highlight Incorrect Words, Write from Dictation |

How it behaves like the real test:

- It opens with the **unscored spoken introduction**, then shows instructions before each part.
- **The server owns the clock.** Every deadline is set when a question is first shown, so refreshing,
  opening a new tab or changing your computer's clock can't buy extra time. An answer sent after the
  deadline is kept but scores zero, like a missed question.
- **Reading runs on one 30 minute clock** and lets you move back and change answers. Everything else
  is one way: once you move on, you can't return.
- **No scores during the test.** The answer is marked and stored, but nothing is shown until the end.
- **Leaving and coming back** resumes at the right question, with whatever time is left. If every
  remaining question has timed out, the test submits itself.
- The **score report** gives an overall practice estimate, the four communicative skills, the enabling
  skills and a per-part breakdown, and every answer can be reviewed with the correct answer shown.

**Spelling** is checked against an offline dictionary that accepts British, Australian and American
spelling, plus the words of the question a student is answering. The report scores it as errors per
100 typed words, says how many words that was measured over, and lists each misspelled word with
what it looked like you meant. A misspelling costs a student once: in the writing tasks it lowers
that item's Spelling trait, and in Write from Dictation and the listening blanks the word was already
marked wrong by the answer key, so it is recorded there rather than deducted twice. The British and
Australian forms are generated from the American word list by rule (see `app/spelling/variants.py`),
so a rare word may be accepted that a full Hunspell dictionary would flag - deliberately, because
wrongly telling a student that "organise" is a mistake is the worse failure.

`MOCK_TIME_SCALE` shortens every clock for end-to-end tests and should stay at 1.

## The question bank

Questions live in `seed/generated/*.json`. Every file has the same shape:

```json
{
  "version": 1,
  "notes": "...",
  "sources": [{ "source_key": "lec-urban-heat", "kind": "lecture", "title": "...", "body": "..." }],
  "questions": [{ "type": "RL", "source_key": "lec-urban-heat", "status": "active", "difficulty": 2, "payload": { "key_points": ["..."] } }]
}
```

Shared texts are stored once as **sources**. One lecture feeds 8 listening and speaking types, one passage feeds 5 reading and writing types, and one discussion feeds Summarize Group Discussion. Passages mark blanks as `{{correct|distractor|distractor|distractor}}`.

To add or change questions:

1. Edit or add a JSON file in `seed/generated/`.
2. Run `make validate-bank`. It checks the required fields for each type, answer indexes, blank markup, word counts and duplicates, and needs at least 30 active and 15 backup questions per type.
3. Run `make seed`.

If `reference/pte_seed_questions.json` exists, the validator and seed script load it too.

Some questions are generated fresh for every student: Describe Image charts get random values from a template, Listening Fill in the Blanks picks new blanks, Highlight Incorrect Words picks which words to swap, and choices are shuffled. The exact version a student saw is saved with their answer, so review and scoring always match.

Answers never reach the browser before the student submits. The one exception is the text read aloud by the browser for listening tasks (see "Things to know").

## How scoring works

All scores are practice estimates. Each answer is scored on the server:

- **Fill in the blanks**: one point per correct blank.
- **Multiple answers and Highlight Incorrect Words**: plus one for each right choice, minus one for each wrong one, never below zero.
- **Reorder Paragraphs**: one point for each correct pair of neighbouring paragraphs.
- **Write from Dictation**: one point for each word spelled correctly, in any order.
- **Summarize Written Text, Write Essay, Summarize Spoken Text**: form is checked first (one sentence of 5 to 75 words; 200 to 300 words; 50 to 70 words). If form scores zero, the whole answer scores zero. Content, grammar, vocabulary and structure use simple, transparent checks.
- **Speaking**: content comes from the speech-to-text transcript, such as words matched in order for Read Aloud and Repeat Sentence, or key points covered for open answers. Fluency and pronunciation come from the student's own rating, or are estimated from the transcript.

A set's practice estimate maps the average percentage onto the 10 to 90 scale. Unanswered questions count as zero.

## Examiner feedback

Speaking and writing answers have a **Get examiner feedback** button. The API sends the task, the student's answer and the automatic score to Claude (`claude-sonnet-5` by default, set with `ANTHROPIC_MODEL`) and saves the result, so asking again costs nothing. The API key only ever lives in the `ANTHROPIC_API_KEY` environment variable on the server.

## Deploy to DigitalOcean

These commands use [`doctl`](https://docs.digitalocean.com/reference/doctl/how-to/install/). Run them yourself; nothing in this repo touches your account.

**1. Sign in to your own DigitalOcean account and connect GitHub**

This app belongs in your personal DigitalOcean account, not the FRENZ one. `doctl` on this computer already has a saved login called `default`, which may be a different account, so create a separate login called `personal` and use it for every command below.

1. Sign in to your personal account in the browser and create a token under **API → Tokens** (read and write).
2. Save it as its own `doctl` login and check it is the right account:

```bash
doctl auth init --context personal   # paste the token from your personal account
doctl account get --context personal   # the email shown must be your personal account
```

Every command below includes `--context personal`, so nothing can land in another account by accident. Don't run `doctl auth switch`; leave your other login as it is.

While signed in to your **personal** account in the control panel, open **Apps → Create App** once and authorise GitHub access to this repository, then cancel. App Platform needs that permission before it can deploy from GitHub.

**2. Create the MySQL database** (Sydney is the closest region to New Zealand)

```bash
doctl databases create pte-mysql --engine mysql --version 8.4 --region syd1 --size db-s-1vcpu-1gb --num-nodes 1 --context personal
doctl databases list --context personal   # copy the cluster ID
doctl databases db create <cluster-id> pte --context personal
doctl databases user create <cluster-id> pte --context personal
```

**3. Prepare the app spec**

```bash
cp .do/app.yaml .do/app.local.yaml                     # ignored by git
```

In `.do/app.local.yaml`, put real values in place of the two `REPLACE_ME` secrets:

```bash
openssl rand -hex 32                                   # use this for JWT_SECRET
```

**4. Create the app**

```bash
doctl apps spec validate .do/app.local.yaml --context personal
doctl apps create --spec .do/app.local.yaml --context personal
doctl apps list --context personal   # copy the app ID
```

Each deploy first runs `alembic upgrade head` as a pre-deploy job.

> **"No components detected" in the control panel?** That's expected. The app lives in `backend/` and `frontend/` rather than the repository root, so DigitalOcean's automatic detection can't find it. Create the app from the spec instead, with the `doctl apps create` command above. If you'd rather use the control panel: set **Source directory** to `frontend` so it detects the website, create the app, then go to **Settings → App Spec → Edit**, paste the whole of `.do/app.local.yaml` and save.

**5. Load the questions and create your admin account** (once, after the first deploy succeeds)

```bash
doctl apps console <app-id> api --context personal
# then, inside the console:
python -m scripts.seed
python -m scripts.create_admin --email you@example.com --name "Your Name"
```

You can also use the **Console** tab for the `api` component in the control panel.

**6. Lock down the database (recommended)**

```bash
doctl databases firewalls append <cluster-id> --rule app:<app-id> --context personal
```

This allows only the app to connect. The GitHub Actions backup below runs outside DigitalOcean, so it can't connect once trusted sources are on. Either add your own backup runner's IP, or run the export from the app console (`python -m scripts.export_bank --out /tmp/bank.json`).

**Updating the app later**: pushes to `main` redeploy automatically. After changing the spec, run `doctl apps update <app-id> --spec .do/app.local.yaml --context personal`.

## Backups

- **Managed MySQL takes daily backups automatically** and keeps them for 7 days. You can restore them from the control panel.
- **A readable copy of the question bank** is exported every week by `.github/workflows/bank-backup.yml` and uploaded to a DigitalOcean Spaces bucket as JSON. It uses the same format as the seed files, so you can edit it and seed it back.

To set up the weekly export, create a private Spaces bucket and a Spaces access key in your personal account's control panel, then add these repository secrets:

```bash
gh secret set PROD_DATABASE_URL          # mysql://pte:<password>@<host>:25060/pte?ssl-mode=REQUIRED
gh secret set PROD_DATABASE_CA_CERT < ca-certificate.crt   # download from the database's Overview page
gh secret set SPACES_ACCESS_KEY_ID
gh secret set SPACES_SECRET_ACCESS_KEY
gh secret set SPACES_BUCKET              # for example pte-bank-backups
gh secret set SPACES_REGION              # for example syd1
```

Run it once by hand from the **Actions** tab (**Question bank backup → Run workflow**) to check it works.

## Rough monthly cost

Check the current prices on the [DigitalOcean pricing page](https://www.digitalocean.com/pricing). The smallest sensible setup, in US dollars:

| Item | Approx. per month |
| --- | --- |
| API service (1 GB instance) | $10 to $12 |
| Static site | free (3 static sites are included) |
| Pre-deploy migration job | a few cents (billed only while it runs) |
| Managed MySQL, 1 GB single node | $15 |
| Spaces for backups (optional) | $5 |
| **Total** | **about $30 to $32** (about $25 to $27 without Spaces) |

Claude API usage for examiner feedback is billed separately by Anthropic.

## Configuration

Every setting is listed with a comment in `.env.example`. The main ones are `QUESTIONS_PER_SET` (15), `MIN_ACTIVE_PER_TYPE` (30), `RECENT_SETS_EXCLUDED` (3), `REPORT_RETIRE_THRESHOLD` (3) and `FEEDBACK_DAILY_LIMIT` (30).

## Things to know

- **Listening audio is read out by the browser** (speech synthesis), so the text being spoken is sent to the browser. A student who opens developer tools could read a dictation sentence. Generating audio files on the server would close this gap.
- **Speech-to-text works in Chrome and Edge.** In other browsers students record, listen back and rate themselves. Pronunciation and fluency can't be measured from text alone, so treat speaking scores as a rough guide and use examiner feedback for more detail.
- **Not built yet**: password reset, email verification, and rate limiting on sign-in attempts.
