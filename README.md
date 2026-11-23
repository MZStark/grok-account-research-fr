# grok-account-research-fr

**An account-research agent for a sales rep selling Grok Bot to French Mid-Market companies (ETI, 250 to 5,000 employees).**

Type a French company name. Get back, in French and in Markdown:

1. **An account brief**: what the company does, size, sector, recent news, and buying signals (funding, hiring, expansion).
2. **The 3 most relevant Grok Bot use cases** for that company, each with the team involved, the problem and the expected benefit, tied to a fact from the brief.
3. **A first outreach message** in French, under 120 words, human tone, no jargon.

```bash
python main.py "Qonto" -o examples/qonto.md
```

## The problem

Before a first call, a Mid-Market AE spends 30 to 45 minutes per account: reading the website, the French business press, the careers page and LinkedIn, then guessing which use case to open with. The research is repetitive, the output is rarely structured, and the opener often ends up generic ("I saw you're growing fast..."). Outreach to French companies also needs to be written in natural French, not translated English.

This tool turns that into one command: sourced facts first, use cases derived from those facts, then a short message that opens on a real, recent event.

## Demo

![Demo](docs/demo.gif)

_Recorded with the Streamlit UI (`streamlit run app.py`)._

Sample outputs on public French companies (Qonto, Alan, Doctolib) are in [`examples/`](examples/).

## Install (3 commands)

```bash
git clone https://github.com/MZStark/grok-account-research-fr.git && cd grok-account-research-fr
pip install -r requirements.txt
cp .env.example .env   # then set XAI_API_KEY
```

Run:

```bash
python main.py "Doctolib"                      # prints the report
python main.py "Alan" -o examples/alan.md      # writes it to a file
streamlit run app.py                           # optional demo UI
pytest                                         # offline tests, no key needed
```

## Architecture

```mermaid
flowchart LR
    A["Company name"] --> R["agents/research.py<br/>account brief"]
    R -->|"Grok Responses API<br/>+ web_search tool"| W[("Live web")]
    R -.->|"SEARCH_PROVIDER=tavily"| T[("Tavily API")]
    R --> U["agents/use_cases.py<br/>3 use cases (JSON, validated)"]
    U --> O["agents/outreach.py<br/>message &lt; 120 words"]
    O --> M["Markdown report<br/>+ sources"]
    P["prompts/*.md"] -.-> R & U & O
```

| Path | Role |
|---|---|
| `agents/research.py` | Builds the account brief from live sources (Grok's built-in `web_search` tool, or Tavily as a fallback). |
| `agents/use_cases.py` | Picks the 3 most relevant Grok Bot use cases from the brief. Asks for strict JSON, validates it, retries once if invalid. |
| `agents/outreach.py` | Writes the first message; counts words and asks for a shorter version if it goes over 120. |
| `prompts/` | One plain-text prompt per step, plus `product.md` (what Grok Bot does, so the model never invents features). |
| `core/llm.py` | Grok client through the OpenAI-compatible SDK (`base_url=https://api.x.ai/v1`), with retries and clear error messages. |
| `core/pipeline.py` | Runs the three steps and assembles the report. |
| `main.py` / `app.py` | CLI and optional Streamlit UI. |

**Design choices**

- **Three small agents, not one big prompt.** Each step has one job and its own prompt, so you can read, test and tune them separately.
- **Facts before ideas.** Use cases and the message only see the brief, and every use case must cite the signal it comes from.
- **Structured hand-off.** Step 2 returns validated JSON; a malformed answer is caught and corrected instead of breaking the report.
- **Prompts are data.** They live in `prompts/` as Markdown, editable without touching the code.

## Configuration

All settings live in `.env` (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `XAI_API_KEY` | (required) | Your xAI API key |
| `GROK_MODEL` | `grok-4.7` | Any Grok model available on your account |
| `XAI_BASE_URL` | `https://api.x.ai/v1` | API endpoint |
| `SEARCH_PROVIDER` | `grok` | `grok` (built-in web search) or `tavily` |
| `TAVILY_API_KEY` | (empty) | Only if `SEARCH_PROVIDER=tavily` |
| `REQUEST_TIMEOUT_S` | `300` | Per-request timeout |
| `MAX_RETRIES` | `3` | Retries on timeouts, rate limits and 5xx errors |

## Error handling

- Missing or invalid settings stop the run before any API call, with a message saying what to fix.
- Timeouts, connection errors, `429` and `5xx` are retried with exponential backoff (1 s, 2 s, 4 s).
- `401` (bad key) and `404` (unknown model) fail immediately with a specific message.
- The CLI exits with code `1` and a one-line French error, never a stack trace.

## Known limitations

- **It can be wrong.** The brief depends on what is public and indexed; small or very discreet companies return thin results. The report says "non trouvé" rather than guessing, and lists its sources, but every fact must be checked before sending anything.
- **Recency is not guaranteed.** Web results can surface old articles; the prompt asks for dated news under 12 months old, but cannot enforce it.
- **Use cases are hypotheses**, not a discovery call. They are meant to pick the opening angle, not to replace qualification.
- **The 120-word limit** is checked after generation and retried once; in rare cases the message stays over the limit and the report flags it.
- **Cost and latency**: one run makes three API calls, the first with web search, so it typically takes 3 to 5 minutes.
- **No CRM integration** yet: output is a Markdown file.
- **Privacy**: the tool only targets companies and public business information. Do not use it to profile private individuals.

## License

MIT, see [LICENSE](LICENSE).
