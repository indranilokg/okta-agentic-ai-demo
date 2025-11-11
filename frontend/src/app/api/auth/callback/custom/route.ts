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
    const { searchParams } = new URL(request.url);
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const error = searchParams.get('error');
    
    const baseUrl = process.env.NEXTAUTH_URL || process.env.NEXT_PUBLIC_API_BASE_URL?.replace('/api', '') || 'http://localhost:3000';
    
    if (error) {
      console.error('Custom server auth error:', error);
      return NextResponse.redirect(`${baseUrl}/?error=custom_auth_error&error_description=${encodeURIComponent(error)}`);
    }
    
    if (!code) {
      return NextResponse.redirect(`${baseUrl}/?error=missing_code`);
    }
    
    // Get current session to ensure user is authenticated with org server first
    const session = await getServerSession(authOptions);
    if (!session) {
      return NextResponse.redirect(`${baseUrl}/?error=not_authenticated`);
    }
    
    const oktaDomain = process.env.OKTA_DOMAIN || process.env.NEXT_PUBLIC_OKTA_BASE_URL;
    const mainServerId = process.env.OKTA_MAIN_SERVER_ID || 'default';
    const clientId = process.env.OKTA_CLIENT_ID;
    const clientSecret = process.env.OKTA_CLIENT_SECRET;
    const audience = process.env.OKTA_AUDIENCE || process.env.OKTA_MAIN_AUDIENCE || 'api://streamward-chat';
    
    // Log configuration for debugging
    console.log(' [Custom Auth Callback] Configuration:');
    console.log('  - OKTA_MAIN_SERVER_ID env var:', process.env.OKTA_MAIN_SERVER_ID || 'NOT SET (using default)');
    console.log('  - mainServerId being used:', mainServerId);
    console.log('  - audience being used:', audience);
    console.log('  - oktaDomain:', oktaDomain);
    const redirectUri = `${process.env.NEXTAUTH_URL || 'http://localhost:3000'}/api/auth/callback/custom`;
    
    if (!oktaDomain || !clientId || !clientSecret) {
      return NextResponse.redirect(`${baseUrl}/?error=missing_config`);
    }
    
    const customIssuer = `${oktaDomain}/oauth2/${mainServerId}`;
    const tokenEndpoint = `${customIssuer}/v1/token`;
    
    // Get code verifier and state from cookies (stored during auth initiation)
    const cookieStore = await cookies();
    const codeVerifier = cookieStore.get('custom-auth-verifier')?.value;
    const storedState = cookieStore.get('custom-auth-state')?.value;
    
    // Verify state to prevent CSRF attacks
    if (state && storedState && state !== storedState) {
      console.error('State mismatch - possible CSRF attack');
      return NextResponse.redirect(`${baseUrl}/?error=state_mismatch`);
    }
    
    // Exchange authorization code for tokens (same app credentials)
    const tokenParams: Record<string, string> = {
      grant_type: 'authorization_code',
      client_id: clientId,
      client_secret: clientSecret,
      code,
      redirect_uri: redirectUri,
    };
    
    // Add PKCE parameters if available
    if (codeVerifier) {
      tokenParams.code_verifier = codeVerifier;
    }
    
    const tokenResponse = await fetch(tokenEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams(tokenParams),
    });
    
    if (!tokenResponse.ok) {
      const errorData = await tokenResponse.json();
      console.error('Token exchange failed:', errorData);
      return NextResponse.redirect(`${baseUrl}/?error=token_exchange_failed&details=${encodeURIComponent(JSON.stringify(errorData))}`);
    }
    
    const tokens = await tokenResponse.json();
    
    console.log(' [Custom Auth Callback] Tokens received from custom server:');
    console.log('  - Access Token (first 50 chars):', tokens.access_token?.substring(0, 50) + '...');
    console.log('  - ID Token (first 50 chars):', tokens.id_token?.substring(0, 50) + '...');
    console.log('  - Full Access Token:', tokens.access_token);
    console.log('  - Full ID Token:', tokens.id_token);
    console.log('  - Token Type:', tokens.token_type);
    console.log('  - Expires In:', tokens.expires_in);
    
    // Store tokens in encrypted cookies that NextAuth JWT callback can access
    const response = NextResponse.redirect(`${baseUrl}/?custom_auth=success`);
    
    // Store tokens temporarily in cookies (will be picked up by JWT callback)
    response.cookies.set('custom-access-token', tokens.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 3600, // 1 hour
      path: '/',
    });
    
    if (tokens.id_token) {
      response.cookies.set('custom-id-token', tokens.id_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge: 3600,
        path: '/',
      });
    }
    
    // Clear PKCE verifier and state cookies
    response.cookies.delete('custom-auth-verifier');
    response.cookies.delete('custom-auth-state');
    
    return response;
  } catch (error) {
    console.error('Custom auth callback error:', error);
    const baseUrl = process.env.NEXTAUTH_URL || process.env.NEXT_PUBLIC_API_BASE_URL?.replace('/api', '') || 'http://localhost:3000';
    return NextResponse.redirect(`${baseUrl}/?error=callback_error`);
  }
}

