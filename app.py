from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import re
import firebase_admin
from firebase_admin import credentials, firestore, storage
import uuid
import logging
from datetime import datetime
import mimetypes
import base64

# --- SETUP ---

# Configure logging for better debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
api_key = os.getenv("API_KEY")

if not api_key:
    logger.error("API_KEY not found in environment variables")
    raise ValueError("API_KEY is required")

genai.configure(api_key=api_key)

app = Flask(__name__)
CORS(app)

# AI model configuration
model = genai.GenerativeModel('gemini-2.0-flash-exp')

# Global variables for Firebase
db = None
bucket = None

# --- Firebase Admin SDK Setup ---
def initialize_firebase():
    global db, bucket
    
    if not firebase_admin._apps:
        try:
            service_account_info_str = os.getenv("FIREBASE_ADMIN_SDK")
            if service_account_info_str:
                service_account_info = json.loads(service_account_info_str)
                cred = credentials.Certificate(service_account_info)
                
                storage_bucket = os.getenv('FIREBASE_STORAGE_BUCKET')
                if storage_bucket:
                    firebase_admin.initialize_app(cred, {'storageBucket': storage_bucket})
                    bucket = storage.bucket()
                else:
                    firebase_admin.initialize_app(cred)
                    
                db = firestore.client()
                logger.info("Firebase initialized successfully")
                return True
            else:
                logger.warning("FIREBASE_ADMIN_SDK not found. Database features will be limited.")
                return False
                
        except Exception as e:
            logger.error(f"Firebase initialization error: {e}")
            return False
    else:
        db = firestore.client()
        if os.getenv('FIREBASE_STORAGE_BUCKET'):
            bucket = storage.bucket()
        return True

firebase_available = initialize_firebase()

# --- HELPER FUNCTIONS ---

def upload_file_to_storage(file_content, filename, user_email):
    """Upload file to Firebase Storage"""
    if not bucket:
        return None
    
    try:
        # Create unique filename
        file_extension = filename.split('.')[-1] if '.' in filename else ''
        unique_filename = f"{user_email}/{uuid.uuid4()}.{file_extension}"
        
        # Upload to Firebase Storage
        blob = bucket.blob(unique_filename)
        blob.upload_from_string(file_content)
        blob.make_public()
        
        return {
            'storage_path': unique_filename,
            'public_url': blob.public_url
        }
    except Exception as e:
        logger.error(f"File upload error: {e}")
        return None

def save_analysis_to_db(user_email, filename, file_type, analysis_result, file_info=None):
    """Save analysis results to Firestore"""
    if not db:
        return None
    
    try:
        doc_data = {
            'user_email': user_email,
            'file_name': filename,
            'file_type': file_type,
            'analysis_result': analysis_result,
            'created_at': firestore.SERVER_TIMESTAMP,
            'analysis_id': str(uuid.uuid4())
        }
        
        if file_info:
            doc_data.update(file_info)
        
        doc_ref = db.collection('user_analyses').document()
        doc_ref.set(doc_data)
        
        return doc_ref.id
    except Exception as e:
        logger.error(f"Database save error: {e}")
        return None

def get_user_analyses(user_email, limit=10):
    """Get user's previous analyses"""
    if not db:
        return []
    
    try:
        docs = db.collection('user_analyses')\
                .where('user_email', '==', user_email)\
                .order_by('created_at', direction=firestore.Query.DESCENDING)\
                .limit(limit)\
                .stream()
        
        analyses = []
        for doc in docs:
            data = doc.to_dict()
            data['doc_id'] = doc.id
            analyses.append(data)
        
        return analyses
    except Exception as e:
        logger.error(f"Error fetching user analyses: {e}")
        return []

# --- ROUTES ---

@app.route('/')
def index():
    """Homepage"""
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
@app.route('/register', methods=['POST'])  # Add fallback route
def register_user():
    """Register or login user with email"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({"error": "Email is required"}), 400
        
        # Simple email validation
        if '@' not in email or '.' not in email.split('@')[1]:
            return jsonify({"error": "Please enter a valid email address"}), 400
        
        # Check if user exists in database
        user_doc = None
        if db:
            try:
                user_ref = db.collection('users').document(email)
                user_doc = user_ref.get()
                
                if not user_doc.exists:
                    # Create new user
                    user_ref.set({
                        'email': email,
                        'created_at': firestore.SERVER_TIMESTAMP,
                        'last_login': firestore.SERVER_TIMESTAMP
                    })
                else:
                    # Update last login
                    user_ref.update({'last_login': firestore.SERVER_TIMESTAMP})
                    
            except Exception as e:
                logger.error(f"User registration error: {e}")
        
        return jsonify({
            "success": True,
            "email": email,
            "message": "Successfully logged in!"
        })
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({"error": "Registration failed"}), 500

@app.route('/api/user-history/<email>')
@app.route('/user-history/<email>')  # Add fallback route
def get_user_history(email):
    """Get user's analysis history"""
    try:
        analyses = get_user_analyses(email)
        return jsonify({"analyses": analyses})
    except Exception as e:
        logger.error(f"History fetch error: {e}")
        return jsonify({"error": "Failed to fetch history"}), 500

@app.route('/api/analyze-file', methods=['POST'])
@app.route('/analyze-file', methods=['POST'])  # Add fallback route
def analyze_uploaded_file():
    """Analyze uploaded file with user authentication"""
    try:
        # Get user email from headers
        user_email = request.headers.get('User-Email')
        if not user_email:
            return jsonify({"error": "User authentication required for file analysis"}), 401
        
        file = request.files.get('file')
        if not file or file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Validate file type
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg', 'text/plain']
        if file.mimetype not in allowed_types:
            return jsonify({"error": f"Unsupported file type. Please upload PDF, image, or text files."}), 400
        
        # Check file size (10MB limit)
        file_content = file.read()
        if len(file_content) > 10 * 1024 * 1024:
            return jsonify({"error": "File too large. Maximum size is 10MB."}), 400
        
        # Upload file to storage
        file_info = upload_file_to_storage(file_content, file.filename, user_email)
        
        # Analyze document with AI
        analysis_result = analyze_document_with_ai(file_content, file.mimetype, file.filename)
        
        if analysis_result.get('error'):
            return jsonify(analysis_result), 500
        
        # Save to database
        doc_id = save_analysis_to_db(
            user_email, 
            file.filename, 
            file.mimetype, 
            analysis_result,
            file_info
        )
        
        # Add visual data for frontend
        visual_data = generate_visual_representations(analysis_result)
        analysis_result.update(visual_data)
        
        return jsonify({
            "success": True,
            "result": analysis_result,
            "doc_id": doc_id,
            "message": "Document analyzed and saved successfully!"
        })
        
    except Exception as e:
        logger.error(f"File analysis error: {e}")
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

@app.route('/api/analyze-text', methods=['POST'])
@app.route('/analyze-text', methods=['POST'])  # Add fallback route
def analyze_text_input():
    """Analyze text input (with or without login)"""
    try:
        data = request.json
        text_content = data.get('text', '').strip()
        user_email = request.headers.get('User-Email')  # Optional
        
        if not text_content:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text_content) > 50000:  # 50k character limit
            return jsonify({"error": "Text too long. Please limit to 50,000 characters."}), 400
        
        # Analyze text with AI
        analysis_result = analyze_text_with_ai(text_content)
        
        if analysis_result.get('error'):
            return jsonify(analysis_result), 500
        
        # Save to database if user is logged in
        doc_id = None
        if user_email and firebase_available:
            doc_id = save_analysis_to_db(
                user_email,
                "Text Analysis",
                "text/plain",
                analysis_result
            )
        
        # Add visual data
        visual_data = generate_visual_representations(analysis_result)
        analysis_result.update(visual_data)
        
        return jsonify({
            "success": True,
            "result": analysis_result,
            "doc_id": doc_id
        })
        
    except Exception as e:
        logger.error(f"Text analysis error: {e}")
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

@app.route('/api/chat', methods=['POST'])
@app.route('/chat', methods=['POST'])  # Add fallback route
def chat():
    """General chatbot for questions and explanations"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        user_query = data.get('query', '').strip()
        if not user_query:
            return jsonify({"error": "No question provided"}), 400
        
        # Generate AI response
        prompt = f"""
        You are MyVakeel, a friendly and knowledgeable AI assistant specializing in legal document simplification.
        
        Your role is to:
        1. Explain legal terms in simple language
        2. Help users understand clauses and provisions
        3. Provide general guidance (not legal advice)
        4. Answer questions about insurance, contracts, and legal documents
        5. Summarize articles, clauses, or terms when asked
        6. Provide risk analysis tips
        
        Always include a brief disclaimer that you don't provide legal advice.
        Keep responses conversational, helpful, and under 300 words.
        Use emojis occasionally to make responses friendly.
        
        User Question: {user_query}
        """
        
        try:
            response = model.generate_content(prompt)
            ai_response = response.text
        except Exception as ai_error:
            logger.error(f"AI chat error: {ai_error}")
            return jsonify({"error": "Failed to generate response. Please try again."}), 500
        
        return jsonify({
            "response": ai_response,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"error": f"Chat failed: {str(e)}"}), 500

def analyze_document_with_ai(file_content, mime_type, filename):
    """Analyze document using AI"""
    try:
        prompt = """
        You are an expert legal document analyzer. Analyze this document and provide comprehensive insights.
        
        Please provide your analysis in JSON format with these keys:
        
        1. "summary": Array of 3-5 main points about the document
        2. "document_type": What type of document this appears to be
        3. "key_terms": Array of important legal/technical terms with simple explanations
        4. "timeline": Array of important dates, deadlines, or time-sensitive items
        5. "risks": Array of potential concerns or risks with explanations
        6. "dependencies": Array of relationships between different sections/concepts
        7. "tip": One practical tip for understanding this type of document
        8. "important_clauses": Array of the most critical clauses to pay attention to
        
        Make all explanations simple and accessible to non-lawyers.
        Focus on practical implications for the user.
        
        Return only valid JSON, no additional text.
        """
        
        prompt_parts = [prompt, {'mime_type': mime_type, 'data': file_content}]
        
        response = model.generate_content(prompt_parts)
        ai_response_text = response.text.strip()
        
        # Parse JSON response
        try:
            # Try direct parsing first
            result = json.loads(ai_response_text)
        except json.JSONDecodeError:
            # Fallback to regex extraction
            json_match = re.search(r'\{.*\}', ai_response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
            else:
                raise ValueError("No valid JSON found in AI response")
        
        return result
        
    except Exception as e:
        logger.error(f"Document AI analysis error: {e}")
        return {"error": f"Failed to analyze document: {str(e)}"}

def analyze_text_with_ai(text_content):
    """Analyze text input using AI"""
    try:
        prompt = f"""
        Analyze the following text and provide insights in JSON format:
        
        Text to analyze: {text_content}
        
        Provide analysis with these keys:
        1. "summary": Main points in 3-5 bullets
        2. "document_type": What type of content this appears to be
        3. "key_terms": Important legal or technical terms with explanations
        4. "risks": Potential concerns or risks
        5. "timeline": Any mentioned dates or deadlines
        6. "dependencies": Relationships between concepts
        7. "tip": Practical advice for this type of content
        8. "important_clauses": Most critical parts to focus on
        
        Make explanations simple and user-friendly.
        Return only valid JSON.
        """
        
        response = model.generate_content(prompt)
        ai_response_text = response.text.strip()
        
        # Parse JSON response
        try:
            result = json.loads(ai_response_text)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', ai_response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
            else:
                raise ValueError("No valid JSON found")
        
        return result
        
    except Exception as e:
        logger.error(f"Text AI analysis error: {e}")
        return {"error": f"Failed to analyze text: {str(e)}"}

def generate_visual_representations(analysis_data):
    """Generate data for visual representations"""
    visual_data = {}
    
    try:
        # Generate mind map data
        if 'dependencies' in analysis_data:
            mind_map_data = []
            for dep in analysis_data.get('dependencies', []):
                if isinstance(dep, dict):
                    mind_map_data.append({
                        'id': dep.get('concept', dep.get('from', 'Unknown')),
                        'label': dep.get('concept', dep.get('from', 'Unknown')),
                        'parent': dep.get('relates_to', dep.get('to', None)),
                        'description': dep.get('relationship', dep.get('description', ''))
                    })
                else:
                    # Handle string format
                    mind_map_data.append({
                        'id': str(dep),
                        'label': str(dep),
                        'parent': None,
                        'description': ''
                    })
            visual_data['mind_map_data'] = mind_map_data
        
        # Generate timeline data
        if 'timeline' in analysis_data:
            timeline_data = []
            for item in analysis_data.get('timeline', []):
                if isinstance(item, dict):
                    timeline_data.append({
                        'date': item.get('date', 'TBD'),
                        'event': item.get('description', item.get('event', 'Important Event')),
                        'importance': item.get('importance', 'medium')
                    })
                else:
                    # Handle string format
                    timeline_data.append({
                        'date': 'TBD',
                        'event': str(item),
                        'importance': 'medium'
                    })
            visual_data['timeline_data'] = timeline_data
        
        # Generate flowchart data for risks
        if 'risks' in analysis_data:
            flowchart_data = []
            for i, risk in enumerate(analysis_data.get('risks', [])):
                if isinstance(risk, dict):
                    flowchart_data.append({
                        'id': f'risk_{i}',
                        'type': 'risk',
                        'title': risk.get('clause', risk.get('title', f'Risk {i+1}')),
                        'description': risk.get('risk_explanation', risk.get('explanation', 'Potential concern')),
                        'severity': risk.get('severity', 'medium')
                    })
                else:
                    # Handle string format
                    flowchart_data.append({
                        'id': f'risk_{i}',
                        'type': 'risk',
                        'title': f'Risk {i+1}',
                        'description': str(risk),
                        'severity': 'medium'
                    })
            visual_data['flowchart_data'] = flowchart_data
        
    except Exception as e:
        logger.error(f"Visual data generation error: {e}")
    
    return visual_data

# --- ADMIN ROUTES ---

@app.route('/admin')
def admin_panel():
    """Admin dashboard"""
    return render_template('admin.html')

@app.route('/admin/users')
def admin_users():
    """Get all users for admin"""
    if not firebase_available or not db:
        return jsonify({"users": [], "error": "Firebase not available"})
    
    try:
        users = []
        docs = db.collection('users').stream()
        for doc in docs:
            user_data = doc.to_dict()
            # Convert timestamps to strings for JSON serialization
            if 'created_at' in user_data and user_data['created_at']:
                user_data['created_at'] = user_data['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if 'last_login' in user_data and user_data['last_login']:
                user_data['last_login'] = user_data['last_login'].strftime('%Y-%m-%d %H:%M:%S')
            users.append(user_data)
        
        return jsonify({"users": users})
    except Exception as e:
        logger.error(f"Admin users error: {e}")
        return jsonify({"users": [], "error": str(e)})

@app.route('/admin/analyses')
def admin_analyses():
    """Get all analyses for admin"""
    if not firebase_available or not db:
        return jsonify({"analyses": [], "error": "Firebase not available"})
    
    try:
        analyses = []
        docs = db.collection('user_analyses').limit(50).stream()
        for doc in docs:
            analysis_data = doc.to_dict()
            analysis_data['doc_id'] = doc.id
            # Convert timestamps
            if 'created_at' in analysis_data and analysis_data['created_at']:
                analysis_data['created_at'] = analysis_data['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            analyses.append(analysis_data)
        
        return jsonify({"analyses": analyses})
    except Exception as e:
        logger.error(f"Admin analyses error: {e}")
        return jsonify({"analyses": [], "error": str(e)})

@app.route('/api/health')
@app.route('/health')  # Add fallback route
def health_check():
    return jsonify({
        "status": "healthy",
        "firebase_available": firebase_available,
        "storage_available": bucket is not None,
        "ai_configured": bool(api_key)
    })

@app.route('/api/test-db')
def test_database():
    """Test database connection and create sample data"""
    if not firebase_available or not db:
        return jsonify({"error": "Firebase not available"}), 500
    
    try:
        # Test writing to database
        test_user = {
            'email': 'test@example.com',
            'created_at': firestore.SERVER_TIMESTAMP,
            'last_login': firestore.SERVER_TIMESTAMP,
            'test_user': True
        }
        
        user_ref = db.collection('users').document('test@example.com')
        user_ref.set(test_user)
        
        # Test analysis data
        test_analysis = {
            'user_email': 'test@example.com',
            'file_name': 'test_document.pdf',
            'file_type': 'application/pdf',
            'analysis_result': {
                'summary': ['This is a test document', 'Created for testing purposes', 'Shows database connectivity'],
                'risks': [{'clause': 'Test clause', 'risk_explanation': 'This is a test risk for demonstration'}],
                'tip': 'This is a test tip for users to understand the platform',
                'timeline': [{'date': '2024-01-01', 'event': 'Test deadline'}],
                'document_type': 'Test Document'
            },
            'created_at': firestore.SERVER_TIMESTAMP,
            'analysis_id': 'test-analysis-001'
        }
        
        analysis_ref = db.collection('user_analyses').document()
        analysis_ref.set(test_analysis)
        
        return jsonify({
            "success": True,
            "message": "Test data created successfully!",
            "firebase_project": os.getenv('FIREBASE_STORAGE_BUCKET', '').replace('.appspot.com', ''),
            "collections_created": ['users', 'user_analyses']
        })
        
    except Exception as e:
        logger.error(f"Database test error: {e}")
        return jsonify({"error": f"Database test failed: {str(e)}"}), 500

@app.route('/api/view-db')
def view_database():
    """View current database contents"""
    if not firebase_available or not db:
        return jsonify({"error": "Firebase not available"}), 500
    
    try:
        # Get users
        users = []
        user_docs = db.collection('users').limit(10).stream()
        for doc in user_docs:
            user_data = doc.to_dict()
            user_data['doc_id'] = doc.id
            users.append(user_data)
        
        # Get analyses
        analyses = []
        analysis_docs = db.collection('user_analyses').limit(10).stream()
        for doc in analysis_docs:
            analysis_data = doc.to_dict()
            analysis_data['doc_id'] = doc.id
            analyses.append(analysis_data)
        
        return jsonify({
            "users": users,
            "analyses": analyses,
            "total_users": len(users),
            "total_analyses": len(analyses)
        })
        
    except Exception as e:
        logger.error(f"Database view error: {e}")
        return jsonify({"error": f"Database view failed: {str(e)}"}), 500

# --- ERROR HANDLERS ---

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# --- RUN SERVER ---

if __name__ == '__main__':
    # Validate required environment variables
    required_vars = ['API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        exit(1)
    
    logger.info("Starting MyVakeel Enhanced Platform...")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))