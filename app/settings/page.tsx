'use client';

import { useState } from 'react';
import { User, Bell, Shield, CreditCard, Key, Globe, Smartphone, Mail } from 'lucide-react';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';

export default function Settings() {
  const [profile, setProfile] = useState({
    name: 'John Doe',
    email: 'john@example.com',
    company: 'Tech Startup Inc.',
    timezone: 'America/New_York',
    language: 'en'
  });

  const [notifications, setNotifications] = useState({
    emailReports: true,
    campaignAlerts: true,
    replyNotifications: true,
    weeklyDigest: false,
    securityAlerts: true
  });

  const [automation, setAutomation] = useState({
    autoReply: false,
    smartScheduling: true,
    rateLimiting: true,
    pauseOnHighActivity: true
  });

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      
      <div className="flex-1 lg:ml-64">
        <Header 
          title="Settings" 
          subtitle="Manage your account preferences and application settings"
        />
        
        <div className="p-6">
          <Tabs defaultValue="profile" className="space-y-6">
            <TabsList className="grid w-full grid-cols-5">
              <TabsTrigger value="profile">Profile</TabsTrigger>
              <TabsTrigger value="notifications">Notifications</TabsTrigger>
              <TabsTrigger value="automation">Automation</TabsTrigger>
              <TabsTrigger value="security">Security</TabsTrigger>
              <TabsTrigger value="billing">Billing</TabsTrigger>
            </TabsList>

            {/* Profile Settings */}
            <TabsContent value="profile">
              <Card className="border-0 shadow-lg">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <User className="w-5 h-5 text-blue-600" />
                    <span>Profile Information</span>
                  </CardTitle>
                  <CardDescription>
                    Update your personal information and preferences
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center space-x-6">
                    <div className="w-20 h-20 bg-gradient-to-br from-blue-600 to-purple-600 rounded-full flex items-center justify-center text-white text-2xl font-bold">
                      {profile.name.split(' ').map(n => n[0]).join('')}
                    </div>
                    <div>
                      <Button variant="outline">Change Avatar</Button>
                      <p className="text-sm text-gray-500 mt-2">JPG, GIF or PNG. 1MB max.</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <Label htmlFor="name">Full Name</Label>
                      <Input
                        id="name"
                        value={profile.name}
                        onChange={(e) => setProfile({...profile, name: e.target.value})}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="email">Email Address</Label>
                      <Input
                        id="email"
                        type="email"
                        value={profile.email}
                        onChange={(e) => setProfile({...profile, email: e.target.value})}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <Label htmlFor="company">Company</Label>
                      <Input
                        id="company"
                        value={profile.company}
                        onChange={(e) => setProfile({...profile, company: e.target.value})}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="timezone">Timezone</Label>
                      <Select value={profile.timezone} onValueChange={(value) => setProfile({...profile, timezone: value})}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="America/New_York">Eastern Time (ET)</SelectItem>
                          <SelectItem value="America/Chicago">Central Time (CT)</SelectItem>
                          <SelectItem value="America/Denver">Mountain Time (MT)</SelectItem>
                          <SelectItem value="America/Los_Angeles">Pacific Time (PT)</SelectItem>
                          <SelectItem value="Europe/London">London (GMT)</SelectItem>
                          <SelectItem value="Europe/Paris">Paris (CET)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="flex justify-end">
                    <Button className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700">
                      Save Changes
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Notification Settings */}
            <TabsContent value="notifications">
              <Card className="border-0 shadow-lg">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Bell className="w-5 h-5 text-blue-600" />
                    <span>Notification Preferences</span>
                  </CardTitle>
                  <CardDescription>
                    Choose how you want to be notified about campaign activities
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <Mail className="w-5 h-5 text-gray-600" />
                        <div>
                          <div className="font-medium">Email Reports</div>
                          <div className="text-sm text-gray-600">Daily campaign performance summaries</div>
                        </div>
                      </div>
                      <Switch 
                        checked={notifications.emailReports}
                        onCheckedChange={(checked) => setNotifications({...notifications, emailReports: checked})}
                      />
                    </div>

                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <Bell className="w-5 h-5 text-gray-600" />
                        <div>
                          <div className="font-medium">Campaign Alerts</div>
                          <div className="text-sm text-gray-600">Notifications when campaigns start, pause, or complete</div>
                        </div>
                      </div>
                      <Switch 
                        checked={notifications.campaignAlerts}
                        onCheckedChange={(checked) => setNotifications({...notifications, campaignAlerts: checked})}
                      />
                    </div>

                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <Smartphone className="w-5 h-5 text-gray-600" />
                        <div>
                          <div className="font-medium">Reply Notifications</div>
                          <div className="text-sm text-gray-600">Instant notifications for new DM replies</div>
                        </div>
                      </div>
                      <Switch 
                        checked={notifications.replyNotifications}
                        onCheckedChange={(checked) => setNotifications({...notifications, replyNotifications: checked})}
                      />
                    </div>

                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <Globe className="w-5 h-5 text-gray-600" />
                        <div>
                          <div className="font-medium">Weekly Digest</div>
                          <div className="text-sm text-gray-600">Weekly summary of all campaign activities</div>
                        </div>
                      </div>
                      <Switch 
                        checked={notifications.weeklyDigest}
                        onCheckedChange={(checked) => setNotifications({...notifications, weeklyDigest: checked})}
                      />
                    </div>

                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <Shield className="w-5 h-5 text-gray-600" />
                        <div>
                          <div className="font-medium">Security Alerts</div>
                          <div className="text-sm text-gray-600">Important security and account notifications</div>
                        </div>
                      </div>
                      <Switch 
                        checked={notifications.securityAlerts}
                        onCheckedChange={(checked) => setNotifications({...notifications, securityAlerts: checked})}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Automation Settings */}
            <TabsContent value="automation">
              <Card className="border-0 shadow-lg">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Shield className="w-5 h-5 text-blue-600" />
                    <span>Automation Settings</span>
                  </CardTitle>
                  <CardDescription>
                    Configure automation rules and safety features
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div>
                        <div className="font-medium">Auto-Reply to DMs</div>
                        <div className="text-sm text-gray-600">Automatically respond to incoming DMs</div>
                      </div>
                      <Switch 
                        checked={automation.autoReply}
                        onCheckedChange={(checked) => setAutomation({...automation, autoReply: checked})}
                      />
                    </div>

                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div>
                        <div className="font-medium">Smart Scheduling</div>
                        <div className="text-sm text-gray-600">Send DMs at optimal times based on recipient timezone</div>
                      </div>
                      <Switch 
                        checked={automation.smartScheduling}
                        onCheckedChange={(checked) => setAutomation({...automation, smartScheduling: checked})}
                      />
                    </div>

                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div>
                        <div className="font-medium">Rate Limiting</div>
                        <div className="text-sm text-gray-600">Automatically limit DM sending to avoid restrictions</div>
                      </div>
                      <Switch 
                        checked={automation.rateLimiting}
                        onCheckedChange={(checked) => setAutomation({...automation, rateLimiting: checked})}
                      />
                    </div>

                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div>
                        <div className="font-medium">Pause on High Activity</div>
                        <div className="text-sm text-gray-600">Pause campaigns if unusual activity is detected</div>
                      </div>
                      <Switch 
                        checked={automation.pauseOnHighActivity}
                        onCheckedChange={(checked) => setAutomation({...automation, pauseOnHighActivity: checked})}
                      />
                    </div>
                  </div>

                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                    <div className="flex items-start space-x-3">
                      <Shield className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <h4 className="font-medium text-amber-800 mb-1">Safety Recommendations</h4>
                        <ul className="text-sm text-amber-700 space-y-1">
                          <li>• Keep daily limits under 100 DMs per account</li>
                          <li>• Use different message templates across campaigns</li>
                          <li>• Monitor reply rates and adjust targeting</li>
                          <li>• Take regular breaks between campaigns</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Security Settings */}
            <TabsContent value="security">
              <div className="space-y-6">
                <Card className="border-0 shadow-lg">
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Key className="w-5 h-5 text-blue-600" />
                      <span>Password & Authentication</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="current-password">Current Password</Label>
                      <Input id="current-password" type="password" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="new-password">New Password</Label>
                      <Input id="new-password" type="password" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="confirm-password">Confirm New Password</Label>
                      <Input id="confirm-password" type="password" />
                    </div>
                    <Button>Update Password</Button>
                  </CardContent>
                </Card>

                <Card className="border-0 shadow-lg">
                  <CardHeader>
                    <CardTitle>API Keys</CardTitle>
                    <CardDescription>
                      Manage your API keys for integrations
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div>
                        <div className="font-medium">Production API Key</div>
                        <div className="text-sm text-gray-600 font-mono">xdm_prod_••••••••••••••••</div>
                      </div>
                      <div className="flex space-x-2">
                        <Button variant="outline" size="sm">Regenerate</Button>
                        <Button variant="outline" size="sm">Copy</Button>
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div>
                        <div className="font-medium">Test API Key</div>
                        <div className="text-sm text-gray-600 font-mono">xdm_test_••••••••••••••••</div>
                      </div>
                      <div className="flex space-x-2">
                        <Button variant="outline" size="sm">Regenerate</Button>
                        <Button variant="outline" size="sm">Copy</Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-0 shadow-lg">
                  <CardHeader>
                    <CardTitle>Login Sessions</CardTitle>
                    <CardDescription>
                      Active sessions across your devices
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {[
                      { device: 'MacBook Pro', location: 'New York, US', current: true, lastActive: 'Active now' },
                      { device: 'iPhone 15', location: 'New York, US', current: false, lastActive: '2 hours ago' },
                      { device: 'Chrome Browser', location: 'San Francisco, US', current: false, lastActive: '1 day ago' }
                    ].map((session, index) => (
                      <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                        <div>
                          <div className="font-medium flex items-center space-x-2">
                            <span>{session.device}</span>
                            {session.current && <Badge variant="default">Current</Badge>}
                          </div>
                          <div className="text-sm text-gray-600">{session.location} • {session.lastActive}</div>
                        </div>
                        {!session.current && (
                          <Button variant="outline" size="sm" className="text-red-600">
                            Revoke
                          </Button>
                        )}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* Billing Settings */}
            <TabsContent value="billing">
              <div className="space-y-6">
                <Card className="border-0 shadow-lg">
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <CreditCard className="w-5 h-5 text-blue-600" />
                      <span>Current Plan</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between p-6 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg">
                      <div>
                        <div className="text-2xl font-bold text-gray-900">Professional Plan</div>
                        <div className="text-gray-600">$79/month • Renews on Feb 15, 2025</div>
                        <div className="text-sm text-gray-500 mt-2">2,500 DMs/month • 5 accounts • AI personalization</div>
                      </div>
                      <div className="text-right">
                        <Button variant="outline">Change Plan</Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-0 shadow-lg">
                  <CardHeader>
                    <CardTitle>Payment Method</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-6 bg-blue-600 rounded flex items-center justify-center text-white text-xs font-bold">
                          VISA
                        </div>
                        <div>
                          <div className="font-medium">•••• •••• •••• 4242</div>
                          <div className="text-sm text-gray-600">Expires 12/27</div>
                        </div>
                      </div>
                      <div className="flex space-x-2">
                        <Button variant="outline" size="sm">Edit</Button>
                        <Button variant="outline" size="sm">Remove</Button>
                      </div>
                    </div>
                    <Button variant="outline">Add Payment Method</Button>
                  </CardContent>
                </Card>

                <Card className="border-0 shadow-lg">
                  <CardHeader>
                    <CardTitle>Billing History</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {[
                        { date: 'Jan 15, 2025', amount: '$79.00', status: 'Paid', invoice: 'INV-001' },
                        { date: 'Dec 15, 2024', amount: '$79.00', status: 'Paid', invoice: 'INV-002' },
                        { date: 'Nov 15, 2024', amount: '$79.00', status: 'Paid', invoice: 'INV-003' }
                      ].map((bill, index) => (
                        <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div>
                            <div className="font-medium">{bill.date}</div>
                            <div className="text-sm text-gray-600">{bill.invoice}</div>
                          </div>
                          <div className="text-right">
                            <div className="font-medium">{bill.amount}</div>
                            <Badge variant="outline" className="text-green-600 border-green-600">
                              {bill.status}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}