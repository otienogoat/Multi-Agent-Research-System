from src.tools.tools import web_search, scrape_url
from src.pipelines.pipeline import run_research_pipeline

r=web_search.invoke("what is the latest research...")
print(r)
topic="Recent research on triton kernels and Distributed parallel training"
run_research_pipeline(topic)