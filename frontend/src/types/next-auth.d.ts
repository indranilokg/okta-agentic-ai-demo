import NextAuth from "next-auth";

declare module "next-auth" {
  interface Session {
    // Store only what's needed:
    idToken?: string; // Org ID token (for frontend display)
    customAccessToken?: string; // Custom access token (for token exchange)
    // NOT stored: org access token, custom ID token (to reduce cookie size)
    user: {
      id?: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
    };
  }

  interface JWT {
    // Store only what's needed:
    idToken?: string; // Org ID token (for frontend display)
    customAccessToken?: string; // Custom access token (for token exchange)
    // NOT stored: org access token, custom ID token (to reduce cookie size)
    profile?: any;
  }
}
