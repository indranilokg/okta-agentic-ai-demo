'use client';

import { useState } from 'react';

interface MCPInfo {
  server: string;
  tools_called: string[];
  id_jag_token?: string;
  mcp_access_token?: string;
  expires_in?: number;
  scope?: string;
}

interface MCPCardProps {
  mcpInfo: MCPInfo | null;
  query?: string;
}

export default function MCPCard({ mcpInfo, query }: MCPCardProps) {
  // Auto-expand when tokens are available
  const hasTokens = mcpInfo?.id_jag_token || mcpInfo?.mcp_access_token;
  const [isExpanded, setIsExpanded] = useState(hasTokens ? true : false);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  // Log component state
  console.debug(`[MCP_CARD] Rendered: server=${mcpInfo?.server}, hasIdJagToken=${!!mcpInfo?.id_jag_token}, hasMcpToken=${!!mcpInfo?.mcp_access_token}`);

  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch (error) {
      console.error(`[MCP_CARD] Copy failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  if (!mcpInfo) return null;

  const getServerColor = (server: string) => {
    if (server === 'employees') return 'bg-blue-500';
    if (server === 'partners') return 'bg-purple-500';
    return 'bg-gray-500';
  };

  const getServerLabel = (server: string) => {
    if (server === 'employees') return 'Employees MCP';
    if (server === 'partners') return 'Partners MCP';
    return server;
  };

  const getServerIcon = (server: string) => {
    if (server === 'employees') {
      return (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
      );
    }
    if (server === 'partners') {
      return (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      );
    }
    return null;
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm w-full">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 text-left flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 ${getServerColor(mcpInfo.server)} rounded-full`}></div>
          <span className="font-medium text-gray-900">MCP Flow</span>
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
          {/* MCP Server Info */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-gray-700">MCP Server</h4>
            </div>
            <div className={`${getServerColor(mcpInfo.server)} bg-opacity-10 rounded-md p-3 border border-${getServerColor(mcpInfo.server)} border-opacity-20`}>
              <div className="flex items-center space-x-2">
                <div className={`${getServerColor(mcpInfo.server)} text-white rounded p-1`}>
                  {getServerIcon(mcpInfo.server)}
                </div>
                <span className="text-sm font-semibold text-gray-800">
                  {getServerLabel(mcpInfo.server)}
                </span>
              </div>
            </div>
          </div>

          {/* Query (if provided) */}
          {query && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-gray-700">Query</h4>
                <button
                  onClick={() => copyToClipboard(query, 'query')}
                  className="flex items-center space-x-1 px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition-colors"
                >
                  {copiedField === 'query' ? (
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
              <div className="bg-purple-50 rounded-md p-3 border border-purple-200">
                <p className="text-sm text-gray-800">{query}</p>
              </div>
            </div>
          )}

          {/* Tools Called */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Tools Executed</h4>
            <div className="space-y-2">
              {mcpInfo.tools_called && mcpInfo.tools_called.length > 0 ? (
                mcpInfo.tools_called.map((tool, index) => (
                  <div
                    key={index}
                    className="bg-gray-50 rounded-md p-3 border border-gray-200"
                  >
                    <div className="flex items-center space-x-2">
                      <svg className="w-4 h-4 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      <span className="text-sm font-medium text-gray-800">{tool}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="bg-gray-50 rounded-md p-3 border border-gray-200">
                  <p className="text-sm text-gray-500">No tools executed</p>
                </div>
              )}
            </div>
          </div>

          {/* Debug: Show if tokens should render */}
          {process.env.NODE_ENV === 'development' && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3">
              <p className="text-xs text-yellow-800">
                <strong>DEBUG:</strong> id_jag_token={!!mcpInfo.id_jag_token ? 'YES' : 'NO'}, mcp_access_token={!!mcpInfo.mcp_access_token ? 'YES' : 'NO'}
              </p>
            </div>
          )}

          {/* ID-JAG Token Display */}
          {mcpInfo.id_jag_token && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-gray-700">ID-JAG Token</h4>
                <button
                  onClick={() => copyToClipboard(mcpInfo.id_jag_token || '', 'id_jag_token')}
                  className="flex items-center space-x-1 px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition-colors"
                >
                  {copiedField === 'id_jag_token' ? (
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
              <div className="bg-blue-50 rounded-md p-3 border border-blue-200 font-mono text-xs break-all">
                <p className="text-gray-800">
                  {mcpInfo.id_jag_token.substring(0, 80)}...
                </p>
              </div>
            </div>
          )}

          {/* MCP Access Token Display */}
          {mcpInfo.mcp_access_token && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex-1">
                  <h4 className="text-sm font-medium text-gray-700">MCP Access Token</h4>
                  {mcpInfo.scope && (
                    <p className="text-xs text-gray-500 mt-1">Scope: <span className="font-semibold text-gray-700">{mcpInfo.scope}</span></p>
                  )}
                  {mcpInfo.expires_in && (
                    <p className="text-xs text-gray-500">Expires in: <span className="font-semibold text-gray-700">{mcpInfo.expires_in}s</span></p>
                  )}
                </div>
                <button
                  onClick={() => copyToClipboard(mcpInfo.mcp_access_token || '', 'mcp_access_token')}
                  className="flex items-center space-x-1 px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition-colors flex-shrink-0 ml-2"
                >
                  {copiedField === 'mcp_access_token' ? (
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
              <div className="bg-green-50 rounded-md p-3 border border-green-200 font-mono text-xs break-all">
                <p className="text-gray-800">
                  {mcpInfo.mcp_access_token.substring(0, 80)}...
                </p>
              </div>
            </div>
          )}

          {/* ID-JAG Flow Visualization */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">ID-JAG Secure Flow</h4>
            <div className="bg-gradient-to-r from-blue-50 via-purple-50 to-green-50 rounded-md p-4 border border-blue-200">
              <div className="space-y-3">
                {/* Chat Assistant Section */}
                <div className="mb-3 pb-3 border-b border-blue-200">
                  <p className="text-xs font-semibold text-blue-700 mb-2"> Chat Assistant (STEPS 1-3)</p>
                </div>

                {/* Step 1: Exchange ID Token */}
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                    1
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-medium text-gray-700">ID → ID-JAG</p>
                    <p className="text-xs text-gray-500">Exchange user ID token for ID-JAG token</p>
                  </div>
                </div>

                {/* Arrow */}
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-8"></div>
                  <div className="flex-1 border-l-2 border-blue-300 border-dashed h-4"></div>
                </div>

                {/* Step 2: Verify ID-JAG */}
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-purple-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                    2
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-medium text-gray-700">Verify ID-JAG</p>
                    <p className="text-xs text-gray-500">Validate ID-JAG token (audit trail)</p>
                  </div>
                </div>

                {/* Arrow */}
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-8"></div>
                  <div className="flex-1 border-l-2 border-purple-300 border-dashed h-4"></div>
                </div>

                {/* Step 3: Exchange for MCP Token */}
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-indigo-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                    3
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-medium text-gray-700">ID-JAG → MCP Token</p>
                    <p className="text-xs text-gray-500">Exchange ID-JAG for authorization server token</p>
                  </div>
                </div>

                {/* MCP Server Section */}
                <div className="mb-3 pb-3 border-b border-green-200 mt-3">
                  <p className="text-xs font-semibold text-green-700"> MCP Server (STEP 4)</p>
                </div>

                {/* Arrow */}
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-8"></div>
                  <div className="flex-1 border-l-2 border-green-300 border-dashed h-4"></div>
                </div>

                {/* Step 4: Validate Token & Execute */}
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                    4
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-medium text-gray-700">Validate & Execute</p>
                    <p className="text-xs text-gray-500">
                      {mcpInfo.tools_called && mcpInfo.tools_called.length > 0
                        ? `Verified access. Executing: ${mcpInfo.tools_called.join(', ')}`
                        : 'Verify MCP token before tool execution'}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Security Badge */}
          <div className="bg-green-50 rounded-md p-3 border border-green-200 flex items-start space-x-2">
            <svg className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <p className="text-xs font-semibold text-green-800">Secure Cross-App Access</p>
              <p className="text-xs text-green-700">ID tokens are never exposed to MCP server. Only short-lived access tokens are used.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

