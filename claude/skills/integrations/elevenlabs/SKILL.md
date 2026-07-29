---
name: elevenlabs
description: Generate speech, sound effects, and music, clone voices, transcribe audio, and manage conversational AI agents using ElevenLabs. Use when the user wants to work with audio, voice, or speech.
---

# ElevenLabs Audio

Generate speech, sound effects, and music, clone voices, transcribe audio, and manage conversational AI agents.

## Available Operations

### Text-to-Speech & Sound

| Operation | Tool | Description |
|-----------|------|-------------|
| Text to speech | `mcp__elevenlabs__text_to_speech` | Convert text to spoken audio using a selected voice and model |
| Text to sound effects | `mcp__elevenlabs__text_to_sound_effects` | Generate sound effects from a text description |
| Text to voice | `mcp__elevenlabs__text_to_voice` | Generate a voice from a text description (voice design) |

### Speech Processing

| Operation | Tool | Description |
|-----------|------|-------------|
| Speech to text | `mcp__elevenlabs__speech_to_text` | Transcribe audio to text |
| Speech to speech | `mcp__elevenlabs__speech_to_speech` | Convert speech from one voice to another |

### Voice Management

| Operation | Tool | Description |
|-----------|------|-------------|
| Search voices | `mcp__elevenlabs__search_voices` | Search your saved voices by name or criteria |
| Get voice | `mcp__elevenlabs__get_voice` | Get details of a specific voice by ID |
| Clone voice | `mcp__elevenlabs__voice_clone` | Clone a voice from audio samples |
| Create from preview | `mcp__elevenlabs__create_voice_from_preview` | Save a previously generated voice preview |
| Voice library | `mcp__elevenlabs__search_voice_library` | Browse the public ElevenLabs voice library |

### Audio Processing

| Operation | Tool | Description |
|-----------|------|-------------|
| Isolate audio | `mcp__elevenlabs__isolate_audio` | Separate vocals from background noise/music |
| Play audio | `mcp__elevenlabs__play_audio` | Play an audio file locally |

### Music Composition

| Operation | Tool | Description |
|-----------|------|-------------|
| Compose music | `mcp__elevenlabs__compose_music` | Generate music from a composition plan |
| Create composition plan | `mcp__elevenlabs__create_composition_plan` | Plan a music composition (structure, instruments, mood) |

### Conversational AI Agents

| Operation | Tool | Description |
|-----------|------|-------------|
| Create agent | `mcp__elevenlabs__create_agent` | Create a new conversational AI agent |
| List agents | `mcp__elevenlabs__list_agents` | List all conversational AI agents |
| Get agent | `mcp__elevenlabs__get_agent` | Get details of a specific agent |
| Add knowledge base | `mcp__elevenlabs__add_knowledge_base_to_agent` | Attach a knowledge base to an agent |

### Conversations & Calls

| Operation | Tool | Description |
|-----------|------|-------------|
| List conversations | `mcp__elevenlabs__list_conversations` | List conversations for an agent |
| Get conversation | `mcp__elevenlabs__get_conversation` | Get details and transcript of a conversation |
| Make outbound call | `mcp__elevenlabs__make_outbound_call` | Initiate an outbound phone call from an agent |

### Account & Models

| Operation | Tool | Description |
|-----------|------|-------------|
| Check subscription | `mcp__elevenlabs__check_subscription` | View account subscription tier and usage limits |
| List models | `mcp__elevenlabs__list_models` | List available TTS and generation models |
| List phone numbers | `mcp__elevenlabs__list_phone_numbers` | List phone numbers available for outbound calls |

## Steps

### Phase 1: Understand Intent

1. Determine what the user wants to do:
   - **Generate speech** → text to speech (need text + voice)
   - **Create sound effects** → text to sound effects (need description)
   - **Compose music** → create composition plan, then compose music
   - **Transcribe audio** → speech to text (need audio file)
   - **Convert voice** → speech to speech (need audio file + target voice)
   - **Manage voices** → search, clone, create, or browse library
   - **Manage agents** → create, list, get, or add knowledge base
   - **Account info** → check subscription, list models, list phone numbers

### Phase 2: Prepare

2. Gather required inputs before executing:
   - For speech generation: use `search_voices` or `search_voice_library` to find a voice if the user hasn't specified one; use `list_models` to pick an appropriate model
   - For voice cloning: confirm the user has audio samples ready
   - For music: use `create_composition_plan` to structure the piece before generating
   - For outbound calls: use `list_phone_numbers` to get available numbers
   - Use `check_subscription` if the user asks about usage, limits, or available features

### Phase 3: Execute

3. Call the appropriate MCP tools:
   - For text-to-speech: pass the text, voice ID, and model to `text_to_speech`
   - For sound effects: pass the description to `text_to_sound_effects`
   - For music: pass the composition plan to `compose_music`
   - For transcription: pass the audio file path to `speech_to_text`
   - For voice conversion: pass audio and target voice to `speech_to_speech`
   - For voice cloning: pass audio samples to `voice_clone`
   - For agents: use the agent management tools as needed

### Phase 4: Playback & Report

4. After generating audio:
   - Use `play_audio` to play generated audio files for the user
   - Confirm what was generated (voice used, duration, file path)
   - Report any relevant details (model used, character count, credits consumed)

5. After non-audio operations:
   - Confirm the result (agent created, voice cloned, transcription complete)
   - Provide IDs or details the user may need for follow-up actions

## Rules

- ALWAYS search for or confirm a voice before generating speech — do not guess voice IDs
- ALWAYS use `create_composition_plan` before `compose_music` to ensure a well-structured result
- NEVER make outbound calls without explicit user confirmation of the phone number and recipient
- NEVER clone a voice without confirming the user has rights to the audio samples
- When the user asks for a specific voice style, search the voice library first to find a match
- For long text, note that generation may take longer and use more credits
- If a generation fails, check the subscription tier and usage limits with `check_subscription`
- Prefer the latest available model from `list_models` unless the user specifies otherwise
