from unittest.mock import patch, MagicMock
from pymongo.errors import ConnectionFailure
from src.repository.db.ferretdb.repository import FerretDBRepository
from src.repository.db.factory import get_database_repository
from src.repository.db.models import DocumentModel
import pytest
from bson import ObjectId
from typing import Dict, Any


class TestFerretDBRepository:
    """Unit tests for the FerretDBRepository."""

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_health_check_success(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test the health check when the database is reachable."""
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
        """Test the health check when the database is unreachable."""
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
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        
        mock_fs = mock_gridfs.return_value
        gridfs_id = ObjectId("40c72b2f9b1d8e2a1c9d4b7f")
        mock_fs.put.return_value = gridfs_id
        
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = "some_id"
        mock_collection.insert_one.return_value = mock_insert_result

        repo = FerretDBRepository()
        repo.collection = mock_collection
        repo.fs = mock_fs
        
        doc_id = repo.store_document("test_assignment", "test_deliverable", "test_student", b"test_document", "txt")

        assert doc_id == "some_id"
        
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
        """Test retrieving a document that exists."""
        doc_id = "60c72b2f9b1d8e2a1c9d4b7f"
        gridfs_id = ObjectId("40c72b2f9b1d8e2a1c9d4b7f")
        
        document_data: Dict[str, Any] = {
            "_id": ObjectId(doc_id),
            "assignment": "test",
            "deliverable": "test",
            "student_name": "test",
            "gridfs_id": gridfs_id,
            "extension": "txt"
        }
        
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = document_data
        
        mock_fs = mock_gridfs.return_value
        mock_gridfs_file = MagicMock()
        mock_gridfs_file.read.return_value = b"test"
        mock_fs.get.return_value = mock_gridfs_file

        repo = FerretDBRepository()
        repo.collection = mock_collection
        repo.fs = mock_fs
        
        result = repo.get_document(doc_id)

        assert isinstance(result, DocumentModel)
        assert result.id == ObjectId(doc_id)
        assert result.document == b"test"
        mock_collection.find_one.assert_called_once_with({"_id": ObjectId(doc_id)})
        mock_fs.get.assert_called_once_with(gridfs_id)

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_get_document_not_found(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test retrieving a document that does not exist."""
        doc_id = "60c72b2f9b1d8e2a1c9d4b7f"
        
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = None

        repo = FerretDBRepository()
        repo.collection = mock_collection
        
        result = repo.get_document(doc_id)

        assert result is None
        mock_collection.find_one.assert_called_once_with({"_id": ObjectId(doc_id)})

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_get_document_invalid_id(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test retrieving a document with an invalid ID."""
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        repo = FerretDBRepository()
        result = repo.get_document("invalid-id")
        assert result is None


class TestDatabaseFactory:
    """Unit tests for the database repository factory."""

    @patch('src.repository.db.factory.get_config')
    def test_get_ferretdb_repository(self, mock_get_config: MagicMock) -> None:
        """Test getting a FerretDB repository."""
        mock_get_config.return_value.database.type = "ferretdb"
        repo = get_database_repository()
        from src.repository.db.ferretdb.repository import FerretDBRepository
        assert isinstance(repo, FerretDBRepository)

    @patch('src.repository.db.factory.get_config')
    def test_unsupported_database_type(self, mock_get_config: MagicMock) -> None:
        """Test that an unsupported database type raises a ValueError."""
        mock_get_config.return_value.database.type = "unsupported_db"
        with pytest.raises(ValueError, match="Unsupported database type: unsupported_db"):
            get_database_repository()