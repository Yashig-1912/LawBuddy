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
    """Analyze uploaded file with enhanced error handling"""
    try:
        user_email = request.headers.get('User-Email')
        if not user_email:
            return jsonify({"error": "User authentication required for file analysis"}), 401
        
        file = request.files.get('file')
        if not file or file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Enhanced file validation
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg', 'text/plain']
        if file.mimetype not in allowed_types:
            return jsonify({
                "error": f"Unsupported file type: {file.mimetype}",
                "supported_types": ["PDF documents", "Images (JPEG, PNG)", "Text files"],
                "suggestion": "Please convert your document to PDF or upload as an image"
            }), 400
        
        # Check file size
        file_content = file.read()
        file_size_mb = len(file_content) / (1024 * 1024)
        if len(file_content) > 10 * 1024 * 1024:
            return jsonify({
                "error": f"File too large: {file_size_mb:.1f}MB",
                "limit": "10MB maximum",
                "suggestion": "Try compressing your PDF or splitting large documents"
            }), 400
        
        logger.info(f"Processing file: {file.filename} ({file_size_mb:.1f}MB) for user: {user_email}")
        
        # Upload file to storage first
        file_info = upload_file_to_storage(file_content, file.filename, user_email)
        
        # Analyze document with enhanced AI
        analysis_result = analyze_document_with_ai(file_content, file.mimetype, file.filename)
        
        if analysis_result.get('error'):
            return jsonify({
                "error": "Analysis failed",
                "details": analysis_result['error'],
                "suggestion": "Try uploading the file again or convert to a different format"
            }), 500
        
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
            "file_size": f"{file_size_mb:.1f}MB",
            "message": "Document analyzed successfully!"
        })
        
    except Exception as e:
        logger.error(f"File analysis error: {e}")
        return jsonify({
            "error": "Analysis failed",
            "details": str(e),
            "suggestion": "Please try again or contact support if the issue persists"
        }), 500

@app.route('/api/analyze-text', methods=['POST'])
@app.route('/analyze-text', methods=['POST'])
def analyze_text_input():
    """Analyze text input with enhanced parsing"""
    try:
        data = request.json
        text_content = data.get('text', '').strip()
        user_email = request.headers.get('User-Email')
        
        if not text_content:
            return jsonify({"error": "No text provided"}), 400
        
        if len(text_content) > 50000:
            return jsonify({
                "error": "Text too long",
                "limit": "50,000 characters maximum",
                "current": len(text_content),
                "suggestion": "Please split your text into smaller sections"
            }), 400
        
        logger.info(f"Processing text analysis ({len(text_content)} chars) for user: {user_email or 'anonymous'}")
        
        # Analyze text with AI
        analysis_result = analyze_text_with_ai(text_content)
        
        if analysis_result.get('error'):
            return jsonify({
                "error": "Analysis failed",
                "details": analysis_result['error'],
                "suggestion": "Try simplifying your text or breaking it into smaller sections"
            }), 500
        
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
            "doc_id": doc_id,
            "text_length": len(text_content)
        })
        
    except Exception as e:
        logger.error(f"Text analysis error: {e}")
        return jsonify({
            "error": "Analysis failed",
            "details": str(e),
            "suggestion": "Please try again with simpler text"
        }), 500

@app.route('/api/chat', methods=['POST'])
@app.route('/chat', methods=['POST'])
def chat():
    """Enhanced chatbot with better responses"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        user_query = data.get('query', '').strip()
        if not user_query:
            return jsonify({"error": "No question provided"}), 400
        
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
        - Include relevant emojis to make responses friendly
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
            return jsonify({
                "error": "AI service temporarily unavailable",
                "suggestion": "Please try again in a few moments",
                "fallback_response": "I'm having trouble connecting to my AI service right now. Please try asking your question again, or feel free to upload a document for analysis instead."
            }), 500
        
        return jsonify({
            "response": ai_response,
            "timestamp": datetime.now().isoformat(),
            "query_length": len(user_query)
        })
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({
            "error": "Chat service failed",
            "details": str(e),
            "suggestion": "Please try again or refresh the page"
        }), 500

def analyze_document_with_ai(file_content, mime_type, filename):
    """Enhanced document analysis with structured prompts"""
    try:
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
        
        prompt_parts = [prompt, {'mime_type': mime_type, 'data': file_content}]
        
        response = model.generate_content(prompt_parts)
        ai_response_text = response.text.strip()
        
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
        
        response = model.generate_content(prompt)
        ai_response_text = response.text.strip()
        
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

# --- ERROR HANDLERS ---

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

# --- RUN SERVER ---

if __name__ == '__main__':
    # Validate required environment variables
    required_vars = ['API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        exit(1)
    
    # Get port from environment (Render sets this automatically)
    port = int(os.environ.get('PORT', 5000))
    
    # Check if running in production (Render sets RENDER environment variable)
    is_production = os.environ.get('RENDER') is not None
    debug_mode = not is_production  # Debug only in development
    
    logger.info("Starting MyVakeel Enhanced Platform v2.0...")
    logger.info(f"Environment: {'Production' if is_production else 'Development'}")
    logger.info(f"Port: {port}")
    logger.info(f"Debug mode: {debug_mode}")
    logger.info(f"Firebase available: {firebase_available}")
    logger.info(f"Storage available: {bucket is not None}")
    
    # Run the Flask app
    app.run(debug=debug_mode, host='0.0.0.0', port=port)