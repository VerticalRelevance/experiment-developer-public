# Scripts Directory

This directory contains utility scripts for building, running, and testing APDeveloper.

## Available Scripts

### Build and Run
- `build_to_ecr.sh` - Builds and pushes the Docker image to Amazon ECR
- `run.sh` - Main script for running the APDeveloper container. Used by Fargate.

### Local Development
- `run_generate_local.sh` - Runs the generation service locally
- `run_ingest_local.sh` - Executes the ingestion process locally

### Configuration
- `set_claude_vars.sh` - Sets up environment variables for Claude AI integration
- `set_oai_vars.sh` - Configures OpenAI-related environment variables. Note the embedding model is limited to only OpenAI so these must always run until other embedding models are supported.

### Testing
- `test_cases/` - Directory containing generation test case configurations.
- all test cases should:
   - source base_exports.sh (internally to the script)
   - source the correct model vars (externally to the script)
   - run from the directory `docker`

## Usage Examples

1. Building and pushing to ECR:
   ```bash
   ./scripts/build_to_ecr.sh
   ```

3. Setting up AI configurations:
   ```bash
   source ./scripts/set_claude_vars.sh  # For Claude
   source ./scripts/set_oai_vars.sh     # For OpenAI
   ```

4. Local development:
   ```bash
   docker/scripts/run_ingest_local.sh
   docker/scripts/run_generate_local.sh
   ```