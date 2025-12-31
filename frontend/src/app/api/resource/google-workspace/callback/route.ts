import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

export async function GET(request: NextRequest) {
  console.log('[CALLBACK] ===== CALLBACK ROUTE HIT =====');
  console.log('[CALLBACK] Full URL:', request.url);
  console.log('[CALLBACK] Method:', request.method);
  console.log('[CALLBACK] Headers:', Object.fromEntries(request.headers.entries()));
  
  try {
    // Get connect_code and state from query parameters
    // Auth0 Connected Accounts returns 'connect_code' parameter
    const searchParams = request.nextUrl.searchParams;
    const connectCode = searchParams.get('connect_code') || searchParams.get('code');
    const state = searchParams.get('state');
    
    console.log('[CALLBACK] ===== PARAMETERS =====');
    console.log('[CALLBACK] Connect code:', connectCode ? connectCode.substring(0, 20) + '...' : null);
    console.log('[CALLBACK] Connect code full length:', connectCode ? connectCode.length : 0);
    console.log('[CALLBACK] State:', state);
    console.log('[CALLBACK] All search params:', Object.fromEntries(searchParams.entries()));
    
    // Detect if this is opened in a popup window by checking the referer
    // If opened from a popup, window.opener will be available on the client side
    // We'll detect this in the HTML response instead of using URL parameters
    
    if (!connectCode) {
      // Check if this is an error from Auth0 (error parameter present)
      const error = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');
      
      // Only send error if Auth0 explicitly returned an error
      // Otherwise, this might just be an initial page load - don't send error message
      if (error) {
        console.error('[CALLBACK] Auth0 returned error:', error, errorDescription);
        return new NextResponse(`
          <!DOCTYPE html>
          <html>
            <head><title>Authorization Error</title></head>
            <body>
              <script>
                if (window.opener) {
                  console.log('[CALLBACK] Sending Auth0 error to parent');
                  try {
                    window.opener.postMessage({
                      type: 'GOOGLE_LINKING_ERROR',
                      error: ${JSON.stringify(errorDescription || error || 'Authorization failed')}
                    }, window.location.origin);
                  } catch (e) {
                    console.error('[CALLBACK] Error sending error message:', e);
                  }
                  setTimeout(() => window.close(), 1000);
                } else {
                  window.location.href = '/?error=auth_failed';
                }
              </script>
              <p>Authorization error occurred. This window will close automatically.</p>
            </body>
          </html>
        `, {
          headers: { 'Content-Type': 'text/html' },
        });
      }
      
      // No code and no error - might be initial page load or redirect
      // Don't send error message, just show a message and close/redirect
      return new NextResponse(`
        <!DOCTYPE html>
        <html>
          <head><title>Authorization</title></head>
          <body>
            <script>
              if (window.opener) {
                // In popup but no code - might be initial load, don't send error
                // Just close the popup silently
                console.log('[CALLBACK] No code received, closing popup silently');
                setTimeout(() => window.close(), 500);
              } else {
                // Not in popup - redirect to main page
                window.location.href = '/';
              }
            </script>
            <p>Please wait...</p>
          </body>
        </html>
      `, {
        headers: { 'Content-Type': 'text/html' },
      });
    }
    
    // Return HTML that extracts connect_code and sends it to parent window
    // Parent window will then call backend to complete linking
    // Backend has auth_session stored server-side from when authz_url was generated
    return new NextResponse(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Authorization Complete</title>
          <style>
            body {
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
              display: flex;
              align-items: center;
              justify-content: center;
              height: 100vh;
              margin: 0;
              background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
              color: white;
            }
            .container {
              text-align: center;
              padding: 2rem;
            }
            .success-icon {
              width: 64px;
              height: 64px;
              margin: 0 auto 1rem;
              background: white;
              border-radius: 50%;
              display: flex;
              align-items: center;
              justify-content: center;
              color: #10b981;
            }
            h1 {
              margin: 0 0 0.5rem;
              font-size: 1.5rem;
            }
            p {
              margin: 0;
              opacity: 0.9;
            }
          </style>
        </head>
        <body>
          <div class="container">
            <div class="success-icon">
              <svg width="32" height="32" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h1>Authorization Received</h1>
            <p>Completing account linking...</p>
          </div>
          <script>
            console.log('[CALLBACK] ===== HTML PAGE LOADED =====');
            console.log('[CALLBACK] Page loaded in popup');
            console.log('[CALLBACK] Full URL:', window.location.href);
            console.log('[CALLBACK] Connect code present:', ${JSON.stringify(!!connectCode)});
            console.log('[CALLBACK] Connect code:', ${JSON.stringify(connectCode ? connectCode.substring(0, 20) + '...' : null)});
            console.log('[CALLBACK] Connect code length:', ${JSON.stringify(connectCode ? connectCode.length : 0)});
            console.log('[CALLBACK] State:', ${JSON.stringify(state || 'null')});
            console.log('[CALLBACK] Window opener:', !!window.opener);
            console.log('[CALLBACK] Window opener closed:', window.opener ? window.opener.closed : 'N/A');
            console.log('[CALLBACK] Window location origin:', window.location.origin);
            
            // Send connect_code to parent window immediately
            if (window.opener && !window.opener.closed) {
              console.log('[CALLBACK] Parent window found, preparing to send message');
              console.log('[CALLBACK] Connect code length:', ${JSON.stringify(connectCode ? connectCode.length : 0)});
              console.log('[CALLBACK] State:', ${JSON.stringify(state || 'null')});
              
              const message = {
                type: 'GOOGLE_AUTH_CODE_RECEIVED',
                connect_code: ${JSON.stringify(connectCode)},
                state: ${JSON.stringify(state || null)}
              };
              
              console.log('[CALLBACK] Message to send:', {
                type: message.type,
                has_connect_code: !!message.connect_code,
                connect_code_preview: message.connect_code ? message.connect_code.substring(0, 20) + '...' : null,
                state: message.state
              });
              
              try {
                window.opener.postMessage(message, window.location.origin);
                console.log('[CALLBACK] ✅ Message sent successfully to parent window');
                
                // Update UI to show success
                document.querySelector('.container').innerHTML = \`
                  <div style="width: 64px; height: 64px; margin: 0 auto 1rem; background: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #10b981;">
                    <svg width="32" height="32" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <h1>Code Sent!</h1>
                  <p>Authorization code sent to parent window. Closing...</p>
                \`;
                
                // Close popup after a short delay
                setTimeout(() => {
                  console.log('[CALLBACK] Closing popup window');
                  window.close();
                }, 1000);
              } catch (e) {
                console.error('[CALLBACK] ❌ Error sending message:', e);
                // Show error and close
                document.querySelector('.container').innerHTML = \`
                  <div style="width: 64px; height: 64px; margin: 0 auto 1rem; background: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #ef4444;">
                    <svg width="32" height="32" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </div>
                  <h1>Error</h1>
                  <p>Failed to communicate with parent window. This window will close.</p>
                \`;
                setTimeout(() => window.close(), 2000);
              }
            } else {
              console.log('[CALLBACK] ⚠️ No opener or opener closed');
              console.log('[CALLBACK] Window opener:', window.opener);
              console.log('[CALLBACK] Opener closed:', window.opener ? window.opener.closed : 'N/A');
              
              // Not in popup - redirect to main page with code
              const redirectUrl = new URL('/', window.location.origin);
              redirectUrl.searchParams.set('google_callback', 'true');
              redirectUrl.searchParams.set('code', ${JSON.stringify(connectCode)});
              ${state ? `redirectUrl.searchParams.set('state', ${JSON.stringify(state)});` : ''}
              console.log('[CALLBACK] Redirecting to:', redirectUrl.toString());
              window.location.href = redirectUrl.toString();
            }
          </script>
        </body>
      </html>
    `, {
      headers: { 'Content-Type': 'text/html' },
    });
  } catch (error) {
    console.error('[GOOGLE_CALLBACK] Error:', error);
    // Return HTML that detects popup mode (via window.opener)
    return new NextResponse(`
      <!DOCTYPE html>
      <html>
        <head><title>Authorization Error</title></head>
        <body>
          <script>
            if (window.opener) {
              // Opened in popup - send error message to parent
              window.opener.postMessage({
                type: 'GOOGLE_LINKING_ERROR',
                error: 'Unexpected error'
              }, window.location.origin);
              window.close();
            } else {
              // Not in popup - redirect to main page with error
              window.location.href = '/?error=callback_failed';
            }
          </script>
          <p>An unexpected error occurred. This window will close automatically.</p>
        </body>
      </html>
    `, {
      headers: { 'Content-Type': 'text/html' },
    });
  }
}

