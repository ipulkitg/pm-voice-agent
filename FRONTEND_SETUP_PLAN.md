# React Frontend Setup Plan

## Overview
This document outlines the steps and directory structure for creating a React frontend using LiveKit CLI to connect to the existing sales agent.

## Current State
- **Agent**: Python-based voice agent (`agent.py`) deployed to LiveKit Cloud
- **Agent ID**: `CA_RzxMQHccWzsm` (from `livekit.toml`)
- **Project**: `project-1-lc548bzb` (LiveKit Cloud subdomain)
- **Agent Type**: Voice AI agent with RAG capabilities (Lenny's Newsletter/Podcast knowledge base)

## Recommended Template
**Template**: `agent-starter-react` (Next.js + TypeScript)
- **Why**: Specifically designed for voice AI agents
- **Features**: 
  - Built-in voice assistant UI components
  - Audio visualizer
  - Token generation endpoint
  - Agent state management
  - Responsive design

## Directory Structure Options

### Option 1: Monorepo (Recommended)
```
sales-agent-livekit/
├── agent/                    # Existing Python agent code
│   ├── agent.py
│   ├── setup_rag.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── livekit.toml
│
├── frontend/                 # New React frontend
│   ├── package.json
│   ├── next.config.js
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   └── api/
│   │   │       └── token/
│   │   │           └── route.ts    # Token generation endpoint
│   │   └── components/
│   │       ├── VoiceAssistant.tsx
│   │       ├── AudioVisualizer.tsx
│   │       └── ...
│   ├── .env.local            # Frontend environment variables
│   └── public/
│
├── context/                  # Shared knowledge base (existing)
│   └── all_content.md
│
└── README.md
```

### Option 2: Separate Repository
```
sales-agent-livekit/         # Existing agent repo
├── agent.py
├── setup_rag.py
└── ...

sales-agent-frontend/         # New frontend repo
├── package.json
├── src/
└── ...
```

**Recommendation**: Use **Option 1 (Monorepo)** for easier development and deployment coordination.

## Implementation Steps

### Step 1: Install LiveKit CLI (if not already installed)
```bash
# macOS
brew install livekit/tap/livekit-cli

# Or download from: https://github.com/livekit/livekit-cli/releases
```

### Step 2: Authenticate with LiveKit Cloud
```bash
# Ensure you're authenticated and project is linked
lk cloud auth
lk project list                    # Verify project is linked
lk project set-default "project-1-lc548bzb"  # Set default project
```

### Step 3: Create Frontend from Template
```bash
# Navigate to project root
cd /Users/pulkitgarg/second/sales-agent-livekit

# Create frontend from template (this will create a 'frontend' directory)
lk app create --template agent-starter-react frontend

# Follow CLI prompts:
# - Select your LiveKit Cloud project
# - The CLI will automatically configure environment variables
```

### Step 4: Review Generated Structure
The CLI will create:
- Next.js application structure
- Environment configuration
- Token generation endpoint
- Basic voice assistant UI
- Package.json with dependencies

### Step 5: Configure Agent Connection
The frontend needs to:
1. **Connect to the same LiveKit project** (already configured by CLI)
2. **Reference the agent ID** for explicit dispatch
3. **Generate tokens** with proper permissions

**Key Configuration Points**:
- `LIVEKIT_URL`: Auto-configured by CLI
- `LIVEKIT_API_KEY`: Auto-configured by CLI  
- `LIVEKIT_API_SECRET`: Auto-configured by CLI
- Agent dispatch: Use agent ID `CA_RzxMQHccWzsm` from `livekit.toml`

### Step 6: Customize Frontend (Optional)
- Update branding/UI for sales agent
- Add agent-specific features
- Customize audio visualizer
- Add transcription display
- Implement conversation history

### Step 7: Test Locally
```bash
cd frontend
npm install          # Install dependencies
npm run dev          # Start development server
```

### Step 8: Deploy Frontend
Options:
- **Vercel** (recommended for Next.js): Auto-deploy from Git
- **Netlify**: Alternative hosting
- **Self-hosted**: Docker container

## Key Integration Points

### 1. Token Generation
The frontend needs a token endpoint that:
- Generates access tokens for users
- Optionally dispatches the agent to the room
- Sets appropriate permissions (publish/subscribe audio)

**Example Token Endpoint** (`frontend/src/app/api/token/route.ts`):
```typescript
import { AccessToken } from 'livekit-server-sdk';

export async function POST(request: Request) {
  const { roomName, participantName } = await request.json();
  
  // Generate token with agent dispatch
  const token = new AccessToken(apiKey, apiSecret, {
    identity: participantName,
  });
  
  token.addGrant({
    room: roomName,
    roomJoin: true,
    canPublish: true,
    canSubscribe: true,
  });
  
  return Response.json({ token: await token.toJwt() });
}
```

### 2. Agent Dispatch
Two options:
- **Implicit**: Agent auto-joins when user connects (via agent dispatch rules)
- **Explicit**: Frontend explicitly dispatches agent using agent ID

**Explicit Dispatch** (recommended):
```typescript
// In your frontend component
const dispatchAgent = async (roomName: string) => {
  await fetch('/api/dispatch', {
    method: 'POST',
    body: JSON.stringify({
      room: roomName,
      agentId: 'CA_RzxMQHccWzsm', // Your agent ID
    }),
  });
};
```

### 3. Environment Variables
**Frontend `.env.local`** (auto-generated by CLI):
```env
NEXT_PUBLIC_LIVEKIT_URL=wss://project-1-lc548bzb.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
```

**Note**: `NEXT_PUBLIC_` prefix is required for client-side access in Next.js.

## What the LiveKit CLI Does

When you run `lk app create --template agent-starter-react frontend`:

1. ✅ **Clones template**: Downloads `agent-starter-react` from GitHub
2. ✅ **Configures environment**: Sets up `.env.local` with your LiveKit credentials
3. ✅ **Installs dependencies**: Creates `package.json` with required packages
4. ✅ **Sets up project structure**: Creates Next.js app structure
5. ✅ **Configures token endpoint**: Creates API route for token generation
6. ✅ **Sets up components**: Includes voice assistant UI components

## Next Steps After Setup

1. **Test Connection**: Verify frontend can connect to LiveKit and agent
2. **Customize UI**: Update branding, colors, layout for sales agent
3. **Add Features**:
   - Conversation history
   - Transcription display
   - Agent state indicators
   - Custom audio visualizer
4. **Deploy**: Deploy frontend to production (Vercel recommended)

## Dependencies Overview

The template will include:
- `@livekit/components-react`: React components for LiveKit
- `@livekit/components-styles`: Styles for components
- `livekit-client`: Core LiveKit SDK
- `next`: Next.js framework
- `react` & `react-dom`: React libraries

## Troubleshooting

### Agent Not Joining
- Check agent ID matches `livekit.toml`
- Verify agent is deployed and running
- Check dispatch rules in LiveKit Cloud dashboard

### Connection Issues
- Verify `LIVEKIT_URL` matches your project subdomain
- Check API keys are correct
- Ensure token has proper permissions

### Audio Issues
- Check browser microphone permissions
- Verify agent is publishing audio tracks
- Check browser console for WebRTC errors

## Resources

- [LiveKit React Components](https://docs.livekit.io/reference/components/react.md)
- [Agent Starter React Template](https://github.com/livekit-examples/agent-starter-react)
- [LiveKit Frontend Docs](https://docs.livekit.io/agents/start/frontend.md)
- [Token Generation Guide](https://docs.livekit.io/home/server/generating-tokens.md)

