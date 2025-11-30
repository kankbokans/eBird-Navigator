# eBird Navigator
Multi-agent birding assistant that automatically finds birding hotspots, recent observations, and top species lists for any location worldwide using Google ADK, Gemini 2.5, Google Search, and eBird MCP tools.

🎯 Features
Feature	Description
🗺️ Auto Location	"Birding near Boston" → Finds lat/lon automatically
📱 Real-time eBird	Hotspots, recent observations via MCP server
🔍 Multi-agent	root_agent → city_agent → ebird_agent
📊 Top 15 Lists	Ranked species by location + count
🌍 Worldwide	Works for any city/country (auto capital lookup)

🎬 Demo Flow
text
User: "Birding hotspots near Seattle"
↓
root_agent → city_agent (Google Search)
↓ "Seattle: lat 47.6062, lon -122.3321"
↓
root_agent → ebird_agent (eBird MCP)
↓ list_hotspots(47.6062, -122.3321)
↓
"1. American Crow - Discovery Park (89)
 2. Glaucous-winged Gull - Alki Beach (67)
 3. Black-capped Chickadee - Green Lake (54)..."

## Available Tools

### ebird_get_recent_observations

Get recent bird observations in a region or location.

**Parameters:**
- `regionCode` (required): Region code (e.g., US, US-NY, L123456)
- `back`: Number of days back to look for observations (default: 14)
- `maxResults`: Maximum number of results to return (default: 100)
- `includeProvisional`: Include provisional observations (default: true)
- `hotspot`: Only include observations from hotspots (default: false)
- `detail`: Detail level of results ('simple' or 'full', default: 'simple')

### ebird_get_recent_observations_for_species

Get recent observations of a specific bird species in a region.

**Parameters:**
- `regionCode` (required): Region code (e.g., US, US-NY, L123456)
- `speciesCode` (required): eBird species code (e.g., amecro for American Crow)
- `back`: Number of days back to look for observations (default: 14)
- `maxResults`: Maximum number of results to return (default: 100)
- `includeProvisional`: Include provisional observations (default: true)
- `hotspot`: Only include observations from hotspots (default: false)

### ebird_get_notable_observations

Get notable bird observations in a region.

**Parameters:**
- `regionCode` (required): Region code (e.g., US, US-NY, L123456)
- `back`: Number of days back to look for observations (default: 14)
- `maxResults`: Maximum number of results to return (default: 100)
- `detail`: Detail level of results ('simple' or 'full', default: 'simple')

### ebird_get_nearby_observations

Get recent bird observations near a location.

**Parameters:**
- `lat` (required): Latitude coordinate
- `lng` (required): Longitude coordinate
- `dist`: Distance in kilometers from lat/lng point (default: 25)
- `back`: Number of days back to look for observations (default: 14)
- `maxResults`: Maximum number of results to return (default: 100)
- `includeProvisional`: Include provisional observations (default: true)
- `hotspot`: Only include observations from hotspots (default: false)
- `detail`: Detail level of results ('simple' or 'full', default: 'simple')

### ebird_get_nearby_notable_observations

Get notable bird observations near a location.

**Parameters:**
- `lat` (required): Latitude coordinate
- `lng` (required): Longitude coordinate
- `dist`: Distance in kilometers from lat/lng point (default: 25)
- `back`: Number of days back to look for observations (default: 14)
- `maxResults`: Maximum number of results to return (default: 100)
- `detail`: Detail level of results ('simple' or 'full', default: 'simple')

### ebird_get_nearby_observations_for_species

Get recent observations of a specific bird species near a location.

**Parameters:**
- `lat` (required): Latitude coordinate
- `lng` (required): Longitude coordinate
- `speciesCode` (required): eBird species code (e.g., amecro for American Crow)
- `dist`: Distance in kilometers from lat/lng point (default: 25)
- `back`: Number of days back to look for observations (default: 14)
- `maxResults`: Maximum number of results to return (default: 100)
- `includeProvisional`: Include provisional observations (default: true)

### ebird_get_hotspots

Get birding hotspots in a region.

**Parameters:**
- `regionCode` (required): Region code (e.g., US, US-NY)
- `back`: Number of days back to look for hotspot activity (default: 14)
- `includeProvisional`: Include provisional observations (default: true)

### ebird_get_nearby_hotspots

Get birding hotspots near a location.

**Parameters:**
- `lat` (required): Latitude coordinate
- `lng` (required): Longitude coordinate
- `dist`: Distance in kilometers from lat/lng point (default: 25)
- `back`: Number of days back to look for hotspot activity (default: 14)
- `includeProvisional`: Include provisional observations (default: true)

### ebird_get_taxonomy

Get eBird taxonomy information.

**Parameters:**
- `locale`: Language for common names (default: 'en')
- `cat`: Taxonomic category to filter by (default: 'species')
- `fmt`: Response format (default: 'json')

### ebird_get_taxonomy_forms

Get eBird taxonomy forms for a specific species.

**Parameters:**
- `speciesCode` (required): eBird species code

 🚀 Quick Start
Prerequisites
powershell
# 1. Python 3.10+ + Node.js 18+
# 2. Google AI Studio API key (auto-configured)

# 3. Clone & Install
git clone https://github.com/YOUR_USERNAME/ebird-birding-agent.git
cd ebird-birding-agent/proj_adk_agent
pip install -r requirements.txt  # or pip install google-adk

Test Queries
text
• "Birding hotspots near Boston MA"
• "Bald eagles near Seattle WA" 
• "What birds in Paris France?"
• "Recent observations NYC"
🏗️ Architecture
text
root_agent (Gemini 2.5)
├── city_agent (Google Search)
│   └── Finds: lat/lon, species taxonomy
└── ebird_agent (eBird MCP)
    └── Tools: list_hotspots(), search_observations()
Agent Flow:

text
1. User mentions CITY → city_agent → lat/lon
2. ebird_agent calls MCP: list_hotspots(lat,lon)
3. root_agent formats top 15 species list

📁 Directory Structure
text
proj_adk_agent/
├── agent.py              # ✅ root_agent (ADK web entrypoint)
├── ebird-mcp-server/     # Node.js MCP server
│   ├── index.js          # eBird API tools
│   ├── package.json
│   └── tools.json        # MCP tool definitions
├── birding_agent.log     # Production logs
└── requirements.txt      # Python deps

🔧 Configuration
bash
# .env (optional)
EBIRD_API_KEY=YOUR_API_KEY
GOOGLE_GENAI_API_KEY=your-key  # Auto-detected

MCP Server: Custom Node.js server exposing eBird API as ADK tools

📊 Example Output
text
**Top 15 Birds Near Boston (Nov 2025)**

1. Canada Goose - Boston Common (125 obs)
2. Mallard - Charles River (98 obs)  
3. Red-winged Blackbird - Fenway Park (67 obs)
4. American Crow - Emerald Necklace (54 obs)
5. Black-capped Chickadee - Arnold Arboretum (49 obs)
...
**Birding Hotspots in Alaska(Nov 2025)**
I've identified Juneau as the capital of Alaska and found its coordinates. Then, I used those coordinates to find 15 birding hotspots in that area. Here is a list of those hotspots:

Auke Bay
Auke Bay--Statter Harbor
Auke Nu Cove
Auke Recreation Area--Pt. Louisa
Brotherhood Bridge Trail
Gold Creek Delta
Kingfisher Pond
Mendenhall Lake-Campgrnd & Trails
Mendenhall Wetlands SGR--Airport Dike Trail
Mendenhall Wetlands SGR--Fish Creek Delta
Mendenhall Wetlands SGR--W of river
Outer Point Trail
Perseverance Trail & Gold Creek Basin
Point Lena & Ted Stevens Marine Research Institute
Rainforest Trail (Douglas Island)

📄 License
Apache 2.0 © 2025 - Built with ❤️ for birders worldwide

🙌 Acknowledgments
Google ADK - Multi-agent framework

eBird API - World birding data

Gemini 2.5 - Reasoning + orchestration

MCP Protocol - Tool calling standard

- [eBird](https://ebird.org/) for providing the API
- [Cornell Lab of Ornithology](https://www.birds.cornell.edu/) for their work on bird conservation
- [Model Context Protocol](https://modelcontextprotocol.io/) for the API integration framework
- https://github.com/moonbirdai/ebird-mcp-server

⭐ Star if you love birding + AI!
🐦 Happy birding! 🔭✨

Built by birders, for birders. Find your next life bird! 🦅
