/**
 * Custom Authorization Server Authentication
 * 
 * This module handles authentication with the custom Okta authorization server
 * alongside the org server authentication. It uses the same Native App but
 * authenticates against the custom server endpoint.
 * 
 * This flow is triggered automatically after org server authentication succeeds.
 */

/**
 * Generate PKCE parameters for secure OAuth flow
 */
async function generatePKCE() {
  const encoder = new TextEncoder();
  
  // Generate code verifier
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  const codeVerifier = btoa(String.fromCharCode(...array))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
  
  // Generate code challenge
  const data = encoder.encode(codeVerifier);
  const hash = await crypto.subtle.digest('SHA-256', data);
  const codeChallenge = btoa(String.fromCharCode(...new Uint8Array(hash)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
  
  return { codeVerifier, codeChallenge };
}

/**
 * Generate random state for OAuth flow
 */
function generateState(): string {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return btoa(String.fromCharCode(...array))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
}

/**
 * Fetch Okta configuration from server-side API
 * This allows access to server-side environment variables (OKTA_MAIN_SERVER_ID)
 * without requiring NEXT_PUBLIC_ prefix
 */
async function fetchOktaConfig(): Promise<{ mainServerId: string; audience: string; oktaDomain: string | null }> {
  try {
    const response = await fetch('/api/config/okta');
    if (response.ok) {
      const config = await response.json();
      console.log(' [Custom Auth] Received config from server:', config);
      return {
        mainServerId: config.mainServerId || 'default',
        audience: config.audience || 'api://streamward-chat',
        oktaDomain: config.oktaDomain,
      };
    } else {
      console.warn(' [Custom Auth] Config API returned error:', response.status, response.statusText);
    }
  } catch (error) {
    console.warn(' [Custom Auth] Failed to fetch Okta config from server, using defaults:', error);
  }
  
  // Fallback to client-side env variables
  const fallbackConfig = {
    mainServerId: process.env.NEXT_PUBLIC_OKTA_MAIN_SERVER_ID || 'default',
    audience: process.env.NEXT_PUBLIC_OKTA_AUDIENCE || 'api://streamward-chat',
    oktaDomain: process.env.NEXT_PUBLIC_OKTA_DOMAIN || process.env.NEXT_PUBLIC_OKTA_BASE_URL || null,
  };
  console.log(' [Custom Auth] Using fallback config:', fallbackConfig);
  return fallbackConfig;
}

/**
 * Initiate custom server OAuth flow (for client-side use)
 * This creates a redirect to the custom server authorization endpoint
 * Uses the same app credentials as org server auth
 */
export async function initiateCustomServerAuth(): Promise<void> {
  // Fetch config from server (to get OKTA_MAIN_SERVER_ID) with client-side fallback
  const config = await fetchOktaConfig();
  const oktaDomain = config.oktaDomain || process.env.NEXT_PUBLIC_OKTA_DOMAIN || process.env.NEXT_PUBLIC_OKTA_BASE_URL;
  const mainServerId = config.mainServerId;
  const clientId = process.env.NEXT_PUBLIC_OKTA_CLIENT_ID;
  const audience = config.audience;
  const redirectUri = `${window.location.origin}/api/auth/callback/custom`;
  
  if (!oktaDomain || !clientId) {
    console.error('Custom server auth: Missing required configuration');
    return;
  }
  
  console.log(' [Custom Auth] Using server ID:', mainServerId, 'with audience:', audience);
  
  const customIssuer = `${oktaDomain}/oauth2/${mainServerId}`;
  const { codeVerifier, codeChallenge } = await generatePKCE();
  const state = generateState();
  
  // Store PKCE parameters in cookies for server-side callback access
  document.cookie = `custom-auth-state=${state}; path=/; SameSite=Lax; max-age=600`;
  document.cookie = `custom-auth-verifier=${codeVerifier}; path=/; SameSite=Lax; max-age=600`;
  
  // Also store in sessionStorage as backup
  sessionStorage.setItem('custom-auth-state', state);
  sessionStorage.setItem('custom-auth-verifier', codeVerifier);
  
  // Redirect to custom server authorization (using same client_id)
  const authUrl = `${customIssuer}/v1/authorize?` +
    `client_id=${clientId}&` +
    `redirect_uri=${encodeURIComponent(redirectUri)}&` +
    `response_type=code&` +
    `scope=openid profile email&` +
    `audience=${encodeURIComponent(audience)}&` +
    `state=${state}&` +
    `code_challenge=${codeChallenge}&` +
    `code_challenge_method=S256`;
  
  window.location.href = authUrl;
}

/**
 * Check if custom server authentication is needed and trigger it automatically
 * This should be called after org server authentication succeeds
 */
export function checkAndTriggerCustomAuth(hasCustomToken: boolean): void {
  // Check if we already have custom token (from session or URL param)
  if (hasCustomToken) {
    // If we have token, clear any logout flags (user is authenticated)
    sessionStorage.removeItem('just-logged-out');
    return; // Already authenticated
  }
  
  // Check if we just logged out - don't trigger custom auth
  // But only if we don't have a custom token (already checked above)
  const justLoggedOut = sessionStorage.getItem('just-logged-out') === 'true';
  const urlParams = new URLSearchParams(window.location.search);
  const fromLogout = urlParams.get('from_logout') === 'true';
  
  // Only skip if actively coming from logout flow
  // Use a time-based check: if flag is older than 3 seconds, assume it's stale
  if (justLoggedOut || fromLogout) {
    // Check when flag was set (if we stored timestamp)
    const logoutTime = sessionStorage.getItem('just-logged-out-time');
    if (logoutTime) {
      const timeSinceLogout = Date.now() - parseInt(logoutTime, 10);
      if (timeSinceLogout > 3000) {
        // More than 3 seconds ago - likely stale, clear it
        console.log('🧹 [Custom Auth] Clearing stale logout flag');
        sessionStorage.removeItem('just-logged-out');
        sessionStorage.removeItem('just-logged-out-time');
      } else {
        console.log('🚫 [Custom Auth] Skipping - user just logged out (recent)');
        return;
      }
    } else {
      // No timestamp - could be stale, but err on side of caution for 2 seconds
      console.log('🚫 [Custom Auth] Skipping - user just logged out (no timestamp)');
      return;
    }
  }
  
  // Check if we're returning from custom auth callback
  if (urlParams.get('custom_auth') === 'success') {
    // We just completed custom auth, reload page to get tokens in session
    window.location.href = window.location.pathname;
    return;
  }
  
  // Check if we've already initiated (to prevent loops)
  if (sessionStorage.getItem('custom-auth-initiated') === 'true') {
    return;
  }
  
  // Mark as initiated and trigger OAuth flow
  sessionStorage.setItem('custom-auth-initiated', 'true');
  console.log('Initiating custom server OAuth flow...');
  initiateCustomServerAuth().catch(error => {
    console.error('Error initiating custom server auth:', error);
    sessionStorage.removeItem('custom-auth-initiated');
  });
}

