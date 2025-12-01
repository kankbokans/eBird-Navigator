
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

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("birding_agent.log", encoding='utf-8')
    ],
    force=True
)

# Suppress known GenAI async client bug
logging.getLogger("google.genai").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# PROJECT_ROOT: directory containing this agent.py file. This makes the code
# portable (no hard-coded absolute paths).
# EBIRD_FOLDER: relative path where the MCP eBird server (Node.js project) lives.
# EBIRD_API_KEY:
# - Pulled from environment for security.
# - Fallback "YOUR_EBIRD_API_KEY" is a placeholder for local testing;

PROJECT_ROOT = Path(__file__).parent.absolute()
EBIRD_FOLDER = PROJECT_ROOT / "ebird-mcp-server"
EBIRD_API_KEY = os.getenv("EBIRD_API_KEY", "YOUR_EBIRD_API_KEY")

if not EBIRD_FOLDER.exists():
    raise FileNotFoundError(f"eBird MCP server folder not found: {EBIRD_FOLDER}")

# MCP Toolset: expose eBird MCP tools to ADK as regular tools
# -----------------------------------------------------------------------------
# McpToolset connects to an MCP server (the Node.js eBird server) via stdio.
# ADK will:
# - Discover the tools exposed by that server.
# - Wrap them as normal ADK tools that LlmAgent can call.

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
# Agent 1: city_species_locator_agent
# - Role: "backend search specialist" using Google Search tools.
# - Responsibilities:
#     * Resolve locations to lat/lon (city, state, country, landmark).
#     * Resolve species names / taxonomy basics via web search.
# - Design: Treated as a sub-agent / helper, not the main UX agent.

city_species_locator_agent = LlmAgent(
    model="gemini-2.5-flash-lite",
    name="city_species_agent",
    description="Location and species lookup using Google Search.",
    # instruction:
    #   This prompt tightly scopes the agent so the model focuses on:
    #   - Geocoding (turning user text into coordinates).
    #   - Species name / taxonomy lookups.
    #   It is intentionally procedural and precise, to improve reliability.
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
    # Note: This agent's response is primarily consumed by the root_agent
    # and ebird_agent, not directly shown to the user.
    # tools:
    #   We give this agent only the Google Search tool so its behavior remains
    #   focused: all external data comes from search, not MCP.
)

# Agent 2: ebird_agent
# - Role: "eBird data specialist" using MCP tools only.
# - Responsibilities:
#     * Given coordinates or species, call the eBird MCP tools to:
#         - list hotspots
#         - fetch recent observations
#         - query taxonomy data
#     * Optionally fall back to general info via city_species_locator_agent (by instruction).
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
    #   This agent only sees the eBird MCP tools, which keeps responsibilities
    #   clean: all heavy bird-data logic is delegated here.
    
)
#Multi-Agent System
# Agent 3: root_agent
# - Role: Main "assistant" agent.
# - Responsibilities:
#     * Interpret user questions.
#     * Decide when/how to delegate work to:
#         - city_species_locator_agent
#         - ebird_agent
#     * Compose a user-friendly final answer.
#
# - Design:
#     * Implemented as an LlmAgent with AgentTool entries for the two specialists.
#     * This makes them callable tools from the root agent's perspective.
#     * ADK web expects a global `root_agent` symbol, so this name is important.


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
    #   We wrap the two sub-agents in AgentTool so the root_agent can invoke
    #   them like tools. ADK handles passing our user/session context to them.
)
    
logger.info("✅ All 3 agents ready")

# BirdingAgentService
# - Thin service layer to:
#     * Own the InMemorySessionService (ephemeral, in-process sessions).
#     * Own a Runner configured with the root_agent.
#     * Provide an async `run_query` method usable from CLI/tests.
#
# - Design:
#     * This isolates ADK wiring from UI / CLI code.
#     * In production, you could swap InMemorySessionService with a persistent
#       implementation without changing calling code. 

class BirdingAgentService:
    def __init__(self):
        self.session_service = InMemorySessionService()
        self.root_runner = Runner(
            app_name="birding_app",
            agent=root_agent,
            session_service=self.session_service,
        # Runner is the main ADK orchestrator:
        # - Binds the root_agent to an app_name.
        # - Uses session_service to keep track of multi-turn context.
        )
    
    async def run_query(self, query: str) -> str:
        """
        Execute a single user query through the root agent.

        Implementation details:
        - Creates a fresh session for each call (stateless between runs).
        - Wraps the user query in google.genai.types.Content.
        - Streams events from Runner.run_async and accumulates the final text.
        """
        try:
            session = await self.session_service.create_session(
                state={}, app_name="birding_app", user_id="test"
            )
            # Wrap the plain text query into a GenAI Content object
            # (role=user, with a single text Part)
            content = genai_types.Content(role="user", parts=[genai_types.Part(text=query)])
                        
            response = ""
            # run_async streams intermediate and final events.
            # We accumulate only the final response text from the agent
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

# Simple programmatic test harness
# - This block runs only when executing `python agent.py` directly.
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
    # When run as a script, print quick usage hints and execute the demo queries.
    print("🎉 Birding Agent READY!")
    print("🌐 Web UI: 'adk web'  → http://127.0.0.1:8000")
    print("🧪 Tests:  'python agent.py'")
    print("-" * 50)

    asyncio.run(main())

