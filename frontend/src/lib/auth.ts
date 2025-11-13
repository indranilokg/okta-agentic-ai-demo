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
        console.debug(`[JWT] Org ID token stored`);
        if (process.env.NODE_ENV === 'development') {
          console.debug(`[JWT] ID Token (first 50): ${account.id_token?.substring(0, 50)}...`);
          console.debug(`[JWT] Full ID Token: ${account.id_token}`);
        }
      }
      
      // Clear tokens if signOut is triggered
      if (trigger === 'signOut') {
        console.debug('[JWT] SignOut triggered - clearing tokens');
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
          token.customAccessToken = customAccessTokenCookie.value;
        } else if (token.customAccessToken) {
          // Tokens missing from cookies - likely logout
          token.customAccessToken = undefined;
        }
      } catch (error) {
        // Cookies might not be available in all contexts, ignore silently
      }
      
      return token;
    },
    async session({ session, token }: any) {
      // If no idToken, user is logged out - return null to clear session
      if (!token.idToken) {
        console.debug('[Session] No idToken in token - user is logged out');
        return null;
      }
      
      // Store only what's needed:
      // - Org ID token (for frontend display)
      // - Custom access token (for token exchange)
      session.idToken = token.idToken;
      session.customAccessToken = token.customAccessToken;
      
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
