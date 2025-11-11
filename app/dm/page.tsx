'use client';

import { useState, useEffect } from 'react';
import { MessageCircle } from 'lucide-react';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import SendDMForm from '@/components/SendDMForm';
import ConnectXAccountButton from '@/components/ConnectXAccountButton';
import { Card, CardContent } from '@/components/ui/card';
import { toast } from '@/hooks/use-toast';
import { api, TwitterAccount } from '@/lib/api';

export default function DMPage() {
  const [accounts, setAccounts] = useState<TwitterAccount[]>([]);
  const [loading, setLoading] = useState(true);

  // Load accounts on component mount
  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      setLoading(true);
      const response = await api.getTwitterAccounts();
      if (response.success && response.data) {
        setAccounts(response.data.accounts);
      } else {
        toast({
          title: "Error",
          description: "Failed to load connected accounts",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load accounts",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleAccountConnected = async () => {
    // Reload accounts after successful connection
    await loadAccounts();
  };

  const connectedAccounts = accounts.filter(account => account.connection_status === 'connected');

  return (
    <div className="flex min-h-screen bg-[var(--bg-page)]">
      <Sidebar />
      
      <div className="flex-1 lg:ml-64">
        <Header 
          title="Send Direct Messages" 
          subtitle="Send personalized DMs to your prospects using connected X accounts"
        />
        
        <div className="p-6 space-y-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--accent-gold-primary)] mx-auto"></div>
                <p className="mt-2 text-[var(--text-secondary)]">Loading accounts...</p>
              </div>
            </div>
          ) : connectedAccounts.length === 0 ? (
            <Card className="bg-[var(--bg-card)] border border-[var(--border-subtle)]">
              <CardContent className="p-8 text-center">
                <div className="w-16 h-16 bg-[var(--border-subtle)] rounded-full flex items-center justify-center mx-auto mb-4">
                  <MessageCircle className="w-8 h-8 text-[var(--accent-gold-secondary)]" />
                </div>
                <h3 className="font-bold text-lg text-[var(--text-primary)] mb-2">No Connected Accounts</h3>
                <p className="text-[var(--text-secondary)] mb-6">
                  You need to connect at least one X account before sending DMs.
                </p>
                <ConnectXAccountButton 
                  onSuccess={handleAccountConnected}
                  className="btn-primary-gold"
                />
              </CardContent>
            </Card>
          ) : (
            <SendDMForm accounts={accounts} />
          )}
        </div>
      </div>
    </div>
  );
}
