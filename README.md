MyVakeel - Generative AI for Legal Document Demystification
💡 The Problem
Legal documents are intentionally complex, filled with jargon and hidden clauses that make them impossible for the average person to understand. This creates a massive information gap, exposing individuals and small business owners to unnecessary financial and legal risks. Our goal is to bridge this gap, making legal information accessible, clear, and safe.

🚀 The Solution
MyVakeel is a web-based, AI-powered tool that acts as a personal legal assistant. It allows users to securely upload legal documents (like insurance policies or claims) and instantly receive a simplified summary, a risk analysis, and a visual mind map of the key terms. We built this project to demonstrate how generative AI can be used to empower people and protect them from hidden risks in their everyday lives.

✨ Key Features
Secure Document Analysis: Users can upload PDF and image files of legal documents. Our application uses Google's multimodal generative AI to process the documents and provide a comprehensive analysis.

Plain-Language Summary: The AI generates a clear, easy-to-read summary of the entire document, translating complex legal language into simple, bulleted points.

Risk Identification: Our tool intelligently highlights dangerous or hidden clauses, such as those related to liability, exclusions, or claims. For each risk, it provides the original text and a simple explanation of why it is a concern.

Interactive Chatbot: A contextual chatbot allows users to ask specific questions about the uploaded document, getting real-time, helpful answers without needing to navigate the entire legal text.

Secure Data Storage: The application securely stores all uploaded documents and AI analyses in a Firebase Firestore database, ensuring that all user data is private and confidential.

Visual Representation: The AI generates a text-based "mind map" that visually represents the key concepts and dependencies within a document, making it easier to understand at a glance.

💻 Tech Stack
Backend: Python with the Flask framework

Frontend: HTML, CSS, and JavaScript with Firebase Authentication and Firestore for the database

Generative AI: Google's Gemini API

Collaboration: Git and GitHub

🏃 How to Run the Project
Clone this repository to your local machine.

Install the required Python libraries:

pip install Flask google-generativeai python-dotenv firebase-admin

Create a .env file in the main directory and add your API keys.

API_KEY=YOUR_GEMINI_API_KEY
FIREBASE_ADMIN_SDK=YOUR_FIREBASE_ADMIN_SDK_JSON_STRING

Run the application from your terminal:

python app.py

Open your browser and navigate to http://127.0.0.1:5000 to see the application in action.

🔭 Future Vision
This prototype is a proof of concept. Our future plans include:

A full user authentication system with email and password login.

Integration with an AI-powered voice feature for an even more accessible experience.

A full-scale dashboard with statistics on common legal misconceptions and a library of educational articles.

Support for a wider range of document types and legal jurisdictions.