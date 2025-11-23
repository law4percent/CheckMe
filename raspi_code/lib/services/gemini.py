"""Gemini Service - Integration with Google Gemini API"""

import os
import google.generativeai as genai
import logging

logger = logging.getLogger(__name__)


client = genai.Client()

response = client.models.generate_content(
    model="gemini-3-pro-preview",
    contents="Explain how AI works in a few words",
)

print(response.text)

exit()






class GeminiService:
    """Service for interacting with Google Gemini API"""
    
    def __init__(self):
        """Initialize Gemini client with API key from environment"""
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model_name = os.getenv('GEMINI_MODEL')
        self.max_tokens = int(os.getenv('GEMINI_MAX_TOKENS', '1000'))
        self.temperature = float(os.getenv('GEMINI_TEMPERATURE', '0.3'))
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be set in environment variables")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        
        logger.info(f"Initialized Gemini service with model: {self.model_name}")
    
    
    def health_check(self) -> bool:
        """Check if Gemini API is accessible
        
        Returns:
            True if accessible, False otherwise
        """
        try:
            # Just check if API key is configured and model is initialized
            # Don't make actual API call to save RPD quota
            return self.model is not None and self.api_key is not None
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return False
    
    
    
    def _create_formatting_prompt(self, ticket_number: str, title: str, 
                                   background: str, expected_behavior: str,
                                   function: str, description: str) -> str:
        """Create the prompt for Gemini to format the ticket
        
        Args:
            ticket_number: Jira ticket number
            title: Ticket title
            background: Background information
            expected_behavior: Expected behavior
            function: Function details
            description: Ticket description
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a technical documentation assistant helping to format Jira release tickets for Slack.

Given the following Jira ticket information, please reformat it into three clear sections following this exact format:

*Ticket Overview:*
[Provide a concise summary of what this ticket is about, combining the title and background]

*Target Functionality:*
[Describe the expected behavior and functionality that will be implemented, based on the expected behavior and function fields]

*Potential Risks:*
[Identify any potential technical risks or areas that need review. If no specific risks can be determined from the ticket, use: "To be confirmed by reviewers (Sakamoto-san, Park-san)"]

Here is the ticket information:

Ticket: {ticket_number}
Title: {title}
Background: {background or description}
Expected Behavior: {expected_behavior}
Function: {function}

Please provide the formatted output in the exact format shown above, keeping it professional and concise. Use clear, technical language appropriate for a development team.
"""
        return prompt
    