'use client';

import { useState } from 'react';

interface TokenExchange {
  from: string;
  to: string;
  audience: string;
  scope: string;
  token: string;
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

interface AgentFlowCardProps {
  agentFlow: AgentFlowStep[] | null;
  tokenExchanges: TokenExchange[] | null;
  workflowType?: string;
  sourceUserToken?: string | null;
}

export default function AgentFlowCard({ agentFlow, tokenExchanges, workflowType, sourceUserToken }: AgentFlowCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [expandedToken, setExpandedToken] = useState<string | null>(null);
  const [showSourceToken, setShowSourceToken] = useState(true); // Default to showing the token

  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
    }
  };

  // Only show card when data is available
  const hasData = agentFlow && agentFlow.length > 0;
  
  if (!hasData) {
    return null;
  }

  const getAgentColor = (agent: string) => {
    if (agent.includes('hr')) return 'bg-blue-500';
    if (agent.includes('finance')) return 'bg-green-500';
    if (agent.includes('legal')) return 'bg-purple-500';
    return 'bg-gray-500';
  };

  const getAgentLabel = (agent: string) => {
    if (agent.includes('hr')) return 'HR Agent';
    if (agent.includes('finance')) return 'Finance Agent';
    if (agent.includes('legal')) return 'Legal Agent';
    return agent;
  };

  const getAgentIcon = (agent: string) => {
    if (agent.includes('hr')) {
      return (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
      );
    }
    if (agent.includes('finance')) {
      return (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
    }
    if (agent.includes('legal')) {
      return (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      );
    }
    return null;
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl border border-gray-100 w-full">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 text-left flex items-center justify-between hover:bg-gray-50 transition-colors rounded-t-2xl"
      >
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-indigo-500 rounded-full"></div>
          <span className="font-medium text-gray-900">A2A Agent Flow</span>
          {agentFlow && agentFlow.length > 0 && (
            <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full">
              {agentFlow.length} agent{agentFlow.length !== 1 ? 's' : ''}
            </span>
          )}
          {workflowType && (
            <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full">
              {workflowType}
            </span>
          )}
        </div>
        <svg
          className={`w-5 h-5 text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      
      {isExpanded && (
        <div className="px-4 pb-4 space-y-4">
          {/* Source User Token - Show once at the top with toggle */}
          {sourceUserToken && (
            <div className="bg-blue-50 rounded-lg border border-blue-200 mb-4">
              <button
                onClick={() => setShowSourceToken(!showSourceToken)}
                className="w-full px-3 py-2 flex items-center justify-between hover:bg-blue-100 transition-colors rounded-t-lg"
              >
                <div className="flex items-center space-x-2">
                  <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                  </svg>
                  <span className="text-sm font-semibold text-blue-900">Source User Token</span>
                </div>
                <svg
                  className={`w-4 h-4 text-blue-600 transition-transform ${showSourceToken ? 'rotate-180' : ''}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              
              {showSourceToken && (
                <div className="px-3 pb-3">
                  <div className="flex items-center justify-end mb-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        copyToClipboard(sourceUserToken, 'source-token');
                      }}
                      className="flex items-center space-x-1 px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
                    >
                      {copiedField === 'source-token' ? (
                        <svg className="w-3 h-3 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                      ) : (
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                      )}
                      <span>{copiedField === 'source-token' ? 'Copied!' : 'Copy'}</span>
                    </button>
                  </div>
                  <p className="text-xs text-blue-700 break-all font-mono bg-white p-2 rounded border border-blue-100">
                    {sourceUserToken}
                  </p>
                </div>
              )}
            </div>
          )}
          
          {/* Agent Flow Visualization */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-3">Agent Routing Flow</h4>
            <div className="space-y-3">
              {/* Orchestrator */}
              <div className="flex items-center">
                <div className="bg-indigo-100 rounded-lg px-3 py-2 flex items-center space-x-2">
                  <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  <span className="text-sm font-semibold text-indigo-900">Orchestrator</span>
                </div>
              </div>

              {/* Agents */}
              {agentFlow.map((step, index) => (
                <div key={index} className="space-y-2">
                  {/* Arrow */}
                  <div className="flex items-center pl-4">
                    <div className="w-0.5 h-6 bg-gray-300"></div>
                    <div className="w-0 h-0 border-l-4 border-l-transparent border-r-4 border-r-transparent border-t-4 border-t-gray-300 ml-[-8px]"></div>
                  </div>
                  
                  {/* Agent Card */}
                  <div className="flex items-center pl-4">
                    <div className={`${getAgentColor(step.agent)} rounded-lg px-3 py-2 flex items-center space-x-2 text-white`}>
                      {getAgentIcon(step.agent)}
                      <span className="text-sm font-semibold">{getAgentLabel(step.agent)}</span>
                      <span className="text-xs bg-white/20 px-1.5 py-0.5 rounded">Step {step.step}</span>
                    </div>
                  </div>
                  
                  {/* Token Exchange Info */}
                  <div className="ml-8 bg-gray-50 rounded-md p-2 border border-gray-200">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                        </svg>
                        <span className="text-xs text-gray-600">
                          Token: {step.token_exchange.from} → {step.token_exchange.to}
                        </span>
                      </div>
                    </div>
                    <div className="mt-1 text-xs text-gray-500">
                      Audience: {step.token_exchange.audience}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Token Exchanges Detail */}
          {tokenExchanges && tokenExchanges.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-gray-700">Token Exchange Details</h4>
              </div>
              <div className="space-y-2">
                {tokenExchanges.map((exchange, index) => (
                  <div key={index} className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg p-3 border border-indigo-200">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-indigo-500 rounded-full"></div>
                        <span className="text-sm font-semibold text-gray-900">
                          {exchange.from} → {exchange.to}
                        </span>
                      </div>
                      <button
                        onClick={() => setExpandedToken(expandedToken === `token-${index}` ? null : `token-${index}`)}
                        className="text-xs text-indigo-600 hover:text-indigo-700"
                      >
                        {expandedToken === `token-${index}` ? 'Hide' : 'Show'} Token
                      </button>
                    </div>
                    
                    <div className="space-y-1 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600">Audience:</span>
                        <span className="font-mono text-gray-800">{exchange.audience}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600">Scope:</span>
                        <span className="font-mono text-gray-800">{exchange.scope}</span>
                      </div>
                      
                      {expandedToken === `token-${index}` && (
                        <div className="mt-2 pt-2 border-t border-indigo-200">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-gray-600">Access Token:</span>
                            <button
                              onClick={() => copyToClipboard(exchange.token, `token-${index}`)}
                              className="flex items-center space-x-1 px-2 py-0.5 text-xs bg-indigo-100 text-indigo-600 rounded hover:bg-indigo-200 transition-colors"
                            >
                              {copiedField === `token-${index}` ? (
                                <>
                                  <svg className="w-3 h-3 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                  </svg>
                                  <span className="text-green-600">Copied!</span>
                                </>
                              ) : (
                                <>
                                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                  </svg>
                                  <span>Copy</span>
                                </>
                              )}
                            </button>
                          </div>
                          <div className="bg-white rounded p-2 border border-indigo-200">
                            <p className="text-xs font-mono text-gray-800 break-all">{exchange.token}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Summary */}
          <div className="bg-indigo-50 rounded-lg p-3 border border-indigo-200">
            <div className="flex items-center space-x-2 mb-2">
              <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm font-semibold text-indigo-900">Flow Summary</span>
            </div>
            <div className="text-xs text-indigo-700 space-y-1">
              <div>• {agentFlow.length} agent{agentFlow.length !== 1 ? 's' : ''} involved</div>
              <div>• {tokenExchanges?.length || 0} token exchange{tokenExchanges?.length !== 1 ? 's' : ''} performed</div>
              <div>• Sequential A2A coordination completed</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

