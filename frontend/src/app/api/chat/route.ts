import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

export async function POST(request: Request) {
  try {
    const { messages, sessionId } = await request.json();
    console.log('Received chat messages:', messages);

    // Get the current session to access the tokens
    const session = await getServerSession(authOptions);
    // Org access token NOT stored in session (not needed, reduces cookie size)
    const customAccessToken = session?.customAccessToken; // Custom server token (for token exchange)
    
    console.log('📨 [Chat API] Session tokens:');
    console.log('  - Session user:', session?.user?.email);
    console.log('  - Custom Access Token (first 50 chars):', customAccessToken ? `${customAccessToken.substring(0, 50)}...` : 'NOT AVAILABLE');
    console.log('  - Has custom access token:', !!customAccessToken);
    console.log('  - Org Access Token NOT in session (not needed)');
    console.log('  - Full Custom Access Token:', customAccessToken);

    // Forward to FastAPI backend
    const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    
    // No Authorization header with org token (org access token not available)
    // Backend will use custom access token for token exchange instead
    console.log('📤 Forwarding request without org access token (not stored to reduce cookie size)');
    
    // Add custom server token header for token exchange (new)
    if (customAccessToken) {
      headers['X-Custom-Access-Token'] = customAccessToken;
      console.log('✅ Forwarding custom server token for token exchange');
    } else {
      console.log('⚠️ No custom access token available');
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
