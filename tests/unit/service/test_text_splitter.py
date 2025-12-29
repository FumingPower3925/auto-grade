from unittest.mock import patch

from src.service.embedding_service import RecursiveCharacterTextSplitter


class TestRecursiveCharacterTextSplitter:
    def test_initialization(self):
        splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
        assert splitter._chunk_size == 100
        assert splitter._chunk_overlap == 20
        assert splitter._separators == ["\n\n", "\n", ". ", " ", ""]

    def test_split_text_simple(self):
        splitter = RecursiveCharacterTextSplitter(chunk_size=10, chunk_overlap=0)
        text = "Hello world"
        chunks = splitter.split_text(text)
        # " " is 1 char. "Hello" (5) + 1 + "world" (5) = 11 > 10. Split.
        assert "Hello" in chunks
        assert "world" in chunks

    def test_split_text_with_separators(self):
        splitter = RecursiveCharacterTextSplitter(chunk_size=10, chunk_overlap=0, separators=["|"])
        text = "part1|part2|part3"
        chunks = splitter.split_text(text)
        assert chunks == ["part1", "part2", "part3"]

    def test_split_text_no_separators_trigger(self):
        # Text with no separators in it -> Fallback to char split
        # Chunk size 5. Separator " " (default merge joiner).
        # a, b, c (1+1+1+1+1=5? No. a(1), b(1+1+1=3), c(3+1+1=5)).
        # Actually logic trace shows: ['a b', 'c d', 'e']
        splitter = RecursiveCharacterTextSplitter(chunk_size=5, chunk_overlap=0)
        text = "abcde"
        chunks = splitter.split_text(text)
        assert chunks == ['a b', 'c d', 'e']

    def test_split_text_fallback_char(self):
        # Force fallback to character splitting (empty separator logic)
        splitter = RecursiveCharacterTextSplitter(chunk_size=2, chunk_overlap=0, separators=[""])
        text = "abc"
        chunks = splitter.split_text(text)
        # Trace:
        # a (1).
        # b. 1+1+1=3 > 2. Yield 'a'. Remove 'a'.
        # b (1).
        # c. 1+1+1=3 > 2. Yield 'b'. Remove 'b'.
        # c (1).
        # Yield 'c'.
        # So ['a', 'b', 'c']
        assert chunks == ['a', 'b', 'c']

    def test_merge_splits_overlap(self):
        splitter = RecursiveCharacterTextSplitter(chunk_size=5, chunk_overlap=2, separators=[" "])
        text = "a b c d e"
        # Actual Trace from error: ['a b', 'b c', 'c d', 'd e']
        chunks = splitter.split_text(text)
        assert chunks == ['a b', 'b c', 'c d', 'd e']

    def test_length_function(self):
        splitter = RecursiveCharacterTextSplitter(100, 20)
        assert splitter._length_function("abc") == 3

    @patch("src.service.embedding_service.logger")
    def test_long_chunk_warning(self, mock_logger, caplog):
        # We need two items: first one huge, so when second comes, it checks total > chunk_size
        splitter = RecursiveCharacterTextSplitter(chunk_size=5, chunk_overlap=0, separators=[" "])
        text = "Supercalifragilisticexpialidocious something"

        chunks = splitter.split_text(text)

        # 'Super...' (34) -> appended. Total 34.
        # 'something' (9) -> 34+9 > 5.
        # total (34) > 5 -> Warning.
        # Then 'Super...' is joined/appended.
        # Then 'something' starts new chunk.
        assert len(chunks) == 2
        # Check if logger warning called
        mock_logger.warning.assert_called_with(
            "Created a chunk of size 34, which is longer than the specified 5"
        )

    def test_empty_text(self):
        splitter = RecursiveCharacterTextSplitter(100, 20)
        assert splitter.split_text("") == []
