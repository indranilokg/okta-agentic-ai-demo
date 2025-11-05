import NextAuth from "next-auth";
import OktaProvider from "next-auth/providers/okta";

export const authOptions = {
  providers: [
    OktaProvider({
      clientId: process.env.OKTA_CLIENT_ID!,
      clientSecret: process.env.OKTA_CLIENT_SECRET!,
      issuer: process.env.OKTA_ISSUER,
      authorization: {
        params: {
          scope: "openid profile email",
        },
      },
    }),
  ],
  callbacks: {
    async jwt({ token, account, profile, trigger }: any) {
      // Store only what's needed: Org ID token (for frontend display) and Custom access token (for token exchange)
      // Do NOT store: Org access token, Custom ID token (to reduce cookie size)
      if (account) {
        // Store org ID token in JWT (needed for frontend display)
        token.idToken = account.id_token;
        // Store org ID token in separate cookie for logout as well
        if (account.id_token) {
          try {
            const { cookies } = await import('next/headers');
            const cookieStore = await cookies();
            cookieStore.set('org-id-token', account.id_token, {
              httpOnly: true,
              secure: process.env.NODE_ENV === 'production',
              sameSite: 'lax',
              maxAge: 3600, // 1 hour
              path: '/',
            });
          } catch (error) {
            // Ignore if cookies not available
          }
        }
        // Do NOT store org access token (not needed)
        console.log('🔐 [JWT Callback] Org server tokens received:');
        console.log('  - ID Token (first 50 chars):', account.id_token?.substring(0, 50) + '...');
        console.log('  - ID Token stored in JWT for frontend display');
        console.log('  - Org Access Token NOT stored (not needed, reduces cookie size)');
        console.log('  - Full ID Token:', account.id_token);
      }
      
      // Clear tokens if signOut is triggered
      if (trigger === 'signOut') {
        console.log('🔐 [JWT Callback] SignOut triggered - clearing all tokens');
        token.idToken = undefined;
        token.customAccessToken = undefined;
        return token;
      }
      
      if (profile) {
        token.profile = profile;
      }
      
      // Check for custom server tokens from OAuth callback (stored in cookies)
      // Only store custom ACCESS token in JWT (needed for token exchange)
      // Do NOT store custom ID token (not needed, reduces cookie size)
      try {
        const { cookies } = await import('next/headers');
        const cookieStore = await cookies();
        const customAccessTokenCookie = cookieStore.get('custom-access-token');
        
        if (customAccessTokenCookie?.value) {
          // Only store access token in JWT to reduce cookie size
          token.customAccessToken = customAccessTokenCookie.value;
          console.log('🔐 [JWT Callback] Custom server tokens found in cookies:');
          console.log('  - Custom Access Token (first 50 chars):', customAccessTokenCookie.value.substring(0, 50) + '...');
          console.log('  - Custom Access Token stored in JWT for token exchange');
          console.log('  - Custom ID Token NOT stored (not needed, reduces cookie size)');
          console.log('  - Full Custom Access Token:', customAccessTokenCookie.value);
        } else {
          // If cookies are missing but we had tokens before, clear them (logout scenario)
          if (token.customAccessToken) {
            console.log('🔐 [JWT Callback] Custom tokens missing from cookies - clearing from JWT (likely logout)');
            token.customAccessToken = undefined;
          } else {
            console.log('🔐 [JWT Callback] No custom server tokens found in cookies');
          }
        }
      } catch (error) {
        // Cookies might not be available in all contexts, ignore silently
        console.log('🔐 [JWT Callback] Could not read cookies (normal in some contexts):', error);
      }
      
      console.log('🔐 [JWT Callback] Current token state:');
      console.log('  - Has org ID token:', !!token.idToken);
      console.log('  - Has custom access token:', !!token.customAccessToken);
      console.log('  - Org access token NOT stored (not needed)');
      console.log('  - Custom ID token NOT stored (not needed)');
      
      return token;
    },
    async session({ session, token }: any) {
      // Store only what's needed:
      // - Org ID token (for frontend display)
      // - Custom access token (for token exchange)
      session.idToken = token.idToken;
      session.customAccessToken = token.customAccessToken;
      
      console.log('👤 [Session Callback] Building session for user:', token.email || token.sub);
      console.log('  - Org ID Token (first 50 chars):', token.idToken ? token.idToken.substring(0, 50) + '...' : 'NOT AVAILABLE');
      console.log('  - Custom Access Token (first 50 chars):', token.customAccessToken ? token.customAccessToken.substring(0, 50) + '...' : 'NOT AVAILABLE');
      console.log('  - Org Access Token NOT in session (not needed)');
      console.log('  - Custom ID Token NOT in session (not needed)');
      console.log('  - Full Org ID Token:', token.idToken);
      console.log('  - Full Custom Access Token:', token.customAccessToken);
      
      session.user = {
        ...session.user,
        id: token.sub,
        name: token.name || token.profile?.name,
        email: token.email || token.profile?.email,
      };
      return session;
    },
  },
  pages: {
    signIn: "/",
    signOut: "/",
    error: "/",
  },
  session: {
    strategy: "jwt" as const,
  },
  // Additional security settings
  secret: process.env.NEXTAUTH_SECRET,
  debug: process.env.NODE_ENV === 'development',
};
