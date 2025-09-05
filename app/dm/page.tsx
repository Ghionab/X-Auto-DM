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
    <div className="flex min-h-screen bg-gray-50">
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
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-2 text-gray-600">Loading accounts...</p>
              </div>
            </div>
          ) : connectedAccounts.length === 0 ? (
            <Card className="border-0 shadow-lg">
              <CardContent className="p-8 text-center">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <MessageCircle className="w-8 h-8 text-gray-400" />
                </div>
                <h3 className="font-bold text-lg text-gray-900 mb-2">No Connected Accounts</h3>
                <p className="text-gray-600 mb-6">
                  You need to connect at least one X account before sending DMs.
                </p>
                <ConnectXAccountButton 
                  onSuccess={handleAccountConnected}
                  className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
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
