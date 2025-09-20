MyVakeel: Generative AI for Demystifying Legal Documents
MyVakeel is a web-based, AI-powered tool designed to bridge the information gap between complex legal jargon and everyday citizens. Our solution provides a private, secure, and supportive platform where users can get clear, actionable insights from legal documents.

The Problem
Legal documents, such as insurance policies and contracts, are often filled with impenetrable language that leads to confusion and risk. This information asymmetry can result in individuals unknowingly agreeing to unfavorable terms, exposing them to significant financial and legal liabilities. We built MyVakeel to solve this problem by making essential legal information accessible and understandable to everyone.

Key Features
Multi-Document Analysis: Upload PDF, image, or text files for instant, AI-driven analysis. The system extracts and simplifies complex clauses, timelines, and risks.

Secure User Login: Users can log in with their email, and all uploaded documents and analyses are securely stored in a private, dedicated Firebase Firestore database.

AI-Powered Insights: Our core functionality uses the Gemini API to:

Generate concise, bulleted summaries of documents.

Identify and highlight potential risks and hidden clauses.

Provide a "Did you know?" tip to educate users on common legal pitfalls.

Visual Representation: The AI-generated analysis is presented in an easy-to-understand format, including a text-based "mind map" to show the relationships between key concepts.

Interactive Chatbot: A conversational AI assistant is available to answer general questions about legal terms and concepts in a friendly, conversational tone.

How to Run the Project
Set up your environment:

Install the required Python libraries: pip install Flask python-dotenv google-generativeai firebase-admin

Set up your .env file with your Gemini API Key and Firebase Admin SDK credentials.

Start the server:

Run the main application file: python app.py

Access the application:

Open your web browser and navigate to http://127.0.0.1:5000

Technologies Used
Frontend: HTML, CSS, JavaScript (D3.js for visualizations)

Backend: Python with the Flask framework

AI: Google Gemini API (gemini-2.5-flash-preview-05-20 model)

Database: Google Firebase Firestore for secure, serverless data storage

Future Enhancements
Advanced OCR: Enhance image analysis with more powerful OCR to handle poor quality scans.

User Dashboard: A personal dashboard for each user to view their history, manage documents, and track their progress.

Voice-to-Text for Chat: Enable users to speak their queries to the chatbot, making the application more accessible.