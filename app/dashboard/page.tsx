'use client';

import { MessageSquare, Users, TrendingUp, Twitter, Send, Reply, Loader2, Plus } from 'lucide-react';
import { useEffect, useState } from 'react';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import AnalyticsCard from '@/components/AnalyticsCard';
import UserListForm from '@/components/UserListForm';
import EmptyState from '@/components/EmptyState';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { api, TwitterAccount, Campaign } from '@/lib/api';

export default function Dashboard() {
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [twitterAccounts, setTwitterAccounts] = useState<TwitterAccount[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // Fetch dashboard analytics using the new endpoint
        const analyticsResponse = await api.getDashboardAnalytics();
        if (analyticsResponse.success) {
          setDashboardData(analyticsResponse.data);
        } else {
          // Set empty state data if API fails
          setDashboardData({
            overview: {
              total_campaigns: 0,
              active_campaigns: 0,
              total_messages_sent: 0,
              total_replies_received: 0,
              overall_reply_rate: 0
            },
            recent_campaigns: [],
            chart_data: {
              campaign_performance: []
            }
          });
        }

        // Fetch Twitter accounts
        const accountsResponse = await api.getTwitterAccounts();
        if (accountsResponse.success) {
          setTwitterAccounts(accountsResponse.data?.accounts || []);
        }

        // Fetch campaigns
        const campaignsResponse = await api.getCampaigns();
        if (campaignsResponse.success) {
          setCampaigns(campaignsResponse.data?.campaigns || []);
        }
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
        // Set empty state data on error
        setDashboardData({
          overview: {
            total_campaigns: 0,
            active_campaigns: 0,
            total_messages_sent: 0,
            total_replies_received: 0,
            overall_reply_rate: 0
          },
          recent_campaigns: [],
          chart_data: {
            campaign_performance: []
          }
        });
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen bg-[var(--bg-page)]">
        <Sidebar />
        <div className="flex-1 lg:ml-64">
          <Header 
            title="Dashboard" 
            subtitle="Monitor your DM campaigns and performance metrics"
          />
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <Loader2 className="w-8 h-8 mx-auto mb-4 animate-spin text-[var(--accent-gold-primary)]" />
              <p className="text-[var(--text-secondary)]">Loading dashboard data...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const overview = dashboardData?.overview || {};

  return (
    <div className="flex min-h-screen bg-[var(--bg-page)]">
      <Sidebar />
      
      <div className="flex-1 lg:ml-64">
        <Header 
          title="Dashboard" 
          subtitle="Monitor your DM campaigns and performance metrics"
        />
        
        <div className="p-6 space-y-6">
          {/* Quick Stats */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <AnalyticsCard
              title="Total DMs Sent"
              value={overview.total_messages_sent?.toLocaleString() || '0'}
              icon={<Send className="w-5 h-5" />}
              description="Messages sent across all campaigns"
            />
            <AnalyticsCard
              title="Reply Rate"
              value={overview.overall_reply_rate ? `${overview.overall_reply_rate.toFixed(1)}%` : '0%'}
              icon={<Reply className="w-5 h-5" />}
              description={overview.total_replies_received ? `${overview.total_replies_received} total replies` : 'No replies yet'}
            />
            <AnalyticsCard
              title="Active Campaigns"
              value={overview.active_campaigns?.toString() || '0'}
              icon={<TrendingUp className="w-5 h-5" />}
              description={`${overview.total_campaigns || 0} total campaigns`}
            />
            <AnalyticsCard
              title="Connected Accounts"
              value={twitterAccounts.length.toString()}
              icon={<Twitter className="w-5 h-5" />}
              description={`${twitterAccounts.filter(acc => acc.is_active).length} active accounts`}
            />
          </div>

          {/* Main Content Tabs */}
          <Tabs defaultValue="overview" className="space-y-6">
            <TabsList className="grid w-full grid-cols-3 bg-[var(--bg-card)] border border-[var(--border-subtle)]">
              <TabsTrigger 
                value="overview"
                className="data-[state=active]:bg-[var(--bg-page)] data-[state=active]:text-[var(--accent-gold-secondary)] data-[state=active]:border-b-2 data-[state=active]:border-[var(--accent-gold-secondary)] text-[var(--text-secondary)]"
              >
                Overview
              </TabsTrigger>
              <TabsTrigger 
                value="campaigns"
                className="data-[state=active]:bg-[var(--bg-page)] data-[state=active]:text-[var(--accent-gold-secondary)] data-[state=active]:border-b-2 data-[state=active]:border-[var(--accent-gold-secondary)] text-[var(--text-secondary)]"
              >
                New Campaign
              </TabsTrigger>
              <TabsTrigger 
                value="accounts"
                className="data-[state=active]:bg-[var(--bg-page)] data-[state=active]:text-[var(--accent-gold-secondary)] data-[state=active]:border-b-2 data-[state=active]:border-[var(--accent-gold-secondary)] text-[var(--text-secondary)]"
              >
                Accounts
              </TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-6">
              {/* Recent Activity */}
              <Card className="bg-[var(--bg-card)] border border-[var(--border-subtle)]">
                <CardHeader>
                  <CardTitle className="text-[var(--text-primary)]">Recent Activity</CardTitle>
                  <CardDescription className="text-[var(--text-secondary)]">Latest DM campaign results and interactions</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {campaigns.length > 0 ? (
                      campaigns.slice(0, 5).map((campaign, index) => {
                        const replyRate = campaign.messages_sent > 0 ? 
                          ((campaign.replies_received / campaign.messages_sent) * 100).toFixed(1) : '0';
                        const status = campaign.status;
                        
                        return (
                          <div key={campaign.id} className="flex items-center justify-between p-3 bg-[var(--bg-page)] rounded-lg border border-[var(--border-subtle)]">
                            <div className="flex items-center space-x-3">
                              <div className="w-8 h-8 bg-[var(--accent-gold-primary)] rounded-full flex items-center justify-center text-[var(--text-inverted)] text-sm font-medium">
                                {campaign.name.charAt(0).toUpperCase()}
                              </div>
                              <div>
                                <div className="font-medium text-[var(--text-primary)]">{campaign.name}</div>
                                <div className="text-sm text-[var(--text-secondary)]">
                                  {campaign.messages_sent} sent • {campaign.replies_received} replies
                                </div>
                              </div>
                            </div>
                            <div className="text-right">
                              <Badge className={
                                status === 'active' ? 'badge-pill-green' : 
                                status === 'paused' ? 'badge-pill-gold' : 
                                'bg-[var(--border-subtle)] text-[var(--text-secondary)]'
                              }>
                                {status}
                              </Badge>
                              <div className="text-xs text-[var(--text-secondary)] mt-1">{replyRate}% reply rate</div>
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <EmptyState
                        icon={MessageSquare}
                        title="No campaigns yet"
                        description="Create your first campaign to see activity and performance metrics here."
                        action={{
                          label: "Create Campaign",
                          onClick: () => {
                            // Switch to campaigns tab
                            const campaignTab = document.querySelector('[value="campaigns"]') as HTMLElement;
                            campaignTab?.click();
                          }
                        }}
                      />
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Performance Chart Placeholder */}
              <Card className="bg-[var(--bg-card)] border border-[var(--border-subtle)]">
                <CardHeader>
                  <CardTitle className="text-[var(--text-primary)]">Performance Trends</CardTitle>
                  <CardDescription className="text-[var(--text-secondary)]">DM performance over the last 30 days</CardDescription>
                </CardHeader>
                <CardContent>
                  {dashboardData?.chart_data?.campaign_performance?.length > 0 ? (
                    <div className="h-64 bg-[var(--bg-page)] rounded-lg flex items-center justify-center border border-[var(--border-subtle)]">
                      <div className="text-center text-[var(--text-secondary)]">
                        <TrendingUp className="w-12 h-12 mx-auto mb-2 opacity-50" />
                        <p>Performance chart will be displayed here</p>
                      </div>
                    </div>
                  ) : (
                    <EmptyState
                      icon={TrendingUp}
                      title="No performance data yet"
                      description="Start running campaigns to see performance trends and analytics charts."
                    />
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="campaigns">
              <UserListForm />
            </TabsContent>

            <TabsContent value="accounts">
              <Card className="bg-[var(--bg-card)] border border-[var(--border-subtle)]">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2 text-[var(--text-primary)]">
                    <Twitter className="w-5 h-5 text-[var(--accent-gold-secondary)]" />
                    <span>Connected X Accounts</span>
                  </CardTitle>
                  <CardDescription className="text-[var(--text-secondary)]">
                    Manage your connected Twitter/X accounts for DM campaigns
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Connected Accounts */}
                  <div className="space-y-3">
                    {twitterAccounts.length > 0 ? (
                      twitterAccounts.map((account) => (
                        <div key={account.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                          <div className="flex items-center space-x-3">
                            <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-purple-600 rounded-full flex items-center justify-center text-white font-medium">
                              {account.display_name ? account.display_name.charAt(0).toUpperCase() : account.username.charAt(0).toUpperCase()}
                            </div>
                            <div>
                              <div className="font-medium flex items-center space-x-2">
                                <span>@{account.username}</span>
                                {account.is_verified && (
                                  <div className="w-4 h-4 bg-blue-500 rounded-full flex items-center justify-center">
                                    <div className="w-2 h-2 bg-white rounded-full" />
                                  </div>
                                )}
                              </div>
                              <div className="text-sm text-gray-600">
                                {account.followers_count?.toLocaleString() || '0'} followers
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center space-x-3">
                            <Badge variant={account.is_active ? 'default' : 'secondary'}>
                              {account.is_active ? 'active' : 'inactive'}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              {account.warmup_status || 'not started'}
                            </Badge>
                            <Button variant="outline" size="sm">
                              Manage
                            </Button>
                          </div>
                        </div>
                      ))
                    ) : (
                      <EmptyState
                        icon={Twitter}
                        title="No accounts connected"
                        description="Connect your Twitter/X accounts to start creating DM campaigns."
                      />
                    )}
                  </div>

                  {/* Connect New Account */}
                  <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 text-center">
                    <Twitter className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                    <h3 className="font-medium text-gray-900 mb-2">Connect Another Account</h3>
                    <p className="text-gray-600 text-sm mb-4">
                      Add more X accounts to scale your outreach campaigns
                    </p>
                    <Button className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700">
                      Connect X Account
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}