import streamlit as st
import azure.cognitiveservices.speech as speechsdk
import openai
from dotenv import load_dotenv
import os
import requests
import base64
import tempfile

# Load credentials from .env file
load_dotenv()
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION = os.getenv("AZURE_REGION")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
DEPLOYED_MODEL_NAME = os.getenv("DEPLOYED_MODEL_NAME")

# Azure Speech-to-Text Function
def speech_to_text():
    """Converts user speech to text using Azure Speech-to-Text."""
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config)

    with st.spinner("Listening... Please speak into your microphone."):
        result = speech_recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        return "Speech could not be recognized."
    elif result.reason == speechsdk.ResultReason.Canceled:
        return "Speech recognition canceled. Please try again."
    return None

# OpenAI Response Generation Function
def generate_response(conversation_history):
    """
    Generate a response using the deployed OpenAI model on Azure.
    """
    url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{DEPLOYED_MODEL_NAME}/chat/completions?api-version=2023-03-15-preview"
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_KEY,
    }
    payload = {
        "messages": conversation_history,
        "temperature": 0.7,
        "max_tokens": 150
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise exception for HTTP errors
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Azure OpenAI: {e}")
        return "I'm sorry, I couldn't process that."

# Azure Text-to-Speech Function
def text_to_speech(text):
    """Converts text to speech using Azure Text-to-Speech."""
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
    audio_file_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
    audio_config = speechsdk.audio.AudioOutputConfig(filename=audio_file_path)

    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    synthesizer.speak_text_async(text).get()
    return audio_file_path

# Streamlit UI
def main():
    """Main function to run the Streamlit app."""
    st.title("🎙️ SpeakMate - Virtual Companion Assistant")
    st.markdown("Interact with your AI assistant using speech!")

    # Initialize session state for conversation history
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = [{"role": "system", "content": "You are a helpful assistant."}]

    # Display conversation history
    st.markdown("### Conversation")
    for i, message in enumerate(st.session_state.conversation_history[1:]):  # Skip the system message
        role = "👤 You" if message["role"] == "user" else "🤖 SpeakMate"
        st.markdown(f"**{role}:** {message['content']}")

    # Step 1: Record and Convert Speech to Text
    if st.button("🎤 Record and Process"):
        user_text = speech_to_text()
        if user_text:
            st.success(f"Recognized Speech: {user_text}")
            st.session_state.conversation_history.append({"role": "user", "content": user_text})

            # Step 2: Generate Response
            with st.spinner("Generating response..."):
                ai_response = generate_response(st.session_state.conversation_history)
                st.session_state.conversation_history.append({"role": "assistant", "content": ai_response})
                st.info(f"AI Response: {ai_response}")

            # Step 3: Convert Response to Speech
            with st.spinner("Converting response to speech..."):
                audio_file = text_to_speech(ai_response)
            
            # Autoplay the audio
            with open(audio_file, "rb") as f:
                audio_data = f.read()
                audio_base64 = base64.b64encode(audio_data).decode()

            audio_html = f"""
                <audio autoplay>
                    <source src="data:audio/wav;base64,{audio_base64}" type="audio/wav">
                    Your browser does not support the audio element.
                </audio>
            """
            st.markdown(audio_html, unsafe_allow_html=True)
        else:
            st.error("Failed to recognize speech.")

    st.markdown("---")
    st.caption("Powered by Azure Speech Services and OpenAI.")

# Run the app
if __name__ == "__main__":
    main()
