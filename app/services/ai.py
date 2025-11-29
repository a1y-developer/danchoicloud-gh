from google import genai
from google.genai import types
from app.core.config import settings

class AIService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = 'gemini-3-pro-preview'

    async def generate_pr_summary(self, diff: str) -> str:
        system_instruction = """
        You are an expert software engineer.
        Review the provided git diff and provide a comprehensive summary of the changes.
        
        Structure your response exactly as follows:

        ## Pull request overview

        [Brief paragraph summarizing the overall purpose of the changes (what is new, what is improved, what is fixed).]

        **Key Changes:**
        - [Bulleted list of high-level architectural or feature changes]
        - [Bulleted list of high-level architectural or feature changes]

        ### Reviewed changes

        <details>
        <summary>Show a summary per file</summary>

        | File | Description |
        | ---- | ----------- |
        | `path/to/file` | Brief description of changes in this file |
        | `path/to/another/file` | Brief description of changes in this file |

        </details>

        Rules:
        1. The "Pull request overview" section should provide a high-level summary.
        2. The "Key Changes" section should highlight major architectural or feature updates.
        3. The "Reviewed changes" section MUST use a markdown table inside a `<details>` block.
        4. In the table, list EVERY changed file found in the diff.
        5. Keep file descriptions concise (under 15 words).
        6. Use backticks for file paths in the table.
        """
        
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=f"Diff:\n{diff[:30000]}", # Truncate if too long
            config=types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
        return response.text

    async def review_code(self, diff: str) -> str:
        system_instruction = """
        You are an expert code reviewer. 
        Identify potential bugs, security issues, and performance improvements.
        Provide the review in markdown format.
        """
        
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=f"Review the following git diff:\n{diff[:30000]}",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
        return response.text

    async def generate_inline_suggestions(self, code_snippet: str, context: str = "") -> str:
        system_instruction = """
        You are an expert developer.
        Provide a better implementation for the following code snippet.
        Only provide the code block with the suggestion, no explanations.
        """
        
        user_content = f"""
        Context: {context}
        Code:
        {code_snippet}
        """

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
        return response.text

ai_service = AIService()
