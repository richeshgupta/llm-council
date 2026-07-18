"""Prompt builders for council stages."""

from __future__ import annotations

from typing import Any


ADVISOR_SYSTEM_PROMPT = """You are one advisor in an LLM Council.
Answer the user's question directly.
Do not modify files.
Do not run commands.
Do not ask follow-up questions unless the question is impossible to answer safely.
Return only the answer content."""


def build_stage1_prompt(user_query: str) -> str:
    return user_query


def build_stage2_prompt(user_query: str, stage1_results: list[dict[str, Any]]) -> tuple[str, dict[str, str]]:
    labels = [chr(65 + i) for i in range(len(stage1_results))]
    label_to_model = {
        f"Response {label}": result["model"]
        for label, result in zip(labels, stage1_results)
    }
    responses_text = "\n\n".join(
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    )

    prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example:

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""
    return prompt, label_to_model


def build_stage3_prompt(
    user_query: str,
    stage1_results: list[dict[str, Any]],
    stage2_results: list[dict[str, Any]],
    aggregate_rankings: list[dict[str, Any]] | None = None,
) -> str:
    stage1_text = "\n\n".join(
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    )
    stage2_text = "\n\n".join(
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage2_results
    )
    aggregate_text = ""
    if aggregate_rankings:
        aggregate_text = "\n\nAGGREGATE RANKINGS:\n" + "\n".join(
            f"- {item['model']}: average rank {item['average_rank']} ({item['rankings_count']} votes)"
            for item in aggregate_rankings
        )

    return f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}{aggregate_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement
- Useful minority views that may be important even if they are lower-ranked

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""


def build_title_prompt(user_query: str) -> str:
    return f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

