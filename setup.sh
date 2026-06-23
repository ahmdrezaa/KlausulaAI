#!/bin/bash
# KlausulaAI RAG Integration - Setup Script
# This script helps you setup the complete RAG integration

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   KlausulaAI RAG Integration - Setup Helper Script       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "🔍 Checking prerequisites..."
echo ""

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✅${NC} Python 3 ($PYTHON_VERSION) found"
else
    echo -e "${RED}❌${NC} Python 3 not found. Please install Python 3.10 or later"
    exit 1
fi

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✅${NC} Node.js ($NODE_VERSION) found"
else
    echo -e "${RED}❌${NC} Node.js not found. Please install Node.js 18 or later"
    exit 1
fi

echo ""
echo "📋 SETUP STEPS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 1: Backend Setup
echo "1️⃣  BACKEND SETUP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ! -f "backend/.env" ]; then
    echo "Creating backend/.env..."
    cat > backend/.env << 'EOF'
# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_SERVICE_KEY=your_service_key_here
SUPABASE_JWT_SECRET=your_jwt_secret_here

# Frontend Configuration
FRONTEND_URL=http://localhost:3000

# Server Configuration
PORT=8000
EOF
    echo -e "${YELLOW}⚠️  ${NC} Please update backend/.env with your Supabase credentials"
    echo "   - SUPABASE_URL: From Supabase → Settings → API"
    echo "   - SUPABASE_SERVICE_KEY: Service role key"
    echo "   - SUPABASE_JWT_SECRET: JWT secret from Supabase"
else
    echo -e "${GREEN}✅${NC} backend/.env already exists"
fi

echo ""
echo "Installing backend dependencies..."
if command -v pip3 &> /dev/null; then
    cd backend
    pip3 install -r requirements.txt --quiet
    cd ..
    echo -e "${GREEN}✅${NC} Backend dependencies installed"
else
    echo -e "${RED}❌${NC} pip3 not found"
    exit 1
fi

echo ""

# Step 2: Frontend Setup  
echo "2️⃣  FRONTEND SETUP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ! -f "frontend/.env.local" ]; then
    echo "Creating frontend/.env.local..."
    cat > frontend/.env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
    echo -e "${GREEN}✅${NC} frontend/.env.local created"
else
    echo -e "${GREEN}✅${NC} frontend/.env.local already exists"
fi

echo ""
echo "Installing frontend dependencies..."
cd frontend
npm install --silent
cd ..
echo -e "${GREEN}✅${NC} Frontend dependencies installed"

echo ""

# Step 3: Database Migration
echo "3️⃣  DATABASE MIGRATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "SQL Migration file: backend/database/migrations/001_create_chat_history.sql"
echo ""
echo "To apply the migration:"
echo "1. Open Supabase Dashboard → SQL Editor"
echo "2. Copy content from: backend/database/migrations/001_create_chat_history.sql"
echo "3. Paste into SQL Editor and run"
echo ""
echo -e "${YELLOW}⚠️  ${NC} Run this before starting the services"

echo ""

# Step 4: Summary
echo "4️⃣  READY TO START"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Backend setup complete"
echo "✅ Frontend setup complete"
echo ""
echo "📝 Next steps:"
echo "   1. Update backend/.env with Supabase credentials"
echo "   2. Run database migration in Supabase"
echo "   3. Start backend:   cd backend && python -m uvicorn main:app --reload"
echo "   4. Start frontend:  cd frontend && npm run dev"
echo "   5. Open browser:    http://localhost:3000"
echo ""
echo "📚 Documentation:"
echo "   • RAG_README.md                 - Start here!"
echo "   • IMPLEMENTATION_CHECKLIST.md   - Detailed setup"
echo "   • ARCHITECTURE.md               - System design"
echo "   • TESTING_GUIDE.md              - Testing procedures"
echo ""
echo -e "${GREEN}🎉 Integration setup complete!${NC}"
echo ""
