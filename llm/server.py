from graph import create_graph, Command
from langgraph.checkpoint.memory import MemorySaver
from tools import transfer, getAccountBalance

###### configuration ######

memory = MemorySaver()
graph = create_graph(memory, tools=[transfer, getAccountBalance])



###### stream event generator ######

async def graph_generator(query, thread_id: str = None):
    
    data = {'messages':[{'role': 'user', 'content': query}]} if isinstance(query, str) else Command(resume=query)
    async for event in graph.astream_events(data, config={"configurable": {"thread_id": thread_id}}, version="v2"):
        
        if event["event"] == "on_chat_model_stream":
            if event["data"]["chunk"].content:
                yield f"data: {event['data']['chunk'].content}\n\n"

        elif event["event"] == "on_tool_start":
            tool_name = event["name"]
            tool_input = event["data"]["input"]
            
            yield f"data: [TOOL_START]{tool_name}:{tool_input}[/TOOL_START]\n\n"
        
        elif event["event"] == "on_tool_end":
            tool_output = event["data"]["output"]
            yield f"data: [TOOL_END]{tool_output}[/TOOL_END]\n\n"
        
        elif event["event"] == "on_chain_end" and "output" in event["data"]:
            if "output" in event["data"]:
                yield f"data: [DONE]\n\n"






from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from typing import Union

app = FastAPI()

class StreamRequest(BaseModel):
    query : Union[str, dict]
    thread_id : str

@app.post("/stream")
async def stream(request: StreamRequest):
    generator = graph_generator(request.query, request.thread_id)
    return StreamingResponse(generator, media_type="text/event-stream")


@app.get('/')
async def root():
    with open('index.html', 'r') as f:
        return HTMLResponse(f.read())
    



