"""Tests for query speaker intent classifier."""

from kuzu_memory.recall.query_classifier import SpeakerIntent, classify_speaker_intent


class TestUserTurnClassification:
    def test_what_did_i_say(self) -> None:
        assert classify_speaker_intent("What did I say about Python?") == SpeakerIntent.USER_TURN

    def test_i_mentioned(self) -> None:
        assert (
            classify_speaker_intent("I mentioned earlier that I prefer async")
            == SpeakerIntent.USER_TURN
        )

    def test_do_you_remember_i_said(self) -> None:
        assert (
            classify_speaker_intent("Do you remember when I said I was using FastAPI?")
            == SpeakerIntent.USER_TURN
        )

    def test_my_question(self) -> None:
        assert (
            classify_speaker_intent("What was my question about database locking?")
            == SpeakerIntent.USER_TURN
        )

    def test_when_i_asked(self) -> None:
        assert (
            classify_speaker_intent("When did I ask about the migration strategy?")
            == SpeakerIntent.USER_TURN
        )

    def test_something_i_mentioned(self) -> None:
        assert (
            classify_speaker_intent("Something I mentioned about testing frameworks")
            == SpeakerIntent.USER_TURN
        )


class TestAssistantTurnClassification:
    def test_what_did_you_say(self) -> None:
        assert (
            classify_speaker_intent("What did you say about database design?")
            == SpeakerIntent.ASSISTANT_TURN
        )

    def test_your_recommendation(self) -> None:
        assert (
            classify_speaker_intent("What was your recommendation for the API framework?")
            == SpeakerIntent.ASSISTANT_TURN
        )

    def test_you_suggested(self) -> None:
        assert (
            classify_speaker_intent("You suggested using Pydantic earlier")
            == SpeakerIntent.ASSISTANT_TURN
        )

    def test_did_you_recommend(self) -> None:
        assert (
            classify_speaker_intent("Did you recommend any testing libraries?")
            == SpeakerIntent.ASSISTANT_TURN
        )

    def test_what_you_said(self) -> None:
        assert (
            classify_speaker_intent("What you said about async patterns earlier")
            == SpeakerIntent.ASSISTANT_TURN
        )

    def test_your_advice(self) -> None:
        assert (
            classify_speaker_intent("Your advice on error handling") == SpeakerIntent.ASSISTANT_TURN
        )


class TestUnspecifiedClassification:
    def test_generic_topic_query(self) -> None:
        assert classify_speaker_intent("Python async patterns") == SpeakerIntent.UNSPECIFIED

    def test_tell_me_about(self) -> None:
        assert (
            classify_speaker_intent("Tell me about database indexing") == SpeakerIntent.UNSPECIFIED
        )

    def test_how_does(self) -> None:
        assert classify_speaker_intent("How does HNSW indexing work?") == SpeakerIntent.UNSPECIFIED

    def test_what_is(self) -> None:
        assert (
            classify_speaker_intent("What is the best approach for memory management?")
            == SpeakerIntent.UNSPECIFIED
        )

    def test_empty_string(self) -> None:
        assert classify_speaker_intent("") == SpeakerIntent.UNSPECIFIED

    def test_both_patterns_match_returns_unspecified(self) -> None:
        # Ambiguous: both user ("I asked") and assistant ("what you recommended") patterns match
        result = classify_speaker_intent("I asked about what you recommended for the database")
        assert result == SpeakerIntent.UNSPECIFIED


class TestCaseInsensitivity:
    def test_uppercase(self) -> None:
        assert classify_speaker_intent("WHAT DID I SAY ABOUT PYTHON?") == SpeakerIntent.USER_TURN

    def test_mixed_case(self) -> None:
        assert classify_speaker_intent("What Did You Recommend?") == SpeakerIntent.ASSISTANT_TURN


class TestSpeakerIntentEnum:
    """Verify enum values match source_speaker field values stored in Memory nodes."""

    def test_user_turn_value(self) -> None:
        assert SpeakerIntent.USER_TURN.value == "user"

    def test_assistant_turn_value(self) -> None:
        assert SpeakerIntent.ASSISTANT_TURN.value == "assistant"

    def test_unspecified_value(self) -> None:
        assert SpeakerIntent.UNSPECIFIED.value == "unspecified"

    def test_all_values_distinct(self) -> None:
        values = [si.value for si in SpeakerIntent]
        assert len(values) == len(set(values)), "SpeakerIntent values must be distinct"
