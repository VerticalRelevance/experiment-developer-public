# Set the AWS Secrets Manager secret name
SECRET_NAME="dev/OpenAI/Api"

# Get the secret value from AWS Secrets Manager
SECRET_VALUE=$(aws secretsmanager get-secret-value --secret-id $SECRET_NAME --query SecretString --output text)

# Extract correct key value
OPENAI_API_KEY=$(echo $SECRET_VALUE | sed -n 's/.*"OPENAI_API_SECRET_KEY":"\([^"]*\)".*/\1/p')

# Export values
export OPENAI_API_KEY=$OPENAI_API_KEY
export OPENAI_MODEL_NAME="gpt-4o-2024-08-06"

export CHROMA_SUMMARIZE=true