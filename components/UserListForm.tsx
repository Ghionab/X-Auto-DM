'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { X, Upload, Users, Loader2 } from 'lucide-react';

export default function UserListForm() {
  const [usernames, setUsernames] = useState<string[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [dmTemplate, setDmTemplate] = useState('');
  const [isScrapingUsers, setIsScrapingUsers] = useState(false);
  const [targetAccount, setTargetAccount] = useState('');

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
    // Simulate scraping process
    setTimeout(() => {
      const mockUsers = ['user1', 'user2', 'user3', 'user4', 'user5'];
      setUsernames([...usernames, ...mockUsers.filter(u => !usernames.includes(u))]);
      setIsScrapingUsers(false);
      setTargetAccount('');
    }, 3000);
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

      {/* DM Template */}
      <Card className="border-0 shadow-lg">
        <CardHeader>
          <CardTitle>DM Template</CardTitle>
          <CardDescription>
            Create your message template. Use {'{name}'} for personalization.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            placeholder="Hi {name}, I noticed you follow @competitor and thought you might be interested in..."
            value={dmTemplate}
            onChange={(e) => setDmTemplate(e.target.value)}
            rows={4}
            className="resize-none"
          />
          <div className="mt-4 flex justify-between items-center">
            <div className="text-sm text-gray-500">
              {dmTemplate.length}/280 characters
            </div>
            <Button 
              disabled={usernames.length === 0 || !dmTemplate.trim()}
              className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
            >
              Start Campaign
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}