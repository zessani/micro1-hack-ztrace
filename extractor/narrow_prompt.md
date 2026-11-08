You are checking one thing in a pull-request summary that a coding agent wrote after finishing a task. Judge only what the summary says. Do not judge whether it is true, and do not guess.

Question: {question}

Return only a JSON object:
{"answer": "yes" | "no" | "not_stated", "quote": string{method_field}}

- "yes": the summary states or clearly implies it.
- "no": the summary states the opposite.
- "not_stated": the summary doesn't address it, or only addresses it too vaguely to answer.
- For "yes" or "no", "quote" must be copied exactly from the summary, at least 5 words long or a full sentence, and must itself support the answer. If you can't quote support, answer "not_stated" with "quote": "".
{method_rule}
PR summary:
<<<
{summary}
>>>
