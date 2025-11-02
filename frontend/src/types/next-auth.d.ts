import NextAuth from "next-auth";

declare module "next-auth" {
  interface Session {
    accessToken?: string;
    idToken?: string;
    user: {
      id?: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
    };
  }

  interface JWT {
    accessToken?: string;
    idToken?: string;
    profile?: any;
  }
}
