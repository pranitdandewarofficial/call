# 🤖 AI Calling Agent — Personal Phone Assistant
**Hinglish • Human-like Voice • Free • 24/7**

---

## What This Does
- Picks up calls to YOUR number automatically
- Speaks in natural Hinglish (Hindi + English)
- Takes messages from callers
- Schedules callback requests
- Answers questions about you
- Runs 24/7 on free cloud hosting

**Monthly cost: ~₹0 for 3–4 months, then ~₹80/month (Twilio number only)**

---

## Tech Stack (All Free)
| Component | Service | Cost |
|---|---|---|
| Phone number | Twilio | $15 free trial |
| AI brain | Groq (LLaMA 3.1) | Free forever |
| Voice (TTS) | Microsoft Edge Neural | Free forever |
| STT | Twilio built-in | From trial credits |
| Hosting | Render | Free tier |

---

## Step-by-Step Setup

### Step 1 — Get Groq API Key (5 min)
1. Go to https://console.groq.com
2. Sign up (no credit card needed)
3. Click "API Keys" → "Create API Key"
4. Copy the key that starts with `gsk_...`

---

### Step 2 — Deploy to Render (10 min)

1. **Upload code to GitHub**
   - Create a new repo at github.com
   - Upload all these files: `main.py`, `requirements.txt`, `render.yaml`

2. **Deploy on Render**
   - Go to https://render.com → Sign up (free)
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Render auto-detects settings from `render.yaml`

3. **Set Environment Variables** in Render Dashboard:
   ```
   GROQ_API_KEY = gsk_your_key_here
   OWNER_NAME   = YourName        (e.g. Rahul, Priya, etc.)
   BASE_URL     = (leave blank for now, fill after first deploy)
   ```

4. **First Deploy** → Wait ~2 min → Copy your URL
   - It looks like: `https://ai-call-agent-xxxx.onrender.com`
   - Test it: open the URL in browser, you should see a green status message

5. **Update BASE_URL** in Render env vars with your URL, then click "Manual Deploy"

---

### Step 3 — Get Twilio Number (10 min)

1. Sign up at https://twilio.com (free $15 credit)
2. Go to **Console → Phone Numbers → Buy a Number**
3. Buy any number (costs ~$1/month from your free credit)
4. Click on your number → **Voice Configuration**
5. Set **"A call comes in"** → **Webhook** → Paste:
   ```
   https://your-app-name.onrender.com/call/incoming
   ```
   Method: `HTTP POST`
6. Set **"Call Status Changes"** webhook:
   ```
   https://your-app-name.onrender.com/call/status
   ```
7. Click **Save**

---

### Step 4 — Keep It Awake 24/7 (5 min)

Render's free tier sleeps after 15 min of inactivity. Fix this for free:

1. Sign up at https://uptimerobot.com (free)
2. "Add New Monitor" → HTTP(s)
3. URL: `https://your-app-name.onrender.com/ping`
4. Interval: **5 minutes**
5. Done! Your server never sleeps.

---

### Step 5 — Test It!
Call your Twilio number. The AI will:
- Greet the caller in Hinglish
- Have a full conversation
- Take messages or schedule callbacks

---

## View Messages & Callbacks
Open in browser:
```
https://your-app-name.onrender.com/messages
```

---

## Customize Your AI

Edit the `build_system_prompt()` function in `main.py` to change:
- Your name and availability info
- What topics the AI can answer
- Tone and style

Example — add your info:
```python
# Inside build_system_prompt(), add:
return f"""...
{OWNER_NAME} ke baare mein:
- Software engineer hain, Pune mein rehte hain
- Working hours: 10am-7pm
- Best time to call: evenings after 7pm
..."""
```

---

## Voices Available (Free)
Change `voice=` in the `tts()` function:

| Voice | Style |
|---|---|
| `hi-IN-SwaraNeural` | Female, warm (default) |
| `hi-IN-MadhurNeural` | Male, professional |
| `en-IN-NeerjaNeural` | Female, Indian English |
| `en-IN-PrabhatNeural` | Male, Indian English |

---

## Troubleshooting

**Call connects but no audio?**
→ Check `BASE_URL` env var is set correctly (no trailing slash)

**AI responds in English only?**
→ The model sometimes switches. Add "ALWAYS reply in Hinglish only" to the system prompt

**Render goes to sleep?**
→ Set up UptimeRobot (Step 4)

**Twilio error 11200?**
→ Your webhook URL is wrong — double-check it in Twilio console

---

## Files
```
ai-call-agent/
├── main.py           ← All the code (FastAPI app)
├── requirements.txt  ← Python packages
├── render.yaml       ← Render deployment config
├── .env.example      ← Environment variables template
└── README.md         ← This file
```
