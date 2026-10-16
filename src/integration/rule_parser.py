"""Offline stand-in for S5's LLM parser.

Produces the same JSON intent as ``src/reasoning/query_parser.py`` so the pipeline, the smoke
test and CI run on machines without Ollama. It is deliberately simple: the real demo uses the
local LLM; this only covers the sentence shapes in S5's prompt examples.
"""

import re

ADJECTIVES = {
    "free", "occupied", "red", "blue", "green", "yellow", "black", "white", "grey", "gray",
    "orange", "purple", "brown", "pink", "small", "big", "large", "empty", "full", "open", "closed",
}
STOPWORDS = {
    "which", "what", "where", "is", "are", "the", "a", "an", "find", "show", "me", "that", "to",
    "go", "pick", "up", "move", "bring", "get", "locate", "please", "there", "it", "of", "s",
    "object", "objects", "thing", "item", "can", "you", "i", "my", "for", "one",
}
GENERIC = {"object", "objects", "thing", "item", "something"}

_NEG = re.compile(r"\b(?:not|isn't|isnt|never|without being)\s+(?:the\s+)?(near|next to|close to|on|under|beside)"
                  r"\s+(?:the\s+|a\s+|an\s+)?([a-z][a-z ]*?)(?=$|\s+(?:and|but|that|which)\b)")
_FAR = re.compile(r"\bfar\s+from\s+(?:the\s+|a\s+|an\s+)?([a-z][a-z ]*?)(?=$|\s+(?:and|but|that|which)\b)")
_CLOSEST = re.compile(r"\b(?:closest|nearest)\s+(?:to\s+)?(?:the\s+|a\s+|an\s+)?([a-z][a-z ]*?)"
                      r"(?=$|\s+(?:and|but|that|which)\b)")


def parse_query(question: str, model=None) -> dict:
    text = re.sub(r"[^a-z' ]", " ", question.lower())
    text = re.sub(r"\s+", " ", text).strip()
    parsed = {"intent": "find_object", "target": "", "reference": "", "relations": [],
              "positive_constraints": [], "negative_constraints": []}

    for m in _NEG.finditer(text):
        rel = m.group(1).replace(" ", "_")
        parsed["negative_constraints"].append({"relation": "near" if rel in ("next_to", "close_to", "beside") else rel,
                                               "object": m.group(2).strip()})
    text = _NEG.sub(" ", text)
    for m in _FAR.finditer(text):
        parsed["negative_constraints"].append({"relation": "near", "object": m.group(1).strip()})
    text = _FAR.sub(" ", text)
    m = _CLOSEST.search(text)
    if m:
        parsed["reference"] = m.group(1).strip()
        parsed["relations"].append("closest_to")
        text = text[:m.start()]

    words = [w for w in text.replace("'", " ").split() if w not in STOPWORDS]
    parsed["positive_constraints"] = [w for w in words if w in ADJECTIVES]
    nouns = [w for w in words if w not in ADJECTIVES]
    if nouns and nouns[-1] not in GENERIC:
        parsed["target"] = nouns[-1]
    return parsed
