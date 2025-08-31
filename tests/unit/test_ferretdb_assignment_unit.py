from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from bson import ObjectId
from typing import Dict, Any

from src.repository.db.ferretdb.repository import FerretDBRepository
from src.repository.db.models import AssignmentModel, FileModel


class TestFerretDBAssignmentRepository:
    """Unit tests for assignment-related methods in FerretDBRepository."""

    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_create_assignment(self, mock_mongo_client: MagicMock) -> None:
        """Test creating an assignment."""
        mock_client = mock_mongo_client.return_value
        mock_db = mock_client.__getitem__.return_value
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        mock_collection.insert_one.return_value = mock_insert_result

        repo = FerretDBRepository()
        repo.assignments_collection = mock_collection
        
        result = repo.create_assignment("Test Assignment", 0.75)
        
        assert result == "60c72b2f9b1d8e2a1c9d4b7f"
        
        # Verify the data passed to insert_one
        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["name"] == "Test Assignment"
        assert call_args["confidence_threshold"] == 0.75
        assert call_args["deliverables"] == []
        assert call_args["evaluation_rubrics"] == []
        assert call_args["relevant_documents"] == []
        assert isinstance(call_args["created_at"], datetime)
        assert isinstance(call_args["updated_at"], datetime)

    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_get_assignment_found(self, mock_mongo_client: MagicMock) -> None:
        """Test retrieving an assignment that exists."""
        assignment_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        assignment_data: Dict[str, Any] = {
            "_id": assignment_id,
            "name": "Test Assignment",
            "confidence_threshold": 0.75,
            "deliverables": [],
            "evaluation_rubrics": [],
            "relevant_documents": [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        
        mock_mongo_client.return_value
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = assignment_data
        
        repo = FerretDBRepository()
        repo.assignments_collection = mock_collection
        
        result = repo.get_assignment(str(assignment_id))
        
        assert isinstance(result, AssignmentModel)
        assert result.name == "Test Assignment"
        assert result.confidence_threshold == 0.75
        mock_collection.find_one.assert_called_once_with({"_id": assignment_id})

    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_get_assignment_not_found(self, mock_mongo_client: MagicMock) -> None:
        """Test retrieving an assignment that doesn't exist."""
        mock_mongo_client.return_value
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = None
        
        repo = FerretDBRepository()
        repo.assignments_collection = mock_collection
        
        result = repo.get_assignment("60c72b2f9b1d8e2a1c9d4b7f")
        
        assert result is None

    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_list_assignments(self, mock_mongo_client: MagicMock) -> None:
        """Test listing all assignments."""
        assignments_data: list[Dict[str, Any]] = [
            {
                "_id": ObjectId(),
                "name": "Assignment 1",
                "confidence_threshold": 0.70,
                "deliverables": [],
                "evaluation_rubrics": [],
                "relevant_documents": [],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "_id": ObjectId(),
                "name": "Assignment 2",
                "confidence_threshold": 0.80,
                "deliverables": [],
                "evaluation_rubrics": [],
                "relevant_documents": [],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        ]
        
        mock_mongo_client.return_value
        mock_collection = MagicMock()
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

    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_delete_assignment(self, mock_mongo_client: MagicMock) -> None:
        """Test deleting an assignment."""
        assignment_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        
        mock_mongo_client.return_value
        mock_assignments_collection = MagicMock()
        mock_files_collection = MagicMock()
        
        mock_delete_result = MagicMock()
        mock_delete_result.deleted_count = 1
        mock_assignments_collection.delete_one.return_value = mock_delete_result
        
        repo = FerretDBRepository()
        repo.assignments_collection = mock_assignments_collection
        repo.files_collection = mock_files_collection
        
        result = repo.delete_assignment(str(assignment_id))
        
        assert result is True
        mock_files_collection.delete_many.assert_called_once_with({"assignment_id": assignment_id})
        mock_assignments_collection.delete_one.assert_called_once_with({"_id": assignment_id})

    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_delete_assignment_not_found(self, mock_mongo_client: MagicMock) -> None:
        """Test deleting a non-existent assignment."""
        mock_mongo_client.return_value
        mock_assignments_collection = MagicMock()
        mock_files_collection = MagicMock()
        
        mock_delete_result = MagicMock()
        mock_delete_result.deleted_count = 0
        mock_assignments_collection.delete_one.return_value = mock_delete_result
        
        repo = FerretDBRepository()
        repo.assignments_collection = mock_assignments_collection
        repo.files_collection = mock_files_collection
        
        result = repo.delete_assignment("60c72b2f9b1d8e2a1c9d4b7f")
        
        assert result is False

    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_update_assignment(self, mock_mongo_client: MagicMock) -> None:
        """Test updating an assignment."""
        assignment_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        
        mock_mongo_client.return_value
        mock_collection = MagicMock()
        
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
        
        # Verify update_one was called correctly
        call_args = mock_collection.update_one.call_args
        assert call_args[0][0] == {"_id": assignment_id}
        update_doc = call_args[0][1]["$set"]
        assert update_doc["name"] == "Updated Assignment"
        assert update_doc["confidence_threshold"] == 0.90
        assert isinstance(update_doc["updated_at"], datetime)

    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_store_file_rubric(self, mock_mongo_client: MagicMock) -> None:
        """Test storing a rubric file."""
        assignment_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        file_id = ObjectId("50c72b2f9b1d8e2a1c9d4b7f")
        
        mock_mongo_client.return_value
        mock_files_collection = MagicMock()
        mock_assignments_collection = MagicMock()
        
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = file_id
        mock_files_collection.insert_one.return_value = mock_insert_result
        
        repo = FerretDBRepository()
        repo.files_collection = mock_files_collection
        repo.assignments_collection = mock_assignments_collection
        
        result = repo.store_file(
            str(assignment_id),
            "rubric.pdf",
            b"content",
            "application/pdf",
            "rubric"
        )
        
        assert result == str(file_id)
        
        # Verify file was inserted
        file_call_args = mock_files_collection.insert_one.call_args[0][0]
        assert file_call_args["assignment_id"] == assignment_id
        assert file_call_args["filename"] == "rubric.pdf"
        assert file_call_args["content"] == b"content"
        assert file_call_args["content_type"] == "application/pdf"
        assert file_call_args["file_type"] == "rubric"
        
        # Verify assignment was updated
        mock_assignments_collection.update_one.assert_called_once_with(
            {"_id": assignment_id},
            {"$push": {"evaluation_rubrics": file_id}}
        )

    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_store_file_relevant_document(self, mock_mongo_client: MagicMock) -> None:
        """Test storing a relevant document file."""
        assignment_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        file_id = ObjectId("50c72b2f9b1d8e2a1c9d4b7f")
        
        mock_mongo_client.return_value
        mock_files_collection = MagicMock()
        mock_assignments_collection = MagicMock()
        
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = file_id
        mock_files_collection.insert_one.return_value = mock_insert_result
        
        repo = FerretDBRepository()
        repo.files_collection = mock_files_collection
        repo.assignments_collection = mock_assignments_collection
        
        result = repo.store_file(
            str(assignment_id),
            "example.docx",
            b"document content",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "relevant_document"
        )
        
        assert result == str(file_id)
        
        # Verify assignment was updated with relevant_documents
        mock_assignments_collection.update_one.assert_called_once_with(
            {"_id": assignment_id},
            {"$push": {"relevant_documents": file_id}}
        )

    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_get_file(self, mock_mongo_client: MagicMock) -> None:
        """Test retrieving a file."""
        file_id = ObjectId("50c72b2f9b1d8e2a1c9d4b7f")
        file_data: Dict[str, Any] = {
            "_id": file_id,
            "assignment_id": ObjectId("60c72b2f9b1d8e2a1c9d4b7f"),
            "filename": "test.pdf",
            "content": b"test content",
            "content_type": "application/pdf",
            "file_type": "rubric",
            "uploaded_at": datetime.now(timezone.utc),
        }
        
        mock_mongo_client.return_value
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = file_data
        
        repo = FerretDBRepository()
        repo.files_collection = mock_collection
        
        result = repo.get_file(str(file_id))
        
        assert isinstance(result, FileModel)
        assert result.filename == "test.pdf"
        assert result.content == b"test content"
        mock_collection.find_one.assert_called_once_with({"_id": file_id})

    @patch('src.repository.db.ferretdb.repository.MongoClient')
    def test_list_files_by_assignment(self, mock_mongo_client: MagicMock) -> None:
        """Test listing files for an assignment."""
        assignment_id = ObjectId("60c72b2f9b1d8e2a1c9d4b7f")
        files_data: list[Dict[str, Any]] = [
            {
                "_id": ObjectId(),
                "assignment_id": assignment_id,
                "filename": "rubric1.pdf",
                "content": b"content1",
                "content_type": "application/pdf",
                "file_type": "rubric",
                "uploaded_at": datetime.now(timezone.utc),
            },
            {
                "_id": ObjectId(),
                "assignment_id": assignment_id,
                "filename": "rubric2.pdf",
                "content": b"content2",
                "content_type": "application/pdf",
                "file_type": "rubric",
                "uploaded_at": datetime.now(timezone.utc),
            }
        ]
        
        mock_mongo_client.return_value
        mock_collection = MagicMock()
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