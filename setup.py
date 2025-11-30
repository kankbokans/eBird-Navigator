#!/usr/bin/env python3
import os
import subprocess
import sys

def install_requirements():
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("✅ Python dependencies installed!")

def setup_ebird_mcp():
    os.chdir("ebird-mcp-server")
    subprocess.check_call(["npm", "install"])
    print("✅ eBird MCP server ready!")
    os.chdir("..")

if __name__ == "__main__":
    print("🦅 Setting up Birding Agent...")
    install_requirements()
    setup_ebird_mcp()
    print("\n🚀 Ready! Run: adk web")