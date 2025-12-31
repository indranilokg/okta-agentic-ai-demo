'use client';

import { useState, useEffect, useRef } from 'react';
import { useSession, signIn, signOut } from 'next-auth/react';
import IdTokenCard from '@/components/IdTokenCard';
import RAGCard from '@/components/RAGCard';
import AgentFlowCard from '@/components/AgentFlowCard';
import MCPCard from '@/components/MCPCard';
import ConnectedAccountsCard from '@/components/ConnectedAccountsCard';
import PromptLibrary from '@/components/PromptLibrary';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  prompt_category?: string;
  requiresLinking?: {
    authorization_url: string;
    state?: string;
  };
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
      console.log(`[SESSION] Tokens available: idToken=${!!session.idToken} (for logout), accessToken=${!!session.accessToken} (for chat)`);
      console.debug(`[SESSION] ID Token (first 50): ${session.idToken?.substring(0, 50) || 'N/A'}`);
      console.debug(`[SESSION] Access Token (first 50): ${session.accessToken?.substring(0, 50) || 'N/A'}`);
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
  const [requiresLinking, setRequiresLinking] = useState<{
    authorization_url: string;
    auth_session?: string;
    state?: string;
    originalRequest?: {
      messages: Message[];
      session_id: string;
    };
  } | null>(null);
  const [pendingLinkingRequest, setPendingLinkingRequest] = useState<{
    messages: Message[];
    session_id: string;
  } | null>(null);
  const popupRef = useRef<Window | null>(null);
  const [connectedAccountsFlow, setConnectedAccountsFlow] = useState<any>(null);
  const [connectedAccountsQuery, setConnectedAccountsQuery] = useState<string | null>(null);
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
  
  // Handle popup postMessage from authorization callback
  useEffect(() => {
    console.log('[POPUP] Setting up message listener...');
    
    const handleMessage = async (event: MessageEvent) => {
      console.log('[POPUP] ===== MESSAGE RECEIVED =====');
      console.log('[POPUP] Origin:', event.origin);
      console.log('[POPUP] Expected origin:', window.location.origin);
      console.log('[POPUP] Data:', event.data);
      console.log('[POPUP] Data type:', typeof event.data);
      console.log('[POPUP] Has pending request:', !!pendingLinkingRequest);
      
      // Verify origin for security
      if (event.origin !== window.location.origin) {
        console.warn('[POPUP] ⚠️ Ignoring message from different origin:', event.origin, 'expected:', window.location.origin);
        return;
      }

      // Only process messages that have a type field (our messages)
      if (!event.data || typeof event.data !== 'object' || !event.data.type) {
        console.log('[POPUP] ⚠️ Ignoring message without type:', event.data);
        return;
      }

      console.log('[POPUP] ✅ Processing message type:', event.data.type);

      if (event.data.type === 'GOOGLE_AUTH_CODE_RECEIVED') {
        console.log('[POPUP] ✅ Received GOOGLE_AUTH_CODE_RECEIVED message');
        console.log('[POPUP] Connect code:', event.data.connect_code);
        console.log('[POPUP] State:', event.data.state);
        console.log('[POPUP] Full message data:', event.data);
        
        // Close popup reference
        if (popupRef.current) {
          console.log('[POPUP] Clearing popup reference');
          popupRef.current = null;
        }
        
        // Call backend to complete linking (backend has auth_session stored server-side)
        if (event.data.connect_code) {
          console.log('[POPUP] Calling backend to complete linking...');
          setIsLoading(true);
          
          try {
            const accessToken = session?.accessToken;
            const response = await fetch('/api/resource/google-workspace/complete-linking', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                ...(accessToken && { 'X-Access-Token': accessToken }),
              },
              body: JSON.stringify({
                connect_code: event.data.connect_code
              }),
            });

            const linkingData = await response.json();
            
            if (!response.ok) {
              throw new Error(linkingData.error || 'Failed to complete linking');
            }
            
            console.log('[POPUP] Linking completed successfully:', {
              has_token: !!linkingData.token,
              success: linkingData.success
            });
            
            // Now retry the original request
            if (pendingLinkingRequest) {
              console.log('[POPUP] Retrying original request...');
              
              const chatResponse = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  ...(accessToken && { 'X-Access-Token': accessToken }),
                },
                body: JSON.stringify(pendingLinkingRequest),
              });

              const data = await chatResponse.json();
              
              // Process the response normally
              if (data.requires_linking) {
                // Still requires linking - shouldn't happen but handle it
                setRequiresLinking({
                  authorization_url: data.authorization_url,
                  state: data.state,
                  originalRequest: pendingLinkingRequest
                });
              } else {
                // Success - clear linking state
                setRequiresLinking(null);
                setPendingLinkingRequest(null);
                
                // Update Connected Accounts flow info
                if (data.connected_accounts_flow) {
                  setConnectedAccountsFlow(data.connected_accounts_flow);
                  setConnectedAccountsQuery(pendingLinkingRequest.messages[pendingLinkingRequest.messages.length - 1]?.content || null);
                }
                
                // Add assistant response
                const assistantMessage: Message = {
                  id: (Date.now() + 1).toString(),
                  role: 'assistant',
                  content: data.content || 'Account linked successfully! Your request has been processed.',
                  timestamp: new Date(),
                };
                
                setTimeout(() => {
                  setMessages(prev => [...prev, assistantMessage]);
                  setIsTyping(false);
                }, 1000);
              }
            } else {
              // No pending request - just show success message
              const successMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: 'Google account linked successfully!',
                timestamp: new Date(),
              };
              setMessages(prev => [...prev, successMessage]);
              setRequiresLinking(null);
              setPendingLinkingRequest(null);
            }
          } catch (error) {
            console.error('[POPUP] Error completing linking:', error);
            const errorMessage: Message = {
              id: (Date.now() + 1).toString(),
              role: 'assistant',
              content: `Failed to complete Google account linking: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again.`,
              timestamp: new Date(),
            };
            setMessages(prev => [...prev, errorMessage]);
            setRequiresLinking(null);
            setPendingLinkingRequest(null);
          } finally {
            setIsLoading(false);
          }
        } else {
          console.warn('[POPUP] ⚠️ No connect_code in message:', event.data);
          const errorMessage: Message = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: '⚠️ Received authorization callback but no connect_code was found.',
            timestamp: new Date(),
          };
          setMessages(prev => [...prev, errorMessage]);
          setRequiresLinking(null);
        }
      } else if (event.data && event.data.type === 'GOOGLE_LINKING_ERROR') {
        console.error('[POPUP] Linking error:', event.data.error);
        // Only show error if we actually have a pending request (to avoid showing errors from unrelated popups)
        if (pendingLinkingRequest) {
          const errorMessage: Message = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: `Failed to link Google account: ${event.data.error || 'Unknown error'}. Please try again.`,
            timestamp: new Date(),
          };
          setMessages(prev => [...prev, errorMessage]);
          setRequiresLinking(null);
          setPendingLinkingRequest(null);
        }
      } else {
        console.warn('[POPUP] Received unknown message type:', event.data);
      }
    };

    window.addEventListener('message', handleMessage);
    console.log('[POPUP] ✅ Message listener attached');
    
    // Log all messages for debugging
    const debugHandler = (event: MessageEvent) => {
      console.log('[POPUP] [DEBUG] All messages:', {
        origin: event.origin,
        expectedOrigin: window.location.origin,
        data: event.data,
        dataType: typeof event.data,
        hasType: event.data && typeof event.data === 'object' && 'type' in event.data
      });
    };
    window.addEventListener('message', debugHandler);
    
    return () => {
      console.log('[POPUP] Removing message listeners');
      window.removeEventListener('message', handleMessage);
      window.removeEventListener('message', debugHandler);
    };
  }, [session, pendingLinkingRequest]);

  // Handle Google callback (legacy - for direct redirects, now handled via popup)
  useEffect(() => {
    if (typeof window !== 'undefined' && session) {
      const urlParams = new URLSearchParams(window.location.search);
      const isCallback = urlParams.get('google_callback') === 'true';
      const connectCode = urlParams.get('code');
      const state = urlParams.get('state');
      
      if (isCallback && connectCode) {
        // Send connect_code to backend to complete linking
        // Backend will retrieve auth_session server-side using user's authenticated session
        const completeLinking = async () => {
          try {
            const accessToken = session?.accessToken;
            const response = await fetch('/api/resource/google-workspace/complete-linking', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                ...(accessToken && { 'X-Access-Token': accessToken }),
              },
              body: JSON.stringify({
                connect_code: connectCode,
                // Note: auth_session is retrieved server-side by user's authenticated session
              }),
            });
            
            const data = await response.json();
            
              if (data.success) {
                // Update Connected Accounts flow to show linking_completed state
                setConnectedAccountsFlow({
                  flow_state: 'linking_completed',
                  google_token: data.token ? data.token.substring(0, 50) + '...' : undefined,
                  token_type: data.token_type,
                  expires_in: data.expires_in,
                  scope: data.scope,
                });
                
                // Add success message
                const successMessage: Message = {
                  id: Date.now().toString(),
                  role: 'assistant',
                  content: 'Google account successfully linked! You can now access your calendar.',
                  timestamp: new Date(),
                };
                setMessages(prev => [...prev, successMessage]);
                
                // Clean up URL
                window.history.replaceState({}, '', window.location.pathname);
              } else {
              throw new Error(data.message || 'Failed to complete linking');
            }
          } catch (error) {
            console.error('[GOOGLE_CALLBACK] Error completing linking:', error);
            const errorMessage: Message = {
              id: Date.now().toString(),
              role: 'assistant',
              content: 'Failed to complete Google account linking. Please try again.',
              timestamp: new Date(),
            };
            setMessages(prev => [...prev, errorMessage]);
          }
        };
        
        completeLinking();
        
        // Clean up URL
        window.history.replaceState({}, '', window.location.pathname);
      }
    }
  }, [session]);
  
  // Note: auth_session is now stored server-side, keyed by user's authenticated session
  // No need to store it in frontend sessionStorage anymore

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

    // Get the prompt category if it was set from the library
    const promptCategory = typeof window !== 'undefined' ? sessionStorage.getItem('promptCategory') : null;
    
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
      prompt_category: promptCategory || undefined,
    };

    // Clear the stored category after using it
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('promptCategory');
    }

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    // Clear previous MCP info when starting a new message
    setMcpInfo(null);
    setMcpQuery(null);
    // Clear Connected Accounts flow unless it's a linking completion
    // (linking completion is handled in the callback useEffect)
    setIsTyping(true);

    try {
      // Extract access token from session for ID-JAG exchange
      const accessToken = session?.accessToken;
      
      // Log token availability
      console.log(`[MESSAGE] Sending access token: ${!!accessToken}`);
      
      // Prepare message with access token
      const messageWithTokens = {
        ...userMessage,
        access_token: accessToken,
      };
      
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // Send access token in header
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
      console.log(`[RESPONSE] requires_linking: ${data.requires_linking}, authorization_url: ${!!data.authorization_url}`);
      
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
      
      // Check if account linking is required (for Google Workspace)
      if (data.requires_linking) {
        console.log('[LINKING] Requires linking detected:', {
          authorization_url: data.authorization_url,
          state: data.state,
          content: data.content
        });
        
        // Store the original request for retry after linking
        const originalRequest = {
          messages: [...messages, messageWithTokens],
          session_id: sessionId,
        };
        setPendingLinkingRequest(originalRequest);
        setRequiresLinking({
          authorization_url: data.authorization_url,
          auth_session: data.auth_session,
          state: data.state,
          originalRequest: originalRequest
        });
        
        // Update assistant message to show linking prompt with button
        const linkingMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.content || 'Google account authorization is required to access your calendar. Please click the button below to authorize.',
          timestamp: new Date(),
          requiresLinking: {
            authorization_url: data.authorization_url,
            state: data.state
          }
        };
        
        console.log('[LINKING] Created linking message:', linkingMessage);
        
        setTimeout(() => {
          setMessages(prev => {
            const updated = [...prev, linkingMessage];
            console.log('[LINKING] Messages updated, total:', updated.length);
            console.log('[LINKING] Last message requiresLinking:', updated[updated.length - 1]?.requiresLinking);
            return updated;
          });
          setIsTyping(false);
        }, 1000);
        setIsLoading(false);
        return; // Exit early - don't process as normal message
      } else {
        setRequiresLinking(null);
        setPendingLinkingRequest(null);
      }
      
      // Update Connected Accounts flow info if present
      if (data.connected_accounts_flow) {
        console.log(`[CONNECTED_ACCOUNTS] Flow info received:`, data.connected_accounts_flow);
        setConnectedAccountsFlow(data.connected_accounts_flow);
        setConnectedAccountsQuery(userMessage.content);
      } else {
        // Clear if not present (unless it's a linking_required state which is handled above)
        if (!data.requires_linking) {
          setConnectedAccountsFlow(null);
          setConnectedAccountsQuery(null);
        }
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

  const handleLogout = () => {
    console.log('[LOGOUT] ===== LOGOUT HANDLER STARTED =====');
    
    // Get ID token (for logout) and client ID BEFORE signing out
    const idToken = session?.idToken;
    const oktaBaseUrl = process.env.NEXT_PUBLIC_OKTA_BASE_URL || process.env.NEXT_PUBLIC_OKTA_DOMAIN || 'https://your-domain.okta.com';
    const mainServerId = process.env.NEXT_PUBLIC_OKTA_MAIN_SERVER_ID || 'default';
    const clientId = process.env.NEXT_PUBLIC_OKTA_CLIENT_ID;
    
    console.log('[LOGOUT] idToken available:', !!idToken);
    console.log('[LOGOUT] clientId available:', !!clientId);
    
    // Clear client-side storage
    sessionStorage.clear();
    console.log('[LOGOUT] Cleared sessionStorage');
    
    // FIRST: Sign out from NextAuth to clear session and cookies
    // This is CRITICAL - it clears the JWT token and session
    signOut({ 
      callbackUrl: '/',
      redirect: false 
    }).then(() => {
      console.log('[LOGOUT] NextAuth signOut completed - cookies cleared');
      
      // SECOND: Redirect to Okta logout (custom authorization server)
      // Use ID token hint for logout (most reliable method)
      const customIssuer = `${oktaBaseUrl}/oauth2/${mainServerId}`;
      if (clientId && idToken) {
        // Use ID token hint for logout (preferred method)
        const oktaLogoutUrl = `${customIssuer}/v1/logout?id_token_hint=${idToken}&post_logout_redirect_uri=${encodeURIComponent(window.location.origin)}`;
        console.log('[LOGOUT] Redirecting to custom authz server logout with id_token_hint');
        window.location.href = oktaLogoutUrl;
      } else if (clientId) {
        // Fallback to client_id based logout
        const oktaLogoutUrl = `${customIssuer}/v1/logout?client_id=${clientId}&post_logout_redirect_uri=${encodeURIComponent(window.location.origin)}`;
        console.log('[LOGOUT] Redirecting to custom authz server logout with client_id');
        window.location.href = oktaLogoutUrl;
      } else {
        // Fallback to basic logout
        const oktaLogoutUrl = `${oktaBaseUrl}/login/signout`;
        console.log('[LOGOUT] Redirecting to Okta basic logout');
        window.location.href = oktaLogoutUrl;
      }
    }).catch((error) => {
      console.error('[LOGOUT] NextAuth signOut error:', error);
      window.location.href = '/';
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
              <PromptLibrary 
                onSelectPrompt={(prompt, category) => {
                  setInput(prompt);
                  // Store the prompt category for later use
                  if (category) {
                    sessionStorage.setItem('promptCategory', category);
                  }
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
                          
                          {/* Authorization Button in Assistant Message */}
                          {message.role === 'assistant' && message.requiresLinking && message.requiresLinking.authorization_url && (
                            <div className="mt-3 pt-3 border-t border-gray-200">
                              <button
                                onClick={() => {
                                  const authUrl = message.requiresLinking?.authorization_url;
                                  if (authUrl) {
                                    // Open popup window with authorization URL as-is (don't modify it)
                                    const width = 600;
                                    const height = 700;
                                    const left = (window.screen.width - width) / 2;
                                    const top = (window.screen.height - height) / 2;
                                    
                                    const popup = window.open(
                                      authUrl,
                                      'google-auth',
                                      `width=${width},height=${height},left=${left},top=${top},toolbar=no,location=yes,status=yes,menubar=no,scrollbars=yes,resizable=yes`
                                    );
                                    
                                    if (!popup) {
                                      alert('Please allow popups for this site to complete authorization.');
                                      return;
                                    }
                                    
                                    // Store popup reference to monitor it
                                    popupRef.current = popup;
                                    console.log('[POPUP] Opened authorization popup with URL:', authUrl);
                                    console.log('[POPUP] Popup reference stored');
                                    console.log('[POPUP] Check if redirect_uri is in URL:', authUrl.includes('redirect_uri'));
                                    
                                    // Monitor popup navigation (if possible)
                                    try {
                                      // Try to access popup location (may be blocked by CORS)
                                      const checkLocation = setInterval(() => {
                                        try {
                                          if (popup.closed) {
                                            console.log('[POPUP] Popup was closed');
                                            clearInterval(checkLocation);
                                            popupRef.current = null;
                                            return;
                                          }
                                          // Try to read popup location (will fail if cross-origin)
                                          try {
                                            const popupLocation = popup.location.href;
                                            console.log('[POPUP] Popup location:', popupLocation);
                                            if (popupLocation.includes('/api/resource/google-workspace/callback')) {
                                              console.log('[POPUP] ✅ Callback route detected in popup!');
                                            }
                                          } catch (e) {
                                            // Cross-origin - can't read location, that's expected
                                            // console.log('[POPUP] Cannot read popup location (cross-origin):', e.message);
                                          }
                                        } catch (e) {
                                          console.error('[POPUP] Error checking popup:', e);
                                        }
                                      }, 500);
                                      
                                      // Clean up interval after 5 minutes
                                      setTimeout(() => {
                                        clearInterval(checkLocation);
                                      }, 300000);
                                    } catch (e) {
                                      console.warn('[POPUP] Could not monitor popup location:', e);
                                    }
                                    
                                    // Monitor popup state (closed check)
                                    const checkPopup = setInterval(() => {
                                      try {
                                        if (popup.closed) {
                                          console.log('[POPUP] Popup was closed');
                                          clearInterval(checkPopup);
                                          popupRef.current = null;
                                        }
                                      } catch (e) {
                                        // Popup might be cross-origin, ignore errors
                                        clearInterval(checkPopup);
                                      }
                                    }, 1000);
                                    
                                    // Clean up interval after 5 minutes
                                    setTimeout(() => {
                                      clearInterval(checkPopup);
                                    }, 300000);
                                  }
                                }}
                                className="w-full flex items-center justify-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors text-sm"
                              >
                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                                </svg>
                                <span>Authorize Google</span>
                              </button>
                            </div>
                          )}
                          
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
              <IdTokenCard accessToken={session?.accessToken || ''} />
              <RAGCard ragInfo={ragInfo} />
              <MCPCard mcpInfo={mcpInfo} query={mcpQuery || undefined} />
              <ConnectedAccountsCard flowInfo={connectedAccountsFlow} query={connectedAccountsQuery || undefined} />
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
