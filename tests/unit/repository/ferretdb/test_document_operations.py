from typing import Any, Dict
from unittest.mock import patch, MagicMock
from pymongo.errors import ConnectionFailure
from bson import ObjectId

from src.repository.db.ferretdb.repository import FerretDBRepository
from src.repository.db.models import DocumentModel


class TestDocumentOperations:
    """Tests for document operations and health check in FerretDBRepository."""

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_health_check_success(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test successful health check."""
        mock_client_instance = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_client_instance.admin.command.return_value = {"ok": 1}

        repo = FerretDBRepository()
        assert repo.health() is True
        mock_client_instance.admin.command.assert_called_once_with('ismaster')

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_health_check_failure(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test health check when database is unreachable."""
        mock_client_instance = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_client_instance.admin.command.side_effect = ConnectionFailure

        repo = FerretDBRepository()
        assert repo.health() is False
        mock_client_instance.admin.command.assert_called_once_with('ismaster')

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
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
        
        doc_id = repo.store_document(
            "test_assignment", "test_deliverable", "test_student",
            b"test_document", "txt"
        )

        assert doc_id == "document_id"
        
        mock_fs.put.assert_called_once_with(
            b"test_document",
            filename="test_student_test_assignment.txt"
        )
        
        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["assignment"] == "test_assignment"
        assert call_args["deliverable"] == "test_deliverable"
        assert call_args["student_name"] == "test_student"
        assert call_args["gridfs_id"] == gridfs_id
        assert call_args["extension"] == "txt"
        assert call_args["file_size"] == len(b"test_document")

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_get_document_found(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test retrieving an existing document."""
        doc_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        gridfs_id = ObjectId("40c72b2f9b1d8e2a1c9d4b7f")

        document_data: Dict[str, Any] = {
            "_id": doc_id,
            "assignment": "test",
            "deliverable": "test",
            "student_name": "test",
            "gridfs_id": gridfs_id,
            "extension": "txt"
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

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_get_document_not_found(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test retrieving non-existent document."""
        mock_collection = self._setup_mock_collection(mock_mongo_client)
        mock_collection.find_one.return_value = None

        repo = FerretDBRepository()
        repo.collection = mock_collection
        
        result = repo.get_document("60c72b2f9b1d8e2a1c9d4b7f")
        assert result is None

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_get_document_invalid_id(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test retrieving document with invalid ID."""
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        repo = FerretDBRepository()
        result = repo.get_document("invalid-id")
        assert result is None

    def _setup_mock_collection(self, mock_mongo_client: MagicMock) -> MagicMock:
        """Setup mock MongoDB collection."""
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        return mock_collection