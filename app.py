from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import re
import firebase_admin
from firebase_admin import credentials, firestore, storage
from PIL import Image
import mimetypes

# --- SETUP ---

# This loads the environment variables (your API key) from the .env file.
load_dotenv()
api_key = os.getenv("API_KEY")

genai.configure(api_key=api_key)

app = Flask(__name__)
CORS(app)

# This is the AI model we will use. It's great for complex document analysis.
model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')

# --- Firebase Admin SDK Setup (For secure backend access) ---
# This is a critical step to ensure the app is initialized before use.
# It checks if Firebase is already initialized to prevent a redundant call.
if not firebase_admin._apps:
    try:
        # Get the global firebase config from the environment variable
        service_account_info_str = os.getenv("FIREBASE_ADMIN_SDK")
        if service_account_info_str:
            service_account_info = json.loads(service_account_info_str)
            cred = credentials.Certificate(service_account_info)
            # Initialize the app with the service account credentials
            firebase_admin.initialize_app(cred, {'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')})
            db = firestore.client()
        else:
            print("FIREBASE_ADMIN_SDK not found. Firestore will not be available.")
    except json.JSONDecodeError as e:
        print(f"Error decoding FIREBASE_ADMIN_SDK environment variable: {e}")
        # For a hackathon, a simple print and exit is fine
        exit()

# --- ROUTES (Your website's different pages) ---

@app.route('/')
def index():
    """
    This is the homepage of your website. It simply serves the index.html file.
    """
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_document():
    """
    Handles file uploads, analyzes the document with AI, and stores the result.
    """
    try:
        # Get the Authorization header for the user ID
        user_id = request.headers.get('Authorization')
        if not user_id:
            return jsonify({"error": "User authentication failed."}), 401
            
        file = request.files.get('file')
        if not file:
            return jsonify({"error": "No file part in the request."}), 400

        file_content = file.read()
        mime_type = file.mimetype

        # Create AI prompt for document analysis
        prompt_text = """
        You are an AI assistant specializing in simplifying legal documents, particularly insurance policies and claims.
        Your goal is to identify and summarize hidden clauses and risks for the average person.

        Analyze the following document and provide four things in a structured JSON format:
        1. A short, easy-to-read, bulleted summary of the main points of the policy.
        2. A mind map of the document's key concepts, using a simple text-based format with indentation to show dependencies and connections.
        3. A list of any clauses or terms that are a high risk for the user. For each risk, provide the original text and a simplified explanation of why it's a risk.
        4. A "Did you know?" style tip about a common mistake people make with this type of document.

        Return your output as a single JSON object. Do not include any extra text or markdown formatting outside of the JSON object.

        JSON format example:
        {
          "summary": [
            "Point 1",
            "Point 2"
          ],
          "mind_map": "Main Idea\\n  - Sub-idea 1\\n    - Detail A\\n  - Sub-idea 2",
          "risks": [
            {
              "original_text": "Original clause text.",
              "simplified_explanation": "A simple explanation of the risk."
            }
          ],
          "tip": "A helpful tip."
        }
        """

        prompt_parts = [
            prompt_text,
            {'mime_type': mime_type, 'data': file_content}
        ]

        response = model.generate_content(prompt_parts)
        ai_response_text = response.text

        # Use a regex to extract only the JSON part from the response
        json_match = re.search(r'\{.*\}', ai_response_text, re.DOTALL)
        if json_match:
            json_string = json_match.group(0)
            ai_response_json = json.loads(json_string)

            # Store the analysis in Firestore
            app_id = os.getenv("APP_ID", "default-app-id")
            doc_ref = db.collection(f'artifacts/{app_id}/users/{user_id}/analyses').document()
            doc_ref.set({
                'file_name': file.filename,
                'file_type': file.mimetype,
                'analysis_result': ai_response_json,
                'timestamp': firestore.SERVER_TIMESTAMP
            })

            return jsonify({"result": ai_response_json})
        else:
            return jsonify({"error": f"AI response was not in a valid JSON format. Raw response: {ai_response_text}"}), 500

    except Exception as e:
        print(f"Error processing AI response: {e}")
        return jsonify({"error": f"An error occurred: {e}"}), 500

@app.route('/chat', methods=['POST'])
def chat():
    """
    Handles chatbot queries for general legal terms and uploaded documents.
    """
    try:
        data = request.json
        user_id = request.headers.get('Authorization')
        if not user_id:
            return jsonify({"error": "User authentication failed."}), 401

        user_query = data.get('query', '')
        
        # This prompt is for a general chatbot with some persona
        prompt = f"""
        You are a supportive and knowledgeable AI assistant named "MyVakeel" who helps people understand legal terms.
        Answer the following question simply and practically. Do not give any legal advice. Always include a disclaimer.

        User query: {user_query}
        """

        response = model.generate_content(prompt)
        ai_response_text = response.text
        
        return jsonify({"response": ai_response_text})
    
    except Exception as e:
        print(f"Chatbot error: {e}")
        return jsonify({"error": f"An error occurred in the chatbot: {e}"}), 500

# --- RUN THE SERVER ---
if __name__ == '__main__':
    app.run(debug=True)
