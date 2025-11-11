'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { MessageCircle, ArrowLeft } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { Toaster } from '@/components/ui/toaster';
import { api, setAuthToken } from '@/lib/api';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();
  const router = useRouter();
  const searchParams = useSearchParams();

  // Show success message if redirected from registration
  useEffect(() => {
    if (searchParams.get('registered') === 'true') {
      toast({
        title: "Registration Successful",
        description: "Your account has been created successfully. Please sign in to continue.",
      });
    }
  }, [searchParams, toast]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      const response = await api.login(email, password);
      
      if (response.success && response.data) {
        setAuthToken(response.data.access_token);
        toast({
          title: "Login Successful",
          description: `Welcome back, ${response.data.user.username}!`,
        });
        router.push('/dashboard');
      } else {
        toast({
          title: "Login Failed",
          description: response.error || "Invalid credentials. Please try again.",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Login Failed",
        description: "Network error. Please check your connection and try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[var(--bg-page)]">
      <div className="w-full max-w-md space-y-6">
        {/* Logo */}
        <div className="text-center">
          <Link href="/" className="inline-flex items-center space-x-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] mb-8 transition-colors">
            <ArrowLeft className="w-4 h-4" />
            <span>Back to home</span>
          </Link>
          <div className="flex items-center justify-center space-x-2 mb-2">
            <div className="w-10 h-10 bg-[var(--accent-gold-primary)] rounded-lg flex items-center justify-center">
              <MessageCircle className="w-6 h-6 text-[var(--text-inverted)]" />
            </div>
            <span className="text-2xl font-bold text-[var(--text-primary)]">
              XReacher
            </span>
          </div>
          <p className="text-[var(--text-secondary)]">Welcome back! Sign in to your account.</p>
        </div>

        {/* Login Card */}
        <Card className="bg-[var(--bg-card)] border border-[var(--border-subtle)]">
          <CardHeader className="space-y-1 pb-6">
            <CardTitle className="text-2xl font-bold text-center text-[var(--text-primary)]">Sign In</CardTitle>
            <CardDescription className="text-center text-[var(--text-secondary)]">
              Enter your email and password to access your dashboard
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-[var(--text-secondary)]">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="h-12 form-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password" className="text-[var(--text-secondary)]">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="h-12 form-input"
                />
              </div>
              <div className="flex items-center justify-between text-sm">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input type="checkbox" className="rounded" />
                  <span className="text-[var(--text-secondary)]">Remember me</span>
                </label>
                <a href="#" className="text-[var(--accent-gold-secondary)] hover:underline">
                  Forgot password?
                </a>
              </div>
              <Button
                type="submit"
                className="w-full h-12 btn-primary-gold"
                disabled={isLoading}
              >
                {isLoading ? 'Signing in...' : 'Sign In'}
              </Button>
            </form>
            
            <div className="mt-6 text-center text-sm text-[var(--text-secondary)]">
              Don't have an account?{' '}
              <Link href="/register" className="text-[var(--accent-gold-secondary)] hover:underline font-medium">
                Sign up for free
              </Link>
            </div>
          </CardContent>
        </Card>


      </div>
      <Toaster />
    </div>
  );
}
