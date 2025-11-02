import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

export async function POST(request: Request) {
  try {
    const { messages, sessionId } = await request.json();
    console.log('Received chat messages:', messages);

    // Get the current session to access the access token
    const session = await getServerSession(authOptions);
    const accessToken = session?.accessToken;
    
    console.log('Session user:', session?.user?.email);
    console.log('Has access token:', !!accessToken);

    // Forward to FastAPI backend
    const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    
    // Add Authorization header if we have an access token
    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
      console.log('✅ Forwarding request with Okta token');
    } else {
      console.log('⚠️ No access token - using demo mode');
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
      throw new Error(`Backend responded with status: ${response.status}`);
    }

    const data = await response.json();
    console.log('Backend response:', data);

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error forwarding to backend:', error);
    
    // Fallback response if backend is not available
    const fallbackResponse = {
      content: "I'm sorry, I'm having trouble connecting to the AI service right now. Please try again later.",
      agentType: 'Chat Assistant'
    };

    return NextResponse.json(fallbackResponse);
  }
}
