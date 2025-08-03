from interview_helper.processing import process_text, ProcessedText


def test_process_text_basic():
    """Test processing a simple text string"""
    text = "Hello world this is a test"
    result = process_text(text)

    assert isinstance(result, ProcessedText)
    assert result.word_count == 6
