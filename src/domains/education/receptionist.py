"""
Education Receptionist — Tenant- and Scenario-Aware
====================================================
Subclass of BaseReceptionist that, at call start, resolves the active
*tenant* (which school we're calling on behalf of), looks up the parent
record from that tenant's registry, picks the *scenario* the call falls
into (fee_paid_confirmation / fee_partial_reminder / fee_overdue_inquiry
/ admission_inquiry / attendance_followup), and renders a personalised
scenario-specific greeting plus a posture-and-record overlay for the LLM.

The generic education domain owns conversation orchestration; the tenant
module (`src/tenants/<tenant_id>/`) owns the school identity, parent data,
and scenario templates. This separation lets the same domain serve many
schools without duplicating prompt logic — only data and templates change.

Ref: Gamma et al. 1994 (Template Method) [^95];
     "Parent data contract" project memory (2026-04-30);
     ADR-013 (patience), DFS-007 (Suryapet demographic);
     user dialogue 2026-04-30 ("build separate module jayahigh school
     system", "templates that would be for different domains").
"""

from typing import Any, Dict, List, Optional

from src.receptionist.base_receptionist import BaseReceptionist
from src.receptionist.service import CallSession, ReceptionistConfig
from src.receptionist.tools.base import ToolRegistry
from src.domains.education.prompts import build_education_prompt
from src.domains.education.parent_registry import ParentRecord, ParentRegistry


class EducationReceptionist(BaseReceptionist):
    """
    Concrete receptionist for the education domain.
    Pulls tenant-specific data + scenario templates from the active
    Tenant facade (see `src.tenants.get_active_tenant`).
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Resolve the active tenant lazily so dev/test environments
        # without a tenant configured still work via the in-memory
        # ParentRegistry default seed.
        from src.tenants import get_active_tenant

        self._tenant = get_active_tenant()
        if self._tenant is not None:
            self._registry = ParentRegistry(self._tenant.parent_records)
        else:
            self._registry = ParentRegistry()

        self._parent_records: Dict[str, Optional[ParentRecord]] = {}
        self._scenarios: Dict[str, Optional[Any]] = {}
        # Post-intent state machine (Voice Intent Framework, ADR-014).
        #
        #   _intent_satisfied  : True after first caller utterance matching
        #                        scenario.success_signals — primary objective
        #                        confirmed received.
        #   _parent_lingering  : Per-turn: True if THIS turn's caller text
        #                        invites continuation (explicit invitation
        #                        like "anything else", a question, "by the
        #                        way…"). Re-evaluated on every caller turn;
        #                        not sticky across turns.
        #   _pivot_offered     : True after the pivot has been injected into
        #                        a prompt (one-shot, prevents repeat).
        #   _news_offered      : True after the news offer has been injected
        #                        into a prompt (one-shot).
        #
        # GATING (user directive 2026-04-30): post-intent offers only fire
        # when the parent has SIGNALLED they want to continue. Default after
        # intent satisfaction is to close warmly. Pushing pivot/news on a
        # parent who said "thank you, bye" is disrespectful.
        #
        # Sequencing per turn:
        #   intent_satisfied + parent_lingering THIS TURN +
        #     pivot configured + !pivot_offered → inject pivot
        #   intent_satisfied + parent_lingering THIS TURN +
        #     (no pivot OR pivot_offered) + news configured +
        #     !news_offered → inject news_offer
        #   else → normal turn; LLM closes via scenario.closing_line
        self._intent_satisfied: Dict[str, bool] = {}
        self._parent_lingering: Dict[str, bool] = {}
        self._pivot_offered: Dict[str, bool] = {}
        self._news_offered: Dict[str, bool] = {}
        # Mid-call intent switching: when caller shifts topic to a
        # different registered intent, this flag fires for ONE turn so
        # the LLM can gracefully acknowledge the topic shift.
        self._intent_shifted_this_turn: Dict[str, bool] = {}

    # ------------------------------------------------------------------
    # Override: handle_call_start — resolve parent + scenario, then greet.
    # ------------------------------------------------------------------

    async def handle_call_start(
        self, session_id: str, caller: str, called: str
    ) -> str:
        from src.emotion.profile import EmotionWindow
        from src.emotion.state_machine import EmotionStateMachine

        # Look up parent — try `called` (outbound) then `caller` (inbound).
        record = self._registry.lookup(called) or self._registry.lookup(caller)
        self._parent_records[session_id] = record

        # Pick scenario via the tenant; fall back to status-only mapping
        # when no tenant is configured (dev mode).
        scenario = None
        if self._tenant is not None:
            scenario = self._tenant.scenario_for(record)
        self._scenarios[session_id] = scenario

        session = CallSession(
            session_id=session_id,
            caller_number=caller,
            called_number=called,
            emotion_window=EmotionWindow(),
        )
        self.sessions[session_id] = session
        self._emotion_machines[session_id] = EmotionStateMachine()

        # Reset post-intent state machine for this session.
        self._intent_satisfied[session_id] = False
        self._parent_lingering[session_id] = False
        self._pivot_offered[session_id] = False
        self._news_offered[session_id] = False
        self._intent_shifted_this_turn[session_id] = False

        greeting = self._greeting_for(record)
        session.conversation_history.append(
            {"role": "assistant", "content": greeting}
        )
        return greeting

    # Required by ABC — used only when no record is loaded for the session
    # (e.g., a future inbound call before lookup resolves).
    def _greeting_text(self) -> str:
        return self._greeting_for(None)

    def _greeting_for(self, record: Optional[ParentRecord]) -> str:
        """
        Minimal greeting: school identity + consent question. The parent
        name, child name, and call reason are NOT mentioned in the
        greeting — they belong in the scenario opening (the agent's
        SECOND turn, after the parent confirms a good time to talk).

        User directive (2026-04-30): "too many words in the beginning…
        calling from jaya school is this a good time to talk to you
        sir." Greeting is ≤16 words regardless of whether the record
        is loaded.

        DFS-010 Option A: branches on ParentRecord.language_preference
        to use 'Garu' for Telugu-preference parents, 'sir' for English.
        """
        short_name = self.config.company_name.split(",")[0].strip()

        if record is None:
            # No record loaded — generic but still names the topic so
            # the parent knows why this call is happening.
            return (
                f"Namaste sir. Calling from {short_name} about your "
                "child's school fees. Is this a good time to talk, sir?"
            )

        is_telugu = (record.language_preference or "").strip().lower() == "telugu"

        if is_telugu:
            # DFS-011 §2 + user feedback (2026-04-30): Telangana phone
            # register names the call's intent within the greeting itself,
            # not after consent. A real Suryapet school admin opens with
            # name + Garu, then states purpose, then asks consent — in
            # one breath. Code-mixed Telugu-English (Telugu function
            # words + English domain nouns: "fees", "school") is the
            # modal register.
            return (
                f"Namaskaaram {record.parent_name} Garu. "
                f"Nenu {short_name} nundi {record.child_name} fees gurinchi "
                "maatladuthunna. Maatladaniki time undha, Garu?"
            )

        # English-pref: intent stated in greeting too (per same user
        # feedback — context was missing). Aura renders this naturally.
        return (
            f"Namaste sir. From {short_name}, calling about "
            f"{record.child_name}'s school fees. "
            "Is this a good time to talk, sir?"
        )

    # ------------------------------------------------------------------
    # Lingering-signal detection
    # ------------------------------------------------------------------

    # Phrases that explicitly invite continuation. Lower-cased substring
    # match — a single hit flips _parent_lingering=True for this turn.
    _LINGER_INVITATIONS = (
        "anything else",
        "what else",
        "is there more",
        "is there anything",
        "by the way",
        "actually",
        "also",
        "one more thing",
        "any other",
        "tell me more",
        "what's happening",
        "anything happening",
        "any news",
    )
    # Phrases that explicitly close the door — even alongside a question
    # mark, treat as wrap-up. Catches "okay bye?", "is that all then?"
    _LINGER_WRAPUPS = (
        "bye",
        "goodbye",
        "good bye",
        "that's all",
        "thats all",
        "nothing else",
        "no thanks",
        "no thank you",
        "i'll go",
        "have to go",
        "i'm leaving",
        "talk later",
    )

    # ------------------------------------------------------------------
    # Mid-call intent switching
    # ------------------------------------------------------------------

    # When the caller introduces a new topic that maps to a different
    # registered intent, we re-pick the active scenario for the rest of
    # the call. The keyword set is deliberately minimal — false-positives
    # would derail a normal call. Each tuple item must be a substring
    # match against the lower-cased caller transcript.
    _INTENT_SHIFT_KEYWORDS: Dict[str, tuple[str, ...]] = {
        "admission_inquiry": (
            "admission",
            "new admission",
            "enrol",
            "enroll",
            "new student",
            "want to join",
            "looking for school",
            "looking for a school",
            "want to study at",
        ),
        "attendance_followup": (
            "absent",
            "missed school",
            "didn't come to school",
            "did not come to school",
            "couldn't attend",
            "could not attend",
            "not going to school",
            "skipped school",
        ),
    }

    def _detect_intent_shift(
        self, caller_text: str, current_intent_id: Optional[str]
    ) -> Optional[str]:
        """
        Return the intent_id the caller has shifted into, or None if
        the current intent still applies.
        """
        if not caller_text:
            return None
        text = caller_text.lower()
        for new_intent_id, keywords in self._INTENT_SHIFT_KEYWORDS.items():
            if new_intent_id == current_intent_id:
                continue
            if any(kw in text for kw in keywords):
                return new_intent_id
        return None

    @classmethod
    def _is_lingering_signal(cls, caller_text: str) -> bool:
        """
        Decide whether the parent's latest utterance signals interest in
        continuing the call past primary-intent satisfaction. Returns
        True only on EXPLICIT invitation or a non-trivial question;
        defaults to False (the user-respectful default).
        """
        if not caller_text:
            return False
        text = caller_text.lower()

        # Wrap-ups always win — even if combined with an invitation.
        if any(w in text for w in cls._LINGER_WRAPUPS):
            return False

        # Explicit invitations.
        if any(inv in text for inv in cls._LINGER_INVITATIONS):
            return True

        # A question (longer than a trivial "huh?"). The 4-word floor
        # filters fragments like "what?" or "really?" which are
        # back-channels, not invitations.
        words = text.split()
        if "?" in caller_text and len(words) >= 4:
            return True

        return False

    # ------------------------------------------------------------------
    # Override: handle_transcript — detect intent satisfaction +
    # lingering signal, then delegate to the base class.
    # ------------------------------------------------------------------

    async def handle_transcript(
        self, session_id: str, transcript: str
    ) -> str:
        # Default: assume no shift this turn.
        self._intent_shifted_this_turn[session_id] = False

        scenario = self._scenarios.get(session_id)

        # Mid-call intent switch detection (ADR-014 §scenario-stickiness):
        # if the caller introduces a topic that maps to a different
        # registered intent, swap the scenario for the rest of the call
        # and reset post-intent flags so the new intent has its own
        # success/pivot/news state machine.
        if (
            transcript
            and self._tenant is not None
            and scenario is not None
        ):
            new_intent_id = self._detect_intent_shift(transcript, scenario.scenario_id)
            if new_intent_id and new_intent_id in self._tenant.scenarios:
                new_scenario = self._tenant.scenarios[new_intent_id]
                self._scenarios[session_id] = new_scenario
                self._intent_satisfied[session_id] = False
                self._pivot_offered[session_id] = False
                self._news_offered[session_id] = False
                self._intent_shifted_this_turn[session_id] = True
                scenario = new_scenario  # use the new one for this turn's checks

        if scenario is not None and transcript:
            text_lower = transcript.lower()
            # Detect intent satisfaction (one-shot, sticky for the
            # currently-active intent — reset above on a shift).
            if not self._intent_satisfied.get(session_id, False):
                if any(sig in text_lower for sig in scenario.success_signals):
                    self._intent_satisfied[session_id] = True
            # Detect lingering signal (re-evaluated each turn).
            self._parent_lingering[session_id] = self._is_lingering_signal(transcript)
        else:
            self._parent_lingering[session_id] = False
        return await super().handle_transcript(session_id, transcript)

    # ------------------------------------------------------------------
    # Override: _build_messages — inject scenario posture + parent record,
    # and the post-intent pivot hint exactly once when due.
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        session: CallSession,
        today_date: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        record = self._parent_records.get(session.session_id)
        scenario = self._scenarios.get(session.session_id)
        merged_context: Dict[str, Any] = dict(context or {})

        # Decide whether THIS turn should carry a post-intent hint.
        # GATING (user directive 2026-04-30): only fire if the parent
        # has signalled interest in continuing this turn. Default after
        # intent satisfaction is to close warmly — the LLM does that
        # naturally from the scenario's posture + closing_line. We do
        # NOT push pivot/news on a parent who said "thank you, bye".
        pivot_hint = ""
        news_offer_hint = ""
        news_block = ""

        if (
            scenario is not None
            and self._intent_satisfied.get(session.session_id, False)
            and self._parent_lingering.get(session.session_id, False)
            and record is not None
        ):
            pivot_configured = scenario.post_intent_pivot is not None
            news_configured = scenario.post_intent_news_offer is not None
            already_pivoted = self._pivot_offered.get(session.session_id, False)
            already_news = self._news_offered.get(session.session_id, False)

            if pivot_configured and not already_pivoted:
                pivot_text = scenario.render_pivot(record)
                if pivot_text:
                    pivot_hint = pivot_text
                    self._pivot_offered[session.session_id] = True
            elif (
                news_configured
                and not already_news
                and (not pivot_configured or already_pivoted)
            ):
                news_text = scenario.render_news_offer(record)
                if news_text:
                    news_offer_hint = news_text
                    self._news_offered[session.session_id] = True
                    # Pull the relevant news block from the tenant's
                    # school_news layer; it scopes to the child's class.
                    try:
                        from src.tenants.jaya_high_school.school_news import (
                            render_news_block,
                        )
                        news_block = render_news_block(record.child_class)
                    except Exception:
                        news_block = ""

        # Intent-shift hint (one-shot per shift turn): instruct the LLM
        # to gracefully acknowledge the topic change before engaging
        # with the new scenario's posture.
        intent_shift_hint = ""
        if self._intent_shifted_this_turn.get(session.session_id, False) and scenario is not None:
            intent_shift_hint = (
                "The parent has just shifted the topic of the call to "
                f"'{scenario.scenario_id.replace('_', ' ')}'. In your next "
                "reply, briefly acknowledge the shift in your own natural "
                "words (≤8 words, e.g. 'Of course sir, let me help with that'), "
                "then engage with the new scenario's posture as outlined above."
            )

        if self._tenant is not None:
            merged_context["parent_block"] = self._tenant.render_prompt_overlay(
                record,
                scenario,
                pivot_hint=pivot_hint,
                news_offer_hint=news_offer_hint,
                news_block=news_block,
                intent_shift_hint=intent_shift_hint,
            )
        elif record is not None:
            merged_context["parent_block"] = record.to_prompt_block()

        return build_education_prompt(
            company_name=self.config.company_name,
            hours_text=self.config.hours_text,
            today_date=today_date,
            conversation_history=session.conversation_history,
            context=merged_context,
        )

    # ------------------------------------------------------------------
    # Override: handle_call_end — purge per-session caches.
    # ------------------------------------------------------------------

    async def handle_call_end(self, session_id: str) -> CallSession:
        self._parent_records.pop(session_id, None)
        self._scenarios.pop(session_id, None)
        self._intent_satisfied.pop(session_id, None)
        self._parent_lingering.pop(session_id, None)
        self._pivot_offered.pop(session_id, None)
        self._news_offered.pop(session_id, None)
        self._intent_shifted_this_turn.pop(session_id, None)
        return await super().handle_call_end(session_id)

    # ------------------------------------------------------------------
    # Public surface for pipeline introspection
    # ------------------------------------------------------------------

    def session_has_record(self, session_id: str) -> bool:
        """
        Whether this session has a verified parent record loaded.
        The pipeline uses this to choose a higher dynamic-budget floor
        for no-record sessions (so the agent has room to be informative
        like "I don't have the latest record here, may I take your
        child's name?" — a 14-word turn that 6 words cannot fit).
        """
        return self._parent_records.get(session_id) is not None

    def session_language_preference(self, session_id: str) -> str:
        """
        Return the parent's language preference for this session, or ""
        if no record is loaded. Used by `TTSRouter` (ADR-019) to route
        each synthesis call to the appropriate TTS provider — Bulbul
        for `"Telugu"`, Aura (default) otherwise.
        """
        record = self._parent_records.get(session_id)
        if record is None:
            return ""
        return (record.language_preference or "").strip()


# References
# - "Parent data contract" project memory (2026-04-30).
# - ADR-009 / ADR-013, DFS-007.
# [^95]: Gamma et al. 1994 (Template Method).
