'use client';

import { useState } from 'react';
import { Play, Pause, Edit, Trash2, Plus, Users, MessageSquare, TrendingUp, Calendar } from 'lucide-react';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState([
    {
      id: 1,
      name: 'Tech Founders Outreach',
      status: 'active',
      targetCount: 450,
      sent: 287,
      replies: 126,
      replyRate: '43.9%',
      account: '@your_account',
      createdAt: '2025-01-15',
      template: 'Hi {name}, I noticed you\'re building something amazing in the tech space...'
    },
    {
      id: 2,
      name: 'Marketing Directors',
      status: 'paused',
      targetCount: 320,
      sent: 198,
      replies: 89,
      replyRate: '44.9%',
      account: '@business_acc',
      createdAt: '2025-01-12',
      template: 'Hey {name}, loved your recent post about marketing automation...'
    },
    {
      id: 3,
      name: 'Startup CEOs',
      status: 'completed',
      targetCount: 280,
      sent: 280,
      replies: 112,
      replyRate: '40.0%',
      account: '@personal_brand',
      createdAt: '2025-01-08',
      template: 'Hi {name}, saw your company\'s recent milestone announcement...'
    }
  ]);

  const [newCampaign, setNewCampaign] = useState({
    name: '',
    account: '',
    template: '',
    targetList: '',
    dailyLimit: '50'
  });

  const toggleCampaignStatus = (id: number) => {
    setCampaigns(campaigns.map(campaign => 
      campaign.id === id 
        ? { ...campaign, status: campaign.status === 'active' ? 'paused' : 'active' }
        : campaign
    ));
  };

  const deleteCampaign = (id: number) => {
    setCampaigns(campaigns.filter(campaign => campaign.id !== id));
  };

  const createCampaign = () => {
    if (!newCampaign.name || !newCampaign.template) return;
    
    const campaign = {
      id: campaigns.length + 1,
      name: newCampaign.name,
      status: 'active' as const,
      targetCount: 0,
      sent: 0,
      replies: 0,
      replyRate: '0%',
      account: newCampaign.account || '@your_account',
      createdAt: new Date().toISOString().split('T')[0],
      template: newCampaign.template
    };
    
    setCampaigns([campaign, ...campaigns]);
    setNewCampaign({ name: '', account: '', template: '', targetList: '', dailyLimit: '50' });
  };

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      
      <div className="flex-1 lg:ml-64">
        <Header 
          title="Campaigns" 
          subtitle="Manage your DM campaigns and track their performance"
        />
        
        <div className="p-6">
          <Tabs defaultValue="active" className="space-y-6">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="active">Active Campaigns</TabsTrigger>
              <TabsTrigger value="create">Create Campaign</TabsTrigger>
            </TabsList>

            <TabsContent value="active" className="space-y-6">
              {/* Campaign Stats */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <Card className="border-0 shadow-lg">
                  <CardContent className="p-6">
                    <div className="flex items-center space-x-3">
                      <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                        <Play className="w-6 h-6 text-blue-600" />
                      </div>
                      <div>
                        <div className="text-2xl font-bold">{campaigns.filter(c => c.status === 'active').length}</div>
                        <div className="text-sm text-gray-600">Active Campaigns</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-0 shadow-lg">
                  <CardContent className="p-6">
                    <div className="flex items-center space-x-3">
                      <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                        <MessageSquare className="w-6 h-6 text-green-600" />
                      </div>
                      <div>
                        <div className="text-2xl font-bold">{campaigns.reduce((sum, c) => sum + c.sent, 0)}</div>
                        <div className="text-sm text-gray-600">Total DMs Sent</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-0 shadow-lg">
                  <CardContent className="p-6">
                    <div className="flex items-center space-x-3">
                      <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                        <TrendingUp className="w-6 h-6 text-purple-600" />
                      </div>
                      <div>
                        <div className="text-2xl font-bold">42.9%</div>
                        <div className="text-sm text-gray-600">Avg Reply Rate</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-0 shadow-lg">
                  <CardContent className="p-6">
                    <div className="flex items-center space-x-3">
                      <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                        <Users className="w-6 h-6 text-orange-600" />
                      </div>
                      <div>
                        <div className="text-2xl font-bold">{campaigns.reduce((sum, c) => sum + c.replies, 0)}</div>
                        <div className="text-sm text-gray-600">Total Replies</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Campaigns List */}
              <div className="space-y-4">
                {campaigns.map((campaign) => (
                  <Card key={campaign.id} className="border-0 shadow-lg">
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            <h3 className="text-lg font-bold text-gray-900">{campaign.name}</h3>
                            <Badge variant={
                              campaign.status === 'active' ? 'default' : 
                              campaign.status === 'paused' ? 'secondary' : 
                              'outline'
                            }>
                              {campaign.status}
                            </Badge>
                          </div>
                          <div className="flex items-center space-x-4 text-sm text-gray-600 mb-3">
                            <span>Account: {campaign.account}</span>
                            <span>Created: {campaign.createdAt}</span>
                          </div>
                          <div className="text-sm text-gray-700 bg-gray-50 p-3 rounded-lg">
                            <strong>Template:</strong> {campaign.template}
                          </div>
                        </div>
                        
                        <div className="flex items-center space-x-2 ml-4">
                          <Switch 
                            checked={campaign.status === 'active'}
                            onCheckedChange={() => toggleCampaignStatus(campaign.id)}
                            disabled={campaign.status === 'completed'}
                          />
                          <Button variant="ghost" size="sm">
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            onClick={() => deleteCampaign(campaign.id)}
                            className="text-red-600 hover:text-red-700"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <div className="text-sm text-gray-600">Target Count</div>
                          <div className="text-xl font-bold text-gray-900">{campaign.targetCount}</div>
                        </div>
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <div className="text-sm text-gray-600">DMs Sent</div>
                          <div className="text-xl font-bold text-blue-600">{campaign.sent}</div>
                        </div>
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <div className="text-sm text-gray-600">Replies</div>
                          <div className="text-xl font-bold text-green-600">{campaign.replies}</div>
                        </div>
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <div className="text-sm text-gray-600">Reply Rate</div>
                          <div className="text-xl font-bold text-purple-600">{campaign.replyRate}</div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="create">
              <Card className="border-0 shadow-lg">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Plus className="w-5 h-5 text-blue-600" />
                    <span>Create New Campaign</span>
                  </CardTitle>
                  <CardDescription>
                    Set up a new DM campaign with personalized messaging
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <Label htmlFor="campaign-name">Campaign Name</Label>
                      <Input
                        id="campaign-name"
                        placeholder="e.g., Tech Founders Q1 2025"
                        value={newCampaign.name}
                        onChange={(e) => setNewCampaign({...newCampaign, name: e.target.value})}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="account-select">X Account</Label>
                      <Select value={newCampaign.account} onValueChange={(value) => setNewCampaign({...newCampaign, account: value})}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select account" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="@your_account">@your_account</SelectItem>
                          <SelectItem value="@business_acc">@business_acc</SelectItem>
                          <SelectItem value="@personal_brand">@personal_brand</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="dm-template">DM Template</Label>
                    <Textarea
                      id="dm-template"
                      placeholder="Hi {name}, I noticed you're working on..."
                      rows={4}
                      value={newCampaign.template}
                      onChange={(e) => setNewCampaign({...newCampaign, template: e.target.value})}
                    />
                    <div className="text-sm text-gray-500">
                      Use {'{name}'} for personalization. {newCampaign.template.length}/280 characters
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <Label htmlFor="target-list">Target List</Label>
                      <Textarea
                        id="target-list"
                        placeholder="@user1, @user2, @user3..."
                        rows={3}
                        value={newCampaign.targetList}
                        onChange={(e) => setNewCampaign({...newCampaign, targetList: e.target.value})}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="daily-limit">Daily DM Limit</Label>
                      <Select value={newCampaign.dailyLimit} onValueChange={(value) => setNewCampaign({...newCampaign, dailyLimit: value})}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="25">25 DMs/day</SelectItem>
                          <SelectItem value="50">50 DMs/day</SelectItem>
                          <SelectItem value="75">75 DMs/day</SelectItem>
                          <SelectItem value="100">100 DMs/day</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="flex justify-end space-x-4">
                    <Button variant="outline">Save as Draft</Button>
                    <Button 
                      onClick={createCampaign}
                      disabled={!newCampaign.name || !newCampaign.template}
                      className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                    >
                      Launch Campaign
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