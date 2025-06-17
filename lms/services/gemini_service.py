import google.generativeai as genai
import os
import logging
import time
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self, model_name='gemini-1.5-flash-latest'):
        """Initialize the Gemini Service."""
        try:
            # Configure API key
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable is required.")
            
            genai.configure(api_key=api_key)
            self.model_name = model_name
            self._model = genai.GenerativeModel(self.model_name)
            logger.info(f"GeminiService initialized with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Model ({self.model_name}): {e}", exc_info=True)
            raise

    def generate_review(self, prompt_text: str, safety_settings=None, generation_config=None, retries=2) -> Optional[str]:
        """
        Generates content using the configured Gemini model.
        
        Args:
            prompt_text: The complete prompt to send to the Gemini API.
            safety_settings: Optional safety settings.
            generation_config: Optional generation config (temperature, max_tokens etc).
            retries: Number of retries for rate limiting.
        
        Returns:
            The generated text content as a string, or None if an error occurs.
        """
        for attempt in range(retries + 1):
            try:
                logger.debug(f"Sending prompt to Gemini ({self.model_name}):\n{prompt_text[:200]}...")

                # Prepare optional configurations
                kwargs = {}
                if safety_settings:
                    kwargs['safety_settings'] = safety_settings
                if generation_config:
                    kwargs['generation_config'] = generation_config

                # Call the API
                response = self._model.generate_content(prompt_text, **kwargs)

                # Basic check on response structure
                if response and hasattr(response, 'text'):
                    logger.debug(f"Received Gemini response (first 100 chars): {response.text[:100]}")
                    return response.text
                elif response and response.prompt_feedback:
                    # Handle cases where content is blocked
                    logger.warning(f"Gemini content generation blocked. Feedback: {response.prompt_feedback}")
                    return f"I apologize, but I cannot provide a response to that request due to safety guidelines. Please try rephrasing your question about courses."
                else:
                    logger.error(f"Received unexpected or empty response from Gemini API. Response: {response}")
                    return "I'm sorry, but I encountered an issue processing your request. Please try again."

            except Exception as e:
                logger.error(f"Gemini API call failed (attempt {attempt + 1}): {e}", exc_info=True)
                
                # Handle rate limiting with exponential backoff
                if "rate limit" in str(e).lower() and attempt < retries:
                    wait_time = (2 ** attempt) + 1  # Exponential backoff: 2, 5, 9 seconds
                    logger.info(f"Rate limited, waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                
                # Final attempt or non-rate-limit error
                if attempt == retries:
                    return "I'm experiencing technical difficulties right now. Please try again in a moment."

        return "I'm sorry, but I'm temporarily unavailable. Please try again later."

    def create_course_guidance_prompt(self, user_message: str, available_courses: list, user_history: list = None) -> str:
        """
        Creates a prompt for Gemini to provide course guidance to students.
        
        Args:
            user_message: The student's question or message
            available_courses: List of available courses with details
            user_history: Previous conversation history for context
        
        Returns:
            Formatted prompt for the AI
        """
        # Format course information
        courses_info = ""
        for course in available_courses:
            courses_info += f"""
**Course: {course.get('title', 'N/A')}**
- Category: {course.get('category', 'N/A')}
- Description: {course.get('description', 'N/A')}
- Instructor: {course.get('teacher', 'N/A')}
- Price: {course.get('price', 'Free')} KZT
- Students Enrolled: {course.get('enrollment_count', 0)}
"""

        # Format conversation history
        history_context = ""
        if user_history:
            history_context = "\n**Previous Conversation:**\n"
            for msg in reversed(user_history[-3:]):  # Last 3 exchanges for context
                history_context += f"Student: {msg.message}\nAI: {msg.response}\n\n"

        prompt = f"""
You are an AI Course Advisor for an online Learning Management System (LMS). Your role is to help students choose the most suitable courses based on their interests, goals, and background.

**Your Personality:**
- Friendly, helpful, and encouraging
- Knowledgeable about education and learning paths
- Ask clarifying questions when needed
- Provide specific course recommendations with clear explanations

**Available Courses:**
{courses_info}

{history_context}

**Current Student Message:**
"{user_message}"

**Instructions:**
1. Analyze the student's message to understand their learning goals, interests, or questions
2. If the message is unclear, ask specific follow-up questions about:
   - Their current skill level
   - Their career goals
   - Their preferred learning style
   - Time availability
   - Budget considerations

3. When recommending courses:
   - Explain WHY each course fits their needs
   - Mention specific benefits they'll gain
   - Suggest a learning path if multiple courses are relevant
   - Be honest about prerequisites or difficulty levels

4. Keep responses conversational, helpful, and encouraging
5. If they ask about topics not covered by available courses, acknowledge this and suggest the closest alternatives
6. Always end with a question to continue the conversation or offer to help further

**Response Guidelines:**
- Keep responses under 300 words
- Use bullet points for course recommendations
- Be specific about course benefits
- Maintain an encouraging, educational tone
- Don't make up information about courses not in the list

Please provide a helpful response to guide this student:
"""
        return prompt

    def get_course_guidance(self, user_message: str, available_courses: list, user_history: list = None) -> str:
        """
        Generate AI guidance for course selection.
        
        Args:
            user_message: Student's question or message
            available_courses: List of available courses
            user_history: Previous conversation history
        
        Returns:
            AI response with course guidance
        """
        prompt = self.create_course_guidance_prompt(user_message, available_courses, user_history)
        
        # Configure generation parameters for course guidance
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,  # Balanced creativity and consistency
            max_output_tokens=1024,  # Reasonable response length
        )
        
        return self.generate_review(prompt, generation_config=generation_config) 