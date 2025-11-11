import { NextResponse } from 'next/server';

/**
 * API endpoint to provide Okta configuration to the frontend
 * This allows the client to access server-side environment variables
 * without exposing sensitive information
 */
export async function GET() {
  try {
    // Try to fetch from backend first (has server-side env variables)
    const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    try {
      const backendResponse = await fetch(`${backendUrl}/api/config/okta`, {
        cache: 'no-store',
      });
      if (backendResponse.ok) {
        const backendConfig = await backendResponse.json();
        console.log('[Config API] Fetched from backend:', backendConfig);
        return NextResponse.json(backendConfig);
      }
    } catch (backendError) {
      console.warn('[Config API] Failed to fetch from backend, using frontend env vars:', backendError);
    }
    
    // Fallback to frontend environment variables
    const mainServerId = process.env.NEXT_PUBLIC_OKTA_MAIN_SERVER_ID || 'default';
    const audience = process.env.NEXT_PUBLIC_OKTA_AUDIENCE || process.env.NEXT_PUBLIC_OKTA_MAIN_AUDIENCE || 'api://streamward-chat';
    const oktaDomain = process.env.NEXT_PUBLIC_OKTA_BASE_URL || process.env.NEXT_PUBLIC_OKTA_DOMAIN;
    
    console.log('[Config API] Using frontend env vars:');
    console.log('  - NEXT_PUBLIC_OKTA_MAIN_SERVER_ID:', mainServerId);
    console.log('  - oktaDomain:', oktaDomain);
    
    // Return only non-sensitive configuration
    return NextResponse.json({
      mainServerId,
      audience,
      oktaDomain,
    });
  } catch (error) {
    console.error('[Config API] Error providing Okta config:', error);
    return NextResponse.json(
      { error: 'Failed to retrieve configuration' },
      { status: 500 }
    );
  }
}

