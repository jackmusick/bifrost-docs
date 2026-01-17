"""Unit tests for field inference utility functions."""

from itglue_migrate.field_inference import detect_field_type


class TestDetectFieldType:
    """Tests for detect_field_type function."""

    def test_empty_samples_returns_text(self) -> None:
        """Test that empty sample list returns 'text'."""
        assert detect_field_type([]) == "text"

    def test_all_empty_samples_returns_text(self) -> None:
        """Test that all empty samples returns 'text'."""
        assert detect_field_type(["", "", ""]) == "text"
        # Note: detect_field_type expects list[str], not list[str | None]
        # Empty strings are used to represent None/missing values

    def test_simple_text_returns_text(self) -> None:
        """Test that simple text without special characters returns 'text'."""
        samples = ["Hello", "World", "Test"]
        assert detect_field_type(samples) == "text"

    def test_newline_returns_textbox(self) -> None:
        """Test that text with newline returns 'textbox'."""
        samples = ["Line 1\nLine 2"]
        assert detect_field_type(samples) == "textbox"

    def test_carriage_return_returns_textbox(self) -> None:
        """Test that text with carriage return returns 'textbox'."""
        samples = ["Line 1\rLine 2"]
        assert detect_field_type(samples) == "textbox"

    def test_crlf_returns_textbox(self) -> None:
        """Test that text with CRLF returns 'textbox'."""
        samples = ["Line 1\r\nLine 2"]
        assert detect_field_type(samples) == "textbox"

    def test_html_tag_returns_textbox(self) -> None:
        """Test that text with HTML tags returns 'textbox'."""
        samples = ["<p>Hello</p>"]
        assert detect_field_type(samples) == "textbox"

    def test_multiple_html_tags_returns_textbox(self) -> None:
        """Test that text with multiple HTML tags returns 'textbox'."""
        samples = ["<div><p>Hello</p><span>World</span></div>"]
        assert detect_field_type(samples) == "textbox"

    def test_html_self_closing_tag_returns_textbox(self) -> None:
        """Test that text with self-closing HTML tag returns 'textbox'."""
        samples = ["<br />"]
        assert detect_field_type(samples) == "textbox"

    def test_html_with_attributes_returns_textbox(self) -> None:
        """Test that text with HTML attributes returns 'textbox'."""
        samples = ['<a href="https://example.com">Link</a>']
        assert detect_field_type(samples) == "textbox"

    def test_mixed_samples_with_newline(self) -> None:
        """Test that mixed samples with one newline returns 'textbox'."""
        samples = ["Simple", "Text\nWith newline", "Another"]
        assert detect_field_type(samples) == "textbox"

    def test_mixed_samples_with_html(self) -> None:
        """Test that mixed samples with one HTML returns 'textbox'."""
        samples = ["Simple", "<b>Bold</b>", "Another"]
        assert detect_field_type(samples) == "textbox"

    def test_long_text_without_formatting_returns_text(self) -> None:
        """Test that long text without formatting returns 'text'."""
        samples = ["a" * 300]  # Longer than TEXTBOX_LENGTH_THRESHOLD
        assert detect_field_type(samples) == "text"

    def test_special_characters_without_html_returns_text(self) -> None:
        """Test that text with special characters but no HTML returns 'text'."""
        samples = ["Hello @world! #test $100"]
        assert detect_field_type(samples) == "text"

    def test_angle_brackets_without_tags_returns_textbox(self) -> None:
        """Test that text with angle brackets but not tags returns 'textbox'."""
        samples = ["2 < 5 and 5 > 2"]
        assert detect_field_type(samples) == "textbox"

    def test_unclosed_html_tag_returns_textbox(self) -> None:
        """Test that text with unclosed HTML tag returns 'textbox'."""
        samples = ["<p>Unclosed paragraph"]
        assert detect_field_type(samples) == "textbox"

    def test_html_in_middle_of_text_returns_textbox(self) -> None:
        """Test that text with HTML in the middle returns 'textbox'."""
        samples = ["Start <b>bold</b> end"]
        assert detect_field_type(samples) == "textbox"

    def test_multiple_newlines_returns_textbox(self) -> None:
        """Test that text with multiple newlines returns 'textbox'."""
        samples = ["Line 1\n\n\nLine 2"]
        assert detect_field_type(samples) == "textbox"

    def test_tab_character_returns_text(self) -> None:
        """Test that text with tab character returns 'text' (not newline)."""
        samples = ["Column1\tColumn2"]
        assert detect_field_type(samples) == "text"

    def test_html_comment_returns_textbox(self) -> None:
        """Test that HTML comment returns 'textbox'."""
        samples = ["<!-- This is a comment -->"]
        assert detect_field_type(samples) == "textbox"

    def test_skip_empty_samples(self) -> None:
        """Test that empty samples are skipped when checking for formatting."""
        samples = ["", "\n", "", "Simple text"]
        # First non-empty sample with newline should trigger textbox
        assert detect_field_type(samples) == "textbox"

    def test_url_without_html_returns_text(self) -> None:
        """Test that URL without HTML returns 'text'."""
        samples = ["https://example.com/path?query=value"]
        assert detect_field_type(samples) == "text"

    def test_email_address_returns_text(self) -> None:
        """Test that email address returns 'text'."""
        samples = ["user@example.com"]
        assert detect_field_type(samples) == "text"
