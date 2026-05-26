#!/bin/bash
# Helper script to automate deployment to Hugging Face Space

# 1. Read token from argument or environment variable
HF_TOKEN="${1:-$HF_TOKEN}"

if [ -n "$HF_TOKEN" ]; then
    echo "🔑 Hugging Face token detected. Configuring authenticated remote..."
    HF_REPO_URL="https://theswatikapasiya:$HF_TOKEN@huggingface.co/spaces/theswatikapasiya/iomt-healthcare-security"
else
    echo "⚠️  No Hugging Face token provided. You will need to enter your credentials."
    HF_REPO_URL="https://huggingface.co/spaces/theswatikapasiya/iomt-healthcare-security"
fi

DEPLOY_DIR="../hf_deploy_temp"

echo "🚀 Preparing deployment to Hugging Face Space..."
echo "📦 Space Repository: https://huggingface.co/spaces/theswatikapasiya/iomt-healthcare-security"

# 1. Clean up any existing temp deployment dir
if [ -d "$DEPLOY_DIR" ]; then
    echo "🧹 Removing old temporary build directory..."
    rm -rf "$DEPLOY_DIR"
fi

# 2. Clone the Hugging Face Space repository
echo "📥 Cloning Hugging Face Space repository..."
git clone "$HF_REPO_URL" "$DEPLOY_DIR"

if [ $? -ne 0 ]; then
    echo "❌ Failed to clone the repository. Check your internet connection or space URL."
    exit 1
fi

# 3. Copy project files to the cloned directory (excluding git and virtual environments)
echo "📂 Copying project files..."
rsync -av --progress ./ "$DEPLOY_DIR/" \
    --exclude '.git/' \
    --exclude '.venv/' \
    --exclude '.venv-1/' \
    --exclude '__pycache__/' \
    --exclude 'data/raw/' \
    --exclude 'data/processed/' \
    --exclude '*.json' \
    --exclude 'hf_deploy_temp/'

# 4. Commit and push changes
cd "$DEPLOY_DIR"
echo "🔀 Preparing Git commit..."
git add .
git commit -m "Deploy IoMT Healthcare Cybersecurity & Intelligence Platform"

echo "📤 Pushing code to Hugging Face Space..."
if [ -z "$HF_TOKEN" ]; then
    echo "⚠️  You will be prompted to enter your Hugging Face username and Access Token (password)."
    echo "🔑 Create a Write Access Token at: https://huggingface.co/settings/tokens"
    echo ""
fi

git push origin main

if [ $? -eq 0 ]; then
    echo "✅ Successfully deployed to Hugging Face Space!"
    echo "🌐 Check the progress at: https://huggingface.co/spaces/theswatikapasiya/iomt-healthcare-security"
else
    echo "❌ Push failed. Please double check your Hugging Face Access Token permissions."
fi

# Return to project root
cd - > /dev/null
rm -rf "$DEPLOY_DIR"
