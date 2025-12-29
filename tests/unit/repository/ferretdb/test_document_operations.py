from typing import Any
from unittest.mock import MagicMock, patch

from bson import ObjectId
from pymongo.errors import ConnectionFailure

from src.repository.db.ferretdb.repository import FerretDBRepository
from src.repository.db.models import DocumentModel


class TestDocumentOperations:
    """Tests for document operations and health check in FerretDBRepository."""

    @patch("src.repository.db.ferretdb.repository.GridFS")
    @patch("src.repository.db.ferretdb.repository.MongoClient")
    def test_health_check_success(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test successful health check."""
        mock_client_instance = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_client_instance.admin.command.return_value = {"ok": 1}

        repo = FerretDBRepository()
        assert repo.health() is True
        mock_client_instance.admin.command.assert_called_once_with("ismaster")

    @patch("src.repository.db.ferretdb.repository.GridFS")
    @patch("src.repository.db.ferretdb.repository.MongoClient")
    def test_health_check_failure(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test health check when database is unreachable."""
        mock_client_instance = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_client_instance.admin.command.side_effect = ConnectionFailure

        repo = FerretDBRepository()
        assert repo.health() is False
        mock_client_instance.admin.command.assert_called_once_with("ismaster")

    @patch("src.repository.db.ferretdb.repository.GridFS")
    @patch("src.repository.db.ferretdb.repository.MongoClient")
    def test_store_document(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test storing a document."""
        mock_collection = self._setup_mock_collection(mock_mongo_client)

        mock_fs = mock_gridfs.return_value
        gridfs_id = ObjectId("40c72b2f9b1d8e2a1c9d4b7f")
        mock_fs.put.return_value = gridfs_id

        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = "document_id"
        mock_collection.insert_one.return_value = mock_insert_result

        repo = FerretDBRepository()
        repo.collection = mock_collection
        repo.fs = mock_fs

        doc_id = repo.store_document("test_assignment", "test_deliverable", "test_student", b"test_document", "txt")

        assert doc_id == "document_id"

        mock_fs.put.assert_called_once_with(b"test_document", filename="test_student_test_assignment.txt")

        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["assignment"] == "test_assignment"
        assert call_args["deliverable"] == "test_deliverable"
        assert call_args["student_name"] == "test_student"
        assert call_args["gridfs_id"] == gridfs_id
        assert call_args["extension"] == "txt"
        assert call_args["file_size"] == len(b"test_document")

    @patch("src.repository.db.ferretdb.repository.GridFS")
    @patch("src.repository.db.ferretdb.repository.MongoClient")
    def test_get_document_found(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test retrieving an existing document."""
        doc_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        gridfs_id = ObjectId("40c72b2f9b1d8e2a1c9d4b7f")

        document_data: dict[str, Any] = {
            "_id": doc_id,
            "assignment": "test",
            "deliverable": "test",
            "student_name": "test",
            "gridfs_id": gridfs_id,
            "extension": "txt",
        }

        mock_collection = self._setup_mock_collection(mock_mongo_client)
        mock_collection.find_one.return_value = document_data

        mock_fs = mock_gridfs.return_value
        mock_gridfs_file = MagicMock()
        mock_gridfs_file.read.return_value = b"test content"
        mock_fs.get.return_value = mock_gridfs_file

        repo = FerretDBRepository()
        repo.collection = mock_collection
        repo.fs = mock_fs

        result = repo.get_document(str(doc_id))

        assert isinstance(result, DocumentModel)
        assert result.id == doc_id
        assert result.document == b"test content"
        mock_collection.find_one.assert_called_once_with({"_id": doc_id})
        mock_fs.get.assert_called_once_with(gridfs_id)

    @patch("src.repository.db.ferretdb.repository.GridFS")
    @patch("src.repository.db.ferretdb.repository.MongoClient")
    def test_get_document_not_found(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test retrieving non-existent document."""
        mock_collection = self._setup_mock_collection(mock_mongo_client)
        mock_collection.find_one.return_value = None

        repo = FerretDBRepository()
        repo.collection = mock_collection

        result = repo.get_document("60c72b2f9b1d8e2a1c9d4b7f")
        assert result is None

    @patch("src.repository.db.ferretdb.repository.GridFS")
    @patch("src.repository.db.ferretdb.repository.MongoClient")
    def test_get_document_invalid_id(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test retrieving document with invalid ID."""
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db

        repo = FerretDBRepository()
        result = repo.get_document("invalid-id")
        assert result is None

    @patch("src.repository.db.ferretdb.repository.GridFS")
    @patch("src.repository.db.ferretdb.repository.MongoClient")
    def test_update_file_chunks(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test updating file with chunks using model_dump."""
        self._setup_mock_collection(mock_mongo_client)
        # Mock file collection specifically
        mock_client = mock_mongo_client.return_value
        mock_db = mock_client.__getitem__.return_value
        mock_files_collection = MagicMock()
        mock_db.__getitem__.side_effect = lambda name: mock_files_collection if name == "files" else MagicMock()

        mock_update_result = MagicMock()
        mock_update_result.modified_count = 1
        mock_files_collection.update_one.return_value = mock_update_result

        repo = FerretDBRepository()
        # Manually set collection because side_effect above might be tricky with __init__
        repo.files_collection = mock_files_collection

        # Mock chunk model
        mock_chunk = MagicMock()
        mock_chunk.model_dump.return_value = {"text": "chunk1", "embedding": [0.1]}

        file_id = "60c72b2f9b1d8e2a1c9d4b7f"
        result = repo.update_file(file_id, chunks=[mock_chunk])

        assert result is True
        mock_files_collection.update_one.assert_called_once()
        call_args = mock_files_collection.update_one.call_args
        assert call_args[0][0] == {"_id": ObjectId(file_id)}
        assert call_args[0][1]["$set"]["chunks"] == [{"text": "chunk1", "embedding": [0.1]}]

    @patch("src.repository.db.ferretdb.repository.GridFS")
    @patch("src.repository.db.ferretdb.repository.MongoClient")
    def test_delete_file_success(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test successful file deletion."""
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db

        mock_files_collection = MagicMock()
        mock_assignments_collection = MagicMock()

        def collection_selector(name: str) -> MagicMock:
            if name == "files":
                return mock_files_collection
            if name == "assignments":
                return mock_assignments_collection
            return MagicMock()

        mock_db.__getitem__.side_effect = collection_selector

        file_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        gridfs_id = ObjectId("40c72b2f9b1d8e2a1c9d4b7f")
        assignment_id = ObjectId("50c72b2f9b1d8e2a1c9d4b7f")

        mock_files_collection.find_one.return_value = {
            "_id": file_id,
            "assignment_id": assignment_id,
            "gridfs_id": gridfs_id,
            "file_type": "rubric",
        }

        mock_delete_result = MagicMock()
        mock_delete_result.deleted_count = 1
        mock_files_collection.delete_one.return_value = mock_delete_result

        mock_fs = mock_gridfs.return_value

        repo = FerretDBRepository()
        repo.files_collection = mock_files_collection
        repo.assignments_collection = mock_assignments_collection
        repo.fs = mock_fs

        result = repo.delete_file(str(file_id))

        assert result is True
        mock_fs.delete.assert_called_once_with(gridfs_id)
        mock_files_collection.delete_one.assert_called_once_with({"_id": file_id})

    @patch("src.repository.db.ferretdb.repository.GridFS")
    @patch("src.repository.db.ferretdb.repository.MongoClient")
    def test_delete_file_not_found(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test deleting non-existent file."""
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db

        mock_files_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_files_collection
        mock_files_collection.find_one.return_value = None

        repo = FerretDBRepository()
        repo.files_collection = mock_files_collection

        result = repo.delete_file("60c72b2f9b1d8e2a1c9d4b7f")

        assert result is False
        mock_files_collection.delete_one.assert_not_called()

    @patch("src.repository.db.ferretdb.repository.GridFS")
    @patch("src.repository.db.ferretdb.repository.MongoClient")
    def test_delete_file_invalid_id(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test deleting file with invalid ID."""
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db

        repo = FerretDBRepository()

        result = repo.delete_file("invalid-id")

        assert result is False

    def _setup_mock_collection(self, mock_mongo_client: MagicMock) -> MagicMock:
        """Setup mock MongoDB collection."""
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db

        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        return mock_collection
