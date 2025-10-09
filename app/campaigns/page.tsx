'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Play, Pause, Edit, Trash2, Plus, Users, MessageSquare, TrendingUp, Calendar, Upload, FileText, AlertCircle, CheckCircle, Loader2, X, Eye, Send, BarChart3, PieChart } from 'lucide-react';
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
import { Checkbox } from '@/components/ui/checkbox';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { api, Campaign, TwitterAccount, withCampaignToast, withFileUploadToast } from '@/lib/api';
import CampaignMonitor from '@/components/CampaignMonitor';
import CampaignAnalyticsDashboard from '@/components/CampaignAnalyticsDashboard';
import CampaignComparison from '@/components/CampaignComparison';
import FollowerPreview from '@/components/FollowerPreview';

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [twitterAccounts, setTwitterAccounts] = useState<TwitterAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [campaignProgress, setCampaignProgress] = useState<{[key: number]: number}>({});
  
  const [newCampaign, setNewCampaign] = useState({
    name: '',
    description: '',
    target_type: 'user_followers' as 'user_followers' | 'list_members' | 'csv_upload',
    target_identifier: '',
    verified_only: false,
    message_template: '',
    sender_account_id: 0,
    daily_limit: 50
  });

  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvUploading, setCsvUploading] = useState(false);
  const [scrapingProgress, setScrapingProgress] = useState<{[key: number]: {progress: number, status: string}}>({});
  
  // New state for enhanced functionality
  const [isDragOver, setIsDragOver] = useState(false);
  const [validationErrors, setValidationErrors] = useState<{[key: string]: string}>({});
  const [showPreview, setShowPreview] = useState(false);
  const [previewMessage, setPreviewMessage] = useState('');
  const [showLaunchConfirm, setShowLaunchConfirm] = useState(false);
  const [campaignToLaunch, setCampaignToLaunch] = useState<Campaign | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);
  const [showMonitor, setShowMonitor] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [analyticsCampaign, setAnalyticsCampaign] = useState<Campaign | null>(null);
  const [showComparison, setShowComparison] = useState(false);
  const [showFollowerPreview, setShowFollowerPreview] = useState(false);
  const [previewUsername, setPreviewUsername] = useState('');
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load campaigns and accounts on component mount
  useEffect(() => {
    loadCampaigns();
    loadTwitterAccounts();
  }, []);

  // Validation functions
  const validateUsername = (username: string): string | null => {
    if (!username.trim()) return 'Username is required';
    if (username.includes('@')) return 'Enter username without @ symbol';
    if (username.length < 1 || username.length > 15) return 'Username must be 1-15 characters';
    if (!/^[a-zA-Z0-9_]+$/.test(username)) return 'Username can only contain letters, numbers, and underscores';
    return null;
  };

  const validateListId = (listId: string): string | null => {
    if (!listId.trim()) return 'List ID is required';
    if (!/^\d+$/.test(listId)) return 'List ID must be numeric';
    return null;
  };

  const validateTemplate = (template: string): string | null => {
    if (!template.trim()) return 'Message template is required';
    if (template.length > 280) return 'Message template must be 280 characters or less';
    if (template.length < 10) return 'Message template should be at least 10 characters';
    return null;
  };

  const validateForm = (): boolean => {
    const errors: {[key: string]: string} = {};

    // Basic validation
    if (!newCampaign.name.trim()) errors.name = 'Campaign name is required';
    if (!newCampaign.sender_account_id) errors.sender_account_id = 'Please select an X account';
    
    // Template validation
    const templateError = validateTemplate(newCampaign.message_template);
    if (templateError) errors.message_template = templateError;

    // Target-specific validation
    if (newCampaign.target_type === 'user_followers') {
      const usernameError = validateUsername(newCampaign.target_identifier);
      if (usernameError) errors.target_identifier = usernameError;
    } else if (newCampaign.target_type === 'list_members') {
      const listIdError = validateListId(newCampaign.target_identifier);
      if (listIdError) errors.target_identifier = listIdError;
    } else if (newCampaign.target_type === 'csv_upload') {
      if (!csvFile) errors.csv_file = 'Please select a CSV file';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Drag and drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    const csvFile = files.find(file => file.type === 'text/csv' || file.name.endsWith('.csv'));
    
    if (csvFile) {
      setCsvFile(csvFile);
      setValidationErrors(prev => ({ ...prev, csv_file: '' }));
    } else {
      setValidationErrors(prev => ({ ...prev, csv_file: 'Please drop a valid CSV file' }));
    }
  }, []);

  // Template preview functionality
  const generatePreview = () => {
    let preview = newCampaign.message_template;
    
    // Replace personalization variables with sample data
    preview = preview.replace(/{name}/g, 'John Doe');
    preview = preview.replace(/{username}/g, 'johndoe');
    preview = preview.replace(/{display_name}/g, 'John Doe');
    
    setPreviewMessage(preview);
    setShowPreview(true);
  };

  const loadCampaigns = async () => {
    try {
      setLoading(true);
      const response = await api.getCampaigns();
      if (response.success && response.data) {
        setCampaigns(response.data.campaigns);
      } else {
        setError(response.error || 'Failed to load campaigns');
      }
    } catch (err) {
      setError('Failed to load campaigns');
    } finally {
      setLoading(false);
    }
  };

  const loadTwitterAccounts = async () => {
    try {
      const response = await api.getTwitterAccounts();
      if (response.success && response.data) {
        setTwitterAccounts(response.data.accounts);
      }
    } catch (err) {
      console.error('Failed to load Twitter accounts:', err);
    }
  };

  const toggleCampaignStatus = async (id: number) => {
    const campaign = campaigns.find(c => c.id === id);
    if (!campaign) return;

    try {
      if (campaign.status === 'active') {
        await withCampaignToast(
          api.pauseCampaign(id),
          'Campaign paused successfully',
          'Pause Campaign'
        );
      } else if (campaign.status === 'paused' || campaign.status === 'draft') {
        await withCampaignToast(
          api.startCampaign(id),
          'Campaign started successfully',
          'Start Campaign'
        );
      }
      loadCampaigns(); // Reload to get updated status
    } catch (err) {
      console.error('Failed to toggle campaign status:', err);
    }
  };

  const deleteCampaign = async (id: number) => {
    try {
      await withCampaignToast(
        api.deleteCampaign(id),
        'Campaign deleted successfully',
        'Delete Campaign'
      );
      loadCampaigns(); // Reload campaigns after deletion
    } catch (err) {
      console.error('Failed to delete campaign:', err);
    }
  };

  const createCampaign = async () => {
    if (!validateForm()) {
      setError('Please fix the validation errors before creating the campaign');
      return;
    }
    
    setIsCreating(true);
    setError(null);
    
    try {
      const response = await withCampaignToast(
        api.createCampaign(newCampaign),
        'Campaign created successfully',
        'Create Campaign'
      );
      
      if (response) {
        const campaignId = response.campaign.id;
        
        // Handle CSV upload if file is selected
        if (csvFile && newCampaign.target_type === 'csv_upload') {
          await handleCSVUpload(campaignId);
        }
        
        // Handle follower scraping if target type is user_followers
        if (newCampaign.target_type === 'user_followers' && newCampaign.target_identifier) {
          await handleFollowerScraping(campaignId, newCampaign.target_identifier);
        }
        
        // Handle list member scraping if target type is list_members
        if (newCampaign.target_type === 'list_members' && newCampaign.target_identifier) {
          await handleListMemberScraping(campaignId, newCampaign.target_identifier);
        }
        
        // Reset form
        resetForm();
        
        loadCampaigns(); // Reload campaigns
        
        // Switch to active campaigns tab
        const activeTab = document.querySelector('[value="active"]') as HTMLElement;
        activeTab?.click();
      }
    } catch (err) {
      console.error('Failed to create campaign:', err);
      setError('Failed to create campaign. Please try again.');
    } finally {
      setIsCreating(false);
    }
  };

  const resetForm = () => {
    setNewCampaign({
      name: '',
      description: '',
      target_type: 'user_followers',
      target_identifier: '',
      verified_only: false,
      message_template: '',
      sender_account_id: 0,
      daily_limit: 50
    });
    setCsvFile(null);
    setValidationErrors({});
    setError(null);
  };

  const handleCSVUpload = async (campaignId: number) => {
    if (!csvFile) return;
    
    setCsvUploading(true);
    try {
      await withFileUploadToast(
        api.uploadCSV(campaignId, csvFile),
        `CSV uploaded successfully: ${csvFile.name}`,
        csvFile.name
      );
    } catch (err) {
      console.error('Failed to upload CSV:', err);
    } finally {
      setCsvUploading(false);
    }
  };

  const handleFollowerScraping = async (campaignId: number, username: string) => {
    setScrapingProgress(prev => ({
      ...prev,
      [campaignId]: { progress: 10, status: 'Starting follower scraping...' }
    }));

    try {
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setScrapingProgress(prev => {
          const current = prev[campaignId]?.progress || 10;
          if (current < 90) {
            return {
              ...prev,
              [campaignId]: { 
                progress: current + 10, 
                status: `Scraping followers from @${username}...` 
              }
            };
          }
          return prev;
        });
      }, 500);

      const response = await withCampaignToast(
        api.scrapeFollowers({
          campaign_id: campaignId,
          username: username,
          verified_only: newCampaign.verified_only
        }),
        `Followers scraped successfully from @${username}`,
        'Scrape Followers'
      );

      clearInterval(progressInterval);

      if (response) {
        setScrapingProgress(prev => ({
          ...prev,
          [campaignId]: { 
            progress: 100, 
            status: `Scraped ${response.total_scraped} followers (${response.valid_targets} valid targets)` 
          }
        }));
      }
    } catch (err) {
      console.error('Failed to scrape followers:', err);
      setScrapingProgress(prev => ({
        ...prev,
        [campaignId]: { progress: 0, status: 'Scraping failed' }
      }));
    }
  };

  const handleListMemberScraping = async (campaignId: number, listId: string) => {
    setScrapingProgress(prev => ({
      ...prev,
      [campaignId]: { progress: 10, status: 'Starting list member scraping...' }
    }));

    try {
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setScrapingProgress(prev => {
          const current = prev[campaignId]?.progress || 10;
          if (current < 90) {
            return {
              ...prev,
              [campaignId]: { 
                progress: current + 15, 
                status: `Scraping members from list ${listId}...` 
              }
            };
          }
          return prev;
        });
      }, 300);

      const response = await withCampaignToast(
        api.scrapeListMembers({
          campaign_id: campaignId,
          list_id: listId
        }),
        `List members scraped successfully from list ${listId}`,
        'Scrape List Members'
      );

      clearInterval(progressInterval);

      if (response) {
        setScrapingProgress(prev => ({
          ...prev,
          [campaignId]: { 
            progress: 100, 
            status: `Scraped ${response.total_scraped} list members (${response.valid_targets} valid targets)` 
          }
        }));
      }
    } catch (err) {
      console.error('Failed to scrape list members:', err);
      setScrapingProgress(prev => ({
        ...prev,
        [campaignId]: { progress: 0, status: 'List scraping failed' }
      }));
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (file.type === 'text/csv' || file.name.endsWith('.csv')) {
        if (file.size > 10 * 1024 * 1024) { // 10MB limit
          setValidationErrors(prev => ({ ...prev, csv_file: 'File size must be less than 10MB' }));
          return;
        }
        setCsvFile(file);
        setValidationErrors(prev => ({ ...prev, csv_file: '' }));
      } else {
        setValidationErrors(prev => ({ ...prev, csv_file: 'Please select a valid CSV file' }));
      }
    }
  };

  const removeCsvFile = () => {
    setCsvFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Campaign launch confirmation
  const confirmLaunch = (campaign: Campaign) => {
    setCampaignToLaunch(campaign);
    setShowLaunchConfirm(true);
  };

  const launchCampaign = async () => {
    if (!campaignToLaunch) return;
    
    try {
      await toggleCampaignStatus(campaignToLaunch.id);
      setShowLaunchConfirm(false);
      setCampaignToLaunch(null);
    } catch (err) {
      console.error('Failed to launch campaign:', err);
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'active': return 'default';
      case 'paused': return 'secondary';
      case 'completed': return 'outline';
      case 'failed': return 'destructive';
      default: return 'secondary';
    }
  };

  const calculateReplyRate = (campaign: Campaign) => {
    if (campaign.messages_sent === 0) return '0%';
    return ((campaign.replies_received / campaign.messages_sent) * 100).toFixed(1) + '%';
  };

  const getTotalStats = () => {
    return {
      activeCampaigns: campaigns.filter(c => c.status === 'active').length,
      totalSent: campaigns.reduce((sum, c) => sum + c.messages_sent, 0),
      totalReplies: campaigns.reduce((sum, c) => sum + c.replies_received, 0),
      avgReplyRate: campaigns.length > 0 
        ? (campaigns.reduce((sum, c) => sum + (c.messages_sent > 0 ? (c.replies_received / c.messages_sent) * 100 : 0), 0) / campaigns.length).toFixed(1) + '%'
        : '0%'
    };
  };

  if (loading) {
    return (
      <div className="flex min-h-screen bg-gray-50">
        <Sidebar />
        <div className="flex-1 lg:ml-64">
          <Header title="Campaigns" subtitle="Loading campaigns..." />
          <div className="p-6 flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin" />
          </div>
        </div>
      </div>
    );
  }

  const stats = getTotalStats();

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
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="active">Active Campaigns</TabsTrigger>
              <TabsTrigger value="create">Create Campaign</TabsTrigger>
              <TabsTrigger value="analytics">Analytics</TabsTrigger>
              <TabsTrigger value="comparison">Compare</TabsTrigger>
            </TabsList>

            <TabsContent value="active" className="space-y-6">
              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {/* Campaign Stats */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <Card className="border-0 shadow-lg">
                  <CardContent className="p-6">
                    <div className="flex items-center space-x-3">
                      <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                        <Play className="w-6 h-6 text-blue-600" />
                      </div>
                      <div>
                        <div className="text-2xl font-bold">{stats.activeCampaigns}</div>
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
                        <div className="text-2xl font-bold">{stats.totalSent}</div>
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
                        <div className="text-2xl font-bold">{stats.avgReplyRate}</div>
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
                        <div className="text-2xl font-bold">{stats.totalReplies}</div>
                        <div className="text-sm text-gray-600">Total Replies</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Campaigns List */}
              <div className="space-y-4">
                {campaigns.length === 0 ? (
                  <Card className="border-0 shadow-lg">
                    <CardContent className="p-12 text-center">
                      <MessageSquare className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">No campaigns yet</h3>
                      <p className="text-gray-600 mb-4">Create your first campaign to start sending DMs</p>
                      <Button onClick={() => {
                        const createTab = document.querySelector('[value="create"]') as HTMLElement;
                        createTab?.click();
                      }}>
                        <Plus className="w-4 h-4 mr-2" />
                        Create Campaign
                      </Button>
                    </CardContent>
                  </Card>
                ) : (
                  campaigns.map((campaign) => {
                    const account = twitterAccounts.find(acc => acc.id === campaign.sender_account_id);
                    const progress = campaignProgress[campaign.id];
                    const scrapingInfo = scrapingProgress[campaign.id];
                    
                    return (
                      <Card key={campaign.id} className="border-0 shadow-lg">
                        <CardContent className="p-6">
                          <div className="flex items-start justify-between mb-4">
                            <div className="flex-1">
                              <div className="flex items-center space-x-3 mb-2">
                                <h3 className="text-lg font-bold text-gray-900">{campaign.name}</h3>
                                <Badge variant={getStatusBadgeVariant(campaign.status)}>
                                  {campaign.status}
                                </Badge>
                                {campaign.verified_only && (
                                  <Badge variant="outline" className="text-blue-600 border-blue-600">
                                    Verified Only
                                  </Badge>
                                )}
                              </div>
                              <div className="flex items-center space-x-4 text-sm text-gray-600 mb-3">
                                <span>Account: @{account?.username || 'Unknown'}</span>
                                <span>Created: {new Date(campaign.created_at).toLocaleDateString()}</span>
                                <span>Type: {campaign.target_type.replace('_', ' ')}</span>
                                {campaign.target_identifier && (
                                  <span>Target: {campaign.target_identifier}</span>
                                )}
                              </div>
                              {campaign.description && (
                                <div className="text-sm text-gray-600 mb-3">
                                  {campaign.description}
                                </div>
                              )}
                              <div className="text-sm text-gray-700 bg-gray-50 p-3 rounded-lg mb-3">
                                <strong>Template:</strong> {campaign.message_template}
                              </div>
                              
                              {/* Progress indicators */}
                              {progress && (
                                <div className="mb-3">
                                  <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
                                    <span>Campaign Progress</span>
                                    <span>{progress}%</span>
                                  </div>
                                  <Progress value={progress} className="h-2" />
                                </div>
                              )}
                              
                              {scrapingInfo && (
                                <div className="mb-3">
                                  <div className="flex items-center space-x-2 text-sm">
                                    {scrapingInfo.progress === 100 ? (
                                      <CheckCircle className="w-4 h-4 text-green-600" />
                                    ) : (
                                      <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                                    )}
                                    <span className="text-gray-600">{scrapingInfo.status}</span>
                                  </div>
                                  {scrapingInfo.progress > 0 && scrapingInfo.progress < 100 && (
                                    <Progress value={scrapingInfo.progress} className="h-2 mt-1" />
                                  )}
                                </div>
                              )}
                            </div>
                            
                            <div className="flex items-center space-x-2 ml-4">
                              <Switch 
                                checked={campaign.status === 'active'}
                                onCheckedChange={() => toggleCampaignStatus(campaign.id)}
                                disabled={campaign.status === 'completed' || campaign.status === 'failed'}
                              />
                              <Button 
                                variant="ghost" 
                                size="sm"
                                onClick={() => {
                                  setSelectedCampaign(campaign);
                                  setShowMonitor(true);
                                }}
                                title="Monitor Campaign"
                              >
                                <Eye className="w-4 h-4" />
                              </Button>
                              <Button 
                                variant="ghost" 
                                size="sm"
                                onClick={() => {
                                  setAnalyticsCampaign(campaign);
                                  setShowAnalytics(true);
                                }}
                                title="View Analytics"
                              >
                                <BarChart3 className="w-4 h-4" />
                              </Button>
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
                              <div className="text-xl font-bold text-gray-900">{campaign.total_targets}</div>
                            </div>
                            <div className="bg-gray-50 p-4 rounded-lg">
                              <div className="text-sm text-gray-600">DMs Sent</div>
                              <div className="text-xl font-bold text-blue-600">{campaign.messages_sent}</div>
                            </div>
                            <div className="bg-gray-50 p-4 rounded-lg">
                              <div className="text-sm text-gray-600">Replies</div>
                              <div className="text-xl font-bold text-green-600">{campaign.replies_received}</div>
                            </div>
                            <div className="bg-gray-50 p-4 rounded-lg">
                              <div className="text-sm text-gray-600">Reply Rate</div>
                              <div className="text-xl font-bold text-purple-600">{calculateReplyRate(campaign)}</div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })
                )}
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
                    Set up a new DM campaign with personalized messaging and target selection
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {error && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}

                  {/* Basic Campaign Info */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <Label htmlFor="campaign-name">Campaign Name *</Label>
                      <Input
                        id="campaign-name"
                        placeholder="e.g., Tech Founders Q1 2025"
                        value={newCampaign.name}
                        onChange={(e) => {
                          setNewCampaign({...newCampaign, name: e.target.value});
                          if (validationErrors.name) {
                            setValidationErrors(prev => ({ ...prev, name: '' }));
                          }
                        }}
                        className={validationErrors.name ? 'border-red-500' : ''}
                      />
                      {validationErrors.name && (
                        <div className="text-sm text-red-600">{validationErrors.name}</div>
                      )}
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="account-select">X Account *</Label>
                      <Select 
                        value={newCampaign.sender_account_id.toString()} 
                        onValueChange={(value) => {
                          setNewCampaign({...newCampaign, sender_account_id: parseInt(value)});
                          if (validationErrors.sender_account_id) {
                            setValidationErrors(prev => ({ ...prev, sender_account_id: '' }));
                          }
                        }}
                      >
                        <SelectTrigger className={validationErrors.sender_account_id ? 'border-red-500' : ''}>
                          <SelectValue placeholder="Select account" />
                        </SelectTrigger>
                        <SelectContent>
                          {twitterAccounts.map((account) => (
                            <SelectItem key={account.id} value={account.id.toString()}>
                              @{account.username} ({account.display_name})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {validationErrors.sender_account_id && (
                        <div className="text-sm text-red-600">{validationErrors.sender_account_id}</div>
                      )}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="campaign-description">Description (Optional)</Label>
                    <Input
                      id="campaign-description"
                      placeholder="Brief description of your campaign"
                      value={newCampaign.description}
                      onChange={(e) => setNewCampaign({...newCampaign, description: e.target.value})}
                    />
                  </div>

                  {/* Target Type Selection */}
                  <div className="space-y-4">
                    <Label>Target Type *</Label>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <Card 
                        className={`cursor-pointer transition-colors ${
                          newCampaign.target_type === 'user_followers' ? 'ring-2 ring-blue-500 bg-blue-50' : 'hover:bg-gray-50'
                        }`}
                        onClick={() => setNewCampaign({...newCampaign, target_type: 'user_followers', target_identifier: ''})}
                      >
                        <CardContent className="p-4 text-center">
                          <Users className="w-8 h-8 mx-auto mb-2 text-blue-600" />
                          <h3 className="font-semibold">User Followers</h3>
                          <p className="text-sm text-gray-600">Target followers of a specific user</p>
                        </CardContent>
                      </Card>

                      <Card 
                        className={`cursor-pointer transition-colors ${
                          newCampaign.target_type === 'list_members' ? 'ring-2 ring-blue-500 bg-blue-50' : 'hover:bg-gray-50'
                        }`}
                        onClick={() => setNewCampaign({...newCampaign, target_type: 'list_members', target_identifier: ''})}
                      >
                        <CardContent className="p-4 text-center">
                          <FileText className="w-8 h-8 mx-auto mb-2 text-green-600" />
                          <h3 className="font-semibold">List Members</h3>
                          <p className="text-sm text-gray-600">Target members of a Twitter list</p>
                        </CardContent>
                      </Card>

                      <Card 
                        className={`cursor-pointer transition-colors ${
                          newCampaign.target_type === 'csv_upload' ? 'ring-2 ring-blue-500 bg-blue-50' : 'hover:bg-gray-50'
                        }`}
                        onClick={() => setNewCampaign({...newCampaign, target_type: 'csv_upload', target_identifier: ''})}
                      >
                        <CardContent className="p-4 text-center">
                          <Upload className="w-8 h-8 mx-auto mb-2 text-purple-600" />
                          <h3 className="font-semibold">CSV Upload</h3>
                          <p className="text-sm text-gray-600">Upload a CSV file with usernames</p>
                        </CardContent>
                      </Card>
                    </div>
                  </div>

                  {/* Target Configuration */}
                  {newCampaign.target_type === 'user_followers' && (
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="target-username">Target Username *</Label>
                        <Input
                          id="target-username"
                          placeholder="e.g., elonmusk (without @)"
                          value={newCampaign.target_identifier}
                          onChange={(e) => {
                            setNewCampaign({...newCampaign, target_identifier: e.target.value});
                            if (validationErrors.target_identifier) {
                              setValidationErrors(prev => ({ ...prev, target_identifier: '' }));
                            }
                          }}
                          className={validationErrors.target_identifier ? 'border-red-500' : ''}
                        />
                        {validationErrors.target_identifier && (
                          <div className="text-sm text-red-600">{validationErrors.target_identifier}</div>
                        )}
                        <div className="flex items-center justify-between">
                          <div className="text-sm text-gray-500">
                            Enter the username without the @ symbol
                          </div>
                          {newCampaign.target_identifier && (
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setPreviewUsername(newCampaign.target_identifier);
                                setShowFollowerPreview(true);
                              }}
                            >
                              <Eye className="w-4 h-4 mr-2" />
                              Preview Followers
                            </Button>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="verified-only"
                          checked={newCampaign.verified_only}
                          onCheckedChange={(checked) => setNewCampaign({...newCampaign, verified_only: !!checked})}
                        />
                        <Label htmlFor="verified-only" className="text-sm">
                          Target verified followers only
                        </Label>
                      </div>
                    </div>
                  )}

                  {newCampaign.target_type === 'list_members' && (
                    <div className="space-y-2">
                      <Label htmlFor="list-id">Twitter List ID *</Label>
                      <Input
                        id="list-id"
                        placeholder="e.g., 123456789"
                        value={newCampaign.target_identifier}
                        onChange={(e) => {
                          setNewCampaign({...newCampaign, target_identifier: e.target.value});
                          if (validationErrors.target_identifier) {
                            setValidationErrors(prev => ({ ...prev, target_identifier: '' }));
                          }
                        }}
                        className={validationErrors.target_identifier ? 'border-red-500' : ''}
                      />
                      {validationErrors.target_identifier && (
                        <div className="text-sm text-red-600">{validationErrors.target_identifier}</div>
                      )}
                      <div className="text-sm text-gray-500">
                        You can find the list ID in the URL when viewing a Twitter list (e.g., twitter.com/i/lists/123456789)
                      </div>
                    </div>
                  )}

                  {newCampaign.target_type === 'csv_upload' && (
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="csv-file">CSV File *</Label>
                        
                        {/* Drag and Drop Area */}
                        <div
                          className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                            isDragOver 
                              ? 'border-blue-500 bg-blue-50' 
                              : csvFile 
                                ? 'border-green-500 bg-green-50' 
                                : 'border-gray-300 hover:border-gray-400'
                          }`}
                          onDragOver={handleDragOver}
                          onDragLeave={handleDragLeave}
                          onDrop={handleDrop}
                          onClick={() => fileInputRef.current?.click()}
                        >
                          <input
                            ref={fileInputRef}
                            type="file"
                            accept=".csv"
                            onChange={handleFileUpload}
                            className="hidden"
                          />
                          
                          {csvFile ? (
                            <div className="space-y-2">
                              <CheckCircle className="w-8 h-8 text-green-600 mx-auto" />
                              <div className="font-medium text-green-700">{csvFile.name}</div>
                              <div className="text-sm text-gray-600">
                                {(csvFile.size / 1024).toFixed(1)} KB
                              </div>
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  removeCsvFile();
                                }}
                                className="mt-2"
                              >
                                <X className="w-4 h-4 mr-1" />
                                Remove
                              </Button>
                            </div>
                          ) : (
                            <div className="space-y-2">
                              <Upload className="w-8 h-8 text-gray-400 mx-auto" />
                              <div className="font-medium text-gray-700">
                                Drop your CSV file here or click to browse
                              </div>
                              <div className="text-sm text-gray-500">
                                Maximum file size: 10MB
                              </div>
                            </div>
                          )}
                        </div>
                        
                        {validationErrors.csv_file && (
                          <div className="text-sm text-red-600">{validationErrors.csv_file}</div>
                        )}
                        
                        <div className="text-sm text-gray-500">
                          CSV should have columns: <strong>username</strong> (required), <strong>display_name</strong> (optional), <strong>notes</strong> (optional)
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Message Template */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="dm-template">DM Template *</Label>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={generatePreview}
                        disabled={!newCampaign.message_template.trim()}
                      >
                        <Eye className="w-4 h-4 mr-1" />
                        Preview
                      </Button>
                    </div>
                    <Textarea
                      id="dm-template"
                      placeholder="Hi {name}, I noticed you're working on..."
                      rows={4}
                      value={newCampaign.message_template}
                      onChange={(e) => {
                        setNewCampaign({...newCampaign, message_template: e.target.value});
                        if (validationErrors.message_template) {
                          setValidationErrors(prev => ({ ...prev, message_template: '' }));
                        }
                      }}
                      className={validationErrors.message_template ? 'border-red-500' : ''}
                    />
                    {validationErrors.message_template && (
                      <div className="text-sm text-red-600">{validationErrors.message_template}</div>
                    )}
                    <div className="flex items-center justify-between text-sm">
                      <div className="text-gray-500">
                        Use <code className="bg-gray-100 px-1 rounded">{'{name}'}</code>, <code className="bg-gray-100 px-1 rounded">{'{username}'}</code>, or <code className="bg-gray-100 px-1 rounded">{'{display_name}'}</code> for personalization
                      </div>
                      <div className={`${newCampaign.message_template.length > 280 ? 'text-red-600' : 'text-gray-500'}`}>
                        {newCampaign.message_template.length}/280 characters
                      </div>
                    </div>
                  </div>

                  {/* Campaign Settings */}
                  <div className="space-y-2">
                    <Label htmlFor="daily-limit">Daily DM Limit</Label>
                    <Select 
                      value={newCampaign.daily_limit.toString()} 
                      onValueChange={(value) => setNewCampaign({...newCampaign, daily_limit: parseInt(value)})}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="25">25 DMs/day</SelectItem>
                        <SelectItem value="50">50 DMs/day</SelectItem>
                        <SelectItem value="100">100 DMs/day</SelectItem>
                        <SelectItem value="200">200 DMs/day</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Create Campaign Button */}
                  <div className="flex items-center justify-between pt-6 border-t">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={resetForm}
                      disabled={isCreating}
                    >
                      Reset Form
                    </Button>
                    <Button
                      onClick={createCampaign}
                      disabled={isCreating}
                      className="min-w-[120px]"
                    >
                      {isCreating ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Creating...
                        </>
                      ) : (
                        <>
                          <Plus className="w-4 h-4 mr-2" />
                          Create Campaign
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="analytics" className="space-y-6">
              {campaigns.length === 0 ? (
                <Card className="border-0 shadow-lg">
                  <CardContent className="p-12 text-center">
                    <BarChart3 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">No campaigns to analyze</h3>
                    <p className="text-gray-600 mb-4">Create campaigns first to view analytics</p>
                    <Button onClick={() => {
                      const createTab = document.querySelector('[value="create"]') as HTMLElement;
                      createTab?.click();
                    }}>
                      <Plus className="w-4 h-4 mr-2" />
                      Create Campaign
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">Campaign Analytics</h3>
                      <p className="text-gray-600">Select a campaign to view detailed analytics</p>
                    </div>
                  </div>
                  
                  {/* Campaign Selection for Analytics */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {campaigns.map((campaign) => (
                      <Card 
                        key={campaign.id} 
                        className="border-0 shadow-lg cursor-pointer hover:shadow-xl transition-all"
                        onClick={() => {
                          setAnalyticsCampaign(campaign);
                          setShowAnalytics(true);
                        }}
                      >
                        <CardContent className="p-6">
                          <div className="flex items-start justify-between mb-4">
                            <div className="flex-1">
                              <div className="flex items-center space-x-2 mb-2">
                                <h4 className="font-semibold text-gray-900">{campaign.name}</h4>
                                <Badge variant={campaign.status === 'active' ? 'default' : 'secondary'}>
                                  {campaign.status}
                                </Badge>
                              </div>
                              <p className="text-sm text-gray-600 mb-3">
                                {campaign.description || 'No description'}
                              </p>
                            </div>
                            <BarChart3 className="w-5 h-5 text-blue-600" />
                          </div>
                          
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <div className="text-gray-600">Targets</div>
                              <div className="font-bold">{campaign.total_targets}</div>
                            </div>
                            <div>
                              <div className="text-gray-600">Sent</div>
                              <div className="font-bold text-blue-600">{campaign.messages_sent}</div>
                            </div>
                            <div>
                              <div className="text-gray-600">Replies</div>
                              <div className="font-bold text-green-600">{campaign.replies_received}</div>
                            </div>
                            <div>
                              <div className="text-gray-600">Rate</div>
                              <div className="font-bold text-purple-600">
                                {campaign.messages_sent > 0 
                                  ? ((campaign.replies_received / campaign.messages_sent) * 100).toFixed(1) + '%'
                                  : '0%'
                                }
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}
            </TabsContent>

            <TabsContent value="comparison" className="space-y-6">
              {campaigns.length < 2 ? (
                <Card className="border-0 shadow-lg">
                  <CardContent className="p-12 text-center">
                    <PieChart className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">Need more campaigns</h3>
                    <p className="text-gray-600 mb-4">Create at least 2 campaigns to compare performance</p>
                    <Button onClick={() => {
                      const createTab = document.querySelector('[value="create"]') as HTMLElement;
                      createTab?.click();
                    }}>
                      <Plus className="w-4 h-4 mr-2" />
                      Create Campaign
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                <CampaignComparison campaigns={campaigns} />
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Message Preview Dialog */}
      <Dialog open={showPreview} onOpenChange={setShowPreview}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Message Preview</DialogTitle>
            <DialogDescription>
              This is how your message will look with sample personalization data
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600 mb-2">Preview with sample data:</div>
              <div className="font-medium">{previewMessage}</div>
            </div>
            <div className="text-sm text-gray-500">
              Character count: {previewMessage.length}/280
            </div>
          </div>
          <DialogFooter>
            <Button onClick={() => setShowPreview(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Campaign Launch Confirmation Dialog */}
      <Dialog open={showLaunchConfirm} onOpenChange={setShowLaunchConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Launch Campaign</DialogTitle>
            <DialogDescription>
              Are you sure you want to launch "{campaignToLaunch?.name}"? This will start sending DMs to all targets.
            </DialogDescription>
          </DialogHeader>
          {campaignToLaunch && (
            <div className="space-y-4">
              <div className="bg-gray-50 p-4 rounded-lg space-y-2">
                <div><strong>Campaign:</strong> {campaignToLaunch.name}</div>
                <div><strong>Targets:</strong> {campaignToLaunch.total_targets} recipients</div>
                <div><strong>Daily Limit:</strong> {campaignToLaunch.daily_limit} DMs/day</div>
                <div><strong>Account:</strong> @{twitterAccounts.find(acc => acc.id === campaignToLaunch.sender_account_id)?.username}</div>
              </div>
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Once launched, the campaign will start sending DMs immediately. Make sure your message template and targets are correct.
                </AlertDescription>
              </Alert>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowLaunchConfirm(false)}>
              Cancel
            </Button>
            <Button onClick={launchCampaign}>
              <Send className="w-4 h-4 mr-2" />
              Launch Campaign
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Campaign Monitor Dialog */}
      <Dialog open={showMonitor} onOpenChange={setShowMonitor}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Campaign Monitor</DialogTitle>
            <DialogDescription>
              Real-time monitoring and control for your campaign
            </DialogDescription>
          </DialogHeader>
          {selectedCampaign && (
            <CampaignMonitor
              campaign={selectedCampaign}
              onCampaignUpdate={(updatedCampaign) => {
                setSelectedCampaign(updatedCampaign);
                // Update the campaign in the main list
                setCampaigns(prev => prev.map(c => 
                  c.id === updatedCampaign.id ? updatedCampaign : c
                ));
              }}
              onClose={() => setShowMonitor(false)}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Campaign Analytics Dialog */}
      <Dialog open={showAnalytics} onOpenChange={setShowAnalytics}>
        <DialogContent className="max-w-7xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Campaign Analytics</DialogTitle>
          </DialogHeader>
          {analyticsCampaign && (
            <CampaignAnalyticsDashboard
              campaignId={analyticsCampaign.id}
              onClose={() => setShowAnalytics(false)}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Follower Preview Dialog */}
      <Dialog open={showFollowerPreview} onOpenChange={setShowFollowerPreview}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Follower Preview</DialogTitle>
          </DialogHeader>
          {previewUsername && (
            <FollowerPreview
              username={previewUsername}
              onClose={() => setShowFollowerPreview(false)}
              onUseForCampaign={(username, followerCount) => {
                setNewCampaign(prev => ({ ...prev, target_identifier: username }));
                setShowFollowerPreview(false);
                // Show a toast or notification about the follower count
                console.log(`Using @${username} with ${followerCount} followers for campaign`);
              }}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}