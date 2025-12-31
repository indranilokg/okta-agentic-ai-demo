import NextAuth from "next-auth";

declare module "next-auth" {
  interface Session {
    // Tokens from custom authorization server
    idToken?: string; // ID token - used for logout only
    accessToken?: string; // Access token - used for chat assistant/MCP exchanges
    user: {
      id?: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
    };
  }

  interface JWT {
    // Tokens from custom authorization server
    idToken?: string; // ID token - used for logout only
    accessToken?: string; // Access token - used for chat assistant/MCP exchanges
    profile?: any;
  }
}
