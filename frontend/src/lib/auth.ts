import NextAuth from "next-auth";
import OktaProvider from "next-auth/providers/okta";

// Get custom authorization server issuer
const getCustomIssuer = () => {
  const oktaDomain = process.env.NEXT_PUBLIC_OKTA_BASE_URL || process.env.NEXT_PUBLIC_OKTA_DOMAIN;
  const mainServerId = process.env.NEXT_PUBLIC_OKTA_MAIN_SERVER_ID || 'default';
  if (oktaDomain) {
    // Remove protocol if present
    const domain = oktaDomain.replace(/^https?:\/\//, '');
    return `https://${domain}/oauth2/${mainServerId}`;
  }
  // Fallback to OKTA_ISSUER if custom server not configured
  return process.env.OKTA_ISSUER;
};

export const authOptions = {
  providers: [
    OktaProvider({
      clientId: process.env.OKTA_CLIENT_ID!,
      clientSecret: process.env.OKTA_CLIENT_SECRET!,
      issuer: getCustomIssuer(),
      authorization: {
        params: {
          scope: "openid profile email",
          audience: process.env.NEXT_PUBLIC_OKTA_AUDIENCE || process.env.NEXT_PUBLIC_OKTA_MAIN_AUDIENCE || "api://streamward-chat",
        },
      },
    }),
  ],
  callbacks: {
    async jwt({ token, account, profile, trigger }: any) {
      // Store only what's needed: Org ID token (for frontend display) and Custom access token (for token exchange)
      // Do NOT store: Org access token, Custom ID token (to reduce cookie size)
      if (account) {
        // Store both ID token (for logout) and access token (for chat assistant)
        token.idToken = account.id_token; // Needed for logout
        token.accessToken = account.access_token; // Used for chat assistant/MCP exchanges
        // Store ID token in cookie for logout
        if (account.id_token) {
          try {
            const { cookies } = await import('next/headers');
            const cookieStore = await cookies();
            cookieStore.set('id-token', account.id_token, {
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
        console.debug(`[JWT] Custom authz server tokens stored (ID token for logout, access token for chat)`);
        if (process.env.NODE_ENV === 'development') {
          console.debug(`[JWT] ID Token (first 50): ${account.id_token?.substring(0, 50)}...`);
          console.debug(`[JWT] Access Token (first 50): ${account.access_token?.substring(0, 50)}...`);
        }
      }
      
      // Clear tokens if signOut is triggered
      if (trigger === 'signOut') {
        console.debug('[JWT] SignOut triggered - clearing tokens');
        token.idToken = undefined;
        token.accessToken = undefined;
        return token;
      }
      
      if (profile) {
        token.profile = profile;
      }
      
      return token;
    },
    async session({ session, token }: any) {
      // If no accessToken, user is logged out - return null to clear session
      if (!token.accessToken) {
        console.debug('[Session] No accessToken in token - user is logged out');
        return null;
      }
      
      // Store both tokens: ID token for logout, access token for chat assistant
      session.idToken = token.idToken; // For logout only
      session.accessToken = token.accessToken; // For chat assistant/MCP exchanges
      
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
  events: {
    async signOut() {
      // Custom signOut event - just log it, don't call any API
      console.log('[AUTH] signOut event triggered');
    },
  },
  session: {
    strategy: "jwt" as const,
  },
  // Additional security settings
  secret: process.env.NEXTAUTH_SECRET,
  debug: process.env.NODE_ENV === 'development',
};
