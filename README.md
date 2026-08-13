💻🎥🧠 EXPLANATION OF MY CODE 💻🎥🧠 -------------->>>>>>>> ""
💻🎥🧠 EXPLANATION OF MY CODE 💻🎥🧠 -------------->>>>>>>> ""



## ⚡ Code Ownership & Architecture

This project is built on a **Custom Core Engine + Integrated Tool Plugins** architecture.

### 🛠️ Core Framework (Custom Built by Me)
* **`main.py`** — Real-time voice engine, event loop & AI tool dispatcher.
* **`model.py`** — PyQt6 sci-fi HUD interface, ARC reactor animations & PC performance monitor.
* **`or_client.py`** — API client with automatic model switching & rate-limit failover.
* **`setup.py`** — Automated environment setup & browser installer.

### 🔌 Integrated Action Modules (Adapted Open-Source)
* **`actions/`** — PC automation tools (web search, browser control, file tools, computer settings).
* **`agent/`** — Multi-step task execution & planning system.
* **`core/prompt.txt`** — Assistant personality & tool definitions.

J.A.R.V.I.S. (MARK XXXIX) — AI Desktop Assistant

An intelligent, real-time voice and automation desktop assistant inspired by
Iron Man's J.A.R.V.I.S. Built with Python, Google Gemini Live Audio, OpenRouter,
and PyQt6.

Overview

J.A.R.V.I.S. (MARK XXXIX) is a hands-free desktop AI assistant designed to help
users control their computer using natural voice commands, inspect files,
analyze screen content, run system tasks, and manage files.

Unlike traditional text-based chatbots, J.A.R.V.I.S. operates through
low-latency streaming voice conversations, continuously monitors system hardware
metrics, and executes real actions on your computer—like opening apps, running
code, organizing files, and controlling web browsers.

Project Goals

1.  Natural Voice Interaction: Enable conversational speech-to-speech
    communication with minimal delay.
2.  Real Desktop Control: Give the AI safe tools to perform actual tasks on the
    PC rather than just returning text instructions.
3.  Multimodal Capabilities: Enable J.A.R.V.I.S. to "see" via webcam and screen
    captures, and "read" user-uploaded files.
4.  Interactive Sci-Fi GUI: Build a smooth Iron Man ARC Reactor UI that shows
    live status and system telemetry without freezing.
5.  Resilient AI Architecture: Provide backup AI models so the assistant
    continues working even if an API hits a rate limit.

Key Features

  - Real-Time Voice Chat: Low-latency voice interaction powered by Google’s
    native audio streaming model.
  - Futuristic PyQt6 HUD: An animated Iron Man ARC Reactor interface with
    glowing visualizers, particle physics, and audio waveforms.
  - Computer Automation: Opens apps, adjusts volume and brightness, types text,
    manages windows, and controls media playback.
  - Web & Browser Automation: Conducts web searches, controls YouTube videos,
    searches Google Flights, and automates browser tasks via Playwright.
  - Vision & Screen Analysis: Analyzes what is on your screen or webcam to
    identify physical objects, documents, or troubleshooting issues.
  - Smart File Processor: Converts, compresses, summarizes, or inspects images,
    PDFs, code files, CSVs, audio, and video files dropped into the UI.
  - Autonomous Developer Agent: Writes, edits, tests, and builds multi-file code
    projects from simple natural language descriptions.
  - System Telemetry: Live background monitoring of CPU, RAM, Network speeds,
    GPU, and temperature metrics.
  - Long-Term Memory: Remembers important details about the user (name,
    preferences, active projects) across sessions.
  - Game Manager: Specialized automation for Steam and Epic Games updates and
    installations.

How It Works

1.  Listening: The microphone continuously records input. A software gain
    scaling layer amplifies quiet voices.
2.  AI Processing: Audio is streamed directly to Google Gemini's native audio
    model over a live WebSocket connection.
3.  Tool Call Execution: When the user asks for an action (e.g., "Open Chrome"
    or "Check my CPU usage"), Gemini returns a tool request. The Python engine
    executes the task locally and sends the output back to Gemini.
4.  Voice Output: Gemini generates continuous speech audio (24kHz PCM), which is
    played through the computer speakers while the UI displays active voice
    waveforms.
5.  Visual Feedback: The PyQt6 GUI updates its status indicators (LISTENING,
    THINKING, SPEAKING) and draws real-time hardware metrics.

AI Model Integration

J.A.R.V.I.S. uses a hybrid approach combining primary real-time streaming and
secondary processing:

  - Primary Model: gemini-2.5-flash-native-audio-preview-12-2025 via Google
    GenAI SDK for low-latency native audio streaming.
  - Secondary / Fallback Engine: OpenRouter API integration for text generation,
    structured JSON output, and static vision processing when direct audio calls
    require fallback processing.

Tool / Function Calling

J.A.R.V.I.S. uses function calling to translate user intent into Python actions.
A total of 18 tools are registered:

| Tool Name                   | Action Description                                                     |
| :-------------------------- | :--------------------------------------------------------------------- |
| `open_app`                  | Launches installed Windows apps or applications.                       |
| `browser_control`           | Operates browser navigation, clicking, typing, and form filling.       |
| `computer_settings`         | Controls system volume, display brightness, dark mode, and hotkeys.    |
| `computer_control`          | Direct mouse clicks, keystrokes, dragging, and window focusing.        |
| `file_controller`           | Manages file system CRUD (create, move, delete, rename, list).         |
| `file_processor`            | Inspects and converts images, PDFs, CSVs, audio, video, and archives.  |
| `screen_process`            | Captures screen or webcam feed to describe visual items.               |
| `code_helper` & `dev_agent` | Writes, executes, tests, and builds software projects automatically.   |
| `game_updater`              | Manages game downloads and update scheduling for Steam & Epic Games.   |
| `save_memory`               | Silently extracts and saves personal user facts to persistent storage. |

Memory System

J.A.R.V.I.S. maintains long-term memory about the user:

  - Extraction: In the background, conversation turns are analyzed to extract
    key facts (such as the user's name, preferences, active coding projects, or
    city).
  - Storage: Facts are saved cleanly categorized in a persistent JSON file
    (memory/).
  - Injection: Stored memories are dynamically injected into the system prompt
    upon startup so J.A.R.V.I.S. remembers context between restarts.

Voice Interaction

  - Audio Input: 16kHz Mono PCM captured using sounddevice.
  - Microphone Gain Scaling: Uses numpy math scaling (MIC_GAIN = 1.8) to boost
    microphone input sensitivity, allowing J.A.R.V.I.S. to hear soft speech from
    a distance.
  - Audio Output: 24kHz Mono PCM speech output for standard voice playback.

Computer & Browser Automation

  - Desktop Control: Uses system hotkeys and execution commands to control
    active windows, typing, and keyboard navigation.
  - Browser Automation: Employs Playwright to open headless or visible browsers,
    perform searches, click elements, fill forms, and extract page contents.

Vision / Screen Analysis

Without visual feedback, an assistant cannot help with on-screen tasks.
J.A.R.V.I.S. includes a vision processing tool:

  - Screen Mode: Captures current desktop displays to answer visual questions or
    troubleshoot software issues.
  - Camera Mode: Accesses webcam feeds to identify physical objects, documents,
    or items held up by the user.

File & Code Tools

  - Drag-and-Drop Processing: Users can drop any file into the UI drop zone.
  - Multi-Format Support: Automatically detects file types (images, PDFs, CSVs,
    source code, archives, audio, video) and suggests logical operations like
    OCR, conversion, summarization, or formatting.
  - Dev Agent: A built-in code engine that plans project architecture, writes
    multi-file repositories, installs dependencies, opens VSCode, and fixes
    runtime errors automatically.

System Monitoring

A background thread continuously samples PC performance using psutil and system
CLI utilities:

  - Monitored Hardware: CPU Usage (%), RAM Usage (%), Network Transfer Speeds
    (KB/s or MB/s), GPU Utilization (%) via nvidia-smi / rocm-smi, CPU
    Temperature (°C), Active Process Count, and System Uptime.

GUI / HUD

The user interface is built with PyQt6 and offers a functional sci-fi aesthetic:

  - Custom QPainter Canvas: Renders animated spinning arc rings, glowing halos,
    radar scanners, and audio visualizer bars at ~60 FPS.
  - Asynchronous Log Console: Displays color-coded terminal messages with a
    smooth typewriter character effect.
  - Responsive Layout: Responsive sidebar displaying system metrics, central ARC
    reactor canvas, activity log, file drop zone, and text command input field.

Multithreading & Background Processing

To prevent the user interface from freezing during heavy tasks, the application
uses thread management:

  - GUI Thread: Runs the PyQt6 event loop exclusively.
  - AI Engine Thread: Runs the asynchronous asyncio event loop for Gemini Live
    streaming.
  - Worker Threads: Executes long-running tasks like system monitoring, web
    searching, dev building, and memory updates in background threads.

API Integration

  - Google GenAI SDK: Handles real-time WebSocket live audio connections and
    function declaration schemas.
  - OpenRouter REST API: Interfaces with multiple open-source and commercial LLM
    providers over HTTP requests using a fallback model architecture.

Model Fallback & Rate Limiting

The secondary OpenRouter engine features resilience mechanisms:

  - Fallback Pool: Cycles through 20+ text models (e.g., Llama 3.3, Gemma, Qwen)
    and 8+ vision models.
  - Rate-Limit Management: Automatically detects HTTP 429 responses, tags the
    model as rate-limited, applies a 60-second cooldown, and immediately retries
    the prompt with the next model in the pool.

Error Handling

  - Audio Reconnection: Automatically attempts to reconnect to Gemini Live
    within 3 seconds if the connection drops.
  - Tool Error Vocalization: Catches exceptions during tool execution, logs full
    stack traces to the console, and instructs J.A.R.V.I.S. to verbally explain
    the error to the user.
  - Safe Memory Extraction: Suppresses rate-limit errors during non-critical
    background memory extraction.

Security & API Key Management

  - Protected Configuration: API keys are stored locally in
    config/api_keys.json, which is excluded from version control via .gitignore.
  - Masked Key Entry: First-time UI configuration uses password-masked input
    fields.

Technologies Used

  - Programming Language: Python 3.10+
  - User Interface: PyQt6, PIL (Pillow)
  - AI & Machine Learning: Google GenAI SDK (google-genai), OpenRouter API
  - Audio Processing: SoundDevice, NumPy
  - System Telemetry: Psutil, Subprocess
  - Browser Automation: Playwright
  - HTTP & Data Handling: Requests, JSON

Installation

Prerequisites

  - Operating System: Windows 10/11 (Recommended for full automation features)
  - Python Version: Python 3.10 or higher
  - Recommended: Virtual Environment (venv)

Configuration

On first run, J.A.R.V.I.S. will present an setup overlay screen in the UI asking
for:

1.  Gemini API Key: Obtainable from Google AI Studio.
2.  OpenRouter API Key: Obtainable from OpenRouter.
3.  Target OS Selection: Auto-detected (Windows / macOS / Linux).

Alternatively, manually create config/api_keys.json:

{
    "gemini_api_key": "YOUR_GEMINI_KEY_HERE",
    "openrouter_api_key": "YOUR_OPENROUTER_KEY_HERE",
    "os_system": "windows"
}

How to Run

Launch J.A.R.V.I.S. by executing:

python main.py

Example Commands

  - General Voice Commands:
      - "J.A.R.V.I.S., open Chrome and search for recent space discoveries."
      - "What is my current CPU and RAM usage?"
      - "Set system volume to 50%."
  - Vision Commands:
      - "Look at what is on my screen and summarize this article."
      - "Examine this object in front of the camera."
  - File & Developer Commands:
      - "I dropped a file into the UI—can you summarize its contents?"
      - "Build a complete Python weather dashboard app from scratch."
  - Gaming & Updates:
      - "Check for any pending updates for Steam games."

Challenges & Solutions

1.  Challenge: Quiet Speech Recognition
      - Problem: Standard microphone audio was often quiet when speaking from
        across a desk.
      - Solution: Implemented software audio scaling with numpy.clip() to boost
        input sensitivity without clipping audio channels.
2.  Challenge: GUI Freezing During Heavy Tasks
      - Problem: Running heavy tool automation tasks caused the PyQt6 user
        interface to freeze.
      - Solution: Decoupled the UI completely by running async event loops and
        delegating tool executions to background worker threads.
3.  Challenge: API Rate Limits Interrupting Usage
      - Problem: Free-tier models occasionally hit HTTP 429 rate limits during
        long usage sessions.
      - Solution: Built an automatic fallback client in openrouter_client.py
        that cycles through backup models when rate limits occur.

Technical Decisions

  - Why Gemini 2.5 Flash Live API? Provides native speech-to-speech interaction,
    eliminating delays from separate Speech-to-Text and Text-to-Speech stages.
  - Why PyQt6 over Tkinter? Offers hardware-accelerated rendering, better
    styling control, and robust support for custom animated graphics.
  - Why Function Calling instead of Script Generation? Function calling returns
    structured parameters, making hardware control safer and more reliable.

What I Learned

Through building J.A.R.V.I.S., I gained practical experience in:

  - Asynchronous network programming with Python asyncio and WebSockets.
  - Multithreaded GUI state synchronization using PyQt6 signals.
  - Real-time audio streaming (PCM buffer management and gain processing).
  - Integrating multimodal AI models with local tool execution.
  - Implementing fallback strategies for external API integrations.

Limitations

  - Operating System Optimization: While core features run cross-platform,
    administrative automation features (like Task Scheduler reminders) are
    optimized primarily for Windows.
  - Internet Dependency: Requires an active internet connection to communicate
    with Gemini and OpenRouter APIs.

Future Improvements

  - Offline Voice Processing: Add local fallback options for STT/TTS (e.g.,
    Whisper and Piper) for basic offline commands.
  - Smart Home Integration: Connect J.A.R.V.I.S. to Home Assistant or IoT APIs
    to control smart lights and devices.
  - Custom Voice Support: Integrate high-quality voice cloning for custom audio
    responses.

Testing

  - Module Self-Test: openrouter_client.py includes a built-in self-test suite.
    Run it directly to verify model pools and JSON parsing:
    python openrouter_client.py
  - Voice & Audio Diagnostics: System logs print input levels and connection
    status to monitor performance.

Credits & Acknowledgements

  - Inspiration: Marvel Studios' Iron Man (J.A.R.V.I.S. AI System).
  - AI Infrastructure: Powered by Google Gemini and OpenRouter.
  - Libraries Used: PyQt6, Playwright, SoundDevice, Psutil, NumPy.

Development / Academic Note

This project was designed and developed as a personal portfolio project
demonstrating concepts in asynchronous software design, multimodal AI
integration, GUI development, and system automation. Submitted as part of my
undergraduate application to the Computer Science program at Rutgers University.

Disclaimer

This project is an independent educational development built for personal
learning. Character names and concepts inspired by Marvel's Iron Man are
intellectual properties of Disney / Marvel Entertainment.
