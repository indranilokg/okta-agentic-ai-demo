'use client';

import { useState } from 'react';

interface PromptLibraryProps {
  onSelectPrompt: (prompt: string) => void;
}

interface PromptCategory {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  prompts: string[];
}

const promptCategories: PromptCategory[] = [
  {
    id: 'rag',
    name: 'RAG (Retrieval Augmented Generation)',
    description: 'Query documents and knowledge base',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    prompts: [
      'What are the security policies for data access?',
      'Search for documents about GDPR compliance',
      'Find information about employee benefits policies',
      'Tell me about our company compliance requirements',
      'What documents do we have related to financial regulations?',
      'Show me the security documentation for data handling'
    ]
  },
  {
    id: 'token-exchange',
    name: 'Token Exchange (A2A)',
    description: 'Multi-agent workflows with token exchange',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
      </svg>
    ),
    prompts: [
      'I need to onboard a new employee',
      'Help me process a financial transaction',
      'I need to approve a high-value payment',
      'Can you help me with employee onboarding?',
      'Process a financial transaction for approval',
      'I need to hire a new staff member'
    ]
  },
  {
    id: 'xaa',
    name: 'Cross-App Access (XAA)',
    description: 'Coming soon - Cross-application access scenarios',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
      </svg>
    ),
    prompts: [
      'Coming soon...',
      'Cross-app access scenarios will be available here'
    ]
  }
];

export default function PromptLibrary({ onSelectPrompt }: PromptLibraryProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);

  const toggleCategory = (categoryId: string) => {
    setExpandedCategory(expandedCategory === categoryId ? null : categoryId);
  };

  const handlePromptClick = (prompt: string) => {
    onSelectPrompt(prompt);
    setIsOpen(false);
  };

  return (
    <>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-1.5 text-sm bg-indigo-50 text-indigo-700 rounded-md hover:bg-indigo-100 transition-colors"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
        </svg>
        <span>Prompt Library</span>
      </button>

      {/* Modal Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
          onClick={() => setIsOpen(false)}
        >
          <div 
            className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Prompt Library</h2>
                <p className="text-sm text-gray-500 mt-1">Select a sample prompt to get started</p>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
              {promptCategories.map((category) => (
                <div 
                  key={category.id} 
                  className="border border-gray-200 rounded-lg overflow-hidden"
                >
                  {/* Category Header */}
                  <button
                    onClick={() => toggleCategory(category.id)}
                    className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center space-x-3">
                      <div className={`${category.id === 'xaa' ? 'text-gray-400' : 'text-indigo-600'}`}>
                        {category.icon}
                      </div>
                      <div className="text-left">
                        <h3 className={`text-sm font-semibold ${category.id === 'xaa' ? 'text-gray-400' : 'text-gray-900'}`}>
                          {category.name}
                        </h3>
                        <p className="text-xs text-gray-500">{category.description}</p>
                      </div>
                    </div>
                    <svg
                      className={`w-5 h-5 text-gray-400 transition-transform ${expandedCategory === category.id ? 'rotate-180' : ''}`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>

                  {/* Prompts List */}
                  {expandedCategory === category.id && (
                    <div className="px-4 pb-3 space-y-2 bg-gray-50">
                      {category.prompts.map((prompt, index) => (
                        <button
                          key={index}
                          onClick={() => handlePromptClick(prompt)}
                          disabled={category.id === 'xaa'}
                          className={`w-full text-left px-3 py-2 text-sm rounded-md transition-colors ${
                            category.id === 'xaa'
                              ? 'text-gray-400 cursor-not-allowed'
                              : 'text-gray-700 hover:bg-white hover:shadow-sm border border-transparent hover:border-gray-200'
                          }`}
                        >
                          {prompt}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Footer */}
            <div className="px-6 py-3 border-t border-gray-200 bg-gray-50">
              <p className="text-xs text-gray-500 text-center">
                Click on any prompt to use it in the chat
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

