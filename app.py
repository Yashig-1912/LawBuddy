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
import hashlib
import secrets
from datetime import datetime, timedelta
import sys

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
model = genai.GenerativeModel('gemini-1.5-flash')

# Global variables for Firebase
db = None
bucket = None

def validate_critical_environment():
    """Validate critical environment variables"""
    errors = []
    
    # Check API Key
    if not api_key:
        errors.append("Missing API_KEY - Required for Google Gemini AI")
    elif len(api_key) < 20:
        errors.append("API_KEY appears to be invalid (too short)")
    
    # Check if model is accessible
    try:
        test_response = model.generate_content("Test")
        logger.info("✅ Gemini AI connection successful")
    except Exception as e:
        errors.append(f"Cannot connect to Gemini AI: {str(e)}")
    
    return errors
def validate_environment():
    """Comprehensive environment validation with helpful error messages"""
    errors = []
    warnings = []
    config_status = {
        'api_key': False,
        'firebase_admin': False,
        'firebase_storage': False,
        'admin_credentials': False
    }
    
    # Check API Key
    api_key = os.getenv("API_KEY")
    if not api_key:
        errors.append("❌ API_KEY is missing - Required for Google Gemini AI")
    elif not api_key.startswith('AI') or len(api_key) < 20:
        warnings.append("⚠️ API_KEY format looks incorrect - Should start with 'AI' and be longer")
    else:
        config_status['api_key'] = True
        logger.info("✅ API_KEY configured")
    
    # Check Firebase Admin SDK
    firebase_admin_sdk = os.getenv("FIREBASE_ADMIN_SDK")
    if not firebase_admin_sdk:
        warnings.append("⚠️ FIREBASE_ADMIN_SDK not set - Database features will be limited")
    else:
        try:
            firebase_config = json.loads(firebase_admin_sdk)
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if field not in firebase_config]
            
            if missing_fields:
                errors.append(f"❌ FIREBASE_ADMIN_SDK missing fields: {', '.join(missing_fields)}")
            else:
                config_status['firebase_admin'] = True
                logger.info("✅ Firebase Admin SDK configured")
                
        except json.JSONDecodeError:
            errors.append("❌ FIREBASE_ADMIN_SDK is not valid JSON")
        except Exception as e:
            errors.append(f"❌ FIREBASE_ADMIN_SDK validation error: {str(e)}")
    
    # Check Firebase Storage Bucket
    storage_bucket = os.getenv("FIREBASE_STORAGE_BUCKET")
    if not storage_bucket:
        warnings.append("⚠️ FIREBASE_STORAGE_BUCKET not set - File upload features will be limited")
    elif not storage_bucket.endswith('.appspot.com'):
        warnings.append("⚠️ FIREBASE_STORAGE_BUCKET should end with '.appspot.com'")
    else:
        config_status['firebase_storage'] = True
        logger.info("✅ Firebase Storage configured")
    
    # Check Admin Credentials
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")
    admin_secret = os.getenv("ADMIN_SECRET_KEY")
    
    if not admin_username:
        warnings.append("⚠️ ADMIN_USERNAME not set - Using default 'admin'")
    if not admin_password:
        warnings.append("⚠️ ADMIN_PASSWORD not set - Using default (INSECURE!)")
    elif admin_password == 'changeme123' or admin_password == '123456':
        warnings.append("🚨 ADMIN_PASSWORD is using default value - CHANGE IT!")
    if not admin_secret:
        warnings.append("⚠️ ADMIN_SECRET_KEY not set - Using default (INSECURE!)")
    
    if admin_username and admin_password and admin_secret:
        config_status['admin_credentials'] = True
        logger.info("✅ Admin credentials configured")
    
    # Print results
    print("\n" + "="*60)
    print("🔧 MyVakeel Environment Validation Report")
    print("="*60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Configuration Status
    print("📋 Configuration Status:")
    for component, status in config_status.items():
        icon = "✅" if status else "❌"
        print(f"  {icon} {component.replace('_', ' ').title()}")
    print()
    
    # Errors (Critical - will prevent startup)
    if errors:
        print("🚨 CRITICAL ERRORS (Must fix to run):")
        for error in errors:
            print(f"  {error}")
        print()
    
    # Warnings (Important but not blocking)
    if warnings:
        print("⚠️  WARNINGS (Recommended to fix):")
        for warning in warnings:
            print(f"  {warning}")
        print()
    
    # Success message or instructions
    if not errors:
        features_count = sum(config_status.values())
        print(f"🎉 Environment validation passed! {features_count}/4 features available")
        if warnings:
            print("💡 Fix warnings above for full functionality")
    else:
        print("❌ Environment validation failed!")
        print("\n📝 Quick Setup Guide:")
        print("1. Copy .env.example to .env")
        print("2. Add your Google Gemini API key to API_KEY")
        print("3. Add Firebase Admin SDK JSON to FIREBASE_ADMIN_SDK")
        print("4. Set secure admin credentials")
        print("\n🔗 See README.md for detailed instructions")
    
    print("="*60 + "\n")
    
    return len(errors) == 0, config_status
def startup_check():
    """Run comprehensive startup checks"""
    print("🚀 Starting MyVakeel Enhanced Platform...")
    
    
    
    # Validate environment
    is_valid, config_status = validate_environment()
    
    if not is_valid:
        print("\n💡 Need help setting up? Check these resources:")
        print("📖 README.md - Complete setup guide")
        print("⚙️  .env.example - Example configuration file")
        print("🌐 https://github.com/your-repo/myvakeel - Documentation")
        print("\n⚠️  Continuing with limited functionality...")
    
    # Test critical components
    test_results = {}
    
    # Test AI Connection
    if config_status['api_key']:
        try:
            genai.configure(api_key=os.getenv("API_KEY"))
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            test_response = model.generate_content("Test connection")
            test_results['ai'] = True
            logger.info("✅ AI connection test passed")
        except Exception as e:
            test_results['ai'] = False
            logger.warning(f"⚠️ AI connection test failed: {e}")
    
    # Test Firebase Connection
    if config_status['firebase_admin']:
        try:
            if initialize_firebase():
                test_results['firebase'] = True
                logger.info("✅ Firebase connection test passed")
            else:
                test_results['firebase'] = False
        except Exception as e:
            test_results['firebase'] = False
            logger.warning(f"⚠️ Firebase connection test failed: {e}")
    
    return is_valid, config_status, test_results

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

# --- ENHANCED HELPER FUNCTIONS ---

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

def parse_analysis_result(ai_response):
    """Enhanced AI response parsing with better error handling"""
    try:
        # If already a dict, validate and return
        if isinstance(ai_response, dict):
            return validate_and_enhance_analysis(ai_response)
        
        # Clean the response string
        response_text = ai_response.strip()
        
        # Remove markdown code blocks if present
        response_text = re.sub(r'```json\s*', '', response_text)
        response_text = re.sub(r'\s*```', '', response_text)
        
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            result = json.loads(json_str)
            return validate_and_enhance_analysis(result)
        else:
            # If no JSON found, create structured response from text
            return create_fallback_response(response_text)
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return create_fallback_response(ai_response)
    except Exception as e:
        logger.error(f"Analysis parsing error: {e}")
        return create_fallback_response(ai_response)

def validate_and_enhance_analysis(analysis_data):
    """Validate and enhance analysis data structure"""
    enhanced = {
        "summary": [],
        "document_type": "Unknown Document",
        "key_terms": [],
        "timeline": [],
        "risks": [],
        "dependencies": [],
        "tip": "",
        "important_clauses": []
    }
    
    # Process summary with examples and explanations
    if "summary" in analysis_data:
        if isinstance(analysis_data["summary"], list):
            enhanced["summary"] = [
                create_enhanced_summary_point(point, i) 
                for i, point in enumerate(analysis_data["summary"])
            ]
        else:
            enhanced["summary"] = [create_enhanced_summary_point(analysis_data["summary"], 0)]
    
    # Process key terms with proper structure
    if "key_terms" in analysis_data:
        if isinstance(analysis_data["key_terms"], list):
            enhanced["key_terms"] = [
                create_enhanced_term(term) for term in analysis_data["key_terms"]
            ]
        else:
            enhanced["key_terms"] = [create_enhanced_term(analysis_data["key_terms"])]
    
    # Process timeline with proper date formatting
    if "timeline" in analysis_data:
        if isinstance(analysis_data["timeline"], list):
            enhanced["timeline"] = [
                create_enhanced_timeline_item(item) for item in analysis_data["timeline"]
            ]
        else:
            enhanced["timeline"] = [create_enhanced_timeline_item(analysis_data["timeline"])]
    
    # Process risks with severity and explanations
    if "risks" in analysis_data:
        if isinstance(analysis_data["risks"], list):
            enhanced["risks"] = [
                create_enhanced_risk_item(risk) for risk in analysis_data["risks"]
            ]
        else:
            enhanced["risks"] = [create_enhanced_risk_item(analysis_data["risks"])]
    
    # Copy other fields
    for field in ["document_type", "tip", "dependencies", "important_clauses"]:
        if field in analysis_data:
            enhanced[field] = analysis_data[field]
    
    return enhanced

def create_enhanced_summary_point(point, index):
    """Create enhanced summary point with examples and impact"""
    if isinstance(point, dict):
        return {
            "title": point.get("title", f"Key Point {index + 1}"),
            "description": point.get("description", str(point)),
            "example": point.get("example", generate_example_for_point(point)),
            "impact": point.get("impact", generate_impact_for_point(point)),
            "category": determine_category(point)
        }
    else:
        # String point - enhance it
        return {
            "title": f"Key Point {index + 1}",
            "description": str(point),
            "example": generate_example_for_point({"description": str(point)}),
            "impact": generate_impact_for_point({"description": str(point)}),
            "category": "general"
        }

def create_enhanced_term(term):
    """Create enhanced key term with clear explanations"""
    if isinstance(term, dict):
        return {
            "term": term.get("term", term.get("name", "Legal Term")),
            "explanation": term.get("explanation", term.get("description", "Important legal concept")),
            "example": term.get("example", ""),
            "importance": term.get("importance", "medium"),
            "category": determine_term_category(term)
        }
    else:
        return {
            "term": str(term),
            "explanation": f"Important legal concept: {str(term)}",
            "example": "",
            "importance": "medium",
            "category": "general"
        }

def create_enhanced_timeline_item(item):
    """Create enhanced timeline item with proper formatting"""
    if isinstance(item, dict):
        return {
            "date": item.get("date", "Important Date"),
            "event": item.get("event", item.get("description", "Important milestone")),
            "action_required": item.get("action_required", "Review this date"),
            "importance": item.get("importance", "medium"),
            "category": determine_timeline_category(item)
        }
    else:
        return {
            "date": "Important Date",
            "event": str(item),
            "action_required": "Review this information",
            "importance": "medium",
            "category": "general"
        }

def create_enhanced_risk_item(risk):
    """Create enhanced risk item with severity and explanations"""
    if isinstance(risk, dict):
        return {
            "title": risk.get("title", risk.get("clause", "Potential Risk")),
            "description": risk.get("risk_explanation", risk.get("explanation", risk.get("description", "Requires attention"))),
            "severity": risk.get("severity", "medium"),
            "impact": risk.get("impact", "May affect your rights or obligations"),
            "mitigation": risk.get("mitigation", "Consider legal review"),
            "category": determine_risk_category(risk)
        }
    else:
        return {
            "title": "Potential Risk",
            "description": str(risk),
            "severity": "medium",
            "impact": "May affect your rights or obligations",
            "mitigation": "Consider legal review",
            "category": "general"
        }

def generate_example_for_point(point):
    """Generate contextual examples for summary points"""
    description = str(point.get("description", point)).lower()
    
    if "employment" in description or "job" in description:
        return "For instance, if you're a software developer, this means you'll have specific duties, work hours, and performance expectations."
    elif "salary" in description or "payment" in description:
        return "For example, if your annual salary is $80,000, you'll receive approximately $6,667 monthly before taxes and deductions."
    elif "contract" in description or "agreement" in description:
        return "This creates a legal obligation - like signing a lease for an apartment, both parties must fulfill their commitments."
    elif "termination" in description or "end" in description:
        return "Similar to a rental lease, there are specific conditions and notice periods for ending the relationship."
    else:
        return "This is an important provision that affects your rights and responsibilities under this agreement."

def generate_impact_for_point(point):
    """Generate practical impact explanations"""
    description = str(point.get("description", point)).lower()
    
    if "probation" in description:
        return "During probation, job security is lower, but it's also your chance to evaluate if the role is right for you."
    elif "benefits" in description:
        return "These benefits can add significant value to your total compensation package, potentially worth thousands per year."
    elif "non-disclosure" in description or "nda" in description:
        return "Violating this could result in legal action and damage to your professional reputation."
    elif "stock" in description or "equity" in description:
        return "If the company grows successfully, this equity could become quite valuable over time."
    else:
        return "Understanding this provision helps you make informed decisions about your commitments."

def determine_category(item):
    """Determine category for better organization"""
    text = str(item).lower()
    if any(word in text for word in ["salary", "payment", "money", "compensation"]):
        return "financial"
    elif any(word in text for word in ["benefits", "insurance", "vacation", "pto"]):
        return "benefits"
    elif any(word in text for word in ["termination", "end", "quit", "fire"]):
        return "termination"
    elif any(word in text for word in ["duties", "responsibilities", "work", "job"]):
        return "obligations"
    else:
        return "general"

def determine_term_category(term):
    """Categorize legal terms"""
    text = str(term).lower()
    if any(word in text for word in ["contract", "agreement", "binding"]):
        return "contract"
    elif any(word in text for word in ["confidential", "nda", "disclosure"]):
        return "confidentiality"
    elif any(word in text for word in ["arbitration", "dispute", "court"]):
        return "dispute_resolution"
    elif any(word in text for word in ["stock", "equity", "options"]):
        return "compensation"
    else:
        return "general"

def determine_timeline_category(item):
    """Categorize timeline items"""
    text = str(item).lower()
    if any(word in text for word in ["start", "begin", "commence"]):
        return "start"
    elif any(word in text for word in ["end", "expire", "terminate"]):
        return "end"
    elif any(word in text for word in ["review", "evaluation", "assessment"]):
        return "review"
    elif any(word in text for word in ["deadline", "due", "submit"]):
        return "deadline"
    else:
        return "milestone"

def determine_risk_category(risk):
    """Categorize risk items"""
    text = str(risk).lower()
    if any(word in text for word in ["financial", "money", "payment", "salary"]):
        return "financial"
    elif any(word in text for word in ["legal", "lawsuit", "court", "arbitration"]):
        return "legal"
    elif any(word in text for word in ["confidential", "proprietary", "trade secret"]):
        return "confidentiality"
    elif any(word in text for word in ["termination", "firing", "quit"]):
        return "employment"
    else:
        return "general"

def create_fallback_response(raw_text):
    """Create structured response when AI returns unstructured text"""
    logger.warning("Creating fallback response for unstructured AI output")
    
    # Extract key information from raw text
    text = str(raw_text)
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    
    fallback = {
        "summary": [
            {
                "title": "Document Analysis",
                "description": sentences[0] if sentences else "Document analysis completed",
                "example": "This analysis was generated from the document content",
                "impact": "Review the key points below for important information",
                "category": "general"
            }
        ],
        "document_type": "Legal Document",
        "key_terms": [
            {
                "term": "Important Terms",
                "explanation": "Key legal terms and concepts found in the document",
                "example": "Terms that affect your rights and obligations",
                "importance": "high",
                "category": "general"
            }
        ],
        "timeline": [
            {
                "date": "Review Required",
                "event": "Document requires careful review",
                "action_required": "Read through all sections carefully",
                "importance": "high",
                "category": "review"
            }
        ],
        "risks": [
            {
                "title": "General Legal Risk",
                "description": "This document contains legal obligations that should be reviewed",
                "severity": "medium",
                "impact": "May affect your legal rights",
                "mitigation": "Consider consulting with a legal professional",
                "category": "legal"
            }
        ],
        "dependencies": ["Document sections may be interconnected"],
        "tip": "Always read legal documents carefully and consider getting professional advice for complex agreements.",
        "important_clauses": ["All clauses in this document should be considered important until reviewed by a professional"]
    }
    
    return fallback

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
@app.route('/register', methods=['POST'])
def register_user():
    """Register or login user with email"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({"error": "Email is required"}), 400
        
        if '@' not in email or '.' not in email.split('@')[1]:
            return jsonify({"error": "Please enter a valid email address"}), 400
        
        user_doc = None
        if db:
            try:
                user_ref = db.collection('users').document(email)
                user_doc = user_ref.get()
                
                if not user_doc.exists:
                    user_ref.set({
                        'email': email,
                        'created_at': firestore.SERVER_TIMESTAMP,
                        'last_login': firestore.SERVER_TIMESTAMP
                    })
                else:
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
@app.route('/user-history/<email>')
def get_user_history(email):
    """Get user's analysis history"""
    try:
        analyses = get_user_analyses(email)
        return jsonify({"analyses": analyses})
    except Exception as e:
        logger.error(f"History fetch error: {e}")
        return jsonify({"error": "Failed to fetch history"}), 500

@app.route('/api/analyze-file', methods=['POST'])
@app.route('/analyze-file', methods=['POST'])
def analyze_uploaded_file():
    try:
        user_email = request.headers.get('User-Email')
        if not user_email:
            return safe_json_response({"error": "User authentication required"}, 401)
        
        file = request.files.get('file')
        if not file or file.filename == '':
            return safe_json_response({"error": "No file selected"}, 400)
        
        # Basic file validation
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'text/plain']
        if file.mimetype not in allowed_types:
            return safe_json_response({
                "error": "Unsupported file type",
                "supported": ["PDF", "JPEG", "PNG", "TXT"],
                "received": file.mimetype
            }, 400)
        
        # Read and analyze file
        try:
            file_content = file.read()
        except Exception as e:
            logger.error(f"File read error: {e}")
            return safe_json_response({"error": "Failed to read file content"}, 400)
            
        if len(file_content) > 10 * 1024 * 1024:  # 10MB limit
            return safe_json_response({"error": "File too large (max 10MB)"}, 400)
        
        # Analyze with AI
        try:
            analysis_result = analyze_document_with_ai(file_content, file.mimetype, file.filename)
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return safe_json_response({
                "error": "Analysis failed", 
                "details": str(e),
                "suggestion": "Try uploading a clearer scan or different format"
            }, 500)
        
        if analysis_result.get('error'):
            return safe_json_response({
                "error": "Analysis failed", 
                "details": analysis_result['error']
            }, 500)
        
        # Save to database if available
        doc_id = None
        if db:
            try:
                doc_id = save_analysis_to_db(user_email, file.filename, file.mimetype, analysis_result)
            except Exception as e:
                logger.error(f"Database save error: {e}")
                # Don't fail the request if DB save fails
                pass
        
        return safe_json_response({
            "success": True,
            "result": analysis_result,
            "doc_id": doc_id,
            "file_size": f"{len(file_content)/1024:.1f}KB",
            "message": "Analysis completed successfully"
        })
        
    except Exception as e:
        logger.error(f"File analysis error: {e}")
        return safe_json_response({
            "error": "Internal server error", 
            "details": str(e),
            "suggestion": "Please try again or contact support"
        }, 500)
        
@app.route('/api/analyze-text', methods=['POST'])
@app.route('/analyze-text', methods=['POST'])
def analyze_text_input():
    """Analyze text input with enhanced parsing"""
    try:
        data = request.get_json()
        if not data:
            return safe_json_response({"error": "No JSON data received"}, 400)
            
        text_content = data.get('text', '').strip()
        user_email = request.headers.get('User-Email')
        
        if not text_content:
            return safe_json_response({"error": "No text provided"}, 400)
        
        if len(text_content) > 50000:
            return safe_json_response({
                "error": "Text too long",
                "limit": "50,000 characters maximum",
                "current": len(text_content),
                "suggestion": "Please split your text into smaller sections"
            }, 400)
        
        logger.info(f"Processing text analysis ({len(text_content)} chars) for user: {user_email or 'anonymous'}")
        
        # Analyze text with AI
        try:
            analysis_result = analyze_text_with_ai(text_content)
        except Exception as e:
            logger.error(f"AI text analysis error: {e}")
            return safe_json_response({
                "error": "Analysis failed",
                "details": str(e),
                "suggestion": "Try simplifying your text or breaking it into smaller sections"
            }, 500)
        
        if analysis_result.get('error'):
            return safe_json_response({
                "error": "Analysis failed",
                "details": analysis_result['error'],
                "suggestion": "Try breaking the text into smaller sections"
            }, 500)
        
        # Save to database if user is logged in
        doc_id = None
        if user_email and db:
            try:
                doc_id = save_analysis_to_db(
                    user_email,
                    "Text Analysis",
                    "text/plain",
                    analysis_result
                )
            except Exception as e:
                logger.error(f"Database save error: {e}")
                # Don't fail the request if DB save fails
                pass
        
        return safe_json_response({
            "success": True,
            "result": analysis_result,
            "doc_id": doc_id,
            "text_length": len(text_content)
        })
        
    except Exception as e:
        logger.error(f"Text analysis error: {e}")
        return safe_json_response({
            "error": "Analysis failed",
            "details": str(e),
            "suggestion": "Please try again with simpler text"
        }, 500)

@app.route('/api/chat', methods=['POST'])
@app.route('/chat', methods=['POST'])
def chat():
    """Enhanced chatbot with better responses"""
    try:
        data = request.get_json()
        if not data:
            return safe_json_response({"error": "No JSON data received"}, 400)
        
        user_query = data.get('query', '').strip()
        if not user_query:
            return safe_json_response({"error": "No question provided"}, 400)
        
        # Enhanced prompt for better responses
        prompt = f"""
        You are MyVakeel, a friendly and knowledgeable AI legal assistant. You specialize in making legal documents and concepts easy to understand.
        
        Your expertise includes:
        - Explaining legal terms in simple, everyday language
        - Breaking down complex contracts and agreements
        - Identifying potential risks and red flags
        - Providing practical advice for document review
        - Helping users understand their rights and obligations
        
        Guidelines for your responses:
        - Use clear, conversational language (avoid legal jargon)
        - Provide practical examples when possible
        - Keep responses under 250 words
        - Always include the disclaimer about not providing legal advice
        - If asked about specific legal situations, suggest consulting a lawyer
        
        User Question: {user_query}
        
        Please provide a helpful, clear response that educates the user while being conversational and accessible.
        """
        
        try:
            response = model.generate_content(prompt)
            ai_response = response.text
            
            # Add standard disclaimer if not already present
            if "legal advice" not in ai_response.lower():
                ai_response += "\n\n⚖️ *Disclaimer: This is general information, not legal advice. For specific legal matters, please consult a qualified attorney.*"
                
        except Exception as ai_error:
            logger.error(f"AI chat error: {ai_error}")
            return safe_json_response({
                "error": "AI service temporarily unavailable",
                "suggestion": "Please try again in a few moments",
                "fallback_response": "I'm having trouble connecting to my AI service right now. Please try asking your question again, or feel free to upload a document for analysis instead."
            }, 500)
        
        return safe_json_response({
            "response": ai_response,
            "timestamp": datetime.now().isoformat(),
            "query_length": len(user_query)
        })
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return safe_json_response({
            "error": "Chat service failed",
            "details": str(e),
            "suggestion": "Please try again or refresh the page"
        }, 500)

def analyze_document_with_ai(file_content, mime_type, filename):
    """Enhanced document analysis with structured prompts"""
    try:
        # Check if API key is configured
        if not api_key:
            return {
                "error": "AI service not configured - API_KEY missing",
                "suggestion": "Please check your environment variables"
            }
            
        # Enhanced prompt for better structured output
        prompt = """
        You are an expert legal document analyzer. Analyze this document and provide comprehensive insights in a structured format.
        
        Please provide your analysis as a JSON object with the following structure:
        
        {
            "summary": [
                {
                    "title": "Brief title of key point",
                    "description": "Clear explanation in simple language",
                    "example": "Real-world example of what this means",
                    "impact": "How this affects the user practically"
                }
            ],
            "document_type": "Type of document (e.g., Employment Contract, Lease Agreement)",
            "key_terms": [
                {
                    "term": "Legal term name",
                    "explanation": "Simple explanation of what it means",
                    "importance": "high/medium/low",
                    "example": "Practical example"
                }
            ],
            "timeline": [
                {
                    "date": "Specific date or time period",
                    "event": "What happens on this date",
                    "action_required": "What the user needs to do"
                }
            ],
            "risks": [
                {
                    "title": "Name of the risk",
                    "description": "Clear explanation of the potential problem",
                    "severity": "high/medium/low",
                    "mitigation": "How to address this risk"
                }
            ],
            "important_clauses": [
                "Most critical clauses that need attention"
            ],
            "tip": "One practical tip for understanding this type of document"
        }
        
        Focus on:
        - Using simple, non-legal language
        - Providing practical examples
        - Explaining financial implications clearly
        - Highlighting time-sensitive items
        - Identifying potential problems
        
        Return only valid JSON with no additional text or formatting.
        """
        
        try:
            prompt_parts = [prompt, {'mime_type': mime_type, 'data': file_content}]
            response = model.generate_content(prompt_parts)
            ai_response_text = response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return {
                "error": f"AI service error: {str(e)}",
                "suggestion": "Please try again in a few moments"
            }
        
        logger.info(f"AI response received for {filename} ({len(ai_response_text)} chars)")
        
        # Parse and enhance the response
        result = parse_analysis_result(ai_response_text)
        
        return result
        
    except Exception as e:
        logger.error(f"Document AI analysis error: {e}")
        return {
            "error": f"Failed to analyze document: {str(e)}",
            "suggestion": "Try uploading a clearer scan or different format",
            "filename": filename
        }

def analyze_text_with_ai(text_content):
    """Enhanced text analysis with better prompts"""
    try:
        # Check if API key is configured
        if not api_key:
            return {
                "error": "AI service not configured - API_KEY missing",
                "suggestion": "Please check your environment variables"
            }
            
        prompt = f"""
        Analyze the following legal text and provide structured insights. Focus on making complex legal language accessible to everyday people.
        
        Text to analyze: {text_content}
        
        Provide analysis in JSON format with this structure:
        {{
            "summary": [
                {{
                    "title": "Key point title",
                    "description": "Simple explanation",
                    "example": "Real-world example",
                    "impact": "Practical implications"
                }}
            ],
            "document_type": "Type of legal content",
            "key_terms": [
                {{
                    "term": "Legal term",
                    "explanation": "Simple definition",
                    "importance": "high/medium/low"
                }}
            ],
            "risks": [
                {{
                    "title": "Potential risk",
                    "description": "What could go wrong",
                    "severity": "high/medium/low",
                    "mitigation": "How to handle it"
                }}
            ],
            "timeline": [
                {{
                    "date": "Important date/deadline",
                    "event": "What happens",
                    "action_required": "What to do"
                }}
            ],
            "important_clauses": ["Critical points to focus on"],
            "tip": "Practical advice for this type of content"
        }}
        
        Make all explanations clear and accessible to non-lawyers. Include practical examples and real-world implications.
        Return only valid JSON.
        """
        
        try:
            response = model.generate_content(prompt)
            ai_response_text = response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return {
                "error": f"AI service error: {str(e)}",
                "suggestion": "Please try again in a few moments"
            }
        
        logger.info(f"AI text analysis response received ({len(ai_response_text)} chars)")
        
        # Parse and enhance the response
        result = parse_analysis_result(ai_response_text)
        
        return result
        
    except Exception as e:
        logger.error(f"Text AI analysis error: {e}")
        return {
            "error": f"Failed to analyze text: {str(e)}",
            "suggestion": "Try breaking the text into smaller sections"
        }
def generate_visual_representations(analysis_data):
    """Generate enhanced visual data for frontend"""
    visual_data = {}
    
    try:
        # Generate enhanced mind map data
        if 'dependencies' in analysis_data and analysis_data['dependencies']:
            mind_map_data = []
            dependencies = analysis_data['dependencies']
            
            if isinstance(dependencies, list):
                for i, dep in enumerate(dependencies):
                    if isinstance(dep, dict):
                        mind_map_data.append({
                            'id': f"node_{i}",
                            'label': dep.get('concept', dep.get('from', f'Node {i+1}')),
                            'description': dep.get('relationship', dep.get('description', '')),
                            'category': dep.get('category', 'general')
                        })
                    else:
                        mind_map_data.append({
                            'id': f"node_{i}",
                            'label': str(dep)[:30] + ('...' if len(str(dep)) > 30 else ''),
                            'description': str(dep),
                            'category': 'general'
                        })
            
            visual_data['mind_map_data'] = mind_map_data
        
        # Generate enhanced timeline data
        if 'timeline' in analysis_data and analysis_data['timeline']:
            timeline_data = []
            for item in analysis_data['timeline']:
                if isinstance(item, dict):
                    timeline_data.append({
                        'date': item.get('date', 'Important Date'),
                        'event': item.get('event', item.get('description', 'Key milestone')),
                        'action_required': item.get('action_required', 'Review required'),
                        'importance': item.get('importance', 'medium'),
                        'category': item.get('category', 'general')
                    })
                else:
                    timeline_data.append({
                        'date': 'Important Date',
                        'event': str(item),
                        'action_required': 'Review this item',
                        'importance': 'medium',
                        'category': 'general'
                    })
            
            visual_data['timeline_data'] = timeline_data
        
        # Generate enhanced risk analysis data
        if 'risks' in analysis_data and analysis_data['risks']:
            risk_chart_data = []
            severity_counts = {'high': 0, 'medium': 0, 'low': 0}
            
            for risk in analysis_data['risks']:
                if isinstance(risk, dict):
                    severity = risk.get('severity', 'medium').lower()
                    if severity in severity_counts:
                        severity_counts[severity] += 1
                    
                    risk_chart_data.append({
                        'title': risk.get('title', 'Risk'),
                        'severity': severity,
                        'category': risk.get('category', 'general')
                    })
                else:
                    severity_counts['medium'] += 1
                    risk_chart_data.append({
                        'title': str(risk)[:50],
                        'severity': 'medium',
                        'category': 'general'
                    })
            
            visual_data['risk_chart_data'] = risk_chart_data
            visual_data['risk_summary'] = severity_counts
        
        # Generate key terms visualization
        if 'key_terms' in analysis_data and analysis_data['key_terms']:
            terms_data = []
            importance_counts = {'high': 0, 'medium': 0, 'low': 0}
            
            for term in analysis_data['key_terms']:
                if isinstance(term, dict):
                    importance = term.get('importance', 'medium').lower()
                    if importance in importance_counts:
                        importance_counts[importance] += 1
                    
                    terms_data.append({
                        'term': term.get('term', 'Legal Term'),
                        'importance': importance,
                        'category': term.get('category', 'general')
                    })
                else:
                    importance_counts['medium'] += 1
                    terms_data.append({
                        'term': str(term),
                        'importance': 'medium',
                        'category': 'general'
                    })
            
            visual_data['terms_data'] = terms_data
            visual_data['terms_summary'] = importance_counts
        
    except Exception as e:
        logger.error(f"Visual data generation error: {e}")
        # Provide fallback visual data
        visual_data = {
            'mind_map_data': [],
            'timeline_data': [],
            'risk_chart_data': [],
            'terms_data': []
        }
    
    return visual_data

# --- VOICE FEATURE ROUTES ---

@app.route('/api/generate-audio', methods=['POST'])
@app.route('/generate-audio', methods=['POST'])
def generate_audio_content():
    """Generate audio-friendly text from analysis results"""
    try:
        data = request.json
        analysis_data = data.get('analysis_data', {})
        language = data.get('language', 'en-US')
        section = data.get('section', 'all')  # all, summary, risks, timeline, terms
        
        audio_text = format_analysis_for_speech(analysis_data, section)
        
        return jsonify({
            "success": True,
            "audio_text": audio_text,
            "language": language,
            "section": section,
            "estimated_duration": estimate_speech_duration(audio_text)
        })
        
    except Exception as e:
        logger.error(f"Audio generation error: {e}")
        return jsonify({
            "error": "Failed to generate audio content",
            "suggestion": "Please try again"
        }), 500

def format_analysis_for_speech(analysis_data, section='all'):
    """Format analysis data for text-to-speech"""
    speech_parts = []
    
    try:
        if section in ['all', 'summary'] and 'summary' in analysis_data:
            speech_parts.append("Document Summary.")
            summary_items = analysis_data['summary']
            if isinstance(summary_items, list):
                for i, item in enumerate(summary_items):
                    if isinstance(item, dict):
                        title = item.get('title', f'Point {i+1}')
                        description = item.get('description', '')
                        speech_parts.append(f"{title}. {description}.")
                    else:
                        speech_parts.append(f"Point {i+1}. {str(item)}.")
        
        if section in ['all', 'risks'] and 'risks' in analysis_data:
            speech_parts.append("Risk Analysis.")
            risks = analysis_data['risks']
            if isinstance(risks, list):
                for risk in risks:
                    if isinstance(risk, dict):
                        title = risk.get('title', 'Risk')
                        description = risk.get('description', '')
                        severity = risk.get('severity', 'medium')
                        speech_parts.append(f"{severity} severity risk: {title}. {description}.")
                    else:
                        speech_parts.append(f"Risk: {str(risk)}.")
        
        if section in ['all', 'timeline'] and 'timeline' in analysis_data:
            speech_parts.append("Important Dates and Timeline.")
            timeline = analysis_data['timeline']
            if isinstance(timeline, list):
                for item in timeline:
                    if isinstance(item, dict):
                        date = item.get('date', 'Important date')
                        event = item.get('event', 'milestone')
                        speech_parts.append(f"{date}: {event}.")
                    else:
                        speech_parts.append(f"Timeline item: {str(item)}.")
        
        if section in ['all', 'terms'] and 'key_terms' in analysis_data:
            speech_parts.append("Key Terms Explained.")
            terms = analysis_data['key_terms']
            if isinstance(terms, list):
                for term in terms:
                    if isinstance(term, dict):
                        term_name = term.get('term', 'Legal term')
                        explanation = term.get('explanation', '')
                        speech_parts.append(f"{term_name}: {explanation}.")
                    else:
                        speech_parts.append(f"Key term: {str(term)}.")
        
        if 'tip' in analysis_data and section in ['all', 'summary']:
            speech_parts.append(f"Pro tip: {analysis_data['tip']}")
        
        # Add disclaimer
        speech_parts.append("Remember, this is general information and not legal advice. For specific legal matters, consult with a qualified attorney.")
        
    except Exception as e:
        logger.error(f"Speech formatting error: {e}")
        return "Analysis completed. Please review the document details on screen."
    
    return " ".join(speech_parts)

def estimate_speech_duration(text):
    """Estimate speech duration in seconds (average 150 words per minute)"""
    word_count = len(text.split())
    duration_minutes = word_count / 150
    return round(duration_minutes * 60, 0)

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
            if 'created_at' in analysis_data and analysis_data['created_at']:
                analysis_data['created_at'] = analysis_data['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            analyses.append(analysis_data)
        
        return jsonify({"analyses": analyses})
    except Exception as e:
        logger.error(f"Admin analyses error: {e}")
        return jsonify({"analyses": [], "error": str(e)})

@app.route('/api/health')
@app.route('/health')
def health_check():
    """Enhanced health check"""
    return jsonify({
        "status": "healthy",
        "firebase_available": firebase_available,
        "storage_available": bucket is not None,
        "ai_configured": bool(api_key),
        "database_connected": db is not None,
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    })

@app.route('/api/test-db')
def test_database():
    """Test database connection with enhanced sample data"""
    if not firebase_available or not db:
        return jsonify({"error": "Firebase not available"}), 500
    
    try:
        # Create enhanced test user
        test_user = {
            'email': 'test@myvakeel.com',
            'created_at': firestore.SERVER_TIMESTAMP,
            'last_login': firestore.SERVER_TIMESTAMP,
            'test_user': True,
            'plan': 'free'
        }
        
        user_ref = db.collection('users').document('test@myvakeel.com')
        user_ref.set(test_user)
        
        # Create enhanced test analysis
        test_analysis = {
            'user_email': 'test@myvakeel.com',
            'file_name': 'sample_employment_contract.pdf',
            'file_type': 'application/pdf',
            'analysis_result': {
                'summary': [
                    {
                        'title': 'Employment Agreement',
                        'description': 'This is a full-time software developer contract with ABC Tech Corp',
                        'example': 'You will work 40 hours per week developing web applications',
                        'impact': 'Creates legal obligation to fulfill job duties and grants employment benefits',
                        'category': 'general'
                    }
                ],
                'risks': [
                    {
                        'title': 'Non-compete clause',
                        'description': 'Cannot work for competitors for 1 year after leaving',
                        'severity': 'medium',
                        'impact': 'Limits future job opportunities in same industry',
                        'mitigation': 'Negotiate shorter period or geographic limits',
                        'category': 'employment'
                    }
                ],
                'key_terms': [
                    {
                        'term': 'At-will employment',
                        'explanation': 'Either party can end employment at any time',
                        'importance': 'high',
                        'category': 'employment'
                    }
                ],
                'timeline': [
                    {
                        'date': '2024-01-15',
                        'event': 'Employment start date',
                        'action_required': 'Complete onboarding paperwork',
                        'importance': 'high',
                        'category': 'start'
                    }
                ],
                'document_type': 'Employment Contract',
                'tip': 'Always negotiate salary and benefits before signing, and understand your termination rights'
            },
            'created_at': firestore.SERVER_TIMESTAMP,
            'analysis_id': 'test-analysis-enhanced-001'
        }
        
        analysis_ref = db.collection('user_analyses').document()
        analysis_ref.set(test_analysis)
        
        return jsonify({
            "success": True,
            "message": "Enhanced test data created successfully!",
            "firebase_project": os.getenv('FIREBASE_STORAGE_BUCKET', '').replace('.appspot.com', ''),
            "collections_created": ['users', 'user_analyses'],
            "features_tested": ['structured_data', 'enhanced_analysis', 'visual_representations']
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
            "total_analyses": len(analyses),
            "database_status": "connected",
            "last_updated": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Database view error: {e}")
        return jsonify({"error": f"Database view failed: {str(e)}"}), 500

@app.route('/api/translate', methods=['POST'])
def translate_text():
    """Translate text between languages"""
    try:
        data = request.json
        text = data.get('text', '')
        source_lang = data.get('source_lang', 'en')
        target_lang = data.get('target_lang', 'en')
        
        if source_lang == target_lang:
            return jsonify({"translated_text": text})
        
        # Simple translation using Google Translate (free tier)
        # Note: For production, use proper Google Translate API
        translated = simple_translate(text, source_lang, target_lang)
        
        return jsonify({
            "success": True,
            "translated_text": translated,
            "source_lang": source_lang,
            "target_lang": target_lang
        })
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return jsonify({"error": "Translation failed", "original_text": text}), 500

def simple_translate(text, source_lang, target_lang):
    """Simple translation function - replace with proper API in production"""
    try:
        # For prototype, we'll use a basic translation
        # In production, integrate with Google Translate API
        
        # Basic legal term translations for demo
        legal_translations = {
            'hi': {
                'contract': 'अनुबंध',
                'agreement': 'समझौता',
                'legal': 'कानूनी',
                'document': 'दस्तावेज़',
                'analysis': 'विश्लेषण'
            }
            # Add more languages and terms
        }
        
        if target_lang in legal_translations:
            for en_term, translated_term in legal_translations[target_lang].items():
                text = text.replace(en_term, f"{en_term} ({translated_term})")
        
        return text
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return text
@app.route('/api/chat', methods=['POST'])
def enhanced_chat():
    """Enhanced chatbot with multi-language support"""
    try:
        data = request.json
        user_query = data.get('query', '').strip()
        user_language = data.get('language', 'en')
        
        if not user_query:
            return jsonify({"error": "No question provided"}), 400
        
        # If not English, translate to English for AI processing
        if user_language != 'en':
            english_query = simple_translate(user_query, user_language, 'en')
        else:
            english_query = user_query
        
        # Enhanced prompt for better multilingual responses
        prompt = f"""
        You are MyVakeel, a friendly AI legal assistant specializing in Indian law.
        
        User's question (in English): {english_query}
        User's preferred language: {user_language}
        
        Provide a helpful response in English first, then if the user's language is not English, 
        provide key legal terms in both English and {user_language}.
        
        Keep responses under 200 words and include relevant emojis.
        Always include the legal disclaimer.
        """
        
        try:
            response = model.generate_content(prompt)
            ai_response = response.text
            
            # Add multilingual legal terms
            if user_language != 'en':
                ai_response = enhance_with_bilingual_terms(ai_response, user_language)
            
            return jsonify({
                "response": ai_response,
                "language": user_language,
                "original_query": user_query,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as ai_error:
            logger.error(f"AI chat error: {ai_error}")
            return jsonify({"error": "AI service temporarily unavailable"}), 500
            
    except Exception as e:
        logger.error(f"Enhanced chat error: {e}")
        return jsonify({"error": "Chat service failed"}), 500

def enhance_with_bilingual_terms(text, target_language):
    """Add bilingual legal terms to response"""
    # Add both English and local language terms
    enhanced_text = text
    
    # Add language-specific enhancements
    if target_language in ['hi', 'ta', 'te', 'bn', 'mr', 'gu', 'kn']:
        enhanced_text += "\n\n📚 *Key terms are provided in both English and your local language for better understanding.*"
    
    return enhanced_text
admin_sessions = {}

def hash_password(password):
    """Hash password with salt"""
    salt = os.getenv('ADMIN_SECRET_KEY', 'default_salt')
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()

def verify_admin_session(session_token):
    """Verify admin session token"""
    if not session_token or session_token not in admin_sessions:
        return False
    
    session = admin_sessions[session_token]
    if datetime.now() > session['expires']:
        del admin_sessions[session_token]
        return False
    
    return True

@app.route('/api/admin-login', methods=['POST'])
def admin_login():
    """Secure admin login endpoint"""
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        # Get credentials from environment
        admin_username = os.getenv('ADMIN_USERNAME', 'admin')
        admin_password_hash = hash_password(os.getenv('ADMIN_PASSWORD', 'changeme123'))
        
        # Verify credentials
        if username == admin_username and hash_password(password) == admin_password_hash:
            # Create session token
            session_token = secrets.token_urlsafe(32)
            expires = datetime.now() + timedelta(hours=2)  # 2-hour session
            
            admin_sessions[session_token] = {
                'username': username,
                'expires': expires,
                'ip': request.remote_addr,
                'created': datetime.now()
            }
            
            logger.info(f"Admin login successful for {username} from {request.remote_addr}")
            
            return jsonify({
                'success': True,
                'session_token': session_token,
                'expires': expires.isoformat(),
                'message': 'Login successful'
            })
        else:
            logger.warning(f"Failed admin login attempt for {username} from {request.remote_addr}")
            return jsonify({
                'success': False,
                'error': 'Invalid credentials'
            }), 401
            
    except Exception as e:
        logger.error(f"Admin login error: {e}")
        return jsonify({
            'success': False,
            'error': 'Login failed'
        }), 500

@app.route('/api/admin-verify', methods=['POST'])
def admin_verify():
    """Verify admin session"""
    try:
        data = request.json
        session_token = data.get('session_token', '')
        
        if verify_admin_session(session_token):
            session = admin_sessions[session_token]
            return jsonify({
                'valid': True,
                'username': session['username'],
                'expires': session['expires'].isoformat()
            })
        else:
            return jsonify({'valid': False}), 401
            
    except Exception as e:
        logger.error(f"Admin verify error: {e}")
        return jsonify({'valid': False}), 500

@app.route('/api/admin-logout', methods=['POST'])
def admin_logout():
    """Admin logout"""
    try:
        data = request.json
        session_token = data.get('session_token', '')
        
        if session_token in admin_sessions:
            del admin_sessions[session_token]
            logger.info("Admin logged out successfully")
        
        return jsonify({'success': True, 'message': 'Logged out successfully'})
        
    except Exception as e:
        logger.error(f"Admin logout error: {e}")
        return jsonify({'success': False, 'error': 'Logout failed'}), 500

# Decorator for protected admin routes
def admin_required(f):
    """Decorator to protect admin routes"""
    def decorated_function(*args, **kwargs):
        session_token = request.headers.get('Admin-Session-Token')
        if not verify_admin_session(session_token):
            return jsonify({'error': 'Admin authentication required'}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Protect existing admin routes
@app.route('/admin/users')
@admin_required
def admin_users_protected():
    """Get all users for admin (protected)"""
    return admin_users()  # Your existing function

@app.route('/admin/analyses')
@admin_required
def admin_analyses_protected():
    """Get all analyses for admin (protected)"""
    return admin_analyses()  # Your existing function
# --- ERROR HANDLERS ---
# ADD this helper function after line 400:
def safe_json_response(data, status=200):
    """Safely return JSON response with error handling"""
    try:
        return jsonify(data), status
    except Exception as e:
        return jsonify({"error": "Response formatting error", "details": str(e)}), 500
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": [
            "/api/analyze-file", "/api/analyze-text", "/api/chat", 
            "/api/register", "/api/health", "/api/generate-audio"
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error",
        "suggestion": "Please try again or contact support"
    }), 500

# 6. Add a simple test endpoint to verify your setup:
@app.route('/api/test-simple', methods=['GET'])
def test_simple():
    """Simple test endpoint to verify basic functionality"""
    try:
        # Test AI connection
        ai_test = "AI service unavailable"
        if api_key:
            try:
                test_response = model.generate_content("Hello, respond with 'AI working'")
                ai_test = "AI service working"
            except Exception as e:
                ai_test = f"AI error: {str(e)}"
        
        return safe_json_response({
            "status": "Server running",
            "ai_status": ai_test,
            "firebase_status": "Connected" if db else "Not configured",
            "timestamp": datetime.now().isoformat(),
            "message": "Basic functionality test complete"
        })
        
    except Exception as e:
        logger.error(f"Simple test error: {e}")
        return safe_json_response({
            "status": "Error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }, 500)
# --- RUN SERVER ---

if __name__ == '__main__':
    # Validate critical environment before starting
    env_errors = validate_critical_environment()
    if env_errors:
        print("\n❌ CRITICAL ENVIRONMENT ERRORS:")
        for error in env_errors:
            print(f"  • {error}")
        print("\n💡 Please fix these issues before starting the server")
        print("📖 Check your .env file and ensure API_KEY is properly set")
        sys.exit(1)
    
    # Run startup checks
    env_valid, config, tests = startup_check()
    
    # Get port and environment
    port = int(os.environ.get('PORT', 5000))
    is_production = os.environ.get('ENVIRONMENT') == 'production' or os.environ.get('RENDER') is not None
    debug_mode = False if os.environ.get('FLASK_ENV') == 'production' else True
    
    # Final startup message
    features_available = sum(config.values())
    print(f"\n🎯 Starting with {features_available}/4 features enabled")
    print(f"🌍 Environment: {'Production' if is_production else 'Development'}")
    print(f"🔧 Debug mode: {debug_mode}")
    print(f"🚪 Port: {port}")
    print(f"📊 Health endpoint: http://localhost:{port}/api/health")
    print(f"🏠 Main app: http://localhost:{port}/")
    print("="*50)
    
    # Run the Flask app
    try:
        app.run(debug=debug_mode, host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        print(f"\n❌ Server startup failed: {e}")
        print("💡 Common fixes:")
        print("- Check if port is already in use")
        print("- Verify environment variables are set")
        print("- Check file permissions")
        sys.exit(1)

