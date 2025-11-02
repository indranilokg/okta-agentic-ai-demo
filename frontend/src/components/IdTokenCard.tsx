'use client';

import { useState } from 'react';

interface IdTokenCardProps {
  idToken: string;
}

export default function IdTokenCard({ idToken }: IdTokenCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [decodedToken, setDecodedToken] = useState<any>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const decodeToken = (token: string) => {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
      }).join(''));
      return JSON.parse(jsonPayload);
    } catch (error) {
      console.error('Error decoding token:', error);
      return null;
    }
  };

  const handleToggle = () => {
    if (!decodedToken && idToken) {
      setDecodedToken(decodeToken(idToken));
    }
    setIsExpanded(!isExpanded);
  };

  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
    }
  };

  if (!idToken) return null;

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm w-full">
      <button
        onClick={handleToggle}
        className="w-full px-4 py-3 text-left flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
          <span className="font-medium text-gray-900">ID Token Details</span>
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
          {/* Decoded Token - Shown First */}
          {decodedToken && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-gray-700">Decoded Token</h4>
                <button
                  onClick={() => copyToClipboard(JSON.stringify(decodedToken, null, 2), 'decoded')}
                  className="flex items-center space-x-1 px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition-colors"
                >
                  {copiedField === 'decoded' ? (
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
              <div className="bg-gray-50 rounded-md p-3 max-h-64 overflow-y-auto">
                <pre className="text-xs text-gray-800 whitespace-pre-wrap">
                  {JSON.stringify(decodedToken, null, 2)}
                </pre>
              </div>
            </div>
          )}
          
          {/* Raw Token */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-gray-700">Raw Token</h4>
              <button
                onClick={() => copyToClipboard(idToken, 'raw')}
                className="flex items-center space-x-1 px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition-colors"
              >
                {copiedField === 'raw' ? (
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
            <div className="bg-gray-50 rounded-md p-3 max-h-32 overflow-y-auto">
              <code className="text-xs text-gray-800 break-all">{idToken}</code>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

