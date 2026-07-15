from setuptools import setup

setup(
    name="agent-pal",
    version="1.0.0",
    description="Desktop Buddy for CLI Agents (Claude Code, Antigravity, Codex)",
    py_modules=["agent_pal"],
    install_requires=[
        "psutil",
        "pywin32",
    ],
    entry_points={
        "console_scripts": [
            "agent-pal = agent_pal:main",
        ],
    },
)
