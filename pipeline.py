from agents import build_search_agent, build_reader_agent, writer_chain, critic_chain

def run_research_pipeline(topic: str) -> dict:
    state = {}

    #search agent working
    print('\n'+'-'*20+"[bold green]Running Search Agent...[/bold green]"+'-'*20+'\n')
    search_agent = build_search_agent()
    search_results = search_agent.invoke({
        "messages" : [("user", f"Find recent, reliable and detailed information about: {topic}")] 
    })
    state["search_results"] = search_result['messages'][-1].content
    print("\n search result ",state['search_results'])