import time

from src.agents.agents import (
    build_search_agent,
    build_reader_agent,
    writer_chain,
    critic_chain,
)

PAUSE = 20  # seconds, keeps us under Groq's free per-minute token limit


def run_research_pipeline(topic: str) -> dict:
    state = {}

    # Step 1: search agent
    print("\n" + "=" * 50)
    print("Step 1 - Search agent is working...")
    print("=" * 50)

    search_agent = build_search_agent()
    search_result = search_agent.invoke({
        "messages": [("user", f"Find recent, reliable and detailed information about: {topic}")]
    })
    state["search_results"] = search_result["messages"][-1].content
    print("\nSearch results:\n", state["search_results"])
    time.sleep(PAUSE)

    # Step 2: reader agent
    print("\n" + "=" * 50)
    print("Step 2 - Reader agent is scraping top sources...")
    print("=" * 50)

    reader_agent = build_reader_agent()
    reader_result = reader_agent.invoke({
        "messages": [("user",
            f"Based on the following results about '{topic}', "
            f"pick the most relevant URL and scrape it for deeper content.\n\n"
            f"Search Results:\n{state['search_results'][:2000]}"
        )]
    })
    state["scraped_content"] = reader_result["messages"][-1].content
    print("\nScraped content:\n", state["scraped_content"])
    time.sleep(PAUSE)

    # Step 3: writer chain
    print("\n" + "=" * 50)
    print("Step 3 - Writer is drafting the report...")
    print("=" * 50)

    research_combined = (
        f"SEARCH RESULTS:\n{state['search_results'][:2500]}\n\n"
        f"DETAILED SCRAPED CONTENT:\n{state['scraped_content'][:2500]}"
    )
    state["report"] = writer_chain.invoke({
        "topic": topic,
        "research": research_combined,
    })
    print("\nFinal report:\n", state["report"])
    time.sleep(PAUSE)

    # Step 4: critic chain
    print("\n" + "=" * 50)
    print("Step 4 - Critic is reviewing the report...")
    print("=" * 50)

    state["feedback"] = critic_chain.invoke({"report": state["report"]})
    print("\nCritic report:\n", state["feedback"])

    return state