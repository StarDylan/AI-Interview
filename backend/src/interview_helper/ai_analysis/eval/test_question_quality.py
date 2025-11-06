from deepeval import assert_test
from deepeval.metrics.g_eval import Rubric
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics import GEval

from deepeval.models import AzureOpenAIModel
from ulid import ULID

from interview_helper.ai_analysis.ai_analysis import SimpleAnalyzer
from interview_helper.context_manager.database import (
    PersistentDatabase,
    add_transcription,
)
from interview_helper.context_manager.types import AIJob, ProjectId, SessionId, UserId
from interview_helper.config import Settings

import pytest

pytestmark = pytest.mark.anyio


@pytest.fixture
def model():
    settings = Settings()  # pyright: ignore[reportCallIssue]
    return AzureOpenAIModel(
        model_name=settings.azure_eval_deployment,
        deployment_name=settings.azure_eval_deployment,
        azure_openai_api_key=settings.azure_api_key.get_secret_value(),
        openai_api_version=settings.azure_api_version,
        azure_endpoint=settings.azure_api_endpoint,
    )


@pytest.mark.llm
async def test_question_quality(model: AzureOpenAIModel):
    correctness_metric = GEval(
        name="Question Quality",
        evaluation_steps=[
            "Read the provided transcript and carefully consider the topic of the conversation.",
            "Read the follow-up question(s) generated and determine if they focus on a relevant area we are interested in: mobility/ability to travel, ability to survive, \
            ability to communicate, ability/willingness to respond, likes/dislikes, what attracts the person's\
            attention, past and recent behaviors, or life history",
            "You should heavily penalize questions that are not succinct and to the point",
            "Check that the question(s) are relevant and aren't already answered in the context",
        ],
        rubric=[
            Rubric(
                score_range=(0, 2),
                expected_outcome="Questions completely irrelevant to the current conversation and/or already asked/answered and/or too long or vague.",
            ),
            Rubric(
                score_range=(3, 6),
                expected_outcome="Some questions are relevant but too long or vague.",
            ),
            Rubric(
                score_range=(7, 9),
                expected_outcome="Mostly relevant and succinct questions.",
            ),
            Rubric(
                score_range=(10, 10),
                expected_outcome="100% relevant, succinct, and on point follow-up question.",
            ),
        ],
        threshold=8.0,
        evaluation_params=[
            LLMTestCaseParams.ACTUAL_OUTPUT,
        ],
        model=model,
    )

    with open("transcript1.txt", "r") as f:
        transcript = f.read()

    config = Settings()  # pyright: ignore[reportCallIssue] (using env)
    db = PersistentDatabase.new_in_memory()

    user = UserId(ULID())
    session = SessionId(ULID())
    project = ProjectId(ULID())
    # Add transcripts

    # chunk transcript by 10 lines
    transcript_chunks = [
        "\n".join(transcript.split("\n")[i : i + 10])
        for i in range(0, len(transcript.split("\n")), 10)
    ][:10]

    # Choose first 10 chunks
    for chunk in transcript_chunks:
        _ = add_transcription(db, user, session, project, chunk)

    ai_analyzer = SimpleAnalyzer(config, db)

    follow_up_questions = await ai_analyzer.analyze(AIJob(project), [])

    question_text = "\n".join(follow_up_questions.text)

    test_case = LLMTestCase(
        input="\n".join(transcript_chunks),
        # Replace this with the actual output from your LLM application
        actual_output=question_text,
    )
    assert_test(test_case, [correctness_metric])


# Create another metric that deals with how likely the interviewer is to use the question
