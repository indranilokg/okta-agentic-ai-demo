# Signout Flow - Debugging Notes

## Current Problem
Logout on Vercel is not working - the Okta IDP session is not being terminated.

## Root Causes Identified

### 1. Query String Being Lost
- Frontend was calling `/api/auth/signout?redirect_to_okta=true` with GET
- Vercel was receiving POST request WITHOUT the query string
- This caused `redirectToOkta` to always be false
- **Fix Applied**: Changed to POST with body parameter `{ redirectToOkta: true }`

### 2. Cookies Cleared Before Okta Logout
- We were clearing cookies BEFORE redirecting to Okta
- Okta needs the session cookies to identify the user for logout
- **Fix Applied**: Don't clear cookies before redirect to Okta (only after returning from Okta)

### 3. Multiple Redirect Chain Issues
- Complex flow: signout route → cookie clearing → Okta redirect → /logout page → home
- Multiple opportunities for things to break
- Browser/Vercel may be interfering with redirects

## Recommended Simpler Approach for Tomorrow

```typescript
// In page.tsx handleLogout():
const handleLogout = async () => {
  // 1. Get ID token before NextAuth session is cleared
  const idToken = session?.idToken;
  
  // 2. Sign out from NextAuth locally
  await signOut({ redirect: false });
  
  // 3. Set logout flag
  sessionStorage.setItem('just-logged-out', 'true');
  
  // 4. Redirect directly to Okta logout with browser navigation
  const oktaBaseUrl = process.env.NEXT_PUBLIC_OKTA_BASE_URL;
  const appUrl = process.env.NEXT_PUBLIC_NEXTAUTH_URL || window.location.origin;
  
  if (oktaBaseUrl && idToken) {
    const logoutUrl = `${oktaBaseUrl}/oauth2/v1/logout?` +
      `id_token_hint=${encodeURIComponent(idToken)}&` +
      `post_logout_redirect_uri=${encodeURIComponent(appUrl + '/?logout=success')}`;
    
    window.location.href = logoutUrl;
  } else {
    window.location.href = '/';
  }
};
```

## Benefits of Simpler Approach
- No complex API route coordination
- No cookies getting cleared at the wrong time
- Okta handles IDP logout directly from browser
- Client-side redirect is straightforward
- Fewer points of failure

## Current Implementation Status
- `/api/auth/signout` now accepts `redirectToOkta` via POST body
- Returns JSON with redirect URL instead of server-side redirect
- POST handler: `/api/auth/signout` with body `{ redirectToOkta: true }`
- Frontend calls from `page.tsx` `handleLogout()`

## Files Modified
- `frontend/src/app/page.tsx` - Changed fetch to POST with JSON body
- `frontend/src/app/api/auth/signout/route.ts` - Added body parameter handling, returns JSON
- `frontend/src/app/logout/page.tsx` - Created but may not be needed in simpler approach
- `frontend/src/lib/auth.ts` - Session callback returns null when no idToken
- `frontend/src/lib/custom-auth.ts` - Checks for logout success parameter

## Next Steps
1. Test the POST+body approach first (already deployed)
2. If still not working, implement the simpler client-side redirect approach
3. Remove `/logout` page and all the complex coordination logic
4. Test end-to-end logout with Okta dashboard verification

