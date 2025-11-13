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
  
  // Clear NextAuth cookies (including JWT token)
  // Note: Cookie names may have dots or dashes - try both variations
  const jwtCookieNames = [
    'next-auth.session-token',
    '__Secure-next-auth.session-token',
    '__Host-next-auth.session-token',
    '__Secure.next-auth.session-token', // With dots
    '__Host.next-auth.session-token',    // With dots
    'next-auth.csrf-token',
    '__Secure-next-auth.csrf-token',
    '__Host-next-auth.csrf-token',
    '__Secure.next-auth.csrf-token',     // With dots
    '__Host.next-auth.csrf-token',       // With dots
    'next-auth.callback-url',
    '__Secure-next-auth.callback-url',
    '__Host-next-auth.callback-url',
    '__Secure.next-auth.callback-url',   // With dots
    '__Host.next-auth.callback-url',     // With dots
    'next-auth',
    '__Secure-next-auth',
    '__Host-next-auth',
    '__Secure.next-auth',                // With dots
    '__Host.next-auth',                  // With dots
  ];
  
  // Get all cookies to ensure we catch all variations
  const allCookies = cookieStore.getAll();
  console.log('[Signout] All cookies found:', allCookies.map(c => c.name));
  
  // Clear all NextAuth related cookies with multiple attempts to ensure deletion
  for (const cookie of allCookies) {
    if (cookie.name.includes('next-auth') || cookie.name.includes('nextauth')) {
      console.log('[Signout] Clearing cookie:', cookie.name);
      
      // Try multiple ways to clear the cookie
      cookieStore.delete(cookie.name);
      
      // Method 1: Set to empty with max-age=0
      response.cookies.set(cookie.name, '', {
        maxAge: 0,
        path: '/',
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
      });
      
      // Method 2: Set to empty with past date
      response.cookies.set(cookie.name, '', {
        expires: new Date(0),
        path: '/',
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
      });
      
      response.cookies.delete(cookie.name);
    }
  }
  
  // Also explicitly clear known cookie names
  for (const cookieName of jwtCookieNames) {
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
    let finalRedirectUrl = baseUrl;
    let shouldClearCookies = true;
    
    if (redirectToOkta && oktaBaseUrl) {
      // Logout from Okta org endpoint
      // Okta will use session cookies to identify the user, so we need to keep them for this request!
      // The cookies will be cleared by Okta's logout response, or by the /logout page when we return
      const postLogoutRedirectUri = `${baseUrl}/logout`;
      finalRedirectUrl = `${oktaBaseUrl}/oauth2/v1/logout?post_logout_redirect_uri=${encodeURIComponent(postLogoutRedirectUri)}`;
      
      // If we have the ID token, add it as a hint (but it's not required)
      if (idToken) {
        finalRedirectUrl += `&id_token_hint=${encodeURIComponent(idToken)}`;
      }
      
      // DO NOT clear cookies yet - Okta needs them to verify the logout request!
      // The browser will include them automatically in the redirect to Okta
      // After Okta logout, we'll redirect to /logout which will clear any remaining cookies
      shouldClearCookies = false;
      console.log('[Signout] Redirecting to Okta org logout, will return to:', postLogoutRedirectUri);
    } else {
      // Redirect to logout page to ensure session is cleared properly
      finalRedirectUrl = `${baseUrl}/logout`;
      console.log('[Signout] Redirecting to logout page');
    }
    
    // Create response with redirect
    const response = NextResponse.redirect(finalRedirectUrl, { status: 302 });
    
    // Only clear cookies if not redirecting to Okta
    if (shouldClearCookies) {
      return clearAllCookies(response);
    }
    
    return response;
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
    let finalRedirectUrl = baseUrl;
    let shouldClearCookies = true;
    
    if (redirectToOkta && oktaBaseUrl) {
      // Logout from Okta org endpoint
      // Okta will use session cookies to identify the user
      const postLogoutRedirectUri = `${baseUrl}/logout`;
      finalRedirectUrl = `${oktaBaseUrl}/oauth2/v1/logout?post_logout_redirect_uri=${encodeURIComponent(postLogoutRedirectUri)}`;
      
      // If we have the ID token, add it as a hint (optional)
      if (idToken) {
        finalRedirectUrl += `&id_token_hint=${encodeURIComponent(idToken)}`;
      }
      
      // DO NOT clear cookies yet - Okta needs them!
      shouldClearCookies = false;
      console.log('[Signout] POST: Redirect to Okta org logout');
    } else {
      finalRedirectUrl = `${baseUrl}/logout`;
      console.log('[Signout] POST: Redirecting to logout page');
    }
    
    // Create response with redirect
    const response = NextResponse.redirect(finalRedirectUrl, { status: 302 });
    
    // Only clear cookies if not redirecting to Okta
    if (shouldClearCookies) {
      return clearAllCookies(response);
    }
    
    return response;
  } catch (error) {
    console.error('[Signout] POST Exception:', error instanceof Error ? error.message : String(error));
    const baseUrl = process.env.NEXTAUTH_URL || 'http://localhost:3000';
    return NextResponse.redirect(baseUrl, { status: 302 });
  }
}
