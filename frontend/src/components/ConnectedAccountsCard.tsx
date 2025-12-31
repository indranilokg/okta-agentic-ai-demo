'use client';

import { useState } from 'react';

interface ConnectedAccountsFlowInfo {
  flow_state: 'token_found' | 'linking_required' | 'linking_completed';
  original_okta_token?: string;
  id_jag_token?: string;
  okta_access_token?: string;
  authorization_url?: string;
  auth_session?: string;
  google_token?: string;
  token_type?: string;
  expires_in?: number;
  scope?: string;
  tools_called?: string[];
  query?: string;
}

interface ConnectedAccountsCardProps {
  flowInfo: ConnectedAccountsFlowInfo | null;
  query?: string;
}

export default function ConnectedAccountsCard({ flowInfo, query }: ConnectedAccountsCardProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [tokensExpanded, setTokensExpanded] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch (error) {
      console.error(`[CONNECTED_ACCOUNTS_CARD] Copy failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  if (!flowInfo) return null;

  const getFlowStateColor = (state: string) => {
    if (state === 'token_found') return 'bg-green-500';
    if (state === 'linking_required') return 'bg-yellow-500';
    if (state === 'linking_completed') return 'bg-blue-500';
    return 'bg-gray-500';
  };

  const getFlowStateLabel = (state: string) => {
    if (state === 'token_found') return 'Token Found (Happy Path)';
    if (state === 'linking_required') return 'Authorization Required';
    if (state === 'linking_completed') return 'Linking Completed';
    return state;
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm w-full">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 text-left flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 ${getFlowStateColor(flowInfo.flow_state)} rounded-full`}></div>
          <span className="font-medium text-gray-900">Connected Accounts Flow</span>
          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
            {getFlowStateLabel(flowInfo.flow_state)}
          </span>
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

          {/* Flow Visualization */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Connected Accounts Flow</h4>
            <div className="bg-gradient-to-r from-blue-50 via-yellow-50 to-green-50 rounded-md p-4 border border-blue-200">
              <div className="space-y-3">
                {/* Step 1: Original Okta Token */}
                <div className="mb-3 pb-3 border-b border-blue-200">
                  <p className="text-xs font-semibold text-blue-700 mb-2">Chat Assistant</p>
                </div>

                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                    1
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-medium text-gray-700">Okta Token</p>
                    <p className="text-xs text-gray-500">User's authenticated Okta token from NextAuth</p>
                    {(flowInfo.original_okta_token || flowInfo.okta_access_token) && (
                      <div className="mt-1 bg-blue-50 rounded p-2 border border-blue-200">
                        <div className="flex items-center justify-between">
                          <p className="text-xs font-mono text-gray-800 break-all flex-1 mr-2">
                            {(flowInfo.original_okta_token || flowInfo.okta_access_token)?.substring(0, 60)}...
                          </p>
                          <button
                            onClick={() => copyToClipboard(flowInfo.original_okta_token || flowInfo.okta_access_token || '', 'okta_token')}
                            className="flex-shrink-0 px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                          >
                            {copiedField === 'okta_token' ? 'Copied!' : 'Copy'}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Arrow */}
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-8"></div>
                  <div className="flex-1 border-l-2 border-blue-300 border-dashed h-4"></div>
                </div>

                {/* Step 2: ID-JAG Exchange */}
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-purple-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                    2
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-medium text-gray-700">ID-JAG Exchange</p>
                    <p className="text-xs text-gray-500">Exchange Okta token for ID-JAG token</p>
                    {flowInfo.id_jag_token && (
                      <div className="mt-1 bg-purple-50 rounded p-2 border border-purple-200">
                        <div className="flex items-center justify-between">
                          <p className="text-xs font-mono text-gray-800 break-all flex-1 mr-2">
                            {flowInfo.id_jag_token.substring(0, 60)}...
                          </p>
                          <button
                            onClick={() => copyToClipboard(flowInfo.id_jag_token || '', 'id_jag_token')}
                            className="flex-shrink-0 px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded hover:bg-purple-200"
                          >
                            {copiedField === 'id_jag_token' ? 'Copied!' : 'Copy'}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Arrow */}
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-8"></div>
                  <div className="flex-1 border-l-2 border-blue-300 border-dashed h-4"></div>
                </div>

                {/* Step 3: Okta Access Token (after ID-JAG) */}
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-indigo-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                    3
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-medium text-gray-700">Okta Access Token</p>
                    <p className="text-xs text-gray-500">Access token after ID-JAG (used for Auth0)</p>
                    {flowInfo.okta_access_token && (
                      <div className="mt-1 bg-indigo-50 rounded p-2 border border-indigo-200">
                        <div className="flex items-center justify-between">
                          <p className="text-xs font-mono text-gray-800 break-all flex-1 mr-2">
                            {flowInfo.okta_access_token.substring(0, 60)}...
                          </p>
                          <button
                            onClick={() => copyToClipboard(flowInfo.okta_access_token || '', 'okta_access_token')}
                            className="flex-shrink-0 px-2 py-1 text-xs bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200"
                          >
                            {copiedField === 'okta_access_token' ? 'Copied!' : 'Copy'}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Arrow */}
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-8"></div>
                  <div className="flex-1 border-l-2 border-indigo-300 border-dashed h-4"></div>
                </div>

                {/* Step 4: Check Auth0 Vault */}
                <div className="mb-3 pb-3 border-b border-indigo-200">
                  <p className="text-xs font-semibold text-indigo-700 mb-2">Auth0 Connected Accounts</p>
                </div>

                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-indigo-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                    4
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-medium text-gray-700">Check Auth0 Vault</p>
                    <p className="text-xs text-gray-500">Query Auth0 vault for existing Google token</p>
                  </div>
                </div>

                {/* Conditional Flow Based on State */}
                {flowInfo.flow_state === 'token_found' && (
                  <>
                    {/* Arrow */}
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0 w-8"></div>
                      <div className="flex-1 border-l-2 border-green-300 border-dashed h-4"></div>
                    </div>

                    {/* Step 5: Token Found */}
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0 w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                        ✓
                      </div>
                      <div className="flex-1">
                        <p className="text-xs font-medium text-gray-700">Token Found in Vault</p>
                        <p className="text-xs text-gray-500">Google token retrieved from Auth0 vault</p>
                      </div>
                    </div>

                    {/* Arrow */}
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0 w-8"></div>
                      <div className="flex-1 border-l-2 border-green-300 border-dashed h-4"></div>
                    </div>

                    {/* Step 6: Use Token */}
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0 w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                        5
                      </div>
                      <div className="flex-1">
                        <p className="text-xs font-medium text-gray-700">Call Google API</p>
                        <p className="text-xs text-gray-500">
                          {flowInfo.tools_called && flowInfo.tools_called.length > 0
                            ? `Executing: ${flowInfo.tools_called.join(', ')}`
                            : 'Use Google token to call Google Calendar API'}
                        </p>
                      </div>
                    </div>
                  </>
                )}

                {flowInfo.flow_state === 'linking_required' && (
                  <>
                    {/* Arrow */}
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0 w-8"></div>
                      <div className="flex-1 border-l-2 border-yellow-300 border-dashed h-4"></div>
                    </div>

                    {/* Step 5: Token Not Found */}
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0 w-8 h-8 bg-yellow-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                        !
                      </div>
                      <div className="flex-1">
                        <p className="text-xs font-medium text-gray-700">Token Not Found</p>
                        <p className="text-xs text-gray-500">No Google token in vault - account linking required</p>
                      </div>
                    </div>

                    {/* Arrow */}
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0 w-8"></div>
                      <div className="flex-1 border-l-2 border-yellow-300 border-dashed h-4"></div>
                    </div>

                    {/* Step 6: Generate Auth URL */}
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0 w-8 h-8 bg-yellow-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                        6
                      </div>
                      <div className="flex-1">
                        <p className="text-xs font-medium text-gray-700">Generate Authorization URL</p>
                        <p className="text-xs text-gray-500">Create OAuth authorization URL for Google account linking</p>
                        {flowInfo.authorization_url && (
                          <div className="mt-1 bg-yellow-50 rounded p-2 border border-yellow-200">
                            <div className="flex items-center justify-between">
                              <p className="text-xs font-mono text-gray-800 break-all flex-1 mr-2">
                                {flowInfo.authorization_url.substring(0, 80)}...
                              </p>
                              <button
                                onClick={() => copyToClipboard(flowInfo.authorization_url || '', 'auth_url')}
                                className="flex-shrink-0 px-2 py-1 text-xs bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200"
                              >
                                {copiedField === 'auth_url' ? 'Copied!' : 'Copy'}
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Arrow (dashed, indicating waiting) */}
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0 w-8"></div>
                      <div className="flex-1 border-l-2 border-yellow-300 border-dashed h-4"></div>
                    </div>

                    {/* Step 7: Waiting for User */}
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0 w-8 h-8 bg-yellow-500 rounded-full flex items-center justify-center text-white text-xs font-bold animate-pulse">
                        ⏳
                      </div>
                      <div className="flex-1">
                        <p className="text-xs font-medium text-gray-700">Waiting for Authorization</p>
                        <p className="text-xs text-gray-500">User needs to authorize Google account connection</p>
                      </div>
                    </div>
                  </>
                )}

                {flowInfo.flow_state === 'linking_completed' && (
                  <>
                    {/* Arrow */}
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0 w-8"></div>
                      <div className="flex-1 border-l-2 border-yellow-300 border-dashed h-4"></div>
                    </div>

                    {/* Step 5: Complete Linking */}
                    <div className="mb-3 pb-3 border-b border-yellow-200">
                      <p className="text-xs font-semibold text-yellow-700 mb-2">Account Linking</p>
                    </div>

                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0 w-8 h-8 bg-yellow-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                        5
                      </div>
                      <div className="flex-1">
                        <p className="text-xs font-medium text-gray-700">Complete Account Linking</p>
                        <p className="text-xs text-gray-500">Exchange connect_code for Google token</p>
                        {flowInfo.auth_session && (
                          <div className="mt-1 bg-yellow-50 rounded p-2 border border-yellow-200">
                            <p className="text-xs text-gray-600">Auth Session: {flowInfo.auth_session.substring(0, 40)}...</p>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Arrow */}
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0 w-8"></div>
                      <div className="flex-1 border-l-2 border-green-300 border-dashed h-4"></div>
                    </div>

                    {/* Step 6: Token Retrieved */}
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0 w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                        ✓
                      </div>
                      <div className="flex-1">
                        <p className="text-xs font-medium text-gray-700">Token Retrieved</p>
                        <p className="text-xs text-gray-500">Google token obtained and stored in vault</p>
                      </div>
                    </div>

                    {/* Arrow */}
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0 w-8"></div>
                      <div className="flex-1 border-l-2 border-green-300 border-dashed h-4"></div>
                    </div>

                    {/* Step 7: Use Token */}
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0 w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                        6
                      </div>
                      <div className="flex-1">
                        <p className="text-xs font-medium text-gray-700">Call Google API</p>
                        <p className="text-xs text-gray-500">
                          {flowInfo.tools_called && flowInfo.tools_called.length > 0
                            ? `Executing: ${flowInfo.tools_called.join(', ')}`
                            : 'Use Google token to call Google Calendar API'}
                        </p>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Tokens Display Section */}
          <div>
            <button
              onClick={() => setTokensExpanded(!tokensExpanded)}
              className="w-full flex items-center justify-between mb-3 hover:text-gray-900 transition-colors"
            >
              <h4 className="text-sm font-medium text-gray-700">Tokens</h4>
              <svg
                className={`w-4 h-4 text-gray-500 transition-transform ${tokensExpanded ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {tokensExpanded && (
              <div className="space-y-3">
              {/* ID-JAG Token */}
              {flowInfo.id_jag_token && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h5 className="text-xs font-medium text-gray-700">ID-JAG Token</h5>
                    <button
                      onClick={() => copyToClipboard(flowInfo.id_jag_token || '', 'id_jag_token_display')}
                      className="flex items-center space-x-1 px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded hover:bg-purple-200 transition-colors"
                    >
                      {copiedField === 'id_jag_token_display' ? (
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
                  <div className="bg-purple-50 rounded-md p-3 border border-purple-200 font-mono text-xs break-all">
                    <p className="text-gray-800">{flowInfo.id_jag_token}</p>
                  </div>
                </div>
              )}

              {/* Okta Access Token */}
              {flowInfo.okta_access_token && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h5 className="text-xs font-medium text-gray-700">Okta Access Token</h5>
                    <button
                      onClick={() => copyToClipboard(flowInfo.okta_access_token || '', 'okta_access_token_display')}
                      className="flex items-center space-x-1 px-2 py-1 text-xs bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200 transition-colors"
                    >
                      {copiedField === 'okta_access_token_display' ? (
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
                  <div className="bg-indigo-50 rounded-md p-3 border border-indigo-200 font-mono text-xs break-all">
                    <p className="text-gray-800">{flowInfo.okta_access_token}</p>
                  </div>
                </div>
              )}

              {/* Google Token */}
              {flowInfo.google_token && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex-1">
                      <h5 className="text-xs font-medium text-gray-700">Google Token</h5>
                      {flowInfo.scope && (
                        <p className="text-xs text-gray-500 mt-1">Scope: <span className="font-semibold text-gray-700">{flowInfo.scope}</span></p>
                      )}
                      {flowInfo.expires_in && (
                        <p className="text-xs text-gray-500">Expires in: <span className="font-semibold text-gray-700">{flowInfo.expires_in}s</span></p>
                      )}
                    </div>
                    <button
                      onClick={() => copyToClipboard(flowInfo.google_token || '', 'google_token')}
                      className="flex items-center space-x-1 px-2 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 transition-colors flex-shrink-0 ml-2"
                    >
                      {copiedField === 'google_token' ? (
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
                    <p className="text-gray-800">{flowInfo.google_token}</p>
                  </div>
                </div>
              )}
              </div>
            )}
          </div>

          {/* Tools Called */}
          {flowInfo.tools_called && flowInfo.tools_called.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Tools Executed</h4>
              <div className="space-y-2">
                {flowInfo.tools_called.map((tool, index) => (
                  <div
                    key={index}
                    className="bg-gray-50 rounded-md p-3 border border-gray-200"
                  >
                    <div className="flex items-center space-x-2">
                      <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      <span className="text-sm font-medium text-gray-800">{tool}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Security Badge */}
          <div className="bg-green-50 rounded-md p-3 border border-green-200 flex items-start space-x-2">
            <svg className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <p className="text-xs font-semibold text-green-800">Secure Token Vault</p>
              <p className="text-xs text-green-700">Google tokens are securely stored in Auth0 vault and retrieved on-demand. No tokens are exposed to the frontend.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

