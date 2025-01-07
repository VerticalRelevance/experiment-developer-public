# Experiment Developer

This directory contains the code for the Experiment Developer solution.

## Directory Structure

- `app/` - Main source code containing the core components like ingestion and generation
- `scripts/` - Utility scripts for building and testing Experiment Developer ([documentation](scripts/readme.md))
- `Dockerfile` - Container definition
- `requirements.txt` - Python dependencies required by the application
- `tmp/` - Temporary directory for runtime artifacts

The two core workflows are triggered by the `main.py` file depending on the user's choice of `ingest` or `generate`. The workflows map on to the the following two files:

- `src/developer_agent.py` - Core AI code generation agent 
- `src/ingestion_agent.py` - Handles content/code preprocessing, embedding, and storage

## Configuration

Application configuration can be modified through environment variables. See the `src/config/settings.py` file for more details on available configuration options.
Prompt tuning can be done by modifying the `src/config/prompts.yaml` file.

## Scripts

The `scripts/` directory contains utility scripts for building, running, and managing the Experiment Developer solution. See the `scripts/README.md` file for more details.