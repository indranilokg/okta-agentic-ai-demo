import { NextResponse } from 'next/server';

/**
 * API endpoint to provide Okta configuration to the frontend
 * This allows the client to access server-side environment variables
 * without exposing sensitive information
 */
export async function GET() {
  try {
    const mainServerId = process.env.OKTA_MAIN_SERVER_ID || 'default';
    const audience = process.env.OKTA_AUDIENCE || process.env.OKTA_MAIN_AUDIENCE || 'api://streamward-chat';
    const oktaDomain = process.env.OKTA_DOMAIN || process.env.NEXT_PUBLIC_OKTA_BASE_URL || process.env.NEXT_PUBLIC_OKTA_DOMAIN;
    
    // Log configuration for debugging
    console.log(' [Config API] Providing Okta configuration:');
    console.log('  - OKTA_MAIN_SERVER_ID env var:', process.env.OKTA_MAIN_SERVER_ID || 'NOT SET (using default)');
    console.log('  - mainServerId:', mainServerId);
    console.log('  - audience:', audience);
    console.log('  - oktaDomain:', oktaDomain);
    
    // Return only non-sensitive configuration
    return NextResponse.json({
      mainServerId,
      audience,
      oktaDomain,
    });
  } catch (error) {
    console.error('Error providing Okta config:', error);
    return NextResponse.json(
      { error: 'Failed to retrieve configuration' },
      { status: 500 }
    );
  }
}

