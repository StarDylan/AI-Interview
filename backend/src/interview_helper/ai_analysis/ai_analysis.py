from collections.abc import Sequence
from langchain_core.callbacks import BaseCallbackHandler
from interview_helper.config import Settings
from interview_helper.context_manager.database import (
    PersistentDatabase,
    get_all_transcripts,
)
from interview_helper.context_manager.types import AIJob, AIResult
from langchain_openai import AzureChatOpenAI
from langchain.agents import create_agent
from pydantic import BaseModel
from textwrap import dedent
import logging

"""Simple interview analyzer with LLM."""

logger = logging.getLogger(__name__)


class Analysis(BaseModel):
    questions: list[str]


class SimpleAnalyzer:
    """Simple LLM-based interview analyzer."""

    SYSTEM_PROMPT: str = dedent("""\
        You will be given a chunk of a transcript from an in-depth profile interview for a Search and Rescue
        operation.

        Your goal is to suggest good questions to the interview that would help uncover important details about the person being interviewed.

        Please make sure you read and understand these instructions carefully. Please keep this document open while reviewing, and refer to it as needed.

        Question Generation Steps:
        1. Read the provided transcript chunks carefully.
        2. Identify the current topic(s) of the conversation (be sure to prioritize recency).
        3. Based on the identified topic(s), generate follow-up questions that would help uncover important details about:
              - Mindset and intent
              - Mobility and ability to travel
              - Ability to survive
              - Ability to communicate
              - Ability or willingness to respond
              - Likes and dislikes, and what attracts the person's attention
              - Past and recent behaviors and life history
        4. Ensure that the questions are open-ended and encourage detailed responses.
        5. Ensure questions aren't already answered / implied in the transcript.
        6. Only respond with your top 3 most relevant and insightful questions.
    """)

    def __init__(self, config: Settings, db: PersistentDatabase):
        llm = AzureChatOpenAI(
            azure_endpoint=config.azure_api_endpoint,
            api_key=config.azure_api_key,
            api_version=config.azure_api_version,
            azure_deployment=config.azure_deployment,
        )

        self.llm = create_agent(  # pyright: ignore[reportUnannotatedClassAttribute, reportUnknownMemberType]
            llm, response_format=Analysis, system_prompt=self.SYSTEM_PROMPT
        )

        self.db: PersistentDatabase = db

    async def analyze(
        self, job: AIJob, callbacks: Sequence[BaseCallbackHandler] | None = None
    ) -> AIResult:
        """Analyze a chunk and return suggestions.

        Args:
            chunk_text: The formatted transcript chunk
            previous_context: Summary of previous chunks

        Returns:
            Analysis and suggestions from the LLM
        """

        logger.info("Running Simple AI Analyzer")

        interview_transcript = " ".join(get_all_transcripts(self.db, job.project_id))

        prompt = dedent(f"""\
            Current interview:
            {interview_transcript}

            Analyze this and identify any important questions that should have been asked but weren't.\
        """)

        response = await self.llm.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
            {"callbacks": list(callbacks) if callbacks is not None else None},
        )

        analysis: Analysis = response["structured_response"]

        return AIResult(text=analysis.questions)


class FakeAnalyzer:
    """Fake analyzer that doesn't do any actual analysis."""

    SYSTEM_PROMPT = dedent("""\
        You are a helpful assistant tasked with helping an in-depth profile interview for a search-and-rescue operation.

        Your primary goals are to help the interviewer uncover pertinent details about:
        - Mindset and intent
        - Mobility and ability to travel
        - Ability to survive
        - Ability to communicate
        - Ability or willingness to respond
        - Likes and dislikes, and what attracts the person's attention
        - Past and recent behaviors and life history

        The person who is answering questions is directing the interview and you are there to assist if you spot anything that might have been MISESED.
    """)

    def __init__(self, config: Settings, db: PersistentDatabase):
        self.db = db

    async def analyze(
        self, job: AIJob, callbacks: Sequence[BaseCallbackHandler] | None = None
    ) -> AIResult:
        _ = callbacks  # We don't use callbacks
        return AIResult(
            text=[
                f"I am a dummy analyzer..., here is my input I got:\n {' '.join(get_all_transcripts(self.db, job.project_id))}"
            ]
        )
