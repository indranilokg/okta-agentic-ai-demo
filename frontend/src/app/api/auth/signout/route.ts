import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

export const dynamic = 'force-dynamic';

/**
 * Sign out API route that clears all authentication cookies
 * This ensures both NextAuth session cookies and custom auth cookies are deleted
 * 
 * Also handles redirect to Okta logout if needed
 * Supports both GET (for redirects) and POST (for API calls)
 */
function clearAllCookies(createResponse: () => NextResponse = () => new NextResponse()) {
  const cookieStore = cookies();
  
  // Clear NextAuth session cookies (they can have different names depending on security settings)
  const nextAuthCookieNames = [
    'next-auth.session-token',
    '__Secure-next-auth.session-token',
    '__Host-next-auth.session-token',
    'next-auth.csrf-token',
    '__Secure-next-auth.csrf-token',
    '__Host-next-auth.csrf-token',
    'next-auth.callback-url',
    '__Secure-next-auth.callback-url',
    '__Host-next-auth.callback-url',
  ];
  
  // Clear custom auth cookies and ID token cookies
  const customCookieNames = [
    'custom-access-token',
    'custom-id-token',
    'org-id-token', // Org ID token stored separately
    'custom-auth-state',
    'custom-auth-verifier',
  ];
  
  const response = createResponse();
  
  // Clear NextAuth cookies
  for (const cookieName of nextAuthCookieNames) {
    cookieStore.delete(cookieName);
    response.cookies.set(cookieName, '', {
      expires: new Date(0),
      path: '/',
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
    });
    response.cookies.delete(cookieName);
  }
  
  // Clear custom auth cookies
  for (const cookieName of customCookieNames) {
    cookieStore.delete(cookieName);
    response.cookies.set(cookieName, '', {
      expires: new Date(0),
      path: '/',
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
    });
    response.cookies.delete(cookieName);
  }
  
  console.log('🧹 [Signout API] Cleared all authentication cookies');
  console.log('  - Cleared NextAuth cookies:', nextAuthCookieNames.length);
  console.log('  - Cleared custom cookies:', customCookieNames.length);
  
  return response;
}

export async function POST(request: Request) {
  try {
    let body: { redirect_to_okta?: boolean; id_token?: string } = {};
    
    // Try to parse JSON body from POST request
    try {
      const contentType = request.headers.get('content-type');
      if (contentType?.includes('application/json')) {
        body = await request.json();
      }
    } catch (e) {
      console.log('[Signout API] No JSON body in POST request');
    }
    
    const redirectToOkta = body.redirect_to_okta === true;
    let idTokenToUse = body.id_token;
    
    console.log('[Signout API] POST request - redirectToOkta:', redirectToOkta, 'hasIdToken:', !!idTokenToUse);
    
    // If no ID token in body, try to get from session or cookies
    if (!idTokenToUse) {
      const session = await getServerSession(authOptions);
      if (session?.idToken) {
        idTokenToUse = session.idToken;
        console.log('[Signout API] Got ID token from session');
      } else {
        // Try from cookie as fallback
        const cookieStore = await cookies();
        const orgIdTokenCookie = cookieStore.get('org-id-token');
        if (orgIdTokenCookie?.value) {
          idTokenToUse = orgIdTokenCookie.value;
          console.log('[Signout API] Got ID token from cookie');
        }
      }
    }
    
    // Clear all cookies
    const response = clearAllCookies(() => NextResponse.json({ success: true, message: 'All cookies cleared' }));
    
    const oktaBaseUrl = process.env.OKTA_DOMAIN || process.env.NEXT_PUBLIC_OKTA_BASE_URL;
    const baseUrl = process.env.NEXTAUTH_URL || 'http://localhost:3000';
    
    if (redirectToOkta && oktaBaseUrl && idTokenToUse) {
      // Redirect to Okta logout with ID token hint
      const oktaLogoutUrl = `${oktaBaseUrl}/oauth2/v1/logout?id_token_hint=${encodeURIComponent(idTokenToUse)}&post_logout_redirect_uri=${encodeURIComponent(baseUrl)}`;
      console.log('[Signout API] Redirecting to Okta logout');
      return NextResponse.redirect(oktaLogoutUrl, { status: 302 });
    }
    
    return response;
  } catch (error) {
    console.error('[Signout API] Error:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to clear cookies' },
      { status: 500 }
    );
  }
}

export async function GET(request: Request) {
  try {
    // Check if we need to redirect to Okta logout
    const { searchParams } = new URL(request.url);
    const redirectToOkta = searchParams.get('redirect_to_okta') === 'true';
    
    // Get ID token from query param (passed from client before session was cleared)
    let idTokenToUse = searchParams.get('id_token');
    
    // Also try to get from session (might still be available)
    const session = await getServerSession(authOptions);
    if (!idTokenToUse && session?.idToken) {
      idTokenToUse = session.idToken;
      console.log(' [Signout API] Got ID token from session');
    }
    
    // Also check cookie as fallback
    if (!idTokenToUse) {
      const cookieStore = await cookies();
      const orgIdTokenCookie = cookieStore.get('org-id-token');
      if (orgIdTokenCookie?.value) {
        idTokenToUse = orgIdTokenCookie.value;
        console.log(' [Signout API] Got ID token from cookie');
      }
    }
    
    const oktaBaseUrl = process.env.OKTA_DOMAIN || process.env.NEXT_PUBLIC_OKTA_BASE_URL;
    const baseUrl = process.env.NEXTAUTH_URL || 'http://localhost:3000';
    
    console.log('[Signout API] GET request - redirectToOkta:', redirectToOkta, 'hasIdToken:', !!idTokenToUse);
    
    if (redirectToOkta && oktaBaseUrl && idTokenToUse) {
      // Use ID token hint for logout (required by Okta)
      const oktaLogoutUrl = `${oktaBaseUrl}/oauth2/v1/logout?id_token_hint=${encodeURIComponent(idTokenToUse)}&post_logout_redirect_uri=${encodeURIComponent(baseUrl)}`;
      console.log('[Signout API] Redirecting to Okta logout with ID token');
      // Clear cookies and redirect to Okta
      return clearAllCookies(() => NextResponse.redirect(oktaLogoutUrl, { status: 302 }));
    } else if (redirectToOkta && !idTokenToUse) {
      // If no ID token available, skip Okta logout and just clear local cookies
      // Okta logout requires id_token_hint - client_id alone doesn't work
      console.log('[Signout API] No ID token available - skipping Okta logout, clearing local cookies only');
      return clearAllCookies(() => NextResponse.redirect(baseUrl, { status: 302 }));
    }
    
    // If no Okta redirect, redirect to home with cookies cleared
    return clearAllCookies(() => NextResponse.redirect(baseUrl, { status: 302 }));
  } catch (error) {
    console.error('[Signout API] Error:', error);
    const baseUrl = process.env.NEXTAUTH_URL || 'http://localhost:3000';
    return NextResponse.redirect(`${baseUrl}?error=logout_failed`, { status: 302 });
  }
}

