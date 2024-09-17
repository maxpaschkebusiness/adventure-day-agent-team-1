#!/bin/bash

# Set the API endpoint URL
API_URL="http://localhost:8000/ask"
# API_URL="https://phase2.orangeground-87613208.swedencentral.azurecontainerapps.io/ask"

# Set the question you want to ask
QUESTION="Which country does 'Hobbiton: The Heist of the Silver Dragon' take place in?"

# Make the API request
RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" -d "{\"question\": \"$QUESTION\", \"type\": \"estimation\"}" $API_URL)

# Print the response
echo $RESPONSE