from typing import Optional
from app.services.llm_provider import LLMProvider, get_llm_provider


class ReplyGenerator:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or get_llm_provider()

    async def generate(self, sender: str, subject: Optional[str], body: Optional[str]) -> str:
        """
        Generates contextual reply proposal using safe delimited prompt.
        Never executes any send action.
        """
        delimited_context = (
            f"Sender: {sender}\n"
            f"Subject: {subject or '(No Subject)'}\n"
            f"Body:\n{body or ''}"
        )
        reply = await self.provider.generate_reply(
            email_context=delimited_context,
            instructions="Draft a concise, professional reply acknowledging the sender's points."
        )
        return reply.strip()
