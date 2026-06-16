from pipelines.retrieval.rag_chain import run_rag_stream

query = "Apa kriteria usaha mikro?"

for event in run_rag_stream(query, project_id=None):
    if event["type"] == "sources":
        print(f"\n[SOURCES] {len(event['data'])} chunks\n")
    elif event["type"] == "token":
        print(event["data"], end="", flush=True)
    elif event["type"] == "done":
        print(f"\n\n[DONE] {event['data']}")