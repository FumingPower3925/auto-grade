from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from bson import ObjectId
from typing import Dict, Any
import pytest

from src.repository.db.ferretdb.repository import FerretDBRepository
from src.repository.db.models import DeliverableModel


class TestFerretDBDeliverableRepository:
    """Unit tests for deliverable-related methods in FerretDBRepository."""

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_store_deliverable(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test storing a deliverable."""
        assignment_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        deliverable_id = ObjectId("50c72b2f9b1d8e2a1c9d4b7f")
        gridfs_id = ObjectId("40c72b2f9b1d8e2a1c9d4b7f")
        
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        mock_deliverables_collection = MagicMock()
        mock_assignments_collection = MagicMock()
        
        mock_fs = mock_gridfs.return_value
        mock_fs.put.return_value = gridfs_id
        
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = deliverable_id
        mock_deliverables_collection.insert_one.return_value = mock_insert_result
        
        repo = FerretDBRepository()
        repo.deliverables_collection = mock_deliverables_collection
        repo.assignments_collection = mock_assignments_collection
        repo.fs = mock_fs
        
        result = repo.store_deliverable(
            str(assignment_id),
            "submission.pdf",
            b"pdf content",
            "pdf",
            "application/pdf",
            "John Doe",
            "Extracted text"
        )
        
        assert result == str(deliverable_id)
        
        mock_fs.put.assert_called_once_with(
            b"pdf content",
            filename="submission.pdf",
            content_type="application/pdf",
            assignment_id=str(assignment_id),
            student_name="John Doe"
        )
        
        call_args = mock_deliverables_collection.insert_one.call_args[0][0]
        assert call_args["assignment_id"] == assignment_id
        assert call_args["filename"] == "submission.pdf"
        assert call_args["gridfs_id"] == gridfs_id
        assert call_args["extension"] == "pdf"
        assert call_args["content_type"] == "application/pdf"
        assert call_args["student_name"] == "John Doe"
        assert call_args["extracted_text"] == "Extracted text"
        assert call_args["mark"] is None
        assert call_args["certainty_threshold"] is None
        
        mock_assignments_collection.update_one.assert_called_once()
        update_call = mock_assignments_collection.update_one.call_args[0]
        assert update_call[0] == {"_id": assignment_id}
        assert "$push" in update_call[1]
        assert update_call[1]["$push"]["deliverables"] == deliverable_id

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_get_deliverable_found(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test retrieving a deliverable that exists."""
        deliverable_id = ObjectId("50c72b2f9b1d8e2a1c9d4b7f")
        gridfs_id = ObjectId("40c72b2f9b1d8e2a1c9d4b7f")
        
        deliverable_data: Dict[str, Any] = {
            "_id": deliverable_id,
            "assignment_id": ObjectId("60c72b2f9b1d8e2a1c9d4b7f"),
            "student_name": "Jane Smith",
            "mark": 85.5,
            "certainty_threshold": 0.95,
            "filename": "assignment.pdf",
            "gridfs_id": gridfs_id,
            "extension": "pdf",
            "content_type": "application/pdf",
            "uploaded_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "extracted_text": None
        }
        
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = deliverable_data
        
        mock_fs = mock_gridfs.return_value
        mock_gridfs_file = MagicMock()
        mock_gridfs_file.read.return_value = b"pdf content"
        mock_fs.get.return_value = mock_gridfs_file
        
        repo = FerretDBRepository()
        repo.deliverables_collection = mock_collection
        repo.fs = mock_fs
        
        result = repo.get_deliverable(str(deliverable_id))
        
        assert isinstance(result, DeliverableModel)
        assert result.student_name == "Jane Smith"
        assert result.mark == 85.5
        assert result.certainty_threshold == 0.95
        assert result.filename == "assignment.pdf"
        assert result.content == b"pdf content"
        mock_collection.find_one.assert_called_once_with({"_id": deliverable_id})
        mock_fs.get.assert_called_once_with(gridfs_id)

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_get_deliverable_not_found(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test retrieving a deliverable that doesn't exist."""
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = None
        
        repo = FerretDBRepository()
        repo.deliverables_collection = mock_collection
        
        result = repo.get_deliverable("50c72b2f9b1d8e2a1c9d4b7f")
        
        assert result is None

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_list_deliverables_by_assignment(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test listing deliverables for an assignment."""
        assignment_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        deliverables_data: list[Dict[str, Any]] = [
            {
                "_id": ObjectId(),
                "assignment_id": assignment_id,
                "student_name": "Student 1",
                "mark": None,
                "certainty_threshold": None,
                "filename": "submission1.pdf",
                "gridfs_id": ObjectId(),
                "extension": "pdf",
                "content_type": "application/pdf",
                "uploaded_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "extracted_text": None
            },
            {
                "_id": ObjectId(),
                "assignment_id": assignment_id,
                "student_name": "Student 2",
                "mark": 90.0,
                "certainty_threshold": 0.85,
                "filename": "submission2.pdf",
                "gridfs_id": ObjectId(),
                "extension": "pdf",
                "content_type": "application/pdf",
                "uploaded_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "extracted_text": "Some text"
            }
        ]
        
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        mock_collection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__iter__ = MagicMock(return_value=iter(deliverables_data))
        mock_collection.find.return_value.sort.return_value = mock_cursor
        
        repo = FerretDBRepository()
        repo.deliverables_collection = mock_collection
        
        result = repo.list_deliverables_by_assignment(str(assignment_id))
        
        assert len(result) == 2
        assert all(isinstance(d, DeliverableModel) for d in result)
        assert result[0].student_name == "Student 1"
        assert result[1].student_name == "Student 2"
        assert result[1].mark == 90.0
        
        mock_collection.find.assert_called_once_with({"assignment_id": assignment_id})

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_update_deliverable(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test updating a deliverable."""
        deliverable_id = ObjectId("50c72b2f9b1d8e2a1c9d4b7f")
        
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        mock_collection = MagicMock()
        
        mock_update_result = MagicMock()
        mock_update_result.modified_count = 1
        mock_collection.update_one.return_value = mock_update_result
        
        repo = FerretDBRepository()
        repo.deliverables_collection = mock_collection
        
        result = repo.update_deliverable(
            str(deliverable_id),
            student_name="Updated Name",
            mark=75.5,
            certainty_threshold=0.80
        )
        
        assert result is True
        
        call_args = mock_collection.update_one.call_args
        assert call_args[0][0] == {"_id": deliverable_id}
        update_doc = call_args[0][1]["$set"]
        assert update_doc["student_name"] == "Updated Name"
        assert update_doc["mark"] == 75.5
        assert update_doc["certainty_threshold"] == 0.80
        assert isinstance(update_doc["updated_at"], datetime)

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_delete_deliverable(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test deleting a deliverable."""
        deliverable_id = ObjectId("50c72b2f9b1d8e2a1c9d4b7f")
        assignment_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        gridfs_id = ObjectId("40c72b2f9b1d8e2a1c9d4b7f")
        
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        mock_deliverables_collection = MagicMock()
        mock_assignments_collection = MagicMock()
        
        mock_deliverables_collection.find_one.return_value = {
            "_id": deliverable_id,
            "assignment_id": assignment_id,
            "gridfs_id": gridfs_id
        }
        
        mock_fs = mock_gridfs.return_value
        
        mock_delete_result = MagicMock()
        mock_delete_result.deleted_count = 1
        mock_deliverables_collection.delete_one.return_value = mock_delete_result
        
        repo = FerretDBRepository()
        repo.deliverables_collection = mock_deliverables_collection
        repo.assignments_collection = mock_assignments_collection
        repo.fs = mock_fs
        
        result = repo.delete_deliverable(str(deliverable_id))
        
        assert result is True
        
        mock_deliverables_collection.find_one.assert_called_once_with({"_id": deliverable_id})
        mock_fs.delete.assert_called_once_with(gridfs_id)
        
        mock_assignments_collection.update_one.assert_called_once()
        update_call = mock_assignments_collection.update_one.call_args[0]
        assert update_call[0] == {"_id": assignment_id}
        assert "$pull" in update_call[1]
        assert update_call[1]["$pull"]["deliverables"] == deliverable_id
        
        mock_deliverables_collection.delete_one.assert_called_once_with({"_id": deliverable_id})

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_delete_deliverable_not_found(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test deleting a non-existent deliverable."""
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        mock_deliverables_collection = MagicMock()
        mock_assignments_collection = MagicMock()
        
        mock_deliverables_collection.find_one.return_value = None
        
        repo = FerretDBRepository()
        repo.deliverables_collection = mock_deliverables_collection
        repo.assignments_collection = mock_assignments_collection
        repo.fs = mock_gridfs.return_value
        
        result = repo.delete_deliverable("50c72b2f9b1d8e2a1c9d4b7f")
        
        assert result is False
        mock_deliverables_collection.delete_one.assert_not_called()
        mock_assignments_collection.update_one.assert_not_called()

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_store_deliverable_exception(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test store_deliverable with an exception."""
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        repo = FerretDBRepository()
        repo.deliverables_collection = MagicMock()
        repo.deliverables_collection.insert_one.side_effect = Exception("DB error")
        repo.fs = mock_gridfs.return_value
        
        with pytest.raises(Exception):
            repo.store_deliverable("60c72b2f9b1d8e2a1c9d4b7f", "test.pdf", b"content", "pdf", "application/pdf")

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_get_deliverable_exception(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test get_deliverable with an exception."""
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        repo = FerretDBRepository()
        repo.deliverables_collection = MagicMock()
        repo.deliverables_collection.find_one.side_effect = Exception("DB error")
        
        assert repo.get_deliverable("50c72b2f9b1d8e2a1c9d4b7f") is None

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_list_deliverables_exception(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test list_deliverables_by_assignment with an exception."""
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        repo = FerretDBRepository()
        repo.deliverables_collection = MagicMock()
        repo.deliverables_collection.find.side_effect = Exception("DB error")
        
        assert repo.list_deliverables_by_assignment("60c72b2f9b1d8e2a1c9d4b7f") == []

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_update_deliverable_exception(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test update_deliverable with an exception."""
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        repo = FerretDBRepository()
        repo.deliverables_collection = MagicMock()
        repo.deliverables_collection.update_one.side_effect = Exception("DB error")
        
        assert repo.update_deliverable("50c72b2f9b1d8e2a1c9d4b7f", student_name="Test") is False

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_delete_deliverable_exception(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test delete_deliverable with an exception."""
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        repo = FerretDBRepository()
        repo.deliverables_collection = MagicMock()
        repo.deliverables_collection.find_one.side_effect = Exception("DB error")
        
        assert repo.delete_deliverable("50c72b2f9b1d8e2a1c9d4b7f") is False

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_delete_deliverable_with_exception_during_update(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test delete_deliverable when assignment update fails."""
        deliverable_id = ObjectId("50c72b2f9b1d8e2a1c9d4b7f")
        assignment_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        gridfs_id = ObjectId("40c72b2f9b1d8e2a1c9d4b7f")
        
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        mock_deliverables_collection = MagicMock()
        mock_assignments_collection = MagicMock()
        
        mock_deliverables_collection.find_one.return_value = {
            "_id": deliverable_id,
            "assignment_id": assignment_id,
            "gridfs_id": gridfs_id
        }
        
        mock_fs = mock_gridfs.return_value
        
        mock_assignments_collection.update_one.side_effect = Exception("Update failed")
        
        mock_delete_result = MagicMock()
        mock_delete_result.deleted_count = 1
        mock_deliverables_collection.delete_one.return_value = mock_delete_result
        
        repo = FerretDBRepository()
        repo.deliverables_collection = mock_deliverables_collection
        repo.assignments_collection = mock_assignments_collection
        repo.fs = mock_fs
        
        result = repo.delete_deliverable(str(deliverable_id))
        
        assert result is False
        mock_fs.delete.assert_called_once_with(gridfs_id)

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_list_deliverables_invalid_document(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test list_deliverables_by_assignment with invalid document."""
        assignment_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        
        deliverables_data: list[Dict[str, Any]] = [
            {
                "_id": ObjectId(),
                "assignment_id": assignment_id,
                "student_name": "Valid Student",
                "filename": "valid.pdf",
                "gridfs_id": ObjectId(),
                "extension": "pdf",
                "content_type": "application/pdf",
                "uploaded_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            },
            {
                "_id": "invalid_objectid",
                "assignment_id": assignment_id,
            }
        ]
        
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        mock_collection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__iter__ = MagicMock(return_value=iter(deliverables_data))
        mock_collection.find.return_value.sort.return_value = mock_cursor
        
        repo = FerretDBRepository()
        repo.deliverables_collection = mock_collection
        
        result = repo.list_deliverables_by_assignment(str(assignment_id))
        
        assert len(result) == 1
        assert result[0].student_name == "Valid Student"

    @patch('src.repository.db.ferretdb.repository.GridFS')
    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_get_deliverable_without_gridfs_id(self, mock_mongo_client: MagicMock, mock_gridfs: MagicMock) -> None:
        """Test retrieving a deliverable without gridfs_id (content stored directly)."""
        deliverable_id = ObjectId("50c72b2f9b1d8e2a1c9d4b7f")
        
        deliverable_data: Dict[str, Any] = {
            "_id": deliverable_id,
            "assignment_id": ObjectId("60c72b2f9b1d8e2a1c9d4b7f"),
            "student_name": "Test Student",
            "mark": 90.0,
            "certainty_threshold": 0.85,
            "filename": "test.pdf",
            "content": b"inline content",
            "extension": "pdf",
            "content_type": "application/pdf",
            "uploaded_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "extracted_text": None
        }
        
        mock_client = mock_mongo_client.return_value
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = deliverable_data
        
        repo = FerretDBRepository()
        repo.deliverables_collection = mock_collection
        
        result = repo.get_deliverable(str(deliverable_id))
        
        assert isinstance(result, DeliverableModel)
        assert result.content == b"inline content"
        assert result.student_name == "Test Student"
        mock_collection.find_one.assert_called_once_with({"_id": deliverable_id})