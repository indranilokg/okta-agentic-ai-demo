/**
 * Custom Authorization Server OAuth Callback Handler
 * 
 * This handles the OAuth callback from the custom authorization server.
 * It processes the authorization code, exchanges it for tokens, and stores
 * them in encrypted cookies that NextAuth JWT callback can read.
 */

import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { cookies } from 'next/headers';

export async function GET(request: Request) {
  try {
    console.log('=== CUSTOM AUTH CALLBACK START ===');
    const { searchParams } = new URL(request.url);
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const error = searchParams.get('error');
    
    console.log('[STEP 1] URL params:', { code: code ? '✓' : '✗', state: state ? '✓' : '✗', error });
    
    const baseUrl = process.env.NEXTAUTH_URL || process.env.NEXT_PUBLIC_API_BASE_URL?.replace('/api', '') || 'http://localhost:3000';
    console.log('[STEP 1.5] baseUrl:', baseUrl);
    
    if (error) {
      console.error('[STEP 2] OAuth error from Okta:', error);
      return NextResponse.redirect(`${baseUrl}/?error=custom_auth_error&error_description=${encodeURIComponent(error)}`);
    }
    
    if (!code) {
      console.error('[STEP 3] No code in callback');
      return NextResponse.redirect(`${baseUrl}/?error=missing_code`);
    }
    
    // Get current session
    console.log('[STEP 4] Getting server session...');
    const session = await getServerSession(authOptions);
    console.log('[STEP 4.5] Session result:', session ? 'EXISTS' : 'MISSING');
    if (!session) {
      console.error('[STEP 5] No session found');
      return NextResponse.redirect(`${baseUrl}/?error=not_authenticated`);
    }
    
    // Fetch config from backend
    const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    console.log('[STEP 6] Backend URL:', backendUrl);
    
    let mainServerId = 'default';
    let audience = 'api://streamward-chat';
    let oktaDomain = process.env.NEXT_PUBLIC_OKTA_BASE_URL;
    
    try {
      console.log('[STEP 7] Attempting to fetch config from:', `${backendUrl}/api/config/okta`);
      const configResponse = await fetch(`${backendUrl}/api/config/okta`, {
        cache: 'no-store',
      });
      console.log('[STEP 7.5] Config response status:', configResponse.status);
      
      if (configResponse.ok) {
        const backendConfig = await configResponse.json();
        mainServerId = backendConfig.mainServerId;
        audience = backendConfig.audience;
        oktaDomain = backendConfig.oktaDomain || oktaDomain;
        console.log('[STEP 8] Backend config received:', { mainServerId, audience, oktaDomain });
      } else {
        console.warn('[STEP 8.5] Config response not ok, status:', configResponse.status);
      }
    } catch (error) {
      console.warn('[STEP 9] Backend config fetch failed:', error instanceof Error ? error.message : String(error));
      mainServerId = process.env.NEXT_PUBLIC_OKTA_MAIN_SERVER_ID || 'default';
      audience = process.env.NEXT_PUBLIC_OKTA_AUDIENCE || process.env.NEXT_PUBLIC_OKTA_MAIN_AUDIENCE || 'api://streamward-chat';
      console.log('[STEP 9.5] Using fallback config:', { mainServerId, audience });
    }
    
    const clientId = process.env.OKTA_CLIENT_ID;
    const clientSecret = process.env.OKTA_CLIENT_SECRET;
    
    console.log('[STEP 10] Credentials check:', { 
      clientId: clientId ? '✓' : '✗', 
      clientSecret: clientSecret ? '✓' : '✗',
      oktaDomain: oktaDomain ? '✓' : '✗'
    });
    
    const redirectUri = `${process.env.NEXTAUTH_URL || 'http://localhost:3000'}/api/auth/callback/custom`;
    console.log('[STEP 11] Redirect URI:', redirectUri);
    
    if (!oktaDomain || !clientId || !clientSecret) {
      console.error('[STEP 12] Missing config:', { oktaDomain, clientId, clientSecret });
      return NextResponse.redirect(`${baseUrl}/?error=missing_config`);
    }
    
    const customIssuer = `${oktaDomain}/oauth2/${mainServerId}`;
    const tokenEndpoint = `${customIssuer}/v1/token`;
    console.log('[STEP 13] Token endpoint:', tokenEndpoint);
    
    // Get code verifier and state from cookies
    console.log('[STEP 14] Reading cookies...');
    const cookieStore = await cookies();
    console.log('[STEP 14.5] Cookie store obtained');
    
    const codeVerifier = cookieStore.get('custom-auth-verifier')?.value;
    const storedState = cookieStore.get('custom-auth-state')?.value;
    console.log('[STEP 15] Cookie values:', { 
      codeVerifier: codeVerifier ? '✓' : '✗', 
      storedState: storedState ? '✓' : '✗'
    });
    
    // Verify state
    if (state && storedState && state !== storedState) {
      console.error('[STEP 16] State mismatch:', { state, storedState });
      return NextResponse.redirect(`${baseUrl}/?error=state_mismatch`);
    }
    console.log('[STEP 17] State verification passed');
    
    // Exchange code for tokens
    const tokenParams: Record<string, string> = {
      grant_type: 'authorization_code',
      client_id: clientId,
      client_secret: clientSecret,
      code,
      redirect_uri: redirectUri,
    };
    
    if (codeVerifier) {
      tokenParams.code_verifier = codeVerifier;
    }
    
    console.log('[STEP 18] Exchanging code for tokens at:', tokenEndpoint);
    const tokenResponse = await fetch(tokenEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams(tokenParams),
    });
    
    console.log('[STEP 19] Token exchange response status:', tokenResponse.status);
    
    if (!tokenResponse.ok) {
      const errorData = await tokenResponse.json();
      console.error('[STEP 20] Token exchange failed:', { status: tokenResponse.status, error: errorData });
      return NextResponse.redirect(`${baseUrl}/?error=token_exchange_failed&details=${encodeURIComponent(JSON.stringify(errorData))}`);
    }
    
    const tokens = await tokenResponse.json();
    console.log('[STEP 21] Tokens received successfully');
    
    // Store tokens in cookies
    const response = NextResponse.redirect(`${baseUrl}/?custom_auth=success`);
    
    console.log('[STEP 22] Setting custom-access-token cookie...');
    response.cookies.set('custom-access-token', tokens.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 3600,
      path: '/',
    });
    console.log('[STEP 22.5] custom-access-token cookie set');
    
    if (tokens.id_token) {
      console.log('[STEP 23] Setting custom-id-token cookie...');
      response.cookies.set('custom-id-token', tokens.id_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge: 3600,
        path: '/',
      });
      console.log('[STEP 23.5] custom-id-token cookie set');
    }
    
    // Clear PKCE cookies
    response.cookies.delete('custom-auth-verifier');
    response.cookies.delete('custom-auth-state');
    console.log('[STEP 24] PKCE cookies cleared');
    
    console.log('=== CUSTOM AUTH CALLBACK SUCCESS ===');
    return response;
  } catch (error) {
    console.error('=== CUSTOM AUTH CALLBACK ERROR ===');
    console.error('Error type:', error?.constructor?.name);
    console.error('Error message:', error instanceof Error ? error.message : String(error));
    console.error('Error stack:', error instanceof Error ? error.stack : undefined);
    console.error('Full error object:', error);
    
    const baseUrl = process.env.NEXTAUTH_URL || process.env.NEXT_PUBLIC_API_BASE_URL?.replace('/api', '') || 'http://localhost:3000';
    const errorMsg = error instanceof Error ? error.message : String(error);
    return NextResponse.redirect(`${baseUrl}/?error=callback_error&details=${encodeURIComponent(errorMsg)}`);
  }
}
