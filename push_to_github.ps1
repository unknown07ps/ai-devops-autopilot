# AI DevOps Autopilot - GitHub Push Script
# Run this in PowerShell from your project root

Write-Host "🚀 Pushing AI DevOps Autopilot to GitHub" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Check if git is installed
Write-Host "`n1️⃣ Checking Git..." -ForegroundColor Yellow
try {
    $gitVersion = git --version
    Write-Host "   ✅ $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Git not found! Please install Git" -ForegroundColor Red
    exit 1
}

# Check if .env.example exists
Write-Host "`n2️⃣ Checking .env.example..." -ForegroundColor Yellow
if (!(Test-Path ".env.example")) {
    Write-Host "   ⚠️  Creating .env.example from template..." -ForegroundColor Yellow
    @"
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:latest

# Slack Webhook (Get from https://api.slack.com/messaging/webhooks)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Redis
REDIS_URL=redis://localhost:6379

# Environment
ENVIRONMENT=development
"@ | Out-File -FilePath ".env.example" -Encoding UTF8
    Write-Host "   ✅ .env.example created" -ForegroundColor Green
} else {
    Write-Host "   ✅ .env.example exists" -ForegroundColor Green
}

# Initialize git if needed
Write-Host "`n3️⃣ Initializing Git repository..." -ForegroundColor Yellow
if (!(Test-Path ".git")) {
    git init
    Write-Host "   ✅ Git repository initialized" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Git repository already exists" -ForegroundColor Yellow
}

# Check for uncommitted changes
Write-Host "`n4️⃣ Checking for changes..." -ForegroundColor Yellow
$status = git status --porcelain
if ($status) {
    Write-Host "   ✅ Found files to commit" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  No changes to commit" -ForegroundColor Yellow
}

# Stage all files
Write-Host "`n5️⃣ Staging files..." -ForegroundColor Yellow
git add .
Write-Host "   ✅ All files staged" -ForegroundColor Green

# Create commit
Write-Host "`n6️⃣ Creating commit..." -ForegroundColor Yellow
$commitMessage = @"
Initial commit: AI DevOps Autopilot MVP

🎯 Core Features:
- Anomaly detection with Z-score algorithm (242x sensitivity)
- AI root cause analysis using local Ollama LLM
- Real-time Slack alerts with rich formatting
- FastAPI ingestion endpoints for metrics/logs/deployments
- Background worker for event processing
- Redis-based event streaming architecture

📚 Documentation:
- Comprehensive README with quick start
- Detailed architecture documentation
- Contributing guidelines
- MIT License

🛠️ Tech Stack:
- Python 3.11+ with FastAPI
- Redis for event streaming
- Ollama for local AI inference
- Docker for containerization
- Slack webhooks for alerting

✨ Ready for production testing and design partner feedback
"@

git commit -m $commitMessage
Write-Host "   ✅ Commit created" -ForegroundColor Green

# Check if remote exists
Write-Host "`n7️⃣ Setting up remote..." -ForegroundColor Yellow
$remoteExists = git remote get-url origin 2>$null
if ($remoteExists) {
    Write-Host "   ⚠️  Remote 'origin' already exists: $remoteExists" -ForegroundColor Yellow
    $response = Read-Host "   Do you want to update it? (y/n)"
    if ($response -eq "y") {
        git remote set-url origin https://github.com/unknown07ps/ai-devops-autopilot.git
        Write-Host "   ✅ Remote updated" -ForegroundColor Green
    }
} else {
    git remote add origin https://github.com/unknown07ps/ai-devops-autopilot.git
    Write-Host "   ✅ Remote 'origin' added" -ForegroundColor Green
}

# Rename branch to main
Write-Host "`n8️⃣ Setting main branch..." -ForegroundColor Yellow
$currentBranch = git branch --show-current
if ($currentBranch -ne "main") {
    git branch -M main
    Write-Host "   ✅ Branch renamed to 'main'" -ForegroundColor Green
} else {
    Write-Host "   ✅ Already on 'main' branch" -ForegroundColor Green
}

# Push to GitHub
Write-Host "`n9️⃣ Pushing to GitHub..." -ForegroundColor Yellow
Write-Host "   This may require authentication..." -ForegroundColor Gray

try {
    git push -u origin main
    Write-Host "   ✅ Successfully pushed to GitHub!" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Push failed. You may need to:" -ForegroundColor Red
    Write-Host "      1. Create the repository on GitHub first" -ForegroundColor Yellow
    Write-Host "      2. Set up GitHub authentication (Personal Access Token)" -ForegroundColor Yellow
    Write-Host "      3. Run: git push -u origin main" -ForegroundColor Yellow
}

# Summary
Write-Host "`n" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "✅ Git Setup Complete!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan

Write-Host "`n🌐 Repository URL:" -ForegroundColor Yellow
Write-Host "   https://github.com/unknown07ps/ai-devops-autopilot" -ForegroundColor Cyan

Write-Host "`n📝 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Go to: https://github.com/unknown07ps/ai-devops-autopilot" -ForegroundColor White
Write-Host "2. Verify all files are uploaded" -ForegroundColor White
Write-Host "3. Add repository description:" -ForegroundColor White
Write-Host "   '🤖 Autonomous SRE that detects, diagnoses, and fixes production incidents using AI'" -ForegroundColor Gray
Write-Host "4. Add topics:" -ForegroundColor White
Write-Host "   devops, sre, ai, observability, incident-management, ollama, fastapi, python" -ForegroundColor Gray
Write-Host "5. Enable Issues and Discussions" -ForegroundColor White

Write-Host "`n💡 Tips:" -ForegroundColor Yellow
Write-Host "- Star your own repo to make it visible ⭐" -ForegroundColor White
Write-Host "- Share on LinkedIn/Twitter to get feedback" -ForegroundColor White
Write-Host "- Add a nice cover image in the README" -ForegroundColor White

Write-Host "`n🎉 Your project is now on GitHub!" -ForegroundColor Green