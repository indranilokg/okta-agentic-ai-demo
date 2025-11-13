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
 */
function clearAllCookies(response: NextResponse) {
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
    'org-id-token',
    'custom-auth-state',
    'custom-auth-verifier',
    'temp-logout-id-token',
  ];
  
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
  
  console.log('[Signout] Cleared all authentication cookies');
  return response;
}

export async function GET(request: Request) {
  try {
    console.log('[Signout] GET request started');
    
    const { searchParams } = new URL(request.url);
    const redirectToOkta = searchParams.get('redirect_to_okta') === 'true';
    
    const cookieStore = await cookies();
    let idToken: string | undefined;
    
    // Try to get ID token from temporary cookie set by client
    const tempCookie = cookieStore.get('temp-logout-id-token');
    if (tempCookie?.value) {
      idToken = tempCookie.value;
      console.log('[Signout] Got token from temp cookie');
    }
    
    // Fallback: try session
    if (!idToken) {
      const session = await getServerSession(authOptions);
      if (session?.idToken) {
        idToken = session.idToken;
        console.log('[Signout] Got token from session');
      }
    }
    
    // Fallback: try org-id-token cookie
    if (!idToken) {
      const orgCookie = cookieStore.get('org-id-token');
      if (orgCookie?.value) {
        idToken = orgCookie.value;
        console.log('[Signout] Got token from org-id-token cookie');
      }
    }
    
    const oktaBaseUrl = process.env.OKTA_DOMAIN || process.env.NEXT_PUBLIC_OKTA_BASE_URL;
    const baseUrl = process.env.NEXTAUTH_URL || 'http://localhost:3000';
    
    console.log('[Signout] Config check - oktaBaseUrl present:', !!oktaBaseUrl, 'redirectToOkta:', redirectToOkta, 'hasToken:', !!idToken);
    
    // Build redirect URL
    let redirectUrl = baseUrl;
    if (redirectToOkta && oktaBaseUrl && idToken) {
      // Okta logout endpoint - it will then redirect to post_logout_redirect_uri
      const postLogoutRedirectUri = `${baseUrl}/?logout=success`;
      redirectUrl = `${oktaBaseUrl}/oauth2/v1/logout?id_token_hint=${encodeURIComponent(idToken)}&post_logout_redirect_uri=${encodeURIComponent(postLogoutRedirectUri)}`;
      console.log('[Signout] Redirecting to Okta logout, will return to:', postLogoutRedirectUri);
    } else {
      console.log('[Signout] Redirecting to home');
    }
    
    // Create response with redirect
    const response = NextResponse.redirect(redirectUrl, { status: 302 });
    
    // Clear all cookies before returning
    return clearAllCookies(response);
  } catch (error) {
    console.error('[Signout] Exception:', error instanceof Error ? error.message : String(error));
    const baseUrl = process.env.NEXTAUTH_URL || 'http://localhost:3000';
    return NextResponse.redirect(baseUrl, { status: 302 });
  }
}

export async function POST(request: Request) {
  try {
    console.log('[Signout] POST request received');
    
    const { searchParams } = new URL(request.url);
    const redirectToOkta = searchParams.get('redirect_to_okta') === 'true';
    
    const cookieStore = await cookies();
    let idToken: string | undefined;
    
    // Try to get ID token from temporary cookie
    const tempCookie = cookieStore.get('temp-logout-id-token');
    if (tempCookie?.value) {
      idToken = tempCookie.value;
      console.log('[Signout] POST: Got token from temp cookie');
    }
    
    const oktaBaseUrl = process.env.OKTA_DOMAIN || process.env.NEXT_PUBLIC_OKTA_BASE_URL;
    const baseUrl = process.env.NEXTAUTH_URL || 'http://localhost:3000';
    
    // Build redirect URL
    let redirectUrl = baseUrl;
    if (redirectToOkta && oktaBaseUrl && idToken) {
      const postLogoutRedirectUri = `${baseUrl}/?logout=success`;
      redirectUrl = `${oktaBaseUrl}/oauth2/v1/logout?id_token_hint=${encodeURIComponent(idToken)}&post_logout_redirect_uri=${encodeURIComponent(postLogoutRedirectUri)}`;
      console.log('[Signout] POST: Redirect to Okta logout');
    }
    
    // Create response with redirect
    const response = NextResponse.redirect(redirectUrl, { status: 302 });
    
    // Clear all cookies before returning
    return clearAllCookies(response);
  } catch (error) {
    console.error('[Signout] POST Exception:', error instanceof Error ? error.message : String(error));
    const baseUrl = process.env.NEXTAUTH_URL || 'http://localhost:3000';
    return NextResponse.redirect(baseUrl, { status: 302 });
  }
}
