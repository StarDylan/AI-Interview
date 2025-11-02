from deepeval.metrics import TaskCompletionMetric
from deepeval.models import AzureOpenAIModel
from deepeval.integrations.langchain import CallbackHandler
from deepeval.dataset import EvaluationDataset, Golden

from interview_helper.config import Settings
from interview_helper.ai_analysis.ai_analysis import SimpleAnalyzer
from interview_helper.context_manager.database import PersistentDatabase
from interview_helper.context_manager.session_context_manager import (
    GLOBAL_PROJECT,
    AIAnalyzer,
)
from interview_helper.context_manager.types import AIJob

from anyio import run

settings = Settings()  # pyright: ignore[reportCallIssue] (env vars)


def get_model():
    return AzureOpenAIModel(
        model_name=settings.azure_deployment,
        deployment_name=settings.azure_deployment,
        azure_openai_api_key=str(settings.azure_api_key),
        openai_api_version=settings.azure_api_version,
        azure_endpoint=settings.azure_api_endpoint,
        temperature=0,
    )


db = PersistentDatabase.new_in_memory()

models: list[AIAnalyzer] = [SimpleAnalyzer(settings, db)]


async def eval():
    eval_model = get_model()

    task_completion_metric = TaskCompletionMetric(model=eval_model)

    callbacks = [CallbackHandler(metrics=[task_completion_metric])]

    dataset = EvaluationDataset(
        goldens=[Golden(input="Provide good questions to ask.")]
    )

    # Loop through dataset
    for test_model in models:
        for _golden in dataset.evals_iterator():
            _ = await test_model.analyze(job=AIJob(GLOBAL_PROJECT), callbacks=callbacks)


if __name__ == "__main__":
    run(eval)
