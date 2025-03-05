# Snapdragon NPU Edge Chat App

A simple, NPU-accelerated chat app running on the [AnythingLLM](https://anythingllm.com/) model server. By using AnythingLLM as your model server, you get automatic access to the built-in RAG, conversation memory, and other LLM functionalities and optimizations for each Workspace.

This application is intended to serve as an extensible base app for a custom local language model. [AnythingLLM](https://anythingllm.com/) includes many API endpoints, including Open AI compatibility, that you can access in Settings -> Tools -> Developer API -> Read the API documentation.

### Table of Contents
[1. Implementation](#implementation)<br>
[2. Setup](#setup)<br>
[3. Usage](#usage)<br>

### Implementation
This app was built for the Snapdragon X Elite but designed to be platform agnostic. Performance may vary on other hardware.

#### Hardware
- Machine: Dell Latitude 7455
- Chip: Snadragon X Elite
- OS: Windows 11
- Memory: 32 GB

#### Software
- Python Version: 3.12.6
- AnythingLLM LLM Provider: Qualcomm QNN
- AnythingLLM Chat Model: Llama 3.1 8B Chat 8K

### Setup
1. Install and setup [AnythingLLM](https://anythingllm.com/).
    1. When prompted to choose an LLM provider, choose Qualcomm QNN for the NPU
    2. Choose a model of your choice when prompted (this sample uses Llama 3.1 8B Chat)
2. Create a workspace by clicking "+ New Workspace"
3. Generate an API key
    1. Click the settings button on the bottom of the left panel
    2. Open the "Tools" dropdown
    3. Click "Developer API"
    4. Click "Generate New API Key"
4. Open a PowerShell instance and clone the repo
    ```
    git clone https://github.com/thatrandomfrenchdude/simple_npu_chatbot.git
    ```
5. Create and activate your virtual environment with reqs
    ```
    # navigate to the directory
    cd simple_npu_chatbot

    # create the virtual environment
    python -m venv llm-venv

    # activate the virtual environment
    ./llm-venv/Scripts/Activate.ps1     # windows
    source \llm-venv\bin\activate       # mac/linux

    # install the requirements
    pip install -r requirements.txt
    ```
6. Create your `config.yaml` file with the following variables
    ```
    api_key: "your-key-here"
    model_server_base_url: "http://localhost:3001/api/v1"
    workspace_slug: "your-slug-here"
    ```
7. Test the model server auth to verify the API key
    ```
    python src/auth.py
    ```
8. Get your workspace slug using the workspaces tool
    1. Run ```python src/workspaces.py``` in your command line console
    2. Find your workspace and its slug from the output
    3. Add the slug to the `workspace_slug` variable in config.yaml

### Usage
After completing setup, run the app from the command line:
```
python src/chatbot.py
```

