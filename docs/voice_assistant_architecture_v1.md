# Real-Time Voice Assistant — Frozen Architecture v1.0

Status: **LOCKED**. Reviewed and converged across two independent passes — no unresolved disagreements on architecture, only wording clarity. No further design rounds. Next step is implementation.

---

## 1. What this system actually is

Not "a voice bot." A **single-process, real-time, event-driven conversational pipeline** with a first-class failure-handling path. One user, one session, low latency, offline-first.

Deliberately excluded (would be over-engineering for this scope): message brokers, distributed event bus, microservices, dependency-injection frameworks, multi-user session management. This runs in one Python process using `asyncio`. Modularity comes from clean interfaces (ABCs) and an **event-driven orchestrator implemented with `asyncio`** — a real dispatcher reacting to real events (`SpeechEnded`, `LLMCompleted`, `PlaybackFinished`, etc.), just without external broker infrastructure. Event-driven, single process — not "event-driven in spirit."

**Governing principle**: optimize for measurable latency, responsiveness, and robustness over maximum model quality. This is why every model choice below defaults to small and fast rather than large and impressive — it explains itself in the report instead of looking like a compute constraint you settled for.

---

## 2. Final architecture

```
                              USER
                               │
                               ▼
                    ┌─────────────────────┐
                    │   AUDIO INPUT       │
                    │  Mic → Buffer → VAD │
                    └──────────┬──────────┘
                               │ SpeechEnded
                               ▼
                    ┌─────────────────────┐
                    │  SPEECH-TO-TEXT     │
                    │  Streaming ASR      │
                    └──────────┬──────────┘
                               │ TranscriptReady(text)
                               ▼
                 ┌───────────────────────────────┐
                 │      ORCHESTRATOR             │
                 │  (state machine + dispatcher)  │
                 │  Idle→Listening→Thinking→      │
                 │  Speaking→Idle | Interrupted   │
                 └───┬───────────────────────┬────┘
                     │                       │
                     ▼                       ▼
          ┌──────────────────────┐  ┌──────────────────────┐
          │ CONVERSATION MANAGER │  │  LATENCY WATCHDOG     │
          │ history + prompt     │  │  timer from SpeechEnded│
          └──────────┬───────────┘  │  → triggers Fallback  │
                    │              └──────────┬─────────────┘
                    ▼                         │
          ┌─────────────────┐                 │
          │   LLM ENGINE     │                 │
          │ local / online   │◄────────────────┘ (races against)
          │ streaming tokens │
          └────────┬─────────┘
                    │ ResponseChunk / ResponseComplete
                    ▼
          ┌─────────────────────┐       ┌───────────────────────┐
          │  RESPONSE MANAGER    │       │  FALLBACK MANAGER      │
          │  validate + format   │       │  cached filler audio   │
          └──────────┬────────────┘      │  plays if watchdog fires│
                     │                    └──────────┬──────────────┘
                     └───────────────┬────────────────┘
                                     ▼
                          ┌─────────────────────┐
                          │  TEXT-TO-SPEECH      │
                          │  streaming synthesis │
                          └──────────┬───────────┘
                                     │ AudioChunkReady
                                     ▼
                          ┌─────────────────────┐
                          │  PLAYBACK MANAGER    │
                          │  interruptible output│
                          └──────────┬───────────┘
                                     │ PlaybackFinished
                                     ▼
                              back to Orchestrator → Idle

     Barge-in path: VAD detects new speech WHILE Playback is active
     → Orchestrator fires Interrupted → Playback Manager cuts audio
     → back to Listening immediately (not queued behind old response)
```

Cross-cutting, used by everything, owned by nothing: **Logger, Config, Metrics/Latency Recorder, Error Handler.** These are plain utility modules imported where needed — not "layers."

---

## 3. Why an orchestrator, not direct calls

`STT` never calls `LLM` directly. Every module publishes a small event; the Orchestrator (a state machine, not a class hierarchy) reacts. Reasons this earns its complexity here — unlike a full event bus:

- Barge-in requires cancelling an in-flight LLM/TTS call from an unrelated input path (new speech). Direct call chains can't express "abort what you're doing," a state machine can.
- The fallback watchdog needs to race against the LLM call and win independently. That's naturally a state-machine concern.
- It costs you one file (`orchestrator.py`, an `asyncio.Queue` + a dict-based event dispatch, ~150 lines). Not a framework.

---

## 4. State machine (frozen)

```
INIT → IDLE → LISTENING → RECOGNIZING → THINKING → SPEAKING → IDLE
                   ▲                        │
                   └────── INTERRUPTED ◄─────┘  (barge-in)

THINKING → FALLBACK → THINKING   (watchdog fires, real answer still coming)
any state → ERROR_RECOVERY → IDLE   (never crash, never silently die)
```

---

## 5. Event list (frozen — this is your interface contract)

```
SystemStarted, ListeningStarted, SpeechStarted, SpeechEnded,
TranscriptReady, TranscriptRejected(low confidence),
PromptBuilt, LLMFirstTokenReceived, LLMCompleted, LLMFailed,
WatchdogTimeout, FallbackAudioStarted, FallbackAudioFinished,
ResponseValidated, TTSFirstChunkReady, PlaybackStarted,
UserInterrupted, PlaybackFinished, ErrorCaught
```

Log every one of these with a timestamp. This log IS your latency measurement system — don't build a separate one.

---

## 6. Latency budget (frozen — measure against this, log actuals)

| Stage | Offline target | Online fallback target |
|---|---|---|
| VAD end-of-speech | ≤150ms | ≤150ms |
| STT (streaming, first-partial) | ≤300ms | ≤500ms |
| Prompt build | ≤20ms | ≤20ms |
| LLM time-to-first-token | ≤400ms | ≤800ms |
| LLM full first sentence | ≤600ms | ≤1000ms |
| TTS time-to-first-audio | ≤250ms | ≤500ms |
| **Total to first audio out** | **~1.3–1.6s** | **~2.0–3.0s** |
| Watchdog fallback trigger | fires at 900ms if no LLM token yet | same |

If total exceeds 2s reliably offline, the fix order is: smaller LLM → shorter max response length → smaller STT model. Don't touch TTS last — it's usually not the bottleneck.

---

## 7. Fallback logic (the part most submissions get wrong — implement exactly this)

1. Watchdog timer starts at `SpeechEnded`.
2. If `LLMFirstTokenReceived` fires before ~900ms → cancel watchdog, proceed normally.
3. If watchdog fires first → play one of 3–5 **pre-synthesized** (not live-generated) filler clips ("let me think about that," "good question, one sec," "mm, working on it") while the LLM call continues in the background.
4. When the LLM completes, interrupt the filler cleanly at the next natural pause and speak the real answer — don't let filler and real answer overlap.
5. If the LLM call fails outright → speak a conversational recovery line ("having a little trouble with that, can you say it again?"), return to `LISTENING`. Never a raw error string, never dead air, never silently close the session.
6. Rotate fillers so it doesn't sound robotic on repeated triggers.

---

## 8. Module responsibility table (frozen — one file per row)

| Module | Responsibility | Must NOT do |
|---|---|---|
| `audio_input.py` | Mic capture, buffering, VAD | Transcription |
| `stt.py` | Audio → text, streaming | Prompt building |
| `orchestrator.py` | State machine, event dispatch | Any AI inference |
| `conversation_manager.py` | History, prompt construction | Talking to the LLM |
| `llm_engine.py` | Call local/online model, stream tokens | Formatting output |
| `watchdog.py` | Timer, fires `WatchdogTimeout` | Playing audio |
| `fallback_manager.py` | Owns filler clips, plays on timeout | Generating real responses |
| `response_manager.py` | Validate/format LLM output | Synthesis |
| `tts.py` | Text → audio, streaming | Playback |
| `playback_manager.py` | Plays audio, supports interrupt | Synthesis |
| `logger.py` / `metrics.py` | Structured logs, latency stats | Business logic |
| `config.py` | Load settings | Everything else |

---

## 9. Tech stack — final decision (offline-first)

| Component | Choice | Why |
|---|---|---|
| VAD | Silero VAD (ONNX) | ~1ms/chunk, CPU-only, no dependency issues |
| STT | `faster-whisper`, `small`/`distil-small.en` | CTranslate2 backend, actually built for streaming latency |
| LLM | Llama-3.2-3B-Instruct or Qwen2.5-3B-Instruct, served via **Ollama** | Small on purpose — latency-bound, not quality-bound. Ollama standardized for setup simplicity, easier model swapping, and cleaner documentation for a demo/report. Switch to raw `llama.cpp` only if benchmarking shows a real latency win on your hardware — note that as a measured decision, not a default |
| TTS | Piper | Purpose-built for low-latency streaming synthesis on CPU |
| Orchestration | Python `asyncio` + WebSocket (duplex) | Full-duplex needed for barge-in detection during playback |
| Online fallback (only if hardware can't run offline) | Groq (LLM) + Deepgram Aura or ElevenLabs streaming (TTS) | Sub-second TTFT, genuinely built for streaming |

State explicitly in your report *why* you picked online over offline if you do — "no GPU available" is a valid, gradable justification; no justification reads as "didn't attempt offline."

---

## 10. Implementation roadmap (day-by-day, buildable — not aspirational)

| Phase | Deliverable |
|---|---|
| 1 | Repo skeleton + interfaces (ABCs) for each module, config loading, logging |
| 2 | Audio input + VAD working standalone (prove you can capture and detect speech) |
| 3 | STT wired in, streaming partial transcripts to console |
| 4 | Orchestrator state machine + event dispatcher, no AI yet — just state transitions logged |
| 5 | LLM wired in, streaming tokens, context manager holding history |
| 6 | Watchdog + fallback manager, pre-synthesized filler clips |
| 7 | TTS + playback manager, streaming synthesis, interruptible |
| 8 | Barge-in: VAD-during-playback → interrupt → back to listening |
| 9 | End-to-end latency logging, measure against budget table, tune |
| 10 | Error recovery paths, stress test (rapid interrupts, garbled speech, LLM timeout forced) |
| 11 | Demo recording, README, architecture doc, AI-usage disclosure |
| 12 | Upload to Drive, permission-test every link logged out, PDF assembly, final submission |

Do not start Phase 2 before Phase 1's interfaces are actually defined on paper — that's the one piece of upfront design worth doing before code. Everything past that, build first, refine second.

---

## 11. Proposed repo structure

```
voice-assistant/
├── config/
│   └── settings.yaml
├── src/
│   ├── audio_input.py
│   ├── vad.py
│   ├── stt.py
│   ├── orchestrator.py
│   ├── conversation_manager.py
│   ├── llm_engine.py
│   ├── watchdog.py
│   ├── fallback_manager.py
│   ├── response_manager.py
│   ├── tts.py
│   ├── playback_manager.py
│   ├── logger.py
│   └── metrics.py
├── assets/
│   └── fallback_clips/        # pre-synthesized filler audio
├── tests/
├── logs/                       # latency + event logs land here
├── docs/
│   ├── architecture.md         # this file, or a diagram export
│   └── ai_usage_disclosure.md
├── demo/                       # recorded conversation + fallback trigger
├── requirements.txt
└── README.md
```

---

## 12. Skills required (complete)

**Python core**: OOP, ABCs/interfaces, type hints, dataclasses, exception handling, packaging, virtual environments.

**Concurrency**: `asyncio`, queues, producer-consumer pattern, cancellation (`asyncio.Task.cancel` — needed for barge-in).

**Audio processing**: PCM basics, sample rate/channels, streaming buffers, mic capture (`sounddevice`/`pyaudio`), playback with interrupt support.

**Speech recognition**: `faster-whisper`, streaming/partial transcription, confidence thresholds.

**LLMs**: local inference (`llama.cpp`/Ollama), prompt engineering, context window management, token limits, streaming token consumption.

**Text-to-speech**: Piper, streaming synthesis, voice model selection.

**AI engineering**: latency optimization, fallback/degradation design, offline deployment tradeoffs.

**Software engineering**: state machines, event-driven design (lightweight, not framework-level), SOLID basics, interface-based module boundaries, config management.

**Data**: SQLite or JSON for session/history persistence.

**Observability**: structured logging, latency instrumentation, basic metrics collection.

**Testing**: unit tests per module, integration test for full pipeline, manual stress testing (interrupt mid-response, force LLM timeout, garbled audio input).

**Documentation**: architecture diagram, README, install guide, AI-usage disclosure, latency measurement report.

---

## 13. Next step

This document is locked. Next: start Phase 1 (repo skeleton + interfaces) with Ollama + the models above as the initial concrete choices. No more architecture iteration after this — if you hit a real constraint during implementation (a model missing your latency target on your hardware, a library not behaving as expected), log it below. Don't reopen this document's design sections to fix it.

---

## 14. Deviations from design (fill in during implementation)

| Date | What changed | Why (evidence, not speculation) |
|---|---|---|
| | | |
