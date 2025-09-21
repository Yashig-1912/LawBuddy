// =========================================================================
// MyVakeel - Complete JavaScript Application
// This file handles all webapp functionality including login, admin, and analysis
// =========================================================================

// =========================
// GLOBAL VARIABLES
// =========================
let currentUser = null;
let analysisResults = null;
let currentUtterance = null;
let isPlaying = false;
let currentSection = 'all';
let speechSynthesis = window.speechSynthesis;
let currentLanguage = 'en';
let isListening = false;
let recognition = null;
let apiManager = null;
let languageManager = null;
let conversationHistory = {};
let isAdminLoggedIn = false;
let adminSessionToken = null;
let adminSessionExpiry = null;

// DOM Elements - will be initialized on DOMContentLoaded
let fileInput, fileUploadArea, textInput, analyzeFileBtn, analyzeTextBtn;
let chatInput, sendChatBtn, chatWindow, resultsContainer;
let loginModal, emailInput, loginBtn, cancelLoginBtn;
let voicePlayer, floatingVoice;

// =========================
// CONFIGURATION & CONSTANTS
// =========================
const ENHANCED_LANGUAGE_CONFIG = {
    'en': { 
        name: 'English', 
        nativeName: 'English',
        code: 'en-US', 
        voice: 'en-US',
        rtl: false,
        ui: {
            chatPlaceholder: 'Ask about legal terms, clauses, or analysis results...',
            analyzeText: 'Analyze Text',
            analyzeDocument: 'Analyze Document',
            listening: 'Listening...',
            voiceNotSupported: 'Voice input not supported in this browser',
            speakingRate: 'Normal speed'
        }
    },
    'hi': { 
        name: 'Hindi', 
        nativeName: 'हिंदी',
        code: 'hi-IN', 
        voice: 'hi-IN',
        rtl: false,
        ui: {
            chatPlaceholder: 'कानूनी शब्दों, धाराओं या विश्लेषण के बारे में पूछें...',
            analyzeText: 'पाठ का विश्लेषण करें',
            analyzeDocument: 'दस्तावेज़ का विश्लेषण करें',
            listening: 'सुन रहा है...',
            voiceNotSupported: 'इस ब्राउज़र में वॉइस इनपुट समर्थित नहीं है',
            speakingRate: 'सामान्य गति'
        }
    },
    'ta': { 
        name: 'Tamil', 
        nativeName: 'தமிழ்',
        code: 'ta-IN', 
        voice: 'ta-IN',
        rtl: false,
        ui: {
            chatPlaceholder: 'சட்ட விதிமுறைகள், பிரிவுகள் அல்லது பகுப்பாய்வு பற்றி கேளுங்கள்...',
            analyzeText: 'உரையை பகுப்பாய்வு செய்யுங்கள்',
            analyzeDocument: 'ஆவணத்தை பகுப்பாய்வு செய்யுங்கள்',
            listening: 'கேட்டுக்கொண்டிருக்கிறது...',
            voiceNotSupported: 'இந்த உலாவியில் குரல் உள்ளீடு ஆதரிக்கப்படவில்லை',
            speakingRate: 'சாதாரண வேகம்'
        }
    }
};

const ERROR_MESSAGES = {
    'network_error': {
        title: 'Connection Problem',
        message: 'Cannot connect to the server. Please check your internet connection.',
        suggestions: [
            'Check if your internet is working',
            'Try refreshing the page', 
            'Make sure Flask server is running on port 5000',
            'Contact support if the problem continues'
        ]
    },
    'server_error': {
        title: 'Server Issue',
        message: 'Our servers are having trouble processing your request.',
        suggestions: [
            'Please try again in a few moments',
            'Try a smaller file if uploading',
            'Check server logs for errors',
            'Contact support if the issue persists'
        ]
    },
    'file_too_large': {
        title: 'File Too Big', 
        message: 'Your file is larger than our 10MB limit.',
        suggestions: [
            'Try compressing your PDF file',
            'Split large documents into smaller parts',
            'Use the text analysis feature instead'
        ]
    },
    'invalid_file': {
        title: 'File Not Supported',
        message: 'We can only analyze PDF files, images (JPG, PNG), and text files.',
        suggestions: [
            'Convert your document to PDF format',
            'Take a clear photo of paper documents', 
            'Copy and paste text into the text analyzer'
        ]
    },
    'login_required': {
        title: 'Login Required',
        message: 'Please log in with your email to analyze documents.',
        suggestions: [
            'Click the login button and enter your email',
            'Your analysis will be saved for future reference',
            'You can still use the chat feature without logging in'
        ]
    },
    'analysis_failed': {
        title: 'Analysis Failed',
        message: 'We couldn\'t analyze your document. This might be due to unclear text or unsupported content.',
        suggestions: [
            'Try uploading a clearer scan of the document',
            'Make sure the document contains readable text',
            'Contact support with the document type you\'re trying to analyze'
        ]
    }
};

// =========================
// API MANAGER CLASS
// =========================
class APIManager {
    constructor() {
        this.baseURL = this.detectBaseURL();
        this.retryAttempts = 2;
        this.retryDelay = 1000;
    }

    detectBaseURL() {
        const { protocol, hostname, port } = window.location;
        if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname.includes('192.168.')) {
            return `${protocol}//${hostname}:${port || 5000}`;
        }
        return window.location.origin;
    }

    async makeRequest(endpoint, options = {}) {
        const url = `${this.baseURL}/api${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;

        const defaultOptions = {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                ...options.headers
            }
        };

        const finalOptions = { ...defaultOptions, ...options };
        finalOptions.headers = { ...(defaultOptions.headers || {}), ...(options.headers || {}) };

        if (finalOptions.body instanceof FormData) {
            delete finalOptions.headers['Content-Type'];
        }

        for (let attempt = 0; attempt <= this.retryAttempts; attempt++) {
            try {
                const response = await fetch(url, finalOptions);
                const contentType = response.headers.get('content-type') || '';
                let payload = null;
                
                if (contentType.includes('application/json')) {
                    payload = await response.json().catch(() => null);
                } else {
                    const text = await response.text().catch(() => null);
                    try { 
                        payload = text ? JSON.parse(text) : null; 
                    } catch { 
                        payload = text; 
                    }
                }

                if (!response.ok) {
                    const errMsg = (payload && payload.error) ? payload.error : `Server error ${response.status}`;
                    throw new APIError(errMsg, response.status, payload);
                }

                return payload;
            } catch (error) {
                if (error instanceof APIError && error.status >= 400 && error.status < 500) {
                    throw error;
                }
                if (attempt === this.retryAttempts) throw error;
                await this.sleep(this.retryDelay * (attempt + 1));
            }
        }
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

class APIError extends Error {
    constructor(message, status, data) {
        super(message);
        this.name = 'APIError';
        this.status = status;
        this.data = data;
    }
}

// =========================
// LANGUAGE MANAGER CLASS
// =========================
class LanguageManager {
    constructor() {
        this.currentLanguage = 'en';
        this.callbacks = [];
        this.initializeFromStorage();
    }
    
    initializeFromStorage() {
        const saved = localStorage.getItem('myvakeel_language');
        if (saved && ENHANCED_LANGUAGE_CONFIG[saved]) {
            this.currentLanguage = saved;
        }
        this.updateAllLanguageSettings();
    }
    
    changeLanguage(langCode) {
        if (!ENHANCED_LANGUAGE_CONFIG[langCode]) {
            console.error(`Language ${langCode} not supported`);
            return false;
        }
        
        this.currentLanguage = langCode;
        localStorage.setItem('myvakeel_language', langCode);
        
        this.updateAllLanguageSettings();
        this.notifyCallbacks(langCode);
        
        showNotification(`Language changed to ${ENHANCED_LANGUAGE_CONFIG[langCode].nativeName}`, 'success');
        return true;
    }
    
    updateAllLanguageSettings() {
        const config = ENHANCED_LANGUAGE_CONFIG[this.currentLanguage];
        this.updateUIElements(config);
        this.updateVoiceSettings(config);
        this.updateSpeechRecognition(config);
        document.documentElement.lang = config.code.split('-')[0];
        document.body.dir = config.rtl ? 'rtl' : 'ltr';
    }
    
    updateUIElements(config) {
        const elements = {
            'chat-input': 'placeholder',
            'text-input': 'placeholder'
        };
        
        Object.entries(elements).forEach(([id, attr]) => {
            const element = document.getElementById(id);
            if (element && config.ui.chatPlaceholder) {
                element[attr] = config.ui.chatPlaceholder;
            }
        });
        
        const analyzeTextBtn = document.getElementById('analyze-text-btn');
        const analyzeFileBtn = document.getElementById('analyze-file-btn');
        
        if (analyzeTextBtn && !analyzeTextBtn.disabled) {
            analyzeTextBtn.textContent = config.ui.analyzeText;
        }
        
        if (analyzeFileBtn && !analyzeFileBtn.disabled) {
            analyzeFileBtn.textContent = config.ui.analyzeDocument;
        }
        
        const languageSelect = document.getElementById('language-select');
        if (languageSelect) {
            languageSelect.value = this.currentLanguage;
        }
    }
    
    updateVoiceSettings(config) {
        const voiceLanguageSelect = document.getElementById('voice-language');
        if (voiceLanguageSelect) {
            const voiceMappings = {
                'en': 'en-US',
                'hi': 'hi-IN', 
                'ta': 'ta-IN'
            };
            
            const voiceCode = voiceMappings[this.currentLanguage] || 'en-US';
            voiceLanguageSelect.value = voiceCode;
        }
    }
    
    updateSpeechRecognition(config) {
        if (recognition) {
            recognition.lang = config.code;
        }
    }
    
    getCurrentConfig() {
        return ENHANCED_LANGUAGE_CONFIG[this.currentLanguage];
    }
    
    onLanguageChange(callback) {
        this.callbacks.push(callback);
    }
    
    notifyCallbacks(langCode) {
        this.callbacks.forEach(callback => {
            try {
                callback(langCode, ENHANCED_LANGUAGE_CONFIG[langCode]);
            } catch (error) {
                console.error('Language callback error:', error);
            }
        });
    }
}

// =========================
// API FUNCTIONS
// =========================
async function registerUser(email) {
    return await apiManager.makeRequest('/register', {
        method: 'POST',
        body: JSON.stringify({ email })
    });
}

async function analyzeFileAPI(file, userEmail) {
    if (!file) {
        throw new Error('No file provided');
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    console.log('🌐 Making API request to /api/analyze-file');
    
    try {
        return await apiManager.makeRequest('/analyze-file', {
            method: 'POST',
            headers: {
                'User-Email': userEmail || ''
            },
            body: formData
        });
    } catch (error) {
        console.error('🚨 API request failed:', error);
        throw error;
    }
}

async function analyzeTextAPI(text, userEmail = '') {
    if (!text || text.trim().length === 0) {
        throw new Error('No text provided');
    }
    
    console.log('🌐 Making API request to /api/analyze-text');
    
    try {
        return await apiManager.makeRequest('/analyze-text', {
            method: 'POST',
            headers: {
                'User-Email': userEmail,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text })
        });
    } catch (error) {
        console.error('🚨 Text API request failed:', error);
        throw error;
    }
}

async function sendChatAPI(query, language = 'en') {
    return await apiManager.makeRequest('/chat', {
        method: 'POST',
        body: JSON.stringify({ query, language })
    });
}

async function checkHealthAPI() {
    return await apiManager.makeRequest('/health');
}

// =========================
// INITIALIZATION FUNCTIONS
// =========================
function initializeApp() {
    console.log('🚀 Initializing MyVakeel...');
    
    // Initialize DOM elements first
    initializeDOMElements();
    
    // Initialize managers
    try {
        apiManager = new APIManager();
        languageManager = new LanguageManager();
        console.log('✅ Managers initialized');
    } catch (e) {
        console.error('❌ Manager init error:', e);
    }
    
    // Set up event listeners
    setupEventListeners();
    
    // Initialize other features
    initializeSpeechRecognition();
    checkUserSession();
    updateUserStatus();
    checkServerStatus();
    setupCharacterCounter();
    
    console.log('✅ MyVakeel initialized successfully!');
}

function initializeDOMElements() {
    console.log('🎯 Initializing DOM elements...');
    
    // File handling elements
    fileInput = document.getElementById('file-input');
    fileUploadArea = document.getElementById('file-upload-area');
    analyzeFileBtn = document.getElementById('analyze-file-btn');
    
    // Text analysis elements
    textInput = document.getElementById('text-input');
    analyzeTextBtn = document.getElementById('analyze-text-btn');
    
    // Chat elements
    chatInput = document.getElementById('chat-input');
    sendChatBtn = document.getElementById('send-chat-btn');
    chatWindow = document.getElementById('chat-window');
    
    // Results and UI elements
    resultsContainer = document.getElementById('results-container');
    voicePlayer = document.getElementById('voice-player');
    floatingVoice = document.getElementById('floating-voice');
    
    // Login elements
    loginModal = document.getElementById('login-modal');
    emailInput = document.getElementById('email-input');
    loginBtn = document.getElementById('login-btn');
    cancelLoginBtn = document.getElementById('cancel-login-btn');
    
    console.log('DOM elements initialized:', {
        fileInput: !!fileInput,
        textInput: !!textInput,
        chatInput: !!chatInput,
        loginModal: !!loginModal
    });
}

// =========================
// EVENT LISTENER SETUP
// =========================
function setupEventListeners() {
    console.log('🎯 Setting up all event listeners...');
    
    try {
        // File upload events
        if (fileUploadArea && fileInput) {
            fileUploadArea.addEventListener('click', () => fileInput.click());
            fileUploadArea.addEventListener('dragover', handleDragOver);
            fileUploadArea.addEventListener('dragleave', handleDragLeave);
            fileUploadArea.addEventListener('drop', handleFileDrop);
            fileInput.addEventListener('change', handleFileSelect);
        }
        
        if (analyzeFileBtn) {
            analyzeFileBtn.addEventListener('click', analyzeFile);
        }

        // Text analysis events
        if (analyzeTextBtn) {
            analyzeTextBtn.addEventListener('click', analyzeText);
        }

        // Chat events
        if (sendChatBtn) {
            sendChatBtn.addEventListener('click', handleChatMessage);
            console.log('✅ Chat send button event listener added');
        }
        
        if (chatInput) {
            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    handleChatMessage();
                }
            });
        }

        // Login events
        if (loginBtn && cancelLoginBtn && emailInput) {
            loginBtn.addEventListener('click', handleLogin);
            cancelLoginBtn.addEventListener('click', closeLoginModal);
            
            emailInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    handleLogin();
                }
            });
            
            console.log('✅ Login event listeners added');
        }

        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => switchTab(tab.dataset.tab));
        });
        
        console.log('✅ All event listeners set up successfully');
        
    } catch (error) {
        console.error('❌ Error setting up event listeners:', error);
    }
}

// =========================
// FILE HANDLING FUNCTIONS
// =========================
function handleDragOver(e) {
    e.preventDefault();
    fileUploadArea.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    fileUploadArea.classList.remove('dragover');
}

function handleFileDrop(e) {
    e.preventDefault();
    fileUploadArea.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        fileInput.files = files;
        handleFileSelect();
    }
}

function handleFileSelect() {
    const file = fileInput.files[0];
    if (file) {
        const sizeMB = (file.size / 1024 / 1024).toFixed(2);
        if (file.size > 10 * 1024 * 1024) {
            showNotification(`File too large: ${sizeMB}MB. Maximum size is 10MB.`, 'error');
            fileInput.value = '';
            return;
        }

        analyzeFileBtn.disabled = false;
        fileUploadArea.innerHTML = `
            <svg width="48" height="48" viewBox="0 0 24 24" fill="#10b981">
                <path d="M9,16.17L4.83,12L3.41,13.41L9,19L21,7L19.59,5.59L9,16.17Z"/>
            </svg>
            <p><strong>File selected:</strong> ${file.name}</p>
            <small>Size: ${sizeMB} MB • Type: ${file.type}</small>
        `;
    }
}

// =========================
// ANALYSIS FUNCTIONS
// =========================
async function analyzeFile() {
    if (!currentUser) {
        showLoginModal();
        return;
    }

    const file = fileInput.files[0];
    if (!file) {
        showNotification('Please select a file', 'error');
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        showEnhancedError('file_too_large', `Your file is ${(file.size / 1024 / 1024).toFixed(2)}MB`);
        return;
    }

    showUploadProgress();
    analyzeFileBtn.disabled = true;
    analyzeFileBtn.textContent = 'Analyzing...';

    try {
        console.log('📤 Starting file analysis...');
        const data = await analyzeFileAPI(file, currentUser.email);
        
        if (data && data.success) {
            analysisResults = data.result;
            displayEnhancedResults(data.result);
            showNotification(`Document analyzed successfully! (${data.file_size})`, 'success');
        } else {
            const errorType = detectErrorType(new Error(data.error || 'Analysis failed'));
            showEnhancedError(errorType, data.details);
        }
    } catch (error) {
        console.error('File analysis error:', error);
        const errorType = detectErrorType(error);
        showEnhancedError(errorType, error.message);
    } finally {
        hideUploadProgress();
        analyzeFileBtn.disabled = false;
        analyzeFileBtn.textContent = 'Analyze Document';
    }
}

async function analyzeText() {
    console.log('📝 Starting text analysis...');
    
    const text = textInput.value.trim();
    if (!text) {
        showNotification('Please enter some text to analyze', 'error');
        return;
    }

    if (text.length > 50000) {
        showEnhancedError('analysis_failed', `Text too long: ${text.length} characters (max: 50,000)`);
        return;
    }

    showLoadingSafe('text-loading', true);
    
    if (analyzeTextBtn) {
        analyzeTextBtn.disabled = true;
        analyzeTextBtn.textContent = 'Analyzing...';
    }

    try {
        console.log('📤 Sending text to server...');
        const data = await analyzeTextAPI(text, currentUser ? currentUser.email : '');
        console.log('✅ Received response:', data);
        
        if (data && data.success) {
            analysisResults = data.result;
            displayEnhancedResults(data.result);
            showNotification(`Text analyzed successfully! (${data.text_length || text.length} characters)`, 'success');
        } else {
            console.error('❌ Text analysis failed:', data);
            const errorMessage = data?.error || 'Analysis failed';
            const errorDetails = data?.details || 'Unknown error occurred';
            showEnhancedError('analysis_failed', `${errorMessage}. ${errorDetails}`);
        }
    } catch (error) {
        console.error('❌ Text analysis error:', error);
        
        if (error instanceof APIError) {
            if (error.status >= 500) {
                showEnhancedError('server_error', error.message);
            } else {
                showEnhancedError('analysis_failed', error.message);
            }
        } else {
            const errorMessage = error.message || 'Unknown error';
            if (errorMessage.includes('Failed to fetch') || errorMessage.includes('NetworkError')) {
                showEnhancedError('network_error', 'Cannot connect to server. Please check if the Flask app is running on port 5000.');
            } else {
                showEnhancedError('analysis_failed', errorMessage);
            }
        }
    } finally {
        showLoadingSafe('text-loading', false);
        
        if (analyzeTextBtn) {
            analyzeTextBtn.disabled = false;
            analyzeTextBtn.textContent = 'Analyze Text';
        }
    }
}

// =========================
// CHAT FUNCTIONS  
// =========================
async function handleChatMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    addMessageToChat(query, 'user');
    chatInput.value = '';

    const thinkingMessage = addMessageToChat('🤔 MyVakeel is thinking...', 'bot', true);
    sendChatBtn.disabled = true;

    try {
        const data = await sendChatAPI(query, languageManager.currentLanguage);
        
        thinkingMessage.remove();
        
        if (data.response) {
            const botMessage = addMessageToChat(data.response, 'bot');
            
            if (speechSynthesis) {
                const voiceBtn = document.createElement('button');
                voiceBtn.className = 'voice-button';
                voiceBtn.style.cssText = 'margin-top: 0.5rem; padding: 0.5rem 1rem; font-size: 0.8rem;';
                voiceBtn.innerHTML = '🔊 Play Response';
                voiceBtn.onclick = () => speakText(data.response);
                botMessage.appendChild(voiceBtn);
            }
        } else {
            addMessageToChat('Sorry, I encountered an error. Please try again.', 'bot');
        }
    } catch (error) {
        thinkingMessage.remove();
        console.error('Chat error:', error);
        
        let errorMessage = '❌ ';
        if (error instanceof APIError) {
            if (error.status >= 500) {
                errorMessage += 'Our chat service is temporarily unavailable. Please try again.';
            } else {
                errorMessage += 'Sorry, I encountered an error. Please try again.';
            }
        } else {
            errorMessage += 'Cannot connect to chat service. Please check your internet connection.';
        }
        
        addMessageToChat(errorMessage, 'bot');
    } finally {
        sendChatBtn.disabled = false;
    }
}

function addMessageToChat(message, sender, isTemporary = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}-message`;
    
    const paragraph = document.createElement('p');
    
    if (sender === 'bot' && message.includes('**')) {
        safeSetHTML(paragraph, message);
    } else {
        paragraph.textContent = message;
    }
    
    messageDiv.appendChild(paragraph);
    
    if (isTemporary) {
        messageDiv.style.opacity = '0.7';
        messageDiv.classList.add('thinking');
    }
    
    chatWindow.appendChild(messageDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    
    return messageDiv;
}

// =========================
// AUTHENTICATION FUNCTIONS
// =========================
function checkUserSession() {
    const savedUser = localStorage.getItem('myvakeel_user');
    if (savedUser) {
        currentUser = JSON.parse(savedUser);
        updateUserStatus();
    }
}

function updateUserStatus() {
    const userEmailDisplay = document.getElementById('user-email-display');
    const userLoggedIn = document.getElementById('user-logged-in');
    const userNotLoggedIn = document.getElementById('user-not-logged-in');
    
    console.log('Updating user status. Current user:', currentUser);
    
    if (currentUser && currentUser.email) {
        if (userLoggedIn && userNotLoggedIn && userEmailDisplay) {
            userEmailDisplay.textContent = currentUser.email;
            userLoggedIn.style.display = 'flex';
            userNotLoggedIn.style.display = 'none';
        }
    } else {
        if (userLoggedIn && userNotLoggedIn) {
            userLoggedIn.style.display = 'none';
            userNotLoggedIn.style.display = 'flex';
        }
    }
}

function showLoginModal() {
    const loginModal = document.getElementById('login-modal');
    if (loginModal) {
        const emailInput = document.getElementById('email-input');
        if (emailInput) {
            emailInput.value = '';
            emailInput.classList.remove('error');
        }
        
        loginModal.style.display = 'flex';
        
        setTimeout(() => {
            if (emailInput) emailInput.focus();
        }, 100);
    }
}

async function handleLogin() {
    const emailInput = document.getElementById('email-input');
    const loginBtn = document.getElementById('login-btn');
    
    if (!emailInput || !loginBtn) {
        console.error('Login elements not found');
        return;
    }
    
    const email = emailInput.value.trim();
    
    if (!email) {
        emailInput.classList.add('error');
        showNotification('Please enter your email address', 'error');
        return;
    }
    
    if (!isValidEmail(email)) {
        emailInput.classList.add('error');
        showNotification('Please enter a valid email address', 'error');
        return;
    }
    
    loginBtn.disabled = true;
    const originalText = loginBtn.textContent;
    loginBtn.textContent = 'Logging in...';
    
    try {
        const data = await registerUser(email);
        
        if (data.success) {
            currentUser = { email: data.email };
            localStorage.setItem('myvakeel_user', JSON.stringify(currentUser));
            
            updateUserStatus();
            closeLoginModal();
            showNotification('Successfully logged in!', 'success');
            
            if (fileInput && fileInput.files.length > 0) {
                analyzeFile();
            }
        } else {
            throw new Error(data.error || 'Login failed');
        }
    } catch (error) {
        console.error('Login error:', error);
        showNotification(error.message || 'Login failed. Please try again.', 'error');
        emailInput.classList.add('error');
    } finally {
        loginBtn.disabled = false;
        loginBtn.textContent = originalText;
    }
}

function closeLoginModal() {
    const loginModal = document.getElementById('login-modal');
    if (loginModal) {
        loginModal.style.display = 'none';
        
        const emailInput = document.getElementById('email-input');
        if (emailInput) {
            emailInput.classList.remove('error');
        }
    }
}

function logout() {
    currentUser = null;
    localStorage.removeItem('myvakeel_user');
    updateUserStatus();
    showNotification('Logged out successfully', 'success');
}

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// =========================
// ADMIN FUNCTIONS
// =========================
function showAdminLogin() {
    document.getElementById('admin-modal').style.display = 'block';
}

function closeAdminModal() {
    document.getElementById('admin-modal').style.display = 'none';
}

async function adminLogin() {
    const username = document.getElementById('admin-username').value;
    const password = document.getElementById('admin-password').value;
    
    if (!username || !password) {
        showNotification('Please enter both username and password', 'error');
        return;
    }
    
    const loginBtn = document.querySelector('.admin-modal .btn');
    const originalText = loginBtn.textContent;
    loginBtn.textContent = 'Logging in...';
    loginBtn.disabled = true;
    
    try {
        const response = await fetch('/api/admin-login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            adminSessionToken = data.session_token;
            adminSessionExpiry = new Date(data.expires);
            
            localStorage.setItem('admin_session', JSON.stringify({
                token: adminSessionToken,
                expires: adminSessionExpiry
            }));
            
            closeAdminModal();
            showNotification('Admin access granted!', 'success');
            
            window.open('/admin', '_blank');
            
            document.getElementById('admin-username').value = '';
            document.getElementById('admin-password').value = '';
            
        } else {
            showNotification(data.error || 'Invalid credentials', 'error');
        }
        
    } catch (error) {
        console.error('Admin login error:', error);
        showNotification('Login failed. Please check server connection.', 'error');
    } finally {
        loginBtn.textContent = originalText;
        loginBtn.disabled = false;
    }
}

function togglePasswordVisibility() {
    const passwordField = document.getElementById('admin-password');
    const toggleBtn = document.querySelector('.password-toggle');
    
    if (passwordField.type === 'password') {
        passwordField.type = 'text';
        toggleBtn.textContent = '🙈';
    } else {
        passwordField.type = 'password';
        toggleBtn.textContent = '👁️';
    }
}

// =========================
// PROGRESS & UI FUNCTIONS
// =========================
function showUploadProgress() {
    try {
        const progressContainer = document.getElementById('upload-progress');
        if (progressContainer) {
            progressContainer.style.display = 'block';
            
            setTimeout(() => updateProgressStepSafe('upload', 25), 500);
            setTimeout(() => updateProgressStepSafe('extract', 50), 1500);
            setTimeout(() => updateProgressStepSafe('analyze', 75), 3000);
        }
    } catch (error) {
        console.warn('Progress display error:', error);
    }
}

function updateProgressStepSafe(stepId, percentage) {
    try {
        const step = document.getElementById(`step-${stepId}`);
        const progressFill = document.getElementById('progress-fill');
        const progressPercent = document.getElementById('progress-percent');
        
        if (!step || !progressFill || !progressPercent) {
            return;
        }
        
        const icon = step.querySelector('.step-icon');
        if (!icon) return;
        
        const steps = ['upload', 'extract', 'analyze', 'complete'];
        const currentIndex = steps.indexOf(stepId);
        
        for (let i = 0; i <= currentIndex; i++) {
            const stepElement = document.getElementById(`step-${steps[i]}`);
            if (stepElement) {
                const stepIcon = stepElement.querySelector('.step-icon');
                if (stepIcon) {
                    stepElement.classList.remove('pending');
                    stepElement.classList.add('completed');
                    stepIcon.classList.remove('pending');
                    stepIcon.classList.add('completed');
                    stepIcon.textContent = '✓';
                }
            }
        }
        
        if (currentIndex < steps.length - 1) {
            const nextStep = document.getElementById(`step-${steps[currentIndex + 1]}`);
            if (nextStep) {
                const nextIcon = nextStep.querySelector('.step-icon');
                if (nextIcon) {
                    nextStep.classList.add('active');
                    nextIcon.classList.remove('pending');
                    nextIcon.classList.add('active');
                }
            }
        }
        
        progressFill.style.width = percentage + '%';
        progressPercent.textContent = percentage + '%';
        
    } catch (error) {
        console.warn('Progress step update error:', error);
    }
}

function hideUploadProgress() {
    try {
        setTimeout(() => {
            const progressContainer = document.getElementById('upload-progress');
            if (progressContainer) {
                progressContainer.style.display = 'none';
                
                const steps = ['upload', 'extract', 'analyze', 'complete'];
                steps.forEach((stepId, index) => {
                    const step = document.getElementById(`step-${stepId}`);
                    if (step) {
                        const icon = step.querySelector('.step-icon');
                        if (icon) {
                            step.className = 'progress-step';
                            icon.className = 'step-icon pending';
                            icon.textContent = index + 1;
                        }
                    }
                });
                
                const progressFill = document.getElementById('progress-fill');
                const progressPercent = document.getElementById('progress-percent');
                
                if (progressFill) progressFill.style.width = '0%';
                if (progressPercent) progressPercent.textContent = '0%';
            }
        }, 1000);
    } catch (error) {
        console.warn('Progress hide error:', error);
    }
}

function showLoadingSafe(elementId, show) {
    try {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = show ? 'block' : 'none';
        }
    } catch (error) {
        console.warn(`Loading element error for ${elementId}:`, error);
    }
}

// =========================
// RESULTS DISPLAY FUNCTIONS
// =========================
function displayEnhancedResults(results) {
    resultsContainer.style.display = 'block';
    if (voicePlayer) voicePlayer.style.display = 'block';
    if (floatingVoice) floatingVoice.style.display = 'block';
    
    if (results.summary) {
        displayEnhancedSummary(results.summary);
    }

    if (results.document_type) {
        const docTypeContent = document.getElementById('document-type-content');
        if (docTypeContent) {
            docTypeContent.innerHTML = `
                <div style="background: linear-gradient(135deg, #667eea20, #764ba220); padding: 1.5rem; border-radius: 10px; border-left: 4px solid #667eea;">
                    <h4 style="color: #667eea; margin-bottom: 0.5rem;">📄 Document Classification</h4>
                    <p style="font-size: 1.2rem; font-weight: 600; color: #2d3748; margin-bottom: 0.5rem;">${results.document_type}</p>
                    <p style="color: #4a5568; font-size: 0.9rem;">This classification helps determine the relevant legal standards and typical provisions.</p>
                </div>
            `;
        }
    }

    if (results.tip) {
        const tipContent = document.getElementById('tip-content');
        if (tipContent) {
            tipContent.innerHTML = `
                <div style="background: linear-gradient(135deg, #10b98120, #059669); padding: 1.5rem; border-radius: 10px; border-left: 4px solid #10b981;">
                    <h4 style="color: #10b981; margin-bottom: 0.75rem;">💡 Expert Tip</h4>
                    <p style="color: #065f46; line-height: 1.6; font-weight: 500;">${results.tip}</p>
                </div>
            `;
        }
    }

    if (results.key_terms) {
        displayEnhancedKeyTerms(results.key_terms);
    }

    if (results.risks) {
        displayEnhancedRisks(results.risks);
    }

    if (results.important_clauses) {
        displayEnhancedClauses(results.important_clauses);
    }

    if (results.timeline) {
        displayEnhancedTimeline(results.timeline);
    }

    createEnhancedVisualizations(results);
    resultsContainer.scrollIntoView({ behavior: 'smooth' });
    showSuccessMessage();
}

function displayEnhancedSummary(summaryData) {
    const container = document.getElementById('summary-content');
    if (!container) return;
    
    if (Array.isArray(summaryData)) {
        container.innerHTML = summaryData.map((point, index) => {
            const pointData = typeof point === 'object' ? point : { description: point };
            const categoryColors = {
                financial: '#10b981',
                benefits: '#8b5cf6', 
                termination: '#ef4444',
                obligations: '#f59e0b',
                general: '#667eea'
            };
            const color = categoryColors[pointData.category] || categoryColors.general;
            
            return `
                <div class="enhanced-summary-point">
                    <div class="point-header">
                        <div class="point-number" style="background: ${color};">${index + 1}</div>
                        <div>
                            <h4>${pointData.title || `Key Point ${index + 1}`}</h4>
                        </div>
                    </div>
                    <div class="point-content">
                        <p>${pointData.description}</p>
                        ${pointData.example ? `
                            <div class="example-box">
                                <strong>Example:</strong> ${pointData.example}
                            </div>
                        ` : ''}
                        ${pointData.impact ? `
                            <div class="impact-box">
                                <strong>Impact:</strong> ${pointData.impact}
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');
    } else {
        container.innerHTML = `
            <div class="enhanced-summary-point">
                <div class="point-header">
                    <div class="point-number">1</div>
                    <div><h4>Document Analysis</h4></div>
                </div>
                <div class="point-content">
                    <p>${summaryData}</p>
                </div>
            </div>
        `;
    }
}

function displayEnhancedKeyTerms(keyTerms) {
    const container = document.getElementById('key-terms-content');
    if (!container) return;
    
    if (Array.isArray(keyTerms)) {
        container.innerHTML = `
            <div class="key-terms-grid">
                ${keyTerms.map(term => {
                    const termData = typeof term === 'object' ? term : { term: term, explanation: 'Important legal concept' };
                    return `
                        <div class="term-card">
                            <div class="term-title">
                                🔑 ${termData.term}
                                ${termData.importance ? `<span class="term-importance ${termData.importance}">${termData.importance}</span>` : ''}
                            </div>
                            <div class="term-explanation">${termData.explanation}</div>
                            ${termData.example ? `
                                <div class="example-box" style="margin-top: 0.75rem;">
                                    <strong>Example:</strong> ${termData.example}
                                </div>
                            ` : ''}
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    } else {
        container.innerHTML = `<p>${keyTerms}</p>`;
    }
}

function displayEnhancedRisks(risks) {
    const container = document.getElementById('risks-content');
    if (!container) return;
    
    if (Array.isArray(risks)) {
        container.innerHTML = risks.map(risk => {
            const riskData = typeof risk === 'object' ? risk : { title: 'Risk', description: risk };
            const severity = riskData.severity || 'medium';
            
            return `
                <div class="risk-item ${severity}-severity">
                    <div class="risk-header">
                        <div class="risk-title">⚠️ ${riskData.title}</div>
                        <div class="severity-badge ${severity}">${severity}</div>
                    </div>
                    <p style="color: #374151; margin-bottom: 0.75rem;">${riskData.description}</p>
                    ${riskData.impact ? `
                        <div style="background: rgba(239, 68, 68, 0.1); padding: 0.75rem; border-radius: 6px; margin-bottom: 0.75rem;">
                            <strong style="color: #dc2626;">Impact:</strong> <span style="color: #374151;">${riskData.impact}</span>
                        </div>
                    ` : ''}
                    ${riskData.mitigation ? `
                        <div style="background: rgba(16, 185, 129, 0.1); padding: 0.75rem; border-radius: 6px;">
                            <strong style="color: #10b981;">How to address:</strong> <span style="color: #374151;">${riskData.mitigation}</span>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');
    } else {
        container.innerHTML = `
            <div class="risk-item medium-severity">
                <div class="risk-header">
                    <div class="risk-title">⚠️ General Risk</div>
                    <div class="severity-badge medium">medium</div>
                </div>
                <p>${risks}</p>
            </div>
        `;
    }
}

function displayEnhancedClauses(clauses) {
    const container = document.getElementById('important-clauses-content');
    if (!container) return;
    
    if (Array.isArray(clauses)) {
        container.innerHTML = clauses.map(clause => `
            <div style="background: linear-gradient(135deg, #fef3c7, #fed7aa); border-left: 4px solid #f59e0b; padding: 1.5rem; border-radius: 10px; margin-bottom: 1rem;">
                <h4 style="color: #92400e; margin-bottom: 0.75rem;">🚨 Important Clause</h4>
                <p style="color: #451a03; line-height: 1.6;">${typeof clause === 'object' ? `<strong>${clause.title}:</strong> ${clause.description}` : clause}</p>
            </div>
        `).join('');
    } else {
        container.innerHTML = `
            <div style="background: linear-gradient(135deg, #fef3c7, #fed7aa); border-left: 4px solid #f59e0b; padding: 1.5rem; border-radius: 10px;">
                <p style="color: #451a03;">${clauses}</p>
            </div>
        `;
    }
}

function displayEnhancedTimeline(timeline) {
    const container = document.getElementById('timeline-content');
    if (!container) return;
    
    if (Array.isArray(timeline)) {
        container.innerHTML = `
            <div class="timeline-improved">
                ${timeline.map((item, index) => {
                    const itemData = typeof item === 'object' ? item : { event: item };
                    const isLast = index === timeline.length - 1;
                    
                    return `
                        <div class="timeline-item-improved">
                            ${!isLast ? '<div class="timeline-line"></div>' : ''}
                            <div class="timeline-dot"></div>
                            <div class="timeline-content">
                                <div class="timeline-date">📅 ${itemData.date || 'Important Date'}</div>
                                <div class="timeline-event">${itemData.event}</div>
                                ${itemData.action_required ? `
                                    <div class="timeline-action">
                                        <strong>Action needed:</strong> ${itemData.action_required}
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    } else {
        container.innerHTML = `
            <div class="timeline-improved">
                <div class="timeline-item-improved">
                    <div class="timeline-dot"></div>
                    <div class="timeline-content">
                        <div class="timeline-event">${timeline}</div>
                    </div>
                </div>
            </div>
        `;
    }
}

function createEnhancedVisualizations(results) {
    const container = document.getElementById('visual-content');
    if (!container) return;
    
    const stats = generateAnalysisStatistics(results);
    
    container.innerHTML = `
        <div class="simple-chart">
            <h4 style="text-align: center; margin-bottom: 1.5rem; color: #374151;">📊 Document Analysis Overview</h4>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">
                <div style="background: linear-gradient(135deg, #667eea20, #667eea10); border: 2px solid #667eea; padding: 1.5rem; border-radius: 12px; text-align: center;">
                    <div style="font-size: 2.5rem; color: #667eea; font-weight: bold;">${stats.summaryPoints}</div>
                    <div style="color: #4a5568; font-weight: 600;">Key Points</div>
                    <div style="font-size: 0.8rem; color: #6b7280; margin-top: 0.5rem;">Legal concepts explained</div>
                </div>
                
                <div style="background: linear-gradient(135deg, #f59e0b20, #f59e0b10); border: 2px solid #f59e0b; padding: 1.5rem; border-radius: 12px; text-align: center;">
                    <div style="font-size: 2.5rem; color: #f59e0b; font-weight: bold;">${stats.timelineCount}</div>
                    <div style="color: #4a5568; font-weight: 600;">Timeline Items</div>
                    <div style="font-size: 0.8rem; color: #6b7280; margin-top: 0.5rem;">Important dates</div>
                </div>
            </div>
            
            <div style="background: #f8fafc; border-radius: 12px; padding: 1.5rem; text-align: center;">
                <h4 style="color: #374151; margin-bottom: 1rem;">🎯 Analysis Completeness</h4>
                <div style="background: #e5e7eb; height: 12px; border-radius: 6px; overflow: hidden; margin: 1rem 0;">
                    <div style="background: linear-gradient(90deg, #10b981, #059669); height: 100%; width: ${stats.completeness}%; border-radius: 6px; transition: width 1s ease;"></div>
                </div>
                <div style="color: #6b7280; font-size: 0.9rem;">
                    <strong>${stats.completeness}%</strong> of document elements analyzed
                </div>
            </div>
        </div>
    `;
}

function generateAnalysisStatistics(results) {
    const stats = {
        summaryPoints: 0,
        riskCount: 0,
        termCount: 0,
        timelineCount: 0,
        completeness: 0
    };

    if (results.summary && Array.isArray(results.summary)) {
        stats.summaryPoints = results.summary.length;
    }

    if (results.risks && Array.isArray(results.risks)) {
        stats.riskCount = results.risks.length;
    }

    if (results.key_terms && Array.isArray(results.key_terms)) {
        stats.termCount = results.key_terms.length;
    }

    if (results.timeline && Array.isArray(results.timeline)) {
        stats.timelineCount = results.timeline.length;
    }

    const fields = ['summary', 'risks', 'key_terms', 'timeline', 'document_type', 'tip'];
    const completedFields = fields.filter(field => results[field] && results[field] !== '').length;
    stats.completeness = Math.round((completedFields / fields.length) * 100);

    return stats;
}

function showSuccessMessage() {
    const successContainer = document.createElement('div');
    successContainer.className = 'success-container';
    successContainer.innerHTML = `
        <div class="success-header">
            <div class="success-icon">✅</div>
            <div style="color: #10b981; font-weight: bold; font-size: 1.1rem;">Analysis Complete!</div>
        </div>
        <div style="color: #065f46; margin-bottom: 1rem;">
            Your document has been successfully analyzed. Review the insights below and use the voice feature to listen to the analysis.
        </div>
        <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
            <button class="voice-button" onclick="playAnalysis()" style="background: #10b981;">
                🎵 Play Full Analysis
            </button>
            <button class="btn btn-secondary" onclick="this.parentElement.parentElement.remove()">
                Dismiss
            </button>
        </div>
    `;
    
    const cardElement = resultsContainer.querySelector('.card');
    if (cardElement) {
        cardElement.insertBefore(successContainer, cardElement.firstChild);
    }
    
    setTimeout(() => {
        if (successContainer.parentNode) {
            successContainer.remove();
        }
    }, 8000);
}

// =========================
// VOICE FUNCTIONS
// =========================
function initializeSpeechRecognition() {
    try {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn('Speech recognition not supported');
            return;
        }

        recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;

        recognition.onresult = function(event) {
            const transcript = Array.from(event.results)
                .map(result => result[0].transcript)
                .join('');
            
            if (chatInput) {
                chatInput.value = transcript;
            }
        };

        recognition.onstart = function() {
            isListening = true;
            updateVoiceUI();
        };

        recognition.onend = function() {
            isListening = false;
            updateVoiceUI();
        };

        recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
            isListening = false;
            updateVoiceUI();
        };
    } catch (error) {
        console.error('Failed to initialize speech recognition:', error);
    }
}

function updateVoiceUI() {
    const voiceBtn = document.getElementById('voice-input-btn');
    const voiceStatus = document.getElementById('voice-status');
    
    if (!voiceBtn || !voiceStatus) return;
    
    if (isListening) {
        voiceBtn.classList.add('listening');
        voiceBtn.innerHTML = '⏹️';
        voiceStatus.style.display = 'block';
    } else {
        voiceBtn.classList.remove('listening');
        voiceBtn.innerHTML = '🎤';
        voiceStatus.style.display = 'none';
    }
}

function toggleVoiceInput() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        showNotification('Voice input requires Chrome or Edge browser', 'error');
        return;
    }
    
    if (!isListening) {
        startVoiceInput();
    } else {
        stopVoiceInput();
    }
}

function startVoiceInput() {
    if (!recognition) {
        initializeSpeechRecognition();
    }
    
    if (recognition) {
        try {
            recognition.lang = ENHANCED_LANGUAGE_CONFIG[currentLanguage].code;
            recognition.start();
        } catch (error) {
            console.error('Failed to start voice recognition:', error);
            showNotification('Voice input failed to start. Please try again.', 'error');
        }
    } else {
        showNotification('Voice input not available in this browser', 'error');
    }
}

function stopVoiceInput() {
    if (recognition && isListening) {
        try {
            recognition.stop();
        } catch (error) {
            console.error('Error stopping voice recognition:', error);
        }
    }
    
    isListening = false;
    const voiceBtn = document.getElementById('voice-input-btn');
    const voiceStatus = document.getElementById('voice-status');
    
    if (voiceBtn) {
        voiceBtn.classList.remove('listening');
        voiceBtn.title = 'Voice Input';
    }
    if (voiceStatus) {
        voiceStatus.style.display = 'none';
    }
}

function playAnalysis() {
    if (!analysisResults) {
        showNotification('No analysis available to play', 'error');
        return;
    }

    if (!speechSynthesis) {
        showNotification('Speech synthesis not supported in this browser', 'error');
        return;
    }

    const section = currentSection;
    const language = document.getElementById('voice-language')?.value || 'en-US';
    const speed = parseFloat(document.getElementById('speed-slider')?.value || 1);

    playSection(section, language, speed);
}

function playSection(section, language = 'en-US', speed = 1.0) {
    if (currentUtterance) {
        speechSynthesis.cancel();
    }

    currentSection = section;
    const text = formatAnalysisForSpeech(analysisResults, section);
    
    if (!text) {
        showNotification('No content available for this section', 'warning');
        return;
    }

    currentUtterance = new SpeechSynthesisUtterance(text);
    
    const currentLang = languageManager.currentLanguage;
    const voiceLanguage = language || ENHANCED_LANGUAGE_CONFIG[currentLang].voice;
    
    currentUtterance.lang = voiceLanguage;
    currentUtterance.rate = speed;
    currentUtterance.pitch = 1.0;
    currentUtterance.volume = 1.0;

    const voices = speechSynthesis.getVoices();
    let voice = voices.find(v => v.lang === voiceLanguage);
    if (!voice) {
        voice = voices.find(v => v.lang.startsWith(voiceLanguage.split('-')[0]));
    }
    if (voice) {
        currentUtterance.voice = voice;
    }

    currentUtterance.onstart = () => {
        isPlaying = true;
        updateVoicePlayerUI();
        const playBtn = document.getElementById('play-btn');
        const pauseBtn = document.getElementById('pause-btn');
        if (playBtn) playBtn.style.display = 'none';
        if (pauseBtn) pauseBtn.style.display = 'inline-flex';
        if (floatingVoice) floatingVoice.classList.add('listening');
    };

    currentUtterance.onend = () => {
        isPlaying = false;
        updateVoicePlayerUI();
        const playBtn = document.getElementById('play-btn');
        const pauseBtn = document.getElementById('pause-btn');
        if (playBtn) playBtn.style.display = 'inline-flex';
        if (pauseBtn) pauseBtn.style.display = 'none';
        if (floatingVoice) floatingVoice.classList.remove('listening');
        const currentSection = document.getElementById('voice-current-section');
        if (currentSection) currentSection.textContent = 'Analysis complete';
    };

    currentUtterance.onerror = (event) => {
        console.error('Speech synthesis error:', event);
        showNotification('Voice playback failed. Please try again.', 'error');
        isPlaying = false;
        updateVoicePlayerUI();
    };

    const currentSectionDisplay = document.getElementById('voice-current-section');
    if (currentSectionDisplay) {
        currentSectionDisplay.textContent = `Playing: ${getSectionName(section)}`;
    }
    updateActiveSectionButton(section);

    speechSynthesis.speak(currentUtterance);
}

function pauseAnalysis() {
    if (speechSynthesis && isPlaying) {
        speechSynthesis.pause();
        const playBtn = document.getElementById('play-btn');
        const pauseBtn = document.getElementById('pause-btn');
        if (playBtn) playBtn.style.display = 'inline-flex';
        if (pauseBtn) pauseBtn.style.display = 'none';
        const currentSection = document.getElementById('voice-current-section');
        if (currentSection) currentSection.textContent = 'Paused';
        if (floatingVoice) floatingVoice.classList.remove('listening');
    }
}

function stopAnalysis() {
    if (speechSynthesis) {
        speechSynthesis.cancel();
        isPlaying = false;
        updateVoicePlayerUI();
        const playBtn = document.getElementById('play-btn');
        const pauseBtn = document.getElementById('pause-btn');
        if (playBtn) playBtn.style.display = 'inline-flex';
        if (pauseBtn) pauseBtn.style.display = 'none';
        const currentSection = document.getElementById('voice-current-section');
        if (currentSection) currentSection.textContent = 'Ready to play analysis';
        if (floatingVoice) floatingVoice.classList.remove('listening');
    }
}

function changePlaybackSpeed(speed) {
    const speedDisplay = document.getElementById('speed-display');
    if (speedDisplay) speedDisplay.textContent = speed + 'x';
    
    if (isPlaying) {
        stopAnalysis();
        setTimeout(() => {
            const language = document.getElementById('voice-language')?.value;
            playSection(currentSection, language, parseFloat(speed));
        }, 100);
    }
}

function formatAnalysisForSpeech(analysisData, section = 'all') {
    let speechParts = [];
    const currentLang = languageManager.currentLanguage;
    const config = ENHANCED_LANGUAGE_CONFIG[currentLang];

    try {
        function cleanTextForSpeech(text) {
            return text
                .replace(/[\u{1F600}-\u{1F64F}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu, '')
                .replace(/\*\*(.*?)\*\*/g, '$1')
                .replace(/\*(.*?)\*/g, '$1')
                .replace(/`(.*?)`/g, '$1')
                .replace(/\s+/g, ' ')
                .trim();
        }

        const introductions = {
            'en': {
                summary: 'Document Summary.',
                risks: 'Risk Analysis.',
                timeline: 'Important Dates and Timeline.',
                terms: 'Key Terms Explained.',
                tip: 'Pro tip:',
                disclaimer: 'Remember, this is general information and not legal advice. For specific legal matters, consult with a qualified attorney.'
            },
            'hi': {
                summary: 'दस्तावेज़ सारांश।',
                risks: 'जोखिम विश्लेषण।',
                timeline: 'महत्वपूर्ण तारीखें और समयसीमा।',
                terms: 'मुख्य शब्दों का स्पष्टीकरण।',
                tip: 'विशेषज्ञ सुझाव:',
                disclaimer: 'याद रखें, यह सामान्य जानकारी है और कानूनी सलाह नहीं है।'
            }
        };

        const labels = introductions[currentLang] || introductions['en'];

        if (section === 'all' || section === 'summary') {
            if (analysisData.summary && Array.isArray(analysisData.summary)) {
                speechParts.push(labels.summary);
                analysisData.summary.forEach((item, index) => {
                    const point = typeof item === 'object' ? item : { description: item };
                    const cleanTitle = cleanTextForSpeech(point.title || `Point ${index + 1}`);
                    const cleanDesc = cleanTextForSpeech(point.description || '');
                    speechParts.push(`${cleanTitle}. ${cleanDesc}.`);
                    
                    if (point.example) {
                        const cleanExample = cleanTextForSpeech(point.example);
                        speechParts.push(`For example, ${cleanExample}.`);
                    }
                });
            }
        }

        if (section === 'all' || section === 'risks') {
            if (analysisData.risks && Array.isArray(analysisData.risks)) {
                speechParts.push(labels.risks);
                analysisData.risks.forEach(risk => {
                    const riskData = typeof risk === 'object' ? risk : { description: risk };
                    const severity = riskData.severity || 'medium';
                    const cleanTitle = cleanTextForSpeech(riskData.title || 'Risk');
                    const cleanDesc = cleanTextForSpeech(riskData.description || '');
                    speechParts.push(`${severity} severity risk: ${cleanTitle}. ${cleanDesc}.`);
            
                    if (riskData.mitigation) {
                        const cleanMitigation = cleanTextForSpeech(riskData.mitigation);
                        speechParts.push(`To address this: ${cleanMitigation}.`);
                    }
                });
            }
        }

        if (section === 'all' || section === 'timeline') {
            if (analysisData.timeline && Array.isArray(analysisData.timeline)) {
                speechParts.push(labels.timeline);
                analysisData.timeline.forEach(item => {
                    const timelineData = typeof item === 'object' ? item : { event: item };
                    const cleanDate = cleanTextForSpeech(timelineData.date || 'Important date');
                    const cleanEvent = cleanTextForSpeech(timelineData.event || '');
                    speechParts.push(`${cleanDate}: ${cleanEvent}.`);
                    
                    if (timelineData.action_required) {
                        const cleanAction = cleanTextForSpeech(timelineData.action_required);
                        speechParts.push(`Action required: ${cleanAction}.`);
                    }
                });
            }
        }

        if (section === 'all' || section === 'terms') {
            if (analysisData.key_terms && Array.isArray(analysisData.key_terms)) {
                speechParts.push(labels.terms);
                analysisData.key_terms.forEach(term => {
                    const termData = typeof term === 'object' ? term : { term: term };
                    const cleanTerm = cleanTextForSpeech(termData.term || '');
                    const cleanExplanation = cleanTextForSpeech(termData.explanation || 'Important legal concept');
                    speechParts.push(`${cleanTerm}: ${cleanExplanation}.`);
                });
            }
        }

        if (analysisData.tip && section === 'all') {
            const cleanTip = cleanTextForSpeech(analysisData.tip);
            speechParts.push(`${labels.tip} ${cleanTip}`);
        }

        speechParts.push(labels.disclaimer);

    } catch (error) {
        console.error('Speech formatting error:', error);
        return currentLang === 'en' ? 
            "Analysis completed. Please review the document details on screen." :
            "विश्लेषण पूर्ण हो गया। कृपया स्क्रीन पर दस्तावेज़ विवरण की समीक्षा करें।";
    }

    return speechParts.join(" ");
}

function getSectionName(section) {
    const names = {
        'summary': 'Summary',
        'risks': 'Risks',
        'timeline': 'Timeline',
        'terms': 'Key Terms',
        'all': 'Full Analysis'
    };
    return names[section] || 'Analysis';
}

function updateActiveSectionButton(section) {
    document.querySelectorAll('.voice-section-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    const activeBtn = document.querySelector(`[onclick*="${section}"]`);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }
}

function updateVoicePlayerUI() {
    if (isPlaying) {
        if (floatingVoice) floatingVoice.classList.add('listening');
    } else {
        if (floatingVoice) floatingVoice.classList.remove('listening');
    }
}

function speakText(text) {
    if (!speechSynthesis) {
        showNotification('Speech synthesis not supported', 'error');
        return;
    }

    if (currentUtterance) {
        speechSynthesis.cancel();
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    speechSynthesis.speak(utterance);
}

function toggleVoiceWidget() {
    if (analysisResults) {
        playAnalysis();
    } else {
        showNotification('No analysis available to play. Upload a document or enter text first.', 'warning');
    }
}

function changeVoiceLanguage() {
    const voiceSelect = document.getElementById('voice-language');
    if (!voiceSelect) return;
    
    const selectedVoice = voiceSelect.value;
    
    const matchingLang = Object.entries(ENHANCED_LANGUAGE_CONFIG).find(([code, config]) => 
        config.voice === selectedVoice || selectedVoice.startsWith(code)
    );
    
    if (matchingLang && matchingLang[0] !== languageManager.currentLanguage) {
        const languageSelect = document.getElementById('language-select');
        if (languageSelect) {
            languageSelect.value = matchingLang[0];
            languageManager.changeLanguage(matchingLang[0]);
        }
    }
    
    if (isPlaying) {
        stopAnalysis();
        setTimeout(() => playSection(currentSection, selectedVoice), 100);
    }
}

// =========================
// UTILITY FUNCTIONS
// =========================
function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(content => {
        content.style.display = 'none';
    });

    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });

    const selectedContent = document.getElementById(`tab-${tabName}`);
    if (selectedContent) {
        selectedContent.style.display = 'block';
    }

    const selectedTab = document.querySelector(`[data-tab="${tabName}"]`);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
}

function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    if (notification) {
        notification.textContent = message;
        notification.className = `notification ${type}`;
        notification.style.display = 'block';

        setTimeout(() => {
            notification.style.display = 'none';
        }, 5000);
    }
}

function changeLanguage() {
    const selectedLang = document.getElementById('language-select').value;
    languageManager.changeLanguage(selectedLang);
}

function setupCharacterCounter() {
    const charCount = document.getElementById('char-count');
    if (textInput && charCount) {
        textInput.addEventListener('input', function() {
            const count = this.value.length;
            charCount.textContent = count;
            
            if (count > 45000) {
                charCount.style.color = '#dc2626';
            } else if (count > 40000) {
                charCount.style.color = '#d97706';
            } else {
                charCount.style.color = '#6b7280';
            }
        });
    }
}

async function checkServerStatus() {
    try {
        const data = await checkHealthAPI();
        
        if (data.status === 'healthy') {
            console.log('✅ Server is running properly');
            addServerIndicator('online');
        } else {
            console.warn('⚠️ Server health check failed');
            addServerIndicator('warning');
        }
    } catch (error) {
        console.error('❌ Server connection failed:', error);
        
        let message = 'Server connection failed.';
        if (error instanceof APIError) {
            message += ` Status: ${error.status}`;
        } else {
            message += ' Please start Flask app on the correct port.';
        }
        
        showNotification(message, 'error');
        addServerIndicator('offline');
    }
}

function addServerIndicator(status) {
    const existing = document.querySelector('.server-indicator');
    if (existing) existing.remove();

    const indicator = document.createElement('div');
    indicator.className = 'server-indicator';
    indicator.style.cssText = `
        position: fixed; top: 10px; left: 10px; 
        width: 12px; height: 12px; 
        border-radius: 50%; 
        z-index: 1000;
        transition: all 0.3s ease;
    `;

    const colors = {
        online: '#10b981',
        warning: '#d97706', 
        offline: '#dc2626'
    };

    const titles = {
        online: 'Server Online',
        warning: 'Server Warning',
        offline: 'Server Offline'
    };

    indicator.style.background = colors[status];
    indicator.title = titles[status];
    
    if (status === 'online') {
        indicator.style.boxShadow = `0 0 8px ${colors[status]}40`;
    }

    document.body.appendChild(indicator);
}

// =========================
// ERROR HANDLING FUNCTIONS
// =========================
function detectErrorType(error, response = null) {
    if (error && (error.message.includes('Failed to fetch') || error.name === 'TypeError')) {
        return 'network_error';
    }
    
    if (response) {
        if (response.status >= 500) return 'server_error';
        if (response.status === 413) return 'file_too_large';
        if (response.status === 401) return 'login_required';
        if (response.status === 415) return 'invalid_file';
    }
    
    if (error && error.message) {
        if (error.message.includes('File too large')) return 'file_too_large';
        if (error.message.includes('login') || error.message.includes('authentication')) return 'login_required';
        if (error.message.includes('file') || error.message.includes('format')) return 'invalid_file';
    }
    
    return 'analysis_failed';
}

function showEnhancedError(errorType, details = null) {
    console.log('🚨 Showing enhanced error:', errorType, details);
    
    const error = ERROR_MESSAGES[errorType] || ERROR_MESSAGES['server_error'];
    
    const errorContainer = document.createElement('div');
    errorContainer.className = 'enhanced-error-container';
    errorContainer.innerHTML = `
        <div class="error-header">
            <div class="error-icon">⚠</div>
            <div class="error-title">${error.title}</div>
            <button class="error-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
        <div class="error-message">
            ${error.message}
            ${details ? `<br><small style="opacity: 0.8;">Details: ${details}</small>` : ''}
        </div>
        <div class="error-suggestions">
            <h4>💡 What you can do:</h4>
            <ul>
                ${error.suggestions.map(suggestion => `<li>${suggestion}</li>`).join('')}
            </ul>
        </div>
        <div class="error-actions">
            <button class="btn btn-secondary" onclick="this.parentElement.parentElement.remove()">Dismiss</button>
            <button class="btn" onclick="contactSupport('${errorType}')">Get Help</button>
        </div>
    `;
    
    errorContainer.style.cssText = `
        background: linear-gradient(135deg, #fef2f2, #fee2e2);
        border: 1px solid #fecaca;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 20px rgba(220, 38, 38, 0.1);
        animation: slideInDown 0.4s ease;
    `;
    
    try {
        const targetElement = document.querySelector('.main-grid') || document.querySelector('.container');
        if (targetElement) {
            targetElement.appendChild(errorContainer);
        } else {
            document.body.appendChild(errorContainer);
        }
    } catch (insertError) {
        console.error('Error inserting error message:', insertError);
        alert(`${error.title}: ${error.message}${details ? ` Details: ${details}` : ''}`);
    }
    
    setTimeout(() => {
        try {
            if (errorContainer.parentNode) {
                errorContainer.style.animation = 'slideOutUp 0.4s ease';
                setTimeout(() => errorContainer.remove(), 400);
            }
        } catch (removeError) {
            console.warn('Error auto-removing error message:', removeError);
        }
    }, 15000);
}

function contactSupport(errorType) {
    const supportInfo = `
🛠️ MyVakeel Support Information

Error Type: ${errorType}
Browser: ${navigator.userAgent}
Time: ${new Date().toISOString()}

📧 Email: support@myvakeel.com
💬 Chat: Available on our website
📱 Phone: +91-XXXX-XXXX (Mon-Fri, 9AM-6PM)

🔧 Quick Self-Help:
1. Try refreshing the page
2. Clear your browser cache
3. Try in Chrome or Edge browser
4. Check if your internet is stable
    `;
    
    alert(supportInfo);
}

function safeSetHTML(element, content) {
    const safeContent = content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
    
    element.innerHTML = safeContent;
}

// =========================
// DEBUG FUNCTIONS
// =========================
async function testServerConnection() {
    console.log('🔍 Testing server connection...');
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        console.log('✅ Server connection test result:', data);
        showNotification('Server connection: OK', 'success');
        return true;
    } catch (error) {
        console.error('❌ Server connection test failed:', error);
        showNotification('Server connection: FAILED - Is Flask running on port 5000?', 'error');
        return false;
    }
}

async function debugAnalysis() {
    console.log('🔧 Starting debug analysis...');
    
    console.log('1️⃣ Checking DOM elements...');
    console.log('- fileInput:', !!fileInput);
    console.log('- textInput:', !!textInput);
    console.log('- analyzeFileBtn:', !!analyzeFileBtn);
    console.log('- analyzeTextBtn:', !!analyzeTextBtn);
    console.log('- currentUser:', currentUser);
    
    console.log('2️⃣ Testing server connection...');
    await testServerConnection();
    
    console.log('3️⃣ Testing API manager...');
    console.log('- apiManager:', !!apiManager);
    if (apiManager) {
        console.log('- baseURL:', apiManager.baseURL);
    }
    
    console.log('🔧 Debug analysis complete. Check console for results.');
}

// =========================
// GLOBAL FUNCTIONS (for HTML onclick handlers)
// =========================
window.showLoginModal = showLoginModal;
window.logout = logout;
window.showAdminLogin = showAdminLogin;
window.closeAdminModal = closeAdminModal;
window.adminLogin = adminLogin;
window.togglePasswordVisibility = togglePasswordVisibility;
window.toggleVoiceInput = toggleVoiceInput;
window.playAnalysis = playAnalysis;
window.playSection = playSection;
window.pauseAnalysis = pauseAnalysis;
window.stopAnalysis = stopAnalysis;
window.changeLanguage = changeLanguage;
window.changeVoiceLanguage = changeVoiceLanguage;
window.changePlaybackSpeed = changePlaybackSpeed;
window.toggleVoiceWidget = toggleVoiceWidget;
window.contactSupport = contactSupport;
window.testServerConnection = testServerConnection;
window.debugAnalysis = debugAnalysis;

// =========================
// INITIALIZATION
// =========================
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM Content Loaded - Initializing MyVakeel...');
    
    // Add error handling styles
    const errorStyles = document.createElement('style');
    errorStyles.textContent = `
        @keyframes slideInDown {
            from { opacity: 0; transform: translateY(-30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes slideOutUp {
            from { opacity: 1; transform: translateY(0); }
            to { opacity: 0; transform: translateY(-30px); }
        }
        .enhanced-error-container .error-header {
            display: flex; align-items: center; justify-content: space-between;
            margin-bottom: 1rem; font-weight: bold; color: #dc2626;
        }
        .enhanced-error-container .error-icon {
            background: #dc2626; color: white; width: 30px; height: 30px;
            border-radius: 50%; display: flex; align-items: center; justify-content: center;
        }
        .enhanced-error-container .error-close {
            background: none; border: none; font-size: 1.5rem; cursor: pointer;
            color: #666; padding: 0; width: 30px; height: 30px;
        }
        .enhanced-error-container .error-actions {
            display: flex; gap: 1rem; margin-top: 1rem;
        }
    `;
    document.head.appendChild(errorStyles);
    
    // Initialize the application
    initializeApp();
    
    // Set up language callback
    if (languageManager) {
        languageManager.onLanguageChange((langCode, config) => {
            if (recognition && recognition.lang !== config.code) {
                recognition.lang = config.code;
                
                if (isListening) {
                    stopVoiceInput();
                    setTimeout(startVoiceInput, 300);
                }
            }
            
            const voiceStatus = document.getElementById('voice-status');
            if (voiceStatus && voiceStatus.style.display !== 'none') {
                const voiceText = document.getElementById('voice-text');
                if (voiceText) voiceText.textContent = config.ui.listening;
            }
        });
    }
    
    // Add input event listener to remove error class when typing
    const emailInputElement = document.getElementById('email-input');
    if (emailInputElement) {
        emailInputElement.addEventListener('input', function() {
            this.classList.remove('error');
        });
    }
    
    console.log('✅ MyVakeel fully initialized and ready!');
});

// =========================
// EXPORT FOR TESTING (if needed)
// =========================
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        APIManager,
        LanguageManager,
        initializeApp,
        analyzeFile,
        analyzeText,
        handleChatMessage
    };
}