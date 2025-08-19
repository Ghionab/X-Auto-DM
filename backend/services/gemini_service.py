import google.generativeai as genai
import json
import logging
from typing import Dict, List, Optional, Tuple
from flask import current_app

logger = logging.getLogger(__name__)

class GeminiService:
    """Service for interacting with Google Gemini AI"""
    
    def __init__(self):
        self.api_key = current_app.config['GEMINI_API_KEY']
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            logger.warning("Gemini API key not configured")
            self.model = None
    
    def generate_personalized_dm(self, target_profile: Dict, campaign_rules: Dict, 
                                template: str = None) -> Tuple[bool, str]:
        """
        Generate a personalized DM based on target profile and campaign rules
        """
        if not self.model:
            return False, "Gemini AI not configured"
        
        try:
            # Construct the prompt for personalized DM generation
            prompt = self._build_dm_prompt(target_profile, campaign_rules, template)
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                # Clean up the response
                generated_dm = response.text.strip()
                
                # Remove any unwanted formatting
                if generated_dm.startswith('"') and generated_dm.endswith('"'):
                    generated_dm = generated_dm[1:-1]
                
                return True, generated_dm
            else:
                return False, "No response generated"
                
        except Exception as e:
            logger.error(f"Error generating DM with Gemini: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def _build_dm_prompt(self, target_profile: Dict, campaign_rules: Dict, template: str = None) -> str:
        """Build a comprehensive prompt for DM generation"""
        
        # Base context
        prompt = """You are an expert at writing personalized, engaging direct messages for Twitter/X. 
Your goal is to create authentic, human-like messages that feel personal and relevant to the recipient.

IMPORTANT RULES:
- Keep messages under 280 characters (Twitter DM limit)
- Make it feel natural and conversational, not salesy
- Use the recipient's profile information to personalize
- Follow the specific campaign rules provided
- Avoid spam-like language
- Don't use excessive emojis or exclamation marks
- Make it feel like a genuine person reaching out

"""
        
        # Add target profile information
        if target_profile:
            prompt += f"""
TARGET PROFILE INFORMATION:
- Username: @{target_profile.get('username', 'user')}
- Display Name: {target_profile.get('name', 'N/A')}
- Bio: {target_profile.get('bio', 'No bio available')}
- Followers: {target_profile.get('followers_count', 0)}
- Following: {target_profile.get('following_count', 0)}
- Verified: {target_profile.get('verified', False)}

"""
        
        # Add campaign rules
        if campaign_rules:
            prompt += "CAMPAIGN RULES TO FOLLOW:\n"
            
            if 'tone' in campaign_rules:
                prompt += f"- Tone: {campaign_rules['tone']}\n"
            
            if 'purpose' in campaign_rules:
                prompt += f"- Purpose: {campaign_rules['purpose']}\n"
            
            if 'call_to_action' in campaign_rules:
                prompt += f"- Call to Action: {campaign_rules['call_to_action']}\n"
            
            if 'avoid_words' in campaign_rules:
                prompt += f"- Words to Avoid: {', '.join(campaign_rules['avoid_words'])}\n"
            
            if 'include_keywords' in campaign_rules:
                prompt += f"- Keywords to Include: {', '.join(campaign_rules['include_keywords'])}\n"
            
            if 'personalization_focus' in campaign_rules:
                prompt += f"- Personalization Focus: {campaign_rules['personalization_focus']}\n"
            
            if 'additional_instructions' in campaign_rules:
                prompt += f"- Additional Instructions: {campaign_rules['additional_instructions']}\n"
        
        # Add template if provided
        if template:
            prompt += f"""
MESSAGE TEMPLATE/STRUCTURE TO FOLLOW:
{template}

Adapt this template to be personalized for the target profile above.
"""
        
        prompt += """
Now generate a personalized direct message for this person. Return only the message text, nothing else.
The message should feel authentic and be something a real person would send.
"""
        
        return prompt
    
    def analyze_reply_sentiment(self, reply_text: str) -> Tuple[bool, Dict]:
        """
        Analyze the sentiment of a reply message
        """
        if not self.model:
            return False, {"error": "Gemini AI not configured"}
        
        try:
            prompt = f"""
Analyze the sentiment of this Twitter/X direct message reply. Classify it as one of:
- positive: Interested, engaged, asking questions, wants to know more
- negative: Dismissive, angry, uninterested, asking to stop
- neutral: Acknowledges but no clear interest either way

Also provide a brief explanation of why you classified it this way.

Message to analyze: "{reply_text}"

Respond in JSON format:
{{
    "sentiment": "positive/negative/neutral",
    "confidence": 0.0-1.0,
    "explanation": "brief explanation",
    "key_indicators": ["list", "of", "key", "words", "or", "phrases"]
}}
"""
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                try:
                    # Try to parse JSON response
                    result = json.loads(response.text.strip())
                    return True, result
                except json.JSONDecodeError:
                    # Fallback to simple sentiment extraction
                    sentiment = "neutral"
                    if any(word in reply_text.lower() for word in ['yes', 'interested', 'tell me more', 'sounds good', 'love', 'great']):
                        sentiment = "positive"
                    elif any(word in reply_text.lower() for word in ['no', 'stop', 'spam', 'not interested', 'leave me alone']):
                        sentiment = "negative"
                    
                    return True, {
                        "sentiment": sentiment,
                        "confidence": 0.7,
                        "explanation": "Fallback analysis",
                        "key_indicators": []
                    }
            else:
                return False, {"error": "No response generated"}
                
        except Exception as e:
            logger.error(f"Error analyzing sentiment with Gemini: {str(e)}")
            return False, {"error": str(e)}
    
    def generate_follow_up_message(self, original_dm: str, reply: str, 
                                  campaign_rules: Dict, target_profile: Dict) -> Tuple[bool, str]:
        """
        Generate a follow-up message based on the original DM and the reply received
        """
        if not self.model:
            return False, "Gemini AI not configured"
        
        try:
            prompt = f"""
You are having a conversation via Twitter/X direct messages. Generate an appropriate follow-up message based on the conversation history.

ORIGINAL MESSAGE YOU SENT:
"{original_dm}"

THEIR REPLY:
"{reply}"

TARGET PROFILE:
- Username: @{target_profile.get('username', 'user')}
- Bio: {target_profile.get('bio', 'No bio')}

CAMPAIGN RULES:
{json.dumps(campaign_rules, indent=2)}

Generate a natural, conversational follow-up message that:
1. Acknowledges their reply appropriately
2. Continues the conversation naturally
3. Stays under 280 characters
4. Feels authentic and human
5. Moves toward the campaign goal if appropriate

Return only the follow-up message text, nothing else.
"""
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                follow_up = response.text.strip()
                if follow_up.startswith('"') and follow_up.endswith('"'):
                    follow_up = follow_up[1:-1]
                return True, follow_up
            else:
                return False, "No response generated"
                
        except Exception as e:
            logger.error(f"Error generating follow-up with Gemini: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def optimize_campaign_rules(self, campaign_performance: Dict, 
                               current_rules: Dict) -> Tuple[bool, Dict]:
        """
        Analyze campaign performance and suggest optimized rules
        """
        if not self.model:
            return False, {"error": "Gemini AI not configured"}
        
        try:
            prompt = f"""
Analyze this DM campaign performance data and suggest optimizations to the campaign rules.

CURRENT CAMPAIGN PERFORMANCE:
- Messages Sent: {campaign_performance.get('messages_sent', 0)}
- Reply Rate: {campaign_performance.get('reply_rate', 0)}%
- Positive Replies: {campaign_performance.get('positive_replies', 0)}
- Negative Replies: {campaign_performance.get('negative_replies', 0)}
- Average Response Time: {campaign_performance.get('avg_response_time', 'N/A')}

CURRENT CAMPAIGN RULES:
{json.dumps(current_rules, indent=2)}

SAMPLE MESSAGES THAT PERFORMED WELL:
{json.dumps(campaign_performance.get('top_performing_messages', []), indent=2)}

SAMPLE MESSAGES THAT PERFORMED POORLY:
{json.dumps(campaign_performance.get('poor_performing_messages', []), indent=2)}

Based on this data, suggest specific improvements to the campaign rules. Focus on:
1. Tone and messaging adjustments
2. Personalization strategies
3. Call-to-action optimization
4. Timing recommendations
5. Target audience refinements

Respond in JSON format with optimized rules and explanations:
{{
    "optimized_rules": {{
        "tone": "suggested tone",
        "purpose": "refined purpose",
        "call_to_action": "optimized CTA",
        "personalization_focus": "what to focus on",
        "additional_instructions": "specific guidance"
    }},
    "changes_made": [
        {{"rule": "rule_name", "change": "description of change", "reason": "why this change"}}
    ],
    "expected_improvements": "what improvements to expect"
}}
"""
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                try:
                    result = json.loads(response.text.strip())
                    return True, result
                except json.JSONDecodeError:
                    return False, {"error": "Could not parse optimization suggestions"}
            else:
                return False, {"error": "No response generated"}
                
        except Exception as e:
            logger.error(f"Error optimizing campaign with Gemini: {str(e)}")
            return False, {"error": str(e)}
    
    def generate_warmup_content(self, content_type: str, target_profile: Dict = None) -> Tuple[bool, str]:
        """
        Generate content for warmup activities (tweets, replies, etc.)
        """
        if not self.model:
            return False, "Gemini AI not configured"
        
        try:
            if content_type == "tweet":
                prompt = """
Generate a natural, engaging tweet that a real person would post. It should:
- Be under 280 characters
- Sound authentic and human
- Be about general topics like technology, business, lifestyle, or current events
- Not be promotional or spam-like
- Include appropriate hashtags (1-2 max)

Return only the tweet text, nothing else.
"""
            
            elif content_type == "reply":
                prompt = f"""
Generate a natural, engaging reply to a tweet. The reply should:
- Be under 280 characters
- Add value to the conversation
- Sound like a real person's response
- Not be spam-like or promotional
- Be relevant to the original tweet context

Target tweet context: {target_profile.get('tweet_text', 'General discussion') if target_profile else 'General discussion'}

Return only the reply text, nothing else.
"""
            
            else:
                return False, f"Unsupported content type: {content_type}"
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                content = response.text.strip()
                if content.startswith('"') and content.endswith('"'):
                    content = content[1:-1]
                return True, content
            else:
                return False, "No response generated"
                
        except Exception as e:
            logger.error(f"Error generating warmup content with Gemini: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def validate_message_quality(self, message: str, campaign_rules: Dict) -> Tuple[bool, Dict]:
        """
        Validate if a generated message meets quality standards
        """
        if not self.model:
            return True, {"score": 0.5, "issues": ["AI not configured"]}
        
        try:
            prompt = f"""
Evaluate this direct message for quality and compliance with the campaign rules.

MESSAGE TO EVALUATE:
"{message}"

CAMPAIGN RULES:
{json.dumps(campaign_rules, indent=2)}

Rate the message on a scale of 0.0 to 1.0 based on:
1. Adherence to campaign rules (0.3 weight)
2. Natural/human-like tone (0.25 weight)  
3. Personalization quality (0.2 weight)
4. Engagement potential (0.15 weight)
5. Spam/bot detection risk (0.1 weight - lower is better)

Respond in JSON format:
{{
    "overall_score": 0.0-1.0,
    "breakdown": {{
        "rule_adherence": 0.0-1.0,
        "natural_tone": 0.0-1.0,
        "personalization": 0.0-1.0,
        "engagement": 0.0-1.0,
        "spam_risk": 0.0-1.0
    }},
    "issues": ["list of specific issues found"],
    "suggestions": ["list of specific improvements"],
    "approved": true/false
}}
"""
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                try:
                    result = json.loads(response.text.strip())
                    return True, result
                except json.JSONDecodeError:
                    # Fallback simple validation
                    issues = []
                    if len(message) > 280:
                        issues.append("Message too long")
                    if message.count('!') > 2:
                        issues.append("Too many exclamation marks")
                    
                    return True, {
                        "overall_score": 0.7 if len(issues) == 0 else 0.4,
                        "issues": issues,
                        "approved": len(issues) == 0
                    }
            else:
                return False, {"error": "No response generated"}
                
        except Exception as e:
            logger.error(f"Error validating message with Gemini: {str(e)}")
            return False, {"error": str(e)}
