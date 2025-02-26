# Snapdragon NPU Edge Chat App

Simple chat app with memory running on an NPU-accelerated [AnythingLLM](https://anythingllm.com/) model server.

### Hardware Info
- Machine: Dell Latitude 7455
- Chip: Snadragon X Elite
- OS: Windows 11
- Memory: 32 GB

### Software Info
- Python Version: 3.12.6
- AnythingLLM LLM Provider: Qualcomm QNN
- AnythingLLM Chat Model: Llama 3.1 8B Chat 8K

### Setup
1. Install [AnythingLLM](https://anythingllm.com/) and choose the NPU model server and a model of your choice during setup.
2. Create a workspace by clicking "+ New Workspace"
3. Generate an API key
    1. Click the settings button on the bottom of the left panel
    2. Open the "Tools" dropdown
    3. Click "Developer API"
    4. Click "Generate New API Key"
4. Open a PowerShell instance and clone the repo
    ```
    PS > git clone https://github.com/thatrandomfrenchdude/simple_npu_chatbot.git
    ```
5. Create and activate your virtual environment with reqs
    ```
    PS > python -m venv llm-venv
    PS > ./llm-venv/Scripts/Activate.ps1
    PS > pip install -r requirements.txt
    ```
6. Get your workspace slug using the workspaces tool
    1. ```> python src/workspaces.py```
    2. Find your workspace and its slug from the output
7. Create your `config.yaml` file with the following variables
    ```
    api_key: "your-key-here"
    model_server_base_url: "http://localhost:3001/api/v1"
    workspace_slug: "your-slug-here"
    ```
8. Test the model server auth
    ```
    PS > python src/auth.py
    ```

### Usage
```
PS > python main.py
```
