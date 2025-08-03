I am working on a project for a Search and Rescue team, here is the abstract:
In Search and Rescue (SAR) operations, time pressure and inexperience can lead to missed opportunities during interviews with a missing person's friends and family. This thesis presents a real-time, end-to-end system that suggests context-aware follow-up questions and extracts actionable clues as the interview unfolds. Leveraging large language models (LLMs), agentic design patterns, and integration with the IntelliSAR platform, the system assists interviewers in surfacing more complete and relevant information. It also compiles key insights into a structured clue log, ready for human review, refinement, and dissemination to the rest of the team. The system's ultimate goal is to accelerate clue discovery and reduce the likelihood of critical information being overlooked in time-sensitive SAR missions.

I am using this techstack: LangGraph/LangChain, Python, Langfuse, WebRTC, Vite, Pydantic, Typescript.

# 🏗️ Architecture Philosophy

## Functional-First Design Principles

This codebase follows a **functional-first, modular architecture** with the following core principles:

### 🎯 Core Tenets

1. **Functions Over Classes**: Prefer pure functions over stateful classes where possible
2. **Explicit Dependencies**: Use dependency injection instead of global state or hidden dependencies  
3. **Hook-Based Extensibility**: Use callback hooks for clean separation of concerns and testability
4. **Immutable Messages**: All communication uses type-safe Pydantic models
5. **Swappable Components**: Design functions to be easily mockable and replaceable for testing

### 📦 Component Structure

#### `session.py` - State Encapsulation
- **Session**: Dataclass for per-user state with minimal coupling
- **SessionManager**: Manages active sessions and routes audio chunks
- Uses explicit `SendCallback` type for message dispatch

#### `transcription.py` - Functional Audio Processing  
- **Pure Functions**: `transcribe_stream()`, `create_recognizer()`, `finalize_transcription()`
- **FastAPI Lifespan**: Expensive Vosk model loaded once via `initialize_vosk_model()`
- **Swappable Providers**: Easy to mock with `mock_transcribe_stream()` for testing

#### `processing.py` - Functional Text Analysis
- **Simple Function**: `process_text(text: str) -> ProcessedText`  
- **Dataclass Results**: Type-safe `ProcessedText` instead of raw dictionaries
- **Easily Extensible**: Add NLP features without changing interface

#### `websocket_server.py` - Connection Management
- **SessionManager**: Encapsulates WebSocket state with `asyncio.Lock` for thread safety
- **Pure Function**: `handle_client(websocket, session_manager)` driven by dependency injection
- **Hook Pattern**: `on_connect`, `on_message`, `on_disconnect` callbacks for extensibility

#### `webrtc_handler.py` - WebRTC Processing
- **Hook Functions**: `setup_webrtc_hooks()` returns pure callback functions
- **Functional Decomposition**: `handle_offer()`, `handle_ice_candidate()`, `process_audio_track()`
- **Clean Integration**: Hooks wire into WebSocket session manager without tight coupling

#### `main.py` - Dependency Injection Bootstrap
- **Lifespan Management**: Initialize expensive resources (Vosk) once at startup
- **Explicit Wiring**: Create managers and inject dependencies explicitly
- **No Globals**: All shared state managed through passed instances

### 🔌 Key Patterns

#### Message Types (Pydantic Models)
```python
# messages.py
class TranscriptionMessage(BaseMessage):
    session_id: str
    text: str
    is_partial: bool = False

# webrtc_messages.py  
class OfferMessage(BaseModel):
    type: Literal["offer"] = "offer"
    sdp: SDPData
```

#### Hook-Based Architecture
```python
# Pure functions as hooks
async def webrtc_on_connect(user_id: str, send_func):
    session_manager.create_session(user_id, send_func)

# Wire hooks via dependency injection
websocket_session_manager.set_hooks(
    on_connect=webrtc_on_connect,
    on_message=webrtc_on_message,
    on_disconnect=webrtc_on_disconnect
)
```

#### Swappable Components
```python
# Production
async for transcript in transcribe_stream(chunk, recognizer):
    # Process transcript...

# Testing  
async for transcript in mock_transcribe_stream(chunk, ["test", "data"]):
    # Same interface, different implementation
```

### ✅ Benefits

- **Testability**: Pure functions and dependency injection enable isolated testing
- **Modularity**: Components can be developed and tested independently  
- **Maintainability**: Clear interfaces and minimal coupling reduce complexity
- **Extensibility**: Hook pattern allows adding features without modifying core logic
- **Type Safety**: Pydantic models catch errors at development time

### 🧪 Testing Philosophy

- **Unit Tests**: Test pure functions in isolation with known inputs/outputs
- **Integration Tests**: Use mock providers and dependency injection for component testing
- **No Global State**: All dependencies passed explicitly, making tests deterministic
