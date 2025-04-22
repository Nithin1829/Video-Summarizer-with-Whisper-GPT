from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import uuid
from moviepy.editor import VideoFileClip
import whisper
from openai import OpenAI
from dotenv import load_dotenv



# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
RESULTS_FOLDER = "results"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Load Whisper model
whisper_model = whisper.load_model("base")

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})

@app.route('/api/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    try:
        # Save video
        video_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_{file.filename}")
        file.save(video_path)

        # Extract audio
        audio_path = video_path.replace('.mp4', '.wav')
        video_clip = VideoFileClip(video_path)
        video_clip.audio.write_audiofile(audio_path)

        # Transcribe with Whisper
        result = whisper_model.transcribe(audio_path)
        transcript = result["text"]

        # Summarize using OpenAI API
        prompt = f"Summarize this meeting transcript this meeting transcript should contain Summay as one sub heading and Action Items as another Sub hesding  . Give me results with mark down:\n\n{transcript}"
        summary_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        summary = summary_response.choices[0].message.content

        # Save transcript and summary
        job_results_dir = os.path.join(RESULTS_FOLDER, job_id)
        os.makedirs(job_results_dir, exist_ok=True)

        transcript_path = os.path.join(job_results_dir, "transcript.txt")
        summary_path = os.path.join(job_results_dir, "summary.txt")

        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript)

        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary)

        return jsonify({
            "job_id": job_id,
            "transcript": transcript,
            "summary": summary
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
