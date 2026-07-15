# Agent Pal 🤖🚀

**Agent Pal** is an interactive, physics-based desktop buddy application for Windows that monitors terminal-based AI coding agents (such as *Claude Code*, *Antigravity CLI*, *Codex*, etc.). 

It helps you keep track of background agents by roaming your screen and visually alerting you when they are busy, waiting for input, or have finished their tasks.

---

## Features

- **Agent-Specific Mascots**:
  - **Antigravity CLI**: A floating blue astronaut with active thruster flames (defies gravity).
  - **Claude Code**: A coral-colored terminal box with orange outlines and blinking green CLI code eyes (`> _`).
  - **Generic Agents**: A classic green-themed terminal monitor.
- **Visual Activity States**:
  - **Writing Code**: Draws a small typewriter keyboard and typing hands wiggling up and down when process CPU is active.
  - **Researching**: Holds a tiny bobbing magnifying glass when inspecting files.
- **Task Success Alert (`✔`)**:
  - Displays a green checkmark bubble and makes the buddy celebrate with a joyful leap and sparkling stars when the task completes.
- **Smart Attention Alert (`!`)**:
  - If the agent drops to 0% CPU (waiting for your input) AND its terminal window is not active, a floating red `!` speech bubble appears over the buddy to grab your attention.
- **Double-Click-to-Focus**:
  - Double-click any buddy to instantly bring its corresponding terminal window (including tabs inside Windows Terminal) to the front.
- **Multi-Monitor Support**:
  - Buddies spawn on the screen where their respective terminal window is open, and can be dragged freely across all monitors. Walking and climbing physics automatically snap to the boundaries of the monitor they reside on.
- **Collision Avoidance**:
  - When two buddies collide on the taskbar, they bounce off each other and walk in opposite directions.
- **Interactive Game (Spawn Code Bug)**:
  - Right-click any buddy to spawn a crawling code bug. Buddies enter a **Chasing** state, run towards the bug, jump on it to squash it, and celebrate with sparkling stars.

---

## Installation & Setup

Clone the repository and run the batch installer:

```bash
install.bat
```

This installer:
1. Installs all Python dependencies and packages `agent-pal` as a local command-line script.
2. Creates a windowless Windows startup script (`agent-pal-startup.vbs`) in your startup folder so Agent Pal starts silently in the background when your PC boots.

---

## Usage

### 1. Silent Background Mode (Default)
Run the coordinator silently in the background:
```bash
pythonw.exe -m agent_pal
```
*(Or simply let the Windows Startup script run it).*
- When no CLI agents are running, the application has **no screen footprint** (runs silently in the background).
- As soon as you open **Claude Code**, **Antigravity CLI**, or **Codex**, their dedicated buddies will pop up on your taskbar.
- When you close the terminal, their buddies disappear automatically.

### 2. Single-Session Mode (Auto-Exit)
If you only want Agent Pal to run for the duration of a single terminal session and exit completely when the terminal is closed, run:
```bash
agent-pal --exit-when-idle
```

---

## Controls

- **Left-Click + Drag**: Pick up and fling/throw buddies across your screen. They will fall back down with realistic squash-and-stretch landing impacts.
- **Double-Click**: Bring the agent's console window to the front.
- **Right-Click Menu**:
  - **Mark Alert as Read**: Clear any floating checkmark or exclamation bubble instantly (only active when bubbles are visible).
  - **Mute Alerts**: Mutes visual alert bubbles.
  - **Hold Buddy**: Pauses physics, holding the buddy in place.
  - **Spawn Code Bug**: Drops a crawling purple bug for buddies to chase and squash.
  - **Exit Pal**: Shuts down the coordinator application.
