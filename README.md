# Multi-Agent Research System

Give it a topic and four agents research it for you. One searches the web, one reads the best page, one writes a structured report, and one scores the report and says what to improve.

Built with LangChain, Groq and Tavily. It runs on free tiers.

## How it works

```
topic
  |
  v
Search agent   -> finds recent sources (Tavily)
  |
  v
Reader agent   -> opens the best URL and extracts the text
  |
  v
Writer chain   -> drafts a report with sources
  |
  v
Critic chain   -> scores it out of 10, lists strengths and fixes
```

- The search and reader agents are tool-calling agents built with `create_agent`.
- The writer and critic are plain prompt chains (`prompt | llm | parser`).
- Page text is pulled with trafilatura first, then readability, then plain BeautifulSoup as a fallback.

## Project structure

```
.
├── app.py                  # Streamlit interface
├── main.py                 # run the pipeline from the terminal
├── requirements.txt
├── .env.example            # copy to .env and add your keys
└── src
    ├── agents/agents.py    # model setup, search agent, reader agent, writer and critic chains
    ├── pipelines/pipeline.py  # runs the four steps in order
    └── tools/tools.py      # web_search and scrape_url tools
```

## Setup

You need Python 3.11 and two free API keys:

- Groq: console.groq.com/keys
- Tavily: tavily.com

**Windows (PowerShell)**

```
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

**macOS / Linux**

```
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your keys:

```
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key
```

`.env` is in `.gitignore`. Never commit your keys.

## Run it

Web interface:

```
streamlit run app.py
```

Terminal:

```
python main.py
```

Run both from the project root so the `src` imports work.

A full run takes a few minutes on the free tier, because the pipeline pauses between steps to stay under Groq's per-minute token limit.

## Change the model

The model is set in `src/agents/agents.py`. It uses Groq through its OpenAI-compatible endpoint, so any provider with that kind of endpoint works. Change `model`, `openai_api_base` and the API key variable.

The default is `openai/gpt-oss-120b`. The agents need a model that handles tool calling cleanly. In testing, Qwen3.8 on Groq sometimes wrote malformed tool calls and failed, so if a model gives tool errors, try a different one. Groq's model list changes, so check your console if a name is rejected.

## Troubleshooting

| Problem                          | Fix                                                                                                        |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `413` or `429` rate limit error  | You hit Groq's free per-minute token limit. Wait a minute and run again, or raise the pause between steps. |
| `model_not_found`                | That model is not available on your account. Pick another from the Groq console.                           |
| `Invalid API key`                | Check `.env` is in the project root, has no quotes or spaces around `=`, and restart the app.              |
| `No module named src`            | Run from the project root, not from inside `src`.                                                          |
| Connection errors during install | Retry with `pip install -r requirements.txt --default-timeout=100 --retries 10`.                           |

## Limitations

- It reads one page per run, so the report is only as good as the search results and that page.
- Some sites block scrapers or load content with JavaScript, and those pages return little or nothing.
- The critic is the same kind of model as the writer, so treat its score as a rough guide.
- Always check the cited sources before relying on a claim.

## License

See [LICENSE](LICENSE).
