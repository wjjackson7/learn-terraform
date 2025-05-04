import openai
from typing import Dict, Any

def analyze_caption(openai_api_key: str, content: str) -> Dict[str, Any]:
    """
    Analyze the caption content using OpenAI API.
    
    Args:
        openai_api_key: Your OpenAI API key
        content: The content of the caption file to analyze
        
    Returns:
        Dictionary containing the analysis results
    """
    try:
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=openai_api_key)
        
        # Create the analysis prompt
        prompt = f"""You are given with a zooming meeting record transcript in which, Saikat Chakrabarti, who is a politician running for Congress to represent San Francisco, was talking to voters. Please clean the transcript into the format of Questions and Answers, where questions are from voters, and answers are from Saikat Chakrabarti. Please note that it is possible there is no identification in the transcript on who is speaker of each sentence. Please try your best to figure out which sentences are from Saikat, which are from voters. For example:

Question: Do you have any strategy in mind of how to work with other congress people, senators in DC?
Answer: In my view, the focus for 2026 and 2028 will be twofold. I'll do everything possible to stop opponents from gaining control over key assets, like the Presidio, and work to build an exceptional constituent services program. I believe that as your congressperson, my role is to be your chief advocate—helping with issues like interrupted Social Security checks or federal job losses—areas where traditional avenues might fall short.

Please also note that this will be used for Saikat Chakrabarti's own reference. The answer should be written in first person point of view. Please keep the details of the answers, especially the parts that are insightful.

Transcript to analyze:
{content}"""

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes political transcripts and formats them into clear Q&A format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        return {
            "success": True,
            "analysis": response.choices[0].message.content
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        } 