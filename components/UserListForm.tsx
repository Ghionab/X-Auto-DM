'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { X, Upload, Users, Loader2 } from 'lucide-react';
import { api, TwitterAccount, withToast } from '@/lib/api';

export default function UserListForm() {
  const [usernames, setUsernames] = useState<string[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [dmTemplate, setDmTemplate] = useState('');
  const [isScrapingUsers, setIsScrapingUsers] = useState(false);
  const [targetAccount, setTargetAccount] = useState('');
  const [campaignName, setCampaignName] = useState('');
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
  const [twitterAccounts, setTwitterAccounts] = useState<TwitterAccount[]>([]);
  const [isCreatingCampaign, setIsCreatingCampaign] = useState(false);
  const [maxFollowersToScrape, setMaxFollowersToScrape] = useState('100');

  useEffect(() => {
    const fetchAccounts = async () => {
      const response = await api.getTwitterAccounts();
      if (response.success) {
        setTwitterAccounts(response.data?.accounts || []);
      }
    };

    fetchAccounts();
  }, []);

  const addUsername = (username: string) => {
    const cleanUsername = username.replace('@', '').trim();
    if (cleanUsername && !usernames.includes(cleanUsername)) {
      setUsernames([...usernames, cleanUsername]);
      setInputValue('');
    }
  };

  const removeUsername = (username: string) => {
    setUsernames(usernames.filter(u => u !== username));
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addUsername(inputValue);
    }
  };

  const scrapeFollowers = async () => {
    if (!targetAccount.trim()) return;
    
    setIsScrapingUsers(true);
    try {
      const maxFollowers = parseInt(maxFollowersToScrape) || 100;
      const cleanUsername = targetAccount.replace('@', '').trim();
      
      const response = await withToast(
        api.scrapeFollowersLegacy(cleanUsername, maxFollowers),
        `Successfully scraped followers from @${cleanUsername}`,
        `Failed to scrape followers from @${cleanUsername}`
      );
      
      if (response && response.followers) {
        const newUsernames = response.followers.map((f: any) => f.username || f.screen_name)
          .filter((username: string) => !usernames.includes(username));
        setUsernames([...usernames, ...newUsernames]);
        setTargetAccount('');
      }
    } catch (error) {
      console.error('Error scraping followers:', error);
    } finally {
      setIsScrapingUsers(false);
    }
  };

  const createCampaign = async () => {
    if (!campaignName.trim() || !selectedAccountId || usernames.length === 0 || !dmTemplate.trim()) {
      return;
    }

    setIsCreatingCampaign(true);
    try {
      const campaignData = {
        name: campaignName,
        sender_account_id: selectedAccountId,
        target_type: 'csv_upload' as const,
        message_template: dmTemplate,
        daily_limit: 50
      };

      const response = await withToast(
        api.createCampaign(campaignData),
        'Campaign created successfully!',
        'Failed to create campaign'
      );

      if (response) {
        // Add targets to the campaign
        const targets = usernames.map(username => ({ username }));
        await withToast(
          api.addCampaignTargets(response.campaign.id, targets),
          `Added ${targets.length} targets to campaign`,
          'Failed to add targets to campaign'
        );

        // Reset form
        setCampaignName('');
        setUsernames([]);
        setDmTemplate('');
        setSelectedAccountId(null);
      }
    } catch (error) {
      console.error('Error creating campaign:', error);
    } finally {
      setIsCreatingCampaign(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Target List Building */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Users className="w-5 h-5 text-blue-600" />
            <span>Build Target List</span>
          </CardTitle>
          <CardDescription>
            Add usernames manually or scrape followers from competitor accounts
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Manual Input */}
          <div className="space-y-2">
            <Label htmlFor="username">Add Username</Label>
            <div className="flex space-x-2">
              <Input
                id="username"
                placeholder="@username or username"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                className="flex-1"
              />
              <Button 
                onClick={() => addUsername(inputValue)}
                disabled={!inputValue.trim()}
              >
                Add
              </Button>
            </div>
          </div>

          {/* Scrape Followers */}
          <div className="space-y-2">
            <Label htmlFor="target">Scrape Followers From</Label>
            <div className="flex space-x-2">
              <Input
                id="target"
                placeholder="@competitor_account"
                value={targetAccount}
                onChange={(e) => setTargetAccount(e.target.value)}
                className="flex-1"
              />
              <Input
                type="number"
                placeholder="100"
                value={maxFollowersToScrape}
                onChange={(e) => setMaxFollowersToScrape(e.target.value)}
                className="w-20"
                min="1"
                max="1000"
              />
              <Button 
                onClick={scrapeFollowers}
                disabled={!targetAccount.trim() || isScrapingUsers}
                className="bg-purple-600 hover:bg-purple-700"
              >
                {isScrapingUsers ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Scraping...
                  </>
                ) : (
                  'Scrape'
                )}
              </Button>
            </div>
            <div className="text-xs text-gray-500">
              Enter the number of followers to scrape (max 1000)
            </div>
          </div>

          {/* Current List */}
          {usernames.length > 0 && (
            <div className="space-y-2">
              <Label>Target Users ({usernames.length})</Label>
              <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto p-3 bg-gray-50 rounded-lg">
                {usernames.map((username) => (
                  <Badge
                    key={username}
                    variant="secondary"
                    className="flex items-center space-x-1 px-3 py-1"
                  >
                    <span>@{username}</span>
                    <X
                      className="w-3 h-3 cursor-pointer hover:text-red-600"
                      onClick={() => removeUsername(username)}
                    />
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Campaign Setup */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <CardTitle>Campaign Setup</CardTitle>
          <CardDescription>
            Configure your campaign settings and message template.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Campaign Name */}
          <div className="space-y-2">
            <Label htmlFor="campaignName">Campaign Name</Label>
            <Input
              id="campaignName"
              placeholder="e.g., Q4 Outreach Campaign"
              value={campaignName}
              onChange={(e) => setCampaignName(e.target.value)}
            />
          </div>

          {/* Select Twitter Account */}
          <div className="space-y-2">
            <Label>Select Twitter Account</Label>
            <Select onValueChange={(value) => setSelectedAccountId(parseInt(value))}>
              <SelectTrigger>
                <SelectValue placeholder="Choose an account to send DMs from" />
              </SelectTrigger>
              <SelectContent>
                {twitterAccounts.filter(acc => acc.is_active).map((account) => (
                  <SelectItem key={account.id} value={account.id.toString()}>
                    @{account.username} ({account.followers_count?.toLocaleString() || 0} followers)
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {twitterAccounts.length === 0 && (
              <p className="text-sm text-red-600">No active Twitter accounts found. Please connect an account first.</p>
            )}
          </div>

          {/* DM Template */}
          <div className="space-y-2">
            <Label htmlFor="dmTemplate">Message Template</Label>
            <Textarea
              id="dmTemplate"
              placeholder="Hi {name}, I noticed you follow @competitor and thought you might be interested in..."
              value={dmTemplate}
              onChange={(e) => setDmTemplate(e.target.value)}
              rows={4}
              className="resize-none"
            />
            <div className="text-xs text-gray-500">
              Use {'{name}'} for personalization. Character count: {dmTemplate.length}/280
            </div>
          </div>

          <div className="flex justify-between items-center pt-4">
            <div className="text-sm text-gray-600">
              {usernames.length} targets • {twitterAccounts.filter(acc => acc.is_active).length} accounts available
            </div>
            <Button 
              onClick={createCampaign}
              disabled={
                usernames.length === 0 || 
                !dmTemplate.trim() || 
                !campaignName.trim() || 
                !selectedAccountId || 
                isCreatingCampaign
              }
              className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
            >
              {isCreatingCampaign ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Campaign'
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}