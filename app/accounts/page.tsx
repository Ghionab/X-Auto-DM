'use client';

import { Twitter, Plus, Settings, BarChart3, AlertCircle, Loader2, ExternalLink } from 'lucide-react';
import { useState, useEffect } from 'react';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { toast } from '@/hooks/use-toast';
import { api, TwitterAccount } from '@/lib/api';
import XLoginForm from '@/components/XLoginForm';

export default function Accounts() {
  const [accounts, setAccounts] = useState<TwitterAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [connectingOAuth, setConnectingOAuth] = useState(false);
  const [disconnectingId, setDisconnectingId] = useState<number | null>(null);
  const [showLoginForm, setShowLoginForm] = useState(false);

  // Load accounts on component mount
  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      setLoading(true);
      const response = await api.getXOAuthStatus();
      if (response.success && response.data) {
        setAccounts(response.data.connected_accounts);
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

  const handleConnectAccount = () => {
    setShowLoginForm(true);
  };

  const handleLoginSuccess = async () => {
    setShowLoginForm(false);
    await loadAccounts();
    toast({
      title: "Success",
      description: "X account connected successfully!",
    });
  };

  const handleLoginCancel = () => {
    setShowLoginForm(false);
  };

  const handleDisconnectAccount = async (accountId: number) => {
    try {
      setDisconnectingId(accountId);
      
      const response = await api.disconnectXAccount(accountId);
      
      if (response.success) {
        toast({
          title: "Success",
          description: "Account disconnected successfully",
        });
        // Reload accounts
        await loadAccounts();
      } else {
        toast({
          title: "Error",
          description: response.error || "Failed to disconnect account",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to disconnect account",
        variant: "destructive",
      });
    } finally {
      setDisconnectingId(null);
    }
  };

  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  };

  const getConnectionStatusBadge = (status: string) => {
    switch (status) {
      case 'connected':
        return <Badge className="bg-green-100 text-green-700">Connected</Badge>;
      case 'pending':
        return <Badge variant="secondary">Pending</Badge>;
      case 'expired':
        return <Badge className="bg-yellow-100 text-yellow-700">Expired</Badge>;
      case 'revoked':
        return <Badge className="bg-red-100 text-red-700">Disconnected</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      
      <div className="flex-1 lg:ml-64">
        <Header 
          title="My Accounts" 
          subtitle="Manage your connected X (Twitter) accounts and their settings"
        />
        
        <div className="p-6 space-y-6">
          {/* Account Overview */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="border-0 shadow-lg">
              <CardContent className="p-6">
                <div className="flex items-center space-x-3">
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <Twitter className="w-6 h-6 text-blue-600" />
                  </div>
                  <div>
                    <div className="text-2xl font-bold">{loading ? '-' : accounts.length}</div>
                    <div className="text-sm text-gray-600">Connected Accounts</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-0 shadow-lg">
              <CardContent className="p-6">
                <div className="flex items-center space-x-3">
                  <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                    <BarChart3 className="w-6 h-6 text-green-600" />
                  </div>
                  <div>
                    <div className="text-2xl font-bold">-</div>
                    <div className="text-sm text-gray-600">Avg Reply Rate</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-0 shadow-lg">
              <CardContent className="p-6">
                <div className="flex items-center space-x-3">
                  <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                    <Settings className="w-6 h-6 text-purple-600" />
                  </div>
                  <div>
                    <div className="text-2xl font-bold">-</div>
                    <div className="text-sm text-gray-600">Active Campaigns</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Connected Accounts */}
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
              <span className="ml-2 text-gray-600">Loading accounts...</span>
            </div>
          ) : accounts.length > 0 ? (
            <div className="space-y-4">
              {accounts.map((account) => (
                <Card key={account.id} className="border-0 shadow-lg">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center space-x-4">
                        <div className="w-16 h-16 bg-gradient-to-br from-blue-600 to-purple-600 rounded-full flex items-center justify-center text-white text-xl font-bold">
                          {account.profile_image_url ? (
                            <img 
                              src={account.profile_image_url} 
                              alt={account.display_name}
                              className="w-16 h-16 rounded-full object-cover"
                            />
                          ) : (
                            account.display_name?.charAt(0)?.toUpperCase() || account.username?.charAt(1)?.toUpperCase() || 'X'
                          )}
                        </div>
                        <div>
                          <div className="flex items-center space-x-2">
                            <h3 className="font-bold text-lg text-gray-900">{account.display_name || account.username}</h3>
                            {account.is_verified && (
                              <Badge className="bg-blue-100 text-blue-700">Verified</Badge>
                            )}
                            {getConnectionStatusBadge(account.connection_status)}
                          </div>
                          <p className="text-gray-600">@{account.username}</p>
                          <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
                            <span>{formatNumber(account.followers_count)} followers</span>
                            <span>{formatNumber(account.following_count)} following</span>
                            <span>Warmup: {account.warmup_status}</span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-4">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDisconnectAccount(account.id)}
                          disabled={disconnectingId === account.id}
                        >
                          {disconnectingId === account.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            'Disconnect'
                          )}
                        </Button>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <div className="text-sm text-gray-600">DMs Sent</div>
                        <div className="text-2xl font-bold text-gray-900">-</div>
                        <div className="text-xs text-gray-500">Coming soon</div>
                      </div>
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <div className="text-sm text-gray-600">Reply Rate</div>
                        <div className="text-2xl font-bold text-green-600">-</div>
                        <div className="text-xs text-gray-500">Coming soon</div>
                      </div>
                      <div className="bg-gray-50 p-4 rounded-lg flex items-center justify-between">
                        <div>
                          <div className="text-sm text-gray-600">Settings</div>
                          <Button variant="ghost" size="sm" className="p-0 h-auto mt-1">
                            <Settings className="w-4 h-4 mr-1" />
                            Configure
                          </Button>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="border-0 shadow-lg">
              <CardContent className="p-8 text-center">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Twitter className="w-8 h-8 text-gray-400" />
                </div>
                <h3 className="font-bold text-lg text-gray-900 mb-2">No Connected Accounts</h3>
                <p className="text-gray-600 mb-4">
                  Connect your first X account to start creating DM campaigns
                </p>
              </CardContent>
            </Card>
          )}

          {/* Add New Account */}
          {showLoginForm ? (
            <XLoginForm 
              onSuccess={handleLoginSuccess}
              onCancel={handleLoginCancel}
            />
          ) : (
            <Card className="border-0 shadow-lg border-dashed border-2 border-gray-200 hover:border-blue-300 transition-colors">
              <CardContent className="p-8 text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-blue-100 to-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Plus className="w-8 h-8 text-blue-600" />
                </div>
                <h3 className="font-bold text-lg text-gray-900 mb-2">Connect New Account</h3>
                <p className="text-gray-600 mb-4 max-w-md mx-auto">
                  Add another X account to scale your outreach campaigns and reach more prospects
                </p>
                <Button 
                  className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                  onClick={handleConnectAccount}
                >
                  <Twitter className="w-4 h-4 mr-2" />
                  Connect X Account
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Account Guidelines */}
          <Card className="border-0 shadow-lg bg-amber-50 border-amber-200">
            <CardContent className="p-6">
              <div className="flex items-start space-x-3">
                <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-medium text-amber-800 mb-2">Account Safety Guidelines</h4>
                  <ul className="text-sm text-amber-700 space-y-1">
                    <li>• Keep daily DM limits reasonable (50-100 per day recommended)</li>
                    <li>• Use different message templates across accounts</li>
                    <li>• Monitor reply rates and adjust targeting accordingly</li>
                    <li>• Take breaks between campaigns to avoid detection</li>
                    <li>• Always personalize messages for better engagement</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}