from __future__ import annotations

import os

from app.rag.models import Chunk


class BedrockConverseLLM:
    """AWS Bedrock adapter. It is optional; local runs default to DeterministicLLM."""

    def __init__(self, model_id: str, region: str = "us-east-1") -> None:
        import boto3
        self.model_id = model_id
        self.client = boto3.client("bedrock-runtime", region_name=region)

    def generate(self, question: str, chunks: list[Chunk]) -> str:
        context = "\n\n".join(f"[S{i}] {c.text}" for i, c in enumerate(chunks, 1))
        prompt = (
            "Answer the question using only the supplied evidence. Every factual sentence "
            "must end with one or more evidence markers such as [S1]. If the evidence is "
            "insufficient, say INSUFFICIENT_EVIDENCE.\n\n"
            f"Question: {question}\n\nEvidence:\n{context}"
        )
        response = self.client.converse(
            modelId=self.model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"temperature": 0.0, "maxTokens": 700},
        )
        return response["output"]["message"]["content"][0]["text"].strip()


def build_llm(provider: str, model_name: str, region: str):
    if provider.lower() == "bedrock":
        return BedrockConverseLLM(model_name, region)
    from app.llm.demo import DeterministicLLM
    return DeterministicLLM()
