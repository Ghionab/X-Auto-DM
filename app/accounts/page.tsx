'use client';

import { Twitter, Plus, Settings, BarChart3, AlertCircle, Loader2, ExternalLink, RefreshCw, Shield, Users } from 'lucide-react';
import { useState, useEffect } from 'react';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import ConnectXAccountButton from '@/components/ConnectXAccountButton';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { toast } from '@/hooks/use-toast';
import { api, TwitterAccount } from '@/lib/api';

export default function Accounts() {
  const [accounts, setAccounts] = useState<TwitterAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [disconnectingId, setDisconnectingId] = useState<number | null>(null);
  const [refreshingAccountId, setRefreshingAccountId] = useState<number | null>(null);
  const [accountsInfo, setAccountsInfo] = useState<{[key: number]: any}>({});

  // Load accounts on component mount
  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      setLoading(true);
      const response = await api.getTwitterAccounts();
      if (response.success && response.data?.accounts) {
        setAccounts(response.data.accounts);
        // Load detailed account info for each connected account
        await loadAccountsInfo(response.data.accounts);
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

  const loadAccountsInfo = async (accountsList: TwitterAccount[]) => {
    const connectedAccounts = accountsList.filter(account => account.connection_status === 'connected');
    const accountInfoPromises = connectedAccounts.map(async (account) => {
      try {
        const response = await api.getMyAccountInfo(account.id);
        if (response.success && response.data?.account) {
          return { accountId: account.id, info: response.data.account };
        }
      } catch (error) {
        console.error(`Failed to load info for account ${account.id}:`, error);
      }
      return null;
    });

    const results = await Promise.all(accountInfoPromises);
    const newAccountsInfo: {[key: number]: any} = {};
    
    results.forEach(result => {
      if (result) {
        newAccountsInfo[result.accountId] = result.info;
      }
    });
    
    setAccountsInfo(newAccountsInfo);
  };

  const handleAuthSuccess = async () => {
    // Reload accounts after successful connection
    await loadAccounts();
  };

  const handleRefreshAccountInfo = async (accountId: number) => {
    try {
      setRefreshingAccountId(accountId);
      const response = await api.getMyAccountInfo(accountId);
      
      if (response.success && response.data?.account) {
        setAccountsInfo(prev => ({
          ...prev,
          [accountId]: response.data!.account
        }));
        
        toast({
          title: "Success",
          description: "Account information refreshed",
        });
      } else {
        toast({
          title: "Error",
          description: response.error || "Failed to refresh account info",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to refresh account information",
        variant: "destructive",
      });
    } finally {
      setRefreshingAccountId(null);
    }
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
              {accounts.map((account) => {
                const accountInfo = accountsInfo[account.id];
                
                return (
                  <Card key={account.id} className="border-0 shadow-lg">
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center space-x-4">
                          <div className="w-16 h-16 bg-gradient-to-br from-blue-600 to-purple-600 rounded-full flex items-center justify-center text-white text-xl font-bold">
                            {(accountInfo?.profile_picture_url || account.profile_image_url) ? (
                              <img 
                                src={accountInfo?.profile_picture_url || account.profile_image_url} 
                                alt={accountInfo?.display_name || account.display_name}
                                className="w-16 h-16 rounded-full object-cover"
                              />
                            ) : (
                              (accountInfo?.display_name || account.display_name)?.charAt(0)?.toUpperCase() || 
                              account.username?.charAt(0)?.toUpperCase() || 'X'
                            )}
                          </div>
                          <div>
                            <div className="flex items-center space-x-2">
                              <h3 className="font-bold text-lg text-gray-900">
                                {accountInfo?.display_name || account.display_name || account.username}
                              </h3>
                              {(accountInfo?.verified || accountInfo?.is_blue_verified || account.is_verified) && (
                                <Shield className="w-5 h-5 text-blue-500" />
                              )}
                              {getConnectionStatusBadge(account.connection_status)}
                            </div>
                            <p className="text-gray-600">@{accountInfo?.username || account.username}</p>
                            
                            {/* Enhanced account details */}
                            <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
                              <div className="flex items-center space-x-1">
                                <Users className="w-4 h-4" />
                                <span>{formatNumber(accountInfo?.follower_count || account.followers_count)} followers</span>
                              </div>
                              <span>{formatNumber(accountInfo?.following_count || account.following_count)} following</span>
                            </div>
                            
                            {/* Account status indicators */}
                            <div className="flex items-center space-x-2 mt-2">
                              <Badge variant="secondary" className="text-xs bg-green-100 text-green-700">
                                DM Enabled
                              </Badge>
                              {accountInfo?.verified_type && (
                                <Badge variant="secondary" className="text-xs bg-blue-100 text-blue-700">
                                  {accountInfo.verified_type}
                                </Badge>
                              )}
                              <Badge variant="outline" className="text-xs">
                                Warmup: {account.warmup_status}
                              </Badge>
                            </div>
                            
                            {/* Account description */}
                            {accountInfo?.description && (
                              <p className="text-sm text-gray-600 mt-2 line-clamp-2 max-w-md">
                                {accountInfo.description}
                              </p>
                            )}
                          </div>
                        </div>
                        
                        <div className="flex items-center space-x-2">
                          {account.connection_status === 'connected' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleRefreshAccountInfo(account.id)}
                              disabled={refreshingAccountId === account.id}
                              title="Refresh account information"
                            >
                              {refreshingAccountId === account.id ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <RefreshCw className="w-4 h-4" />
                              )}
                            </Button>
                          )}
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
                          <div className="text-sm text-gray-600">Account Connected</div>
                          <div className="text-sm font-medium text-gray-900">
                            {accountInfo?.connected_at ? 
                              new Date(accountInfo.connected_at).toLocaleDateString() : 
                              'Unknown'
                            }
                          </div>
                          <div className="text-xs text-gray-500">
                            {accountInfo?.location || 'No location'}
                          </div>
                        </div>
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <div className="text-sm text-gray-600">Verification</div>
                          <div className="text-lg font-bold text-blue-600">
                            {accountInfo?.is_blue_verified ? 'Blue Verified' : 
                             accountInfo?.verified ? 'Verified' : 'Not Verified'}
                          </div>
                          <div className="text-xs text-gray-500">
                            {accountInfo?.verified_type || 'Standard account'}
                          </div>
                        </div>
                        <div className="bg-gray-50 p-4 rounded-lg flex items-center justify-between">
                          <div>
                            <div className="text-sm text-gray-600">Account Status</div>
                            <div className="text-sm font-medium text-gray-900">
                              {accountInfo?.connection_status === 'connected' ? 'Active' : 'Inactive'}
                            </div>
                            <div className="text-xs text-gray-500">
                              {accountInfo?.last_updated ? 
                                `Updated ${new Date(accountInfo.last_updated).toLocaleDateString()}` :
                                'Status unknown'
                              }
                            </div>
                          </div>
                          <Button variant="ghost" size="sm" className="p-0 h-auto">
                            <Settings className="w-4 h-4 mr-1" />
                            Configure
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
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
          <Card className="border-0 shadow-lg border-dashed border-2 border-gray-200 hover:border-blue-300 transition-colors">
            <CardContent className="p-8 text-center">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-100 to-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Plus className="w-8 h-8 text-blue-600" />
              </div>
              <h3 className="font-bold text-lg text-gray-900 mb-2">Connect New Account</h3>
              <p className="text-gray-600 mb-4 max-w-md mx-auto">
                Add another X account using your credentials
              </p>
              <ConnectXAccountButton 
                className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                onSuccess={handleAuthSuccess}
                size="lg"
              />
            </CardContent>
          </Card>

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
