# MyVakeel - AI Legal Document Assistant 🤖⚖️

> MyVakeel uses generative AI to simplify legal documents. It analyzes contracts and policies to provide clear summaries, identify hidden risks, and empower users with accessible legal insights.

## ✨ Features

### 🎯 Core Functionality
- **📄 Document Analysis** - Upload PDFs, images, or text files for comprehensive AI analysis
- **🤖 AI-Powered Insights** - Get summaries, risk analysis, key terms, and practical tips
- **💬 Legal Chatbot** - Ask questions about legal terms without login required
- **🎨 Visual Representations** - Interactive mind maps, timelines, and dependency charts
- **🔐 Smart Authentication** - Email-based user accounts for document storage
- **💾 Cloud Storage** - Firebase integration for persistent data and file storage
- **📊 Admin Dashboard** - Monitor usage, view analytics, and manage the platform

### 🚀 User Experience
- **Anonymous Chat** - Get help immediately without creating an account
- **Simple Login** - Just enter your email to access document analysis
- **Drag & Drop** - Easy file uploads with visual feedback
- **Tabbed Results** - Organized analysis with summary, risks, timeline, and visual views
- **Mobile Responsive** - Works perfectly on desktop, tablet, and mobile devices

## 🛠️ Tech Stack

- **Backend**: Flask (Python), RESTful API architecture
- **AI**: Google Gemini 2.0 Flash API for document analysis
- **Database**: Firebase Firestore for user data and analysis storage
- **Storage**: Firebase Storage for uploaded documents
- **Frontend**: Modern HTML5, CSS3, JavaScript (ES6+)
- **Visualization**: D3.js for interactive charts and mind maps
- **Styling**: Custom CSS with gradients, animations, and responsive design

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Google Gemini API key
- Firebase project (optional but recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Yashig-1912/myVakeel.git
   cd myVakeel
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   # Google Gemini API Key (Required)
   API_KEY=your_gemini_api_key_here
   
   # Firebase Configuration (Optional)
   FIREBASE_ADMIN_SDK={"type":"service_account","project_id":"your-project",...}
   FIREBASE_STORAGE_BUCKET=your-project.appspot.com
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open your browser**
   - Main App: http://localhost:5000
   - Admin Panel: http://localhost:5000/admin

## 📖 Usage Guide

### For Regular Users

1. **💬 Chat (No Login Required)**
   - Ask questions about legal terms, clauses, or general guidance
   - Get instant AI-powered responses
   - Perfect for quick consultations

2. **📝 Text Analysis**
   - Paste any legal text, contract clause, or document content
   - Get immediate analysis without uploading files
   - Works with or without login

3. **📄 Document Upload (Login Required)**
   - Click "Login" and enter your email
   - Upload PDF, image, or text files (up to 10MB)
   - Get comprehensive analysis with visual representations

### For Administrators

1. **🛠️ Admin Dashboard**
   - Visit `/admin` to access the control panel
   - Monitor system health and database status
   - View user activity and analysis history

2. **📊 Database Management**
   - Create test data for development
   - View all users and their analyses
   - Monitor platform statistics

## 🏗️ Project Structure

```
myVakeel/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── .env                   # Environment variables (create this)
├── .gitignore            # Git ignore rules
├── README.md             # This documentation
├── static/
│   └── style.css         # Modern responsive styling
└── templates/
    ├── index.html        # Main application interface
    └── admin.html        # Admin dashboard
```

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `API_KEY` | ✅ | Google Gemini API key for AI analysis |
| `FIREBASE_ADMIN_SDK` | ❌ | Firebase service account JSON (for database) |
| `FIREBASE_STORAGE_BUCKET` | ❌ | Firebase storage bucket name |

### Getting API Keys

1. **Google Gemini API**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Add it to your `.env` file

2. **Firebase (Optional)**
   - Create project at [Firebase Console](https://console.firebase.google.com/)
   - Generate service account key
   - Enable Firestore Database and Storage

## 🎨 Features in Detail

### Document Analysis Pipeline

1. **Upload & Validation**
   - Support for PDF, images (JPG, PNG), and text files
   - File size validation (10MB limit)
   - MIME type checking for security

2. **AI Processing**
   - Advanced document parsing with Google Gemini
   - Extraction of key information, risks, and timelines
   - Generation of practical tips and insights

3. **Visual Generation**
   - Interactive mind maps showing document relationships
   - Timeline visualizations for important dates
   - Risk assessment with severity indicators

4. **Storage & Retrieval**
   - Secure file storage in Firebase
   - User-specific analysis history
   - Searchable database of insights

### Chat System

- **Real-time responses** using streaming AI
- **Context awareness** for follow-up questions
- **Legal disclaimers** to ensure responsible use
- **No registration required** for maximum accessibility

## 🔒 Security & Privacy

### Data Protection
- Environment variables for all sensitive data
- No API keys or secrets in source code
- User data stored securely in Firebase
- File uploads validated and sanitized

### Access Control
- Email-based authentication for document storage
- Anonymous chat for privacy-conscious users
- Admin panel restricted to authorized users
- Regular security audits and updates

## 🚀 Deployment

### Local Development
```bash
python app.py
# Visit http://localhost:5000
```

### Production (Heroku)
```bash
# Add Procfile
echo "web: gunicorn app:app" > Procfile

# Deploy
git push heroku main
```

### Production (Railway/Render)
- Set environment variables in platform dashboard
- Deploy directly from GitHub repository
- Configure custom domain if needed

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Test thoroughly**
5. **Commit with descriptive messages**
   ```bash
   git commit -m "Add amazing feature"
   ```
6. **Push to your branch**
   ```bash
   git push origin feature/amazing-feature
   ```
7. **Open a Pull Request**

### Development Guidelines

- Follow PEP 8 for Python code
- Add comments for complex logic
- Test all features before submitting
- Update documentation for new features
- Ensure mobile responsiveness

## 📊 Roadmap

### Upcoming Features
- [ ] **Multi-language support** for global accessibility
- [ ] **Document comparison** tool
- [ ] **Template library** for common legal documents
- [ ] **API endpoints** for third-party integrations
- [ ] **Advanced analytics** dashboard
- [ ] **Email notifications** for analysis completion
- [ ] **Collaboration features** for team document review

### Performance Improvements
- [ ] **Caching system** for faster response times
- [ ] **Database optimization** for large-scale usage
- [ ] **CDN integration** for global content delivery
- [ ] **Background processing** for large document analysis

## 🐛 Troubleshooting

### Common Issues

**Server won't start**
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify your `.env` file exists and has the correct `API_KEY`
- Ensure port 5000 is not already in use

**Firebase connection failed**
- Verify your `FIREBASE_ADMIN_SDK` JSON is valid
- Check that Firestore and Storage are enabled in Firebase Console
- Ensure service account has proper permissions

**Document upload fails**
- Check file size (must be under 10MB)
- Verify file type is supported (PDF, JPG, PNG, TXT)
- Ensure user is logged in with valid email

**AI analysis not working**
- Confirm Google Gemini API key is valid and active
- Check API quota limits in Google Cloud Console
- Verify internet connection for API calls

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- **Google Gemini AI** for powerful document analysis capabilities
- **Firebase** for reliable cloud infrastructure
- **D3.js** for beautiful data visualizations
- **The open source community** for inspiration and contributions
- **Legal professionals** who provided domain expertise

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Yashig-1912/myVakeel/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Yashig-1912/myVakeel/discussions)
- **Email**: [Contact the maintainer](mailto:your-email@example.com)

---

**Built with ❤️ to make legal documents accessible to everyone**

*Making legal complexity simple, one document at a time.*