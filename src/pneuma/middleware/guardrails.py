from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from fastapi import HTTPException

class SecurityGuardrail:
    def __init__(self):
        print("[Guardrail] Initializing local NLP engines for PII detection...")
        # We load this locally so no sensitive data is ever sent to a third-party API for scanning
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        # A basic heuristic list for immediate blocking. 
        # In a real prod environment, this is replaced by a quantized DistilBERT model.
        self.toxic_keywords = ["hack the database", "bypass security", "ignore previous instructions", "system prompt"]

    def check_toxicity(self, text: str) -> None:
        """Instantly rejects malicious or jailbreak prompts."""
        text_lower = text.lower()
        for keyword in self.toxic_keywords:
            if keyword in text_lower:
                print(f"[Guardrail] WARNING: Malicious intent detected: '{keyword}'")
                raise HTTPException(
                    status_code=403, 
                    detail="Request blocked by enterprise security policy: Malicious intent detected."
                )

    def scrub_pii(self, text: str) -> str:
        """Detects and redacts sensitive information."""
        # Analyze the text for specific entities
        results = self.analyzer.analyze(
            text=text,
            entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "US_SSN"],
            language='en'
        )
        
        if not results:
            return text
            
        # Anonymize the found entities
        anonymized_result = self.anonymizer.anonymize(text=text, analyzer_results=results)
        scrubbed_text = anonymized_result.text
        
        print(f"[Guardrail] PII Redacted. Original length: {len(text)}, Scrubbed length: {len(scrubbed_text)}")
        return scrubbed_text
        
    def process_input(self, text: str) -> str:
        """The main pipeline: Check for toxicity, then scrub PII."""
        self.check_toxicity(text)
        return self.scrub_pii(text)