from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import httpx
import json
import logging
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class LLMResponse(BaseModel):
    text: str
    raw_response: Dict[str, Any]
    model: str
    usage: Optional[Dict[str, Any]] = None


class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        pass


class HuggingFaceProvider(LLMProvider):
    def __init__(self, api_key: str, model_id: str):
        self.api_key = api_key
        self.model_id = model_id
        self.base_url = "https://router.huggingface.co/v1"
        # Do not keep an AsyncClient across event loops.
        # Render/demo execution can create separate event loops.


    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        if response_format:
            payload["response_format"] = response_format

        url = f"{self.base_url}/chat/completions"

        try:
            # Create the client inside the current event loop.
            # This prevents "Event loop is closed" when the provider is reused
            # across separate asyncio.run() calls.
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=30.0),
                follow_redirects=True,
            ) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            return LLMResponse(
                text=content,
                raw_response=data,
                model=self.model_id,
                usage=data.get("usage"),
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"HF API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"HF generation error: {e}")
            raise

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        response_format = {"type": "json_object"} if schema else None

        if schema:
            schema_prompt = f"\n\nYou MUST respond with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
            prompt = prompt + schema_prompt

        response = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )

        try:
            return json.loads(response.text)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}. Attempting repair.")
            repaired = self._repair_json(response.text)
            return json.loads(repaired)

    def _repair_json(self, text: str) -> str:
        text = text.strip()

        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        open_braces = text.count("{")
        close_braces = text.count("}")
        if open_braces > close_braces:
            text += "}" * (open_braces - close_braces)

        open_brackets = text.count("[")
        close_brackets = text.count("]")
        if open_brackets > close_brackets:
            text += "]" * (open_brackets - close_brackets)

        return text

    async def close(self):
        # HTTP clients are scoped to individual generate() calls.
        pass


class MockLLMProvider(LLMProvider):
    """Mock provider for testing without API keys. Extracts values from prompt text."""

    def __init__(self):
        self.model_id = "mock-model"

    def _extract_values_from_prompt(self, prompt: str) -> dict:
        """Extract key values from prompt text (which contains document chunks)."""
        values = {
            "cap_percentage": None,
            "basket_amount": None,
            "survival_months": None,
            "mae_exceptions": [],
            "termination_conditions": [],
            "closing_conditions": [],
            "has_ip_rep": False,
        }

        # Extract cap percentage: "15%", "20%", "15.0%", etc.
        cap_matches = re.findall(r'(\d+(?:\.\d+)?)\s*%\s*(?:of\s*(?:the\s*)?Purchase Price|Cap|liability cap)', prompt, re.IGNORECASE)
        if cap_matches:
            values["cap_percentage"] = float(cap_matches[0])

        # Extract basket amount: "$500,000", "$250,000", "500000", "250000"
        basket_matches = re.findall(r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:\(?Basket\)?|basket threshold|indemnification threshold)', prompt, re.IGNORECASE)
        if basket_matches:
            values["basket_amount"] = float(basket_matches[0].replace(',', ''))
        else:
            # Try alternative pattern
            basket_matches = re.findall(r'(?:Basket|basket).*?(?:exceeds?|over)\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', prompt, re.IGNORECASE)
            if basket_matches:
                values["basket_amount"] = float(basket_matches[0].replace(',', ''))

        # Extract survival period: "18 months", "24 months", "1.5 years", etc.
        survival_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:months?|years?)', prompt, re.IGNORECASE)
        for m in survival_matches:
            val = float(m)
            if val <= 3:  # likely years
                values["survival_months"] = int(val * 12)
            elif 6 <= val <= 36:  # likely months
                values["survival_months"] = int(val)
                break

        # Extract MAE exceptions
        if 'pandemic' in prompt.lower():
            values["mae_exceptions"].append("pandemics")
        if 'regulatory change' in prompt.lower():
            values["mae_exceptions"].append("regulatory changes")
        if 'general economic' in prompt.lower():
            values["mae_exceptions"].append("general economic conditions")
        if 'industry' in prompt.lower() and 'change' in prompt.lower():
            values["mae_exceptions"].append("industry changes")
        if 'act of war' in prompt.lower() or 'terrorism' in prompt.lower():
            values["mae_exceptions"].append("acts of war")
        if 'natural disaster' in prompt.lower():
            values["mae_exceptions"].append("natural disasters")

        # Extract termination conditions
        if '30 day' in prompt.lower() or 'thirty day' in prompt.lower():
            values["termination_conditions"].append("breach not cured within 30 days")
        if 'material breach' in prompt.lower():
            values["termination_conditions"].append("material breach of representations")
        if 'mae occurred' in prompt.lower() and 'continuing' in prompt.lower():
            values["termination_conditions"].append("MAE occurred and continuing")

        # Extract closing conditions
        if 'representation' in prompt.lower() and 'true' in prompt.lower():
            values["closing_conditions"].append("representations true and correct")
        if 'seller perform' in prompt.lower():
            values["closing_conditions"].append("seller performed obligations")
        if 'no mae' in prompt.lower() or 'no material adverse' in prompt.lower():
            values["closing_conditions"].append("no MAE")
        if 'regulatory approval' in prompt.lower():
            values["closing_conditions"].append("regulatory approvals received")

        # Check for IP representation
        if 'intellectual property' in prompt.lower() and ('own' in prompt.lower() or 'represent' in prompt.lower()):
            values["has_ip_rep"] = True

        return values

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        return LLMResponse(
            text='{"document_type": "SPA", "confidence": 0.9, "reason": "Mock classification", "governing_entities": [], "source_metadata": {}}',
            raw_response={},
            model=self.model_id,
        )

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        values = self._extract_values_from_prompt(prompt)

        # Check more specific prompts first
        if "verify" in prompt_lower:
            pos_count = len(re.findall(r'position \d+', prompt_lower))
            if pos_count == 0:
                pos_count = 1
            verifications = []
            for i in range(pos_count):
                verifications.append({
                    "position_index": i,
                    "status": "VERIFIED",
                    "field_verifications": {
                        "party": "VERIFIED",
                        "percentage": "VERIFIED",
                        "unit": "VERIFIED",
                        "qualifier": "VERIFIED",
                        "consequence": "VERIFIED",
                    },
                    "discrepancies": [],
                    "notes": "Mock verification passed",
                })
            return {"verifications": verifications}

        elif "extract" in prompt_lower or "position" in prompt_lower:
            cap_pct = values["cap_percentage"] or 15.0
            basket_amt = values["basket_amount"] or 500000.0
            survival_mo = values["survival_months"] or 18
            mae_exceptions = values["mae_exceptions"] or ["general economic conditions", "industry changes", "acts of war", "natural disasters"]
            termination_cond = values["termination_conditions"] or ["breach not cured within 30 days", "material breach of representations"]
            closing_cond = values["closing_conditions"] or ["representations true and correct", "seller performed obligations", "no MAE"]
            has_ip = values["has_ip_rep"]

            positions = [
                {
                    "category": "Indemnification",
                    "subcategory": "General Liability Cap",
                    "provision_name": "General Liability Cap",
                    "party": "Seller",
                    "obligation_right": "liability limitation",
                    "threshold": None,
                    "amount": None,
                    "percentage": cap_pct,
                    "unit": "percent",
                    "duration": None,
                    "condition": [],
                    "exception": ["fraud", "willful misconduct"],
                    "qualifier": ["aggregate"],
                    "consequence": [f"liability limited to {cap_pct}% of purchase price"],
                    "evidence": {
                        "document_id": "mock-doc",
                        "page_number": 1,
                        "section_number": "3.3",
                        "heading": "Limitation of Liability",
                        "text": f"the aggregate liability of Seller under this Agreement shall not exceed {cap_pct}% of the Purchase Price (the \"Cap\"). The foregoing Cap shall not apply to liability arising from fraud or willful misconduct.",
                        "char_start": 1000,
                        "char_end": 1200,
                    },
                    "confidence": 0.95,
                    "status": "VERIFIED",
                },
                {
                    "category": "Indemnification",
                    "subcategory": "Basket",
                    "provision_name": "Basket",
                    "party": "Seller",
                    "obligation_right": "indemnification threshold",
                    "threshold": str(int(basket_amt)),
                    "amount": basket_amt,
                    "percentage": None,
                    "unit": "USD",
                    "duration": None,
                    "condition": [],
                    "exception": [],
                    "qualifier": ["basket"],
                    "consequence": [f"no indemnification obligation until losses exceed ${basket_amt:,.0f}"],
                    "evidence": {
                        "document_id": "mock-doc",
                        "page_number": 1,
                        "section_number": "3.4",
                        "heading": "Basket",
                        "text": f"Seller shall have no obligation to indemnify Buyer for any Losses unless and until the aggregate amount of such Losses exceeds ${basket_amt:,.0f} (the \"Basket\")",
                        "char_start": 1200,
                        "char_end": 1350,
                    },
                    "confidence": 0.93,
                    "status": "VERIFIED",
                },
                {
                    "category": "Representations & Warranties",
                    "subcategory": "Survival Period",
                    "provision_name": "Survival Period",
                    "party": "Seller",
                    "obligation_right": "survival of representations",
                    "threshold": None,
                    "amount": None,
                    "percentage": None,
                    "unit": None,
                    "duration": f"{survival_mo} months",
                    "condition": [],
                    "exception": [],
                    "qualifier": [],
                    "consequence": [f"representations survive closing for {survival_mo} months"],
                    "evidence": {
                        "document_id": "mock-doc",
                        "page_number": 1,
                        "section_number": "3.1",
                        "heading": "Survival",
                        "text": f"The representations and warranties of Seller contained in this Agreement shall survive the Closing for a period of {survival_mo} months (the \"Survival Period\").",
                        "char_start": 800,
                        "char_end": 950,
                    },
                    "confidence": 0.94,
                    "status": "VERIFIED",
                },
                {
                    "category": "Material Adverse Effect",
                    "subcategory": "MAE Definition",
                    "provision_name": "Material Adverse Effect Definition",
                    "party": "Unknown",
                    "obligation_right": "MAE definition",
                    "threshold": None,
                    "amount": None,
                    "percentage": None,
                    "unit": None,
                    "duration": None,
                    "condition": [],
                    "exception": mae_exceptions,
                    "qualifier": [],
                    "consequence": ["defines what constitutes a Material Adverse Effect"],
                    "evidence": {
                        "document_id": "mock-doc",
                        "page_number": 1,
                        "section_number": "5.1",
                        "heading": "Material Adverse Effect",
                        "text": "\"Material Adverse Effect\" means any change, event, or effect that, individually or in the aggregate, has or would reasonably be expected to have a material adverse effect on the business, assets, or financial condition of Target, except that the following shall not constitute a Material Adverse Effect: " + "; ".join(mae_exceptions) + ".",
                        "char_start": 1500,
                        "char_end": 1800,
                    },
                    "confidence": 0.91,
                    "status": "VERIFIED",
                },
                {
                    "category": "Termination Rights",
                    "subcategory": "Termination",
                    "provision_name": "Termination Rights",
                    "party": "Buyer",
                    "obligation_right": "termination right",
                    "threshold": None,
                    "amount": None,
                    "percentage": None,
                    "unit": None,
                    "duration": None,
                    "condition": termination_cond,
                    "exception": [],
                    "qualifier": [],
                    "consequence": ["Buyer may terminate agreement"],
                    "evidence": {
                        "document_id": "mock-doc",
                        "page_number": 1,
                        "section_number": "4.1",
                        "heading": "Termination",
                        "text": "This Agreement may be terminated at any time prior to the Closing: (b) by Buyer if any representation or warranty of Seller is untrue in any material respect and such breach is not cured within 30 days",
                        "char_start": 1350,
                        "char_end": 1500,
                    },
                    "confidence": 0.90,
                    "status": "VERIFIED",
                },
                {
                    "category": "Closing Conditions",
                    "subcategory": "Closing Conditions",
                    "provision_name": "Closing Conditions",
                    "party": "Buyer",
                    "obligation_right": "condition precedent",
                    "threshold": None,
                    "amount": None,
                    "percentage": None,
                    "unit": None,
                    "duration": None,
                    "condition": closing_cond,
                    "exception": [],
                    "qualifier": [],
                    "consequence": ["Buyer not obligated to close if conditions not met"],
                    "evidence": {
                        "document_id": "mock-doc",
                        "page_number": 1,
                        "section_number": "6.1",
                        "heading": "Conditions to Obligations of Buyer",
                        "text": "The obligation of Buyer to consummate the Closing is subject to the satisfaction of the following conditions: " + "; ".join(closing_cond) + ".",
                        "char_start": 1800,
                        "char_end": 2000,
                    },
                    "confidence": 0.92,
                    "status": "VERIFIED",
                }
            ]

            # Add IP representation if detected
            if has_ip:
                positions.append({
                    "category": "Representations & Warranties",
                    "subcategory": "Intellectual Property",
                    "provision_name": "Intellectual Property",
                    "party": "Target",
                    "obligation_right": "IP ownership representation",
                    "threshold": None,
                    "amount": None,
                    "percentage": None,
                    "unit": None,
                    "duration": None,
                    "condition": [],
                    "exception": [],
                    "qualifier": [],
                    "consequence": ["Target owns all IP rights necessary for its business"],
                    "evidence": {
                        "document_id": "mock-doc",
                        "page_number": 1,
                        "section_number": "2.1(d)",
                        "heading": "Intellectual Property",
                        "text": "Target represents that it owns all right, title, and interest in and to the Intellectual Property used in the Business.",
                        "char_start": 2000,
                        "char_end": 2200,
                    },
                    "confidence": 0.88,
                    "status": "VERIFIED",
                })

            return {"positions": positions}

        elif "classif" in prompt_lower:
            return {
                "document_type": "SPA",
                "confidence": 0.9,
                "reason": "Mock classification - document contains share purchase agreement language",
                "governing_entities": ["Seller", "Buyer"],
                "source_metadata": {},
            }

        elif "provision" in prompt_lower or "identif" in prompt_lower:
            values = self._extract_values_from_prompt(prompt)
            cap_pct = values["cap_percentage"] or 15.0
            basket_amt = values["basket_amount"] or 500000.0
            survival_mo = values["survival_months"] or 18

            provisions = [
                {
                    "category": "Indemnification",
                    "subcategory": "General Liability Cap",
                    "provision_name": "General Liability Cap",
                    "section_number": "3.3",
                    "heading": "Limitation of Liability",
                    "text": f"the aggregate liability of Seller under this Agreement shall not exceed {cap_pct}% of the Purchase Price (the \"Cap\"). The foregoing Cap shall not apply to liability arising from fraud or willful misconduct.",
                    "page_number": 1,
                    "party_mentioned": ["Seller"],
                    "keywords": ["liability", "cap", "purchase price", "aggregate"],
                },
                {
                    "category": "Indemnification",
                    "subcategory": "Basket",
                    "provision_name": "Basket",
                    "section_number": "3.4",
                    "heading": "Basket",
                    "text": f"Seller shall have no obligation to indemnify Buyer for any Losses unless and until the aggregate amount of such Losses exceeds ${basket_amt:,.0f} (the \"Basket\")",
                    "page_number": 1,
                    "party_mentioned": ["Seller"],
                    "keywords": ["basket", "indemnification", "losses", "threshold"],
                },
                {
                    "category": "Representations & Warranties",
                    "subcategory": "Survival Period",
                    "provision_name": "Survival Period",
                    "section_number": "3.1",
                    "heading": "Survival",
                    "text": f"The representations and warranties of Seller contained in this Agreement shall survive the Closing for a period of {survival_mo} months (the \"Survival Period\").",
                    "page_number": 1,
                    "party_mentioned": ["Seller"],
                    "keywords": ["survival", "representations", "warranties", f"{survival_mo} months"],
                },
            ]
            return {"provisions": provisions}

        return {}


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.hf_api_key and settings.hf_api_key != "your_huggingface_api_key_here":
        return HuggingFaceProvider(settings.hf_api_key, settings.hf_model_id)
    return MockLLMProvider()