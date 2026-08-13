import subprocess
import sys

python_path = sys.executable

# Define setup steps: (message, command)
setup_steps = [
    ("Installing requirements...", [python_path, "-m", "pip", "install", "-r", "requirement.txt"]),
    ("Installing Playwright browsers...", [python_path, "-m", "playwright", "install"])
]

# Run each step
for message, command in setup_steps:
    print(message)
    subprocess.run(command, check = True)

print("\n✅ Setup complete! Run 'python main.py' to start ARYAN'S jarvis.")