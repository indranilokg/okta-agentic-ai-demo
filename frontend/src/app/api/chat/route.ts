import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

export async function POST(request: Request) {
  try {
    const { messages, sessionId } = await request.json();

    // Get the current session to access the tokens
    const session = await getServerSession(authOptions);
    const idToken = session?.idToken;
    const customAccessToken = session?.customAccessToken;
    
    console.debug(`[CHAT_API] Request: user=${session?.user?.email}, has_idToken=${!!idToken}, has_customAccessToken=${!!customAccessToken}`);

    // Forward to FastAPI backend
    const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    
    // Add ID token header for ID-JAG token exchange (MCP flows)
    if (idToken) {
      headers['X-ID-Token'] = idToken;
    }
    
    // Add custom server token header for token exchange
    if (customAccessToken) {
      headers['X-Custom-Access-Token'] = customAccessToken;
    }
    
    const response = await fetch(`${backendUrl}/api/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ 
        messages, 
        session_id: sessionId || 'default-session' 
      }),
    });

    if (!response.ok) {
      console.error(`[CHAT_API] Backend error: status=${response.status}`);
      throw new Error(`Backend responded with status: ${response.status}`);
    }

    const data = await response.json();
    console.debug(`[CHAT_API] Response: agent_type=${data.agentType}, has_agent_flow=${Array.isArray(data.agent_flow)}, has_mcp_info=${!!data.mcp_info}, used_rag=${data.used_rag}`);

    return NextResponse.json(data);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(`[CHAT_API] Error: ${errorMessage}`);
    
    // Fallback response if backend is not available
    const fallbackResponse = {
      content: "I'm sorry, I'm having trouble connecting to the AI service right now. Please try again later.",
      agentType: 'Chat Assistant'
    };

    return NextResponse.json(fallbackResponse);
  }
}
