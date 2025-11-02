'use client';

import { useState, useEffect } from 'react';
import { useSession, signIn, signOut } from 'next-auth/react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export default function StreamwardAssistant() {
  const { data: session, status } = useSession();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId, setSessionId] = useState<string>(() => {
    // Generate a session ID that persists across page reloads
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('streamward-session-id');
      if (stored) return stored;
      const newId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('streamward-session-id', newId);
      return newId;
    }
    return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  });

  // Initialize with welcome message
  useEffect(() => {
    if (session && messages.length === 0) {
      setMessages([
        {
          id: '1',
          content: 'Welcome to Streamward AI Assistant! I can help you with employee information, partner data, policy lookups, and complex workflows. How can I assist you today?',
          role: 'assistant',
          timestamp: new Date()
        }
      ]);
    }
  }, [session, messages.length]);

  // Show loading while checking authentication
  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full flex items-center justify-center mx-auto mb-4 animate-pulse">
            <img 
              src="/streamward-icon.png" 
              alt="Streamward" 
              className="w-8 h-8"
            />
          </div>
          <h2 className="text-xl font-semibold text-gray-900">Loading Streamward AI...</h2>
          <p className="text-gray-600 mt-2">Please wait while we check your authentication status.</p>
        </div>
      </div>
    );
  }

  // Show sign in page if not authenticated
  if (status === 'unauthenticated') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <img 
              src="/streamward-icon.png" 
              alt="Streamward" 
              className="w-8 h-8"
            />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Welcome to Streamward AI!</h2>
          <p className="text-gray-600 mb-6">Please sign in to access the Enterprise AI Assistant.</p>
          <button
            onClick={() => signIn('okta')}
            className="px-6 py-3 bg-gradient-to-r from-indigo-500 to-purple-500 text-white rounded-lg hover:from-indigo-600 hover:to-purple-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-200"
          >
            Sign in with Okta
          </button>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setIsTyping(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [...messages, userMessage],
          session_id: sessionId,
        }),
      });

      const data = await response.json();
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.content || 'I received your message. The backend is not yet connected.',
        timestamp: new Date(),
      };

      setTimeout(() => {
        setMessages(prev => [...prev, assistantMessage]);
        setIsTyping(false);
      }, 1000); // Simulate typing delay
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
      setIsTyping(false);
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const suggestedQuestions = [
    "What are Streamward's company policies?",
    "How do I submit an expense report?",
    "What's the IT support process?",
    "Tell me about employee benefits",
    "How do I request time off?",
    "What's the dress code policy?"
  ];

  const handleLogout = () => {
    // First, sign out from NextAuth
    signOut({ 
      callbackUrl: '/',
      redirect: false 
    }).then(() => {
      // Then redirect to Okta logout with proper parameters
      const oktaBaseUrl = process.env.NEXT_PUBLIC_OKTA_BASE_URL || 'https://ijtestcustom.oktapreview.com';
      const clientId = process.env.NEXT_PUBLIC_OKTA_CLIENT_ID;
      
      // Use OIDC logout with id_token_hint if available (with post_logout_redirect_uri)
      if (clientId && session?.idToken) {
        const oktaLogoutUrl = `${oktaBaseUrl}/oauth2/v1/logout?id_token_hint=${session.idToken}&post_logout_redirect_uri=${encodeURIComponent('http://localhost:3000')}`;
        window.location.href = oktaLogoutUrl;
      } else if (clientId) {
        // Fallback to client_id based logout (with post_logout_redirect_uri)
        const oktaLogoutUrl = `${oktaBaseUrl}/oauth2/v1/logout?client_id=${clientId}&post_logout_redirect_uri=${encodeURIComponent('http://localhost:3000')}`;
        window.location.href = oktaLogoutUrl;
      } else {
        // Fallback to basic logout
        const oktaLogoutUrl = `${oktaBaseUrl}/login/signout`;
        window.location.href = oktaLogoutUrl;
      }
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-lg flex items-center justify-center">
                <img 
                  src="/streamward-icon.png" 
                  alt="Streamward" 
                  className="w-6 h-6"
                />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Streamward AI Assistant</h1>
                <p className="text-sm text-gray-500">Powered by AI • Secure • Confidential</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm text-gray-500">Online</span>
              </div>

              {session?.user && (
                <div className="flex items-center space-x-3">
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900">{session.user.name}</p>
                    <p className="text-xs text-gray-500">{session.user.email}</p>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
                  >
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Chat Interface */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
              {/* Chat Messages */}
              <div className="h-[70vh] overflow-y-auto p-6 bg-gradient-to-b from-gray-50 to-white">
                {messages.length === 0 ? (
                  <div className="text-center py-12">
                    <div className="w-16 h-16 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full flex items-center justify-center mx-auto mb-4">
                      <img 
                        src="/streamward-icon.png" 
                        alt="Streamward" 
                        className="w-8 h-8"
                      />
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900 mb-2">Welcome to Streamward AI!</h2>
                    <p className="text-gray-600 mb-6 max-w-md mx-auto">
                      I'm your AI assistant, here to help with company policies, HR questions, IT support, and more.
                    </p>
                    
                    {/* Suggested Questions */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl mx-auto">
                      {suggestedQuestions.map((question, index) => (
                        <button
                          key={index}
                          onClick={() => setInput(question)}
                          className="text-left p-3 bg-white border border-gray-200 rounded-lg hover:border-indigo-300 hover:bg-indigo-50 transition-all duration-200 text-sm text-gray-700 hover:text-indigo-700"
                        >
                          {question}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {messages.map((message) => (
                      <div
                        key={message.id}
                        className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-xs lg:max-w-md px-4 py-3 rounded-2xl ${
                            message.role === 'user'
                              ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white'
                              : 'bg-white border border-gray-200 text-gray-800 shadow-sm'
                          }`}
                        >
                          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                          <p className={`text-xs mt-2 ${
                            message.role === 'user' ? 'text-indigo-100' : 'text-gray-400'
                          }`}>
                            {formatTime(message.timestamp)}
                          </p>
                        </div>
                      </div>
                    ))}
                    
                    {isTyping && (
                      <div className="flex justify-start">
                        <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3 shadow-sm">
                          <div className="flex items-center space-x-2">
                            <div className="flex space-x-1">
                              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                            </div>
                            <span className="text-sm text-gray-500">Streamward Assistant is typing...</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Input Area */}
              <div className="border-t border-gray-100 p-4 bg-white">
                <form onSubmit={handleSubmit} className="flex items-end space-x-3">
                  <div className="flex-1 relative">
                    <input
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder="Ask me anything about Streamward policies, benefits, or procedures..."
                      className="w-full p-4 pr-12 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none text-gray-900 placeholder-gray-500"
                      disabled={isLoading}
                    />
                    <button
                      type="submit"
                      disabled={isLoading || !input.trim()}
                      className="absolute right-2 bottom-2 p-2 bg-gradient-to-r from-indigo-500 to-purple-500 text-white rounded-lg hover:from-indigo-600 hover:to-purple-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                      </svg>
                    </button>
                  </div>
                </form>
                
                {/* Quick Actions */}
                <div className="flex items-center justify-between mt-3 text-xs text-gray-500">
                  <div className="flex items-center space-x-4">
                    <span>💬 Secure chat</span>
                    <span>🔒 End-to-end encrypted</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span>Powered by AI</span>
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar - System Status */}
          <div className="lg:col-span-1">
            <div className="sticky top-6 space-y-4">
              <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">System Status</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">AI Assistant</span>
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      <span className="text-xs text-green-600">Active</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Authentication</span>
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      <span className="text-xs text-green-600">Secure</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Data Privacy</span>
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      <span className="text-xs text-green-600">Protected</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-6">
          <p className="text-sm text-gray-500">
            © 2024 Streamward Corporation. This assistant is designed to help with company-related inquiries.
          </p>
        </div>
      </div>
    </div>
  );
}
