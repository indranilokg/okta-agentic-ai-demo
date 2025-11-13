'use client';

import { useEffect } from 'react';
import { useSession, signOut } from 'next-auth/react';

/**
 * Dedicated logout page that ensures proper session cleanup
 * This page is visited after signout to prevent session recreation
 */
export default function LogoutPage() {
  const { data: session, status } = useSession();

  useEffect(() => {
    // If session still exists after logout attempt, force clear it
    if (status === 'authenticated' && session) {
      console.log('[LogoutPage] Session still exists, calling signOut again');
      signOut({ redirect: false }).then(() => {
        // After signOut, wait a moment and redirect
        setTimeout(() => {
          window.location.href = '/?logout=success';
        }, 500);
      });
      return;
    }

    // If unauthenticated, redirect to home after a short delay
    if (status === 'unauthenticated') {
      console.log('[LogoutPage] Session cleared, redirecting to home');
      const timer = setTimeout(() => {
        window.location.href = '/?logout=success';
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [status, session]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      <div className="text-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mb-4"></div>
        <h1 className="text-2xl font-bold text-gray-800 mb-2">Logging you out...</h1>
        <p className="text-gray-600">Please wait while we clear your session.</p>
      </div>
    </div>
  );
}

