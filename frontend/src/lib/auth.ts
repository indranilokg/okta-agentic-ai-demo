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
    async jwt({ token, account, profile }: any) {
      // Persist the OAuth access_token and or the user id to the token right after signin
      if (account) {
        token.accessToken = account.access_token;
        token.idToken = account.id_token;
      }
      if (profile) {
        token.profile = profile;
      }
      return token;
    },
    async session({ session, token }: any) {
      // Send properties to the client, like an access_token and user id from a provider.
      session.accessToken = token.accessToken;
      session.idToken = token.idToken;
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
