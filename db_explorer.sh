# Bash file for running the simple example
echo "Running visualization..."
uv run streamlit run sqlite_explorer.py -- --db outputs/tech_radar.db
