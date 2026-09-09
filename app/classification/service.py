import json
import logging
import asyncio
from typing import List
from app.llm.provider import get_llm_provider, LLMProvider
from app.models.schemas import ClassificationResult, DocumentType
from prompts import CLASSIFICATION_SYSTEM_PROMPT, CLASSIFICATION_USER_PROMPT

logger = logging.getLogger(__name__)


class ClassificationService:
    def __init__(self, llm: LLMProvider = None):
        self.llm = llm or get_llm_provider()

    async def classify(self, text: str) -> ClassificationResult:
        prompt = CLASSIFICATION_USER_PROMPT.format(text=text[:8000])

        schema = {
            "type": "object",
            "properties": {
                "document_type": {"type": "string", "enum": [e.value for e in DocumentType]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "reason": {"type": "string"},
                "governing_entities": {"type": "array", "items": {"type": "string"}},
                "source_metadata": {"type": "object"},
            },
            "required": ["document_type", "confidence", "reason"],
        }

        try:
            result = await self.llm.generate_structured(
                prompt=prompt,
                system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
                schema=schema,
                temperature=0.1,
                max_tokens=1024,
            )

            doc_type_str = result.get("document_type", "Unknown")
            try:
                doc_type = DocumentType(doc_type_str)
            except ValueError:
                doc_type = DocumentType.UNKNOWN

            return ClassificationResult(
                document_type=doc_type,
                confidence=float(result.get("confidence", 0.0)),
                reason=result.get("reason", ""),
                governing_entities=result.get("governing_entities", []),
                source_metadata=result.get("source_metadata", {}),
            )
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return ClassificationResult(
                document_type=DocumentType.UNKNOWN,
                confidence=0.0,
                reason=f"Classification error: {str(e)}",
            )

    def classify_sync(self, text: str) -> ClassificationResult:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.classify(text))
                return future.result()
        else:
            return asyncio.run(self.classify(text))