import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

export async function POST(request: NextRequest) {
  try {
    const { connect_code } = await request.json();
    
    if (!connect_code) {
      return NextResponse.json(
        { error: 'connect_code is required' },
        { status: 400 }
      );
    }
    
    // Note: auth_session is retrieved server-side using user's authenticated session
    // This ensures multi-user support - each user's linking state is isolated
    
    // Get the current session to access the access token
    const session = await getServerSession(authOptions);
    const accessToken = session?.accessToken;
    
    if (!accessToken) {
      return NextResponse.json(
        { error: 'Not authenticated' },
        { status: 401 }
      );
    }
    
    // Forward to FastAPI backend
    const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    
    const response = await fetch(`${backendUrl}/api/resource/google-workspace/complete-linking`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Access-Token': accessToken,
      },
      body: JSON.stringify({
        connect_code,
        // auth_session retrieved server-side by user's authenticated session
      }),
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: 'Backend error' }));
      return NextResponse.json(
        { error: errorData.message || 'Failed to complete linking' },
        { status: response.status }
      );
    }
    
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[COMPLETE_LINKING] Error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

