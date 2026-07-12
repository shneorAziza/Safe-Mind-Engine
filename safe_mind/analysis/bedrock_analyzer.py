import json

from safe_mind.analysis.heuristic_analyzer import analyze_with_heuristics
from safe_mind.analysis.models import PsychologicalAnalysisResult
from safe_mind.analysis.openai_analyzer import SYSTEM_PROMPT
from safe_mind.bedrock_runtime import BedrockClaudeMessagesClient, BedrockRuntimeClient


class BedrockPsychologicalAnalyzer:
    def __init__(
        self,
        *,
        model: str,
        region: str,
        client: BedrockRuntimeClient | None = None,
    ) -> None:
        self.model = model
        self.region = region
        self.client = BedrockClaudeMessagesClient(model=model, region=region, client=client)

    def analyze(
        self,
        text: str,
        *,
        allow_fallback: bool = True,
    ) -> PsychologicalAnalysisResult:
        try:
            content = self.client.complete_json(
                system_prompt=SYSTEM_PROMPT.replace('"provider": "openai"', '"provider": "bedrock"'),
                user_content=json.dumps({"redacted_text": text}, ensure_ascii=False),
            )
            result = PsychologicalAnalysisResult.model_validate_json(content)
            return result.model_copy(
                update={"features": result.features.model_copy(update={"provider": "bedrock"})}
            )
        except Exception:
            if not allow_fallback:
                raise
            return analyze_with_heuristics(text)
