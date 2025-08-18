'use client';

import { Check, Star, Zap } from 'lucide-react';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export default function Plans() {
  const plans = [
    {
      name: 'Starter',
      price: '$29',
      period: '/month',
      description: 'Perfect for individuals getting started with DM automation',
      features: [
        'Up to 500 DMs per month',
        '1 connected X account',
        'Basic templates',
        'Email support',
        'Basic analytics'
      ],
      popular: false,
      buttonText: 'Start Free Trial'
    },
    {
      name: 'Professional',
      price: '$79',
      period: '/month',
      description: 'Ideal for businesses and agencies scaling their outreach',
      features: [
        'Up to 2,500 DMs per month',
        '5 connected X accounts',
        'AI-powered personalization',
        'Advanced analytics',
        'Priority support',
        'Custom templates',
        'A/B testing'
      ],
      popular: true,
      buttonText: 'Start Free Trial'
    },
    {
      name: 'Enterprise',
      price: '$199',
      period: '/month',
      description: 'For large organizations with advanced automation needs',
      features: [
        'Unlimited DMs',
        'Unlimited connected accounts',
        'Custom AI models',
        'Advanced automation',
        'Dedicated support',
        'Custom integrations',
        'White-label options',
        'Priority processing'
      ],
      popular: false,
      buttonText: 'Contact Sales'
    }
  ];

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      
      <div className="flex-1 lg:ml-64">
        <Header 
          title="Subscription Plans" 
          subtitle="Choose the perfect plan for your DM automation needs"
        />
        
        <div className="p-6">
          {/* Billing Toggle */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center space-x-4 bg-white rounded-lg p-1 border">
              <Button variant="default" size="sm">Monthly</Button>
              <Button variant="ghost" size="sm">
                Annual 
                <Badge className="ml-2 bg-green-100 text-green-700">Save 20%</Badge>
              </Button>
            </div>
          </div>

          {/* Plans Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
            {plans.map((plan, index) => (
              <Card 
                key={index}
                className={`relative border-0 shadow-lg transition-all duration-300 hover:shadow-xl ${
                  plan.popular ? 'ring-2 ring-blue-600 scale-105' : ''
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                    <Badge className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-4 py-1">
                      <Star className="w-3 h-3 mr-1" />
                      Most Popular
                    </Badge>
                  </div>
                )}
                
                <CardHeader className="text-center pb-4">
                  <CardTitle className="text-xl font-bold">{plan.name}</CardTitle>
                  <div className="flex items-baseline justify-center space-x-1 mt-2">
                    <span className="text-4xl font-bold text-gray-900">{plan.price}</span>
                    <span className="text-gray-600">{plan.period}</span>
                  </div>
                  <CardDescription className="mt-2">
                    {plan.description}
                  </CardDescription>
                </CardHeader>
                
                <CardContent className="pt-0">
                  <ul className="space-y-3 mb-6">
                    {plan.features.map((feature, featureIndex) => (
                      <li key={featureIndex} className="flex items-center space-x-3">
                        <Check className="w-5 h-5 text-green-600 flex-shrink-0" />
                        <span className="text-sm text-gray-700">{feature}</span>
                      </li>
                    ))}
                  </ul>
                  
                  <Button 
                    className={`w-full ${
                      plan.popular 
                        ? 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700' 
                        : ''
                    }`}
                    variant={plan.popular ? 'default' : 'outline'}
                  >
                    {plan.buttonText}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Feature Comparison */}
          <div className="mt-16 max-w-4xl mx-auto">
            <h3 className="text-2xl font-bold text-center mb-8">Feature Comparison</h3>
            <Card className="border-0 shadow-lg">
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-4 font-medium text-gray-900">Features</th>
                        <th className="text-center p-4 font-medium text-gray-900">Starter</th>
                        <th className="text-center p-4 font-medium text-gray-900 bg-blue-50">Professional</th>
                        <th className="text-center p-4 font-medium text-gray-900">Enterprise</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { feature: 'Monthly DMs', starter: '500', pro: '2,500', enterprise: 'Unlimited' },
                        { feature: 'Connected Accounts', starter: '1', pro: '5', enterprise: 'Unlimited' },
                        { feature: 'AI Personalization', starter: '❌', pro: '✅', enterprise: '✅' },
                        { feature: 'Advanced Analytics', starter: '❌', pro: '✅', enterprise: '✅' },
                        { feature: 'A/B Testing', starter: '❌', pro: '✅', enterprise: '✅' },
                        { feature: 'Priority Support', starter: '❌', pro: '✅', enterprise: '✅' },
                        { feature: 'Custom Integrations', starter: '❌', pro: '❌', enterprise: '✅' },
                      ].map((row, index) => (
                        <tr key={index} className="border-b hover:bg-gray-50">
                          <td className="p-4 font-medium text-gray-900">{row.feature}</td>
                          <td className="p-4 text-center text-gray-700">{row.starter}</td>
                          <td className="p-4 text-center text-gray-700 bg-blue-50">{row.pro}</td>
                          <td className="p-4 text-center text-gray-700">{row.enterprise}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* FAQ Section */}
          <div className="mt-16 max-w-3xl mx-auto">
            <h3 className="text-2xl font-bold text-center mb-8">Frequently Asked Questions</h3>
            <div className="space-y-4">
              {[
                {
                  question: 'Can I change my plan at any time?',
                  answer: 'Yes, you can upgrade or downgrade your plan at any time. Changes take effect immediately.'
                },
                {
                  question: 'Is there a free trial?',
                  answer: 'We offer a 7-day free trial for all plans. No credit card required to get started.'
                },
                {
                  question: 'What happens if I exceed my DM limit?',
                  answer: 'Your campaigns will be paused until the next billing cycle. You can upgrade anytime to continue.'
                },
                {
                  question: 'Do you offer refunds?',
                  answer: 'We offer a 30-day money-back guarantee for all plans. Contact support for assistance.'
                }
              ].map((faq, index) => (
                <Card key={index} className="border-0 shadow-sm">
                  <CardContent className="p-6">
                    <div className="font-medium text-gray-900 mb-2">{faq.question}</div>
                    <div className="text-gray-600">{faq.answer}</div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}