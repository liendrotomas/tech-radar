"""
You are a senior Python software architect.

I want to build a scalable AI-powered "Tech Radar" system.

The system should:
- Daily ingest data from multiple sources (RSS, APIs, social media, etc.)
- Filter relevant information about emerging technologies
- Enrich the data (summaries, tags, entities)
- Store the data in a structured format (database-ready)
- Use an AI agent to identify startup opportunities based on:
    - the collected data
    - a founder profile (skills, vision, constraints)
- Generate reports and metrics (trends, clusters, insights)

Technical constraints:
- Main language: Python
- Project should be modular and scalable (multi-agent architecture)
- Configuration-driven (YAML or similar)
- Designed to run locally and later in cloud environments
- Compatible with modern Python tooling (pyproject.toml, virtual environments)

What I need from you:

1. Generate a clean and scalable project folder structure
2. Create the initial files with minimal but meaningful code:
    - main.py (entry point)
    - base agent class
    - filter agent
    - enrichment agent
    - opportunity agent
    - ingestion module (RSS example)
    - pipeline (daily pipeline)
3. Add clear comments in English explaining:
    - purpose of each module
    - how components interact
4. Use clean architecture principles (separation of concerns)
5. Include placeholders for:
    - LLM integration
    - database layer
    - configuration files
6. Keep implementation minimal but realistic (no pseudocode only)
7. Use type hints where possible
8. Make it easy to extend with new agents and skills

Output the result as a full project scaffold with file paths and code.

Do not overcomplicate, but design for future scalability.

Also:
- Use a "src/" layout if appropriate
- Include a simple CLI interface
- Use logging best practices
- Prepare the code to be used with uv package manager
"""
# Generate the project structure and initial files with minimal but meaningful code.
# Project structure:
# tech-radar/
# ├── src/
# │   ├── __init__.py
# │   ├── main.py (entry point)
# │   ├── agents/
# │   │   ├── __init__.py
# │   │   ├── base_agent.py
# │   │   ├── filter_agent.py
# │   │   ├── enrichment_agent.py
# │   │   └── opportunity_agent.py
# │   ├── ingestion/
# │   │   ├── __init__.py
# │   │   └── rss_ingestion.py
# │   ├── pipeline/
# │   │   ├── __init__.py
# │   │   └── daily_pipeline.py
# │   ├── config/
# │   │   ├── __init__.py
# │   │   └── config.yaml
# │   └── utils/
# │       ├── __init__.py
# │       └── logger.py
# ├── .gitignore
# ├── pyproject.toml
# └── README.md
