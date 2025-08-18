'use client';

import { BarChart3, TrendingUp, Users, MessageSquare } from 'lucide-react';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import AnalyticsCard from '@/components/AnalyticsCard';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function Analytics() {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      
      <div className="flex-1 lg:ml-64">
        <Header 
          title="Analytics" 
          subtitle="Detailed insights into your DM campaign performance"
        />
        
        <div className="p-6 space-y-6">
          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <AnalyticsCard
              title="Total DMs Sent"
              value="12,847"
              change={{ value: 18.2, trend: 'up' }}
              icon={<MessageSquare className="w-5 h-5" />}
              description="Last 30 days"
            />
            <AnalyticsCard
              title="Overall Reply Rate"
              value="42.8%"
              change={{ value: 5.1, trend: 'up' }}
              icon={<TrendingUp className="w-5 h-5" />}
              description="Above industry average"
            />
            <AnalyticsCard
              title="Unique Conversations"
              value="5,476"
              change={{ value: 12.3, trend: 'up' }}
              icon={<Users className="w-5 h-5" />}
              description="Active conversations"
            />
            <AnalyticsCard
              title="Conversion Rate"
              value="15.2%"
              change={{ value: 2.8, trend: 'up' }}
              icon={<BarChart3 className="w-5 h-5" />}
              description="DMs to meetings"
            />
          </div>

          {/* Charts Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Performance Over Time */}
            <Card className="border-0 shadow-lg">
              <CardHeader>
                <CardTitle>Performance Over Time</CardTitle>
                <CardDescription>DM metrics for the last 30 days</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-80 bg-gradient-to-br from-blue-50 to-purple-50 rounded-lg flex items-center justify-center">
                  <div className="text-center text-gray-500">
                    <BarChart3 className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>Performance chart visualization</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Reply Rate by Campaign */}
            <Card className="border-0 shadow-lg">
              <CardHeader>
                <CardTitle>Reply Rate by Campaign</CardTitle>
                <CardDescription>Compare campaign performance</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {[
                    { name: 'Tech Founders', sent: 450, replies: 198, rate: '44.0%' },
                    { name: 'Marketing Directors', sent: 320, replies: 142, rate: '44.4%' },
                    { name: 'Startup CEOs', sent: 280, replies: 112, rate: '40.0%' },
                    { name: 'Sales Leaders', sent: 210, replies: 92, rate: '43.8%' },
                    { name: 'Product Managers', sent: 180, replies: 68, rate: '37.8%' },
                  ].map((campaign, index) => (
                    <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div>
                        <div className="font-medium text-gray-900">{campaign.name}</div>
                        <div className="text-sm text-gray-600">{campaign.sent} sent • {campaign.replies} replies</div>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-bold text-gray-900">{campaign.rate}</div>
                        <div className="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-blue-600 to-purple-600"
                            style={{ width: campaign.rate }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Detailed Analytics */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Top Performing Messages */}
            <Card className="border-0 shadow-lg">
              <CardHeader>
                <CardTitle>Top Performing Messages</CardTitle>
                <CardDescription>Highest reply rates</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {[
                    { message: 'Hi {name}, loved your recent post about...', rate: '52.3%' },
                    { message: 'Hey {name}, saw you speak at...', rate: '48.9%' },
                    { message: 'Hi {name}, noticed we both follow...', rate: '45.7%' },
                    { message: 'Hey {name}, quick question about...', rate: '43.2%' },
                  ].map((msg, index) => (
                    <div key={index} className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-sm text-gray-900 mb-1 truncate">
                        {msg.message}
                      </div>
                      <div className="text-xs text-green-600 font-medium">
                        {msg.rate} reply rate
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Best Times to Send */}
            <Card className="border-0 shadow-lg">
              <CardHeader>
                <CardTitle>Best Times to Send</CardTitle>
                <CardDescription>Optimal sending schedule</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {[
                    { time: '9:00 AM - 10:00 AM', rate: '48.2%', day: 'Tuesday' },
                    { time: '2:00 PM - 3:00 PM', rate: '45.7%', day: 'Wednesday' },
                    { time: '11:00 AM - 12:00 PM', rate: '44.1%', day: 'Thursday' },
                    { time: '4:00 PM - 5:00 PM', rate: '42.8%', day: 'Monday' },
                  ].map((slot, index) => (
                    <div key={index} className="p-3 bg-gray-50 rounded-lg">
                      <div className="flex justify-between items-center">
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {slot.day} {slot.time}
                          </div>
                        </div>
                        <div className="text-sm text-green-600 font-medium">
                          {slot.rate}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Account Performance */}
            <Card className="border-0 shadow-lg">
              <CardHeader>
                <CardTitle>Account Performance</CardTitle>
                <CardDescription>Performance by connected account</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {[
                    { account: '@your_account', sent: 2150, rate: '44.2%', status: 'active' },
                    { account: '@business_acc', sent: 1890, rate: '42.8%', status: 'active' },
                    { account: '@personal_brand', sent: 980, rate: '40.1%', status: 'paused' },
                  ].map((acc, index) => (
                    <div key={index} className="p-3 bg-gray-50 rounded-lg">
                      <div className="flex justify-between items-center mb-2">
                        <div className="font-medium text-gray-900">{acc.account}</div>
                        <div className="text-sm text-green-600 font-medium">{acc.rate}</div>
                      </div>
                      <div className="text-xs text-gray-600">
                        {acc.sent} DMs sent • {acc.status}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}