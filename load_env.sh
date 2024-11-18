#!/bin/bash

# Check if Conda environment is activated
if [ -z "$CONDA_PREFIX" ]; then
  echo "Please activate your Conda environment before running this script."
  exit 1
fi

# Load each variable from the .env file into the Conda environment
while read -r line || [[ -n "$line" ]]; do
  if [[ ! "$line" =~ ^# && -n "$line" ]]; then
    key=$(echo "$line" | cut -d '=' -f 1)
    value=$(echo "$line" | cut -d '=' -f 2-)
    conda env config vars set "$key"="$value"
  fi
done < .env

# Inform user to restart environment
echo "Environment variables set. Please deactivate and reactivate your Conda environment to apply changes."