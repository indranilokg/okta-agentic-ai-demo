import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

/**
 * This endpoint forces the browser to refetch the session from the server
 * After logout, we need to refresh the client-side session cache
 */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const redirectUrl = searchParams.get('redirect') || '/?logout=success';

  // By making this route dynamic and hitting the server, we force NextAuth
  // to re-validate the session, which will now return null since cookies are cleared
  const response = NextResponse.redirect(redirectUrl, { status: 302 });

  console.log('[SessionRefresh] Redirecting to:', redirectUrl);
  return response;
}


