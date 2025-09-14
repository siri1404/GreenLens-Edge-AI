#!/usr/bin/env python3
"""
Test script to verify Gradio chatbot fix
"""
import gradio as gr

def test_chat(message, history):
    """Test chat function with new messages format"""
    if not message.strip():
        return history, ""
    
    # Add user message to history (new messages format)
    history.append({"role": "user", "content": message})
    
    # Simple response
    response = f"Echo: {message}"
    history.append({"role": "assistant", "content": response})
    
    return history, ""

# Create simple test interface
with gr.Blocks(title="Test Chatbot Fix") as demo:
    gr.Markdown("# Test Gradio Chatbot Fix")
    
    chatbot = gr.Chatbot(
        height=400,
        label="Test Assistant",
        show_label=True,
        type="messages"  # This should fix the warning
    )
    
    with gr.Row():
        msg = gr.Textbox(
            placeholder="Type a message...",
            label="Your Message",
            lines=2
        )
        send_btn = gr.Button("Send", variant="primary")
    
    clear_btn = gr.Button("Clear Chat", variant="secondary")
    
    # Event handlers
    msg.submit(test_chat, [msg, chatbot], [chatbot, msg])
    send_btn.click(test_chat, [msg, chatbot], [chatbot, msg])
    clear_btn.click(lambda: ([], ""), outputs=[chatbot, msg])

if __name__ == "__main__":
    print("Testing Gradio chatbot fix...")
    print("This should not show the deprecation warning anymore.")
    demo.launch(server_name="127.0.0.1", server_port=7861, share=False, inbrowser=False, quiet=True)

