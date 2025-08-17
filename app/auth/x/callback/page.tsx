'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';

export default function XOAuthCallback() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [message, setMessage] = useState('Processing OAuth callback...');

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Get OAuth parameters from URL
        const oauthToken = searchParams.get('oauth_token');
        const oauthVerifier = searchParams.get('oauth_verifier');
        
        if (!oauthToken || !oauthVerifier) {
          setStatus('error');
          setMessage('Missing OAuth parameters. Please try connecting your account again.');
          return;
        }

        // Get stored token secret from session storage
        const oauthTokenSecret = sessionStorage.getItem('oauth_token_secret');
        
        if (!oauthTokenSecret) {
          setStatus('error');
          setMessage('OAuth session expired. Please try connecting your account again.');
          return;
        }

        // Clean up session storage
        sessionStorage.removeItem('oauth_token_secret');

        // Complete OAuth flow
        const response = await api.handleXOAuthCallback({
          oauth_token: oauthToken,
          oauth_verifier: oauthVerifier,
          oauth_token_secret: oauthTokenSecret
        });

        if (response.success && response.data) {
          setStatus('success');
          setMessage(`Successfully connected @${response.data.screen_name}!`);
          
          // Redirect to accounts page after a short delay
          setTimeout(() => {
            window.close(); // Close popup if opened in popup
            // If not in popup, redirect to accounts
            if (window.opener) {
              window.opener.postMessage({ type: 'oauth_success' }, window.location.origin);
            } else {
              router.push('/accounts');
            }
          }, 2000);
        } else {
          setStatus('error');
          setMessage(response.error || 'Failed to connect account. Please try again.');
        }
      } catch (error) {
        console.error('OAuth callback error:', error);
        setStatus('error');
        setMessage('An unexpected error occurred. Please try again.');
      }
    };

    handleCallback();
  }, [searchParams, router]);

  const handleRetry = () => {
    router.push('/accounts');
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardContent className="p-8 text-center">
          {status === 'processing' && (
            <>
              <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Connecting Account</h2>
              <p className="text-gray-600">{message}</p>
            </>
          )}

          {status === 'success' && (
            <>
              <CheckCircle className="w-12 h-12 text-green-600 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Account Connected!</h2>
              <p className="text-gray-600 mb-4">{message}</p>
              <p className="text-sm text-gray-500">Redirecting you back...</p>
            </>
          )}

          {status === 'error' && (
            <>
              <XCircle className="w-12 h-12 text-red-600 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Connection Failed</h2>
              <p className="text-gray-600 mb-6">{message}</p>
              <Button onClick={handleRetry} className="w-full">
                Back to Accounts
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}