from agents import build_search_agent, build_reader_agent, writer_chain, critic_chain

def run_research_pipeline(topic: str) -> dict:
    state = {}

    # search agent working
    print('\n'+'-'*20+"[bold green]Running Search Agent...[/bold green]"+'-'*20+'\n')
    search_agent = build_search_agent()
    search_result = search_agent.invoke({
        "messages" : [("user", f"Find recent, reliable and detailed information about: {topic}")] 
    })
    state["search_results"] = search_result['messages'][-1].content
    print("\nsearch result: \n",state['search_results'])

    # reader agent working
    print('\n'+'-'*20+"[bold green]Reader Agent is scraping top sources...[/bold green]"+'-'*20+'\n')
    reader_agent = build_reader_agent()
    reader_result = reader_agent.invoke({
        "messages": [("user",
            f"Based on the following search results about '{topic}', "
            f"pick the most relevant URL and scrape it for deeper content.\n\n"
            f"Search Results:\n{state['search_results'][:800]}"
        )]
    })
    state['scraped_content'] = reader_result['messages'][-1].content
    print("\nscraped content: \n", state['scraped_content'])

    # writer chain working
    print('\n'+'-'*20+"[bold green]Writer Agent is drafting the research report...[/bold green]"+'-'*20+'\n')
    research_combined = (
        f"SEARCH RESULTS : \n {state['search_results']} \n\n"
        f"DETAILED SCRAPED CONTENT : \n {state['scraped_content']}"
    )
    state["report"] = writer_chain.invoke({
        "topic" : topic,
        "research" : research_combined
    })
    print("\n Final Report\n",state['report'])

    # critic chain working
    print('\n'+'-'*20+"[bold green]Critic Agent is evaluating the report...[/bold green]"+'-'*20+'\n')
    state["feedback"] = critic_chain.invoke({
        "report":state['report']
    })
    print("\n critic report \n", state['feedback'])

    return state

if __name__ == "__main__":
    topic = input("\n Enter a research topic : ")
    run_research_pipeline(topic)