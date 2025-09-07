from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from bson import ObjectId
from typing import TypedDict, Literal
import pytest

from src.repository.db.ferretdb.repository import FerretDBRepository
from src.repository.db.models import AssignmentModel, FileModel


class AssignmentDoc(TypedDict):
    _id: ObjectId
    name: str
    confidence_threshold: float
    deliverables: list[ObjectId]
    evaluation_rubrics: list[ObjectId]
    relevant_documents: list[ObjectId]
    created_at: datetime
    updated_at: datetime

class FileDoc(TypedDict):
    _id: ObjectId
    assignment_id: ObjectId
    filename: str
    gridfs_id: ObjectId
    content_type: str
    file_type: Literal["rubric", "relevant_document"]
    uploaded_at: datetime

class TestAssignmentOperations:
    """Tests for assignment-related operations in FerretDBRepository."""

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_create_assignment(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test creating an assignment."""
        mock_collection = self._setup_mock_collection(mock_mongo_client)
        
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        mock_collection.insert_one.return_value = mock_insert_result

        repo = FerretDBRepository()
        repo.assignments_collection = mock_collection
        
        result = repo.create_assignment("Test Assignment", 0.75)
        
        assert result == "60c72b2f9b1d8e2a1c9d4b7f"
        
        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["name"] == "Test Assignment"
        assert call_args["confidence_threshold"] == 0.75
        assert call_args["deliverables"] == []
        assert call_args["evaluation_rubrics"] == []
        assert call_args["relevant_documents"] == []
        assert isinstance(call_args["created_at"], datetime)
        assert isinstance(call_args["updated_at"], datetime)

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_get_assignment_found(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test retrieving an existing assignment."""
        assignment_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        assignment_data = self._create_assignment_data(assignment_id)
        
        mock_collection = self._setup_mock_collection(mock_mongo_client)
        mock_collection.find_one.return_value = assignment_data
        
        repo = FerretDBRepository()
        repo.assignments_collection = mock_collection
        
        result = repo.get_assignment(str(assignment_id))
        
        assert isinstance(result, AssignmentModel)
        assert result.name == "Test Assignment"
        assert result.confidence_threshold == 0.75
        mock_collection.find_one.assert_called_once_with({"_id": assignment_id})

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_get_assignment_not_found(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test retrieving non-existent assignment."""
        mock_collection = self._setup_mock_collection(mock_mongo_client)
        mock_collection.find_one.return_value = None
        
        repo = FerretDBRepository()
        repo.assignments_collection = mock_collection
        
        result = repo.get_assignment("60c72b2f9b1d8e2a1c9d4b7f")
        assert result is None

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_get_assignment_exception(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test get_assignment with exception handling."""
        mock_collection = self._setup_mock_collection(mock_mongo_client)
        mock_collection.find_one.side_effect = Exception("DB error")
        
        repo = FerretDBRepository()
        repo.assignments_collection = mock_collection
        
        result = repo.get_assignment("60c72b2f9b1d8e2a1c9d4b7f")
        assert result is None

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_list_assignments(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test listing all assignments."""
        assignments_data = [
            self._create_assignment_data(ObjectId(), "Assignment 1", 0.70),
            self._create_assignment_data(ObjectId(), "Assignment 2", 0.80)
        ]
        
        mock_collection = self._setup_mock_collection(mock_mongo_client)
        mock_cursor = MagicMock()
        mock_cursor.__iter__ = MagicMock(return_value=iter(assignments_data))
        mock_collection.find.return_value.sort.return_value = mock_cursor
        
        repo = FerretDBRepository()
        repo.assignments_collection = mock_collection
        
        result = repo.list_assignments()
        
        assert len(result) == 2
        assert all(isinstance(a, AssignmentModel) for a in result)
        assert result[0].name == "Assignment 1"
        assert result[1].name == "Assignment 2"

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_list_assignments_exception(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test list_assignments with exception during iteration."""
        mock_collection = self._setup_mock_collection(mock_mongo_client)
        mock_collection.find.return_value.sort.return_value = [Exception("DB error")]
        
        repo = FerretDBRepository()
        repo.assignments_collection = mock_collection
        
        result = repo.list_assignments()
        assert result == []

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_update_assignment(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test updating an assignment."""
        assignment_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        mock_collection = self._setup_mock_collection(mock_mongo_client)
        
        mock_update_result = MagicMock()
        mock_update_result.modified_count = 1
        mock_collection.update_one.return_value = mock_update_result
        
        repo = FerretDBRepository()
        repo.assignments_collection = mock_collection
        
        result = repo.update_assignment(
            str(assignment_id),
            name="Updated Assignment",
            confidence_threshold=0.90
        )
        
        assert result is True
        
        call_args = mock_collection.update_one.call_args
        assert call_args[0][0] == {"_id": assignment_id}
        update_doc = call_args[0][1]["$set"]
        assert update_doc["name"] == "Updated Assignment"
        assert update_doc["confidence_threshold"] == 0.90
        assert isinstance(update_doc["updated_at"], datetime)

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_update_assignment_exception(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test update_assignment with exception."""
        mock_collection = self._setup_mock_collection(mock_mongo_client)
        mock_collection.update_one.side_effect = Exception("DB error")
        
        repo = FerretDBRepository()
        repo.assignments_collection = mock_collection
        
        result = repo.update_assignment("60c72b2f9b1d8e2a1c9d4b7f")
        assert result is False

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_delete_assignment(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test deleting an assignment with associated files."""
        assignment_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        mock_assignments_collection = MagicMock()
        mock_files_collection = MagicMock()
        mock_deliverables_collection = MagicMock()
        
        mock_fs = mock_gridfs.return_value
        
        # Mock associated files
        mock_files_collection.find.return_value = [
            {"_id": ObjectId(), "gridfs_id": ObjectId()},
            {"_id": ObjectId(), "gridfs_id": ObjectId()}
        ]
        mock_deliverables_collection.find.return_value = [
            {"_id": ObjectId(), "gridfs_id": ObjectId()}
        ]
        
        mock_delete_result = MagicMock()
        mock_delete_result.deleted_count = 1
        mock_assignments_collection.delete_one.return_value = mock_delete_result
        
        repo = FerretDBRepository()
        repo.assignments_collection = mock_assignments_collection
        repo.files_collection = mock_files_collection
        repo.deliverables_collection = mock_deliverables_collection
        repo.fs = mock_fs
        
        result = repo.delete_assignment(str(assignment_id))
        
        assert result is True
        mock_files_collection.delete_many.assert_called_once_with({"assignment_id": assignment_id})
        mock_deliverables_collection.delete_many.assert_called_once_with({"assignment_id": assignment_id})
        mock_assignments_collection.delete_one.assert_called_once_with({"_id": assignment_id})
        assert mock_fs.delete.call_count == 3

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_delete_assignment_not_found(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test deleting non-existent assignment."""
        mock_assignments_collection = MagicMock()
        mock_files_collection = MagicMock()
        mock_deliverables_collection = MagicMock()
        
        mock_files_collection.find.return_value = []
        mock_deliverables_collection.find.return_value = []
        
        mock_delete_result = MagicMock()
        mock_delete_result.deleted_count = 0
        mock_assignments_collection.delete_one.return_value = mock_delete_result
        
        repo = FerretDBRepository()
        repo.assignments_collection = mock_assignments_collection
        repo.files_collection = mock_files_collection
        repo.deliverables_collection = mock_deliverables_collection
        repo.fs = mock_gridfs.return_value
        
        result = repo.delete_assignment("60c72b2f9b1d8e2a1c9d4b7f")
        assert result is False

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_delete_assignment_exception(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test delete_assignment with exception."""
        mock_collection = self._setup_mock_collection(mock_mongo_client)
        mock_collection.delete_one.side_effect = Exception("DB error")
        
        repo = FerretDBRepository()
        repo.assignments_collection = mock_collection
        
        result = repo.delete_assignment("60c72b2f9b1d8e2a1c9d4b7f")
        assert result is False

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    @pytest.mark.parametrize("file_type,update_field", [
        ("rubric", "evaluation_rubrics"),
        ("relevant_document", "relevant_documents"),
    ])
    def test_store_file(
        self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock,
        file_type: str, update_field: str
    ) -> None:
        """Test storing files (rubrics and documents)."""
        assignment_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        file_id = ObjectId("50c72b2f9b1d8e2a1c9d4b7f")
        gridfs_id = ObjectId("40c72b2f9b1d8e2a1c9d4b7f")
        
        mock_files_collection = self._setup_mock_collection(mock_mongo_client)
        mock_assignments_collection = MagicMock()
        
        mock_fs = mock_gridfs.return_value
        mock_fs.put.return_value = gridfs_id
        
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = file_id
        mock_files_collection.insert_one.return_value = mock_insert_result
        
        repo = FerretDBRepository()
        repo.files_collection = mock_files_collection
        repo.assignments_collection = mock_assignments_collection
        repo.fs = mock_fs
        
        result = repo.store_file(
            str(assignment_id), "test.pdf", b"content",
            "application/pdf", file_type
        )
        
        assert result == str(file_id)
        
        mock_fs.put.assert_called_once_with(
            b"content",
            filename="test.pdf",
            content_type="application/pdf",
            assignment_id=str(assignment_id),
            file_type=file_type
        )
        
        mock_assignments_collection.update_one.assert_called_once_with(
            {"_id": assignment_id},
            {"$push": {update_field: file_id}}
        )

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_store_file_exception(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test store_file with exception."""
        mock_collection = self._setup_mock_collection(mock_mongo_client)
        mock_collection.insert_one.side_effect = Exception("DB error")
        
        repo = FerretDBRepository()
        repo.files_collection = mock_collection
        repo.fs = mock_gridfs.return_value
        
        with pytest.raises(Exception):
            repo.store_file("60c72b2f9b1d8e2a1c9d4b7f", "test.txt", b"test", "text/plain", "rubric")

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_get_file(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test retrieving a file."""
        file_id = ObjectId("50c72b2f9b1d8e2a1c9d4b7f")
        gridfs_id = ObjectId("40c72b2f9b1d8e2a1c9d4b7f")
        
        file_data: FileDoc = {
            "_id": file_id,
            "assignment_id": ObjectId("60c72b2f9b1d8e2a1c9d4b7f"),
            "filename": "test.pdf",
            "gridfs_id": gridfs_id,
            "content_type": "application/pdf",
            "file_type": "rubric",
            "uploaded_at": datetime.now(timezone.utc)
        }
        
        mock_collection = self._setup_mock_collection(mock_mongo_client)
        mock_collection.find_one.return_value = file_data
        
        mock_fs = mock_gridfs.return_value
        mock_gridfs_file = MagicMock()
        mock_gridfs_file.read.return_value = b"test content"
        mock_fs.get.return_value = mock_gridfs_file
        
        repo = FerretDBRepository()
        repo.files_collection = mock_collection
        repo.fs = mock_fs
        
        result = repo.get_file(str(file_id))
        
        assert isinstance(result, FileModel)
        assert result.filename == "test.pdf"
        assert result.content == b"test content"
        mock_collection.find_one.assert_called_once_with({"_id": file_id})
        mock_fs.get.assert_called_once_with(gridfs_id)

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_get_file_exception(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test get_file with exception."""
        mock_collection = self._setup_mock_collection(mock_mongo_client)
        mock_collection.find_one.side_effect = Exception("DB error")
        
        repo = FerretDBRepository()
        repo.files_collection = mock_collection
        
        result = repo.get_file("50c72b2f9b1d8e2a1c9d4b7f")
        assert result is None

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_list_files_by_assignment(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test listing files for an assignment."""
        assignment_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        files_data = [
            self._create_file_data(ObjectId(), assignment_id, "rubric1.pdf"),
            self._create_file_data(ObjectId(), assignment_id, "rubric2.pdf")
        ]
        
        mock_collection = self._setup_mock_collection(mock_mongo_client)
        mock_cursor = MagicMock()
        mock_cursor.__iter__ = MagicMock(return_value=iter(files_data))
        mock_collection.find.return_value.sort.return_value = mock_cursor
        
        repo = FerretDBRepository()
        repo.files_collection = mock_collection
        
        result = repo.list_files_by_assignment(str(assignment_id), "rubric")
        
        assert len(result) == 2
        assert all(isinstance(f, FileModel) for f in result)
        assert result[0].filename == "rubric1.pdf"
        assert result[1].filename == "rubric2.pdf"
        
        mock_collection.find.assert_called_once_with({
            "assignment_id": assignment_id,
            "file_type": "rubric"
        })

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_list_files_by_assignment_exception(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test list_files_by_assignment with exception."""
        mock_collection = self._setup_mock_collection(mock_mongo_client)
        mock_collection.find.side_effect = Exception("DB error")
        
        repo = FerretDBRepository()
        repo.files_collection = mock_collection
        
        result = repo.list_files_by_assignment("60c72b2f9b1d8e2a1c9d4b7f")
        assert result == []

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_list_files_by_assignment_validation_error(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test list_files_by_assignment with validation error."""
        mock_collection = self._setup_mock_collection(mock_mongo_client)
        mock_collection.find.return_value.sort.return_value = [{"_id": "invalid"}]
        
        repo = FerretDBRepository()
        repo.files_collection = mock_collection
        
        result = repo.list_files_by_assignment("60c72b2f9b1d8e2a1c9d4b7f")
        assert result == []

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_get_file_not_found(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test get_file when file doesn't exist (covers line 174)."""
        mock_collection = self._setup_mock_collection(mock_mongo_client)
        mock_collection.find_one.return_value = None
        
        repo = FerretDBRepository()
        repo.files_collection = mock_collection
        
        result = repo.get_file("60c72b2f9b1d8e2a1c9d4b7f")
        
        assert result is None
        mock_collection.find_one.assert_called_once()

    def _setup_mock_collection(self, mock_mongo_client: MagicMock) -> MagicMock:
        """Setup mock MongoDB collection."""
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        return mock_collection

    def _create_assignment_data(
        self, assignment_id: ObjectId, name: str = "Test Assignment",
        confidence_threshold: float = 0.75
    ) -> AssignmentDoc:
        """Create assignment test data."""
        return {
            "_id": assignment_id,
            "name": name,
            "confidence_threshold": confidence_threshold,
            "deliverables": [],
            "evaluation_rubrics": [],
            "relevant_documents": [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

    def _create_file_data(
        self, file_id: ObjectId, assignment_id: ObjectId, filename: str
    ) -> FileDoc:
        """Create file test data."""
        return {
            "_id": file_id,
            "assignment_id": assignment_id,
            "filename": filename,
            "gridfs_id": ObjectId(),
            "content_type": "application/pdf",
            "file_type": "rubric",
            "uploaded_at": datetime.now(timezone.utc)
        }