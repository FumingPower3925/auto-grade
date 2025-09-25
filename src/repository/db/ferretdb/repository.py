from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from gridfs import GridFS
from pydantic import ValidationError
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure

from config.config import get_config
from src.repository.db.base import DatabaseRepository
from src.repository.db.models import AssignmentModel, DeliverableModel, DocumentModel, FileModel

MONGO_PUSH = "$push"


class FerretDBRepository(DatabaseRepository):
    def __init__(self) -> None:
        config = get_config().database
        self.client: MongoClient[dict[str, Any]] = MongoClient(host=config.host, port=config.port)
        self.db: Database[dict[str, Any]] = self.client[config.name]
        self.collection: Collection[dict[str, Any]] = self.db["grades"]
        self.assignments_collection: Collection[dict[str, Any]] = self.db["assignments"]
        self.files_collection: Collection[dict[str, Any]] = self.db["files"]
        self.deliverables_collection: Collection[dict[str, Any]] = self.db["deliverables"]
        self.fs = GridFS(self.db)

    def health(self) -> bool:
        try:
            self.client.admin.command("ismaster")
            return True
        except ConnectionFailure:
            return False

    def store_document(
        self, assignment: str, deliverable: str, student_name: str, document: bytes, extension: str
    ) -> str:
        file_id = self.fs.put(document, filename=f"{student_name}_{assignment}.{extension}")

        document_data: dict[str, Any] = {
            "assignment": assignment,
            "deliverable": deliverable,
            "student_name": student_name,
            "gridfs_id": file_id,
            "extension": extension,
            "file_size": len(document),
        }
        result = self.collection.insert_one(document_data)
        return str(result.inserted_id)

    def get_document(self, document_id: str) -> DocumentModel | None:
        try:
            obj_id = ObjectId(document_id)
            document = self.collection.find_one({"_id": obj_id})
            if document:
                if "gridfs_id" in document:
                    file_data = self.fs.get(document["gridfs_id"])
                    document["document"] = file_data.read()
                return DocumentModel.model_validate(document)
            return None
        except Exception:
            return None

    def create_assignment(self, name: str, confidence_threshold: float) -> str:
        assignment_data: dict[str, Any] = {
            "name": name,
            "confidence_threshold": confidence_threshold,
            "deliverables": [],
            "evaluation_rubrics": [],
            "relevant_documents": [],
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        result = self.assignments_collection.insert_one(assignment_data)
        return str(result.inserted_id)

    def get_assignment(self, assignment_id: str) -> AssignmentModel | None:
        try:
            obj_id = ObjectId(assignment_id)
            assignment = self.assignments_collection.find_one({"_id": obj_id})
            if assignment:
                return AssignmentModel.model_validate(assignment)
            return None
        except Exception:
            return None

    def list_assignments(self) -> list[AssignmentModel]:
        assignments: list[AssignmentModel] = []
        for doc in self.assignments_collection.find().sort("created_at", -1):
            try:
                model = AssignmentModel.model_validate(doc)
            except ValidationError:
                model = None
            if model is not None:
                assignments.append(model)
        return assignments

    def delete_assignment(self, assignment_id: str) -> bool:
        try:
            obj_id = ObjectId(assignment_id)

            for file_doc in self.files_collection.find({"assignment_id": obj_id}):
                if "gridfs_id" in file_doc:
                    self.fs.delete(file_doc["gridfs_id"])

            for deliverable_doc in self.deliverables_collection.find({"assignment_id": obj_id}):
                if "gridfs_id" in deliverable_doc:
                    self.fs.delete(deliverable_doc["gridfs_id"])

            self.files_collection.delete_many({"assignment_id": obj_id})
            self.deliverables_collection.delete_many({"assignment_id": obj_id})

            result = self.assignments_collection.delete_one({"_id": obj_id})
            return result.deleted_count > 0
        except Exception:
            return False

    def update_assignment(self, assignment_id: str, **kwargs: Any) -> bool:
        try:
            obj_id = ObjectId(assignment_id)

            kwargs["updated_at"] = datetime.now(UTC)

            result = self.assignments_collection.update_one({"_id": obj_id}, {"$set": kwargs})
            return result.modified_count > 0
        except Exception:
            return False

    def store_file(self, assignment_id: str, filename: str, content: bytes, content_type: str, file_type: str) -> str:
        try:
            obj_id = ObjectId(assignment_id)

            gridfs_id = self.fs.put(
                content, filename=filename, content_type=content_type, assignment_id=str(obj_id), file_type=file_type
            )

            file_data: dict[str, Any] = {
                "assignment_id": obj_id,
                "filename": filename,
                "gridfs_id": gridfs_id,
                "content_type": content_type,
                "file_type": file_type,
                "file_size": len(content),
                "uploaded_at": datetime.now(UTC),
            }
            result = self.files_collection.insert_one(file_data)
            file_id = str(result.inserted_id)

            if file_type == "rubric":
                self.assignments_collection.update_one(
                    {"_id": obj_id}, {MONGO_PUSH: {"evaluation_rubrics": result.inserted_id}}
                )
            elif file_type == "relevant_document":
                self.assignments_collection.update_one(
                    {"_id": obj_id}, {MONGO_PUSH: {"relevant_documents": result.inserted_id}}
                )

            return file_id
        except Exception:
            raise

    def get_file(self, file_id: str) -> FileModel | None:
        try:
            obj_id = ObjectId(file_id)
            file_doc = self.files_collection.find_one({"_id": obj_id})
            if file_doc:
                if "gridfs_id" in file_doc:
                    file_data = self.fs.get(file_doc["gridfs_id"])
                    file_doc["content"] = file_data.read()
                return FileModel.model_validate(file_doc)
            return None
        except Exception:
            return None

    def list_files_by_assignment(self, assignment_id: str, file_type: str | None = None) -> list[FileModel]:
        try:
            obj_id = ObjectId(assignment_id)
            query: dict[str, Any] = {"assignment_id": obj_id}
            if file_type:
                query["file_type"] = file_type

            files: list[FileModel] = []
            for doc in self.files_collection.find(query).sort("uploaded_at", -1):
                if "gridfs_id" in doc:
                    doc["content"] = b""
                try:
                    model = FileModel.model_validate(doc)
                except ValidationError:
                    model = None
                if model is not None:
                    files.append(model)
            return files
        except Exception:
            return []

    def store_deliverable(
        self,
        assignment_id: str,
        filename: str,
        content: bytes,
        extension: str,
        content_type: str,
        student_name: str = "Unknown",
        extracted_text: str | None = None,
    ) -> str:
        try:
            obj_id = ObjectId(assignment_id)

            gridfs_id = self.fs.put(
                content,
                filename=filename,
                content_type=content_type,
                assignment_id=str(obj_id),
                student_name=student_name,
            )

            deliverable_data: dict[str, Any] = {
                "assignment_id": obj_id,
                "student_name": student_name,
                "mark": None,
                "certainty_threshold": None,
                "filename": filename,
                "gridfs_id": gridfs_id,
                "extension": extension,
                "content_type": content_type,
                "file_size": len(content),
                "uploaded_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
                "extracted_text": extracted_text,
            }
            result = self.deliverables_collection.insert_one(deliverable_data)
            deliverable_id = result.inserted_id

            self.assignments_collection.update_one(
                {"_id": obj_id},
                {MONGO_PUSH: {"deliverables": deliverable_id}, "$set": {"updated_at": datetime.now(UTC)}},
            )

            return str(deliverable_id)
        except Exception:
            raise

    def get_deliverable(self, deliverable_id: str) -> DeliverableModel | None:
        try:
            obj_id = ObjectId(deliverable_id)
            deliverable = self.deliverables_collection.find_one({"_id": obj_id})
            if deliverable:
                if "gridfs_id" in deliverable:
                    file_data = self.fs.get(deliverable["gridfs_id"])
                    deliverable["content"] = file_data.read()
                else:
                    deliverable["content"] = deliverable.get("content", b"")
                return DeliverableModel.model_validate(deliverable)
            return None
        except Exception:
            return None

    def list_deliverables_by_assignment(self, assignment_id: str) -> list[DeliverableModel]:
        try:
            obj_id = ObjectId(assignment_id)
            deliverables: list[DeliverableModel] = []
            for doc in self.deliverables_collection.find({"assignment_id": obj_id}).sort("uploaded_at", -1):
                if "gridfs_id" in doc:
                    doc["content"] = b""
                else:
                    doc["content"] = doc.get("content", b"")
                try:
                    model = DeliverableModel.model_validate(doc)
                except ValidationError:
                    model = None
                if model is not None:
                    deliverables.append(model)
            return deliverables
        except Exception:
            return []

    def update_deliverable(self, deliverable_id: str, **kwargs: Any) -> bool:
        try:
            obj_id = ObjectId(deliverable_id)

            kwargs["updated_at"] = datetime.now(UTC)

            result = self.deliverables_collection.update_one({"_id": obj_id}, {"$set": kwargs})
            return result.modified_count > 0
        except Exception:
            return False

    def delete_deliverable(self, deliverable_id: str) -> bool:
        try:
            obj_id = ObjectId(deliverable_id)

            deliverable = self.deliverables_collection.find_one({"_id": obj_id})
            if not deliverable:
                return False

            if "gridfs_id" in deliverable:
                self.fs.delete(deliverable["gridfs_id"])

            self.assignments_collection.update_one(
                {"_id": deliverable["assignment_id"]},
                {"$pull": {"deliverables": obj_id}, "$set": {"updated_at": datetime.now(UTC)}},
            )

            result = self.deliverables_collection.delete_one({"_id": obj_id})
            return result.deleted_count > 0
        except Exception:
            return False
