import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import tempfile
import ffmpeg

# Load the .env file
load_dotenv()

# Initialize OpenAI client
client = OpenAI()

# Set page config
st.set_page_config(page_title="Video Transcription & Translation", layout="wide")

# Custom CSS 
st.markdown("""
<style>
    body {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        background-attachment: fixed;
    }
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .st-emotion-cache-1v0mbdj > img {
        width: 100%;
        max-width: 150px;
    }
    .stMultiSelect [data-baseweb=select] {
        background-color: rgba(255, 255, 255, 0.7);
    }
    .stTextInput>div>div>input {
        background-color: rgba(255, 255, 255, 0.7);
    }
    .stTextArea textarea {
        background-color: rgba(255, 255, 255, 0.7);
    }
    .stButton>button {
        background-color: #4e8cff;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 5px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #3a7be8;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .sidebar .sidebar-content {
        background-color: rgba(255, 255, 255, 0.1);
    }
</style>
""", unsafe_allow_html=True)

def process_video(uploaded_file, selected_languages):
    with st.spinner("Processing your video... This may take a few minutes."):
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
            temp_video.write(uploaded_file.read())
            temp_video_path = temp_video.name

        # Convert video to audio using ffmpeg
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_audio_path = temp_audio.name
        temp_audio.close()

        ffmpeg.input(temp_video_path).output(temp_audio_path, acodec='libmp3lame').overwrite_output().run()

        # Transcribe audio
        with open(temp_audio_path, 'rb') as audio:
            transcription_response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio,
                response_format="srt"
            )
        
        transcription_text = transcription_response

        # Translate
        translations = {}
        for lang in selected_languages:
            with st.spinner(f"Translating to {lang}..."):
                translation_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a skilled translator. Translate the given SRT subtitle text accurately while preserving the original format and timestamps."},
                        {"role": "user", "content": f"Translate this SRT subtitle text to {lang}:\n\n{transcription_text}"}
                    ]
                )
                translated_text = translation_response.choices[0].message.content
                translations[lang] = translated_text

        # Clean up temporary files
        os.unlink(temp_audio_path)
        os.unlink(temp_video_path)

    return transcription_text, translations

def main():
    st.title("🎥 Video Transcription & Translation Hub")

    # Sidebar
    with st.sidebar:
        st.header("📋 Instructions")
        st.markdown("""
        1. 📤 Upload your video file
        2. 🌐 Select target languages
        3. 🚀 Click 'Process Video'
        4. 📜 View transcription & translations
        5. 💾 Download SRT files
        """)

    # Initialize session state
    if 'processed' not in st.session_state:
        st.session_state.processed = False
        st.session_state.transcription = None
        st.session_state.translations = None

    # Main content
    if not st.session_state.processed:
        st.subheader("📤 Upload Your Video")
        uploaded_file = st.file_uploader("Choose a video file", type=["mp4", "avi", "mov"])

        if uploaded_file:
            st.video(uploaded_file)

        st.subheader("🌐 Select Languages for Translation")
        languages = {
            "Turkish": "🇹🇷", "French": "🇫🇷", "English": "🇬🇧", 
            "German": "🇩🇪", "Spanish": "🇪🇸", "Italian": "🇮🇹", "Russian": "🇷🇺"
        }
        
        # Create options for multiselect with flag emojis
        options = [f"{flag} {lang}" for lang, flag in languages.items()]
        
        selected_languages = st.multiselect(
            "Choose one or more languages for translation:",
            options=options
        )
        
        # Extract language names without emojis
        selected_languages = [lang.split()[-1] for lang in selected_languages]

        if uploaded_file and selected_languages:
            if st.button("🚀 Process Video"):
                transcription, translations = process_video(uploaded_file, selected_languages)
                st.session_state.processed = True
                st.session_state.transcription = transcription
                st.session_state.translations = translations
                st.experimental_rerun()

    if st.session_state.processed:
        st.subheader("📝 Original Transcription")
        st.text_area("", value=st.session_state.transcription, height=200)
        st.download_button("💾 Download Original Transcription", st.session_state.transcription, "transcription.srt")

        for lang, translated_text in st.session_state.translations.items():
            st.subheader(f"🌐 {lang} Translation")
            st.text_area("", value=translated_text, height=200)
            st.download_button(f"💾 Download {lang} Translation", translated_text, f"{lang.lower()}_translation.srt")

        if st.button("🔄 Process Another Video"):
            st.session_state.processed = False
            st.session_state.transcription = None
            st.session_state.translations = None
            st.experimental_rerun()

if __name__ == "__main__":
    main()