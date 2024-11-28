from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import httpx
import os
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BPMN_SYNTAX_DOC = """You are a BPMN XML generator. Generate valid BPMN 2.0 XML that can be rendered by bpmn-js.
The XML should include:
- Proper BPMN 2.0 namespace declarations
- Process elements with proper IDs
- Start and end events
- Tasks and sequence flows
- Gateways when needed
- Proper positioning of elements using x,y coordinates

Example structure:
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="false">
    <!-- Process elements go here -->
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <!-- Diagram elements go here -->
  </bpmndi:BPMNDiagram>
</bpmn:definitions>"""

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class Prompt(BaseModel):
    prompt: str

@app.get("/")
def read_root():
    return FileResponse("index.html")

@app.post("/generate/")
async def generate_bpmn(prompt: Prompt):
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama3-8b-8192",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a BPMN XML generator that creates valid BPMN 2.0 XML diagrams.\n\n" + BPMN_SYNTAX_DOC
                },
                {
                    "role": "user",
                    "content": "Generate a BPMN 2.0 XML diagram for the following scenario:\n\n" + prompt.prompt
                }
            ],
            "temperature": 0,
            "top_p": 1,
            "stream": False
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Groq API error: {response.text}"
                )

            completion_data = response.json()
            bpmn_xml = completion_data['choices'][0]['message']['content']
            
            # Extract just the XML content (in case there's any additional text)
            xml_start = bpmn_xml.find('<?xml')
            xml_end = bpmn_xml.find('</bpmn:definitions>') + len('</bpmn:definitions>')
            if xml_start >= 0 and xml_end >= 0:
                bpmn_xml = bpmn_xml[xml_start:xml_end]
            
            return {
                "bpmnXML": bpmn_xml
            }
                
    except Exception as e:
        print(f"Unexpected error: {str(e)}")  # Debug print
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )
