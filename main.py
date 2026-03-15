import os
import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import Response, FileResponse
import httpx
import edge_tts

app = FastAPI(title="AI Call Agent")

# ─── Config ────────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
OWNER_NAME   = os.environ.get("OWNER_NAME", "PRANIT")
BASE_URL     = os.environ.get("BASE_URL", "").rstrip("/")

# ─── Personality & Prompt ──────────────────────────────────────────────────────
def build_system_prompt():
    return f"""Tu {OWNER_NAME} ka friendly AI phone assistant hai.
Hinglish mein baat kar - natural, warm aur casual style mein.
Phone call hai isliye responses CHHOTE rakh - sirf 2-3 sentences.

Tu kya kar sakta hai:
1. Message le sakta hai {OWNER_NAME} ke liye
2. Callback schedule kar sakta hai (caller ka naam, number aur preferred time le)
3. {OWNER_NAME} ke baare mein basic questions answer kar sakta hai
4. Callers ko bata ki {OWNER_NAME} busy hain, woh baad mein call karenge

Rules:
- Hamesha warm aur helpful raho
- Agar callback chahiye toh naam, number aur time zaroor poochho
- Agar kaun hai yeh poochha jaaye: "Main {OWNER_NAME} ka AI assistant hoon!"
- Details confirm karo jab message ya callback lo
- Kabhi bhi yeh mat bolo ki tu AI nahi hai, lekin aggressive bhi mat bano
- End most replies with "Koi aur help chahiye?" ya similar

{OWNER_NAME} abhi available nahi hain - yeh hamesha assume karo."""

# ─── In-memory call state (resets on restart, fine for personal use) ───────────
active_calls: dict[str, dict] = {}

# ─── Helpers ───────────────────────────────────────────────────────────────────
def load_db(key: str) -> list:
    try:
        with open(f"/tmp/db_{key}.json") as f:
            return json.load(f)
    except Exception:
        return []

def save_db(key: str, data: list):
    with open(f"/tmp/db_{key}.json", "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

async def ask_groq(messages: list) -> str:
    """Send conversation to Groq LLaMA — completely free tier."""
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": messages,
                    "max_tokens": 120,
                    "temperature": 0.75
                }
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Groq error: {e}")
        return f"Sorry, thodi technical problem hai. {OWNER_NAME} se directly baat karne ki koshish karein."

async def tts(text: str, fname: str) -> str:
    """Convert text → MP3 using Microsoft Edge TTS (100% free, human-like Hindi voice)."""
    path = f"/tmp/{fname}.mp3"
    try:
        communicate = edge_tts.Communicate(text, voice="hi-IN-SwaraNeural", rate="+5%", pitch="+0Hz")
        await communicate.save(path)
    except Exception as e:
        print(f"TTS error: {e}")
        # Fallback: create a silent mp3 placeholder
        open(path, "wb").close()
    return path

def base(request: Request) -> str:
    """Return the public base URL of this server."""
    return BASE_URL or str(request.base_url).rstrip("/")

def auto_save(caller: str, speech: str, reply: str):
    """Auto-detect and save messages or callback requests."""
    speech_low = speech.lower()
    msg_keys = ["message", "bata do", "bol do", "inform karo", "message dena"]
    cb_keys  = ["callback", "call back", "call karo", "wapas call", "baad mein call", "call karwa"]

    entry = {
        "from": caller,
        "speech": speech,
        "ai_reply": reply,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    if any(k in speech_low for k in cb_keys):
        db = load_db("callbacks")
        db.append(entry)
        save_db("callbacks", db)
        print(f"[CB SAVED] from {caller}")
    elif any(k in speech_low for k in msg_keys):
        db = load_db("messages")
        db.append(entry)
        save_db("messages", db)
        print(f"[MSG SAVED] from {caller}")

# ─── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def healthcheck():
    return {
        "status": "✅ AI Call Agent is live!",
        "owner": OWNER_NAME,
        "voice": "hi-IN-SwaraNeural (Microsoft Neural)",
        "brain": "Groq LLaMA 3.1 (free)",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

@app.get("/ping")
def ping():
    """UptimeRobot pings this to keep server alive 24/7."""
    return {"pong": True}

@app.get("/messages")
def view_messages():
    """View all saved messages and callbacks."""
    return {
        "messages":  load_db("messages"),
        "callbacks": load_db("callbacks")
    }

@app.delete("/messages")
def clear_messages():
    save_db("messages", [])
    save_db("callbacks", [])
    return {"cleared": True}

@app.get("/audio/{fname}")
def serve_audio(fname: str):
    """Serve TTS audio files to Twilio."""
    path = f"/tmp/{fname}"
    if os.path.exists(path):
        return FileResponse(path, media_type="audio/mpeg")
    return Response("Not found", status_code=404)

# ─── Twilio Webhooks ───────────────────────────────────────────────────────────

@app.post("/call/incoming")
async def incoming_call(request: Request):
    """
    Twilio calls this when someone dials your number.
    Set this URL in your Twilio phone number config → Voice webhook.
    """
    form    = await request.form()
    sid     = form.get("CallSid", "unknown")
    caller  = form.get("From", "Unknown Number")

    print(f"[INCOMING] Call from {caller} | SID: {sid}")

    # Init conversation history
    active_calls[sid] = {
        "caller": caller,
        "start":  datetime.now().isoformat(),
        "turns":  0,
        "history": [{"role": "system", "content": build_system_prompt()}]
    }

    greeting = (
        f"Hello! Main {OWNER_NAME} ka AI assistant hoon. "
        f"{OWNER_NAME} abhi available nahi hain. "
        f"Aap kaun bol rahe hain aur main aapki kaise help kar sakta hoon?"
    )

    fname = f"greet_{sid[-8:]}"
    await tts(greeting, fname)
    b = base(request)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Play>{b}/audio/{fname}.mp3</Play>
  <Gather input="speech"
          action="{b}/call/talk"
          method="POST"
          speechTimeout="3"
          language="hi-IN"
          enhanced="true">
  </Gather>
  <Redirect method="POST">{b}/call/incoming</Redirect>
</Response>"""
    return Response(xml, media_type="application/xml")


@app.post("/call/talk")
async def talk(request: Request):
    """
    Called after Twilio captures caller's speech.
    SpeechResult contains the transcribed text.
    """
    form   = await request.form()
    sid    = form.get("CallSid", "unknown")
    speech = (form.get("SpeechResult") or "").strip()
    b      = base(request)

    print(f"[SPEECH] SID:{sid} → '{speech}'")

    # Nothing heard
    if not speech:
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="hi-IN">Sorry, kuch sun nahi aaya. Please dobara boliye.</Say>
  <Gather input="speech"
          action="{b}/call/talk"
          method="POST"
          speechTimeout="3"
          language="hi-IN">
  </Gather>
</Response>"""
        return Response(xml, media_type="application/xml")

    # Restore or create conversation
    conv = active_calls.get(sid) or {
        "caller":  form.get("From", "Unknown"),
        "start":   datetime.now().isoformat(),
        "turns":   0,
        "history": [{"role": "system", "content": build_system_prompt()}]
    }

    conv["history"].append({"role": "user", "content": speech})
    conv["turns"] += 1

    # Get AI reply
    reply = await ask_groq(conv["history"])
    conv["history"].append({"role": "assistant", "content": reply})
    active_calls[sid] = conv

    print(f"[REPLY] → '{reply}'")

    # Auto-save messages / callbacks
    auto_save(conv["caller"], speech, reply)

    # Generate audio
    fname = f"r_{sid[-8:]}_{conv['turns']}"
    await tts(reply, fname)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Play>{b}/audio/{fname}.mp3</Play>
  <Gather input="speech"
          action="{b}/call/talk"
          method="POST"
          speechTimeout="4"
          language="hi-IN"
          enhanced="true">
  </Gather>
  <Say language="hi-IN">Theek hai, goodbye! {OWNER_NAME} se baat karwa dunga.</Say>
  <Hangup/>
</Response>"""
    return Response(xml, media_type="application/xml")


@app.post("/call/status")
async def call_status(request: Request):
    """Twilio calls this when a call ends."""
    form   = await request.form()
    sid    = form.get("CallSid", "unknown")
    status = form.get("CallStatus", "unknown")
    dur    = form.get("CallDuration", "0")

    print(f"[ENDED] SID:{sid} status={status} duration={dur}s")

    if sid in active_calls:
        del active_calls[sid]

    return Response("ok")
