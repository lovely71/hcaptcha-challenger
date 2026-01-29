# -*- coding: utf-8 -*-
"""
Tests for the keyword-based challenge type classification.
"""
import pytest

from hcaptcha_challenger.models import ChallengeTypeEnum
from hcaptcha_challenger.agent.challenger import RoboticArm


class TestClassifyByPromptText:
    """Test cases for _classify_by_prompt_text method."""

    # ============ Click/Select Tests ============

    @pytest.mark.parametrize(
        "prompt,expected",
        [
            # English - single select
            ("Please click on the object that is different", ChallengeTypeEnum.IMAGE_LABEL_SINGLE_SELECT),
            ("Click the unique item", ChallengeTypeEnum.IMAGE_LABEL_SINGLE_SELECT),
            ("Select the odd one out", ChallengeTypeEnum.IMAGE_LABEL_SINGLE_SELECT),
            ("Please click on the different object", ChallengeTypeEnum.IMAGE_LABEL_SINGLE_SELECT),
            # English - multi select
            ("Please click on the two elements that are identical", ChallengeTypeEnum.IMAGE_LABEL_MULTI_SELECT),
            ("Click all the matching objects", ChallengeTypeEnum.IMAGE_LABEL_MULTI_SELECT),
            ("Select both identical items", ChallengeTypeEnum.IMAGE_LABEL_MULTI_SELECT),
            ("Click on each similar element", ChallengeTypeEnum.IMAGE_LABEL_MULTI_SELECT),
            # Chinese - single select
            ("请点击不同的物体", ChallengeTypeEnum.IMAGE_LABEL_SINGLE_SELECT),
            ("点击唯一的物体", ChallengeTypeEnum.IMAGE_LABEL_SINGLE_SELECT),
            # Chinese - multi select
            ("请点击两个相同的元素", ChallengeTypeEnum.IMAGE_LABEL_MULTI_SELECT),
            ("选择所有相似的物体", ChallengeTypeEnum.IMAGE_LABEL_MULTI_SELECT),
        ],
    )
    def test_click_classification(self, prompt: str, expected: ChallengeTypeEnum):
        result = RoboticArm._classify_by_prompt_text(prompt)
        assert result == expected, f"Prompt: {prompt!r} expected {expected}, got {result}"

    # ============ Drag Tests ============

    @pytest.mark.parametrize(
        "prompt,expected",
        [
            # English - single drag
            ("Please drag the puzzle piece to complete the image", ChallengeTypeEnum.IMAGE_DRAG_SINGLE),
            ("Drag the element to its shadow", ChallengeTypeEnum.IMAGE_DRAG_SINGLE),
            ("Move the piece to the correct position", ChallengeTypeEnum.IMAGE_DRAG_SINGLE),
            # English - multi drag
            ("Arrange all the shapes by dragging them", ChallengeTypeEnum.IMAGE_DRAG_MULTI),
            ("Drag each segment to its position", ChallengeTypeEnum.IMAGE_DRAG_MULTI),
            ("Move all pieces to their matching outlines", ChallengeTypeEnum.IMAGE_DRAG_MULTI),
            # Chinese - single drag
            ("请拖动拼图到正确位置", ChallengeTypeEnum.IMAGE_DRAG_SINGLE),
            ("拖拽元素到匹配的形状", ChallengeTypeEnum.IMAGE_DRAG_SINGLE),
            # Chinese - multi drag
            ("拖动所有形状到对应位置", ChallengeTypeEnum.IMAGE_DRAG_MULTI),
            ("请拖拽每个元素到正确的地方", ChallengeTypeEnum.IMAGE_DRAG_MULTI),
        ],
    )
    def test_drag_classification(self, prompt: str, expected: ChallengeTypeEnum):
        result = RoboticArm._classify_by_prompt_text(prompt)
        assert result == expected, f"Prompt: {prompt!r} expected {expected}, got {result}"

    # ============ Edge Cases ============

    def test_empty_prompt_returns_none(self):
        assert RoboticArm._classify_by_prompt_text("") is None
        assert RoboticArm._classify_by_prompt_text(None) is None

    def test_ambiguous_prompt_returns_none(self):
        # Contains both click and drag keywords
        result = RoboticArm._classify_by_prompt_text("Click and drag the element")
        assert result is None

    def test_no_action_keyword_returns_none(self):
        # No recognizable action keywords
        result = RoboticArm._classify_by_prompt_text("Complete the challenge")
        assert result is None

    # ============ Multi-language Tests ============

    @pytest.mark.parametrize(
        "prompt,expected",
        [
            # Russian
            ("Нажмите на отличающийся объект", ChallengeTypeEnum.IMAGE_LABEL_SINGLE_SELECT),
            ("Перетащите элемент на место", ChallengeTypeEnum.IMAGE_DRAG_SINGLE),
            # German
            ("Klicken Sie auf das unterschiedliche Objekt", ChallengeTypeEnum.IMAGE_LABEL_SINGLE_SELECT),
            ("Ziehen Sie alle Teile an die richtige Stelle", ChallengeTypeEnum.IMAGE_DRAG_MULTI),
            # French
            ("Cliquez sur l'élément différent", ChallengeTypeEnum.IMAGE_LABEL_SINGLE_SELECT),
            ("Glisser tous les éléments", ChallengeTypeEnum.IMAGE_DRAG_MULTI),
            # Spanish
            ("Haga clic en el objeto diferente", ChallengeTypeEnum.IMAGE_LABEL_SINGLE_SELECT),
            ("Arrastre todas las piezas", ChallengeTypeEnum.IMAGE_DRAG_MULTI),
        ],
    )
    def test_multilingual_classification(self, prompt: str, expected: ChallengeTypeEnum):
        result = RoboticArm._classify_by_prompt_text(prompt)
        assert result == expected, f"Prompt: {prompt!r} expected {expected}, got {result}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
