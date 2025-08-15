from typing import Any, Dict, Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure
from bson import ObjectId
from config.config import get_config
from src.repository.db.base import DatabaseRepository
from src.repository.db.models import DocumentModel


class FerretDBRepository(DatabaseRepository):

    def __init__(self) -> None:
        config = get_config().database
        self.client: MongoClient[Dict[str, Any]] = MongoClient(host=config.host, port=config.port)
        self.db: Database[Dict[str, Any]] = self.client[config.name]
        self.collection: Collection[Dict[str, Any]] = self.db["grades"]

    def health(self) -> bool:
        try:
            self.client.admin.command('ismaster')
            return True
        except ConnectionFailure:
            return False

    def store_document(self, assignment: str, deliverable: str, student_name: str, document: bytes, extension: str) -> str:
        document_data: Dict[str, Any] = {
            "assignment": assignment,
            "deliverable": deliverable,
            "student_name": student_name,
            "document": document,
            "extension": extension,
        }
        result = self.collection.insert_one(document_data)
        return str(result.inserted_id)

    def get_document(self, document_id: str) -> Optional[DocumentModel]:
        try:
            obj_id = ObjectId(document_id)
            document = self.collection.find_one({"_id": obj_id})
            if document:
                return DocumentModel.model_validate(document)
            return None
        except Exception:
            return None