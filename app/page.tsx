'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ArrowRight, MessageCircle, Users, TrendingUp, Shield, Zap, Target } from 'lucide-react';
import Link from 'next/link';

export default function Home() {
  const [hoveredFeature, setHoveredFeature] = useState<number | null>(null);

  const features = [
    {
      icon: MessageCircle,
      title: 'AI-Powered DMs',
      description: 'Generate personalized messages using advanced AI that converts 3x better than generic templates.'
    },
    {
      icon: Users,
      title: 'Smart Targeting',
      description: 'Automatically scrape and identify high-value prospects from competitor followers and industry leaders.'
    },
    {
      icon: TrendingUp,
      title: 'Real-time Analytics',
      description: 'Track reply rates, engagement metrics, and ROI with comprehensive dashboard analytics.'
    },
    {
      icon: Shield,
      title: 'Safe & Compliant',
      description: 'Built-in rate limiting and compliance features to keep your account safe from restrictions.'
    },
    {
      icon: Zap,
      title: 'Automation',
      description: 'Set up campaigns once and let our system handle the outreach while you focus on closing deals.'
    },
    {
      icon: Target,
      title: 'High Conversion',
      description: 'Our users see 40%+ reply rates with AI-personalized messages tailored to each prospect.'
    }
  ];

  return (
    <div className="flex flex-col min-h-screen bg-[var(--bg-page)]">
      {/* Navigation */}
      <header className="border-b border-[var(--border-subtle)] bg-[var(--bg-card)] sticky top-0 z-50">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-[var(--accent-gold-primary)] rounded-lg flex items-center justify-center">
                <MessageCircle className="w-5 h-5 text-[var(--text-inverted)]" />
              </div>
              <span className="text-xl font-bold text-[var(--text-primary)]">
                X DM Pro
              </span>
            </div>
            <nav className="hidden md:flex space-x-8">
              <a href="#features" className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">Features</a>
              <a href="#pricing" className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">Pricing</a>
              <a href="#contact" className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">Contact</a>
            </nav>
            <div className="flex items-center space-x-4">
              <Link href="/login">
                <Button className="btn-secondary-gold">Sign In</Button>
              </Link>
              <Link href="/register">
                <Button className="btn-primary-gold">
                  Sign Up
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="flex-1 container mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center space-y-8">
          <div className="space-y-4">
            <Badge className="badge-pill-gold">
              🚀 Now with AI-powered personalization
            </Badge>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-[var(--text-primary)]">
              Automate Your{' '}
              <span className="text-[var(--accent-gold-secondary)]">
                Twitter DM
              </span>{' '}
              Campaigns
            </h1>
            <p className="text-lg sm:text-xl text-[var(--text-secondary)] max-w-3xl mx-auto leading-relaxed">
              Leverage AI to send personalized DMs at scale. Generate leads, build relationships, and grow your business with intelligent automation that feels human.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/register">
              <Button size="lg" className="btn-primary-gold px-8">
                Get Started
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </Link>
            <Button size="lg" className="btn-secondary-gray">
              Watch Demo
            </Button>
          </div>

          <div className="pt-12">
            <div className="text-sm text-[var(--text-secondary)] mb-6">Trusted by 2,500+ businesses</div>
            <div className="flex items-center justify-center space-x-8 opacity-60">
              <div className="text-2xl font-bold text-[var(--text-secondary)]">TechCorp</div>
              <div className="text-2xl font-bold text-[var(--text-secondary)]">StartupXYZ</div>
              <div className="text-2xl font-bold text-[var(--text-secondary)]">GrowthCo</div>
              <div className="text-2xl font-bold text-[var(--text-secondary)]">ScaleUp</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 bg-[var(--bg-card)]">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold mb-4 text-[var(--text-primary)]">
              Everything you need to scale your outreach
            </h2>
            <p className="text-lg text-[var(--text-secondary)] max-w-2xl mx-auto">
              From AI-powered personalization to comprehensive analytics, we've built the complete solution for Twitter DM automation.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <Card 
                  key={index}
                  className="bg-[var(--bg-page)] border border-[var(--border-subtle)] hover:border-[var(--accent-gold-secondary)] transition-all duration-300 cursor-pointer"
                  onMouseEnter={() => setHoveredFeature(index)}
                  onMouseLeave={() => setHoveredFeature(null)}
                >
                  <CardHeader className="pb-4">
                    <div className={`w-12 h-12 rounded-lg flex items-center justify-center mb-4 transition-all duration-300 ${
                      hoveredFeature === index 
                        ? 'bg-[var(--accent-gold-primary)] text-[var(--text-inverted)] scale-110' 
                        : 'bg-[var(--border-subtle)] text-[var(--accent-gold-secondary)]'
                    }`}>
                      <Icon className="w-6 h-6" />
                    </div>
                    <CardTitle className="text-xl text-[var(--text-primary)]">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="text-[var(--text-secondary)] leading-relaxed">
                      {feature.description}
                    </CardDescription>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-20 bg-[var(--bg-page)] border-y border-[var(--border-subtle)]">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
            <div className="space-y-2">
              <div className="text-4xl font-bold text-[var(--accent-gold-secondary)]">40%+</div>
              <div className="text-[var(--text-secondary)]">Average Reply Rate</div>
            </div>
            <div className="space-y-2">
              <div className="text-4xl font-bold text-[var(--accent-gold-secondary)]">2.5M+</div>
              <div className="text-[var(--text-secondary)]">DMs Sent Successfully</div>
            </div>
            <div className="space-y-2">
              <div className="text-4xl font-bold text-[var(--accent-gold-secondary)]">99.9%</div>
              <div className="text-[var(--text-secondary)]">Uptime Guarantee</div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-[var(--bg-card)] border-t border-[var(--border-subtle)] py-12">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center space-x-2 mb-4 md:mb-0">
              <div className="w-8 h-8 bg-[var(--accent-gold-primary)] rounded-lg flex items-center justify-center">
                <MessageCircle className="w-5 h-5 text-[var(--text-inverted)]" />
              </div>
              <span className="text-xl font-bold text-[var(--text-primary)]">X DM Pro</span>
            </div>
            <div className="text-[var(--text-secondary)] text-sm">
              © 2025 X DM Pro. All rights reserved.
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}