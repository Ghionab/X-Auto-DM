'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

export default function XOAuthCallback() {
  const router = useRouter();

  useEffect(() => {
    // This page is now just a fallback for any remaining OAuth redirects
    // Since we're now using direct TwitterAPI.io login, we'll just redirect back to accounts
    setTimeout(() => {
      router.push('/accounts');
    }, 1500);
  }, [router]);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardContent className="p-8 text-center">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Redirecting</h2>
          <p className="text-gray-600">
            We've updated our authentication system. Taking you back to the accounts page...
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
