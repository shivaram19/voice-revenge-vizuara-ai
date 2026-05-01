"""
Sentence Aggregator for Streaming TTS
Ref: SigArch 2026, Section 4.5; Pipecat SentenceAggregator pattern.

Bridges streaming LLM tokens with sentence-level TTS synthesis.
"""

import re
from typing import Iterator, Optional
from dataclasses import dataclass


@dataclass
class Sentence:
    text: str
    is_complete: bool = True


class SentenceAggregator:
    """
    Accumulates LLM tokens until a complete sentence is detected.
    
    Rules (from production literature):
    1. Detect sentence-ending punctuation: . ! ?
    2. Exclude abbreviations: Dr. Mr. Mrs. Ms. Prof. etc.
    3. Exclude decimal numbers: 3.14, 2.5
    4. Minimum length: 10 characters (avoid fragments)
    5. Flush remainder on stream end
    """
    
    # Common abbreviations that end with period but aren't sentence terminators
    ABBREVIATIONS = {
        'dr', 'mr', 'mrs', 'ms', 'prof', 'sr', 'jr', 'st', 'ave', 'blvd',
        'rd', 'no', 'vol', 'vols', 'inc', 'ltd', 'jr', 'sr', 'co', 'corp',
        'plc', 'llc', 'llp', 'etc', 'eg', 'ie', 'vs', 'ft', 'mt', 'pt'
    }
    
    SENTENCE_END_RE = re.compile(r'[.!?]+\s+')
    MIN_LENGTH = 10
    
    def __init__(self):
        self._buffer = ""
    
    def ingest(self, token: str) -> Iterator[Sentence]:
        """
        Ingest a token. Yields complete sentences when detected.
        
        Args:
            token: Next LLM output token (may be partial word)
            
        Yields:
            Sentence objects when a complete sentence is formed.
        """
        self._buffer += token
        
        # Check if buffer contains sentence boundary
        while len(self._buffer) >= self.MIN_LENGTH:
            match = self.SENTENCE_END_RE.search(self._buffer)
            if not match:
                # End-of-buffer check: if buffer ends with terminal punctuation
                # and sufficient length, yield as complete sentence.
                stripped = self._buffer.strip()
                if len(stripped) >= self.MIN_LENGTH and stripped[-1] in '.!?' \
                   and not self._is_abbreviation_at_end(stripped):
                    yield Sentence(text=stripped, is_complete=True)
                    self._buffer = ""
                break
                
            end_pos = match.end()
            candidate = self._buffer[:end_pos].strip()
            
            # Check if the period belongs to an abbreviation
            if self._is_abbreviation_at_position(self._buffer, match.start(), match.end()):
                # Remove space after period so regex won't match here again
                # Preserve prefix: "Meet Dr. Smith" -> "Meet Dr.Smith"
                self._buffer = self._buffer[:match.end()-1] + self._buffer[match.end():]
                continue
            
            # Valid sentence found
            yield Sentence(text=candidate, is_complete=True)
            self._buffer = self._buffer[end_pos:]
    
    def flush(self) -> Optional[Sentence]:
        """
        Flush remaining buffer (call when LLM stream ends).
        Returns remaining text as sentence if non-empty.
        """
        remainder = self._buffer.strip()
        self._buffer = ""
        if remainder:
            return Sentence(text=remainder, is_complete=False)
        return None
    
    def reset(self):
        """Reset buffer (e.g., on barge-in)."""
        self._buffer = ""
    
    def _is_abbreviation_at_end(self, text: str) -> bool:
        """
        Check if the terminal punctuation at the end of text is part of
        an abbreviation or decimal.
        """
        # Check for decimal: digit on both sides of the period
        if len(text) >= 3:
            if text[-2].isdigit() and text[-3].isdigit():
                return True
        
        # Check for abbreviation: word before terminal period
        word_match = re.search(r'(\w+)\s*[.!?]+\s*$', text)
        if word_match:
            word = word_match.group(1).lower()
            if word in self.ABBREVIATIONS:
                return True
        
        return False
    
    def _is_abbreviation_at_position(self, text: str, match_start: int, match_end: int) -> bool:
        """
        Check if the period at the matched position is part of an abbreviation or decimal.
        
        Args:
            text: The full buffer text
            match_start: Start position of the matched punctuation+space
            match_end: End position of the matched punctuation+space
        """
        # The period is at position match_end - 2 (before the whitespace)
        period_pos = match_end - 2
        if period_pos < 0:
            return False
        
        # Check for decimal: digit on both sides of the period
        if period_pos > 0 and period_pos + 1 < len(text):
            left_char = text[period_pos - 1]
            right_char = text[period_pos + 1]
            if left_char.isdigit() and right_char.isdigit():
                return True
        
        # Check for abbreviation: word before period
        # Extract word immediately preceding the period
        word_match = re.search(r'(\w+)\s*' + re.escape(text[period_pos:period_pos+1]) + r'\s*$', text[:match_end])
        if word_match:
            word = word_match.group(1).lower()
            if word in self.ABBREVIATIONS:
                return True
        
        return False


# References
# [^3]: Gandhi, S., et al. (2023). Distil-Whisper: Robust Knowledge Distillation via Large-Scale Pseudo Labelling. arXiv:2311.00430.
# [^7]: Kim, J., et al. (2021). Conditional Variational Autoencoder with Adversarial Learning for End-to-End Text-to-Speech. ICML.
# [^16]: SigArch. (2026). Building Enterprise Realtime Voice Agents from Scratch. arXiv:2603.05413.

# ---------------------------------------------------------------------------
# Example usage & validation
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    aggregator = SentenceAggregator()
    
    # Simulate streaming LLM tokens
    tokens = [
        "The weather in Seattle",
        " is 62 degrees",
        " Fahrenheit.",
        " It will",
        " rain later",
        " in the evening.",
        " Dr. Smith",
        " says so."
    ]
    
    print("Streaming sentence aggregation demo:")
    print("-" * 50)
    
    for token in tokens:
        for sentence in aggregator.ingest(token):
            print(f"[COMPLETE] {sentence.text}")
    
    # Flush remainder
    remainder = aggregator.flush()
    if remainder:
        print(f"[REMAINDER] {remainder.text}")
    
    # Test abbreviation handling
    print("\n" + "-" * 50)
    print("Abbreviation test:")
    agg2 = SentenceAggregator()
    tokens2 = ["Meet Dr. Smith at 3.14 pm.", " He is nice."]
    for token in tokens2:
        for sentence in agg2.ingest(token):
            print(f"[COMPLETE] {sentence.text}")
