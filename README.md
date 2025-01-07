# Experiment Developer

Experiment Developer (formerly AP Developer) is an AI-powered solution that generates code for resiliency and chaos testing. From three inputs, it generates python code that can serve as actions and probes in a ChaosToolkit experiment.

## Project Structure

The project is organized into three main directories:

### 1. Docker Source Code (`/docker`)
Contains the core backend services:
- Python code for content ingestion and code generation
- Docker configuration and containarization
- Utility scripts for building, running, and testing the solution

See [`docker/README.md`](docker/README.md) for more details

### 2. Infrastructure (`/cdk`)
AWS CDK infrastructure code for deploying and managing the solution:
- Cloud infrastructure as code
- Deployment configurations

### 3. React UI (`/react-ui`)
Sample web interface for interacting with the Experiment Developer solution:
- User interface for code generation
- Simple three input form

## Getting Started

1. Set up the development environment:
   - Configure AWS credentials and ensure secrets manager secrets are present (for OpenAI api key)
   - Install Docker
   - Set up Node.js for the React UI
   - Set up python virtual environment and install requirements

2. Example local executions:
   
   Run ingest
   ```bash
   sh docker/scripts/run_ingest_local.sh
   ```
   
   Run generate 
   ```bash
   sh docker/scripts/run_generate_local.sh
   ```
   See [`docker/README.md`](docker/README.md) for more details

3. Deploy to AWS:
   - Ensure context variables are updated
   - Ensure required secrets manager secrets exist
   - Deploy infrastructure
   - Push Docker images to ECR
   - Update allowed IP addresses API Gateway resource policy via cdk.json or console
   - Invoke via `cdk\lambda\testing\invoke.py` or `react-ui`, local deployment
   
   See [`cdk/README.md`](cdk/README.md) for more details

4. Start the React UI:
   Export API GW invoke url
   ```bash
   export REACT_APP_API_URL="your_url" 
   ```
   
   ```bash
   cd react-ui
   npm start
   ```

   Ensure you install dependencies if first time:
   ```bash
   npm install
   ```
   See [`react-ui/README.md`](react-ui/README.md) for more details