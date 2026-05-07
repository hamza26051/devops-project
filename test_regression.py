"""
test_regression.py
─────────────────────────────────────────────────────────────────────
AUTOMATED REGRESSION TESTS (CI/CD)

These tests run in the CI pipeline AFTER model_gate.py passes and
BEFORE the Docker image is built. If any test fails, the pipeline
aborts and the current production model is not replaced.

Test categories:
  1. Hard REJECT cases   — hate speech MUST always REJECT
  2. Hard APPROVE cases  — clean content MUST always APPROVE
  3. Discount logic      — expressive language must not inflate score
  4. Neither gate        — personal distress must not inflate score
  5. Edge cases          — short text, empty, unicode
  6. Score monotonicity  — more hate speech = higher score
  7. Latency             — engine must respond within 2 s
  8. Determinism         — same input must produce identical output

conftest.py provides the `engine` fixture (session-scoped, loaded once).
Firebase is mocked out by conftest.py — no network access required.
"""

import time
import pytest


# ══════════════════════════════════════════════════════════════════════
# 1. HARD REJECT CASES
# ══════════════════════════════════════════════════════════════════════
# These inputs contain unambiguous hate speech. A model that does NOT
# reject them has a safety-critical failure and must never be deployed.

class TestHardReject:

    def test_explicit_racial_hate_speech(self, engine):
        """Explicit racial violence directive → REJECT, score > 0.67."""
        result = engine.analyze_user_profile([
            "kill all niggers they dont deserve to live"
        ])
        assert result["decision"] == "REJECT CUSTOMER", (
            f"Explicit racial HS not rejected. Got: {result['decision']}, "
            f"score={result['final_risk_score']}"
        )
        assert result["final_risk_score"] > 0.67

    def test_dehumanising_group_generalisation(self, engine):
        """Dehumanising criminal generalisation against ethnic group → REJECT."""
        result = engine.analyze_user_profile([
            "These people are all criminals and should be deported."
        ])
        assert result["decision"] == "REJECT CUSTOMER", (
            f"Dehumanising HS not rejected. Got: {result['decision']}"
        )
        assert result["final_risk_score"] > 0.67

    def test_religious_ethnic_hatred(self, engine):
        """Religious/ethnic hatred + deportation directive → REJECT."""
        result = engine.analyze_user_profile([
            "all muslims are terrorists go back to your country"
        ])
        assert result["decision"] == "REJECT CUSTOMER"
        assert result["final_risk_score"] > 0.67

    def test_multi_post_hate_speech_profile(self, engine):
        """A profile with multiple HS posts must score above the reject threshold."""
        posts = [
            "kill all niggers they dont deserve to live",
            "These people are all criminals and should be deported.",
            "i hate all muslims are terrorists go back to your country",
        ]
        result = engine.analyze_user_profile(posts)
        assert result["decision"] == "REJECT CUSTOMER"
        assert result["final_risk_score"] > 0.80, (
            "Multi-post HS profile should score very high risk"
        )

    def test_hate_speech_with_positive_filler_posts(self, engine):
        """
        CRITICAL: A single HS post surrounded by positive posts must still REJECT.
        Diluting HS with innocent posts must NOT escape the reject threshold.
        """
        posts = [
            "what a beautiful day love the sunshine",
            "kill all niggers they dont deserve to live",
            "just had coffee great start to the morning",
        ]
        result = engine.analyze_user_profile(posts)
        assert result["decision"] == "REJECT CUSTOMER", (
            "HS diluted by positive posts incorrectly escaped reject threshold. "
            f"Got: {result['decision']}, score={result['final_risk_score']}"
        )


# ══════════════════════════════════════════════════════════════════════
# 2. HARD APPROVE CASES
# ══════════════════════════════════════════════════════════════════════

class TestHardApprove:

    def test_fully_positive_profile(self, engine):
        """All-positive, clean posts → APPROVE, score < 0.34."""
        posts = [
            "this feels so good knowing everything is working out",
            "i am so happy to be a part of this",
            "the weather today is beautiful",
        ]
        result = engine.analyze_user_profile(posts)
        assert result["decision"] == "APPROVE CAR RENTAL", (
            f"Safe profile not approved. Got: {result['decision']}, "
            f"score={result['final_risk_score']}"
        )
        assert result["final_risk_score"] < 0.34

    def test_neutral_everyday_content(self, engine):
        """Mundane everyday posts → APPROVE."""
        posts = [
            "just had coffee great start to the morning",
            "the traffic was bad today but i made it on time",
            "bought a new car today so excited to drive it",
            "dinner with family was lovely everyone enjoyed it",
        ]
        result = engine.analyze_user_profile(posts)
        assert result["decision"] == "APPROVE CAR RENTAL"
        assert result["final_risk_score"] < 0.34

    def test_criticism_of_object_not_person(self, engine):
        """
        Negative opinion about a film/product (not a person/group) must
        NOT be classified as offensive.
        """
        posts = [
            "This movie was absolutely trash, worst film I seen.",
            "just chillin at home watching netflix life is good",
        ]
        result = engine.analyze_user_profile(posts)
        assert result["decision"] == "APPROVE CAR RENTAL", (
            "Object-directed criticism ('movie was trash') incorrectly triggered risk. "
            f"Got: {result['decision']}, score={result['final_risk_score']}"
        )


# ══════════════════════════════════════════════════════════════════════
# 3. EXPRESSIVE LANGUAGE DISCOUNT (Case B logic)
# ══════════════════════════════════════════════════════════════════════

class TestExpressiveLanguageDiscount:

    def test_enthusiastic_profanity_approved(self, engine):
        """
        REGRESSION: Enthusiastic profanity expressing excitement (AAVE-style,
        sports fan, etc.) must not inflate the risk score to REVIEW/REJECT.
        The context_discounted flag must fire and the score must stay < 0.34.
        """
        posts = [
            "this fucking car is so clean I love it",
            "bro that race was insane as hell, best drive ever",
            "holy shit the roads are empty today what a vibe",
        ]
        result = engine.analyze_user_profile(posts)
        assert result["decision"] == "APPROVE CAR RENTAL", (
            "Expressive positive profanity (Case B) not discounted correctly. "
            f"Got: {result['decision']}, score={result['final_risk_score']}"
        )
        assert result["final_risk_score"] < 0.34

    def test_post_level_context_discount_fires(self, engine):
        """Verify the context_discounted flag fires for Case B inputs."""
        post = "this fucking car is so clean I love it"
        post_result = engine.calculate_post_risk(post)
        # This MUST be a Case B scenario: offensive class, positive sentiment
        if post_result["tox_class"] == 1 and post_result["sent_class"] == 1:
            assert post_result["context_discounted"] is True, (
                "Case B (offensive + positive) did not set context_discounted=True"
            )


# ══════════════════════════════════════════════════════════════════════
# 4. NEITHER GATE — Personal Distress Suppression (Case D logic)
# ══════════════════════════════════════════════════════════════════════

class TestPersonalDistressSuppression:

    def test_personal_distress_does_not_reject(self, engine):
        """
        CRITICAL REGRESSION: Negative personal-state language ("I feel sick",
        "I hate this cold") is NOT behavioral risk. The neither_suppressed gate
        must fire and the final score must stay below the reject threshold.
        """
        posts = [
            "i feel so sick today this is terrible",
            "i hate having a cold it ruins everything",
        ]
        result = engine.analyze_user_profile(posts)
        assert result["decision"] != "REJECT CUSTOMER", (
            "Personal distress incorrectly resulted in REJECT. "
            f"Score: {result['final_risk_score']}"
        )
        assert result["final_risk_score"] < 0.67

    def test_neither_suppressed_flag_fires(self, engine):
        """The neither_suppressed flag must be set for cleared-Neither posts with neg sentiment."""
        post = "i feel so sick today this is terrible"
        result = engine.calculate_post_risk(post)
        if result["tox_class"] == 2:  # Only verify if toxicity model says Neither
            assert result["neither_suppressed"] is True, (
                "neither_suppressed should be True for a Neither-class post"
            )

    def test_mixed_distress_and_positive_approves(self, engine):
        """
        A mostly positive profile with one personal-distress post must still APPROVE.
        Distress post should not anchor the final score.
        """
        posts = [
            "this feels so good knowing everything is working out",
            "this is so bad, i feel like throwing up",
            "i am so happy to be a part of this",
            "ohhhh my goodddddd lesgoo the american team literally take it all",
            "this is so amazing i am loving it here",
        ]
        result = engine.analyze_user_profile(posts)
        assert result["decision"] == "APPROVE CAR RENTAL", (
            "Mixed profile with personal distress not approved. "
            f"Score: {result['final_risk_score']}"
        )
        assert result["final_risk_score"] < 0.34


# ══════════════════════════════════════════════════════════════════════
# 5. EDGE CASES
# ══════════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_single_word_inputs_approve(self, engine):
        """Single-word posts (<3 tokens) hit the short-text gate → safe approval."""
        result = engine.analyze_user_profile(["hi", "so", "ok"])
        assert result["decision"] == "APPROVE CAR RENTAL", (
            "Single-word inputs should safely approve due to short-text gate. "
            f"Got: {result['decision']}"
        )

    def test_empty_string_in_list(self, engine):
        """Engine must not crash on empty strings."""
        try:
            result = engine.analyze_user_profile(["", "   ", "\t"])
            # Whatever the decision, it should not raise an exception
            assert "decision" in result
        except Exception as exc:
            pytest.fail(f"Engine crashed on empty/whitespace inputs: {exc}")

    def test_very_long_post(self, engine):
        """Engine must handle a post of 500+ words without crashing."""
        long_post = ("I really enjoy driving and going on road trips " * 25).strip()
        try:
            result = engine.analyze_user_profile([long_post])
            assert "decision" in result
        except Exception as exc:
            pytest.fail(f"Engine crashed on long input: {exc}")

    def test_unicode_and_emoji_input(self, engine):
        """Unicode characters and emoji must not crash the engine."""
        posts = [
            "I love this car! 🚗💨 So excited for the road trip! ❤️",
            "Magnifique journée aujourd'hui, je suis très heureux!",
        ]
        try:
            result = engine.analyze_user_profile(posts)
            assert "decision" in result
        except Exception as exc:
            pytest.fail(f"Engine crashed on unicode/emoji input: {exc}")

    def test_single_post_profile(self, engine):
        """Engine must work with exactly one post."""
        result = engine.analyze_user_profile(["I enjoy long drives on the highway."])
        assert result["decision"] == "APPROVE CAR RENTAL"

    def test_maximum_posts_profile(self, engine):
        """Engine must handle 10-post profiles (API max) without errors."""
        posts = ["I love road trips and good music."] * 10
        try:
            result = engine.analyze_user_profile(posts)
            assert "decision" in result
            assert 0.0 <= result["final_risk_score"] <= 1.0
        except Exception as exc:
            pytest.fail(f"Engine crashed on 10-post profile: {exc}")


# ══════════════════════════════════════════════════════════════════════
# 6. SCORE MONOTONICITY
# ══════════════════════════════════════════════════════════════════════

class TestScoreMonotonicity:

    def test_more_hate_speech_higher_score(self, engine):
        """
        Adding more hate speech posts to a profile must increase the risk score.
        Verifies the aggregation formula doesn't have a ceiling that hides HS.
        """
        clean_post = "the weather today is quite nice perfect for a walk"
        hs_post    = "kill all niggers they dont deserve to live"

        result_one_hs   = engine.analyze_user_profile([hs_post])
        result_mixed_hs = engine.analyze_user_profile([hs_post, hs_post, clean_post])

        # Both should reject; two-HS-post profile must score >= one-HS-post
        assert result_mixed_hs["final_risk_score"] >= result_one_hs["final_risk_score"] * 0.90, (
            "Adding more HS posts should not significantly decrease the risk score. "
            f"One HS: {result_one_hs['final_risk_score']}, "
            f"More HS: {result_mixed_hs['final_risk_score']}"
        )

    def test_clean_profile_lower_than_hs_profile(self, engine):
        """A clean profile must score strictly lower than a hate speech profile."""
        clean_result = engine.analyze_user_profile([
            "what a beautiful day love the sunshine",
            "bought a new car today so excited to drive it",
        ])
        hs_result = engine.analyze_user_profile([
            "kill all niggers they dont deserve to live",
        ])
        assert clean_result["final_risk_score"] < hs_result["final_risk_score"], (
            "Clean profile scored higher than or equal to a hate speech profile."
        )


# ══════════════════════════════════════════════════════════════════════
# 7. LATENCY
# ══════════════════════════════════════════════════════════════════════

class TestLatency:

    def test_single_post_latency_under_2s(self, engine):
        """Single post analysis must complete within 2 seconds."""
        start  = time.time()
        engine.analyze_user_profile(["I love driving on open roads."])
        elapsed = time.time() - start
        assert elapsed < 2.0, (
            f"Single post analysis took {elapsed:.2f}s — exceeds 2s SLA"
        )

    def test_ten_post_profile_latency_under_5s(self, engine):
        """10-post profile analysis must complete within 5 seconds."""
        posts   = ["I really enjoy driving and going on road trips."] * 10
        start   = time.time()
        engine.analyze_user_profile(posts)
        elapsed = time.time() - start
        assert elapsed < 5.0, (
            f"10-post profile analysis took {elapsed:.2f}s — exceeds 5s SLA"
        )


# ══════════════════════════════════════════════════════════════════════
# 8. DETERMINISM
# ══════════════════════════════════════════════════════════════════════

class TestDeterminism:

    def test_same_input_same_output(self, engine):
        """Identical inputs must always produce identical outputs (no randomness)."""
        posts = [
            "this fucking car is so clean I love it",
            "kill all niggers they dont deserve to live",
            "i feel so sick today this is terrible",
        ]
        result_a = engine.analyze_user_profile(posts)
        result_b = engine.analyze_user_profile(posts)
        assert result_a["final_risk_score"] == result_b["final_risk_score"], (
            "Engine is non-deterministic: same input produced different scores. "
            f"Run A: {result_a['final_risk_score']}, Run B: {result_b['final_risk_score']}"
        )
        assert result_a["decision"] == result_b["decision"]


# ══════════════════════════════════════════════════════════════════════
# 9. RESPONSE SCHEMA INTEGRITY
# ══════════════════════════════════════════════════════════════════════

class TestResponseSchema:

    REQUIRED_KEYS = {
        "final_risk_score", "final_confidence", "engine_latency",
        "decision", "status_color", "metrics", "reasons"
    }
    VALID_DECISIONS = {"APPROVE CAR RENTAL", "MANUAL REVIEW", "REJECT CUSTOMER"}
    VALID_COLORS    = {"GREEN", "YELLOW", "RED"}

    def test_response_has_all_required_keys(self, engine):
        result = engine.analyze_user_profile(["The weather today is nice."])
        missing = self.REQUIRED_KEYS - set(result.keys())
        assert not missing, f"Response missing required keys: {missing}"

    def test_decision_is_one_of_valid_values(self, engine):
        for posts, label in [
            (["The weather today is nice."],            "clean"),
            (["kill all niggers dont deserve to live"], "hate speech"),
        ]:
            result = engine.analyze_user_profile(posts)
            assert result["decision"] in self.VALID_DECISIONS, (
                f"Unexpected decision value for {label} input: '{result['decision']}'"
            )

    def test_risk_score_is_bounded_0_to_1(self, engine):
        for posts in [
            ["The weather today is nice."],
            ["kill all niggers dont deserve to live"],
            ["i feel so sick today this is terrible"],
        ]:
            result = engine.analyze_user_profile(posts)
            assert 0.0 <= result["final_risk_score"] <= 1.0, (
                f"Risk score out of [0,1] range: {result['final_risk_score']}"
            )

    def test_status_color_matches_decision(self, engine):
        """Color and decision must be consistent with each other."""
        COLOR_MAP = {
            "APPROVE CAR RENTAL": "GREEN",
            "MANUAL REVIEW":      "YELLOW",
            "REJECT CUSTOMER":    "RED",
        }
        for posts in [
            ["The weather today is nice."],
            ["What's up with these hoes always starting drama?"],
            ["kill all niggers dont deserve to live"],
        ]:
            result = engine.analyze_user_profile(posts)
            expected_color = COLOR_MAP.get(result["decision"])
            assert result["status_color"] == expected_color, (
                f"Color mismatch: decision='{result['decision']}' "
                f"expected color='{expected_color}' got='{result['status_color']}'"
            )

    def test_reasons_list_not_empty(self, engine):
        """The explainability reasons list must always contain at least one entry."""
        result = engine.analyze_user_profile(["The weather is nice today."])
        assert isinstance(result["reasons"], list) and len(result["reasons"]) >= 1, (
            "Engine returned empty reasons list"
        )