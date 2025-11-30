
import os
import asyncio
import logging
import sys
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

import google.genai.types as genai_types
from google.adk.sessions import InMemorySessionService
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.tools import google_search, AgentTool
from google.adk.tools.mcp_tool.mcp_toolset import (
    McpToolset,
    StdioConnectionParams,
    StdioServerParameters,
)

# --- FIXED: Unicode-safe + GenAI warning suppression ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("birding_agent.log", encoding='utf-8')
    ],
    force=True
)

# ✅ Suppress known GenAI async client bug
logging.getLogger("google.genai").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.absolute()
EBIRD_FOLDER = PROJECT_ROOT / "ebird-mcp-server"
EBIRD_API_KEY = os.getenv("EBIRD_API_KEY", "YOUR_EBIRD_API_KEY")

if not EBIRD_FOLDER.exists():
    raise FileNotFoundError(f"eBird MCP server folder not found: {EBIRD_FOLDER}")

# --- GLOBAL AGENTS (Required for adk web) ---
logger.info("Creating eBird MCP toolset...")
#Custom Tool-MCP
ebird_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="node",
            args=[str(EBIRD_FOLDER / "index.js"), "--api-key", EBIRD_API_KEY],
            cwd=str(EBIRD_FOLDER),
        ),
    ),
)

#In-Built Tool
city_species_locator_agent = LlmAgent(
    model="gemini-2.5-flash-lite",
    name="city_species_agent",
    description="Location and species lookup using Google Search.",
    instruction=(
        "You specialize in finding latitude/longitude for cities,states,countries, locations, or landmarks. "
        "Use Google Search to find coordinates for ANY location mentioned. "
        "If a state is mentioned then find the capital city of that state and provide the coordinates of the capital city."
        "If a country is mentioned then find the capital city of that country and provide the coordinates of the capital city."
        "Extract the main city/place from the query if multiple locations are mentioned."
        "You also specialize in finding information about any species, the scientific or common name, at any location,  that is asked. "
        "Use Google Search to find information about any species, broader category that is asked."
        "Extract the main species and their scientific name or common name from the query if multiple species are mentioned and then pass this information to the eBird Taxonomy tool."

    ),
    tools=[google_search],
)

ebird_agent = LlmAgent(
    model="gemini-2.5-flash-lite",
    name="ebird_agent",
    description="eBird specialist using MCP tools for hotspots and observations.",
    instruction=(
        "You are an eBird specialist. Use the eBird MCP tools to answer birding questions. "
        "If given latitude/longitude, use tools like list_hotspots or search_observations. "
        "If given a city/place, FIRST ask the city_species_locator_agent for coordinates, THEN use eBird tools. "
        "If given a general category or species/bird/common name, ask the city_species_locator_agent for common name or scientific name, THEN use eBird tools."
        "Provide concise, useful birding insights (hotspots, recent sightings, species lists, taxonomy)."
        "If you do not find any answers from the ebird tool, find the best answer by using the city_species_locator_agent to get information about the species and give some information in 4-5 lines about the species that is being asked"
    ),
    tools=[ebird_toolset],
    
)
#Multi-Agent System

# ✅ GLOBAL ROOT_AGENT - REQUIRED for adk web
root_agent = LlmAgent(
    model="gemini-2.5-flash-lite",
    name="root_agent",
    description="Professional birding assistant with auto-orchestration.",
    instruction=(
           "You are a kind, helpful and professional birding assistant. For birding/hotspot questions:\n"
        "1. If the user mentions a SPECIFIC CITY/PLACE, use the city_species_locator_agent "
           "to get lat/long, then pass those coordinates to ebird_agent.\n"
        "2. If the user mentions a SPECIFIC SPECIES/BIRD, use the city_species_locator_agent "
           "to get the common or scientific name, then pass that to ebird_agent.\n"
        "3. If the user asks about birds' broad general category or species/bird/common name, ask the city_species_locator_agent for common name or scientific name, then use eBird tools.\n"
        "4. If the user already provides lat/long OR asks general birding questions, "
           "ask city_species_locator_agent first and then consult with ebird_agent with added context.\n"
        "5. For non-birding questions, answer directly.\n\n"
        "Always explain briefly what you did and why."
        "6. Always provide answer in the form of a list of 15 most relevant bird species that can be found at the location or 10-15 hotspots asked based on the data from ebird_agent."
    ),
    tools=[AgentTool(agent=city_species_locator_agent), AgentTool(agent=ebird_agent)],
)
    
logger.info("✅ All 3 agents ready")

class BirdingAgentService:
    def __init__(self):
        self.session_service = InMemorySessionService()
        self.root_runner = Runner(
            app_name="birding_app",
            agent=root_agent,
            session_service=self.session_service,
        )
    
    async def run_query(self, query: str) -> str:
        try:
            session = await self.session_service.create_session(
                state={}, app_name="birding_app", user_id="test"
            )
            content = genai_types.Content(role="user", parts=[genai_types.Part(text=query)])
                        
            response = ""
            async for event in self.root_runner.run_async(
                session_id=session.id, user_id="test", new_message=content
            ):
                if (event.response and event.response.output and 
                    event.response.output.final and event.response.output.final.text):
                    response += event.response.output.final.text
            
            logger.info(f"✅ Response: {len(response)} chars")
            return response.strip()
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return f"Error: {str(e)}"


async def main():
    """Test programmatic execution"""
    service = BirdingAgentService()
    
    print("\n🧪 PROGRAMMATIC TESTS:")
    queries = ["Birding hotspots near Boston", "Bald eagles Seattle", "Paris birds"]
    
    for query in queries:
        print(f"\nQuery: {query}")
        print("=" * 50)
        response = await service.run_query(query)
        print(response[:600] + "..." if len(response) > 600 else response)
        await asyncio.sleep(1)

if __name__ == "__main__":
    print("🎉 Birding Agent READY!")
    print("🌐 Web UI: 'adk web'  → http://127.0.0.1:8000")
    print("🧪 Tests:  'python agent.py'")
    print("-" * 50)

    asyncio.run(main())
