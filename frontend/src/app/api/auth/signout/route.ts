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
    console.log('[Signout API] GET request started');
    
    // Check if we need to redirect to Okta logout
    const { searchParams } = new URL(request.url);
    const redirectToOkta = searchParams.get('redirect_to_okta') === 'true';
    console.log('[Signout API] Redirect to Okta requested:', redirectToOkta);
    
    // Get ID token from query param (passed from client before session was cleared)
    let idTokenToUse = searchParams.get('id_token');
    
    // Try multiple sources for ID token to avoid URL length issues
    const cookieStore = await cookies();
    
    // 1. First check for temporary cookie set by client (avoids URL length limits)
    const tempTokenCookie = cookieStore.get('temp-logout-id-token');
    if (tempTokenCookie?.value) {
      idTokenToUse = tempTokenCookie.value;
      console.log('[Signout API] Got ID token from temporary logout cookie (length: ' + idTokenToUse.length + ')');
    } else {
      console.log('[Signout API] No temporary logout cookie found');
    }
    
    // 2. Try to get from session
    if (!idTokenToUse) {
      const session = await getServerSession(authOptions);
      if (session?.idToken) {
        idTokenToUse = session.idToken;
        console.log('[Signout API] Got ID token from session');
      }
    }
    
    // 3. Check org-id-token cookie as fallback
    if (!idTokenToUse) {
      const orgIdTokenCookie = cookieStore.get('org-id-token');
      if (orgIdTokenCookie?.value) {
        idTokenToUse = orgIdTokenCookie.value;
        console.log('[Signout API] Got ID token from org-id-token cookie');
      }
    }
    
    const oktaBaseUrl = process.env.OKTA_DOMAIN || process.env.NEXT_PUBLIC_OKTA_BASE_URL;
    const baseUrl = process.env.NEXTAUTH_URL || 'http://localhost:3000';
    
    console.log('[Signout API] Final check - redirectToOkta:', redirectToOkta, 'hasIdToken:', !!idTokenToUse, 'oktaBaseUrl:', !!oktaBaseUrl);
    
    // Clear all cookies
    const response = clearAllCookies(() => NextResponse.json({ 
      success: true,
      redirectUrl: null,
    }));
    
    // Clear the temporary logout token cookie
    response.cookies.delete('temp-logout-id-token');
    
    // If redirect to Okta is requested, return the URL as JSON instead of redirecting server-side
    // This avoids Vercel timeout issues with external redirects
    if (redirectToOkta && oktaBaseUrl && idTokenToUse) {
      // Use ID token hint for logout (required by Okta)
      const oktaLogoutUrl = `${oktaBaseUrl}/oauth2/v1/logout?id_token_hint=${encodeURIComponent(idTokenToUse)}&post_logout_redirect_uri=${encodeURIComponent(baseUrl)}`;
      console.log('[Signout API] Returning Okta logout URL to client');
      
      const jsonResponse = NextResponse.json({
        success: true,
        redirectUrl: oktaLogoutUrl,
      });
      
      // Copy cookies from the clearAllCookies response
      for (const [name, value] of response.cookies.getSetCookie()) {
        jsonResponse.cookies.set(name, value);
      }
      
      return jsonResponse;
    } else if (redirectToOkta && !idTokenToUse) {
      console.log('[Signout API] No ID token - returning home URL to client');
      
      const jsonResponse = NextResponse.json({
        success: true,
        redirectUrl: baseUrl,
      });
      
      for (const [name, value] of response.cookies.getSetCookie()) {
        jsonResponse.cookies.set(name, value);
      }
      
      return jsonResponse;
    }
    
    // Default: return home URL
    console.log('[Signout API] Returning home URL to client');
    const jsonResponse = NextResponse.json({
      success: true,
      redirectUrl: baseUrl,
    });
    
    for (const [name, value] of response.cookies.getSetCookie()) {
      jsonResponse.cookies.set(name, value);
    }
    
    return jsonResponse;
  } catch (error) {
    console.error('[Signout API] Error:', error);
    const baseUrl = process.env.NEXTAUTH_URL || 'http://localhost:3000';
    return NextResponse.redirect(`${baseUrl}?error=logout_failed`, { status: 302 });
  }
}

