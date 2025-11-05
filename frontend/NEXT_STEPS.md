# Next Steps After Cloning Template

## ✅ What's Done
- Frontend template cloned successfully
- Next.js app structure created
- Token generation endpoint created at `/app/api/connection-details/route.ts`
- Configuration file created at `app-config.ts`

## 📋 Step-by-Step Setup

### Step 1: Check Environment Variables
The CLI should have created `.env.local` automatically. Verify it exists:

```bash
cd frontend
ls -la | grep env
```

If `.env.local` exists, check it contains:
```env
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
LIVEKIT_URL=wss://project-1-lc548bzb.livekit.cloud
```

If `.env.local` doesn't exist, create it with your LiveKit credentials.

### Step 2: Configure Agent Connection
Update `app-config.ts` to connect to your agent. The agent needs to be dispatched using the agent name.

**Option A: If your agent uses explicit dispatch (has `agent_name` set in WorkerOptions)**
- Check your `agent.py` to see if `agent_name` is set in `WorkerOptions`
- If yes, use that name in `app-config.ts`

**Option B: If your agent uses automatic dispatch (default)**
- The frontend will automatically connect to your agent
- You can skip setting `agentName` in config

Update `app-config.ts`:
```typescript
export const APP_CONFIG_DEFAULTS: AppConfig = {
  // ... existing config ...
  
  // Set agentName if using explicit dispatch
  // agentName: 'your-agent-name',  // Only if agent has agent_name set
  agentName: undefined,  // Use undefined for automatic dispatch
};
```

### Step 3: Customize App Config (Optional)
Update branding and features in `app-config.ts`:
```typescript
export const APP_CONFIG_DEFAULTS: AppConfig = {
  companyName: 'Your Company',
  pageTitle: 'Sales Agent',
  pageDescription: 'Your sales assistant powered by LiveKit',
  startButtonText: 'Start conversation',
  // ... other settings
};
```

### Step 4: Install Dependencies
```bash
cd frontend
pnpm install
```

### Step 5: Start Development Server
```bash
pnpm dev
```

The app will be available at `http://localhost:3000`

### Step 6: Test the Connection
1. Open `http://localhost:3000` in your browser
2. Click "Start call" button
3. Allow microphone permissions
4. The frontend should:
   - Generate a token
   - Connect to LiveKit
   - Dispatch your agent (if configured)
   - Establish audio connection

## 🔍 Troubleshooting

### Agent Not Connecting
- Check that your agent is deployed and running
- Verify agent ID matches `livekit.toml`: `CA_RzxMQHccWzsm`
- Check LiveKit Cloud dashboard to see if agent worker is active

### Environment Variables Missing
- The CLI should have created `.env.local` automatically
- If missing, get your credentials from:
  - LiveKit Cloud dashboard → Settings → API Keys
  - Or use: `lk app env` command

### Token Generation Errors
- Verify `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, and `LIVEKIT_URL` are correct
- Check the browser console for errors
- Check Next.js server logs for token generation errors

## 📝 Important Notes

1. **Agent Dispatch**: 
   - If your agent uses **automatic dispatch** (default), it will join any new room automatically
   - If your agent uses **explicit dispatch**, you need to set `agentName` in both the agent's `WorkerOptions` and the frontend's `app-config.ts`

2. **Agent ID vs Agent Name**:
   - Agent ID (`CA_RzxMQHccWzsm`) is the deployment ID
   - Agent Name is what you set in `WorkerOptions(agent_name=...)` for explicit dispatch
   - Check your `agent.py` to see which dispatch method you're using

3. **Package Manager**: 
   - This project uses `pnpm` (not npm or yarn)
   - Make sure you have pnpm installed: `npm install -g pnpm`

## 🚀 Next Steps After Testing

Once everything works:
1. Customize the UI for your sales agent
2. Add conversation history
3. Add transcription display
4. Deploy to production (Vercel recommended for Next.js)

