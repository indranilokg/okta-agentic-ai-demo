'use client';

import { useState, useEffect, useRef } from 'react';
import { useSession, signIn, signOut } from 'next-auth/react';
import { checkAndTriggerCustomAuth } from '@/lib/custom-auth';
import IdTokenCard from '@/components/IdTokenCard';
import RAGCard from '@/components/RAGCard';
import AgentFlowCard from '@/components/AgentFlowCard';
import MCPCard from '@/components/MCPCard';
import PromptLibrary from '@/components/PromptLibrary';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface RAGInfo {
  query: string;
  documents_count: number;
  context_preview: string;
}

interface MCPInfo {
  server: string;
  tools_called: string[];
}

interface AgentFlowStep {
  agent: string;
  step: number;
  timestamp: string;
  token_exchange: {
    from: string;
    to: string;
    audience: string;
  };
}

interface TokenExchange {
  from: string;
  to: string;
  audience: string;
  scope: string;
  token: string;
}

export default function StreamwardAssistant() {
  const { data: session, status } = useSession();
  
  // Check for logout state on mount and clear flag if user is authenticated
  useEffect(() => {
    const justLoggedOut = sessionStorage.getItem('just-logged-out') === 'true';
    const urlParams = new URLSearchParams(window.location.search);
    const fromLogout = urlParams.get('from_logout') === 'true';
    const logoutSuccess = urlParams.get('logout') === 'success';
    
    // Handle successful logout redirect from Okta
    if (logoutSuccess) {
      console.log('[PAGE] Logout success parameter detected');
      sessionStorage.setItem('just-logged-out', 'true');
      // Clean up URL
      const newUrl = window.location.pathname;
      window.history.replaceState({}, '', newUrl);
      return;
    }
    
    // If user is authenticated, clear the logout flag (fresh login)
    if (status === 'authenticated' && session && justLoggedOut) {
      console.log('[PAGE] User authenticated - clearing logout flag');
      sessionStorage.removeItem('just-logged-out');
      // Clean up URL if from_logout param is present
      if (fromLogout) {
        const newUrl = window.location.pathname;
        window.history.replaceState({}, '', newUrl);
      }
    } else if (justLoggedOut || fromLogout) {
      console.log('[PAGE] Logout state detected - preventing re-auth');
      // Set flag if from_logout param is present but flag not set
      if (fromLogout && !justLoggedOut) {
        sessionStorage.setItem('just-logged-out', 'true');
      }
      // Clear the flag after a shorter delay (user likely already logged back in)
      setTimeout(() => {
        sessionStorage.removeItem('just-logged-out');
        console.log('[PAGE] Logout flag cleared');
      }, 2000); // Reduced from 5s to 2s
    }
  }, [status, session]);
  
  // Log tokens on client side
  useEffect(() => {
    if (status === 'authenticated' && session) {
      console.log(`[SESSION] Tokens available: idToken=${!!session.idToken}, customToken=${!!session.customAccessToken}`);
      console.debug(`[SESSION] Org ID Token (first 50): ${session.idToken?.substring(0, 50) || 'N/A'}`);
      console.debug(`[SESSION] Custom Access Token (first 50): ${session.customAccessToken?.substring(0, 50) || 'N/A'}`);
    }
  }, [status, session]);
  
  // Automatically trigger custom server OAuth flow after org auth succeeds
  useEffect(() => {
    if (status === 'authenticated' && session) {
      // Check if we just logged out - don't trigger custom auth
      const justLoggedOut = sessionStorage.getItem('just-logged-out') === 'true';
      const urlParams = new URLSearchParams(window.location.search);
      const fromLogout = urlParams.get('from_logout') === 'true';
      const logoutSuccess = urlParams.get('logout') === 'success';
      
      // Skip custom auth if user just logged out
      if (justLoggedOut || fromLogout || logoutSuccess) {
        if (session.customAccessToken && !logoutSuccess) {
          // User has custom token and NOT coming from logout - they're properly logged in
          console.log('[CUSTOM_AUTH] User has custom token - clearing logout flag');
          sessionStorage.removeItem('just-logged-out');
        } else {
          // No custom token and coming from logout - skip completely
          console.log('[CUSTOM_AUTH] Skipping - user just logged out');
          return;
        }
      }
      
      // Check if custom token is needed and trigger OAuth flow
      checkAndTriggerCustomAuth(!!session.customAccessToken);
    }
  }, [status, session]);
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const [ragInfo, setRagInfo] = useState<RAGInfo | null>(null);
  const [mcpInfo, setMcpInfo] = useState<MCPInfo | null>(null);
  const [mcpQuery, setMcpQuery] = useState<string | null>(null);
  const [agentFlow, setAgentFlow] = useState<AgentFlowStep[] | null>(null);
  const [tokenExchanges, setTokenExchanges] = useState<TokenExchange[] | null>(null);
  const [workflowType, setWorkflowType] = useState<string | null>(null);
  const [sourceUserToken, setSourceUserToken] = useState<string | null>(null);
  
  // Log agent flow state changes
  useEffect(() => {
    console.debug(`[AGENT_FLOW] State: flowLength=${agentFlow?.length || 0}, hasTokenExchanges=${!!tokenExchanges}, workflowType=${workflowType}`);
  }, [agentFlow, tokenExchanges, workflowType, sourceUserToken]);
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
    const features = [
      {
        icon: (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            <circle cx="12" cy="8" r="2" fill="currentColor" />
          </svg>
        ),
        title: "Employee Management",
        description: "HR workflows & data"
      },
      {
        icon: (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
        ),
        title: "Partner Integration",
        description: "External systems"
      },
      {
        icon: (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        ),
        title: "Policy Compliance",
        description: "Legal & security"
      },
      {
        icon: (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        ),
        title: "AI Workflows",
        description: "Automated processes"
      }
    ];

    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-purple-900 flex">
        {/* Left Panel - Login Card */}
        <div className="w-full lg:w-2/5 flex items-center justify-center p-8">
          <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8">
            {/* Logo */}
            <div className="mb-8">
              <div className="flex items-center space-x-2 mb-4">
                <span className="text-3xl font-bold text-orange-500">Streamward</span>
                <svg className="w-6 h-6 text-orange-500" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z"/>
                </svg>
              </div>
              <h1 className="text-2xl font-bold text-gray-900 mb-1">Streamward AI</h1>
              <p className="text-lg text-gray-700">Enterprise AI Assistant</p>
            </div>

            {/* Welcome Message */}
            <div className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-2">Welcome Back</h2>
              <p className="text-gray-600">
                Sign in to access your intelligent enterprise assistant
              </p>
            </div>

            {/* Sign In Button */}
            <button
              onClick={() => signIn('okta')}
              className="w-full flex items-center justify-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white font-medium py-4 px-6 rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>Sign in with Okta</span>
            </button>

            {/* Security Note */}
            <p className="text-sm text-gray-500 text-center mt-4">
              Secure enterprise authentication
            </p>
          </div>
        </div>

        {/* Right Panel - Features */}
        <div className="hidden lg:flex lg:w-3/5 flex-col justify-center px-12 py-16">
          <div className="max-w-2xl">
            {/* Title */}
            <h2 className="text-5xl font-bold text-white mb-4">
              Enterprise AI Assistant
            </h2>
            <p className="text-xl text-blue-100 mb-12">
              Secure, intelligent, and always available
            </p>

            {/* Feature Cards Grid */}
            <div className="grid grid-cols-2 gap-6">
              {features.map((feature, index) => (
                <div
                  key={index}
                  className="bg-blue-800/40 backdrop-blur-sm rounded-xl p-6 border border-blue-700/30 hover:bg-blue-800/50 transition-all duration-200"
                >
                  <div className="text-white mb-3">
                    {feature.icon}
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-1">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-blue-200">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
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
    // Clear previous MCP info when starting a new message
    setMcpInfo(null);
    setMcpQuery(null);
    setIsTyping(true);

    try {
      // Extract tokens from session for ID-JAG exchange
      const idToken = session?.idToken;
      const accessToken = session?.customAccessToken;
      
      // Log token availability
      console.log(`[MESSAGE] Sending tokens: idToken=${!!idToken}, accessToken=${!!accessToken}`);
      
      // Prepare message with tokens
      const messageWithTokens = {
        ...userMessage,
        id_token: idToken,
        access_token: accessToken,
      };
      
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // Also send tokens in headers for additional security/flexibility
          ...(idToken && { 'X-ID-Token': idToken }),
          ...(accessToken && { 'X-Access-Token': accessToken }),
        },
        body: JSON.stringify({
          messages: [...messages, messageWithTokens],
          session_id: sessionId,
        }),
      });

      const data = await response.json();
      
      // Log response summary
      console.log(`[RESPONSE] workflow=${data.workflow_info?.workflow_type}, hasAgentFlow=${Array.isArray(data.agent_flow)}, usedRag=${data.used_rag}, hasMcp=${!!data.mcp_info}`);
      console.debug(`[RESPONSE] Full response keys: ${Object.keys(data).join(', ')}`);
      
      // Update RAG info if RAG was used
      if (data.used_rag && data.rag_info) {
        setRagInfo({
          query: data.rag_info.query || userMessage.content,
          documents_count: data.rag_info.documents_count || 0,
          context_preview: data.rag_info.context_preview || ''
        });
      } else {
        // Clear RAG info if not used
        setRagInfo(null);
      }
      
      // Update MCP info if MCP was used
      if (data.mcp_info) {
        setMcpInfo({
          server: data.mcp_info.server || 'unknown',
          tools_called: data.mcp_info.tools_called || [],
          id_jag_token: data.mcp_info.id_jag_token,
          mcp_access_token: data.mcp_info.mcp_access_token,
          expires_in: data.mcp_info.expires_in,
          scope: data.mcp_info.scope
        });
        setMcpQuery(userMessage.content);
      } else {
        // Clear MCP info if not used
        setMcpInfo(null);
        setMcpQuery(null);
      }
      
      // Update agent flow info if workflow was executed
      const hasAgentFlow = data.agent_flow && Array.isArray(data.agent_flow) && data.agent_flow.length > 0;
      console.log(`[AGENT_FLOW] Received: count=${data.agent_flow?.length || 0}, hasTokenExchanges=${!!data.token_exchanges}`);
      
      if (hasAgentFlow) {
        console.log(`[AGENT_FLOW] Setting flow data with ${data.agent_flow.length} steps`);
        setAgentFlow(data.agent_flow);
        setTokenExchanges(data.token_exchanges || null);
        setWorkflowType(data.workflow_info?.workflow_type || null);
        setSourceUserToken(data.source_user_token || null);
      } else {
        console.log(`[AGENT_FLOW] No workflow data received - clearing`);
        // Always clear on next prompt (hide card when no workflow data)
        setAgentFlow(null);
        setTokenExchanges(null);
        setWorkflowType(null);
        setSourceUserToken(null);
      }
      
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

  const handleLogout = async () => {
    try {
      // Set logout flag to prevent custom auth from triggering
      // Store timestamp so we can detect stale flags
      sessionStorage.setItem('just-logged-out', 'true');
      sessionStorage.setItem('just-logged-out-time', Date.now().toString());
      
      // IMPORTANT: Get ID token from session BEFORE calling signOut (session will be cleared)
      const idToken = session?.idToken;
      console.log(`[LOGOUT] Starting logout with idToken=${!!idToken}`);
      
      // Clear client-side storage first
      sessionStorage.removeItem('custom-auth-initiated');
      sessionStorage.removeItem('custom-auth-state');
      sessionStorage.removeItem('custom-auth-verifier');
      console.debug('[LOGOUT] Cleared sessionStorage');
      
      // Sign out from NextAuth - this clears the session cookie
      // Use redirect: false so we can handle cookie clearing and Okta logout
      await signOut({ 
        callbackUrl: window.location.origin,
        redirect: false
      });
      
      // Store ID token temporarily in a client-side cookie so the signout endpoint can access it
      // This avoids putting the full JWT in the URL (which can exceed URL length limits)
      if (idToken) {
        // Set a temporary cookie that will be cleared by the signout endpoint
        // Use Secure flag in production, Lax SameSite for cross-site handling
        const isProduction = process.env.NODE_ENV === 'production';
        const secureFlagStr = isProduction ? '; Secure' : '';
        document.cookie = `temp-logout-id-token=${encodeURIComponent(idToken)}; path=/; max-age=60; SameSite=Lax${secureFlagStr}`;
        console.log('[LOGOUT] Stored ID token in temporary cookie');
      }
      
      // Add a small delay to ensure cookie is written before redirect
      // This prevents race conditions between cookie setting and redirect
      await new Promise(resolve => setTimeout(resolve, 50));
      
      // Simple direct logout to Okta - no complex API coordination
      // This is the same approach used in okta-cross-app-access-demo and it works!
      console.log('[LOGOUT] Redirecting directly to Okta logout');
      
      const oktaBaseUrl = process.env.NEXT_PUBLIC_OKTA_BASE_URL || 'https://your-domain.okta.com';
      
      // Use OIDC logout with id_token_hint (WITHOUT post_logout_redirect_uri which causes issues)
      if (idToken) {
        const oktaLogoutUrl = `${oktaBaseUrl}/oauth2/v1/logout?id_token_hint=${encodeURIComponent(idToken)}`;
        console.log('[LOGOUT] Using Okta logout URL with id_token_hint');
        window.location.href = oktaLogoutUrl;
      } else {
        console.log('[LOGOUT] No idToken, redirecting to home');
        window.location.href = '/';
      }
    } catch (error) {
      console.error(`[LOGOUT] ERROR: ${error instanceof Error ? error.message : String(error)}`);
      // Even on error, redirect to home page with logout flag
      sessionStorage.setItem('just-logged-out', 'true');
      window.location.href = '/';
    }
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
              <PromptLibrary 
                onSelectPrompt={(prompt) => {
                  setInput(prompt);
                  // Focus the input field after a short delay
                  setTimeout(() => {
                    inputRef.current?.focus();
                  }, 100);
                }} 
              />
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
                      ref={inputRef}
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
                    <span> Secure chat</span>
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

          {/* Sidebar - Token Card, RAG Card, Agent Flow Card, A2A Card, and System Status */}
          <div className="lg:col-span-1">
            <div className="sticky top-6 space-y-4">
              <IdTokenCard idToken={session?.idToken || ''} />
              <RAGCard ragInfo={ragInfo} />
              <MCPCard mcpInfo={mcpInfo} query={mcpQuery || undefined} />
              {/* Agent Flow Card - Always visible */}
              <AgentFlowCard 
                agentFlow={agentFlow} 
                tokenExchanges={tokenExchanges}
                workflowType={workflowType || undefined}
                sourceUserToken={sourceUserToken}
              />
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
